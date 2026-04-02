"""Regression tests for the shipped Review Gate V2 MCP server."""

from __future__ import annotations

import asyncio
import shutil
import unittest
from pathlib import Path
from unittest import mock

from review_gate_test_loader import (
    disable_speech_monitoring,
    isolated_review_gate_user,
    isolated_review_gate_runtime,
    load_review_gate_module,
)


MODULE = load_review_gate_module()


class ReviewGateServerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user_context = isolated_review_gate_user()
        self.user_context.__enter__()
        self.runtime_context = isolated_review_gate_runtime(MODULE)
        self.runtime_context.__enter__()
        self.speech_context = disable_speech_monitoring(MODULE)
        self.speech_context.__enter__()
        self.addCleanup(self.speech_context.__exit__, None, None, None)
        self.addCleanup(self.runtime_context.__exit__, None, None, None)
        self.addCleanup(self.user_context.__exit__, None, None, None)

        self.server = MODULE.ReviewGateServer()
        self.runtime_root = MODULE.get_runtime_root()
        self.addCleanup(lambda: shutil.rmtree(self.runtime_root, ignore_errors=True))

    def _create_contract(self, trigger_id: str) -> dict:
        return self.server._create_session_contract(trigger_id)

    def _extension_envelope(self, trigger_id: str, **extra) -> dict:
        return {
            **self.server._session_envelope_fields(trigger_id),
            "source": "review_gate_extension",
            **extra,
        }

    async def _write_json_after(self, path: Path, payload: dict, delay: float = 0.01) -> None:
        await asyncio.sleep(delay)
        path.parent.mkdir(parents=True, exist_ok=True)
        MODULE._write_json_atomically(path, payload)

    async def _write_text_after(self, path: Path, payload: str, delay: float = 0.01) -> None:
        await asyncio.sleep(delay)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")

    async def test_trigger_cursor_popup_immediately_writes_signed_trigger_envelope(self):
        trigger_id = "trigger-signed"
        data = {
            "trigger_id": trigger_id,
            "tool": "review_gate_chat",
            "message": "Please review",
            "timestamp": "2026-04-02T22:00:00",
        }

        with mock.patch.object(MODULE.os, "sync", return_value=None):
            created = await self.server._trigger_cursor_popup_immediately(data)

        self.assertTrue(created)

        trigger_path = MODULE._session_file("trigger", trigger_id)
        self.assertTrue(trigger_path.exists())

        payload = MODULE._read_json_file(trigger_path)
        self.assertEqual(payload["protocol_version"], MODULE.IPC_PROTOCOL_VERSION)
        self.assertEqual(payload["trigger_issued_at"], data["timestamp"])
        self.assertEqual(payload["data"]["trigger_id"], trigger_id)
        self.assertEqual(payload["data"]["tool"], "review_gate_chat")
        self.assertIn("session_token", payload)
        self.assertIn("trigger_signature", payload)

        expected_signature = self.server._build_initial_trigger_signature(
            trigger_id=payload["trigger_id"],
            protocol_version=payload["protocol_version"],
            session_token=payload["session_token"],
            timestamp=payload["trigger_issued_at"],
            pid=payload["pid"],
            tool_name=payload["data"]["tool"],
        )
        self.assertEqual(payload["trigger_signature"], expected_signature)

    async def test_wait_for_extension_acknowledgement_accepts_matching_envelope(self):
        trigger_id = "ack-success"
        self._create_contract(trigger_id)
        ack_path = MODULE._session_file("ack", trigger_id)

        writer = asyncio.create_task(
            self._write_json_after(
                ack_path,
                self._extension_envelope(
                    trigger_id,
                    acknowledged=True,
                    status="acknowledged",
                    message="Popup open",
                ),
            )
        )
        self.addAsyncCleanup(writer.cancel)

        acknowledged = await self.server._wait_for_extension_acknowledgement(trigger_id, timeout=1)

        self.assertTrue(acknowledged)
        self.assertFalse(ack_path.exists())
        self.assertEqual(self.server._last_acknowledgement_outcome["status"], "acknowledged")
        self.assertEqual(self.server._last_acknowledgement_outcome["message"], "Popup open")

    async def test_wait_for_extension_acknowledgement_discards_invalid_envelopes_before_success(self):
        trigger_id = "ack-invalid-then-valid"
        self._create_contract(trigger_id)
        ack_path = MODULE._session_file("ack", trigger_id)

        async def write_sequence():
            await self._write_text_after(ack_path, "{not json", delay=0.01)
            await self._write_json_after(
                ack_path,
                {
                    **self.server._session_envelope_fields(trigger_id),
                    "source": "review_gate_extension",
                    "acknowledged": True,
                    "status": "acknowledged",
                    "session_token": "wrong-token",
                },
                delay=0.12,
            )
            await self._write_json_after(
                ack_path,
                self._extension_envelope(
                    trigger_id,
                    acknowledged=True,
                    status="acknowledged",
                    message="Recovered after invalid envelopes",
                ),
                delay=0.24,
            )

        writer = asyncio.create_task(write_sequence())
        self.addAsyncCleanup(writer.cancel)

        acknowledged = await self.server._wait_for_extension_acknowledgement(trigger_id, timeout=1)

        self.assertTrue(acknowledged)
        self.assertFalse(ack_path.exists())
        self.assertEqual(
            self.server._last_acknowledgement_outcome["message"],
            "Recovered after invalid envelopes",
        )

    async def test_wait_for_extension_acknowledgement_returns_busy_or_cancelled_outcome(self):
        for status, event_type, expected_message in (
            ("busy", "SESSION_BUSY", "Review Gate popup is already handling another active session."),
            ("cancelled", "SESSION_CANCELLED", "Review Gate popup was cancelled before it could be acknowledged."),
        ):
            with self.subTest(status=status):
                trigger_id = f"ack-{status}"
                self._create_contract(trigger_id)
                ack_path = MODULE._session_file("ack", trigger_id)

                writer = asyncio.create_task(
                    self._write_json_after(
                        ack_path,
                        self._extension_envelope(
                            trigger_id,
                            acknowledged=False,
                            status=status,
                            event_type=event_type,
                        ),
                    )
                )
                self.addAsyncCleanup(writer.cancel)

                acknowledged = await self.server._wait_for_extension_acknowledgement(trigger_id, timeout=1)

                self.assertFalse(acknowledged)
                self.assertEqual(self.server._last_acknowledgement_outcome["status"], status)
                self.assertEqual(
                    self.server._last_acknowledgement_outcome["message"],
                    expected_message,
                )

    async def test_wait_for_extension_acknowledgement_records_timeout(self):
        trigger_id = "ack-timeout"
        self._create_contract(trigger_id)

        acknowledged = await self.server._wait_for_extension_acknowledgement(trigger_id, timeout=0.2)

        self.assertFalse(acknowledged)
        self.assertEqual(self.server._last_acknowledgement_outcome["status"], "timeout")
        self.assertIn("within 0.2 seconds", self.server._last_acknowledgement_outcome["message"])

    async def test_wait_for_user_input_accepts_matching_response_and_formats_attachments(self):
        trigger_id = "response-success"
        self._create_contract(trigger_id)
        response_path = MODULE._session_file("response", trigger_id)

        writer = asyncio.create_task(
            self._write_json_after(
                response_path,
                self._extension_envelope(
                    trigger_id,
                    user_input="Approved with screenshot",
                    attachments=[
                        {"fileName": "mock.png", "mimeType": "image/png"},
                        {"fileName": "notes.txt", "mimeType": "text/plain"},
                    ],
                ),
            )
        )
        self.addAsyncCleanup(writer.cancel)

        response = await self.server._wait_for_user_input(trigger_id, timeout=1)

        self.assertIsNotNone(response)
        self.assertIn("Approved with screenshot", response)
        self.assertIn("Attached: Image: mock.png", response)
        self.assertEqual(self.server._last_session_outcome["status"], "response")
        self.assertEqual(len(self.server._last_attachments), 2)
        self.assertFalse(response_path.exists())

    async def test_wait_for_user_input_discards_wrong_session_response_before_success(self):
        trigger_id = "response-wrong-session"
        self._create_contract(trigger_id)
        response_path = MODULE._session_file("response", trigger_id)

        async def write_sequence():
            await self._write_json_after(
                response_path,
                {
                    **self.server._session_envelope_fields(trigger_id),
                    "source": "review_gate_extension",
                    "user_input": "should be ignored",
                    "session_token": "wrong-token",
                },
                delay=0.01,
            )
            await self._write_json_after(
                response_path,
                self._extension_envelope(
                    trigger_id,
                    user_input="Accepted response",
                    attachments=[{"fileName": "screen.png", "mimeType": "image/png"}],
                ),
                delay=0.14,
            )

        writer = asyncio.create_task(write_sequence())
        self.addAsyncCleanup(writer.cancel)

        response = await self.server._wait_for_user_input(trigger_id, timeout=1)

        self.assertEqual(response, "Accepted response\n\nAttached: Image: screen.png")
        self.assertFalse(response_path.exists())
        self.assertEqual(self.server._last_session_outcome["status"], "response")

    async def test_wait_for_user_input_returns_none_for_busy_or_cancelled_and_clears_attachments(self):
        for status, event_type, expected_message in (
            ("busy", "SESSION_BUSY", "Review Gate popup is already handling another active session."),
            ("cancelled", "SESSION_CANCELLED", "Review Gate popup was closed before the user responded."),
        ):
            with self.subTest(status=status):
                trigger_id = f"response-{status}"
                self._create_contract(trigger_id)
                response_path = MODULE._session_file("response", trigger_id)
                self.server._last_attachments = [{"fileName": "stale.png", "mimeType": "image/png"}]

                writer = asyncio.create_task(
                    self._write_json_after(
                        response_path,
                        self._extension_envelope(
                            trigger_id,
                            status=status,
                            event_type=event_type,
                            message=expected_message,
                        ),
                    )
                )
                self.addAsyncCleanup(writer.cancel)

                response = await self.server._wait_for_user_input(trigger_id, timeout=1)

                self.assertIsNone(response)
                self.assertEqual(self.server._last_session_outcome["status"], status)
                self.assertEqual(self.server._last_session_outcome["message"], expected_message)
                self.assertEqual(self.server._last_attachments, [])
                self.assertFalse(response_path.exists())

    async def test_wait_for_user_input_timeout_clears_attachments_and_records_timeout(self):
        trigger_id = "response-timeout"
        self._create_contract(trigger_id)
        self.server._last_attachments = [{"fileName": "stale.png", "mimeType": "image/png"}]

        response = await self.server._wait_for_user_input(trigger_id, timeout=0.2)

        self.assertIsNone(response)
        self.assertEqual(self.server._last_session_outcome["status"], "timeout")
        self.assertIn("within 0.2 seconds", self.server._last_session_outcome["message"])
        self.assertEqual(self.server._last_attachments, [])


if __name__ == "__main__":
    unittest.main()
