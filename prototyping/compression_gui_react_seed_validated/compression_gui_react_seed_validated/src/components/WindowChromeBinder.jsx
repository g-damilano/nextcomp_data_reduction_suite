import React from 'react';

function isElement(value) {
  return value && value.nodeType === 1 && typeof value.matches === 'function';
}

function isInteractiveFromPath(path) {
  return path.some((node) => {
    if (!isElement(node)) return false;
    if (node.matches('button,input,textarea,select,a,[role="button"],[contenteditable="true"],[data-window-control],[data-window-action],.window-control')) return true;
    if (node.matches('.menu-item,.menu__btn,.menu__pop,.menu-pop,.menubar__schema,.desktop-window-control,.modal,.drawer-scrim,.scrim')) return true;
    const cursor = window.getComputedStyle(node).cursor;
    return cursor === 'pointer' || cursor === 'text';
  });
}

function isChromeRegion(screen, event, path) {
  if (path.some((node) => isElement(node) && node.matches('[data-window-drag],.menubar--desktop,.menubar'))) return true;

  const topBand = {
    home: 30,
    packaging: 30,
    'method-editor': 30,
    analysis: 30,
  }[screen] || 34;

  return event.clientY >= 0 && event.clientY <= topBand;
}

function syncWindowState(result) {
  Promise.resolve(result)
    .then((state) => {
      if (state && typeof state === 'object') {
        window.__compressionSyncWindowState?.(state);
      }
    })
    .catch(() => {});
}

export function WindowChromeBinder({ screen }) {
  React.useEffect(() => {
    const onMouseDown = (event) => {
      if (event.button !== 0) return;
      if (event.detail > 1) return;
      if (!window.desktopApi?.host || !window.desktopApi?.startWindowDrag) return;
      const path = event.composedPath ? event.composedPath() : [];
      if (isInteractiveFromPath(path)) return;
      if (!isChromeRegion(screen, event, path)) return;
      event.preventDefault();
      window.desktopApi.startWindowDrag({
        source: 'browser-event',
        screen,
        clientX: event.clientX,
        clientY: event.clientY,
      });
    };

    const onDoubleClick = (event) => {
      if (event.button !== 0) return;
      if (!window.desktopApi?.host || !window.desktopApi?.toggleMaximizeWindow) return;
      const path = event.composedPath ? event.composedPath() : [];
      if (isInteractiveFromPath(path)) return;
      if (!isChromeRegion(screen, event, path)) return;
      event.preventDefault();
      event.stopPropagation();
      syncWindowState(window.desktopApi.toggleMaximizeWindow());
    };

    document.addEventListener('mousedown', onMouseDown, true);
    document.addEventListener('dblclick', onDoubleClick, true);
    return () => {
      document.removeEventListener('mousedown', onMouseDown, true);
      document.removeEventListener('dblclick', onDoubleClick, true);
    };
  }, [screen]);

  return null;
}
