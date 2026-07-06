import React from 'react';
import * as ReactDOMClient from 'react-dom/client';
import { createDesktopApi } from './backend/desktopApi.js';

window.React = React;
window.ReactDOM = ReactDOMClient;
window.desktopApi = window.desktopApi || createDesktopApi();
window.__COMPRESSION_GUI_MOUNT_STATE = 'booting';

function waitForDcRuntime(timeoutMs = 5000) {
  const start = performance.now();
  return new Promise((resolve, reject) => {
    const tick = () => {
      if (window.__dcUpdate && window.getDC) return resolve();
      if (performance.now() - start > timeoutMs) return reject(new Error('dc-runtime did not initialise'));
      setTimeout(tick, 0);
    };
    tick();
  });
}

function markMounted(root) {
  if (!root || root.dataset.compressionGuiMounted === 'true') return;
  root.dataset.compressionGuiMounted = 'true';
  window.__COMPRESSION_GUI_MOUNT_STATE = 'mounted';
  window.dispatchEvent(new CustomEvent('compression-gui-mounted'));
}

async function boot() {
  await import('./vendor/dc-runtime.js');
  await waitForDcRuntime();
  const { default: App } = await import('./App.jsx');
  const root = document.getElementById('root');
  if (!root) throw new Error('React root element #root was not found');
  window.__COMPRESSION_GUI_MOUNT_STATE = 'rendering';
  ReactDOMClient.createRoot(root).render(<App onReady={() => markMounted(root)} />);
}

boot().catch((error) => {
  console.error('[compression-suite] boot failed', error);
  window.__COMPRESSION_GUI_MOUNT_STATE = 'error';
  window.__COMPRESSION_GUI_BOOT_ERROR = String(error && error.stack || error);
  document.body.innerHTML = `<pre style="white-space:pre-wrap;padding:24px;font-family:ui-monospace,Consolas,monospace;color:#991b1b">${String(error && error.stack || error)}</pre>`;
});
