const assert = require('assert/strict');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const test = require('node:test');

const { loadExtensionForTest } = require('./load-extension');

const IPC_PROTOCOL_VERSION = 'review-gate-v2-session-v1';

function setupExtensionTest(t) {
    const loaded = loadExtensionForTest();
    t.after(() => {
        loaded.cleanup();
    });
    return loaded;
}

function writeJson(filePath, payload) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, JSON.stringify(payload, null, 2));
}

function readJson(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function waitForAsyncTurn() {
    return new Promise((resolve) => {
        setImmediate(resolve);
    });
}

function writeRuntimeSecret(hooks, secret) {
    const secretPath = hooks.getRuntimeSecretPath();
    fs.mkdirSync(path.dirname(secretPath), { recursive: true });
    fs.writeFileSync(secretPath, secret);
}

function writeHeartbeat(hooks, options = {}) {
    const heartbeat = {
        timestamp: options.timestamp || new Date().toISOString(),
        source: 'review_gate_mcp_status',
        protocol_version: IPC_PROTOCOL_VERSION,
        server_state: options.serverState || 'running',
        pid: options.pid || 4242
    };

    writeJson(hooks.getStatusFilePath(), heartbeat);
    return heartbeat;
}

function createTriggerEnvelope(options = {}) {
    const triggerId = options.triggerId || `review_${Date.now()}`;
    const sessionToken = options.sessionToken || `${triggerId}_token`;
    const timestamp = options.timestamp || new Date().toISOString();
    const toolName = options.tool || 'review_gate_chat';
    const pid = options.pid || 4242;
    const secret = options.secret || 'review-gate-secret';
    const signaturePayload = [
        triggerId,
        IPC_PROTOCOL_VERSION,
        sessionToken,
        timestamp,
        String(pid),
        toolName
    ].join('\n');
    const triggerSignature = options.triggerSignature || crypto
        .createHmac('sha256', secret)
        .update(signaturePayload)
        .digest('hex');

    return {
        timestamp,
        trigger_issued_at: options.triggerIssuedAt || timestamp,
        trigger_signature: triggerSignature,
        system: 'review-gate-v2',
        editor: 'cursor',
        source: 'review_gate_mcp',
        trigger_id: triggerId,
        protocol_version: IPC_PROTOCOL_VERSION,
        session_token: sessionToken,
        data: {
            tool: toolName,
            trigger_id: triggerId,
            message: options.message || 'Please review this change.',
            title: options.title || 'Review Gate',
            timestamp,
            immediate_activation: true
        },
        pid,
        active_window: true,
        mcp_integration: true,
        immediate_activation: true
    };
}

test('accepts a valid signed trigger and opens the Review Gate popup', { concurrency: false }, (t) => {
    const { hooks, context, state } = setupExtensionTest(t);
    const secret = 'valid-trigger-secret';
    const heartbeat = writeHeartbeat(hooks, { pid: 5511 });
    writeRuntimeSecret(hooks, secret);

    const trigger = createTriggerEnvelope({
        triggerId: 'review_valid_trigger',
        pid: heartbeat.pid,
        secret
    });
    const triggerFile = hooks.getSessionFilePath('trigger', trigger.trigger_id);
    writeJson(triggerFile, trigger);

    const processed = hooks.processTriggerFile(context, triggerFile);

    assert.equal(processed, true);
    assert.equal(state.panels.length, 1);
    assert.equal(state.panels[0].title, 'Review Gate');
    assert.equal(fs.existsSync(triggerFile), false);

    const acknowledgement = readJson(hooks.getSessionFilePath('ack', trigger.trigger_id));
    assert.equal(acknowledgement.acknowledged, true);
    assert.equal(acknowledgement.status, 'acknowledged');
    assert.equal(acknowledgement.trigger_id, trigger.trigger_id);
}
);

test('rejects forged and stale triggers before popup mutation', { concurrency: false }, (t) => {
    const { hooks, context, state } = setupExtensionTest(t);
    const secret = 'rejected-trigger-secret';
    const heartbeat = writeHeartbeat(hooks, { pid: 6612 });
    writeRuntimeSecret(hooks, secret);

    const forgedTrigger = createTriggerEnvelope({
        triggerId: 'review_forged_trigger',
        pid: heartbeat.pid,
        secret,
        triggerSignature: '0'.repeat(64)
    });
    const forgedTriggerFile = hooks.getSessionFilePath('trigger', forgedTrigger.trigger_id);
    writeJson(forgedTriggerFile, forgedTrigger);

    assert.equal(hooks.processTriggerFile(context, forgedTriggerFile), false);
    assert.equal(state.panels.length, 0);
    assert.equal(fs.existsSync(forgedTriggerFile), false);
    assert.equal(fs.existsSync(hooks.getExistingSessionFilePath('ack', forgedTrigger.trigger_id)), false);
    assert.equal(fs.existsSync(hooks.getExistingSessionFilePath('response', forgedTrigger.trigger_id)), false);

    const staleTimestamp = new Date(Date.now() - 16_000).toISOString();
    const staleTrigger = createTriggerEnvelope({
        triggerId: 'review_stale_trigger',
        pid: heartbeat.pid,
        secret,
        timestamp: staleTimestamp,
        triggerIssuedAt: staleTimestamp
    });
    const staleTriggerFile = hooks.getSessionFilePath('trigger', staleTrigger.trigger_id);
    writeJson(staleTriggerFile, staleTrigger);

    assert.equal(hooks.processTriggerFile(context, staleTriggerFile), false);
    assert.equal(state.panels.length, 0);
    assert.equal(fs.existsSync(staleTriggerFile), false);
    assert.equal(fs.existsSync(hooks.getExistingSessionFilePath('ack', staleTrigger.trigger_id)), false);
    assert.equal(fs.existsSync(hooks.getExistingSessionFilePath('response', staleTrigger.trigger_id)), false);
});

test('writes a busy session result when a second trigger arrives during an active popup', { concurrency: false }, (t) => {
    const { hooks, context, state } = setupExtensionTest(t);
    const secret = 'busy-trigger-secret';
    const heartbeat = writeHeartbeat(hooks, { pid: 7713 });
    writeRuntimeSecret(hooks, secret);

    const firstTrigger = createTriggerEnvelope({
        triggerId: 'review_primary_trigger',
        pid: heartbeat.pid,
        secret
    });
    const firstTriggerFile = hooks.getSessionFilePath('trigger', firstTrigger.trigger_id);
    writeJson(firstTriggerFile, firstTrigger);
    assert.equal(hooks.processTriggerFile(context, firstTriggerFile), true);
    assert.equal(state.panels.length, 1);

    const secondTrigger = createTriggerEnvelope({
        triggerId: 'review_secondary_trigger',
        pid: heartbeat.pid,
        secret
    });
    const secondTriggerFile = hooks.getSessionFilePath('trigger', secondTrigger.trigger_id);
    writeJson(secondTriggerFile, secondTrigger);

    assert.equal(hooks.processTriggerFile(context, secondTriggerFile), true);
    assert.equal(state.panels.length, 1);

    const busyAcknowledgement = readJson(hooks.getSessionFilePath('ack', secondTrigger.trigger_id));
    assert.equal(busyAcknowledgement.acknowledged, false);
    assert.equal(busyAcknowledgement.status, 'busy');
    assert.equal(busyAcknowledgement.owner_trigger_id, firstTrigger.trigger_id);

    const busyResponse = readJson(hooks.getSessionFilePath('response', secondTrigger.trigger_id));
    assert.equal(busyResponse.status, 'busy');
    assert.equal(busyResponse.event_type, 'SESSION_BUSY');
    assert.equal(busyResponse.owner_trigger_id, firstTrigger.trigger_id);
    assert.match(busyResponse.message, /already handling trigger review_primary_trigger/);
});

test('disposing an active MCP popup writes the documented cancelled result', { concurrency: false }, (t) => {
    const { hooks, context, state } = setupExtensionTest(t);
    const triggerId = 'review_cancelled_trigger';

    hooks.openReviewGatePopup(context, {
        message: 'Please provide your review.',
        mcpIntegration: true,
        triggerId,
        sessionToken: `${triggerId}_token`,
        protocolVersion: IPC_PROTOCOL_VERSION,
        toolData: {
            tool: 'review_gate_chat',
            trigger_id: triggerId
        }
    });

    assert.equal(state.panels.length, 1);
    state.panels[0].dispose();

    const cancelledResponse = readJson(hooks.getSessionFilePath('response', triggerId));
    assert.equal(cancelledResponse.status, 'cancelled');
    assert.equal(cancelledResponse.event_type, 'SESSION_CANCELLED');
    assert.equal(cancelledResponse.tool_type, 'review_gate_chat');
    assert.equal(
        cancelledResponse.message,
        'Review Gate popup was closed before a response was submitted.'
    );
});

test('handleImageUpload plus writeSessionResponse persists uploaded attachment metadata', { concurrency: false }, async (t) => {
    const { hooks, context, state } = setupExtensionTest(t);
    const triggerId = 'review_attachment_trigger';
    const imagePath = path.join(hooks.getRuntimeRoot(), 'sample.png');
    const imageBytes = Buffer.from(
        '89504e470d0a1a0a0000000d4948445200000001000000010802000000907753de0000000c4944415408d763f8ffff3f0005fe02fea7a6d50000000049454e44ae426082',
        'hex'
    );

    fs.mkdirSync(path.dirname(imagePath), { recursive: true });
    fs.writeFileSync(imagePath, imageBytes);

    hooks.openReviewGatePopup(context, {
        message: 'Attach an image.',
        mcpIntegration: true,
        triggerId,
        sessionToken: `${triggerId}_token`,
        protocolVersion: IPC_PROTOCOL_VERSION,
        toolData: {
            tool: 'review_gate_chat',
            trigger_id: triggerId
        }
    });

    state.setOpenDialogResult([{ fsPath: imagePath }]);
    hooks.handleImageUpload(triggerId);
    await waitForAsyncTurn();

    assert.equal(state.openDialogRequests.length, 1);
    assert.deepEqual(state.openDialogRequests[0].filters, {
        Images: ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']
    });

    const imageUploadMessage = state.panels[0].webview.messages.find((message) => {
        return message.command === 'imageUploaded';
    });

    assert.ok(imageUploadMessage);
    assert.equal(imageUploadMessage.imageData.fileName, 'sample.png');
    assert.equal(imageUploadMessage.imageData.mimeType, 'image/png');
    assert.equal(imageUploadMessage.imageData.size, imageBytes.length);
    assert.match(imageUploadMessage.imageData.dataUrl, /^data:image\/png;base64,/);

    assert.equal(
        hooks.writeSessionResponse(triggerId, 'Attached an image for review.', [imageUploadMessage.imageData]),
        true
    );

    const response = readJson(hooks.getSessionFilePath('response', triggerId));
    assert.equal(response.user_input, 'Attached an image for review.');
    assert.equal(response.attachments.length, 1);
    assert.equal(response.attachments[0].fileName, 'sample.png');
    assert.equal(response.attachments[0].mimeType, 'image/png');
    assert.equal(response.attachments[0].base64Data, imageBytes.toString('base64'));
});
