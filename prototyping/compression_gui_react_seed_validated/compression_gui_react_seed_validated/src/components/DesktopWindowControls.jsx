import React from 'react';

function syncWindowState(result) {
  Promise.resolve(result)
    .then((state) => {
      if (state && typeof state === 'object') {
        window.__compressionSyncWindowState?.(state);
      }
    })
    .catch(() => {});
}

function callWindowAction(method) {
  const api = window.desktopApi;
  if (!api || typeof api[method] !== 'function') return undefined;
  return api[method]();
}

export function DesktopWindowControls({ className = '' }) {
  const invoke = (method, shouldSync = false) => (event) => {
    event.preventDefault();
    event.stopPropagation();
    const result = callWindowAction(method);
    if (shouldSync) syncWindowState(result);
  };

  return (
    <div className={['desktop-window-controls', className].filter(Boolean).join(' ')} data-window-controls="true" aria-label="Window controls">
      <button type="button" className="desktop-window-control" data-window-control="minimize" onClick={invoke('minimizeWindow')} title="Minimize" aria-label="Minimize window">-</button>
      <button type="button" className="desktop-window-control" data-window-control="maximize" onClick={invoke('toggleMaximizeWindow', true)} title="Maximize window" aria-label="Maximize window">▢</button>
      <button type="button" className="desktop-window-control desktop-window-control--close" data-window-control="close" onClick={invoke('closeWindow')} title="Close" aria-label="Close window">x</button>
    </div>
  );
}
