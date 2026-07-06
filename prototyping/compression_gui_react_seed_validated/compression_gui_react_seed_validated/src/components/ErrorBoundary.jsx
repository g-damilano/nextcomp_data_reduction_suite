import React from 'react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidUpdate(prevProps) {
    if (prevProps.resetKey !== this.props.resetKey && this.state.error) {
      this.setState({ error: null });
    }
  }

  componentDidCatch(error, info) {
    console.error('[CompressionGuiErrorBoundary]', error, info);
    window.__COMPRESSION_GUI_MOUNT_STATE = 'error';
    window.__COMPRESSION_GUI_BOOT_ERROR = error?.stack || error?.message || String(error);
  }

  render() {
    if (this.state.error) {
      const message = this.state.error?.stack || this.state.error?.message || String(this.state.error);
      return (
        <div className="suite-screen-error">
          <h2>Interface segment failed to render</h2>
          <p>The mock GUI shell caught a render error instead of leaving the viewport blank.</p>
          <pre>{message}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}
