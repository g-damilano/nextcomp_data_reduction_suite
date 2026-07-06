from __future__ import annotations

from collections.abc import Callable

from mtdp_enrichment.ui.qt_compat import QtGui, QtWidgets


def install_menu_bar(window: QtWidgets.QMainWindow) -> dict[str, QtGui.QAction]:
    actions: dict[str, QtGui.QAction] = {}
    bar = window.menuBar()

    def make_action(
        key: str,
        text: str,
        slot: Callable[[], None] | Callable[[], bool],
        *,
        shortcut: str | None = None,
        enabled: bool = True,
    ) -> QtGui.QAction:
        action = QtGui.QAction(text, window)
        if shortcut:
            action.setShortcut(QtGui.QKeySequence(shortcut))
        action.setEnabled(enabled)
        action.triggered.connect(lambda _checked=False: slot())
        actions[key] = action
        return action

    file_menu = bar.addMenu("&File")
    file_menu.addAction(make_action("open_folder", "Select source folder...", window.choose_folder, shortcut="Ctrl+O"))
    file_menu.addAction(make_action("open_package", "Open MTDP package...", window.open_existing_package))
    file_menu.addAction(make_action("propose_bundles", "Propose groups", window.propose_folder_bundles, shortcut="Ctrl+R"))
    file_menu.addSeparator()
    file_menu.addAction(make_action("validate_selected", "Validate selected group", window.validate_selected_bundle))
    file_menu.addAction(make_action("export_selected", "Export selected group", window.export_selected_bundle, shortcut="Ctrl+S"))
    file_menu.addAction(make_action("export_all", "Export all ready groups", window.export_all_ready_bundles))
    file_menu.addSeparator()
    file_menu.addAction(make_action("exit", "Exit", window.close, shortcut="Ctrl+Q"))

    edit_menu = bar.addMenu("&Edit")
    edit_menu.addAction(make_action("create_bundle", "Create new group...", window.bundle_builder.prompt_create_bundle))
    edit_menu.addAction(make_action("rename_bundle", "Rename selected group...", window.bundle_builder.rename_selected_bundle))
    edit_menu.addAction(make_action("delete_empty_bundle", "Delete selected empty group", window.bundle_builder.delete_selected_empty_bundle))
    edit_menu.addAction(make_action("remove_bundle", "Remove selected group and unassign runs", window.bundle_builder.remove_selected_bundle_to_unassigned))
    edit_menu.addSeparator()
    edit_menu.addAction(make_action("move_run", "Move selected run to group...", window.bundle_builder.move_selected_run_dialog))
    edit_menu.addAction(make_action("exclude_run", "Unassign selected run", window.bundle_builder.exclude_selected_run))
    edit_menu.addAction(make_action("restore_run", "Restore unassigned run...", window.bundle_builder.include_selected_run))
    edit_menu.addSeparator()
    edit_menu.addAction(make_action("rematch_yaml", "Review / re-match YAML...", window.rematch_selected_run_yaml))

    view_menu = bar.addMenu("&View")
    view_menu.addAction(make_action("expand_selected", "Expand selected group", window.expand_selected_bundle))
    view_menu.addAction(make_action("collapse_selected", "Collapse selected group", window.collapse_selected_bundle))
    view_menu.addAction(make_action("expand_all", "Expand all groups", window.bundle_builder.expand_all))
    view_menu.addAction(make_action("collapse_all", "Collapse all groups", window.bundle_builder.collapse_all))
    view_menu.addSeparator()
    view_menu.addAction(make_action("activity_log", "Activity Log", window.show_activity_log))
    view_menu.addSeparator()
    view_menu.addAction(make_action("refresh_index", "Refresh folder index", window.refresh_folder_index))

    bundle_menu = bar.addMenu("&Group")
    bundle_menu.addAction(make_action("bundle_create", "Create group...", window.bundle_builder.prompt_create_bundle))
    bundle_menu.addAction(make_action("bundle_rename", "Rename group...", window.bundle_builder.rename_selected_bundle))
    bundle_menu.addAction(make_action("bundle_delete_empty", "Delete empty group", window.bundle_builder.delete_selected_empty_bundle))
    bundle_menu.addAction(make_action("bundle_remove", "Remove group and unassign runs", window.bundle_builder.remove_selected_bundle_to_unassigned))
    bundle_menu.addAction(make_action("bundle_merge", "Merge selected groups...", window.bundle_builder.merge_selected_bundles_dialog, enabled=False))
    bundle_menu.addAction(make_action("bundle_split", "Split group...", window.bundle_builder.split_selected_run_dialog))
    bundle_menu.addSeparator()
    bundle_menu.addAction(make_action("bundle_validate", "Validate selected group", window.validate_selected_bundle))
    bundle_menu.addAction(make_action("bundle_export", "Export selected group", window.export_selected_bundle))
    bundle_menu.addAction(make_action("bundle_export_all", "Export all ready groups", window.export_all_ready_bundles))

    run_menu = bar.addMenu("&Run")
    run_menu.addAction(make_action("run_add_raw", "Add raw file(s) to selected group...", window.add_raw_files_to_selected_group))
    run_menu.addAction(make_action("run_remove", "Remove selected run from group...", window.remove_selected_run_from_group))
    run_menu.addSeparator()
    run_menu.addAction(make_action("run_move", "Move to group...", window.bundle_builder.move_selected_run_dialog))
    run_menu.addAction(make_action("run_exclude", "Unassign from group", window.bundle_builder.exclude_selected_run))
    run_menu.addAction(make_action("run_restore", "Restore unassigned run...", window.bundle_builder.include_selected_run))
    run_menu.addSeparator()
    run_menu.addAction(make_action("run_up", "Move up", lambda: window.bundle_builder.reorder_selected_run(-1)))
    run_menu.addAction(make_action("run_down", "Move down", lambda: window.bundle_builder.reorder_selected_run(1)))
    run_menu.addSeparator()
    run_menu.addAction(make_action("run_yaml", "Review / re-match YAML...", window.rematch_selected_run_yaml))
    run_menu.addAction(make_action("run_images", "Manage image evidence...", window.open_image_evidence_dialog))

    tools_menu = bar.addMenu("&Tools")
    tools_menu.addAction(make_action("tools_yaml", "Review / re-match YAML...", window.rematch_selected_run_yaml))
    tools_menu.addAction(make_action("tools_images", "Manage run image evidence...", window.open_image_evidence_dialog))
    tools_menu.addAction(make_action("tools_supplemental", "Manage supplemental files...", window.open_supplemental_files_dialog))
    tools_menu.addAction(make_action("tools_refresh", "Refresh suggestions / folder index", window.refresh_folder_index))

    help_menu = bar.addMenu("&Help")
    help_menu.addAction(make_action("about", "About Data Reduction Pipeline", window.show_about_dialog))

    window.addActions(list(actions.values()))
    return actions
