let bridgePromise = null;
let commandSequence = 0;
const analysisEventHandlers = new Set();
let analysisEventSignalConnected = false;

function loadQWebChannelScript() {
  if (window.QWebChannel) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const existing = document.querySelector('script[data-qwebchannel="true"]');
    if (existing) {
      existing.addEventListener('load', resolve, { once: true });
      existing.addEventListener('error', reject, { once: true });
      return;
    }
    const script = document.createElement('script');
    script.dataset.qwebchannel = 'true';
    script.src = 'qrc:///qtwebchannel/qwebchannel.js';
    script.onload = resolve;
    script.onerror = reject;
    document.head.appendChild(script);
  });
}

async function getQtBridge() {
  if (!window.qt?.webChannelTransport) return null;
  if (bridgePromise) return bridgePromise;

  bridgePromise = loadQWebChannelScript().then(() => new Promise((resolve) => {
    new window.QWebChannel(window.qt.webChannelTransport, (channel) => {
      resolve(channel.objects.mtdpBridge || null);
    });
  })).catch((err) => {
    console.warn('[desktopApi] QWebChannel unavailable', err);
    bridgePromise = null;
    return null;
  });

  return bridgePromise;
}

async function callBridge(method, payload) {
  const bridge = await getQtBridge();
  if (!bridge || typeof bridge[method] !== 'function') {
    console.info(`[desktopApi.${method}:stub]`, payload ?? '');
    return {
      status: 'error',
      error_type: 'BridgeUnavailable',
      message: `PySide6 backend bridge method ${method} is not available in this browser context.`,
      recoverable: true,
      details: { method, source: 'browser-stub' },
    };
  }

  return new Promise((resolve) => {
    const finish = (raw) => {
      if (typeof raw !== 'string') {
        resolve(raw ?? { status: 'ok' });
        return;
      }
      try {
        resolve(JSON.parse(raw));
      } catch {
        resolve({ status: 'ok', raw });
      }
    };

    if (payload === undefined) {
      bridge[method](finish);
    } else {
      bridge[method](JSON.stringify(payload), finish);
    }
  });
}

function parseBridgePayload(raw) {
  if (typeof raw !== 'string') return raw ?? {};
  try {
    return JSON.parse(raw);
  } catch {
    return { status: 'ok', raw };
  }
}

async function ensureAnalysisEventSignal() {
  const bridge = await getQtBridge();
  if (!bridge?.analysisEvent?.connect || analysisEventSignalConnected) return Boolean(analysisEventSignalConnected);
  bridge.analysisEvent.connect((raw) => {
    const payload = parseBridgePayload(raw);
    analysisEventHandlers.forEach((handler) => {
      try {
        handler(payload);
      } catch (err) {
        console.warn('[desktopApi.analysisEvent] handler failed', err);
      }
    });
  });
  analysisEventSignalConnected = true;
  return true;
}

async function dispatchCommand(namespace, command, payload = {}, options = {}) {
  const bridge = await getQtBridge();
  const request = {
    id: options.id || `gui-${Date.now()}-${++commandSequence}`,
    namespace,
    command,
    session_id: options.sessionId || options.session_id || null,
    payload: payload || {},
  };

  if (!bridge || typeof bridge.dispatch !== 'function') {
    console.info(`[desktopApi.command:stub] ${namespace}.${command}`, payload ?? '');
    return {
      id: request.id,
      status: 'error',
      error_type: 'BridgeUnavailable',
      message: 'PySide6 backend bridge is not available in this browser context.',
      recoverable: true,
      details: { namespace, command, source: 'browser-stub' },
    };
  }

  return callBridge('dispatch', request);
}

async function callBridgeRequired(method, payload, details = {}) {
  const bridge = await getQtBridge();
  if (!bridge || typeof bridge[method] !== 'function') {
    return {
      status: 'error',
      error_type: 'BridgeUnavailable',
      message: `PySide6 backend bridge method ${method} is not available in this browser context.`,
      recoverable: true,
      details,
    };
  }
  return callBridge(method, payload);
}

function normalizeSubscriptionOptions(options) {
  if (typeof options === 'function') return { onEvent: options };
  return options || {};
}

async function subscribeAnalysisEvents(payload = {}, options = {}) {
  const subscriptionOptions = normalizeSubscriptionOptions(options);
  const onEvent = subscriptionOptions.onEvent;
  if (typeof onEvent === 'function') {
    analysisEventHandlers.add(onEvent);
    await ensureAnalysisEventSignal();
  }
  const response = await callBridgeRequired('subscribeAnalysisEvents', payload, {
    namespace: 'analysis',
    command: 'subscribeEvents',
  });
  if (response?.status === 'ok') {
    return {
      ...response,
      unsubscribe: async () => {
        if (typeof onEvent === 'function') analysisEventHandlers.delete(onEvent);
        return callBridgeRequired('unsubscribeAnalysisEvents', { session_id: payload?.session_id || payload?.sessionId || null }, {
          namespace: 'analysis',
          command: 'unsubscribeEvents',
        });
      },
    };
  }
  if (typeof onEvent === 'function') analysisEventHandlers.delete(onEvent);
  return response;
}

async function unsubscribeAnalysisEvents(payload = {}, options = {}) {
  const subscriptionOptions = normalizeSubscriptionOptions(options);
  if (typeof subscriptionOptions.onEvent === 'function') {
    analysisEventHandlers.delete(subscriptionOptions.onEvent);
  }
  return callBridgeRequired('unsubscribeAnalysisEvents', payload, {
    namespace: 'analysis',
    command: 'unsubscribeEvents',
  });
}

function openBrowserChildWindow(payload) {
  const screen = payload?.screen || 'packaging';
  const title = payload?.title || payload?.label || 'Compression GUI';
  const width = Number(payload?.width || 1400);
  const height = Number(payload?.height || 900);
  const url = new URL(window.location.href);
  url.searchParams.set('mode', 'child');
  url.searchParams.set('screen', screen);
  const features = [
    'popup=yes',
    `width=${width}`,
    `height=${height}`,
    `left=${Math.max(0, Math.round((window.screenX || 0) + 42))}`,
    `top=${Math.max(0, Math.round((window.screenY || 0) + 42))}`,
  ].join(',');
  const child = window.open(url.toString(), title, features);
  return {
    status: child ? 'opened' : 'blocked',
    source: 'browser-window',
    screen,
    title,
    width,
    height,
  };
}

export function createDesktopApi() {
  const host = Boolean(window.qt && window.qt.webChannelTransport);
  if (host) getQtBridge();

  return {
    host,
    async openChildWindow(payload) {
      const bridge = await getQtBridge();
      if (bridge && typeof bridge.openChildWindow === 'function') {
        return callBridge('openChildWindow', payload);
      }
      return openBrowserChildWindow(payload);
    },
    async command(namespace, command, payload = {}, options = {}) {
      return dispatchCommand(namespace, command, payload, options);
    },
    packaging: {
      async createSession(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'createSession', payload, options);
      },
      async getSession(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'getSession', payload, options);
      },
      async listSchemas(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'listSchemas', payload, options);
      },
      async openPackageDialog(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'openPackageDialog', payload, options);
      },
      async openSourcesDialog(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'openSourcesDialog', payload, options);
      },
      async loadSources(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'loadSources', payload, options);
      },
      async loadPackage(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'loadPackage', payload, options);
      },
      async setSchema(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'setSchema', payload, options);
      },
      async validateGroup(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'validateGroup', payload, options);
      },
      async exportGroup(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'exportGroup', payload, options);
      },
      async exportAllReady(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'exportAllReady', payload, options);
      },
      async updateDatasetFields(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'updateDatasetFields', payload, options);
      },
      async updateRunFields(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'updateRunFields', payload, options);
      },
      async updateGroupRunFields(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'updateGroupRunFields', payload, options);
      },
      async updateRunFieldMatrix(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'updateRunFieldMatrix', payload, options);
      },
      async setGroupRunUnit(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'setGroupRunUnit', payload, options);
      },
      async proposeGroups(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'proposeGroups', payload, options);
      },
      async applyGroupingProposal(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'applyGroupingProposal', payload, options);
      },
      async addImageEvidence(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'addImageEvidence', payload, options);
      },
      async removeImageEvidence(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'removeImageEvidence', payload, options);
      },
      async addSupplementalFiles(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'addSupplementalFiles', payload, options);
      },
      async removeSupplementalFile(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'removeSupplementalFile', payload, options);
      },
      async rematchYamlSidecars(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'rematchYamlSidecars', payload, options);
      },
      async reviewYamlMapping(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'reviewYamlMapping', payload, options);
      },
      async applyYamlMappingProfile(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'applyYamlMappingProfile', payload, options);
      },
      async createGroup(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'createGroup', payload, options);
      },
      async renameGroup(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'renameGroup', payload, options);
      },
      async deleteGroup(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'deleteGroup', payload, options);
      },
      async moveRun(payload = {}, options = {}) {
        return dispatchCommand('packaging', 'moveRun', payload, options);
      },
    },
    methodEditor: {
      async listMethods(payload = {}, options = {}) {
        return dispatchCommand('methodEditor', 'listMethods', payload, options);
      },
      async loadMethod(payload = {}, options = {}) {
        return dispatchCommand('methodEditor', 'loadMethod', payload, options);
      },
      async createDraft(payload = {}, options = {}) {
        return dispatchCommand('methodEditor', 'createDraft', payload, options);
      },
      async updateDraft(payload = {}, options = {}) {
        return dispatchCommand('methodEditor', 'updateDraft', payload, options);
      },
      async validateDraft(payload = {}, options = {}) {
        return dispatchCommand('methodEditor', 'validateDraft', payload, options);
      },
      async generateVersion(payload = {}, options = {}) {
        return dispatchCommand('methodEditor', 'generateVersion', payload, options);
      },
      async registerGeneratedMethod(payload = {}, options = {}) {
        return dispatchCommand('methodEditor', 'registerGeneratedMethod', payload, options);
      },
      async exportMethodPackage(payload = {}, options = {}) {
        return dispatchCommand('methodEditor', 'exportMethodPackage', payload, options);
      },
      async openMethodPackage(payload = {}, options = {}) {
        return dispatchCommand('methodEditor', 'openMethodPackage', payload, options);
      },
      async renameMethod(payload = {}, options = {}) {
        return dispatchCommand('methodEditor', 'renameMethod', payload, options);
      },
      async deleteMethod(payload = {}, options = {}) {
        return dispatchCommand('methodEditor', 'deleteMethod', payload, options);
      },
    },
    analysis: {
      async createSession(payload = {}, options = {}) {
        return dispatchCommand('analysis', 'createSession', payload, options);
      },
      async getSession(payload = {}, options = {}) {
        return dispatchCommand('analysis', 'getSession', payload, options);
      },
      async getEvents(payload = {}, options = {}) {
        return dispatchCommand('analysis', 'getEvents', payload, options);
      },
      async listRecentPackages(payload = {}, options = {}) {
        return dispatchCommand('analysis', 'listRecentPackages', payload, options);
      },
      async subscribeEvents(payload = {}, options = {}) {
        return subscribeAnalysisEvents(payload, options);
      },
      async unsubscribeEvents(payload = {}, options = {}) {
        return unsubscribeAnalysisEvents(payload, options);
      },
      async loadPackage(payload = {}, options = {}) {
        return dispatchCommand('analysis', 'loadPackage', payload, options);
      },
      async openPackageDialog(payload = {}, options = {}) {
        return dispatchCommand('analysis', 'openPackageDialog', payload, options);
      },
      async listMethods(payload = {}, options = {}) {
        return dispatchCommand('analysis', 'listMethods', payload, options);
      },
      async selectMethod(payload = {}, options = {}) {
        return dispatchCommand('analysis', 'selectMethod', payload, options);
      },
      async loadMapping(payload = {}, options = {}) {
        return dispatchCommand('analysis', 'loadMapping', payload, options);
      },
      async openMappingDialog(payload = {}, options = {}) {
        return dispatchCommand('analysis', 'openMappingDialog', payload, options);
      },
      async confirmMapping(payload = {}, options = {}) {
        return dispatchCommand('analysis', 'confirmMapping', payload, options);
      },
      async applyMappingPatch(payload = {}, options = {}) {
        return dispatchCommand('analysis', 'applyMappingPatch', payload, options);
      },
      async saveMappingDialog(payload = {}, options = {}) {
        return dispatchCommand('analysis', 'saveMappingDialog', payload, options);
      },
      async checkReadiness(payload = {}, options = {}) {
        return dispatchCommand('analysis', 'checkReadiness', payload, options);
      },
      async startRun(payload = {}, options = {}) {
        return dispatchCommand('analysis', 'startRun', payload, options);
      },
      async cancelRun(payload = {}, options = {}) {
        return dispatchCommand('analysis', 'cancelRun', payload, options);
      },
      async updateAcceptanceDecision(payload = {}, options = {}) {
        return dispatchCommand('analysis', 'updateAcceptanceDecision', payload, options);
      },
      async confirmReview(payload = {}, options = {}) {
        return dispatchCommand('analysis', 'confirmReview', payload, options);
      },
      async finalizeMtda(payload = {}, options = {}) {
        return dispatchCommand('analysis', 'finalizeMtda', payload, options);
      },
      async applyReportAmendments(payload = {}, options = {}) {
        return dispatchCommand('analysis', 'applyReportAmendments', payload, options);
      },
      async copyOutputPath(payload = {}, options = {}) {
        return dispatchCommand('analysis', 'copyOutputPath', payload, options);
      },
      async openArtifact(payload = {}, options = {}) {
        return dispatchCommand('analysis', 'openArtifact', payload, options);
      },
    },
    async loadProject() {
      return callBridge('loadProject');
    },
    async saveProject(payload) {
      return callBridge('saveProject', payload);
    },
    async validate(payload) {
      return callBridge('validate', payload);
    },
    async exportPackage(payload) {
      return callBridge('exportPackage', payload);
    },
    async startWindowDrag(payload) {
      return callBridge('startWindowDrag', payload);
    },
    async minimizeWindow() {
      return callBridge('minimizeWindow');
    },
    async toggleMaximizeWindow() {
      return callBridge('toggleMaximizeWindow');
    },
    async closeWindow() {
      return callBridge('closeWindow');
    },
    async quitApplication() {
      const bridge = await getQtBridge();
      if (bridge && typeof bridge.quitApplication === 'function') {
        return callBridge('quitApplication');
      }
      return callBridge('closeWindow');
    }
  };
}
