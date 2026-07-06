import React from 'react';
import { DcRuntimeHost } from '../components/DcRuntimeHost.jsx';
import { METHOD_EDITOR_DC, METHOD_EDITOR_LOGIC } from '../generated/dcSources.js';
import { withBackendMethodEditorLogic, withBackendMethodEditorTemplate } from '../backend/methodEditorLogicBridge.js';

const METHOD_EDITOR_BACKEND_DC = withBackendMethodEditorTemplate(METHOD_EDITOR_DC);
const METHOD_EDITOR_BACKEND_LOGIC = withBackendMethodEditorLogic(METHOD_EDITOR_LOGIC);

export default function MethodEditorScreen({ onReady }) {
  return (
    <DcRuntimeHost
      name="AnalysisMethodEditorHiFiV2"
      template={METHOD_EDITOR_BACKEND_DC}
      logic={METHOD_EDITOR_BACKEND_LOGIC}
      methodEditorApi={window.desktopApi?.methodEditor}
      showValidation={true}
      onReady={onReady}
    />
  );
}
