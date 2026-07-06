function countOccurrences(source, needle) {
  let count = 0;
  let index = 0;
  while ((index = source.indexOf(needle, index)) !== -1) {
    count += 1;
    index += needle.length;
  }
  return count;
}

function replaceExactCount(source, needle, replacement, expectedCount) {
  const found = countOccurrences(source, needle);
  if (found !== expectedCount) {
    throw new Error(`Method Editor generated source drifted: expected ${expectedCount} match(es), found ${found}.`);
  }
  return source.split(needle).join(replacement);
}

function replaceAnyExactCount(source, needles, replacement, expectedCount) {
  const found = needles.reduce((total, needle) => total + countOccurrences(source, needle), 0);
  if (found !== expectedCount) {
    throw new Error(`Method Editor generated source drifted: expected ${expectedCount} match(es), found ${found}.`);
  }
  return needles.reduce((next, needle) => next.split(needle).join(replacement), source);
}

function replaceOnce(source, needle, replacement) {
  return replaceExactCount(source, needle, replacement, 1);
}

const createMethodNowSource = `  createMethodNow() {
    this.setState(st => { const n = st.newSeq; const id = 'draft_' + n; const label = 'New method ' + n; return { methods:[...st.methods, { id, label, version:'0.1.0' }], methodId:id, newSeq:n+1, menuOpen:true, editingNameId:id, nameDraft:label, topMenu:null }; });
  }`;

const createMethodNowBridge = `  createLocalMethodNow() {
    this.setState(st => { const n = st.newSeq; const id = 'draft_' + n; const label = 'New method ' + n; return { methods:[...st.methods, { id, label, version:'0.1.0' }], methodId:id, newSeq:n+1, menuOpen:true, editingNameId:id, nameDraft:label, topMenu:null }; });
  }
  async createMethodNow() {
    const api = this.methodEditorApi();
    if (!api?.createDraft) { this.createLocalMethodNow(); return; }
    if (!api?.generateVersion || !api?.registerGeneratedMethod) { await this.createBackendDraftNow(); return; }
    const label = 'New method ' + this.state.newSeq;
    const generated = await this.generateVersionNow({ defaultLabel:label });
    if (generated) {
      this.setState(st => ({ newSeq:st.newSeq + 1, menuOpen:true, editingNameId:generated.method_id, nameDraft:label }));
    }
  }`;

const renameCurrentNowSource = `  renameCurrentNow() {
    this.setState(st => { const cur = st.methods.find(m => m.id === st.methodId) || st.methods[0]; return { menuOpen:true, editingNameId: cur.id, nameDraft: cur.label, topMenu:null }; });
  }`;

const renameCurrentNowBridge = `  renameCurrentNow() {
    const cur = this.currentMethodOption();
    if (!cur) return;
    this.startRenameMethod(cur);
  }`;

const backendMethods = `
  methodEditorApi() {
    return this.props.methodEditorApi || window.desktopApi?.methodEditor || null;
  }
  apiData(response, action) {
    if (response && response.status === 'ok') return response.data || {};
    if (response && response.status === undefined) return response;
    const message = response?.message || response?.error || response?.error_type || (action + ' failed');
    throw new Error(message);
  }
  backendUnavailable() {
    return 'Method Editor backend unavailable';
  }
  displayMethodLabel(label) {
    const raw = String(label || '').trim();
    return raw.replace(/\\s*\\(generated\\s+v?[0-9]+(?:\\.[0-9]+){2}\\)\\s*$/i, '').trim() || raw;
  }
  handleBackendError(error, fallback) {
    const message = error?.message || fallback;
    this.setState({ backendBusy:false, backendStatusText: message });
    this.fireToast(message);
    return null;
  }
  hasUnsavedMethodEdits() {
    return !!this.state.methodDirty;
  }
  markMethodDirty(update) {
    if (typeof update === 'function') {
      this.setState(st => {
        const patch = update(st) || {};
        return { ...patch, methodDirty:true, backendStatusText:'Unsaved method edits' };
      });
      return;
    }
    this.setState({ ...(update || {}), methodDirty:true, backendStatusText:'Unsaved method edits' });
  }
  clearMethodDirty(statusText) {
    this.setState({ methodDirty:false, backendStatusText: statusText || this.state.backendStatusText });
  }
  saveMethodIfDirtyNow() {
    if (!this.hasUnsavedMethodEdits()) {
      this.fireToast('No method edits to save');
      return null;
    }
    return this.generateVersionNow();
  }
  confirmDiscardUnsavedEdits() {
    if (!this.hasUnsavedMethodEdits()) return true;
    return window.confirm('You have unsaved method edits. Close Method Editor and discard them?');
  }
  requestCloseWindow(e) {
    e?.preventDefault?.();
    e?.stopPropagation?.();
    if (!this.confirmDiscardUnsavedEdits()) return;
    window.desktopApi?.closeWindow?.();
  }
  methodOptionFromBackend(item) {
    const method = item?.method || item || {};
    const id = item?.method_id || item?.methodId || item?.id || method.method_id || method.methodId || method.id;
    const version = item?.version || method.version || '0.0.0';
    const rawLabel = item?.label || item?.method_name || item?.name || method.label || method.method_name || method.name || id;
    const label = this.displayMethodLabel(rawLabel);
    const generated = !!(item?.generated || item?.source === 'method_editor_generated' || item?.source_draft_id || method.generated);
    return id ? {
      ...item,
      id,
      method_id:id,
      label,
      version,
      generated,
      canonical:item?.canonical ?? !generated,
      editable:item?.editable ?? generated,
      deletable:item?.deletable ?? generated,
    } : null;
  }
  methodPathForOption(method) {
    return method?.method_path || method?.methodPath || method?.method?.method_path || method?.method?.methodPath || '';
  }
  currentMethodOption() {
    return this.state.methods.find(m => m.id === this.state.methodId) || this.state.methods[0] || null;
  }
  async loadBackendMethods() {
    const api = this.methodEditorApi();
    if (!api?.listMethods) return;
    this.setState({ backendMode:true, backendBusy:true, backendStatusText:'Loading method registry...' });
    try {
      const data = this.apiData(await api.listMethods({}), 'List methods');
      const methods = (Array.isArray(data.methods) ? data.methods : [])
        .map(item => this.methodOptionFromBackend(item))
        .filter(Boolean);
      if (!methods.length) {
        this.setState({ backendBusy:false, backendStatusText:'No backend methods registered' });
        return;
      }
      const selected = methods.find(m => m.id === this.state.methodId) || methods[0];
      this.setState({ methods, methodId:selected.id, backendMode:true, backendBusy:false, backendDraft:null, backendGeneratedMethod:null, backendStatusText:'Method registry loaded', methodDirty:false });
      await this.loadBackendMethod(selected.id);
    } catch (error) {
      this.handleBackendError(error, 'Method registry unavailable');
    }
  }
  async loadBackendMethod(methodId) {
    const api = this.methodEditorApi();
    if (!api?.loadMethod || !methodId) return null;
    try {
      const data = this.apiData(await api.loadMethod({ methodId }), 'Load method');
      this.setState({ backendBaseMethod:data.method || null, backendDraft:null, backendGeneratedMethod:null, methodDirty:false });
      return data.method || null;
    } catch (error) {
      this.handleBackendError(error, 'Method load failed');
      return null;
    }
  }
  selectMethodNow(method) {
    const id = method?.id || method?.method_id;
    if (!id) return;
    if (!this.confirmDiscardUnsavedEdits()) return;
    this.setState({ methodId:id, menuOpen:false, editingNameId:null, backendDraft:null, backendGeneratedMethod:null, backendStatusText:'Method selected', methodDirty:false });
    this.loadBackendMethod(id);
  }
  startRenameMethod(method) {
    if (!method?.id) return;
    if (this.state.backendMode && !(method.editable || method.generated)) { this.fireToast('ISO reference methods are read-only'); return; }
    this.setState({ menuOpen:true, editingNameId: method.id, nameDraft: method.label });
  }
  async commitMethodNameNow() {
    const editingId = this.state.editingNameId;
    if (editingId == null) return;
    const label = String(this.state.nameDraft || '').trim();
    const method = this.state.methods.find(item => item.id === editingId);
    if (!label) {
      this.setState({ editingNameId:null });
      return;
    }
    if (this.state.backendMode && method && !(method.editable || method.generated)) {
      this.setState({ editingNameId:null });
      this.fireToast('ISO reference methods are read-only');
      return;
    }
    this.setState(st => ({
      methods: st.methods.map(item => item.id === editingId ? { ...item, label } : item),
      editingNameId:null,
      backendStatusText:'Renamed ' + label,
    }));
    const api = this.methodEditorApi();
    if (!this.state.backendMode || !api?.renameMethod || !method) {
      return;
    }
    try {
      const data = this.apiData(await api.renameMethod({
        method_id: method.method_id || method.id,
        method_path: this.methodPathForOption(method),
        label,
      }), 'Rename method');
      const option = this.methodOptionFromBackend(data.method || data.registry_entry || data);
      if (option) {
        this.setState(st => ({
          methods: st.methods.map(item => item.id === editingId ? { ...item, ...option, label } : item),
          backendStatusText:'Renamed ' + label,
        }));
      }
    } catch (error) {
      this.handleBackendError(error, 'Method rename failed');
    }
  }
  async createBackendDraftNow() {
    const api = this.methodEditorApi();
    if (!api?.createDraft) return null;
    const method = this.currentMethodOption();
    const methodId = this.state.methodId || method?.id;
    if (!methodId) return this.handleBackendError(new Error('No method selected'), 'Draft creation failed');
    this.setState({ backendBusy:true, backendStatusText:'Creating draft...', topMenu:null });
    try {
      const data = this.apiData(await api.createDraft({ methodId, draftLabel:(method?.label || methodId) + ' draft' }), 'Create draft');
      const draft = data.draft;
      if (!draft?.draft_id && !draft?.draft_path) throw new Error('Draft response missing draft reference');
      this.setState({
        backendMode:true,
        backendBusy:false,
        backendDraft:draft,
        backendGeneratedMethod:null,
        backendStatusText:'Draft ready',
        menuOpen:false,
        editingNameId:null,
        methodId:draft.base_method_id || draft.method?.method_id || methodId,
      });
      this.fireToast('Draft ready');
      return draft;
    } catch (error) {
      return this.handleBackendError(error, 'Draft creation failed');
    }
  }
  async ensureBackendDraft() {
    const draft = this.state.backendDraft;
    const methodId = this.state.methodId;
    if (draft && (draft.base_method_id === methodId || draft.method?.method_id === methodId || !draft.base_method_id)) return draft;
    const created = await this.createBackendDraftNow();
    if (!created) throw new Error('Draft not available');
    return created;
  }
  controlledModulusValues() {
    const start = Number.parseFloat(this.state.startStrain);
    const end = Number.parseFloat(this.state.endStrain);
    if (!Number.isFinite(start) || !Number.isFinite(end) || start < 0 || end <= start) {
      throw new Error('Fix field format to continue');
    }
    return { start_strain:start, end_strain:end };
  }
  async saveControlledModulusDraft() {
    const api = this.methodEditorApi();
    if (!api?.updateDraft) throw new Error(this.backendUnavailable());
    const draft = await this.ensureBackendDraft();
    this.setState({ backendBusy:true, backendStatusText:'Saving draft...', topMenu:null });
    const data = this.apiData(await api.updateDraft({
      draft_id:draft.draft_id,
      draft_path:draft.draft_path,
      patch:{
        parameter_group:'modulus_chord_strain_window',
        values:this.controlledModulusValues(),
        reason:'Method Editor UI controlled modulus update',
      },
    }), 'Save draft');
    const updatedDraft = data.draft || draft;
    this.setState({ backendBusy:false, backendDraft:updatedDraft, backendValidation:data.validation || null, backendStatusText:'Draft saved' });
    return updatedDraft;
  }
  async saveDraftNow() {
    const api = this.methodEditorApi();
    if (!api?.updateDraft) { this.fireToast(this.backendUnavailable()); return null; }
    try {
      const draft = await this.saveControlledModulusDraft();
      this.fireToast('Draft saved');
      return draft;
    } catch (error) {
      return this.handleBackendError(error, 'Draft save failed');
    }
  }
  async validateDraftNow() {
    const api = this.methodEditorApi();
    if (!api?.validateDraft) { this.fireToast(this.backendUnavailable()); return null; }
    try {
      this.setState({ backendBusy:true, backendStatusText:'Validating draft...', topMenu:null });
      const draft = await this.saveControlledModulusDraft();
      const data = this.apiData(await api.validateDraft({ draft_id:draft.draft_id, draft_path:draft.draft_path }), 'Validate draft');
      const validation = data.validation || {};
      const valid = validation.status === 'valid' || validation.loadable === true;
      this.setState({
        backendBusy:false,
        backendDraft:data.draft || draft,
        backendValidation:validation,
        backendStatusText:valid ? 'Draft valid' : 'Draft checked',
      });
      this.fireToast(valid ? 'Draft valid' : 'Draft checked');
      return { draft:data.draft || draft, validation };
    } catch (error) {
      return this.handleBackendError(error, 'Draft validation failed');
    }
  }
  nextTargetVersion() {
    const method = this.currentMethodOption();
    const raw = String(method?.version || this.state.backendBaseMethod?.version || '0.1.0').replace(/^v/i, '');
    const parts = raw.split('.').map(part => Number.parseInt(part, 10));
    if (parts.length !== 3 || parts.some(part => !Number.isFinite(part) || part < 0)) return '0.1.1';
    parts[2] += 1;
    return parts.join('.');
  }
  async generateVersionNow(options = {}) {
    const api = this.methodEditorApi();
    if (!api?.generateVersion || !api?.registerGeneratedMethod) { this.fireToast(this.backendUnavailable()); return null; }
    try {
      if (!options.defaultLabel && !this.hasUnsavedMethodEdits()) {
        this.fireToast('No method edits to save');
        return null;
      }
      this.setState({ backendBusy:true, backendStatusText:'Saving method...', topMenu:null });
      const draft = await this.saveControlledModulusDraft();
      let validation = null;
      if (api.validateDraft) {
        const validationData = this.apiData(await api.validateDraft({ draft_id:draft.draft_id, draft_path:draft.draft_path }), 'Validate draft');
        validation = validationData.validation || null;
        if (validation && validation.loadable === false) throw new Error('Draft validation failed');
      }
      const targetVersion = this.nextTargetVersion();
      const generatedData = this.apiData(await api.generateVersion({ draft_id:draft.draft_id, draft_path:draft.draft_path, targetVersion }), 'Generate version');
      const generated = generatedData.generated_method;
      if (!generated?.method_path) throw new Error('Generated method response missing method path');
      const registerData = this.apiData(await api.registerGeneratedMethod({ method_path:generated.method_path }), 'Register generated method');
      const option = this.methodOptionFromBackend(generated);
      if (!option) throw new Error('Generated method response missing method id');
      if (options.defaultLabel) option.label = options.defaultLabel;
      option.generated = true;
      option.canonical = false;
      option.editable = true;
      option.deletable = true;
      if (options.defaultLabel && api.renameMethod) {
        try {
          const renameData = this.apiData(await api.renameMethod({
            method_id: option.method_id || option.id,
            method_path: generated.method_path,
            label: options.defaultLabel,
          }), 'Rename method');
          const renamedOption = this.methodOptionFromBackend(renameData.method || renameData.registry_entry || renameData);
          if (renamedOption?.label) option.label = renamedOption.label;
        } catch (renameError) {
          this.fireToast(renameError?.message || 'Method saved; rename failed');
        }
      }
      this.setState(st => {
        const methods = [...st.methods.filter(m => m.id !== option.id), option];
        return {
          methods,
          methodId:option.id,
          backendMode:true,
          backendBusy:false,
          backendDraft:null,
          backendGeneratedMethod:generated,
          backendRegistered:registerData.registry_entry || null,
          backendValidation:generatedData.validation || validation,
          backendStatusText:'Saved method v' + option.version,
          methodDirty:false,
          menuOpen:false,
          topMenu:null,
        };
      });
      this.fireToast('Saved method v' + option.version);
      return generated;
    } catch (error) {
      return this.handleBackendError(error, 'Generate version failed');
    }
  }
  async exportGeneratedMethodNow() {
    const api = this.methodEditorApi();
    if (!api?.exportMethodPackage) { this.fireToast(this.backendUnavailable()); return null; }
    const method = this.currentMethodOption();
    const methodPath = this.state.backendGeneratedMethod?.method_path || this.methodPathForOption(method);
    if (!methodPath) { this.fireToast('Generate a method before export'); return null; }
    try {
      this.setState({ backendBusy:true, backendStatusText:'Exporting method package...', topMenu:null });
      const defaultName = ((method?.method_id || method?.id || 'method_package') + '.zip').replace(/[^A-Za-z0-9_.-]+/g, '_');
      const data = this.apiData(await api.exportMethodPackage({ method_path:methodPath, default_name:defaultName }), 'Export method package');
      const exported = data.export || {};
      const exportName = exported.export_name || exported.archive_name || 'method package';
      const target = exported.export_path || exportName;
      this.setState({ backendBusy:false, backendExport:exported, backendStatusText:'Exported to ' + target });
      this.fireToast('Exported to ' + target);
      return exported;
    } catch (error) {
      return this.handleBackendError(error, 'Method package export failed');
    }
  }
  async openMethodPackageNow() {
    const api = this.methodEditorApi();
    if (!api?.openMethodPackage) { this.fireToast(this.backendUnavailable()); return null; }
    try {
      this.setState({ backendMode:true, backendBusy:true, backendStatusText:'Opening method package...', topMenu:null });
      const data = this.apiData(await api.openMethodPackage({ register:true }), 'Open method package');
      const generated = data.generated_method || data.method || data.imported_method;
      const option = this.methodOptionFromBackend(generated);
      if (!option) throw new Error('Opened method package response missing method id');
      option.generated = true;
      option.canonical = false;
      option.editable = true;
      option.deletable = true;
      this.setState(st => ({
        methods:[...st.methods.filter(m => m.id !== option.id), option],
        methodId:option.id,
        backendMode:true,
        backendBusy:false,
        backendDraft:null,
        backendGeneratedMethod:generated,
        backendRegistered:data.registry?.registry_entry || null,
        backendStatusText:'Opened ' + (option.label || option.id),
        menuOpen:false,
        topMenu:null,
      }));
      this.fireToast('Opened ' + (option.label || option.id));
      return generated;
    } catch (error) {
      return this.handleBackendError(error, 'Method package open failed');
    }
  }
  deleteLocalMethodNow(method) {
    this.setState(st => {
      if (st.methods.length <= 1) return {};
      const mm = st.methods.filter(x => x.id !== method.id);
      const methodId = st.methodId === method.id ? mm[0].id : st.methodId;
      return { methods:mm, methodId };
    });
  }
  async deleteMethodNow(method) {
    const api = this.methodEditorApi();
    if (!this.state.backendMode || !api?.deleteMethod) { this.deleteLocalMethodNow(method); return null; }
    if (!(method?.deletable || method?.generated)) { this.fireToast('Reference methods cannot be deleted'); return null; }
    const methodPath = method.method_path || method.method?.method_path;
    try {
      this.setState({ backendBusy:true, backendStatusText:'Deleting method...', topMenu:null });
      const data = this.apiData(await api.deleteMethod({ method_id:method.method_id || method.id, method_path:methodPath }), 'Delete method');
      let nextId = null;
      this.setState(st => {
        const methods = st.methods.filter(item => item.id !== method.id);
        nextId = st.methodId === method.id ? methods[0]?.id || null : st.methodId;
        return {
          methods,
          methodId:nextId,
          backendBusy:false,
          backendDraft:null,
          backendGeneratedMethod:st.backendGeneratedMethod?.method_id === method.id ? null : st.backendGeneratedMethod,
          backendStatusText:'Deleted ' + (data.method_id || method.label || 'method'),
          menuOpen:false,
        };
      });
      if (nextId) await this.loadBackendMethod(nextId);
      this.fireToast('Deleted ' + (data.method_id || method.label || 'method'));
      return data;
    } catch (error) {
      return this.handleBackendError(error, 'Method delete failed');
    }
  }
`;

const renameIconTemplateSource = `            <span onClick="{{ m.onStartRename }}" title="Rename method" style="display:inline-flex; align-items:center; padding:4px; border-radius:4px; cursor:pointer;">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#a09a8e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z"></path></svg>
            </span>`;

const renameIconTemplateBridge = `            <sc-if value="{{ m.canRename }}" hint-placeholder-val="{{ true }}">
            <span onClick="{{ m.onStartRename }}" title="Rename method" style="display:inline-flex; align-items:center; padding:4px; border-radius:4px; cursor:pointer;">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#a09a8e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z"></path></svg>
            </span>
            </sc-if>`;

export function withBackendMethodEditorTemplate(template) {
  let bridged = replaceOnce(
    template,
    '<button style="border:1px solid {{ genBorder }}; background:{{ genBg }}; color:{{ genColor }}; font-family:inherit; font-size:13px; font-weight:600; padding:9px 18px; border-radius:4px; cursor:{{ genCursor }}; display:inline-flex; align-items:center; gap:8px;">\u25b6 Generate new method version</button>',
    '<button onClick="{{ saveMethod }}" aria-disabled="{{ saveDisabled }}" title="{{ saveTitle }}" style="border:1px solid {{ genBorder }}; background:{{ genBg }}; color:{{ genColor }}; font-family:inherit; font-size:13px; font-weight:600; padding:9px 18px; border-radius:4px; cursor:{{ genCursor }}; pointer-events:{{ savePointerEvents }}; display:inline-flex; align-items:center; gap:8px;">\u2713 Save method</button>'
  );
  bridged = replaceOnce(
    bridged,
    '<span class="mono" style="font-size:11.5px; color:#8a93a0;">CAG-CF-Modied-ULV20.mtdp</span>',
    ''
  );
  bridged = replaceOnce(
    bridged,
    '<button onClick="{{ toggleMenu }}" onDoubleClick="{{ startRenameCurrent }}" title="Click to switch \u00b7 double-click to rename"',
    '<button onClick="{{ toggleMenu }}" onDoubleClick="{{ renameCurrentFromSelector }}" title="Click to switch \u00b7 double-click to rename"'
  );
  bridged = replaceOnce(
    bridged,
    '<span onClick="{{ m.onSelect }}" style="display:flex; align-items:center; gap:9px; flex:1; cursor:pointer;">',
    '<span onClick="{{ m.onSelect }}" onDoubleClick="{{ m.onStartRename }}" title="{{ m.title }}" style="display:flex; align-items:center; gap:9px; flex:1; cursor:pointer;">'
  );
  bridged = replaceOnce(
    bridged,
    '<span style="font-size:12px; color:#6e7a86;">Stress\u2013strain</span>',
    '<span title="Stress\u2013strain is derived from the source data and is not edited here" style="font-size:12px; color:#8f98a3; background:#eef1f4; border:1px solid #d8dde3; border-radius:999px; padding:3px 10px; cursor:not-allowed;">Stress\u2013strain</span>'
  );
  bridged = replaceOnce(
    bridged,
    '<div style="position:absolute; top:-10px; left:50%; transform:translateX(-50%); z-index:40; background:#fff; border:1px solid #e3e7eb; border-radius:10px; box-shadow:0 16px 44px rgba(40,35,25,0.17); padding:16px 22px 20px;">',
    '<div style="position:absolute; top:-10px; left:50%; transform:translateX(-50%); z-index:40; width:min(884px, calc(100vw - 96px)); max-width:calc(100vw - 96px); background:#fff; border:1px solid #e3e7eb; border-radius:10px; box-shadow:0 16px 44px rgba(40,35,25,0.17); padding:12px 16px 16px; overflow:hidden;">'
  );
  bridged = replaceOnce(
    bridged,
    '<div style="font-size:10px; letter-spacing:0.1em; text-transform:uppercase; color:#a09a8e; font-weight:600; margin-bottom:12px;">Analysis pipeline \u2014 how the data is processed, in order \u00b7 click an editable box</div>\n          <div style="width:884px;">',
    '<div style="font-size:9px; letter-spacing:0.1em; text-transform:uppercase; color:#a09a8e; font-weight:700; margin-bottom:10px;">Pipeline map \u00b7 editable boxes match the compact strip</div>\n          <div style="width:100%; min-width:0;">'
  );
  bridged = replaceOnce(
    bridged,
    '<div style="flex:0 0 276px; border:1px solid #e3e7eb; border-radius:8px; background:#fafbfc; padding:8px 13px;">\n            <div style="font-size:12.5px; font-weight:600;">Data entry point</div>\n            <div style="font-size:10.5px; color:#5a6675; margin-top:1px;">load \u00b7 strain \u00b7 geometry \u2192 area \u00b7 mean strain</div>\n          </div>',
    '<div style="flex:1 1 0; min-width:0; border:1px solid #e3e7eb; border-radius:8px; background:#fafbfc; padding:8px 13px;">\n            <div style="font-size:12.5px; font-weight:600;">Data entry point</div>\n            <div style="font-size:10.5px; color:#5a6675; margin-top:1px;">load \u00b7 strain \u00b7 geometry \u2192 area \u00b7 mean strain</div>\n          </div>'
  );
  bridged = replaceOnce(
    bridged,
    '<div style="flex:0 0 276px; border:1.5px solid #c3cad2; border-radius:8px; background:#fff; padding:8px 13px;">\n            <div style="font-size:12.5px; font-weight:600;">Stress\u2013strain</div>\n            <div style="font-size:10.5px; color:#5a6675; margin-top:1px;">bounded curve</div>\n          </div>',
    '<div title="Stress\u2013strain is derived from the source data and is not editable here" style="flex:1 1 0; min-width:0; border:1px solid #d8dde3; border-radius:8px; background:#eef1f4; padding:8px 13px; cursor:not-allowed;">\n            <div style="font-size:12.5px; font-weight:600; color:#8f98a3;">Stress\u2013strain</div>\n            <div style="font-size:10.5px; color:#9aa3ad; margin-top:1px;">derived curve \u00b7 read-only</div>\n          </div>'
  );
  bridged = replaceOnce(
    bridged,
    '<svg viewBox="0 0 884 46" width="884" height="46" style="position:absolute; inset:0;">',
    '<svg viewBox="0 0 884 46" width="100%" height="46" preserveAspectRatio="none" style="position:absolute; inset:0;">'
  );
  bridged = replaceOnce(
    bridged,
    '<div style="flex:0 0 276px; border:1px solid #e3e7eb; border-radius:8px; background:#fafbfc; padding:8px 14px;">\n            <div style="font-size:12.5px; font-weight:600; color:#5a6675;">Strength</div>\n            <div style="font-size:10.5px; color:#a09a8e; margin-top:2px;">max load \u2192 strength \u2192 failure strain</div>\n          </div>',
    '<div style="flex:1 1 0; min-width:0; border:1px solid #e3e7eb; border-radius:8px; background:#fafbfc; padding:8px 14px;">\n            <div style="font-size:12.5px; font-weight:600; color:#5a6675;">Strength</div>\n            <div style="font-size:10.5px; color:#a09a8e; margin-top:2px;">max load \u2192 strength \u2192 failure strain</div>\n          </div>'
  );
  bridged = replaceOnce(
    bridged,
    'Tune an analysis setting, then generate a new version',
    'Tune an analysis setting, then save a method version'
  );
  bridged = replaceOnce(
    bridged,
    'Generate commits the {{ changeCount }} change(s) listed below \u00b7 picked up by the Method Wizard on next run',
    'Save commits the {{ changeCount }} change(s) listed below \u00b7 picked up by Method Analysis on next run'
  );
  bridged = replaceOnce(
    bridged,
    'identical to v0.1.0 \u2014 nothing to generate yet',
    'identical to v0.1.0 \u2014 nothing to save yet'
  );
  bridged = replaceOnce(bridged, renameIconTemplateSource, renameIconTemplateBridge);
  bridged = replaceOnce(
    bridged,
    'Double-click a method, or use \u270e, to rename.',
    'Double-click an editable method, or use \u270e, to rename. ISO reference stays read-only.'
  );
  return bridged;
}

export function withBackendMethodEditorLogic(logic) {
  let bridged = logic;
  bridged = replaceOnce(
    bridged,
    '  componentDidMount() {\n    this._onKey = (e) => {',
    '  componentDidMount() {\n    this.loadBackendMethods();\n    this._onKey = (e) => {'
  );
  bridged = replaceOnce(
    bridged,
    "    nameDraft: '',",
    "    nameDraft: '',\n    methodDirty: false,"
  );
  bridged = replaceOnce(
    bridged,
    "      if (meta && (e.key === 'n' || e.key === 'N')) { e.preventDefault(); this.createMethodNow(); return; }\n      if (meta && (e.key === 'p' || e.key === 'P')) { e.preventDefault(); this.setState(st => ({ pipeExpanded: !st.pipeExpanded, topMenu:null })); return; }",
    "      if (meta && (e.key === 'n' || e.key === 'N')) { e.preventDefault(); this.createMethodNow(); return; }\n      if (meta && (e.key === 's' || e.key === 'S')) { e.preventDefault(); this.saveMethodIfDirtyNow(); return; }\n      if (meta && (e.key === 'w' || e.key === 'W')) { e.preventDefault(); this.requestCloseWindow(e); return; }\n      if (meta && (e.key === 'p' || e.key === 'P')) { e.preventDefault(); this.setState(st => ({ pipeExpanded: !st.pipeExpanded, topMenu:null })); return; }"
  );
  bridged = replaceAnyExactCount(
    bridged,
    ["this.fireToast('Generating new method version\u2026')", "this.fireToast('Generating new method version\\u2026')"],
    'this.generateVersionNow()',
    2
  );
  bridged = replaceAnyExactCount(
    bridged,
    ["this.fireToast('Validating draft\u2026')", "this.fireToast('Validating draft\\u2026')"],
    'this.validateDraftNow()',
    2
  );
  bridged = replaceOnce(bridged, createMethodNowSource, createMethodNowBridge);
  bridged = replaceOnce(bridged, renameCurrentNowSource, renameCurrentNowBridge);
  bridged = replaceOnce(
    bridged,
    '\n  fireToast(msg) { clearTimeout(this._tt); this.setState({ toast: msg, topMenu:null }); this._tt = setTimeout(() => this.setState({ toast:null }), 1900); }\n\n  renderVals() {',
    `\n  fireToast(msg) { clearTimeout(this._tt); this.setState({ toast: msg, topMenu:null }); this._tt = setTimeout(() => this.setState({ toast:null }), 1900); }\n${backendMethods}\n  renderVals() {`
  );
  bridged = replaceOnce(bridged, 'const canDel = s.methods.length > 1;', 'const canDel = s.methods.length > 1;');
  bridged = replaceOnce(
    bridged,
    'label: m.label, version: m.version, canDel,',
    "label: m.label, version: m.version, canDel: s.backendMode ? !!(m.deletable || m.generated) : canDel, canRename: s.backendMode ? !!(m.editable || m.generated) : true, title: (s.backendMode && !(m.editable || m.generated)) ? 'Reference method is read-only' : 'Double-click to rename editable method',"
  );
  bridged = replaceOnce(
    bridged,
    'onStartRename: () => this.setState({ editingNameId: m.id, nameDraft: m.label }),',
    'onStartRename: (e) => { e?.preventDefault?.(); e?.stopPropagation?.(); this.startRenameMethod(m); },'
  );
  bridged = replaceOnce(
    bridged,
    'startRenameCurrent: () => this.setState({ menuOpen:true, editingNameId: cur.id, nameDraft: cur.label }),',
    'startRenameCurrent: () => this.startRenameMethod(cur),'
  );
  bridged = replaceOnce(
    bridged,
    'onSelect: () => this.setState({ methodId: m.id, menuOpen: false }),',
    'onSelect: (e) => { e?.stopPropagation?.(); this.selectMethodNow(m); },'
  );
  bridged = replaceOnce(
    bridged,
    "onDelete: () => this.setState(st => {\n        if (st.methods.length <= 1) return {};\n        const mm = st.methods.filter(x => x.id !== m.id);\n        const methodId = st.methodId === m.id ? mm[0].id : st.methodId;\n        return { methods: mm, methodId };\n      }),",
    'onDelete: () => this.deleteMethodNow(m),'
  );
  bridged = replaceOnce(
    bridged,
    "mkItem('Open package\u2026', 'Ctrl+O', () => this.fireToast('Open package\u2026 (demo)')),",
    "mkItem('Import package\u2026', 'Ctrl+O', () => this.openMethodPackageNow()),"
  );
  bridged = replaceOnce(
    bridged,
    "mkItem('Save draft', 'Ctrl+S', () => this.fireToast('Draft saved')),",
    "mkItem('Save method', 'Ctrl+S', () => this.saveMethodIfDirtyNow(), !this.hasUnsavedMethodEdits()),"
  );
  bridged = replaceOnce(
    bridged,
    "mkItem('Export\u2026', 'Ctrl+E', () => this.fireToast('Export\u2026 (demo)')),",
    "mkItem('Export\u2026', 'Ctrl+E', () => this.exportGeneratedMethodNow()),"
  );
  bridged = replaceOnce(
    bridged,
    "mkItem('Close', 'Ctrl+W', () => this.fireToast('Close (demo)')),",
    "mkItem('Close', 'Ctrl+W', () => this.requestCloseWindow()),"
  );
  bridged = replaceOnce(
    bridged,
    "createMethod: () => this.setState(st => { const n = st.newSeq; const id = 'draft_' + n; const label = 'New method ' + n; return { methods:[...st.methods, { id, label, version:'0.1.0' }], methodId:id, newSeq:n+1, menuOpen:true, editingNameId:id, nameDraft:label }; }),",
    'createMethod: () => this.createMethodNow(),'
  );
  bridged = replaceOnce(
    bridged,
    '      menus, anyMenuOpen: !!tm, closeMenus: () => this.setState({ topMenu:null }),',
    '      menus, saveMethod: () => this.saveMethodIfDirtyNow(), saveDisabled: !this.hasUnsavedMethodEdits(), saveTitle: this.hasUnsavedMethodEdits() ? \'Save method edits\' : \'No method edits to save\', savePointerEvents: this.hasUnsavedMethodEdits() ? \'auto\' : \'none\', anyMenuOpen: !!tm, closeMenus: () => this.setState({ topMenu:null }),'
  );
  bridged = replaceOnce(
    bridged,
    "const baseBox = { flex:'0 0 276px', borderRadius:'8px', padding:'8px 13px', cursor:'pointer', position:'relative' };",
    "const baseBox = { flex:'1 1 0', minWidth:'0', borderRadius:'8px', padding:'8px 13px', cursor:'pointer', position:'relative' };"
  );
  bridged = replaceOnce(
    bridged,
    "const baseRes = { flex:'0 0 276px', borderRadius:'8px', padding:'8px 14px', cursor:'pointer', position:'relative' };",
    "const baseRes = { flex:'1 1 0', minWidth:'0', borderRadius:'8px', padding:'8px 14px', cursor:'pointer', position:'relative' };"
  );
  bridged = replaceOnce(
    bridged,
    "      { id:'generate', label:'Generate', items:[\n        mkItem('Validate draft', 'Ctrl+Enter', () => this.validateDraftNow()),\n        mkItem('Generate new version', 'Ctrl+G', () => this.generateVersionNow()),\n      ]},",
    "      { id:'generate', label:'Save', items:[\n        mkItem('Validate draft', 'Ctrl+Enter', () => this.validateDraftNow()),\n        mkItem('Save method', 'Ctrl+S', () => this.saveMethodIfDirtyNow(), !this.hasUnsavedMethodEdits()),\n      ]},"
  );
  bridged = replaceOnce(
    bridged,
    "mkItem('About Method Editor', '', () => this.fireToast('Method Editor · mtdp v0.2.0')),",
    "mkItem('About Method Editor', '', () => { this.setState({ topMenu:null }); window.__openMethodGuidelines?.(); }),"
  );
  bridged = replaceOnce(
    bridged,
    "      { k:'Ctrl+Enter', d:'Validate draft' },\n      { k:'Ctrl+G', d:'Generate new method version' },",
    "      { k:'Ctrl+Enter', d:'Validate draft' },\n      { k:'Ctrl+S', d:'Save method' },"
  );
  bridged = replaceOnce(
    bridged,
    "    const commitName = () => this.setState(st => {\n      if (st.editingNameId == null) return {};\n      const nm = (st.nameDraft || '').trim();\n      const methods = nm ? st.methods.map(x => x.id === st.editingNameId ? { ...x, label: nm } : x) : st.methods;\n      return { methods, editingNameId: null };\n    });",
    "    const commitName = () => this.commitMethodNameNow();"
  );
  bridged = replaceOnce(
    bridged,
    "value: s.startStrain, onInput: (e) => this.setState({ startStrain: e.target.value }),",
    "value: s.startStrain, onInput: (e) => this.markMethodDirty({ startStrain: e.target.value }),"
  );
  bridged = replaceOnce(
    bridged,
    "value: s.endStrain, onInput: (e) => this.setState({ endStrain: e.target.value }),",
    "value: s.endStrain, onInput: (e) => this.markMethodDirty({ endStrain: e.target.value }),"
  );
  bridged = replaceOnce(
    bridged,
    "label, onClick: () => this.setState(st => ({ excl: { ...st.excl, [k]: !st.excl[k] } })),",
    "label, onClick: () => this.markMethodDirty(st => ({ excl: { ...st.excl, [k]: !st.excl[k] } })),"
  );
  bridged = replaceOnce(
    bridged,
    "const setGp = (k, v) => this.setState(st => ({ gateP: { ...st.gateP, [k]: v } }));",
    "const setGp = (k, v) => this.markMethodDirty(st => ({ gateP: { ...st.gateP, [k]: v } }));"
  );
  bridged = replaceOnce(
    bridged,
    "toggle: () => this.setState(st => ({ excl: { ...st.excl, [key]: !st.excl[key] } })),",
    "toggle: () => this.markMethodDirty(st => ({ excl: { ...st.excl, [key]: !st.excl[key] } })),"
  );
  bridged = replaceOnce(
    bridged,
    "const bl = { magV:String(s.blMag), magOn:(e)=>this.setState({blMag:e.target.value}), ptsV:String(s.blPts), ptsOn:(e)=>this.setState({blPts:e.target.value}), pStyle:pillStyle(true) };",
    "const bl = { magV:String(s.blMag), magOn:(e)=>this.markMethodDirty({blMag:e.target.value}), ptsV:String(s.blPts), ptsOn:(e)=>this.markMethodDirty({blPts:e.target.value}), pStyle:pillStyle(true) };"
  );
  bridged = replaceOnce(
    bridged,
    "onToggle: () => this.setState(st => ({ trunc: { ...st.trunc, [d.key]: !st.trunc[d.key] } })),",
    "onToggle: () => this.markMethodDirty(st => ({ trunc: { ...st.trunc, [d.key]: !st.trunc[d.key] } })),"
  );
  bridged = replaceOnce(
    bridged,
    "onInput: d.hasInput ? ((e) => this.setState({ [d.valKey]: e.target.value })) : null,",
    "onInput: d.hasInput ? ((e) => this.markMethodDirty({ [d.valKey]: e.target.value })) : null,"
  );
  bridged = replaceOnce(
    bridged,
    "const setBend = (k, v) => this.setState(st => ({ bend: { ...st.bend, [k]: v } }));",
    "const setBend = (k, v) => this.markMethodDirty(st => ({ bend: { ...st.bend, [k]: v } }));"
  );
  bridged = replaceOnce(
    bridged,
    "toggleGate: () => this.setState(st => ({ gateOn: !st.gateOn })),",
    "toggleGate: () => this.markMethodDirty(st => ({ gateOn: !st.gateOn })),"
  );
  bridged = replaceOnce(
    bridged,
    "setReview: () => this.setState({ borderline:'review' }), setExclude: () => this.setState({ borderline:'exclude' }),",
    "setReview: () => this.markMethodDirty({ borderline:'review' }), setExclude: () => this.markMethodDirty({ borderline:'exclude' }),"
  );
  bridged = replaceOnce(
    bridged,
    "toggleTrunc: () => this.setState(st => ({ truncOn: !st.truncOn })),",
    "toggleTrunc: () => this.markMethodDirty(st => ({ truncOn: !st.truncOn })),"
  );
  bridged = replaceOnce(
    bridged,
    "closeWindow: (e) => { e?.stopPropagation?.(); window.desktopApi?.closeWindow?.(); },",
    "closeWindow: (e) => this.requestCloseWindow(e),"
  );
  bridged = replaceOnce(
    bridged,
    "      startRenameCurrent: () => this.startRenameMethod(cur),",
    "      startRenameCurrent: () => this.startRenameMethod(cur),\n      renameCurrentFromSelector: (e) => { e?.preventDefault?.(); e?.stopPropagation?.(); this.renameCurrentNow(); },"
  );
  bridged = replaceOnce(
    bridged,
    "dirtyLabel: anyErr ? changeCount + ' change' + (changeCount===1?'':'s') + ' \u00b7 1 field needs attention' : changesSummary,",
    "dirtyLabel: s.methodDirty ? (anyErr ? changeCount + ' change' + (changeCount===1?'':'s') + ' \u00b7 unsaved \u00b7 1 field needs attention' : changesSummary + ' \u00b7 unsaved') : (s.backendDirtyLabel || (anyErr ? changeCount + ' change' + (changeCount===1?'':'s') + ' \u00b7 1 field needs attention' : changesSummary)),"
  );
  bridged = replaceOnce(
    bridged,
    "genBg:     anyErr ? '#eff1f4' : A,\n      genColor:  anyErr ? '#a09a8e' : '#fff',\n      genBorder: anyErr ? '#e3e7eb' : A,\n      genCursor: anyErr ? 'not-allowed' : 'pointer',",
    "genBg:     (anyErr || !s.methodDirty) ? '#eff1f4' : A,\n      genColor:  (anyErr || !s.methodDirty) ? '#a09a8e' : '#fff',\n      genBorder: (anyErr || !s.methodDirty) ? '#e3e7eb' : A,\n      genCursor: (anyErr || !s.methodDirty) ? 'not-allowed' : 'pointer',"
  );
  bridged = replaceOnce(
    bridged,
    "statusText: anyErr ? 'Fix field format to continue' : 'Draft \u2014 not saved',",
    "statusText: s.backendStatusText || (anyErr ? 'Fix field format to continue' : (s.methodDirty ? 'Draft \u2014 unsaved edits' : 'No unsaved edits')),"
  );
  return bridged;
}
