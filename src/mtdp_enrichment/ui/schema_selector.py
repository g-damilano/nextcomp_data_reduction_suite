from __future__ import annotations

from mtdp_enrichment.package import MTDPSchema
from mtdp_enrichment.schemas import SchemaInference, SchemaRegistry
from mtdp_enrichment.ui.qt_compat import QtCore, QtWidgets


class SchemaSelector(QtWidgets.QWidget):
    schema_changed = QtCore.pyqtSignal(object)

    def __init__(self, registry: SchemaRegistry, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.registry = registry
        self._loaded_schema: MTDPSchema | None = None
        self.detected_label = QtWidgets.QLabel("Detected schema: none")
        self.combo = QtWidgets.QComboBox()
        self.combo.currentIndexChanged.connect(self._emit_schema)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.detected_label)
        layout.addWidget(self.combo)

        self._populate()

    def set_detected(self, inference: SchemaInference) -> None:
        self.detected_label.setText(
            f"Detected schema: {self._schema_label(inference.schema)} ({inference.confidence:.0%})"
        )
        self.clear_loaded_schema()
        self.select_schema(inference.schema)

    def set_loaded_schema(self, schema: MTDPSchema) -> None:
        self._loaded_schema = schema if not self.registry.is_current(schema) else None
        self._populate(select_schema=schema, emit=True)

    def clear_loaded_schema(self) -> None:
        if self._loaded_schema is None:
            return
        current = self.current_schema()
        self._loaded_schema = None
        self._populate(select_schema=current, emit=False)

    def select_schema(self, schema: MTDPSchema) -> None:
        if self._find_schema_index(schema) < 0:
            loaded = schema if not self.registry.is_current(schema) else self._loaded_schema
            self._populate(loaded_schema=loaded, select_schema=schema, emit=False)
        self._set_current_schema(schema, emit=True)

    def current_schema(self) -> MTDPSchema:
        return self.combo.currentData()

    def _emit_schema(self) -> None:
        schema = self.current_schema()
        if schema is not None:
            self.schema_changed.emit(schema)

    def _populate(
        self,
        *,
        loaded_schema: MTDPSchema | None = None,
        select_schema: MTDPSchema | None = None,
        emit: bool = False,
    ) -> None:
        if loaded_schema is not None:
            self._loaded_schema = loaded_schema
        legacy_schema = self._loaded_schema
        show_status_for_schema_id = legacy_schema.schema_id if legacy_schema is not None else None

        previous = select_schema or self.current_schema()
        blocked = self.combo.blockSignals(True)
        self.combo.clear()
        for schema in self.registry.selectable():
            include_status = schema.schema_id == show_status_for_schema_id
            self.combo.addItem(self._schema_label(schema, include_status=include_status), schema)
            if legacy_schema is not None and schema.schema_id == legacy_schema.schema_id:
                self.combo.addItem(self._schema_label(legacy_schema, include_status=True), legacy_schema)
        self.combo.blockSignals(blocked)

        target = previous if self._find_schema_index(previous) >= 0 else None
        if target is None and self.combo.count():
            target = self.combo.itemData(0)
        if target is not None:
            self._set_current_schema(target, emit=emit)

    def _set_current_schema(self, schema: MTDPSchema, *, emit: bool) -> None:
        index = self._find_schema_index(schema)
        if index < 0:
            return
        if emit:
            if self.combo.currentIndex() == index:
                self._emit_schema()
            else:
                self.combo.setCurrentIndex(index)
            return
        blocked = self.combo.blockSignals(True)
        self.combo.setCurrentIndex(index)
        self.combo.blockSignals(blocked)

    def _find_schema_index(self, schema: MTDPSchema | None) -> int:
        if schema is None:
            return -1
        for index in range(self.combo.count()):
            item = self.combo.itemData(index)
            if item.schema_id == schema.schema_id and item.schema_version == schema.schema_version:
                return index
        return -1

    def _schema_label(self, schema: MTDPSchema, *, include_status: bool = False) -> str:
        label = f"{schema.display_label} - v{schema.schema_version}"
        if include_status:
            label = f"{label} - {self.registry.effective_status(schema)}"
        return label
