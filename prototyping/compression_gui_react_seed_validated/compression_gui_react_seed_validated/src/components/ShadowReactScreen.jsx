import React from 'react';
import { createPortal } from 'react-dom';

export function normaliseCss(css) {
  return (css || '')
    .replaceAll(':root', ':host')
    .replace(/html\s*,\s*body\s*\{/g, ':host {')
    .replace(/(^|[\s,{;}])body\s*\{/g, '$1.shadow-viewport {');
}

export function ShadowReactScreen({ css, children, className }) {
  const hostRef = React.useRef(null);
  const [shadowRoot, setShadowRoot] = React.useState(null);

  React.useLayoutEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    setShadowRoot(host.shadowRoot || host.attachShadow({ mode: 'open' }));
  }, []);

  React.useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const mirror = () => {
      const root = document.documentElement;
      const density = root.getAttribute('data-density');
      if (density) host.setAttribute('data-density', density);
      else host.removeAttribute('data-density');
      const cssText = root.getAttribute('style') || '';
      if (cssText) {
        cssText.split(';').forEach((part) => {
          const idx = part.indexOf(':');
          if (idx > 0) {
            const name = part.slice(0, idx).trim();
            const value = part.slice(idx + 1).trim();
            if (name.startsWith('--') && value) host.style.setProperty(name, value);
          }
        });
      }
    };
    mirror();
    const observer = new MutationObserver(mirror);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-density', 'style'] });
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={hostRef} className={['shadow-screen-host', className].filter(Boolean).join(' ')}>
      {shadowRoot && createPortal(
        <>
          <style>{`:host{display:block;width:100%;height:100%;min-height:0;contain:layout paint style;} .shadow-viewport{width:100%;height:100%;min-height:0;overflow:hidden;} ${normaliseCss(css)}`}</style>
          <div className="shadow-viewport">{children}</div>
        </>,
        shadowRoot
      )}
    </div>
  );
}
