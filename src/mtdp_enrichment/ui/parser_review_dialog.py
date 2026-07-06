from __future__ import annotations

from dataclasses import dataclass

from parsing.models import ChannelRecord

from mtdp_enrichment.package import MTDPSchema
from mtdp_enrichment.ui.bundle_builder import BundleRunState
from mtdp_enrichment.ui.qt_compat import QtCore, QtWidgets
from mtdp_enrichment.units import default_unit_normaliser


CHANNEL_LIST_BY_FAMILY = {
    "load": "load_channels",
    "extension": "extension_channels",
    "displacement": "displacement_channels",
    "strain": "strain_channels",
    "stress": "stress_channels",
    "time": "time_channels",
}


@dataclass(slots=True)
class ChannelReviewRow:
    channel: ChannelRecord
    family_combo: QtWidgets.QComboBox
    unit_combo: QtWidgets.QComboBox
    status_item: QtWidgets.QTableWidgetItem
    quality_item: QtWidgets.QTableWidgetItem


class ParserReviewDialog(QtWidgets.QDialog):
    def __init__(self, run: BundleRunState, schema: MTDPSchema, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.run = run
        self.schema = schema
        self.rows: list[ChannelReviewRow] = []
        self.setWindowTitle(f"Review parsed channels - {run.run_id}")
        self.resize(820, 420)

        layout = QtWidgets.QVBoxLayout(self)
        source_label = QtWidgets.QLabel(str(run.source_path))
        source_label.setWordWrap(True)
        layout.addWidget(source_label)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Column", "Header", "Family", "Unit", "Status", "Parse quality"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._populate()

    def apply_changes(self) -> None:
        for row in self.rows:
            family = str(row.family_combo.currentData() or row.family_combo.currentText()).strip()
            unit = row.unit_combo.currentText().strip().strip("()")
            _assign_channel_family(self.run, row.channel, family)
            if unit != row.unit_combo.property("initial_unit"):
                row.channel.original_unit_text = unit or None
                row.channel.canonical_unit = None

    def accept(self) -> None:  # type: ignore[override]
        self.apply_changes()
        super().accept()

    def _populate(self) -> None:
        channels = sorted(self.run.parsed.channels.all_channels(), key=lambda item: item.source_column_index)
        self.table.setRowCount(len(channels))
        for row_index, channel in enumerate(channels):
            self.table.setItem(row_index, 0, QtWidgets.QTableWidgetItem(str(channel.source_column_index + 1)))
            self.table.setItem(row_index, 1, QtWidgets.QTableWidgetItem(channel.descriptor.original_name))

            family_combo = QtWidgets.QComboBox()
            for family in _family_choices(self.schema, channel.descriptor.family):
                family_combo.addItem(family, family)
            family_combo.setCurrentText(channel.descriptor.family)
            self.table.setCellWidget(row_index, 2, family_combo)

            unit_combo = QtWidgets.QComboBox()
            unit_combo.setEditable(True)
            unit_text = channel.original_unit_text or channel.canonical_unit or ""
            for unit in _unit_choices(self.schema, channel.descriptor.family, unit_text):
                unit_combo.addItem(unit)
            unit_combo.setCurrentText(unit_text)
            unit_combo.setProperty("initial_unit", unit_text)
            self.table.setCellWidget(row_index, 3, unit_combo)

            status_item = QtWidgets.QTableWidgetItem(_channel_status(self.schema, channel))
            self.table.setItem(row_index, 4, status_item)
            quality_item = QtWidgets.QTableWidgetItem(_parse_quality_status(channel))
            quality_item.setToolTip(_parse_quality_tooltip(channel))
            self.table.setItem(row_index, 5, quality_item)
            review_row = ChannelReviewRow(channel, family_combo, unit_combo, status_item, quality_item)
            self.rows.append(review_row)
            family_combo.currentTextChanged.connect(lambda _text, item=review_row: self._refresh_row(item))
            unit_combo.currentTextChanged.connect(lambda _text, item=review_row: self._refresh_row(item))

    def _refresh_row(self, row: ChannelReviewRow) -> None:
        family = str(row.family_combo.currentData() or row.family_combo.currentText()).strip()
        unit = row.unit_combo.currentText().strip().strip("()") or None
        row.status_item.setText(_channel_status(self.schema, row.channel, family=family, unit=unit))


def _family_choices(schema: MTDPSchema, current: str) -> list[str]:
    choices = [item.family for item in schema.expected_table]
    choices.extend(["record_id", "timestamp", "temperature", "unknown"])
    if current and current not in choices:
        choices.insert(0, current)
    return _dedupe(choices)


def _unit_choices(schema: MTDPSchema, family: str, current: str) -> list[str]:
    choices = [""]
    definition = schema.table_definition_for_family(family)
    if definition is not None:
        choices.extend(definition.accepted_units)
        if definition.standard_unit:
            choices.append(definition.standard_unit)
    if current:
        choices.insert(1, current)
    return _dedupe(choices)


def _channel_status(
    schema: MTDPSchema,
    channel: ChannelRecord,
    *,
    family: str | None = None,
    unit: str | None = None,
) -> str:
    family = family or channel.descriptor.family
    unit = unit if unit is not None else channel.original_unit_text or channel.canonical_unit
    definition = schema.table_definition_for_family(family)
    if definition is None:
        return "Auxiliary channel; exported without schema unit checks."
    normalized_unit = default_unit_normaliser.normalize_unit_text(unit)
    accepted = {default_unit_normaliser.normalize_unit_text(item) for item in definition.accepted_units}
    if definition.accepted_units and not normalized_unit:
        return f"Missing unit; assuming {definition.standard_unit or 'schema default'} unless edited."
    if definition.accepted_units and normalized_unit not in accepted:
        return "Unit is not accepted by the selected schema."
    return "OK"


def _parse_quality_status(channel: ChannelRecord) -> str:
    cells = channel.parsed_cells
    if not cells:
        return "No cell audit records"
    counts = _parse_quality_counts(channel)
    profile = channel.parse_profile.numeric_policy_id if channel.parse_profile is not None else "no profile"
    problem_count = counts["missing"] + counts["ambiguous"] + counts["invalid"] + counts["unsupported"]
    if problem_count:
        return (
            f"Parsed {counts['ok']}/{len(cells)}; "
            f"missing {counts['missing']}, invalid {counts['invalid']}, "
            f"ambiguous {counts['ambiguous']} ({profile})"
        )
    return f"Parsed {counts['ok']}/{len(cells)} ({profile})"


def _parse_quality_tooltip(channel: ChannelRecord) -> str:
    cells = channel.parsed_cells
    if not cells:
        return "Parser did not provide parsed-cell audit records for this channel."
    examples = []
    for cell in cells:
        if cell.status == "ok" and cell.normalized_text is not None:
            examples.append(f"{cell.raw_value} -> {cell.normalized_text}")
        elif cell.status != "ok":
            examples.append(f"{cell.raw_value}: {cell.diagnostic_code or cell.status}")
        if len(examples) >= 3:
            break
    return "\n".join(examples)


def _parse_quality_counts(channel: ChannelRecord) -> dict[str, int]:
    counts = {"ok": 0, "missing": 0, "ambiguous": 0, "invalid": 0, "unsupported": 0}
    for cell in channel.parsed_cells:
        counts[cell.status] = counts.get(cell.status, 0) + 1
    return counts


def _assign_channel_family(run: BundleRunState, channel: ChannelRecord, family: str) -> None:
    channels = run.parsed.channels
    for attr in set(CHANNEL_LIST_BY_FAMILY.values()) | {"unknown_channels"}:
        items = getattr(channels, attr)
        if channel in items:
            items.remove(channel)
    target_attr = CHANNEL_LIST_BY_FAMILY.get(family, "unknown_channels")
    getattr(channels, target_attr).append(channel)
    channel.descriptor.family = family


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result
