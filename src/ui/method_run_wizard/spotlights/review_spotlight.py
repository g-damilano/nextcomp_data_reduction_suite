from __future__ import annotations

import html
from dataclasses import dataclass, field

from mtdp_enrichment.ui.qt_compat import QtCore, QtWidgets
from ui.method_run_wizard.components.sparkline import BendingSparkline, CurveFamilySparkline
from ui.method_run_wizard.components.task_card import TaskCard
from ui.method_run_wizard.view_models.diagnostic_cockpit import DiagnosticCockpitView


@dataclass(slots=True)
class RunRowModel:
    run_id: str
    default_call: str
    reason: str
    is_excluded: bool
    bending_series: list[float]
    bending_peak: float | None
    bending_threshold: float | None
    bending_points_above_threshold: int | None
    bending_assessed_points: int | None
    peak_load_N: float | None
    kept_mean_load: float | None
    modulus_GPa: float | None
    kept_mean_modulus: float | None
    failure_mode: str
    narrative_html: str
    has_bending_evidence: bool = True
    evidence_kind: str = "bending"
    acceptance_flags: list[dict[str, str]] = field(default_factory=list)
    defect_labels: list[str] = field(default_factory=list)
    bending_trace_points: list[dict[str, object]] = field(default_factory=list)
    bending_assessment_window: tuple[float | None, float | None] = (None, None)
    bending_exceedance_segments: list[dict[str, object]] = field(default_factory=list)
    curve_family_points: list[dict[str, object]] = field(default_factory=list)
    curve_family_reference_points: list[dict[str, object]] = field(default_factory=list)
    curve_family_focus_run_id: str = ""
    curve_family_metric: str = ""
    curve_family_value: float | None = None
    curve_family_threshold: float | None = None
    curve_family_rank: str = ""
    curve_family_classification: str = ""
    diagnostic_cockpit: DiagnosticCockpitView | None = None
    diagnostic_cockpits: list[DiagnosticCockpitView] = field(default_factory=list)


class MetricTile(QtWidgets.QFrame):
    def __init__(
        self,
        key: str,
        value: str,
        sub: str,
        level: str = "info",
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("metricTile")
        self.setProperty("level", level)
        self.setProperty("evidence_key", key)
        self.setProperty("state", "ok")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        key_label = QtWidgets.QLabel(key.upper())
        key_label.setObjectName("metricKey")
        value_label = QtWidgets.QLabel(value)
        value_label.setObjectName("metricValue")
        value_label.setProperty("level", level)
        value_label.setWordWrap(True)
        sub_label = QtWidgets.QLabel(sub)
        sub_label.setObjectName("metricSub")
        sub_label.setWordWrap(True)

        layout.addWidget(key_label)
        layout.addWidget(value_label)
        layout.addWidget(sub_label)


class EvidencePane(QtWidgets.QFrame):
    def __init__(self, model: RunRowModel, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("evidencePane")
        self.setMinimumHeight(126)

        grid = QtWidgets.QGridLayout(self)
        grid.setContentsMargins(16, 14, 16, 14)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)

        cockpits = _model_cockpits(model)
        if len(cockpits) > 1:
            tabs = QtWidgets.QTabWidget()
            tabs.setObjectName("diagnosticCockpitTabs")
            tabs.setDocumentMode(True)
            for cockpit in cockpits:
                tabs.addTab(_DiagnosticCockpitPane(model, cockpit, show_title=True), _cockpit_tab_label(cockpit))
            grid.addWidget(tabs, 0, 0, 1, 2)
        else:
            cockpit = cockpits[0] if cockpits else None
            grid.addWidget(_DiagnosticCockpitPane(model, cockpit, show_title=False), 0, 0, 1, 2)

        narrative = QtWidgets.QLabel(model.narrative_html)
        narrative.setObjectName("evidenceNarrative")
        narrative.setWordWrap(True)
        narrative.setTextFormat(QtCore.Qt.TextFormat.RichText)
        grid.addWidget(narrative, 1, 0, 1, 2)
        if model.acceptance_flags:
            flags = QtWidgets.QFrame()
            flags.setObjectName("acceptanceFlagCluster")
            flags_layout = QtWidgets.QVBoxLayout(flags)
            flags_layout.setContentsMargins(0, 0, 0, 0)
            flags_layout.setSpacing(4)
            title = QtWidgets.QLabel(f"Acceptance findings ({len(model.acceptance_flags)})")
            title.setObjectName("acceptanceFlagTitle")
            flags_layout.addWidget(title)
            for flag in model.acceptance_flags:
                label = QtWidgets.QLabel(_flag_label(flag))
                label.setObjectName("acceptanceFlagLine")
                label.setWordWrap(True)
                label.setTextFormat(QtCore.Qt.TextFormat.RichText)
                flags_layout.addWidget(label)
            grid.addWidget(flags, 2, 0, 1, 2)


class _DiagnosticCockpitPane(QtWidgets.QFrame):
    def __init__(
        self,
        model: RunRowModel,
        cockpit: DiagnosticCockpitView | None,
        *,
        show_title: bool,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("diagnosticCockpitPane")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        if show_title and cockpit is not None:
            title = QtWidgets.QLabel(_cockpit_title(cockpit))
            title.setObjectName("diagnosticCockpitTitle")
            layout.addWidget(title)

        grid = QtWidgets.QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)
        layout.addLayout(grid)

        plot_contract = cockpit.plot_contract if cockpit is not None else None
        threshold = model.bending_threshold or 0.0
        if plot_contract is not None and plot_contract.plot_kind == "curve_family" and model.curve_family_points:
            grid.addWidget(
                CurveFamilySparkline(
                    model.curve_family_points,
                    reference_points=model.curve_family_reference_points,
                    focus_run_id=model.curve_family_focus_run_id or model.run_id,
                ),
                0,
                0,
            )
        elif plot_contract is not None and plot_contract.plot_kind == "curve_family":
            grid.addWidget(_evidence_gap_label(", ".join(plot_contract.missing_required_keys) or "plot.curve_family_curve"), 0, 0)
        elif plot_contract is not None and plot_contract.plot_kind == "bending_evidence" and model.has_bending_evidence and (model.bending_trace_points or model.bending_series):
            grid.addWidget(
                BendingSparkline(
                    model.bending_series,
                    threshold,
                    trace_points=model.bending_trace_points,
                    assessment_window=model.bending_assessment_window,
                    exceedance_segments=model.bending_exceedance_segments,
                ),
                0,
                0,
            )
        else:
            missing = ", ".join(plot_contract.missing_required_keys) if plot_contract is not None else "diagnostic.view_contract"
            grid.addWidget(_evidence_gap_label(missing), 0, 0)

        metrics = QtWidgets.QGridLayout()
        metrics.setHorizontalSpacing(8)
        metrics.setVerticalSpacing(8)
        cards = cockpit.cards if cockpit is not None else ()
        for index, card in enumerate(cards):
            tile = MetricTile(card.label, card.value, card.subtext, card.level)
            tile.setProperty("evidence_key", card.evidence_key)
            tile.setProperty("state", card.state)
            _repolish(tile)
            metrics.addWidget(tile, index // 2, index % 2)
        metrics_widget = QtWidgets.QWidget()
        metrics_widget.setLayout(metrics)
        grid.addWidget(metrics_widget, 0, 1)


def _evidence_gap_label(missing: str) -> QtWidgets.QLabel:
    empty = QtWidgets.QLabel(f"Evidence gap: missing {missing}.")
    empty.setObjectName("evidenceNarrative")
    empty.setMinimumSize(280, 86)
    empty.setWordWrap(True)
    empty.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    return empty


def _model_cockpits(model: RunRowModel) -> tuple[DiagnosticCockpitView, ...]:
    if model.diagnostic_cockpits:
        return tuple(model.diagnostic_cockpits)
    return (model.diagnostic_cockpit,) if model.diagnostic_cockpit is not None else ()


def _cockpit_tab_label(cockpit: DiagnosticCockpitView) -> str:
    plot_kind = cockpit.plot_contract.plot_kind
    if plot_kind == "bending_evidence":
        return "Bending"
    if plot_kind == "curve_family":
        return "Curve shape"
    return "Diagnostic"


def _cockpit_title(cockpit: DiagnosticCockpitView) -> str:
    return f"{_cockpit_tab_label(cockpit)} defect"


class OverrideJustifyRow(QtWidgets.QFrame):
    reason_changed = QtCore.pyqtSignal(str, str)

    def __init__(self, run_id: str, defect_labels: list[str] | None = None, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.run_id = run_id
        self.defect_labels = _normalised_defect_labels(defect_labels or [])
        self.setObjectName("overrideJustifyRow")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        label_column = QtWidgets.QVBoxLayout()
        label_column.setContentsMargins(0, 0, 0, 0)
        label_column.setSpacing(3)
        label = QtWidgets.QLabel("WHY KEEP?")
        label.setObjectName("overrideKey")
        scope = QtWidgets.QLabel(_override_scope_text(self.defect_labels))
        scope.setObjectName("overrideScope")
        scope.setWordWrap(True)
        label_column.addWidget(label)
        label_column.addWidget(scope)

        self.line_edit = QtWidgets.QLineEdit()
        defect_text = _join_defect_labels(self.defect_labels)
        self.line_edit.setPlaceholderText(f"Motivate keeping this run despite {defect_text}")
        self.line_edit.setAccessibleName(f"Override justification for {run_id}: {defect_text}")
        self.line_edit.textChanged.connect(lambda text: self.reason_changed.emit(self.run_id, text))

        layout.addLayout(label_column)
        layout.addWidget(self.line_edit, 1)


class _MainRunRow(QtWidgets.QFrame):
    row_clicked = QtCore.pyqtSignal()
    keep_clicked = QtCore.pyqtSignal()
    remove_clicked = QtCore.pyqtSignal()

    def __init__(self, model: RunRowModel, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.model = model
        self.setObjectName("acceptanceMainRow")
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        self._run = QtWidgets.QLabel(model.run_id)
        self._run.setObjectName("acceptRun")
        self._call = QtWidgets.QLabel(model.default_call)
        self._call.setObjectName("acceptCall")
        self._defects = QtWidgets.QLabel(_defect_scope_text(model))
        self._defects.setObjectName("acceptDefects")
        self._defects.setWordWrap(False)
        self._defects.setToolTip(f"Override covers: {_defect_scope_text(model)}")
        self._reason = QtWidgets.QLabel(model.reason)
        self._reason.setObjectName("acceptReason")
        self._reason.setWordWrap(False)
        self._reason.setToolTip(model.reason)

        defect_text = _join_defect_labels(_model_defect_labels(model))
        self.keep_button = QtWidgets.QPushButton("Keep run")
        self.keep_button.setProperty("class", "subtle")
        self.keep_button.setAccessibleName(f"Keep {model.run_id}; override {defect_text}")
        self.keep_button.setToolTip(f"Keep this run and override: {defect_text}")
        self.remove_button = QtWidgets.QPushButton("Remove run")
        self.remove_button.setProperty("class", "subtle")
        self.remove_button.setAccessibleName(f"Remove {model.run_id}; keep default for {defect_text}")
        self.remove_button.setToolTip(f"Remove this run for: {defect_text}")
        self.keep_button.clicked.connect(self.keep_clicked.emit)
        self.remove_button.clicked.connect(self.remove_clicked.emit)

        layout.addWidget(self._run, 0)
        layout.addWidget(self._call, 0)
        layout.addWidget(self._defects, 1)
        layout.addWidget(self._reason, 1)
        layout.addWidget(self.keep_button)
        layout.addWidget(self.remove_button)

    def mousePressEvent(self, event: object) -> None:
        button = event.button() if hasattr(event, "button") else None
        if button == QtCore.Qt.MouseButton.LeftButton:
            self.row_clicked.emit()
        super().mousePressEvent(event)

    def set_decision_highlight(self, keep: bool | None) -> None:
        self.setProperty("decision", "keep" if keep is True else "remove" if keep is False else "")
        self.keep_button.setProperty("class", "primary" if keep is True else "subtle")
        self.remove_button.setProperty("class", "primary" if keep is False else "subtle")
        self.style().unpolish(self)
        self.style().polish(self)
        for button in (self.keep_button, self.remove_button):
            button.style().unpolish(button)
            button.style().polish(button)


class AcceptanceRow(QtWidgets.QFrame):
    keep_clicked = QtCore.pyqtSignal(str)
    remove_clicked = QtCore.pyqtSignal(str)
    expanded = QtCore.pyqtSignal(str, bool)

    def __init__(self, model: RunRowModel, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.model = model
        self.setObjectName("acceptanceRow")
        self._open = False

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._row = _MainRunRow(model)
        self._row.row_clicked.connect(self._toggle)
        self._row.keep_clicked.connect(lambda: self.keep_clicked.emit(model.run_id))
        self._row.remove_clicked.connect(lambda: self.remove_clicked.emit(model.run_id))

        self._detail = EvidencePane(model)
        self._detail.setVisible(False)

        self.justify = OverrideJustifyRow(model.run_id, model.defect_labels)
        self.justify.setVisible(False)

        layout.addWidget(self._row)
        layout.addWidget(self._detail)
        layout.addWidget(self.justify)

    def set_decision(self, keep: bool | None) -> None:
        self._row.set_decision_highlight(keep)
        self.justify.setVisible(keep is True)
        if keep is False:
            self.justify.line_edit.clear()
        _notify_layout_changed(self)

    def set_expanded(self, open_: bool) -> None:
        if self._open == open_:
            return
        self._open = open_
        self._detail.setVisible(open_)
        _notify_layout_changed(self)
        self.expanded.emit(self.model.run_id, open_)

    def _toggle(self) -> None:
        self.set_expanded(not self._open)


class AcceptanceList(QtWidgets.QWidget):
    keep_clicked = QtCore.pyqtSignal(str)
    remove_clicked = QtCore.pyqtSignal(str)
    expanded = QtCore.pyqtSignal(str, bool)
    reason_changed = QtCore.pyqtSignal(str, str)

    def __init__(self, runs: list[RunRowModel] | None = None, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.rows: dict[str, AcceptanceRow] = {}
        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self.set_runs(runs or [])

    def set_runs(self, runs: list[RunRowModel]) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        self.rows = {}
        self._layout.addWidget(_make_header_row())
        if not runs:
            empty = QtWidgets.QLabel("No flagged runs require review.")
            empty.setObjectName("evidenceNarrative")
            empty.setWordWrap(True)
            empty.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self._layout.addWidget(empty)
            self._layout.addStretch(1)
            return
        for model in runs:
            row = AcceptanceRow(model)
            row.keep_clicked.connect(self.keep_clicked.emit)
            row.remove_clicked.connect(self.remove_clicked.emit)
            row.expanded.connect(self.expanded.emit)
            row.justify.reason_changed.connect(self.reason_changed.emit)
            self.rows[model.run_id] = row
            self._layout.addWidget(row)
        self._layout.addStretch(1)
        _notify_layout_changed(self)


class ReviewSpotlight(QtWidgets.QWidget):
    keep_clicked = QtCore.pyqtSignal(str)
    remove_clicked = QtCore.pyqtSignal(str)
    expanded = QtCore.pyqtSignal(str, bool)
    reason_changed = QtCore.pyqtSignal(str, str)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("reviewSpotlight")
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 8, 24, 20)
        layout.setSpacing(12)

        self.summary_strip = self._make_summary_strip()
        layout.addWidget(self.summary_strip)

        self.task = TaskCard(
            "acceptance",
            "needs you",
            "Confirm flagged runs",
            "Review the diagnostic evidence and confirm the safe default choices.",
        )
        self.list = AcceptanceList([])
        self.list.keep_clicked.connect(self.keep_clicked.emit)
        self.list.remove_clicked.connect(self.remove_clicked.emit)
        self.list.expanded.connect(self._row_expanded)
        self.list.reason_changed.connect(self.reason_changed.emit)
        self.task.set_body_widget(self.list)
        self.task.set_expanded(True)
        self.task._header._chev.setText("")
        try:
            self.task._header.clicked.disconnect(self.task._on_header_clicked)
        except (TypeError, RuntimeError):
            pass

        layout.addWidget(self.task)
        layout.addStretch(1)

    @property
    def rows(self) -> dict[str, AcceptanceRow]:
        return self.list.rows

    def set_runs(self, runs: list[RunRowModel]) -> None:
        self.list.set_runs(runs)
        _notify_layout_changed(self)

    def set_summary(
        self,
        *,
        total_runs: int,
        flagged_runs: int,
        final_runs: int,
        overrides: int,
        missing_reasons: int,
    ) -> None:
        self.total_value.setText(str(int(total_runs)))
        self.flagged_value.setText(str(int(flagged_runs)))
        self.final_value.setText(str(int(final_runs)))
        self.override_value.setText(str(int(overrides)))
        self.override_sub.setText("missing reasons" if missing_reasons else "justified overrides")
        self.override_tile.setProperty("state", "warn" if missing_reasons else "ok" if overrides else "")
        _repolish(self.override_tile)

    def set_decision(self, run_id: str, keep: bool | None) -> None:
        row = self.rows.get(run_id)
        if row is not None:
            row.set_decision(keep)

    def focus_reason(self, run_id: str) -> None:
        row = self.rows.get(run_id)
        if row is not None:
            row.justify.setVisible(True)
            row.justify.line_edit.setFocus()

    def _row_expanded(self, run_id: str, is_open: bool) -> None:
        if is_open:
            for other_id, row in self.rows.items():
                if other_id != run_id:
                    row.set_expanded(False)
        _notify_layout_changed(self)
        self.expanded.emit(run_id, is_open)

    def _make_summary_strip(self) -> QtWidgets.QFrame:
        strip = QtWidgets.QFrame()
        strip.setObjectName("reviewSummary")
        layout = QtWidgets.QHBoxLayout(strip)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        self.total_tile, self.total_value, self.total_sub = _summary_tile("TOTAL RUNS", "0", "in package")
        self.flagged_tile, self.flagged_value, self.flagged_sub = _summary_tile("FLAGGED", "0", "need review")
        self.final_tile, self.final_value, self.final_sub = _summary_tile("FINAL REPORT", "0", "selected runs")
        self.override_tile, self.override_value, self.override_sub = _summary_tile("OVERRIDES", "0", "justified overrides")
        for tile in (self.total_tile, self.flagged_tile, self.final_tile, self.override_tile):
            layout.addWidget(tile)
        return strip


def _make_header_row() -> QtWidgets.QFrame:
    row = QtWidgets.QFrame()
    row.setObjectName("acceptanceHeader")
    layout = QtWidgets.QHBoxLayout(row)
    layout.setContentsMargins(12, 8, 12, 8)
    layout.setSpacing(12)
    for text, stretch in (("RUN", 0), ("DEFAULT", 0), ("DEFECTS", 1), ("REASON", 1), ("DECISION", 0)):
        label = QtWidgets.QLabel(text)
        label.setObjectName("acceptHeaderLabel")
        layout.addWidget(label, stretch)
    return row


def _summary_tile(key: str, value: str, sub: str) -> tuple[QtWidgets.QFrame, QtWidgets.QLabel, QtWidgets.QLabel]:
    tile = QtWidgets.QFrame()
    tile.setObjectName("reviewSummaryTile")
    layout = QtWidgets.QVBoxLayout(tile)
    layout.setContentsMargins(10, 8, 10, 8)
    layout.setSpacing(2)
    key_label = QtWidgets.QLabel(key)
    key_label.setObjectName("reviewSummaryKey")
    value_label = QtWidgets.QLabel(value)
    value_label.setObjectName("reviewSummaryValue")
    sub_label = QtWidgets.QLabel(sub)
    sub_label.setObjectName("reviewSummarySub")
    layout.addWidget(key_label)
    layout.addWidget(value_label)
    layout.addWidget(sub_label)
    return tile, value_label, sub_label


def _repolish(widget: QtWidgets.QWidget) -> None:
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def _notify_layout_changed(widget: QtWidgets.QWidget) -> None:
    widget.updateGeometry()
    if widget.layout() is not None:
        widget.layout().invalidate()
        widget.layout().activate()
        widget.layout().setGeometry(widget.rect())
    parent = widget.parentWidget()
    while parent is not None:
        parent.updateGeometry()
        if parent.layout() is not None:
            parent.layout().invalidate()
            parent.layout().activate()
            parent.layout().setGeometry(parent.rect())
        parent = parent.parentWidget()


def _flag_label(flag: dict[str, str]) -> str:
    severity = html.escape(flag.get("severity", "flag"))
    category = html.escape(flag.get("category", "acceptance"))
    message = html.escape(flag.get("message", ""))
    return f"<b>{severity}</b> &middot; {category}: {message}"


def _model_defect_labels(model: RunRowModel) -> list[str]:
    labels = _normalised_defect_labels(model.defect_labels)
    if labels:
        return labels
    return _normalised_defect_labels([_cockpit_tab_label(cockpit) for cockpit in _model_cockpits(model)])


def _normalised_defect_labels(labels: list[str] | tuple[str, ...]) -> list[str]:
    normalised: list[str] = []
    for label in labels:
        text = str(label or "").strip()
        if text and text not in normalised:
            normalised.append(text)
    return normalised or ["acceptance finding"]


def _join_defect_labels(labels: list[str] | tuple[str, ...]) -> str:
    normalised = _normalised_defect_labels(labels)
    if len(normalised) == 1:
        return normalised[0]
    return " + ".join(normalised)


def _defect_scope_text(model: RunRowModel) -> str:
    labels = _model_defect_labels(model)
    return _join_defect_labels(labels)


def _override_scope_text(defect_labels: list[str]) -> str:
    return f"Motivate every override covered by this run decision: {_join_defect_labels(defect_labels)}"


def _default_call_is_keep(model: RunRowModel) -> bool:
    return str(model.default_call).strip().lower().startswith("keep")
