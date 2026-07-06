from __future__ import annotations

from collections import defaultdict
import os
from pathlib import Path
from typing import Protocol

from parsing.models import ParsedSampleRecord

from mtdp_enrichment.models import EnrichedFieldValue
from mtdp_enrichment.package import MTDPSchema
from mtdp_enrichment.ui.metadata_section_panel import (
    FIELD_MARKER_LEGEND,
    importance_marker,
    is_recommended_importance,
    is_required_importance,
    metadata_section_panel_model,
)
from mtdp_enrichment.ui.qt_compat import QT_API, QtCore, QtGui, QtWidgets
from mtdp_enrichment.ui.wheel_guard import install_wheel_guard


class SuggestionProvider(Protocol):
    def suggestions(self, field_id: str, prefix: str = "", limit: int = 12) -> list[str]:
        ...


class SchemaForm(QtWidgets.QWidget):
    changed = QtCore.pyqtSignal()
    message_requested = QtCore.pyqtSignal(str)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.schema: MTDPSchema | None = None
        self._scope = "run"
        self._parsed: ParsedSampleRecord | None = None
        self._importance_filter = "all"
        self._fields = ()
        self._field_by_id: dict[str, object] = {}
        self._value_widgets: dict[str, QtWidgets.QWidget] = {}
        self._unit_widgets: dict[str, QtWidgets.QComboBox] = {}
        self._row_widgets: dict[str, tuple[QtWidgets.QWidget, QtWidgets.QWidget]] = {}
        self._touched_fields: set[str] = set()
        self._loading_values = False
        self._suggestion_provider: SuggestionProvider | None = None
        self._section_tabs: QtWidgets.QTabWidget | None = None
        self._section_tab_fields: list[tuple[str, str, tuple[object, ...], str]] = []
        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.addStretch()

    def set_suggestion_provider(self, provider: SuggestionProvider | None) -> None:
        self._suggestion_provider = provider

    def build(
        self,
        schema: MTDPSchema,
        parsed: ParsedSampleRecord | None = None,
        *,
        scope: str = "run",
        importance_filter: str = "all",
    ) -> None:
        self.schema = schema
        self._scope = scope
        self._parsed = parsed
        self._importance_filter = _normalise_importance_filter(importance_filter)
        all_fields = schema.dataset_fields if scope == "dataset" else schema.run_fields
        self._fields = tuple(field for field in all_fields if self._field_visible_for_filter(field))
        self._field_by_id = {getattr(field, "field_id", ""): field for field in self._fields}
        self._clear()
        self._value_widgets.clear()
        self._unit_widgets.clear()
        self._row_widgets.clear()
        self._touched_fields.clear()
        sections = schema.metadata_sections_for_scope(scope)
        if sections:
            panel_model = metadata_section_panel_model(schema, scope=scope)
            section_models = {section.id: section for section in panel_model.sections}
            tabs = QtWidgets.QTabWidget()
            self._section_tabs = tabs
            self._section_tab_fields = []
            for section in sections:
                section_fields = tuple(field for field in section.fields if self._field_visible_for_filter(field))
                if not section_fields:
                    continue
                page = QtWidgets.QWidget()
                form = QtWidgets.QFormLayout(page)
                form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
                for field in section_fields:
                    row_widget = self._build_row(field)
                    tooltip = self._field_tooltip(field)
                    if tooltip:
                        row_widget.setToolTip(tooltip)
                    self._add_form_row(form, field, row_widget)
                section_model = section_models.get(section.id)
                tab_label = section.label
                if section_model:
                    tab_label = self._section_tab_label(section.label, section_fields)
                index = tabs.addTab(page, tab_label)
                self._section_tab_fields.append(
                    (section.id, section.label, section_fields, section.report_section or section.ui_group)
                )
                tooltip_parts = [section.report_section or section.ui_group]
                if section_model:
                    tooltip_parts.append(section_model.completion_badge)
                tabs.setTabToolTip(index, "\n".join(part for part in tooltip_parts if part))
            if tabs.count():
                self._layout.insertWidget(self._layout.count() - 1, tabs)
                legend = QtWidgets.QLabel(FIELD_MARKER_LEGEND)
                legend.setObjectName("metadata_marker_legend")
                legend.setWordWrap(True)
                self._layout.insertWidget(self._layout.count() - 1, legend)
            if parsed is not None and scope == "run":
                self.load_parsed_defaults(parsed)
            self._refresh_conditional_fields()
            return

        grouped = defaultdict(list)
        for field in self._fields:
            grouped[field.ui_group].append(field)

        for group_name, fields in grouped.items():
            box = QtWidgets.QGroupBox(group_name)
            form = QtWidgets.QFormLayout(box)
            form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
            for field in fields:
                row_widget = self._build_row(field)
                tooltip = self._field_tooltip(field)
                if tooltip:
                    row_widget.setToolTip(tooltip)
                self._add_form_row(form, field, row_widget)
            self._layout.insertWidget(self._layout.count() - 1, box)

        if parsed is not None and scope == "run":
            self.load_parsed_defaults(parsed)
        self._refresh_conditional_fields()

    def load_parsed_defaults(self, parsed: ParsedSampleRecord) -> None:
        if self.schema is None:
            return
        token_values = {token.raw_key.strip().casefold(): token for token in parsed.preamble_tokens}
        previous = self._loading_values
        self._loading_values = True
        try:
            for field in self._fields:
                token = token_values.get((field.storage.token or "").casefold())
                if token is None:
                    continue
                self.set_field_value(field.field_id, token.coerced_value_text or token.raw_value, token.raw_unit)
            if "original_filename" in self._value_widgets:
                self.set_field_value("original_filename", parsed.source_file.name, None)
        finally:
            self._loading_values = previous

    def values(self, *, only_filled: bool = False) -> tuple[dict[str, EnrichedFieldValue], dict[str, str | None]]:
        values: dict[str, EnrichedFieldValue] = {}
        units: dict[str, str | None] = {}
        if self.schema is None:
            return values, units
        for field in self._fields:
            if not self._field_active(field):
                continue
            widget = self._value_widgets.get(field.field_id)
            if widget is None:
                continue
            value = self._read_widget(widget, field.type)
            if only_filled and (field.field_id not in self._touched_fields or value in (None, "")):
                continue
            unit_widget = self._unit_widgets.get(field.field_id)
            unit = unit_widget.currentText() if unit_widget is not None else field.standard_unit
            units[field.field_id] = unit
            values[field.field_id] = EnrichedFieldValue(value, unit, source="user")
        return values, units

    def set_field_value(self, field_id: str, value: object, unit: str | None) -> None:
        widget = self._value_widgets.get(field_id)
        if widget is None:
            return
        previous = self._loading_values
        self._loading_values = True
        try:
            if isinstance(widget, QtWidgets.QLineEdit):
                widget.setText(str(value))
            elif isinstance(widget, QtWidgets.QComboBox):
                idx = widget.findData(value)
                if idx < 0 and isinstance(value, str):
                    normalized = value.strip().casefold()
                    if normalized in {"true", "yes", "1", "valid"}:
                        idx = widget.findData(True)
                    elif normalized in {"false", "no", "0", "invalid"}:
                        idx = widget.findData(False)
                if idx < 0:
                    idx = widget.findData(str(value))
                if idx < 0:
                    idx = widget.findText(str(value))
                if idx >= 0:
                    widget.setCurrentIndex(idx)
                else:
                    widget.setCurrentIndex(0)
                self._refresh_conditional_fields()
            elif isinstance(widget, QtWidgets.QCheckBox):
                text = str(value).strip().lower()
                widget.setChecked(text in {"true", "yes", "1", "valid"})
            elif isinstance(widget, QtWidgets.QDateEdit):
                date = _qdate_from_text(str(value))
                if date.isValid():
                    widget.setDate(date)

            unit_widget = self._unit_widgets.get(field_id)
            if unit_widget is not None and unit:
                idx = unit_widget.findText(str(unit).strip().strip("()"))
                if idx >= 0:
                    unit_widget.setCurrentIndex(idx)
            self._refresh_section_tab_labels()
        finally:
            self._loading_values = previous

    def _build_row(self, field) -> QtWidgets.QWidget:
        wrapper = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)

        if field.type == "enum":
            widget = QtWidgets.QComboBox()
            widget.addItem("", "")
            display_labels = getattr(field, "display_labels", {}) or {}
            for value in field.allowed_values:
                widget.addItem(str(display_labels.get(value, _enum_display_label(value))), value)
            install_wheel_guard(widget)
            widget.currentTextChanged.connect(self.changed)
            widget.currentTextChanged.connect(lambda _text, fid=field.field_id: self._mark_touched(fid))
            widget.currentTextChanged.connect(lambda _text: self._refresh_section_tab_labels())
            widget.currentIndexChanged.connect(lambda _index: self._refresh_conditional_fields())
        elif field.type == "bool":
            widget = QtWidgets.QComboBox()
            widget.addItem("", "")
            widget.addItem("Yes", True)
            widget.addItem("No", False)
            install_wheel_guard(widget)
            widget.currentTextChanged.connect(self.changed)
            widget.currentTextChanged.connect(lambda _text, fid=field.field_id: self._mark_touched(fid))
            widget.currentTextChanged.connect(lambda _text: self._refresh_section_tab_labels())
            widget.currentIndexChanged.connect(lambda _index: self._refresh_conditional_fields())
        elif field.type == "date":
            widget = QtWidgets.QDateEdit()
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("yyyy-MM-dd")
            widget.setDate(QtCore.QDate.currentDate())
            install_wheel_guard(widget)
            widget.dateChanged.connect(self.changed)
            widget.dateChanged.connect(lambda _date, fid=field.field_id: self._mark_touched(fid))
            widget.dateChanged.connect(lambda _date: self._refresh_section_tab_labels())
        else:
            widget = QtWidgets.QLineEdit()
            if field.type == "float":
                validator = QtGui.QDoubleValidator(widget)
                validator.setBottom(float(field.validation.get("min", -1e300)))
                widget.setValidator(validator)
            pattern = field.validation.get("pattern")
            if pattern and field.type != "float":
                widget.setValidator(QtGui.QRegularExpressionValidator(QtCore.QRegularExpression(pattern), widget))
            widget.textChanged.connect(self.changed)
            widget.textChanged.connect(lambda _text, fid=field.field_id: self._mark_touched(fid))
            widget.textChanged.connect(lambda text, fid=field.field_id: self._queue_suggestions(fid, text))
            widget.textChanged.connect(lambda _text: self._refresh_section_tab_labels())
            self._attach_completer(field.field_id, widget)

        self._value_widgets[field.field_id] = widget
        layout.addWidget(widget, 1)

        if field.accepted_units:
            unit_widget = QtWidgets.QComboBox()
            unit_widget.addItems(list(field.accepted_units))
            install_wheel_guard(unit_widget)
            if field.standard_unit:
                idx = unit_widget.findText(field.standard_unit)
                if idx >= 0:
                    unit_widget.setCurrentIndex(idx)
            unit_widget.currentTextChanged.connect(self.changed)
            unit_widget.currentTextChanged.connect(lambda _text, fid=field.field_id: self._mark_touched(fid))
            unit_widget.currentTextChanged.connect(lambda _text: self._refresh_section_tab_labels())
            self._unit_widgets[field.field_id] = unit_widget
            layout.addWidget(unit_widget)
        elif field.standard_unit:
            unit_label = QtWidgets.QLabel(field.standard_unit)
            unit_label.setMinimumWidth(56)
            layout.addWidget(unit_label)

        return wrapper

    def _mark_touched(self, field_id: str) -> None:
        if not self._loading_values:
            self._touched_fields.add(field_id)

    def _read_widget(self, widget: QtWidgets.QWidget, field_type: str) -> object:
        if isinstance(widget, QtWidgets.QLineEdit):
            return widget.text().strip()
        if isinstance(widget, QtWidgets.QComboBox):
            data = widget.currentData()
            if data is None:
                return widget.currentText().strip()
            return data.strip() if isinstance(data, str) else data
        if isinstance(widget, QtWidgets.QCheckBox):
            return widget.isChecked()
        if isinstance(widget, QtWidgets.QDateEdit):
            return widget.date().toString("yyyy-MM-dd")
        return ""

    def _field_label(self, field) -> str:
        marker = self._field_marker(field)
        return f"{field.label} {marker}" if marker else str(field.label)

    def _add_form_row(self, form: QtWidgets.QFormLayout, field: object, row_widget: QtWidgets.QWidget) -> None:
        label = QtWidgets.QLabel(self._field_label(field))
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        form.addRow(label, row_widget)
        self._row_widgets[getattr(field, "field_id", "")] = (label, row_widget)

    def _field_tooltip(self, field) -> str:
        parts: list[str] = []
        if getattr(field, "description", ""):
            parts.append(str(field.description))
        if getattr(field, "report_role", ""):
            parts.append(f"Report role: {field.report_role}")
        if getattr(field, "report_importance", ""):
            parts.append(f"Report importance: {field.report_importance}")
        marker = importance_marker(field)
        if marker == "*":
            parts.append("Required for method execution or formal report completeness.")
        elif marker == "**":
            parts.append("Recommended for formal report completeness.")
        return "\n".join(parts)

    def _attach_completer(self, field_id: str, widget: QtWidgets.QLineEdit) -> None:
        if QT_API == "PySide6" and os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            widget.setProperty("field_id", field_id)
            return
        completer = QtWidgets.QCompleter([], widget)
        completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        completer.setCompletionMode(QtWidgets.QCompleter.CompletionMode.PopupCompletion)
        widget.setCompleter(completer)
        widget.setProperty("field_id", field_id)

    def _queue_suggestions(self, field_id: str, prefix: str) -> None:
        if self._suggestion_provider is None:
            return
        QtCore.QTimer.singleShot(0, lambda: self._apply_suggestions(field_id, prefix))

    def _apply_suggestions(self, field_id: str, prefix: str) -> None:
        widget = self._value_widgets.get(field_id)
        if not isinstance(widget, QtWidgets.QLineEdit) or self._suggestion_provider is None:
            return
        suggestions = self._suggestion_provider.suggestions(field_id, prefix)
        completer = widget.completer()
        if completer is not None:
            completer.setModel(QtCore.QStringListModel(suggestions, completer))

    def _refresh_section_tab_labels(self) -> None:
        if self._section_tabs is None:
            return
        for index, (_section_id, label, fields, tooltip_prefix) in enumerate(self._section_tab_fields):
            self._section_tabs.setTabText(index, self._section_tab_label(label, fields))
            self._section_tabs.setTabToolTip(index, self._section_tooltip(tooltip_prefix, fields))

    def _section_tab_label(self, label: str, fields: tuple[object, ...]) -> str:
        active_count = self._section_active_count(fields)
        return f"{label} ({self._section_present_count(fields)}/{active_count} filled)"

    def _section_tooltip(self, prefix: str, fields: tuple[object, ...]) -> str:
        active_count = self._section_active_count(fields)
        present = self._section_present_count(fields)
        required_missing = sum(
            1
            for field in fields
            if self._field_active(field)
            and self._field_missing(field)
            and self._field_required(field)
        )
        recommended_missing = sum(
            1
            for field in fields
            if self._field_active(field)
            and self._field_missing(field)
            and not self._field_required(field)
            and is_recommended_importance(getattr(field, "report_importance", ""))
        )
        parts = [prefix, f"{present}/{active_count} fields filled"]
        if required_missing:
            parts.append(f"{required_missing} required missing")
        if recommended_missing:
            parts.append(f"{recommended_missing} recommended missing")
        if not required_missing and not recommended_missing:
            parts.append("Complete")
        return "\n".join(part for part in parts if part)

    def _section_present_count(self, fields: tuple[object, ...]) -> int:
        return sum(1 for field in fields if self._field_active(field) and not self._field_missing(field))

    def _section_active_count(self, fields: tuple[object, ...]) -> int:
        return sum(1 for field in fields if self._field_active(field))

    def _field_missing(self, field: object) -> bool:
        widget = self._value_widgets.get(getattr(field, "field_id", ""))
        if widget is None:
            return True
        value = self._read_widget(widget, getattr(field, "type", "string"))
        if isinstance(widget, QtWidgets.QCheckBox):
            return not bool(value)
        return value in (None, "")

    def _field_required(self, field: object) -> bool:
        return (
            bool(getattr(field, "required", False))
            or is_required_importance(getattr(field, "report_importance", ""))
            or _condition_matches(getattr(field, "required_when", {}) or {}, self._field_value_for_condition, default=False)
        )

    def _field_marker(self, field: object) -> str:
        if self._field_required(field):
            return "*"
        if is_recommended_importance(getattr(field, "report_importance", "")):
            return "**"
        return ""

    def _field_active(self, field: object) -> bool:
        return _condition_matches(getattr(field, "visible_when", {}) or {}, self._field_value_for_condition, default=True)

    def _field_visible_for_filter(self, field: object) -> bool:
        level = self._field_importance_level(field)
        if self._importance_filter == "required":
            return level == "required"
        if self._importance_filter == "recommended":
            return level in {"required", "recommended"}
        return True

    def _field_importance_level(self, field: object) -> str:
        importance = getattr(field, "report_importance", "")
        if (
            bool(getattr(field, "required", False))
            or bool(getattr(field, "required_when", {}) or {})
            or is_required_importance(importance)
        ):
            return "required"
        if is_recommended_importance(importance):
            return "recommended"
        return "optional"

    def _field_value_for_condition(self, field_id: str) -> object:
        widget = self._value_widgets.get(field_id)
        field = self._field_by_id.get(field_id)
        if widget is None:
            return None
        return self._read_widget(widget, getattr(field, "type", "string"))

    def _refresh_conditional_fields(self) -> None:
        for field in self._fields:
            row = self._row_widgets.get(getattr(field, "field_id", ""))
            if row is None:
                continue
            visible = self._field_active(field)
            row[0].setText(self._field_label(field))
            for widget in row:
                widget.setVisible(visible)
        self._refresh_section_tab_labels()

    def _clear(self) -> None:
        self._section_tabs = None
        self._section_tab_fields = []
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()


def _qdate_from_text(text: str):
    for fmt in ("yyyy-MM-dd", "dd/MM/yyyy", "d/M/yyyy", "dd-MM-yyyy", "d-M-yyyy", "dd.MM.yyyy", "d.M.yyyy"):
        date = QtCore.QDate.fromString(text, fmt)
        if date.isValid():
            return date
    return QtCore.QDate()


def _enum_display_label(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    words = [part for part in text.replace("-", "_").split("_") if part]
    if not words:
        return ""
    initialisms = {"id", "iso", "dic"}
    labels = []
    for index, word in enumerate(words):
        lowered = word.casefold()
        if lowered in initialisms:
            labels.append(lowered.upper())
        elif lowered == "fmax":
            labels.append("Fmax")
        elif lowered in {"b1", "b2"}:
            labels.append(lowered.upper())
        elif index == 0:
            labels.append(lowered.capitalize())
        else:
            labels.append(lowered)
    return " ".join(labels)


def _condition_matches(condition: dict[str, object], value_lookup, *, default: bool) -> bool:
    if not condition:
        return default
    field_id = str(condition.get("field") or condition.get("field_id") or "").strip()
    if not field_id:
        return default
    value = value_lookup(field_id)
    if "equals" in condition:
        return _condition_text(value) == _condition_text(condition.get("equals"))
    if "in" in condition:
        raw_options = condition.get("in", ()) or ()
        options = (raw_options,) if isinstance(raw_options, str) else raw_options
        return _condition_text(value) in {_condition_text(item) for item in options}
    return value not in (None, "")


def _condition_text(value: object) -> str:
    return str(value or "").strip().casefold()


def _normalise_importance_filter(value: str) -> str:
    text = str(value or "").strip().casefold().replace("+", " ")
    if text in {"required", "required only"}:
        return "required"
    if text in {"recommended", "required recommended", "required and recommended"}:
        return "recommended"
    return "all"
