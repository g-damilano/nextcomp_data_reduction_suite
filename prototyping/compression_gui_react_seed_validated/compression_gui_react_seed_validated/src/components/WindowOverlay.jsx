import React from 'react';

export function WindowOverlay({ screen, onHome, onOpen }) {
  const desktop = window.desktopApi;
  const isHome = screen === 'home';
  return (
    <div className="suite-floating-tools" onMouseDown={(e) => e.stopPropagation()}>
      {!isHome && <button className="suite-pill" onClick={onHome}>⌂ Home</button>}
      <button className="suite-pill" onClick={() => onOpen('packaging')}>Dataset</button>
      <button className="suite-pill" onClick={() => onOpen('method-editor')}>Method</button>
      <button className="suite-pill" onClick={() => onOpen('analysis')}>Analysis</button>
      <span className="suite-pill suite-pill--drag" data-window-drag="true" title="Drag window">⋮⋮</span>
      <button className="suite-pill suite-win" onClick={() => desktop?.minimizeWindow?.()} title="Minimise">−</button>
      <button className="suite-pill suite-win" onClick={() => desktop?.toggleMaximizeWindow?.()} title="Maximise / restore">□</button>
      <button className="suite-pill suite-win suite-win--close" onClick={() => desktop?.closeWindow?.()} title="Close">×</button>
    </div>
  );
}
