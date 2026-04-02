const fs = require('fs');
const path = require('path');
const Module = require('module');

const extensionPath = path.resolve(__dirname, '../../V2/cursor-extension/extension.js');

class FakeOutputChannel {
    constructor(name) {
        this.name = name;
        this.lines = [];
        this.disposed = false;
    }

    appendLine(line) {
        this.lines.push(line);
    }

    dispose() {
        this.disposed = true;
    }
}

class FakeWebview {
    constructor(panel) {
        this.panel = panel;
        this.cspSource = 'test-csp-source';
        this.html = '';
        this.messages = [];
        this.messageHandler = null;
    }

    postMessage(message) {
        this.messages.push(message);
        return Promise.resolve(true);
    }

    onDidReceiveMessage(handler, thisArg, subscriptions) {
        this.messageHandler = thisArg ? handler.bind(thisArg) : handler;
        const disposable = {
            dispose: () => {
                this.messageHandler = null;
            }
        };

        if (Array.isArray(subscriptions)) {
            subscriptions.push(disposable);
        }

        return disposable;
    }

    emitMessage(message) {
        if (this.messageHandler) {
            this.messageHandler(message);
        }
    }
}

class FakeWebviewPanel {
    constructor(viewType, title, column, options) {
        this.viewType = viewType;
        this.title = title;
        this.column = column;
        this.options = options;
        this.disposed = false;
        this.revealedColumns = [];
        this.disposeHandlers = [];
        this.webview = new FakeWebview(this);
    }

    reveal(column) {
        this.revealedColumns.push(column);
    }

    onDidDispose(handler, thisArg, subscriptions) {
        const boundHandler = thisArg ? handler.bind(thisArg) : handler;
        this.disposeHandlers.push(boundHandler);
        const disposable = {
            dispose: () => {
                const index = this.disposeHandlers.indexOf(boundHandler);
                if (index >= 0) {
                    this.disposeHandlers.splice(index, 1);
                }
            }
        };

        if (Array.isArray(subscriptions)) {
            subscriptions.push(disposable);
        }

        return disposable;
    }

    dispose() {
        if (this.disposed) {
            return;
        }

        this.disposed = true;
        for (const handler of [...this.disposeHandlers]) {
            handler();
        }
    }
}

function createState() {
    return {
        panels: [],
        outputChannels: [],
        infoMessages: [],
        errorMessages: [],
        openDialogRequests: [],
        registeredCommands: [],
        openDialogResult: [],
        openDialogHandler: null,
        setOpenDialogResult(result) {
            this.openDialogHandler = null;
            this.openDialogResult = result;
        },
        setOpenDialogHandler(handler) {
            this.openDialogHandler = handler;
        }
    };
}

function createVscodeStub(state) {
    return {
        window: {
            createOutputChannel(name) {
                const channel = new FakeOutputChannel(name);
                state.outputChannels.push(channel);
                return channel;
            },
            createWebviewPanel(viewType, title, column, options) {
                const panel = new FakeWebviewPanel(viewType, title, column, options);
                state.panels.push(panel);
                return panel;
            },
            showInformationMessage(message) {
                state.infoMessages.push(message);
                return Promise.resolve(message);
            },
            showErrorMessage(message) {
                state.errorMessages.push(message);
                return Promise.resolve(message);
            },
            showOpenDialog(options) {
                state.openDialogRequests.push(options);
                if (typeof state.openDialogHandler === 'function') {
                    return Promise.resolve(state.openDialogHandler(options));
                }
                return Promise.resolve(state.openDialogResult);
            }
        },
        commands: {
            registerCommand(command, handler) {
                state.registeredCommands.push({ command, handler });
                return {
                    dispose() {}
                };
            }
        },
        workspace: {},
        Uri: {
            file(fsPath) {
                return { fsPath };
            }
        },
        ViewColumn: {
            One: 1,
            Beside: 2
        }
    };
}

function loadExtensionForTest(options = {}) {
    const previousUserId = process.env.REVIEW_GATE_USER_ID;
    const userId = options.userId || `review-gate-node-test-${process.pid}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const state = createState();
    const vscodeStub = createVscodeStub(state);
    const context = {
        extensionUri: { fsPath: path.dirname(extensionPath) },
        subscriptions: []
    };
    const originalLoad = Module._load;

    process.env.REVIEW_GATE_USER_ID = userId;
    delete require.cache[require.resolve(extensionPath)];

    Module._load = function patchedLoad(request, parent, isMain) {
        if (request === 'vscode') {
            return vscodeStub;
        }

        return originalLoad.apply(this, arguments);
    };

    let extension;
    try {
        extension = require(extensionPath);
    } finally {
        Module._load = originalLoad;
    }

    const hooks = extension.__testHooks;
    if (!hooks || typeof hooks.resetState !== 'function') {
        throw new Error('Extension did not expose resettable test hooks');
    }

    hooks.resetState();
    const runtimeRoot = hooks.getRuntimeRoot();

    return {
        extension,
        hooks,
        context,
        state,
        vscodeStub,
        userId,
        cleanup() {
            try {
                hooks.resetState();
            } catch (error) {
                // Ignore cleanup failures during test teardown.
            }

            for (const subscription of [...context.subscriptions].reverse()) {
                if (subscription && typeof subscription.dispose === 'function') {
                    try {
                        subscription.dispose();
                    } catch (error) {
                        // Ignore subscription cleanup failures in tests.
                    }
                }
            }

            try {
                fs.rmSync(runtimeRoot, { recursive: true, force: true });
            } catch (error) {
                // Ignore temp cleanup failures in tests.
            }

            delete require.cache[require.resolve(extensionPath)];
            if (previousUserId === undefined) {
                delete process.env.REVIEW_GATE_USER_ID;
            } else {
                process.env.REVIEW_GATE_USER_ID = previousUserId;
            }
        }
    };
}

module.exports = {
    loadExtensionForTest
};
