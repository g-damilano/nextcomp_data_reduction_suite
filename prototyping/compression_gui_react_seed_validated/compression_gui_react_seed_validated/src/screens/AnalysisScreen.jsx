import React from 'react';
import { ShadowReactScreen } from '../components/ShadowReactScreen.jsx';
import MethodRunWizardApp from './MethodRunWizardApp.jsx';
import css from '../styles/method-run-wizard.css?raw';
import chromeCss from '../styles/window-chrome.css?raw';

export default function AnalysisScreen() {
  return (
    <ShadowReactScreen css={css + chromeCss} className="analysis-shadow">
      <MethodRunWizardApp />
    </ShadowReactScreen>
  );
}
