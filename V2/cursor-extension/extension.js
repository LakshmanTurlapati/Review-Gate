const vscode = require('vscode');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawn } = require('child_process');
const IPC_PROTOCOL_VERSION = 'review-gate-v2-session-v1';

function svgToDataUri(svgMarkup) {
    return `data:image/svg+xml;base64,${Buffer.from(svgMarkup).toString('base64')}`;
}

const WEBVIEW_ICON_URIS = Object.freeze({
    microphone: svgToDataUri(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="black" d="M12 14a3 3 0 0 0 3-3V7a3 3 0 1 0-6 0v4a3 3 0 0 0 3 3Zm5-3a1 1 0 1 1 2 0a7 7 0 0 1-6 6.93V21h3a1 1 0 1 1 0 2H8a1 1 0 1 1 0-2h3v-3.07A7 7 0 0 1 5 11a1 1 0 1 1 2 0a5 5 0 0 0 10 0Z"/></svg>`),
    stop: svgToDataUri(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect fill="black" x="7" y="7" width="10" height="10" rx="2"/></svg>`),
    spinner: svgToDataUri(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="black" d="M12 2a10 10 0 1 0 10 10h-3a7 7 0 1 1-7-7V2Z"/></svg>`),
    image: svgToDataUri(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="black" d="M6 4a3 3 0 0 0-3 3v10a3 3 0 0 0 3 3h12a3 3 0 0 0 3-3V7a3 3 0 0 0-3-3H6Zm0 2h12a1 1 0 0 1 1 1v6.59l-2.29-2.3a1 1 0 0 0-1.42 0l-1.79 1.8-2.79-2.8a1 1 0 0 0-1.42 0L5 15.59V7a1 1 0 0 1 1-1Zm3 2.5A1.5 1.5 0 1 1 9 11.5a1.5 1.5 0 0 1 0-3ZM6.41 18l3.59-3.59 2.79 2.8a1 1 0 0 0 1.42 0l1.79-1.8L19 18H6.41Z"/></svg>`),
    send: svgToDataUri(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="black" d="M11 20V8.83L8.41 11.4A1 1 0 0 1 7 10l4.3-4.3a1 1 0 0 1 1.4 0L17 10a1 1 0 1 1-1.41 1.41L13 8.83V20a1 1 0 1 1-2 0Z"/></svg>`),
    close: svgToDataUri(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="black" d="M7.7 6.3a1 1 0 0 0-1.4 1.4L10.59 12 6.3 16.3a1 1 0 1 0 1.4 1.4L12 13.41l4.3 4.29a1 1 0 0 0 1.4-1.4L13.41 12l4.29-4.3a1 1 0 0 0-1.4-1.4L12 10.59 7.7 6.3Z"/></svg>`),
    drop: svgToDataUri(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="black" d="M11 4a1 1 0 1 1 2 0v7.17l2.59-2.58A1 1 0 1 1 17 10l-4.3 4.3a1 1 0 0 1-1.4 0L7 10a1 1 0 1 1 1.41-1.41L11 11.17V4Zm-6 13a1 1 0 0 1 1 1v1h12v-1a1 1 0 1 1 2 0v1a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-1a1 1 0 0 1 1-1Z"/></svg>`)
});

// Cross-platform temp directory helper
function getTempPath(filename) {
    // Use /tmp/ for macOS and Linux, system temp for Windows
    if (process.platform === 'win32') {
        return path.join(os.tmpdir(), filename);
    } else {
        return path.join('/tmp', filename);
    }
}

function sanitizeRuntimeComponent(value, fallback = 'unknown-user') {
    const sanitized = String(value || '')
        .trim()
        .replace(/[^A-Za-z0-9._-]/g, '_')
        .replace(/^[._-]+|[._-]+$/g, '');

    return sanitized || fallback;
}

function getRuntimeUserId() {
    const candidates = [
        process.env.REVIEW_GATE_USER_ID,
        process.env.USER,
        process.env.USERNAME
    ];

    try {
        candidates.push(os.userInfo().username);
    } catch (error) {
        // Ignore userInfo lookup failures and fall back to "unknown-user".
    }

    for (const candidate of candidates) {
        if (candidate && String(candidate).trim()) {
            return sanitizeRuntimeComponent(candidate, 'unknown-user');
        }
    }

    return 'unknown-user';
}

function ensureDirectory(directoryPath) {
    fs.mkdirSync(directoryPath, { recursive: true, mode: 0o700 });
    if (process.platform !== 'win32') {
        try {
            fs.chmodSync(directoryPath, 0o700);
        } catch (error) {
            // Ignore chmod failures on filesystems that do not support POSIX permissions.
        }
    }
    return directoryPath;
}

function getRuntimeRoot() {
    return ensureDirectory(path.join(getTempPath(''), 'review-gate-v2', getRuntimeUserId()));
}

function getSessionsRoot() {
    return ensureDirectory(path.join(getRuntimeRoot(), 'sessions'));
}

function getSessionId(triggerId) {
    return sanitizeRuntimeComponent(triggerId, 'session');
}

function getSessionPath(triggerId) {
    return path.join(getSessionsRoot(), getSessionId(triggerId));
}

function getSessionDir(triggerId) {
    return ensureDirectory(getSessionPath(triggerId));
}

const SESSION_FILE_NAMES = {
    trigger: 'review_gate_trigger_{triggerId}.json',
    ack: 'review_gate_ack_{triggerId}.json',
    response: 'review_gate_response_{triggerId}.json',
    speechTrigger: 'review_gate_speech_trigger_{triggerId}.json',
    speechResponse: 'review_gate_speech_response_{triggerId}.json'
};
const STATUS_FILE_NAME = 'review_gate_status.json';
const RUNTIME_SECRET_FILE_NAME = 'review_gate_runtime_secret';
const INITIAL_TRIGGER_MAX_AGE_MS = 15 * 1000;
const STATUS_HEARTBEAT_MAX_AGE_MS = 30 * 1000;
const SESSION_STALE_MAX_AGE_MS = 10 * 60 * 1000;
const STALE_CLEANUP_INTERVAL_MS = 30 * 1000;

function getSessionFileName(kind, triggerId) {
    const sessionId = getSessionId(triggerId);
    return SESSION_FILE_NAMES[kind].replace('{triggerId}', sessionId);
}

function getSessionFilePath(kind, triggerId) {
    const sessionId = getSessionId(triggerId);
    return path.join(getSessionDir(sessionId), getSessionFileName(kind, sessionId));
}

function getExistingSessionFilePath(kind, triggerId) {
    const sessionId = getSessionId(triggerId);
    return path.join(getSessionPath(sessionId), getSessionFileName(kind, sessionId));
}

function getStatusFilePath() {
    return path.join(getRuntimeRoot(), STATUS_FILE_NAME);
}

function getRuntimeSecretPath() {
    return path.join(getRuntimeRoot(), RUNTIME_SECRET_FILE_NAME);
}

function isPathWithinRuntimeRoot(candidatePath, runtimeRoot) {
    const relativePath = path.relative(runtimeRoot, candidatePath);
    return relativePath === '' || (!relativePath.startsWith('..') && !path.isAbsolute(relativePath));
}

function assertSafeRuntimePath(targetPath, options = {}) {
    const runtimeRoot = fs.realpathSync.native(getRuntimeRoot());
    const normalizedPath = path.resolve(targetPath);

    if (!isPathWithinRuntimeRoot(normalizedPath, runtimeRoot)) {
        throw new Error(`Runtime path escapes Review Gate root: ${targetPath}`);
    }

    let chainTarget = normalizedPath;
    if (options.allowMissing && !fs.existsSync(normalizedPath)) {
        chainTarget = path.dirname(normalizedPath);
    }

    let currentPath = chainTarget;
    while (true) {
        const stats = fs.lstatSync(currentPath);
        if (stats.isSymbolicLink()) {
            throw new Error(`Refusing symlinked runtime path: ${currentPath}`);
        }
        if (currentPath === normalizedPath) {
            if (options.expectFile && !stats.isFile()) {
                throw new Error(`Refusing non-regular runtime file: ${currentPath}`);
            }
            if (options.expectDirectory && !stats.isDirectory()) {
                throw new Error(`Refusing non-directory runtime path: ${currentPath}`);
            }
        }
        if (currentPath === runtimeRoot) {
            break;
        }
        const parentPath = path.dirname(currentPath);
        if (parentPath === currentPath) {
            break;
        }
        currentPath = parentPath;
    }

    const resolvedPath = fs.realpathSync.native(chainTarget);
    if (!isPathWithinRuntimeRoot(resolvedPath, runtimeRoot)) {
        throw new Error(`Resolved runtime path escapes Review Gate root: ${targetPath}`);
    }

    return normalizedPath;
}

function readJsonFileSafely(filePath) {
    assertSafeRuntimePath(filePath, { expectFile: true });
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function writeJsonAtomically(filePath, payload) {
    ensureDirectory(path.dirname(filePath));
    assertSafeRuntimePath(path.dirname(filePath), { expectDirectory: true });

    try {
        assertSafeRuntimePath(filePath, { expectFile: true });
    } catch (error) {
        if (error.code !== 'ENOENT') {
            throw error;
        }
    }

    const tempPath = path.join(
        path.dirname(filePath),
        `.${path.basename(filePath)}.${process.pid}.${Date.now()}.tmp`
    );
    const serialized = JSON.stringify(payload, null, 2);
    let fileDescriptor;

    try {
        fileDescriptor = fs.openSync(tempPath, 'w', 0o600);
        fs.writeFileSync(fileDescriptor, serialized, 'utf8');
        fs.fsyncSync(fileDescriptor);
    } finally {
        if (fileDescriptor !== undefined) {
            fs.closeSync(fileDescriptor);
        }
    }

    try {
        fs.renameSync(tempPath, filePath);
        try {
            const directoryDescriptor = fs.openSync(path.dirname(filePath), 'r');
            try {
                fs.fsyncSync(directoryDescriptor);
            } finally {
                fs.closeSync(directoryDescriptor);
            }
        } catch (error) {
            // Ignore directory fsync failures on platforms that do not support them.
        }
    } finally {
        if (fs.existsSync(tempPath)) {
            fs.unlinkSync(tempPath);
        }
    }
}

function buildSessionEnvelope(triggerId, sessionContract, source = 'review_gate_extension') {
    const contract = sessionContract || getSessionContract(triggerId);
    if (!contract) {
        throw new Error(`Missing active session contract for trigger ${triggerId || 'unknown'}`);
    }

    return {
        trigger_id: contract.triggerId,
        protocol_version: contract.protocolVersion,
        session_token: contract.sessionToken,
        source: source
    };
}

function validateSessionEnvelope(envelope, options = {}) {
    if (!envelope || typeof envelope !== 'object' || Array.isArray(envelope)) {
        throw new Error('Session envelope must be a JSON object');
    }

    const triggerId = String(envelope.trigger_id || (envelope.data && envelope.data.trigger_id) || '').trim();
    if (!triggerId) {
        throw new Error('Session envelope is missing trigger_id');
    }

    const protocolVersion = String(envelope.protocol_version || '').trim();
    if (protocolVersion !== IPC_PROTOCOL_VERSION) {
        throw new Error(`Unsupported protocol version: ${protocolVersion || 'missing'}`);
    }

    const sessionToken = String(envelope.session_token || '').trim();
    if (!sessionToken) {
        throw new Error('Session envelope is missing session_token');
    }

    if (options.expectedTriggerId && triggerId !== options.expectedTriggerId) {
        throw new Error(`Unexpected trigger_id ${triggerId}`);
    }

    if (options.expectedSource) {
        const source = String(envelope.source || '').trim();
        if (source !== options.expectedSource) {
            throw new Error(`Unexpected session envelope source: ${source || 'missing'}`);
        }
    }

    if (options.expectedSystem) {
        const system = String(envelope.system || '').trim();
        if (system !== options.expectedSystem) {
            throw new Error(`Unexpected session envelope system: ${system || 'missing'}`);
        }
    }

    if (options.expectedEditor) {
        const editor = String(envelope.editor || '').trim();
        if (editor !== options.expectedEditor) {
            throw new Error(`Unexpected session envelope editor: ${editor || 'missing'}`);
        }
    }

    if (options.expectedSession) {
        const expectedSession = options.expectedSession;
        if (expectedSession.triggerId && expectedSession.triggerId !== triggerId) {
            throw new Error(`Session trigger mismatch for ${triggerId}`);
        }
        if (expectedSession.sessionToken && expectedSession.sessionToken !== sessionToken) {
            throw new Error(`Session token mismatch for ${triggerId}`);
        }
        if (expectedSession.protocolVersion && expectedSession.protocolVersion !== protocolVersion) {
            throw new Error(`Session protocol mismatch for ${triggerId}`);
        }
    }

    if (options.requireDataKeys && (!envelope.data || typeof envelope.data !== 'object' || Array.isArray(envelope.data))) {
        throw new Error('Session envelope data payload must be a JSON object');
    }

    if (options.requireDataKeys) {
        for (const key of options.requireDataKeys) {
            if (envelope.data[key] === undefined || envelope.data[key] === null || envelope.data[key] === '') {
                throw new Error(`Session envelope data is missing required field '${key}'`);
            }
        }
    }

    if (envelope.data && typeof envelope.data === 'object' && !Array.isArray(envelope.data)) {
        if (envelope.data.trigger_id && String(envelope.data.trigger_id).trim() !== triggerId) {
            throw new Error('Nested trigger_id does not match the session envelope');
        }
        if (envelope.data.protocol_version && String(envelope.data.protocol_version).trim() !== protocolVersion) {
            throw new Error('Nested protocol_version does not match the session envelope');
        }
        if (envelope.data.session_token && String(envelope.data.session_token).trim() !== sessionToken) {
            throw new Error('Nested session_token does not match the session envelope');
        }
    }

    return {
        ...envelope,
        trigger_id: triggerId,
        protocol_version: protocolVersion,
        session_token: sessionToken
    };
}

function getSessionAudioPath(triggerId, timestamp = Date.now()) {
    const sessionId = getSessionId(triggerId);
    return path.join(getSessionDir(sessionId), `review_gate_audio_${sessionId}_${timestamp}.wav`);
}

function loadRuntimeSecret() {
    const secretPath = assertSafeRuntimePath(getRuntimeSecretPath(), { expectFile: true });
    const runtimeSecret = fs.readFileSync(secretPath, 'utf8').trim();
    if (!runtimeSecret) {
        throw new Error('Missing Review Gate runtime secret');
    }
    return runtimeSecret;
}

function readMcpStatusHeartbeat(maxAgeMs = STATUS_HEARTBEAT_MAX_AGE_MS) {
    const statusPath = getStatusFilePath();
    if (!fs.existsSync(statusPath)) {
        throw new Error('Missing MCP status heartbeat');
    }

    const statusData = readJsonFileSafely(statusPath);
    const heartbeatTimestamp = Date.parse(String(statusData.timestamp || '').trim());
    const serverState = String(statusData.server_state || '').trim();
    const source = String(statusData.source || '').trim();
    const protocolVersion = String(statusData.protocol_version || '').trim();
    const pid = Number(statusData.pid);

    if (!Number.isFinite(heartbeatTimestamp) || !serverState) {
        throw new Error('Malformed MCP status heartbeat');
    }
    if (protocolVersion !== IPC_PROTOCOL_VERSION) {
        throw new Error(`Unexpected MCP status protocol: ${protocolVersion || 'missing'}`);
    }
    if (source !== 'review_gate_mcp_status') {
        throw new Error(`Unexpected MCP status source: ${source || 'missing'}`);
    }
    if (!Number.isInteger(pid) || pid <= 0) {
        throw new Error('Malformed MCP status heartbeat pid');
    }

    const heartbeatAgeMs = Date.now() - heartbeatTimestamp;
    if (heartbeatAgeMs < 0 || heartbeatAgeMs > maxAgeMs) {
        throw new Error('Stale MCP status heartbeat');
    }

    return {
        ...statusData,
        pid,
        server_state: serverState,
        protocol_version: protocolVersion,
        source,
        timestamp: new Date(heartbeatTimestamp).toISOString(),
        heartbeatAgeMs
    };
}

function buildInitialTriggerProofPayload(triggerData) {
    return [
        String(triggerData.trigger_id || '').trim(),
        String(triggerData.protocol_version || '').trim(),
        String(triggerData.session_token || '').trim(),
        String(triggerData.timestamp || '').trim(),
        String(triggerData.pid || '').trim(),
        String((triggerData.data && triggerData.data.tool) || '').trim()
    ].join('\n');
}

function verifyInitialTrigger(triggerData, runtimeSecret) {
    const providedSignature = String(triggerData.trigger_signature || '').trim().toLowerCase();
    if (!/^[a-f0-9]{64}$/.test(providedSignature)) {
        return false;
    }

    const expectedSignature = crypto
        .createHmac('sha256', runtimeSecret)
        .update(buildInitialTriggerProofPayload(triggerData))
        .digest('hex');

    return crypto.timingSafeEqual(
        Buffer.from(providedSignature, 'hex'),
        Buffer.from(expectedSignature, 'hex')
    );
}

function validateInitialTriggerEnvelope(triggerData) {
    const triggerIssuedAt = String(triggerData.trigger_issued_at || '').trim();
    const timestamp = String(triggerData.timestamp || '').trim();
    if (!triggerIssuedAt || triggerIssuedAt !== timestamp) {
        throw new Error('Initial trigger timestamp mismatch');
    }

    const issuedAtMs = Date.parse(triggerIssuedAt);
    if (!Number.isFinite(issuedAtMs)) {
        throw new Error('Initial trigger freshness timestamp is invalid');
    }

    const triggerAgeMs = Date.now() - issuedAtMs;
    if (triggerAgeMs < 0 || triggerAgeMs > INITIAL_TRIGGER_MAX_AGE_MS) {
        throw new Error('Initial trigger freshness window expired');
    }

    const triggerPid = Number(triggerData.pid);
    if (!Number.isInteger(triggerPid) || triggerPid <= 0) {
        throw new Error('Initial trigger pid is invalid');
    }

    const toolName = String((triggerData.data && triggerData.data.tool) || '').trim();
    if (!toolName) {
        throw new Error('Initial trigger is missing tool name');
    }

    const statusData = readMcpStatusHeartbeat();
    if (['shutting_down', 'stopped'].includes(statusData.server_state)) {
        throw new Error(`Initial trigger rejected for MCP state ${statusData.server_state}`);
    }
    if (statusData.pid !== triggerPid) {
        throw new Error('Initial trigger pid does not match active MCP heartbeat');
    }

    const runtimeSecret = loadRuntimeSecret();
    if (!verifyInitialTrigger(triggerData, runtimeSecret)) {
        throw new Error('Initial trigger signature mismatch');
    }

    return {
        ...triggerData,
        pid: triggerPid,
        trigger_issued_at: triggerIssuedAt,
        trigger_signature: String(triggerData.trigger_signature || '').trim()
    };
}

function listPendingTriggerFiles() {
    const triggerPattern = /^review_gate_trigger_.+\.json$/;
    const pendingFiles = [];

    try {
        for (const sessionEntry of fs.readdirSync(getSessionsRoot(), { withFileTypes: true })) {
            if (!sessionEntry.isDirectory()) {
                continue;
            }

            const sessionDir = path.join(getSessionsRoot(), sessionEntry.name);
            for (const fileName of fs.readdirSync(sessionDir)) {
                if (!triggerPattern.test(fileName)) {
                    continue;
                }

                const filePath = path.join(sessionDir, fileName);
                try {
                    if (fs.lstatSync(filePath).isFile()) {
                        pendingFiles.push(filePath);
                    }
                } catch (error) {
                    // Ignore files that disappeared between the directory read and stat call.
                }
            }
        }
    } catch (error) {
        if (error.code !== 'ENOENT') {
            logMessage(`Could not list pending trigger files: ${error.message}`);
        }
        return [];
    }

    return pendingFiles.sort((left, right) => {
        try {
            const leftStats = fs.statSync(left);
            const rightStats = fs.statSync(right);
            if (leftStats.mtimeMs !== rightStats.mtimeMs) {
                return leftStats.mtimeMs - rightStats.mtimeMs;
            }
        } catch (error) {
            return left.localeCompare(right);
        }
        return left.localeCompare(right);
    });
}

let chatPanel = null;
let reviewGateWatcher = null;
let outputChannel = null;
let mcpStatus = false;
let statusCheckInterval = null;
let activeMcpSession = null;
let handledTriggerIds = new Set();
let lastStaleCleanupAt = 0;
let currentPopupContext = {
    message: null,
    triggerId: null,
    mcpIntegration: false,
    specialHandling: null,
    toolData: null,
    sessionToken: null,
    protocolVersion: null
};
let currentRecording = null;

function setPopupContext(nextContext = {}) {
    currentPopupContext = {
        message: nextContext.message || null,
        triggerId: nextContext.triggerId || null,
        mcpIntegration: Boolean(nextContext.mcpIntegration),
        specialHandling: nextContext.specialHandling || null,
        toolData: nextContext.toolData || null,
        sessionToken: nextContext.sessionToken || null,
        protocolVersion: nextContext.protocolVersion || null
    };
}

function getPopupContext() {
    if (activeMcpSession) {
        return {
            message: activeMcpSession.message || null,
            triggerId: activeMcpSession.triggerId,
            mcpIntegration: true,
            specialHandling: activeMcpSession.specialHandling || null,
            toolData: activeMcpSession.toolData || null,
            sessionToken: activeMcpSession.sessionToken || null,
            protocolVersion: activeMcpSession.protocolVersion || null
        };
    }

    return { ...currentPopupContext };
}

function getSessionContract(triggerId) {
    if (!triggerId) {
        return null;
    }

    if (activeMcpSession && activeMcpSession.triggerId === triggerId) {
        return {
            triggerId: activeMcpSession.triggerId,
            sessionToken: activeMcpSession.sessionToken,
            protocolVersion: activeMcpSession.protocolVersion
        };
    }

    return null;
}

function clearActiveMcpSession(triggerId = null) {
    if (!activeMcpSession) {
        return;
    }

    if (triggerId && activeMcpSession.triggerId !== triggerId) {
        return;
    }

    activeMcpSession = null;
    setPopupContext();
}

function cleanupSessionDirectory(triggerId, reason = 'session cleanup') {
    if (!triggerId) {
        return false;
    }

    const sessionPath = getSessionPath(triggerId);
    if (!fs.existsSync(sessionPath)) {
        return false;
    }

    try {
        fs.rmSync(sessionPath, { recursive: true, force: true });
        logMessage(`${reason}: removed session directory ${path.basename(sessionPath)}`);
        return true;
    } catch (error) {
        logMessage(`Failed to remove session directory ${path.basename(sessionPath)}: ${error.message}`);
        return false;
    }
}

function getSessionLastActivity(sessionPath) {
    let latestMtime = 0;

    try {
        const sessionStats = fs.statSync(sessionPath);
        latestMtime = sessionStats.mtimeMs;
    } catch (error) {
        return latestMtime;
    }

    for (const entryName of fs.readdirSync(sessionPath)) {
        const entryPath = path.join(sessionPath, entryName);
        try {
            latestMtime = Math.max(latestMtime, fs.statSync(entryPath).mtimeMs);
        } catch (error) {
            // Ignore files that disappeared during the sweep.
        }
    }

    return latestMtime;
}

function removeSessionFile(filePath, reason = 'session file cleanup') {
    try {
        fs.lstatSync(filePath);
        fs.rmSync(filePath, { force: true });
        if (!reason.includes('Removed invalid runtime path')) {
            logMessage(`${reason}: ${path.basename(filePath)}`);
        }
    } catch (error) {
        if (error.code !== 'ENOENT') {
            logMessage(`Failed to remove ${path.basename(filePath)}: ${error.message}`);
        }
    }
}

function escapeRegExp(value) {
    return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function generateWebviewNonce() {
    return crypto.randomBytes(18).toString('base64').replace(/[^A-Za-z0-9]/g, '');
}

function serializeForWebview(value) {
    return JSON.stringify(value)
        .replace(/</g, '\\u003c')
        .replace(/>/g, '\\u003e')
        .replace(/&/g, '\\u0026')
        .replace(/\u2028/g, '\\u2028')
        .replace(/\u2029/g, '\\u2029');
}

function resolveSpeechTriggerId(triggerId = null) {
    const popupContext = getPopupContext();
    if (activeMcpSession && activeMcpSession.triggerId) {
        return activeMcpSession.triggerId;
    }

    if (triggerId) {
        return triggerId;
    }

    if (popupContext.triggerId) {
        return popupContext.triggerId;
    }

    const manualTriggerId = `manual_${Date.now()}`;
    setPopupContext({
        ...popupContext,
        triggerId: manualTriggerId
    });
    return manualTriggerId;
}

function isSpeechSessionCurrent(triggerId) {
    if (!triggerId) {
        return false;
    }

    const popupContext = getPopupContext();
    if (activeMcpSession && activeMcpSession.triggerId) {
        return activeMcpSession.triggerId === triggerId;
    }

    return popupContext.triggerId === triggerId;
}

function removeSessionAudioFiles(triggerId, reason = 'session audio cleanup') {
    if (!triggerId) {
        return 0;
    }

    const sessionId = getSessionId(triggerId);
    const sessionDir = getSessionPath(sessionId);
    const audioPattern = new RegExp(`^review_gate_audio_${escapeRegExp(sessionId)}_.+\\.wav$`);
    let removedCount = 0;

    try {
        for (const fileName of fs.readdirSync(sessionDir)) {
            if (!audioPattern.test(fileName)) {
                continue;
            }

            const filePath = path.join(sessionDir, fileName);
            try {
                fs.unlinkSync(filePath);
                removedCount += 1;
                logMessage(`${reason}: ${filePath}`);
            } catch (error) {
                if (error.code !== 'ENOENT') {
                    logMessage(`Failed to remove audio file ${filePath}: ${error.message}`);
                }
            }
        }
    } catch (error) {
        if (error.code !== 'ENOENT') {
            logMessage(`Failed to scan for session audio files: ${error.message}`);
        }
    }

    return removedCount;
}

function cleanupSessionSpeechArtifacts(triggerId, reason = 'session speech cleanup', options = {}) {
    if (!triggerId) {
        return 0;
    }

    removeSessionFile(getExistingSessionFilePath('speechTrigger', triggerId), `${reason}: removed speech trigger`);
    removeSessionFile(getExistingSessionFilePath('speechResponse', triggerId), `${reason}: removed speech response`);

    if (options.removeAudioFiles) {
        return removeSessionAudioFiles(triggerId, `${reason}: removed audio file`);
    }

    return 0;
}

function cancelActiveRecording(reason, triggerId = null) {
    if (!currentRecording) {
        return false;
    }

    if (triggerId && currentRecording.triggerId !== triggerId) {
        return false;
    }

    const recording = currentRecording;
    currentRecording = null;

    if (recording.finalizeTimer) {
        clearTimeout(recording.finalizeTimer);
    }

    if (recording.forceKillTimer) {
        clearTimeout(recording.forceKillTimer);
    }

    try {
        if (recording.pid) {
            recording.kill('SIGKILL');
        }
    } catch (error) {
        logMessage(`Could not terminate recording process ${recording.pid}: ${error.message}`);
    }

    if (recording.audioFile) {
        try {
            if (fs.existsSync(recording.audioFile)) {
                fs.unlinkSync(recording.audioFile);
                logMessage(`${reason}: removed recording file ${recording.audioFile}`);
            }
        } catch (error) {
            logMessage(`Failed to remove recording file ${recording.audioFile}: ${error.message}`);
        }
    }

    logMessage(`${reason}: cancelled active recording for trigger ${recording.triggerId || 'unknown'}`);
    return true;
}

function cleanupStaleSessionFiles(maxAgeMs = SESSION_STALE_MAX_AGE_MS) {
    const now = Date.now();
    let removedCount = 0;
    const activeSessionIds = new Set();

    if (activeMcpSession && activeMcpSession.triggerId) {
        activeSessionIds.add(getSessionId(activeMcpSession.triggerId));
    }
    if (currentPopupContext.triggerId && chatPanel) {
        activeSessionIds.add(getSessionId(currentPopupContext.triggerId));
    }
    if (currentRecording && currentRecording.triggerId) {
        activeSessionIds.add(getSessionId(currentRecording.triggerId));
    }

    try {
        for (const sessionEntry of fs.readdirSync(getSessionsRoot(), { withFileTypes: true })) {
            if (!sessionEntry.isDirectory()) {
                continue;
            }

            const sessionId = sessionEntry.name;
            if (activeSessionIds.has(sessionId)) {
                continue;
            }

            const sessionPath = path.join(getSessionsRoot(), sessionId);

            try {
                const latestMtime = getSessionLastActivity(sessionPath);
                if (!latestMtime || now - latestMtime <= maxAgeMs) {
                    continue;
                }

                if (cleanupSessionDirectory(sessionId, 'Removed stale session cleanup')) {
                    removedCount += 1;
                }
            } catch (error) {
                if (error.code !== 'ENOENT') {
                    logMessage(`Failed stale cleanup for ${sessionPath}: ${error.message}`);
                }
            }
        }
    } catch (error) {
        if (error.code !== 'ENOENT') {
            logMessage(`Failed to scan session runtime directory for stale cleanup: ${error.message}`);
        }
    }

    return removedCount;
}

function maybeCleanupStaleSessionFiles(maxAgeMs = SESSION_STALE_MAX_AGE_MS) {
    const now = Date.now();
    if (now - lastStaleCleanupAt < STALE_CLEANUP_INTERVAL_MS) {
        return 0;
    }

    lastStaleCleanupAt = now;
    return cleanupStaleSessionFiles(maxAgeMs);
}

function writeSessionResult(triggerId, status, payload = {}, sessionContract = null) {
    if (!triggerId) {
        logMessage(`Cannot write session result without trigger ID (status: ${status})`);
        return false;
    }

    const eventType = payload.eventType || (
        status === 'busy'
            ? 'SESSION_BUSY'
            : status === 'cancelled'
                ? 'SESSION_CANCELLED'
                : 'SESSION_RESULT'
    );
    const responseFile = getSessionFilePath('response', triggerId);

    try {
        const responseData = {
            timestamp: new Date().toISOString(),
            ...buildSessionEnvelope(triggerId, sessionContract),
            status: status,
            event_type: eventType,
            message: payload.message || '',
            user_input: payload.userInput || '',
            response: payload.userInput || '',
            attachments: payload.attachments || [],
            owner_trigger_id: payload.ownerTriggerId || null,
            owner_message_present: Boolean(payload.ownerMessage),
            tool_type: payload.toolType || null,
            source: 'review_gate_extension',
            popup_active: Boolean(activeMcpSession && activeMcpSession.triggerId === triggerId)
        };
        writeJsonAtomically(responseFile, responseData);
        logMessage(`Session result written (${status}): ${path.basename(responseFile)}`);
        return true;
    } catch (error) {
        logMessage(`Failed to write session result ${path.basename(responseFile)}: ${error.message}`);
        return false;
    }
}

function writeSessionResponse(triggerId, inputText, attachments = [], eventType = 'MCP_RESPONSE', sessionContract = null) {
    if (!triggerId) {
        logMessage('Cannot write MCP response without trigger ID');
        return false;
    }

    const responseFile = getSessionFilePath('response', triggerId);

    try {
        const responseData = {
            timestamp: new Date().toISOString(),
            ...buildSessionEnvelope(triggerId, sessionContract),
            user_input: inputText,
            response: inputText,
            message: inputText,
            attachments: attachments,
            event_type: eventType,
            source: 'review_gate_extension'
        };
        writeJsonAtomically(responseFile, responseData);
        logMessage(`MCP response written: ${path.basename(responseFile)}`);
        return true;
    } catch (error) {
        logMessage(`Failed to write response file ${path.basename(responseFile)}: ${error.message}`);
        return false;
    }
}

function postPopupPrompt(message, sessionContext) {
    if (!chatPanel || !message || message.includes('I have completed')) {
        return;
    }

    chatPanel.webview.postMessage({
        command: 'addMessage',
        text: message,
        type: 'system',
        plain: true,
        toolData: sessionContext.toolData || null,
        mcpIntegration: sessionContext.mcpIntegration,
        triggerId: sessionContext.triggerId,
        specialHandling: sessionContext.specialHandling || null
    });
}

function activate(context) {
    // Create output channel for logging
    outputChannel = vscode.window.createOutputChannel('Review Gate V2 ゲート');
    context.subscriptions.push(outputChannel);
    
    logMessage('Review Gate V2 extension activated for Cursor MCP integration');

    // Register command to open Review Gate manually
    let disposable = vscode.commands.registerCommand('reviewGate.openChat', () => {
        openReviewGatePopup(context, {
            message: "Welcome to Review Gate V2! Please provide your review or feedback.",
            title: "Review Gate"
        });
    });

    context.subscriptions.push(disposable);

    // Start MCP status monitoring immediately
    startMcpStatusMonitoring(context);

    // Start Review Gate integration immediately
    startReviewGateIntegration(context);
    
    // Show activation notification
    vscode.window.showInformationMessage('Review Gate V2 activated! Use Cmd+Shift+R or wait for MCP tool calls.');
}

function logMessage(message) {
    const timestamp = new Date().toISOString();
    const logMsg = `[${timestamp}] ${message}`;
    console.log(logMsg);
    if (outputChannel) {
        outputChannel.appendLine(logMsg);
        // Don't auto-show output channel to avoid stealing focus
    }
}

function logUserInput(inputText, eventType = 'MESSAGE', triggerId = null, attachments = [], metadata = {}) {
    const timestamp = new Date().toISOString();
    const attachmentCount = Array.isArray(attachments) ? attachments.length : 0;
    const charCount = Number.isFinite(Number(metadata.charCount))
        ? Math.max(0, Math.floor(Number(metadata.charCount)))
        : (typeof inputText === 'string' ? inputText.length : 0);
    const sessionLabel = triggerId ? `trigger=${triggerId}` : 'trigger=manual';
    const detailParts = [];

    for (const [label, value] of [
        ['files', metadata.fileCount],
        ['images', metadata.imageCount],
        ['items', metadata.itemCount]
    ]) {
        const parsedValue = Number(value);
        if (Number.isFinite(parsedValue) && parsedValue >= 0) {
            detailParts.push(`${label}=${Math.floor(parsedValue)}`);
        }
    }

    const logMsg = `[${timestamp}] ${eventType} ${sessionLabel} chars=${charCount} attachments=${attachmentCount}${detailParts.length ? ` ${detailParts.join(' ')}` : ''}`;
    
    if (outputChannel) {
        outputChannel.appendLine(logMsg);
    }
}

function startMcpStatusMonitoring(context) {
    // Silent start - no logging to avoid focus stealing
    
    // Check MCP status every 2 seconds
    statusCheckInterval = setInterval(() => {
        checkMcpStatus();
    }, 2000);
    
    // Initial check
    checkMcpStatus();
    
    // Clean up on extension deactivation
    context.subscriptions.push({
        dispose: () => {
            if (statusCheckInterval) {
                clearInterval(statusCheckInterval);
            }
        }
    });
}

function checkMcpStatus() {
    try {
        const statusPath = getStatusFilePath();
        if (!fs.existsSync(statusPath)) {
            if (mcpStatus) {
                mcpStatus = false;
                updateChatPanelStatus();
            }
            return;
        }

        const statusData = readMcpStatusHeartbeat();
        const nextStatus = !['shutting_down', 'stopped'].includes(statusData.server_state);
        if (nextStatus !== mcpStatus) {
            mcpStatus = nextStatus;
            updateChatPanelStatus();
        }
    } catch (error) {
        logMessage(`MCP status check failed: ${error.message}`);
        if (mcpStatus) {
            mcpStatus = false;
            updateChatPanelStatus();
        }
    }
}

function updateChatPanelStatus() {
    if (chatPanel) {
        chatPanel.webview.postMessage({
            command: 'updateMcpStatus',
            active: activeMcpSession ? true : mcpStatus
        });
    }
}

function startReviewGateIntegration(context) {
    // Silent integration start

    cleanupStaleSessionFiles();
    processPendingTriggers(context);

    // Use a more robust polling approach instead of fs.watchFile
    // fs.watchFile can miss rapid file creation/deletion cycles
    const pollInterval = setInterval(() => {
        processPendingTriggers(context);
    }, 250); // Check every 250ms for better performance
    
    // Store the interval for cleanup
    reviewGateWatcher = pollInterval;
    
    // Add to context subscriptions for proper cleanup
    context.subscriptions.push({
        dispose: () => {
            if (pollInterval) {
                clearInterval(pollInterval);
            }
        }
    });
    
    // Immediate check on startup
    setTimeout(() => {
        processPendingTriggers(context);
    }, 100);
    
    // Show notification that we're ready
    vscode.window.showInformationMessage('Review Gate V2 MCP integration ready! Extension is monitoring for Cursor Agent tool calls...');
}

function processPendingTriggers(context) {
    maybeCleanupStaleSessionFiles();

    const pendingTriggers = listPendingTriggerFiles();
    for (const filePath of pendingTriggers) {
        if (processTriggerFile(context, filePath)) {
            break;
        }
    }
}

function processTriggerFile(context, filePath) {
    try {
        if (!fs.existsSync(filePath)) {
            return false;
        }

        const triggerData = validateSessionEnvelope(readJsonFileSafely(filePath), {
            expectedSource: 'review_gate_mcp',
            expectedSystem: 'review-gate-v2',
            expectedEditor: 'cursor',
            requireDataKeys: ['trigger_id', 'tool']
        });
        const expectedTriggerPath = path.resolve(getExistingSessionFilePath('trigger', triggerData.trigger_id));
        if (path.resolve(filePath) !== expectedTriggerPath) {
            removeSessionFile(filePath, 'Removed invalid runtime path trigger file');
            return false;
        }

        if (handledTriggerIds.has(triggerData.trigger_id)) {
            removeSessionFile(filePath, 'Removed already-handled trigger file');
            return false;
        }

        let validatedTriggerData;
        try {
            validatedTriggerData = validateInitialTriggerEnvelope(triggerData);
        } catch (validationError) {
            logMessage(`Rejected trigger=${triggerData.trigger_id} reason=invalid_trigger_proof`);
            removeSessionFile(filePath, 'Rejected unauthenticated trigger file');
            return false;
        }

        if (activeMcpSession && activeMcpSession.triggerId !== validatedTriggerData.trigger_id) {
            const busyMessage = `Review Gate popup is already handling trigger ${activeMcpSession.triggerId}`;
            const triggerContract = {
                triggerId: validatedTriggerData.trigger_id,
                sessionToken: validatedTriggerData.session_token,
                protocolVersion: validatedTriggerData.protocol_version
            };

            sendExtensionAcknowledgement(validatedTriggerData.trigger_id, validatedTriggerData.data.tool, {
                acknowledged: false,
                status: 'busy',
                message: busyMessage,
                ownerTriggerId: activeMcpSession.triggerId
            }, triggerContract);
            writeSessionResult(validatedTriggerData.trigger_id, 'busy', {
                eventType: 'SESSION_BUSY',
                message: busyMessage,
                ownerTriggerId: activeMcpSession.triggerId,
                ownerMessage: activeMcpSession.message || null,
                toolType: validatedTriggerData.data.tool
            }, triggerContract);

            handledTriggerIds.add(validatedTriggerData.trigger_id);
            removeSessionFile(filePath, 'Rejected busy trigger file');
            return true;
        }

        logMessage(`Review Gate triggered tool=${validatedTriggerData.data.tool} trigger=${validatedTriggerData.trigger_id}`);

        handleReviewGateToolCall(context, validatedTriggerData.data, {
            triggerId: validatedTriggerData.trigger_id,
            sessionToken: validatedTriggerData.session_token,
            protocolVersion: validatedTriggerData.protocol_version
        });
        handledTriggerIds.add(validatedTriggerData.trigger_id);
        removeSessionFile(filePath, 'Consumed trigger file');
        return true;
    } catch (error) {
        if (error.code !== 'ENOENT') { // Don't log file not found errors
            logMessage(`Error reading trigger file: ${error.message}`);
            removeSessionFile(filePath, 'Removed unreadable trigger file');
        }
        return false;
    }
}

function handleReviewGateToolCall(context, toolData, sessionContract) {
    // Silent tool call processing
    
    let popupOptions = {};
    
    switch (toolData.tool) {
        case 'review_gate':
            // UNIFIED: New unified tool that handles all modes
            const mode = toolData.mode || 'chat';
            let modeTitle = `Review Gate V2 - ${mode.charAt(0).toUpperCase() + mode.slice(1)} Mode`;
            if (toolData.unified_tool) {
                modeTitle = `Review Gate V2 ゲート - Unified (${mode})`;
            }
            
            popupOptions = {
                message: toolData.message || "Please provide your input:",
                title: toolData.title || modeTitle,
                autoFocus: true,
                toolData: toolData,
                mcpIntegration: true,
                specialHandling: `unified_${mode}`
            };
            break;
            
        case 'review_gate_chat':
            popupOptions = {
                message: toolData.message || "Please provide your review or feedback:",
                title: toolData.title || "Review Gate V2 - ゲート",
                autoFocus: true,
                toolData: toolData,
                mcpIntegration: true
            };
            break;
            
        case 'quick_review':
            popupOptions = {
                message: toolData.prompt || "Quick feedback needed:",
                title: toolData.title || "Review Gate V2 ゲート - Quick Review",
                autoFocus: true,
                toolData: toolData,
                mcpIntegration: true,
                specialHandling: 'quick_review'
            };
            break;
            
        case 'ingest_text':
            popupOptions = {
                message: `Cursor Agent received text input and needs your feedback:\n\n**Text Content:** ${toolData.text_content}\n**Source:** ${toolData.source}\n**Context:** ${toolData.context || 'None'}\n**Processing Mode:** ${toolData.processing_mode}\n\nPlease review and provide your feedback:`,
                title: toolData.title || "Review Gate V2 ゲート - Text Input",
                autoFocus: true,
                toolData: toolData,
                mcpIntegration: true
            };
            break;
            
        case 'shutdown_mcp':
            popupOptions = {
                message: `Cursor Agent is requesting to shutdown the MCP server:\n\n**Reason:** ${toolData.reason}\n**Immediate:** ${toolData.immediate ? 'Yes' : 'No'}\n**Cleanup:** ${toolData.cleanup ? 'Yes' : 'No'}\n\nType 'CONFIRM' to proceed with shutdown, or provide alternative instructions:`,
                title: toolData.title || "Review Gate V2 ゲート - Shutdown Confirmation",
                autoFocus: true,
                toolData: toolData,
                mcpIntegration: true,
                specialHandling: 'shutdown_mcp'
            };
            break;
            
        case 'file_review':
            popupOptions = {
                message: toolData.instruction || "Cursor Agent needs you to select files:",
                title: toolData.title || "Review Gate V2 ゲート - File Review",
                autoFocus: true,
                toolData: toolData,
                mcpIntegration: true
            };
            break;
            
        default:
            popupOptions = {
                message: toolData.message || toolData.prompt || toolData.instruction || "Cursor Agent needs your input. Please provide your response:",
                title: toolData.title || "Review Gate V2 ゲート - General Input",
                autoFocus: true,
                toolData: toolData,
                mcpIntegration: true
            };
    }
    
    // Add trigger ID to popup options
    popupOptions.triggerId = toolData.trigger_id;
    popupOptions.sessionToken = sessionContract ? sessionContract.sessionToken : null;
    popupOptions.protocolVersion = sessionContract ? sessionContract.protocolVersion : null;
    logMessage(`Opening Review Gate popup for trigger=${toolData.trigger_id}`);
    
    // Force consistent title regardless of tool call
    popupOptions.title = "Review Gate";
    
    // Immediately open Review Gate popup when tools are triggered by Cursor Agent
    openReviewGatePopup(context, popupOptions);
    
    // FIXED: Send acknowledgement to MCP server that popup was activated
    sendExtensionAcknowledgement(toolData.trigger_id, toolData.tool, {}, sessionContract);
    
    // Show appropriate notification
    const toolDisplayName = toolData.tool.replace('_', ' ').toUpperCase();
    vscode.window.showInformationMessage(`Cursor Agent triggered "${toolDisplayName}" - Review Gate popup opened for your input!`);
}

function sendExtensionAcknowledgement(triggerId, toolType, options = {}, sessionContract = null) {
    try {
        const timestamp = new Date().toISOString();
        const acknowledged = options.acknowledged !== undefined ? Boolean(options.acknowledged) : true;
        const ackData = {
            ...buildSessionEnvelope(triggerId, sessionContract),
            acknowledged: acknowledged,
            status: options.status || (acknowledged ? 'acknowledged' : 'error'),
            timestamp: timestamp,
            tool_type: toolType,
            extension: 'review-gate-v2',
            popup_activated: acknowledged,
            message: options.message || null,
            owner_trigger_id: options.ownerTriggerId || null
        };
        
        const ackFile = getSessionFilePath('ack', triggerId);
        writeJsonAtomically(ackFile, ackData);
        
        // Silent acknowledgement 
        
    } catch (error) {
        logMessage(`Could not send extension acknowledgement: ${error.message}`);
    }
}

function openReviewGatePopup(context, options = {}) {
    const {
        message = "Welcome to Review Gate V2! Please provide your review or feedback.",
        title = "Review Gate",
        autoFocus = false,
        toolData = null,
        mcpIntegration = false,
        triggerId = null,
        specialHandling = null,
        sessionToken = null,
        protocolVersion = null
    } = options;

    const nextPopupContext = {
        message: message,
        triggerId: triggerId,
        mcpIntegration: mcpIntegration,
        specialHandling: specialHandling,
        toolData: toolData,
        sessionToken: sessionToken,
        protocolVersion: protocolVersion
    };

    if (mcpIntegration && triggerId) {
        activeMcpSession = {
            triggerId: triggerId,
            sessionToken: sessionToken,
            protocolVersion: protocolVersion,
            message: message,
            specialHandling: specialHandling,
            toolData: toolData
        };
        setPopupContext(nextPopupContext);
    } else if (!activeMcpSession) {
        setPopupContext(nextPopupContext);
    }

    // Silent popup opening

    if (chatPanel) {
        chatPanel.reveal(vscode.ViewColumn.One);
        // Always use consistent title
        chatPanel.title = "Review Gate";

        setTimeout(() => {
            if (!chatPanel) {
                return;
            }

            const popupContext = getPopupContext();
            chatPanel.webview.postMessage({
                command: 'updateMcpStatus',
                active: popupContext.mcpIntegration ? true : mcpStatus
            });

            if (mcpIntegration || !activeMcpSession) {
                postPopupPrompt(message, popupContext);
            }
        }, 100);

        if (autoFocus) {
            setTimeout(() => {
                chatPanel.webview.postMessage({
                    command: 'focus'
                });
            }, 200);
        }

        return;
    }

    // Create webview panel
    chatPanel = vscode.window.createWebviewPanel(
        'reviewGateChat',
        title,
        vscode.ViewColumn.One,
        {
            enableScripts: true,
            retainContextWhenHidden: true,
            localResourceRoots: [context.extensionUri]
        }
    );

    // Set the HTML content
    const scriptNonce = generateWebviewNonce();
    chatPanel.webview.html = getReviewGateHTML({
        title: title,
        mcpIntegration: mcpIntegration,
        cspSource: chatPanel.webview.cspSource,
        nonce: scriptNonce
    });

    // Handle messages from webview
    chatPanel.webview.onDidReceiveMessage(
        webviewMessage => {
            const popupContext = getPopupContext();
            const currentTriggerId = popupContext.triggerId;
            const currentMcpIntegration = popupContext.mcpIntegration;
            const currentSpecialHandling = popupContext.specialHandling;
            
            switch (webviewMessage.command) {
                case 'send':
                    const attachments = webviewMessage.attachments || [];
                    const eventType = currentMcpIntegration ? 'MCP_RESPONSE' : 'REVIEW_SUBMITTED';
                    logUserInput(webviewMessage.text, eventType, currentTriggerId, attachments);
                    let responseWritten = true;

                    if (currentMcpIntegration && currentTriggerId) {
                        responseWritten = writeSessionResponse(currentTriggerId, webviewMessage.text, attachments, eventType);
                    }

                    handleReviewMessage(webviewMessage.text, attachments, currentTriggerId, currentMcpIntegration, currentSpecialHandling);

                    if (currentTriggerId) {
                        cancelActiveRecording('Review Gate response submitted', currentTriggerId);
                        cleanupSessionSpeechArtifacts(currentTriggerId, 'Submitted session cleanup', {
                            removeAudioFiles: true
                        });
                        if (!currentMcpIntegration) {
                            cleanupSessionDirectory(currentTriggerId, 'Submitted manual session cleanup');
                        }
                    }

                    if (currentMcpIntegration && currentTriggerId && responseWritten) {
                        clearActiveMcpSession(currentTriggerId);
                    }
                    break;
                case 'attach':
                    logUserInput('User clicked attachment button', 'ATTACHMENT_CLICK', currentTriggerId);
                    handleFileAttachment(currentTriggerId);
                    break;
                case 'uploadImage':
                    logUserInput('User clicked image upload button', 'IMAGE_UPLOAD_CLICK', currentTriggerId);
                    handleImageUpload(currentTriggerId);
                    break;
                case 'logPastedImage':
                    logUserInput('', 'IMAGE_PASTED', currentTriggerId, [], { imageCount: 1 });
                    break;
                case 'logDragDropImage':
                    logUserInput('', 'IMAGE_DROPPED', currentTriggerId, [], { imageCount: 1 });
                    break;
                case 'logImageRemoved':
                    logUserInput('', 'IMAGE_REMOVED', currentTriggerId, [], { imageCount: 1 });
                    break;
                case 'startRecording':
                    logUserInput('User started speech recording', 'SPEECH_START', currentTriggerId);
                    startNodeRecording(currentTriggerId);
                    break;
                case 'stopRecording':
                    logUserInput('User stopped speech recording', 'SPEECH_STOP', currentTriggerId);
                    stopNodeRecording(currentTriggerId);
                    break;
                case 'showError':
                    vscode.window.showErrorMessage(webviewMessage.message);
                    break;
                case 'ready':
                    const readyContext = getPopupContext();
                    chatPanel.webview.postMessage({
                        command: 'updateMcpStatus',
                        active: readyContext.mcpIntegration ? true : mcpStatus
                    });
                    postPopupPrompt(readyContext.message, readyContext);
                    break;
            }
        },
        undefined,
        context.subscriptions
    );

    // Clean up when panel is closed
    chatPanel.onDidDispose(
        () => {
            const closingSession = activeMcpSession ? { ...activeMcpSession } : null;
            const closingTriggerId = closingSession ? closingSession.triggerId : currentPopupContext.triggerId;
            chatPanel = null;

            if (closingSession) {
                writeSessionResult(closingSession.triggerId, 'cancelled', {
                    eventType: 'SESSION_CANCELLED',
                    message: 'Review Gate popup was closed before a response was submitted.',
                    ownerTriggerId: closingSession.triggerId,
                    ownerMessage: closingSession.message || null,
                    toolType: closingSession.toolData ? closingSession.toolData.tool : null
                });
            }

            cancelActiveRecording('Popup disposed', closingTriggerId || null);
            if (closingTriggerId) {
                cleanupSessionSpeechArtifacts(closingTriggerId, 'Disposed session cleanup', {
                    removeAudioFiles: true
                });
                if (!closingSession) {
                    cleanupSessionDirectory(closingTriggerId, 'Disposed manual session cleanup');
                }
            }

            activeMcpSession = null;
            setPopupContext();
        },
        null,
        context.subscriptions
    );

    // Auto-focus if requested
    if (autoFocus) {
        setTimeout(() => {
            chatPanel.webview.postMessage({
                command: 'focus'
            });
        }, 200);
    }
}

function getReviewGateHTML(options = {}) {
    const {
        title = 'Review Gate',
        mcpIntegration = false,
        cspSource = '',
        nonce = ''
    } = options;
    const popupConfig = serializeForWebview({
        title: String(title || 'Review Gate'),
        mcpIntegration: Boolean(mcpIntegration),
        placeholders: {
            defaultBase: 'Type your review or feedback',
            mcpBase: 'Cursor Agent is waiting for your response',
            inactive: 'MCP server is not active. Please start the server to enable input.',
            processing: 'Processing speech... Please wait',
            speechFailed: 'Speech failed - try again',
            noSpeech: 'No speech detected - try again'
        },
        titles: {
            attach: 'Upload image',
            mic: 'Click to speak',
            micReady: 'Click to speak (SoX recording)',
            recording: 'Recording... Click to stop',
            processing: 'Processing speech...',
            removeImage: 'Remove image',
            send: `Send ${mcpIntegration ? 'response to Agent' : 'review'}`
        }
    });
    const contentSecurityPolicy = `default-src 'none'; img-src ${cspSource} data:; style-src ${cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';`;

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="${contentSecurityPolicy}">
    <title>Review Gate</title>
    <style>
        body {
            font-family: var(--vscode-font-family);
            color: var(--vscode-foreground);
            background: var(--vscode-editor-background);
            margin: 0;
            padding: 0;
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .review-container {
            height: 100vh;
            display: flex;
            flex-direction: column;
            max-width: 600px;
            margin: 0 auto;
            width: 100%;
            animation: slideIn 0.3s ease-out;
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .review-header {
            flex-shrink: 0;
            padding: 16px 20px 12px 20px;
            border-bottom: 1px solid var(--vscode-panel-border);
            display: flex;
            align-items: center;
            gap: 8px;
            background: var(--vscode-editor-background);
        }
        
        .review-title {
            font-size: 18px;
            font-weight: 600;
            color: var(--vscode-foreground);
        }
        
        .review-author {
            font-size: 12px;
            opacity: 0.7;
            margin-left: auto;
        }
        
        .status-indicator {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--vscode-charts-orange);
            animation: pulse 2s infinite;
            transition: background-color 0.3s ease;
            margin-right: 4px;
        }
        
        .status-indicator.active {
            background: var(--vscode-charts-green);
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .messages-container {
            flex: 1;
            overflow-y: auto;
            padding: 16px 20px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        
        .message {
            display: flex;
            gap: 8px;
            animation: messageSlide 0.3s ease-out;
        }
        
        @keyframes messageSlide {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .message.user {
            justify-content: flex-end;
        }
        
        .message-bubble {
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 18px;
            word-wrap: break-word;
            white-space: pre-wrap;
        }
        
        .message.system .message-bubble {
            background: var(--vscode-badge-background);
            color: var(--vscode-badge-foreground);
            border-bottom-left-radius: 6px;
        }
        
        .message.user .message-bubble {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border-bottom-right-radius: 6px;
        }
        
        .message.system.plain {
            justify-content: center;
            margin: 8px 0;
        }
        
        .message.system.plain .message-content {
            background: none;
            padding: 8px 16px;
            border-radius: 0;
            font-size: 13px;
            opacity: 0.8;
            font-style: italic;
            text-align: center;
            border: none;
            color: var(--vscode-foreground);
        }
        
        /* Speech error message styling */
        .message.system.plain .message-content[data-speech-error] {
            background: rgba(255, 107, 53, 0.1);
            border: 1px solid rgba(255, 107, 53, 0.3);
            color: var(--vscode-errorForeground);
            font-weight: 500;
            opacity: 1;
            padding: 12px 16px;
            border-radius: 8px;
        }
        
        .message-time {
            font-size: 11px;
            opacity: 0.6;
            margin-top: 4px;
        }
        
        .input-container {
            flex-shrink: 0;
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 16px 20px 20px 20px;
            border-top: 1px solid var(--vscode-panel-border);
            background: var(--vscode-editor-background);
        }
        
        .input-container.disabled {
            opacity: 0.5;
            pointer-events: none;
        }
        
        .input-wrapper {
            flex: 1;
            display: flex;
            align-items: center;
            background: var(--vscode-input-background);
            border: 1px solid var(--vscode-input-border);
            border-radius: 20px;
            padding: 8px 12px;
            transition: all 0.2s ease;
            position: relative;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .input-wrapper:focus-within {
            border-color: transparent;
            box-shadow: 0 0 0 2px rgba(255, 165, 0, 0.4), 0 0 8px rgba(255, 165, 0, 0.2);
        }
        
        .message-input {
            flex: 1;
            background: transparent;
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
            color: var(--vscode-input-foreground);
            resize: none;
            min-height: 20px;
            max-height: 120px;
            font-family: inherit;
            font-size: 14px;
            line-height: 1.4;
            padding-left: 24px; /* Make room for mic icon */
        }
        
        .message-input:focus {
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
        }
        
        .message-input:focus-visible {
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
        }
        
        .message-input::placeholder {
            color: var(--vscode-input-placeholderForeground);
        }
        
        .message-input:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .message-input.paste-highlight {
            box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.4) !important;
            transition: box-shadow 0.2s ease;
        }

        .button-icon {
            position: relative;
            color: inherit;
        }

        .button-icon::before {
            content: '';
            display: block;
            width: var(--icon-size, 16px);
            height: var(--icon-size, 16px);
            background-color: currentColor;
            mask-repeat: no-repeat;
            mask-position: center;
            mask-size: contain;
            -webkit-mask-repeat: no-repeat;
            -webkit-mask-position: center;
            -webkit-mask-size: contain;
        }

        .icon-microphone::before {
            mask-image: url('${WEBVIEW_ICON_URIS.microphone}');
            -webkit-mask-image: url('${WEBVIEW_ICON_URIS.microphone}');
        }

        .icon-stop::before {
            mask-image: url('${WEBVIEW_ICON_URIS.stop}');
            -webkit-mask-image: url('${WEBVIEW_ICON_URIS.stop}');
        }

        .icon-spinner::before {
            mask-image: url('${WEBVIEW_ICON_URIS.spinner}');
            -webkit-mask-image: url('${WEBVIEW_ICON_URIS.spinner}');
        }

        .icon-image::before {
            mask-image: url('${WEBVIEW_ICON_URIS.image}');
            -webkit-mask-image: url('${WEBVIEW_ICON_URIS.image}');
        }

        .icon-send::before {
            mask-image: url('${WEBVIEW_ICON_URIS.send}');
            -webkit-mask-image: url('${WEBVIEW_ICON_URIS.send}');
        }

        .icon-close::before {
            mask-image: url('${WEBVIEW_ICON_URIS.close}');
            -webkit-mask-image: url('${WEBVIEW_ICON_URIS.close}');
        }
        
        .attach-button {
            background: none;
            border: none;
            color: var(--vscode-foreground);
            cursor: pointer;
            font-size: 14px;
            padding: 4px;
            border-radius: 50%;
            width: 28px;
            height: 28px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
        }

        .attach-button::before {
            margin: 0 auto;
        }

        .attach-button:hover {
            background: var(--vscode-button-hoverBackground);
            transform: scale(1.1);
        }
        
        .attach-button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        .send-button {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            border-radius: 50%;
            width: 36px;
            height: 36px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
            font-size: 14px;
        }

        .send-button::before {
            margin: 0 auto;
        }
        
        .send-button:hover {
            background: var(--vscode-button-hoverBackground);
            transform: scale(1.05);
        }
        
        .send-button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        .typing-indicator {
            display: none;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            font-size: 12px;
            opacity: 0.7;
        }
        
        .typing-dots {
            display: flex;
            gap: 2px;
        }
        
        .typing-dot {
            width: 4px;
            height: 4px;
            background: var(--vscode-foreground);
            border-radius: 50%;
            animation: typingDot 1.4s infinite ease-in-out;
        }
        
        .typing-dot:nth-child(1) { animation-delay: -0.32s; }
        .typing-dot:nth-child(2) { animation-delay: -0.16s; }
        
        @keyframes typingDot {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }
        
        .mcp-status {
            font-size: 11px;
            opacity: 0.6;
            margin-left: 4px;
        }
        
        /* Drag and drop styling */
        body.drag-over {
            background: rgba(0, 123, 255, 0.05);
        }
        
        body.drag-over::before {
            content: 'Drop images here to attach them';
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: var(--vscode-badge-background);
            color: var(--vscode-badge-foreground);
            padding: 16px 24px 16px 48px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            z-index: 1000;
            pointer-events: none;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            font-family: var(--vscode-font-family);
        }
        
        body.drag-over::after {
            content: '';
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) translate(-120px, 0);
            width: 18px;
            height: 18px;
            background-color: var(--vscode-badge-foreground);
            z-index: 1001;
            pointer-events: none;
            mask-image: url('${WEBVIEW_ICON_URIS.drop}');
            mask-repeat: no-repeat;
            mask-position: center;
            mask-size: contain;
            -webkit-mask-image: url('${WEBVIEW_ICON_URIS.drop}');
            -webkit-mask-repeat: no-repeat;
            -webkit-mask-position: center;
            -webkit-mask-size: contain;
        }
        
        /* Image preview styling */
        .image-preview {
            position: relative;
        }
        
        .image-container {
            position: relative;
        }
        
        .image-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        
        .image-filename {
            font-size: 12px;
            font-weight: 500;
            opacity: 0.9;
            flex: 1;
            margin-right: 8px;
            word-break: break-all;
        }
        
        .remove-image-btn {
            background: rgba(255, 59, 48, 0.1);
            border: 1px solid rgba(255, 59, 48, 0.3);
            color: #ff3b30;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            transition: all 0.2s ease;
            flex-shrink: 0;
            --icon-size: 10px;
        }

        .remove-image-btn::before {
            margin: 0 auto;
        }
        
        .remove-image-btn:hover {
            background: rgba(255, 59, 48, 0.2);
            border-color: rgba(255, 59, 48, 0.5);
            transform: scale(1.1);
        }
        
        .remove-image-btn:active {
            transform: scale(0.95);
        }

        .image-preview-image {
            display: block;
            max-width: 200px;
            max-height: 200px;
            border-radius: 8px;
            margin-top: 8px;
        }

        .image-meta {
            margin-top: 8px;
            font-size: 12px;
            opacity: 0.7;
        }

        .mic-icon,
        .attach-button,
        .send-button,
        .remove-image-btn {
            appearance: none;
            -webkit-appearance: none;
        }

        .mic-icon {
            position: absolute;
            left: 12px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--vscode-input-placeholderForeground);
            pointer-events: none;
            opacity: 0.7;
            transition: all 0.2s ease;
            background: none;
            border: none;
            padding: 0;
            margin: 0;
            width: 18px;
            height: 18px;
            cursor: pointer;
        }

        .mic-icon.active {
            color: #ff6b35;
            pointer-events: auto;
        }

        .mic-icon.recording {
            color: #ff3333;
            animation: pulse 1.5s infinite;
        }

        .mic-icon.processing {
            color: #ff6b35;
        }

        .mic-icon.processing::before {
            animation: spin 1s linear infinite;
        }

        .mic-icon:focus-visible,
        .attach-button:focus-visible,
        .send-button:focus-visible,
        .remove-image-btn:focus-visible {
            outline: 1px solid var(--vscode-focusBorder);
            outline-offset: 2px;
        }
    </style>
</head>
<body>
    <div class="review-container">
        <div class="review-header">
            <div class="review-title" id="reviewTitle"></div>
            <div class="status-indicator" id="statusIndicator"></div>
            <div class="mcp-status" id="mcpStatus">Checking MCP...</div>
            <div class="review-author">by Lakshman Turlapati</div>
        </div>
        
        <div class="messages-container" id="messages">
            <!-- Messages will be added here -->
        </div>
        
        <div class="typing-indicator" id="typingIndicator">
            <span>Processing review</span>
            <div class="typing-dots">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
        
        <div class="input-container" id="inputContainer">
            <div class="input-wrapper">
                <button id="micIcon" class="mic-icon button-icon icon-microphone active" type="button"></button>
                <textarea id="messageInput" class="message-input" placeholder="" rows="1"></textarea>
                <button id="attachButton" class="attach-button button-icon icon-image" type="button"></button>
            </div>
            <button id="sendButton" class="send-button button-icon icon-send" type="button"></button>
        </div>
    </div>

    <script nonce="${nonce}">
        const popupConfig = ${popupConfig};
        const vscode = acquireVsCodeApi();
        
        const reviewTitle = document.getElementById('reviewTitle');
        const messagesContainer = document.getElementById('messages');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const attachButton = document.getElementById('attachButton');
        const micIcon = document.getElementById('micIcon');
        const typingIndicator = document.getElementById('typingIndicator');
        const statusIndicator = document.getElementById('statusIndicator');
        const mcpStatus = document.getElementById('mcpStatus');
        const inputContainer = document.getElementById('inputContainer');
        
        let messageCount = 0;
        let mcpActive = true; // Default to true for better UX
        let mcpIntegration = Boolean(popupConfig.mcpIntegration);
        let attachedImages = []; // Store uploaded images
        let isRecording = false;
        let mediaRecorder = null;

        function setElementLabel(element, text) {
            element.title = text;
            element.setAttribute('aria-label', text);
        }

        function setInputPlaceholder(overrideText = null) {
            if (typeof overrideText === 'string') {
                messageInput.placeholder = overrideText;
                return;
            }

            if (!mcpActive) {
                messageInput.placeholder = popupConfig.placeholders.inactive;
                return;
            }

            const baseText = mcpIntegration
                ? popupConfig.placeholders.mcpBase
                : popupConfig.placeholders.defaultBase;
            messageInput.placeholder = attachedImages.length > 0
                ? baseText + '... ' + attachedImages.length + ' image(s) attached'
                : baseText + '...';
        }

        function setMicIconState(iconName, stateClass = '', titleText = popupConfig.titles.mic) {
            let className = 'mic-icon button-icon active icon-' + iconName;
            if (stateClass) {
                className += ' ' + stateClass;
            }

            micIcon.className = className;
            setElementLabel(micIcon, titleText);
        }

        function createElement(tagName, className = '', text = null) {
            const element = document.createElement(tagName);
            if (className) {
                element.className = className;
            }
            if (text !== null) {
                element.textContent = text;
            }
            return element;
        }

        function isSafeImageDataUrl(dataUrl) {
            return typeof dataUrl === 'string' && /^data:image\\/[a-z0-9.+-]+;base64,/i.test(dataUrl);
        }

        function formatImageSize(size) {
            const numericSize = Number(size);
            if (!Number.isFinite(numericSize) || numericSize < 0) {
                return '0.0';
            }

            return (numericSize / 1024).toFixed(1);
        }

        function createImagePreviewNode(imageData, imageId) {
            const imagePreview = createElement('div', 'message system image-preview');
            imagePreview.setAttribute('data-image-id', imageId);

            const imageContainer = createElement('div', 'message-bubble image-container');
            const imageHeader = createElement('div', 'image-header');
            const imageFileName = createElement('span', 'image-filename', String(imageData.fileName || 'uploaded-image'));
            const removeButton = createElement('button', 'remove-image-btn button-icon icon-close');
            removeButton.type = 'button';
            setElementLabel(removeButton, popupConfig.titles.removeImage);
            removeButton.addEventListener('click', () => {
                removeImage(imageId);
            });

            const previewImage = document.createElement('img');
            previewImage.className = 'image-preview-image';
            previewImage.alt = imageData.fileName
                ? 'Uploaded image: ' + imageData.fileName
                : 'Uploaded image';
            previewImage.src = imageData.dataUrl;

            const imageMeta = createElement(
                'div',
                'image-meta',
                'Image ready to send (' + formatImageSize(imageData.size) + ' KB)'
            );
            const timeDiv = createElement('div', 'message-time', new Date().toLocaleTimeString());

            imageHeader.appendChild(imageFileName);
            imageHeader.appendChild(removeButton);
            imageContainer.appendChild(imageHeader);
            imageContainer.appendChild(previewImage);
            imageContainer.appendChild(imageMeta);
            imagePreview.appendChild(imageContainer);
            imagePreview.appendChild(timeDiv);

            return imagePreview;
        }

        document.title = popupConfig.title;
        reviewTitle.textContent = popupConfig.title;
        setElementLabel(attachButton, popupConfig.titles.attach);
        setElementLabel(sendButton, popupConfig.titles.send);
        setMicIconState('microphone', '', popupConfig.titles.micReady);
        setInputPlaceholder();
        
        function updateMcpStatus(active) {
            mcpActive = active;
            
            if (active) {
                statusIndicator.classList.add('active');
                mcpStatus.textContent = 'MCP Active';
                inputContainer.classList.remove('disabled');
                messageInput.disabled = false;
                sendButton.disabled = false;
                attachButton.disabled = false;
                micIcon.disabled = false;
                setInputPlaceholder();
            } else {
                statusIndicator.classList.remove('active');
                mcpStatus.textContent = 'MCP Inactive';
                inputContainer.classList.add('disabled');
                messageInput.disabled = true;
                sendButton.disabled = true;
                attachButton.disabled = true;
                micIcon.disabled = true;
                setInputPlaceholder();
            }
        }
        
        function addMessage(text, type = 'user', toolData = null, plain = false, isError = false) {
            messageCount++;
            const messageDiv = document.createElement('div');
            messageDiv.className = \`message \${type}\${plain ? ' plain' : ''}\`;
            
            const contentDiv = document.createElement('div');
            contentDiv.className = plain ? 'message-content' : 'message-bubble';
            contentDiv.textContent = text;
            
            // Add special styling for speech errors
            if (isError && plain) {
                contentDiv.setAttribute('data-speech-error', 'true');
            }
            
            messageDiv.appendChild(contentDiv);
            
            // Only add timestamp for non-plain messages
            if (!plain) {
                const timeDiv = document.createElement('div');
                timeDiv.className = 'message-time';
                timeDiv.textContent = new Date().toLocaleTimeString();
                messageDiv.appendChild(timeDiv);
            }
            
            messagesContainer.appendChild(messageDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
        
        function addSpeechError(errorMessage) {
            // Add prominent error message with special styling
            addMessage('🎤 Speech Error: ' + errorMessage, 'system', null, true, true);
            
            // Add helpful troubleshooting tips based on error type
            let tip = '';
            if (errorMessage.includes('permission') || errorMessage.includes('Permission')) {
                tip = '💡 Grant microphone access in system settings';
            } else if (errorMessage.includes('busy') || errorMessage.includes('device')) {
                tip = '💡 Close other recording apps and try again';
            } else if (errorMessage.includes('SoX') || errorMessage.includes('sox')) {
                tip = '💡 SoX audio tool may need to be installed or updated';
            } else if (errorMessage.includes('timeout')) {
                tip = '💡 Try speaking more clearly or check microphone connection';
            } else if (errorMessage.includes('Whisper') || errorMessage.includes('transcription')) {
                tip = '💡 Speech-to-text service may be unavailable';
            } else {
                tip = '💡 Check microphone permissions and try again';
            }
            
            if (tip) {
                setTimeout(() => {
                    addMessage(tip, 'system', null, true);
                }, 500);
            }
        }
        
        function showTyping() {
            typingIndicator.style.display = 'flex';
        }
        
        function hideTyping() {
            typingIndicator.style.display = 'none';
        }
        
        function simulateResponse(userMessage) {
            // Don't simulate response - the backend handles acknowledgments now
            // This avoids duplicate messages
            hideTyping();
        }
        
        function sendMessage() {
            const text = messageInput.value.trim();
            if (!text && attachedImages.length === 0) return;
            
            // Create message with text and images
            let displayMessage = text;
            if (attachedImages.length > 0) {
                displayMessage += (text ? '\\n\\n' : '') + \`[\${attachedImages.length} image(s) attached]\`;
            }
            
            addMessage(displayMessage, 'user');
            
            // Send to extension with images
            vscode.postMessage({
                command: 'send',
                text: text,
                attachments: attachedImages,
                timestamp: new Date().toISOString(),
                mcpIntegration: mcpIntegration
            });
            
            messageInput.value = '';
            attachedImages = []; // Clear attached images
            updateImageCounter();
            adjustTextareaHeight();
            
            // Ensure mic icon is visible after sending message
            toggleMicIcon();
            
            simulateResponse(displayMessage);
        }
        
        function adjustTextareaHeight() {
            messageInput.style.height = 'auto';
            messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + 'px';
        }
        
        function handleImageUploaded(imageData) {
            if (!imageData || !isSafeImageDataUrl(imageData.dataUrl)) {
                addMessage('❌ Invalid image data received', 'system', null, true);
                return;
            }

            const imageId = 'img_' + Date.now() + '_' + Math.random().toString(36).slice(2, 11);
            const imageRecord = Object.assign({}, imageData, { id: imageId });
            attachedImages.push(imageRecord);

            const imagePreview = createImagePreviewNode(imageRecord, imageId);
            messagesContainer.appendChild(imagePreview);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            
            updateImageCounter();
        }
        
        // Remove image function
        function removeImage(imageId) {
            // Remove from attachments array
            attachedImages = attachedImages.filter(img => img.id !== imageId);
            
            // Remove from DOM
            const imagePreview = document.querySelector(\`[data-image-id="\${imageId}"]\`);
            if (imagePreview) {
                imagePreview.remove();
            }
            
            updateImageCounter();
            
            // Log removal
            console.log('🗑️ Image removed from attachment list');
            vscode.postMessage({
                command: 'logImageRemoved',
                imageId: imageId
            });
        }
        
        // Update image counter in input placeholder
        function updateImageCounter() {
            setInputPlaceholder();
        }
        
        // Handle paste events for images with debounce to prevent duplicates
        let lastPasteTime = 0;
        function handlePaste(e) {
            const now = Date.now();
            // Prevent duplicate pastes within 500ms
            if (now - lastPasteTime < 500) {
                return;
            }
            
            const clipboardData = e.clipboardData || window.clipboardData;
            if (!clipboardData) return;
            
            const items = clipboardData.items;
            if (!items) return;
            
            // Look for image items in clipboard
            for (let i = 0; i < items.length; i++) {
                const item = items[i];
                
                if (item.type.indexOf('image') !== -1) {
                    e.preventDefault(); // Prevent default paste behavior for images
                    lastPasteTime = now; // Update last paste time
                    
                    const file = item.getAsFile();
                    if (file) {
                        processPastedImage(file);
                    }
                    break;
                }
            }
        }
        
        // Process pasted image file
        function processPastedImage(file) {
            const reader = new FileReader();
            
            reader.onload = function(e) {
                const dataUrl = e.target.result;
                const base64Data = dataUrl.split(',')[1];
                
                // Generate a filename with timestamp
                const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
                const extension = file.type.split('/')[1] || 'png';
                const fileName = \`pasted-image-\${timestamp}.\${extension}\`;
                
                const imageData = {
                    fileName: fileName,
                    filePath: 'clipboard', // Indicate this came from clipboard
                    mimeType: file.type,
                    base64Data: base64Data,
                    dataUrl: dataUrl,
                    size: file.size,
                    source: 'paste' // Mark as pasted image
                };
                
                console.log('📋 Image pasted into attachment list');
                
                // Log the pasted image for MCP integration
                vscode.postMessage({
                    command: 'logPastedImage',
                    fileName: fileName,
                    size: file.size,
                    mimeType: file.type
                });
                
                // Add to attachments and show preview
                handleImageUploaded(imageData);
            };
            
            reader.onerror = function() {
                console.error('Error reading pasted image');
                addMessage('❌ Error processing pasted image', 'system', null, true);
            };
            
            reader.readAsDataURL(file);
        }
        
        // Drag and drop handlers
        let dragCounter = 0;
        
        function handleDragEnter(e) {
            e.preventDefault();
            dragCounter++;
            if (hasImageFiles(e.dataTransfer)) {
                document.body.classList.add('drag-over');
                messageInput.classList.add('paste-highlight');
            }
        }
        
        function handleDragLeave(e) {
            e.preventDefault();
            dragCounter--;
            if (dragCounter <= 0) {
                document.body.classList.remove('drag-over');
                messageInput.classList.remove('paste-highlight');
                dragCounter = 0;
            }
        }
        
        function handleDragOver(e) {
            e.preventDefault();
            if (hasImageFiles(e.dataTransfer)) {
                e.dataTransfer.dropEffect = 'copy';
            }
        }
        
        function handleDrop(e) {
            e.preventDefault();
            dragCounter = 0;
            document.body.classList.remove('drag-over');
            messageInput.classList.remove('paste-highlight');
            
            const files = e.dataTransfer.files;
            if (files && files.length > 0) {
                // Process files with a small delay to prevent conflicts with paste events
                setTimeout(() => {
                    for (let i = 0; i < files.length; i++) {
                        const file = files[i];
                        if (file.type.startsWith('image/')) {
                            // Log drag and drop action
                            vscode.postMessage({
                                command: 'logDragDropImage',
                                fileName: file.name,
                                size: file.size,
                                mimeType: file.type
                            });
                            processPastedImage(file);
                        }
                    }
                }, 50);
            }
        }
        
        function hasImageFiles(dataTransfer) {
            if (dataTransfer.types) {
                for (let i = 0; i < dataTransfer.types.length; i++) {
                    if (dataTransfer.types[i] === 'Files') {
                        return true; // We'll check for images on drop
                    }
                }
            }
            return false;
        }
        
        // Hide/show mic icon based on input
        function toggleMicIcon() {
            // Don't toggle if we're currently recording or processing
            if (isRecording || micIcon.classList.contains('processing')) {
                return;
            }
            
            if (messageInput.value.trim().length > 0) {
                micIcon.style.opacity = '0';
                micIcon.style.pointerEvents = 'none';
            } else {
                // Always ensure mic is visible and clickable when input is empty
                micIcon.style.opacity = '0.7';
                micIcon.style.pointerEvents = 'auto';
                // Ensure proper mic icon state
                if (!micIcon.classList.contains('icon-microphone')) {
                    setMicIconState('microphone', '', popupConfig.titles.mic);
                }
            }
        }
        
        // Check if speech recording is available
        function isSpeechAvailable() {
            return (
                navigator.mediaDevices && 
                navigator.mediaDevices.getUserMedia && 
                typeof MediaRecorder !== 'undefined'
            );
        }
        
        // Speech recording functions - using Node.js backend
        function startRecording() {
            // Start recording via extension backend
            vscode.postMessage({
                command: 'startRecording',
                timestamp: new Date().toISOString()
            });
            
            isRecording = true;
            // Change icon to stop icon and add recording state
            setMicIconState('stop', 'recording', popupConfig.titles.recording);
            console.log('🎤 Recording started - UI updated to stop icon');
        }
        
        function stopRecording() {
            // Stop recording via extension backend
            vscode.postMessage({
                command: 'stopRecording',
                timestamp: new Date().toISOString()
            });
            
            isRecording = false;
            // Change to processing state
            setMicIconState('spinner', 'processing', popupConfig.titles.processing);
            setInputPlaceholder(popupConfig.placeholders.processing);
            console.log('🔄 Recording stopped - processing speech...');
        }
        
        function resetMicIcon() {
            // Reset to normal microphone state
            isRecording = false; // Ensure recording flag is cleared
            setMicIconState('microphone', '', popupConfig.titles.mic);
            setInputPlaceholder();
            
            // Force visibility based on input state
            if (messageInput.value.trim().length === 0) {
                micIcon.style.opacity = '0.7';
                micIcon.style.pointerEvents = 'auto';
            } else {
                micIcon.style.opacity = '0';
                micIcon.style.pointerEvents = 'none';
            }
            
            console.log('🎤 Mic icon reset to normal state');
        }
        
        // Event listeners
        messageInput.addEventListener('input', () => {
            adjustTextareaHeight();
            toggleMicIcon();
        });
        
        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        // Add paste event listener for images
        messageInput.addEventListener('paste', handlePaste);
        document.addEventListener('paste', handlePaste);
        
        // Add drag and drop support for images
        document.addEventListener('dragover', handleDragOver);
        document.addEventListener('drop', handleDrop);
        document.addEventListener('dragenter', handleDragEnter);
        document.addEventListener('dragleave', handleDragLeave);
        
        sendButton.addEventListener('click', () => {
            sendMessage();
        });
        
        attachButton.addEventListener('click', () => {
            vscode.postMessage({ command: 'uploadImage' });
        });
        
        micIcon.addEventListener('click', () => {
            if (isRecording) {
                stopRecording();
            } else {
                startRecording();
            }
        });
        
        // Handle messages from extension
        window.addEventListener('message', event => {
            const message = event.data;
            
            switch (message.command) {
                case 'addMessage':
                    addMessage(message.text, message.type || 'system', message.toolData, message.plain || false);
                    break;
                case 'newMessage':
                    addMessage(message.text, message.type || 'system', message.toolData, message.plain || false);
                    if (message.mcpIntegration) {
                        mcpIntegration = true;
                        setInputPlaceholder();
                    }
                    break;
                case 'focus':
                    messageInput.focus();
                    break;
                case 'updateMcpStatus':
                    updateMcpStatus(message.active);
                    break;
                case 'imageUploaded':
                    handleImageUploaded(message.imageData);
                    break;
                case 'recordingStarted':
                    console.log('✅ Recording confirmation received from backend');
                    break;
                case 'speechTranscribed':
                    // Handle speech-to-text result
                    console.log('📝 Speech transcription received for active session');
                    if (message.transcription && message.transcription.trim()) {
                        messageInput.value = message.transcription.trim();
                        adjustTextareaHeight();
                        messageInput.focus();
                        console.log('✅ Text injected into the input');
                        // Reset mic icon after successful transcription
                        resetMicIcon();
                        toggleMicIcon();
                    } else if (message.error) {
                        console.error('❌ Speech transcription error:', message.error);
                        
                        // Show prominent error message in chat
                        addSpeechError(message.error);
                        
                        // Also show in placeholder briefly
                        setInputPlaceholder(popupConfig.placeholders.speechFailed);
                        setTimeout(() => {
                            resetMicIcon();
                        }, 3000);
                    } else {
                        console.log('⚠️ Empty transcription received');
                        
                        // Show helpful message in chat
                        addMessage('🎤 No speech detected - please speak clearly and try again', 'system', null, true);
                        
                        setInputPlaceholder(popupConfig.placeholders.noSpeech);
                        setTimeout(() => {
                            resetMicIcon();
                        }, 3000);
                    }
                    break;
            }
        });
        
        // Initialize speech availability - now using SoX directly
        function initializeSpeech() {
            // Always available since we're using SoX directly
            micIcon.style.opacity = '0.7';
            micIcon.style.pointerEvents = 'auto';
            setMicIconState('microphone', '', popupConfig.titles.micReady);
            console.log('Speech recording available via SoX direct recording');
            
            // Ensure mic icon visibility on initialization
            if (messageInput.value.trim().length === 0) {
                micIcon.style.opacity = '0.7';
                micIcon.style.pointerEvents = 'auto';
            }
        }
        
        // Initialize
        vscode.postMessage({ command: 'ready' });
        initializeSpeech();
        
        // Focus input immediately
        setTimeout(() => {
            messageInput.focus();
        }, 100);
    </script>
</body>
</html>`;
}

function handleReviewMessage(text, attachments, triggerId, mcpIntegration, specialHandling) {
    // Funny response templates - randomly rotated
    const funnyResponses = [
        "Review sent - Hold on to your pants until the review gate is called again! 🎢",
        "Message delivered! Agent is probably doing agent things now... ⚡",
        "Your wisdom has been transmitted to the digital overlords! 🤖",
        "Response launched into the void - expect agent magic soon! ✨",
        "Review gate closed - Agent is chewing on your input! 🍕",
        "Message received and filed under 'Probably Important'! 📁",
        "Your input is now part of the agent's master plan! 🧠",
        "Review sent - The agent owes you one! 🤝",
        "Success! Your thoughts are now haunting the agent's dreams! 👻",
        "Delivered faster than pizza on a Friday night! 🍕"
    ];
    
    // Silent message processing
    
    // Handle special cases for different tool types
    if (specialHandling === 'shutdown_mcp') {
        if (text.toUpperCase().includes('CONFIRM') || text.toUpperCase() === 'YES') {
            logUserInput('', 'SHUTDOWN_CONFIRMED', triggerId, attachments, {
                charCount: typeof text === 'string' ? text.length : 0
            });
            
            // Send confirmation response
            if (chatPanel) {
                setTimeout(() => {
                    chatPanel.webview.postMessage({
                        command: 'addMessage',
                        text: `🛑 Shutdown approved: "${text}"\n\nMCP server shutdown has been approved by user.\n\nCursor Agent will proceed with graceful shutdown.`,
                        type: 'system'
                    });
                    
                    // Set MCP status to inactive after shutdown confirmation
                    setTimeout(() => {
                        if (chatPanel) {
                            chatPanel.webview.postMessage({
                                command: 'updateMcpStatus',
                                active: activeMcpSession ? true : false
                            });
                        }
                    }, 1000);
                }, 500);
            }
        } else {
            logUserInput('', 'SHUTDOWN_ALTERNATIVE', triggerId, attachments, {
                charCount: typeof text === 'string' ? text.length : 0
            });
            
            // Send alternative instructions response
            if (chatPanel) {
                setTimeout(() => {
                    chatPanel.webview.postMessage({
                        command: 'addMessage',
                        text: `💡 Alternate instructions received: "${text}"\n\nYour instructions have been sent to the Cursor Agent instead of shutdown confirmation.\n\nThe Agent will process your alternative request.`,
                        type: 'system'
                    });
                    
                    // Set MCP status to inactive after alternative instructions
                    setTimeout(() => {
                        if (chatPanel) {
                            chatPanel.webview.postMessage({
                                command: 'updateMcpStatus',
                                active: activeMcpSession ? true : false
                            });
                        }
                    }, 1000);
                }, 500);
            }
        }
    } else if (specialHandling === 'ingest_text') {
        logUserInput('', 'TEXT_FEEDBACK', triggerId, attachments, {
            charCount: typeof text === 'string' ? text.length : 0
        });
        
        // Send text feedback response
        if (chatPanel) {
            setTimeout(() => {
                chatPanel.webview.postMessage({
                    command: 'addMessage',
                    text: `🔄 Text input processed: "${text}"\n\nYour feedback on the ingested text has been sent to the Cursor Agent.\n\nThe Agent will continue processing with your input.`,
                    type: 'system'
                });
                
                // Set MCP status to inactive after text feedback
                setTimeout(() => {
                    if (chatPanel) {
                        chatPanel.webview.postMessage({
                            command: 'updateMcpStatus',
                            active: activeMcpSession ? true : false
                        });
                    }
                }, 1000);
            }, 500);
        }
    } else {
        // Send standard response back to webview
        if (chatPanel) {
            setTimeout(() => {
                // Pick a random funny response
                const randomResponse = funnyResponses[Math.floor(Math.random() * funnyResponses.length)];
                
                chatPanel.webview.postMessage({
                    command: 'addMessage',
                    text: randomResponse,
                    type: 'system',
                    plain: true  // Use plain styling for acknowledgments
                });
                
                // Set MCP status to inactive after sending response
                setTimeout(() => {
                    if (chatPanel) {
                        chatPanel.webview.postMessage({
                            command: 'updateMcpStatus',
                            active: activeMcpSession ? true : false
                        });
                    }
                }, 1000);
                
            }, 500);
        }
    }
}

function handleFileAttachment(triggerId) {
    logUserInput('User requested file attachment for review', 'FILE_ATTACHMENT', triggerId);
    
    vscode.window.showOpenDialog({
        canSelectMany: true,
        openLabel: 'Select file(s) for review',
        filters: {
            'All files': ['*']
        }
    }).then(fileUris => {
        if (fileUris && fileUris.length > 0) {
            const filePaths = fileUris.map(uri => uri.fsPath);
            const fileNames = filePaths.map(fp => path.basename(fp));
            
            logUserInput('', 'FILE_SELECTED', triggerId, [], { fileCount: fileNames.length });
            
            if (chatPanel) {
                chatPanel.webview.postMessage({
                    command: 'addMessage',
                    text: `Files attached for review:\n${fileNames.map(name => '• ' + name).join('\n')}\n\nPaths:\n${filePaths.map(fp => '• ' + fp).join('\n')}`,
                    type: 'system'
                });
            }
        } else {
            logUserInput('No files selected for review', 'FILE_CANCELLED', triggerId);
        }
    });
}

function handleImageUpload(triggerId) {
    logUserInput('User requested image upload for review', 'IMAGE_UPLOAD', triggerId);
    
    vscode.window.showOpenDialog({
        canSelectMany: true,
        openLabel: 'Select image(s) to upload',
        filters: {
            'Images': ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']
        }
    }).then(fileUris => {
        if (fileUris && fileUris.length > 0) {
            fileUris.forEach(fileUri => {
                const filePath = fileUri.fsPath;
                const fileName = path.basename(filePath);
                
                
                try {
                    // Read the image file
                    const imageBuffer = fs.readFileSync(filePath);
                    const base64Data = imageBuffer.toString('base64');
                    const mimeType = getMimeType(fileName);
                    const dataUrl = `data:${mimeType};base64,${base64Data}`;
                    
                    const imageData = {
                        fileName: fileName,
                        filePath: filePath,
                        mimeType: mimeType,
                        base64Data: base64Data,
                        dataUrl: dataUrl,
                        size: imageBuffer.length
                    };
                    
                    logUserInput('', 'IMAGE_UPLOADED', triggerId, [], { imageCount: 1 });
                    
                    // Send image data to webview
                    if (chatPanel) {
                        chatPanel.webview.postMessage({
                            command: 'imageUploaded',
                            imageData: imageData
                        });
                    }
                    
                } catch (error) {
                    console.log(`Error processing selected image: ${error.message}`);
                    vscode.window.showErrorMessage(`Failed to process image: ${fileName}`);
                }
            });
        } else {
            logUserInput('No images selected for upload', 'IMAGE_CANCELLED', triggerId);
        }
    });
}

function getMimeType(fileName) {
    const ext = path.extname(fileName).toLowerCase();
    const mimeTypes = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.webp': 'image/webp'
    };
    return mimeTypes[ext] || 'image/jpeg';
}

async function handleSpeechToText(audioData, triggerId, isFilePath = false) {
    const sessionTriggerId = resolveSpeechTriggerId(triggerId);

    try {
        if (!sessionTriggerId) {
            return;
        }

        const sessionContract = getSessionContract(sessionTriggerId);
        if (!sessionContract) {
            logMessage(`Rejected speech request without an active MCP session contract for ${sessionTriggerId}`);
            cleanupSessionSpeechArtifacts(sessionTriggerId, 'Rejected unauthenticated speech request', {
                removeAudioFiles: true
            });
            if (chatPanel) {
                chatPanel.webview.postMessage({
                    command: 'speechTranscribed',
                    transcription: '',
                    error: 'Speech transcription is only available for the active Review Gate session'
                });
            }
            return;
        }

        if (activeMcpSession && activeMcpSession.triggerId !== sessionTriggerId) {
            logMessage(`Ignoring speech request for stale trigger=${sessionTriggerId}`);
            if (isFilePath && audioData && fs.existsSync(audioData)) {
                fs.unlinkSync(audioData);
            }
            cleanupSessionSpeechArtifacts(sessionTriggerId, 'Ignored stale speech request', {
                removeAudioFiles: true
            });
            return;
        }

        cleanupSessionSpeechArtifacts(sessionTriggerId, 'Preparing speech transcription');

        let tempAudioPath;
        
        if (isFilePath) {
            tempAudioPath = audioData;
            logMessage(`Using existing audio file for transcription file=${path.basename(tempAudioPath)}`);
        } else {
            const base64Data = audioData.split(',')[1];
            const audioBuffer = Buffer.from(base64Data, 'base64');
            tempAudioPath = getSessionAudioPath(sessionTriggerId, Date.now());
            fs.writeFileSync(tempAudioPath, audioBuffer);
            logMessage(`Audio buffered for transcription file=${path.basename(tempAudioPath)}`);
        }
        
        const transcriptionRequest = {
            timestamp: new Date().toISOString(),
            system: "review-gate-v2",
            editor: "cursor",
            ...buildSessionEnvelope(sessionTriggerId, sessionContract),
            data: {
                tool: "speech_to_text",
                audio_file: tempAudioPath,
                trigger_id: sessionTriggerId,
                format: "wav"
            },
            mcp_integration: true
        };
        
        const triggerFile = getSessionFilePath('speechTrigger', sessionTriggerId);
        writeJsonAtomically(triggerFile, transcriptionRequest);
        
        logMessage(`Speech-to-text request sent trigger=${sessionTriggerId} file=${path.basename(triggerFile)}`);
        
        const maxWaitTime = 30000;
        const pollInterval = 500;
        let waitTime = 0;
        
        const pollForResult = setInterval(() => {
            const resultFile = getSessionFilePath('speechResponse', sessionTriggerId);

            if (!isSpeechSessionCurrent(sessionTriggerId)) {
                clearInterval(pollForResult);
                cleanupSessionSpeechArtifacts(sessionTriggerId, 'Ignored speech result for inactive session');
                return;
            }
            
            if (fs.existsSync(resultFile)) {
                try {
                    const result = validateSessionEnvelope(readJsonFileSafely(resultFile), {
                        expectedSource: 'review_gate_whisper',
                        expectedTriggerId: sessionTriggerId,
                        expectedSession: sessionContract
                    });
                    
                    if (result.transcription) {
                        if (chatPanel && isSpeechSessionCurrent(sessionTriggerId)) {
                            chatPanel.webview.postMessage({
                                command: 'speechTranscribed',
                                transcription: result.transcription
                            });
                        }
                        
                        logMessage(`Speech transcription received trigger=${sessionTriggerId} chars=${result.transcription.length}`);
                        logUserInput('', 'SPEECH_TRANSCRIBED', sessionTriggerId);
                    }
                    
                    removeSessionFile(resultFile, 'Cleaned up speech response file');
                    removeSessionFile(triggerFile, 'Cleaned up speech trigger file');
                } catch (error) {
                    logMessage(`Error reading transcription result: ${error.message}`);
                }
                
                clearInterval(pollForResult);
            }
            
            waitTime += pollInterval;
            if (waitTime >= maxWaitTime) {
                logMessage(`Speech-to-text timeout trigger=${sessionTriggerId}`);
                if (chatPanel && isSpeechSessionCurrent(sessionTriggerId)) {
                    chatPanel.webview.postMessage({
                        command: 'speechTranscribed',
                        transcription: ''
                    });
                }
                clearInterval(pollForResult);
                cleanupSessionSpeechArtifacts(sessionTriggerId, 'Speech transcription timeout');
            }
        }, pollInterval);
        
    } catch (error) {
        logMessage(`Speech-to-text error: ${error.message}`);
        cleanupSessionSpeechArtifacts(sessionTriggerId, 'Speech transcription error');
        if (chatPanel && (!sessionTriggerId || isSpeechSessionCurrent(sessionTriggerId))) {
            chatPanel.webview.postMessage({
                command: 'speechTranscribed',
                transcription: ''
            });
        }
    }
}

async function validateSoxSetup() {
    /**
     * Validate SoX installation and microphone access
     * Returns: {success: boolean, error: string}
     */
    return new Promise((resolve) => {
        try {
            // Test if sox command exists
            const testProcess = spawn('sox', ['--version'], { stdio: 'pipe' });
            
            let soxVersion = '';
            testProcess.stdout.on('data', (data) => {
                soxVersion += data.toString();
            });
            
            testProcess.on('close', (code) => {
                if (code !== 0) {
                    resolve({ success: false, error: 'SoX command not found or failed' });
                    return;
                }
                
                console.log(`✅ SoX found: ${soxVersion.trim()}`);
                
                // Test microphone access with a very short recording
                const testFile = path.join(getRuntimeRoot(), `review_gate_test_${Date.now()}.wav`);
                const micTestProcess = spawn('sox', ['-d', '-r', '16000', '-c', '1', testFile, 'trim', '0', '0.1'], { stdio: 'pipe' });
                
                let testError = '';
                micTestProcess.stderr.on('data', (data) => {
                    testError += data.toString();
                });
                
                micTestProcess.on('close', (testCode) => {
                    // Clean up test file
                    try {
                        if (fs.existsSync(testFile)) {
                            fs.unlinkSync(testFile);
                        }
                    } catch (e) {}
                    
                    if (testCode !== 0) {
                        let errorMsg = 'Microphone access failed';
                        if (testError.includes('Permission denied')) {
                            errorMsg = 'Microphone permission denied - please allow microphone access in system settings';
                        } else if (testError.includes('No such device')) {
                            errorMsg = 'No microphone device found';
                        } else if (testError.includes('Device or resource busy')) {
                            errorMsg = 'Microphone is busy - close other recording applications';
                        } else if (testError) {
                            errorMsg = `Microphone test failed: ${testError.substring(0, 100)}`;
                        }
                        resolve({ success: false, error: errorMsg });
                    } else {
                        console.log('✅ Microphone access test successful');
                        resolve({ success: true, error: null });
                    }
                });
                
                // Timeout for microphone test
                setTimeout(() => {
                    try {
                        micTestProcess.kill('SIGTERM');
                        resolve({ success: false, error: 'Microphone test timed out' });
                    } catch (e) {}
                }, 3000);
            });
            
            testProcess.on('error', (error) => {
                resolve({ success: false, error: `SoX not installed: ${error.message}` });
            });
            
            // Timeout for version check
            setTimeout(() => {
                try {
                    testProcess.kill('SIGTERM');
                    resolve({ success: false, error: 'SoX version check timed out' });
                } catch (e) {}
            }, 2000);
            
        } catch (error) {
            resolve({ success: false, error: `SoX validation error: ${error.message}` });
        }
    });
}

async function startNodeRecording(triggerId) {
    try {
        const sessionTriggerId = resolveSpeechTriggerId(triggerId);
        if (!sessionTriggerId) {
            return;
        }

        if (currentRecording) {
            console.log('Recording already in progress');
            // Send feedback to webview
            if (chatPanel) {
                chatPanel.webview.postMessage({
                    command: 'speechTranscribed',
                    transcription: '',
                    error: 'Recording already in progress'
                });
            }
            return;
        }

        if (activeMcpSession && activeMcpSession.triggerId !== sessionTriggerId) {
            console.log(`Ignoring recording start for stale trigger: ${sessionTriggerId}`);
            if (chatPanel) {
                chatPanel.webview.postMessage({
                    command: 'speechTranscribed',
                    transcription: '',
                    error: 'Recording is only available for the active Review Gate session'
                });
            }
            cleanupSessionSpeechArtifacts(sessionTriggerId, 'Ignored stale recording start', {
                removeAudioFiles: true
            });
            return;
        }

        cleanupSessionSpeechArtifacts(sessionTriggerId, 'Starting speech recording', {
            removeAudioFiles: true
        });
        
        // Validate SoX setup before recording
        logMessage(`Validating SoX and microphone access trigger=${sessionTriggerId}`);
        const validation = await validateSoxSetup();
        if (!validation.success) {
            logMessage(`SoX validation failed trigger=${sessionTriggerId}: ${validation.error}`);
            if (chatPanel) {
                chatPanel.webview.postMessage({
                    command: 'speechTranscribed',
                    transcription: '',
                    error: validation.error
                });
            }
            return;
        }
        logMessage(`SoX validation successful trigger=${sessionTriggerId}`);
        
        const timestamp = Date.now();
        const audioFile = getSessionAudioPath(sessionTriggerId, timestamp);
        
        logMessage(`Starting SoX recording trigger=${sessionTriggerId} file=${path.basename(audioFile)}`);
        
        // Use sox directly to record audio
        // sox -d -r 16000 -c 1 output.wav (let SoX auto-detect bit depth)
        const soxArgs = [
            '-d',           // Use default input device (microphone)
            '-r', '16000',  // Sample rate 16kHz
            '-c', '1',      // Mono (1 channel)
            audioFile       // Output file
        ];
        
        logMessage(`Launching sox process trigger=${sessionTriggerId} sample_rate=16000 channels=1`);
        
        // Spawn sox process
        const recordingProcess = spawn('sox', soxArgs);
        currentRecording = recordingProcess;
        
        // Store metadata
        recordingProcess.audioFile = audioFile;
        recordingProcess.triggerId = sessionTriggerId;
        recordingProcess.startTime = Date.now();
        recordingProcess.finalizeTimer = null;
        recordingProcess.forceKillTimer = null;
        
        // Handle sox process events
        recordingProcess.on('error', (error) => {
            logMessage(`SoX process error trigger=${sessionTriggerId}: ${error.message}`);
            if (chatPanel) {
                chatPanel.webview.postMessage({
                    command: 'speechTranscribed',
                    transcription: '',
                    error: `Recording failed: ${error.message}`
                });
            }
            cleanupSessionSpeechArtifacts(sessionTriggerId, 'Speech recording process error', {
                removeAudioFiles: true
            });
            if (currentRecording && currentRecording.pid === recordingProcess.pid) {
                currentRecording = null;
            }
        });
        
        recordingProcess.stderr.on('data', (data) => {
            logMessage(`SoX stderr trigger=${sessionTriggerId}: ${String(data).trim().slice(0, 120)}`);
        });
        
        logMessage(`SoX recording started trigger=${sessionTriggerId} pid=${recordingProcess.pid} file=${path.basename(audioFile)}`);
        
        // Send confirmation to webview that recording has started
        if (chatPanel) {
            chatPanel.webview.postMessage({
                command: 'recordingStarted',
                audioFile: audioFile
            });
        }
        
    } catch (error) {
        logMessage(`Failed to start SoX recording: ${error.message}`);
        if (chatPanel) {
            chatPanel.webview.postMessage({
                command: 'speechTranscribed',
                transcription: '',
                error: `Recording failed: ${error.message}`
            });
        }
        currentRecording = null;
    }
}

function stopNodeRecording(triggerId) {
    try {
        const sessionTriggerId = resolveSpeechTriggerId(triggerId);
        if (!currentRecording) {
            logMessage('No recording in progress');
            if (chatPanel) {
                chatPanel.webview.postMessage({
                    command: 'speechTranscribed',
                    transcription: '',
                    error: 'No recording in progress'
                });
            }
            return;
        }

        const recording = currentRecording;
        if (!sessionTriggerId || recording.triggerId !== sessionTriggerId || !isSpeechSessionCurrent(recording.triggerId)) {
            logMessage(`Discarding stale recording trigger=${recording.triggerId}`);
            cancelActiveRecording('Discarded stale recording', recording.triggerId);
            cleanupSessionSpeechArtifacts(recording.triggerId, 'Discarded stale recording cleanup', {
                removeAudioFiles: true
            });
            return;
        }
        
        currentRecording = null;
        const audioFile = recording.audioFile;
        const recordingPid = recording.pid;
        logMessage(`Stopping SoX recording trigger=${sessionTriggerId} pid=${recordingPid} file=${path.basename(audioFile)}`);
        
        // Stop the sox process by sending SIGTERM
        recording.kill('SIGTERM');
        
        // Wait for process to exit and file to be finalized
        recording.on('exit', (code, signal) => {
            logMessage(`SoX process exited trigger=${sessionTriggerId} code=${code} signal=${signal}`);
            if (recording.forceKillTimer) {
                clearTimeout(recording.forceKillTimer);
            }
            
            // Give a moment for file system to sync
            recording.finalizeTimer = setTimeout(() => {
                logMessage(`Checking finalized audio file trigger=${sessionTriggerId} file=${path.basename(audioFile)}`);

                if (!isSpeechSessionCurrent(sessionTriggerId)) {
                    logMessage(`Ignoring finalized recording for inactive session trigger=${sessionTriggerId}`);
                    cleanupSessionSpeechArtifacts(sessionTriggerId, 'Ignored stale recording result', {
                        removeAudioFiles: true
                    });
                    return;
                }
                
                if (fs.existsSync(audioFile)) {
                    const stats = fs.statSync(audioFile);
                    logMessage(`Audio file created trigger=${sessionTriggerId} file=${path.basename(audioFile)} bytes=${stats.size}`);
                    
                    // Check minimum file size (more generous for SoX)
                    if (stats.size > 500) {
                        logMessage(`Audio file ready for transcription trigger=${sessionTriggerId} file=${path.basename(audioFile)} bytes=${stats.size}`);
                        // Send to MCP server for transcription
                        handleSpeechToText(audioFile, sessionTriggerId, true);
                    } else {
                        logMessage(`Audio file too small for transcription trigger=${sessionTriggerId} file=${path.basename(audioFile)} bytes=${stats.size}`);
                        if (chatPanel) {
                            chatPanel.webview.postMessage({
                                command: 'speechTranscribed',
                                transcription: '',
                                error: 'No speech detected - try speaking louder or closer to microphone'
                            });
                        }
                        // Clean up small file
                        try {
                            fs.unlinkSync(audioFile);
                        } catch (e) {
                            logMessage(`Could not clean up small audio file: ${e.message}`);
                        }
                    }
                } else {
                    logMessage(`Audio file was not created trigger=${sessionTriggerId}`);
                    if (chatPanel) {
                        chatPanel.webview.postMessage({
                            command: 'speechTranscribed',
                            transcription: '',
                            error: 'Recording failed - no audio file created'
                        });
                    }
                }
            }, 1000); // Wait 1 second for file system sync
        });
        
        // Set a timeout in case the process doesn't exit gracefully
        recording.forceKillTimer = setTimeout(() => {
            if (recording.pid) {
                console.log(`⚠️ Force killing SoX process: ${recording.pid}`);
                try {
                    recording.kill('SIGKILL');
                } catch (e) {
                    console.log(`Could not force kill: ${e.message}`);
                }
                cleanupSessionSpeechArtifacts(sessionTriggerId, 'Force cleaned speech recording', {
                    removeAudioFiles: true
                });
            }
        }, 3000);
        
    } catch (error) {
        console.log(`❌ Failed to stop SoX recording: ${error.message}`);
        currentRecording = null;
        if (chatPanel) {
            chatPanel.webview.postMessage({
                command: 'speechTranscribed',
                transcription: '',
                error: `Stop recording failed: ${error.message}`
            });
        }
    }
}

function deactivate() {
    // Silent deactivation
    
    if (reviewGateWatcher) {
        clearInterval(reviewGateWatcher);
    }
    
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }

    cancelActiveRecording('Extension deactivated');
    cleanupStaleSessionFiles(0);
    
    if (outputChannel) {
        outputChannel.dispose();
    }
}

module.exports = {
    activate,
    deactivate
}; 
