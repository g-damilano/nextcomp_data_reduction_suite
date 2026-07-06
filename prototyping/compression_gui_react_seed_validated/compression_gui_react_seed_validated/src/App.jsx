import React from 'react';
import './styles/suite.css';
import './styles/window-chrome.css';
import HomeScreen from './screens/HomeScreen.jsx';
import PackagingScreen from './screens/PackagingScreen.jsx';
import MethodEditorScreen from './screens/MethodEditorScreen.jsx';
import AnalysisScreen from './screens/AnalysisScreen.jsx';
import { ErrorBoundary } from './components/ErrorBoundary.jsx';
import { WindowChromeBinder } from './components/WindowChromeBinder.jsx';

export const SCREEN_CONFIG = {
  home: {
    label: 'Launcher',
    title: 'Compression Model Launcher',
    width: 980,
    height: 930,
    minWidth: 980,
    minHeight: 930,
  },
  packaging: {
    label: 'Dataset Packaging',
    title: 'Dataset Packaging',
    width: 1480,
    height: 960,
    minWidth: 1360,
    minHeight: 860,
  },
  'method-editor': {
    label: 'Method Editor',
    title: 'Analysis Method Editor',
    width: 988,
    height: 960,
    minWidth: 988,
    minHeight: 900,
  },
  analysis: {
    label: 'Method Analysis',
    title: 'Method Analysis',
    width: 1460,
    height: 940,
    minWidth: 1280,
    minHeight: 820,
  },
};

function normaliseScreen(raw) {
  if (raw && typeof raw === 'object') return normaliseScreen(raw.screen || raw.target || 'home');
  const aliases = { dataset: 'packaging', 'dataset-packaging': 'packaging', method: 'method-editor', 'method-editor': 'method-editor', mtdp: 'packaging' };
  const key = aliases[raw] || raw;
  return SCREEN_CONFIG[key] ? key : 'home';
}

function screenFromLocation() {
  const params = new URLSearchParams(window.location.search);
  return normaliseScreen(params.get('screen') || 'home');
}

function modeFromLocation() {
  const params = new URLSearchParams(window.location.search);
  const explicit = params.get('mode') || params.get('window');
  if (explicit) return explicit === 'child' ? 'child' : 'launcher';
  const requested = normaliseScreen(params.get('screen'));
  return requested && requested !== 'home'
    ? 'child'
    : 'launcher';
}

export default function App({ onReady } = {}) {
  const [windowMode] = React.useState(modeFromLocation);
  const [screen] = React.useState(() => windowMode === 'child' ? screenFromLocation() : 'home');

  const openChildWindow = React.useCallback(async (target) => {
    const childScreen = normaliseScreen(target);
    if (childScreen === 'home') return;
    const config = SCREEN_CONFIG[childScreen];
    const extra = target && typeof target === 'object' ? target : {};
    const payload = { ...extra, screen: childScreen, ...config };

    if (window.desktopApi?.openChildWindow) {
      await window.desktopApi.openChildWindow(payload);
      return;
    }

    const url = new URL(window.location.href);
    url.searchParams.set('mode', 'child');
    url.searchParams.set('screen', childScreen);
    if (payload.initial_package_path || payload.package_path) {
      url.searchParams.set('initial_package_path', payload.initial_package_path || payload.package_path);
    }
    window.open(
      url.toString(),
      config.title,
      `popup=yes,width=${config.width},height=${config.height},minWidth=${config.minWidth},minHeight=${config.minHeight}`,
    );
  }, []);

  React.useEffect(() => {
    window.__compressionSuiteOpenChild = openChildWindow;
    return () => {
      if (window.__compressionSuiteOpenChild === openChildWindow) {
        delete window.__compressionSuiteOpenChild;
      }
    };
  }, [openChildWindow]);

  const notifyReady = React.useCallback((detail = {}) => {
    onReady?.({ screen, windowMode, ...detail });
  }, [onReady, screen, windowMode]);

  React.useEffect(() => {
    const waitsForDcRuntimeHost = windowMode === 'launcher'
      || (windowMode === 'child' && (screen === 'home' || screen === 'method-editor'));
    if (waitsForDcRuntimeHost) return undefined;
    const timer = window.setTimeout(() => notifyReady({ source: 'react-screen' }), 0);
    return () => window.clearTimeout(timer);
  }, [notifyReady, screen, windowMode]);

  React.useEffect(() => {
    const url = new URL(window.location.href);
    const currentMode = url.searchParams.get('mode') || url.searchParams.get('window') || 'launcher';
    if (url.searchParams.get('screen') !== screen || currentMode !== windowMode) {
      url.searchParams.set('screen', screen);
      url.searchParams.set('mode', windowMode);
      window.history.replaceState(null, '', url);
    }
  }, [screen, windowMode]);

  React.useEffect(() => {
    const onKey = (event) => {
      if (event.target && (
        ['INPUT', 'TEXTAREA', 'SELECT'].includes(event.target.tagName)
        || event.target.closest?.('[contenteditable="true"]')
      )) return;
      const key = event.key.toLowerCase();

      if (event.key === 'F11' || (event.altKey && event.key === 'Enter')) {
        event.preventDefault();
        window.desktopApi?.toggleMaximizeWindow?.();
        return;
      }

      if ((event.ctrlKey || event.metaKey) && key === 'w') {
        event.preventDefault();
        window.desktopApi?.closeWindow?.();
        return;
      }

      if ((event.ctrlKey || event.metaKey) && key === 'q') {
        event.preventDefault();
        const quit = window.desktopApi?.quitApplication || window.desktopApi?.closeWindow;
        quit?.();
        return;
      }

      if ((event.ctrlKey || event.metaKey) && event.shiftKey && key === 'm') {
        event.preventDefault();
        window.desktopApi?.minimizeWindow?.();
        return;
      }

      if (!(event.ctrlKey || event.metaKey) || event.altKey || event.shiftKey) return;
      if (key === 'd') { event.preventDefault(); openChildWindow('packaging'); }
      if (key === 'm') { event.preventDefault(); openChildWindow('method-editor'); }
      if (key === 'a') { event.preventDefault(); openChildWindow('analysis'); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [openChildWindow]);

  return (
    <div className="suite-root" data-screen={screen} data-window-mode={windowMode}>
      <WindowChromeBinder screen={screen} />
      <main className="suite-screen" aria-label={SCREEN_CONFIG[screen]?.label || 'Compression suite'}>
        <ErrorBoundary resetKey={`${windowMode}:${screen}`}>
          {windowMode === 'launcher' && <HomeScreen onLaunch={openChildWindow} onReady={notifyReady} />}
          {windowMode === 'child' && screen === 'packaging' && <PackagingScreen />}
          {windowMode === 'child' && screen === 'method-editor' && <MethodEditorScreen onReady={notifyReady} />}
          {windowMode === 'child' && screen === 'analysis' && <AnalysisScreen />}
          {windowMode === 'child' && screen === 'home' && <HomeScreen onLaunch={openChildWindow} onReady={notifyReady} />}
        </ErrorBoundary>
      </main>
    </div>
  );
}
