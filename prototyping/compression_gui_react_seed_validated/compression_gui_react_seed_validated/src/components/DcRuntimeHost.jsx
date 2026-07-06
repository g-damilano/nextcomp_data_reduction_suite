import React from 'react';

export function DcRuntimeHost({ name, template, logic, hostStyle, className, onReady, ...props }) {
  const [Component, setComponent] = React.useState(null);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    let cancelled = false;
    function mount() {
      try {
        if (!window.__dcUpdate || !window.getDC) {
          throw new Error('dc-runtime is not available. main.jsx must load src/vendor/dc-runtime.js before rendering.');
        }
        setComponent(null);
        window.__dcUpdate(name, 'html', template, false);
        window.__dcUpdate(name, 'js', logic, false);
        if (window.__dcRegistry?.[name]) window.__dcRegistry[name].fetched = true;
        const Root = window.getDC(name);
        if (!Root) {
          throw new Error(`dc-runtime did not return a component for ${name}.`);
        }
        if (!cancelled) {
          setComponent(() => Root);
          setError(null);
        }
      } catch (err) {
        console.error('[DcRuntimeHost]', err);
        if (!cancelled) {
          setComponent(null);
          setError(err);
          window.__COMPRESSION_GUI_MOUNT_STATE = 'error';
          window.__COMPRESSION_GUI_BOOT_ERROR = err?.stack || String(err);
        }
      }
    }
    mount();
    return () => { cancelled = true; };
  }, [name, template, logic]);

  React.useEffect(() => {
    if (!Component || error) return undefined;
    const timer = window.setTimeout(() => {
      onReady?.({ name });
      window.dispatchEvent(new CustomEvent('compression-gui-screen-ready', { detail: { name } }));
    }, 0);
    return () => window.clearTimeout(timer);
  }, [Component, error, name, onReady]);

  if (error) {
    return (
      <div className="dc-host-error">
        <h2>DC component failed to mount</h2>
        <pre>{error.stack || String(error)}</pre>
      </div>
    );
  }

  if (!Component) {
    return <div className="dc-host-loading">Preparing interface…</div>;
  }

  return (
    <div className={['dc-runtime-host', className].filter(Boolean).join(' ')}>
      <Component {...props} __hostStyle={hostStyle || { height: '100%' }} />
    </div>
  );
}
