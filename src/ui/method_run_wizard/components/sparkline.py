from __future__ import annotations

from mtdp_enrichment.ui.qt_compat import QtCore, QtGui, QtWidgets
from ui.method_run_wizard._tokens import Color


class BendingSparkline(QtWidgets.QFrame):
    def __init__(
        self,
        series: list[float] | tuple[float, ...],
        threshold: float,
        *,
        trace_points: list[dict[str, object]] | None = None,
        assessment_window: tuple[float | None, float | None] | None = None,
        exceedance_segments: list[dict[str, object]] | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._series = [float(value) for value in series]
        self._threshold = float(threshold)
        self._trace_points = _trace_points(trace_points or [])
        self._assessment_window = assessment_window or (None, None)
        self._exceedance_segments = list(exceedance_segments or [])
        self.setMinimumSize(360 if self._trace_points else 300, 176 if self._trace_points else 132)
        self.setObjectName("bendingSparkline")

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        if self._trace_points:
            self._paint_trace_plot(painter)
            return

        y_axis_label = "Bending / %"
        left_margin = _axis_label_margin(painter, y_axis_label, minimum=56)
        rect = self.rect().adjusted(left_margin, 14, -12, -34)
        if rect.width() <= 0 or rect.height() <= 0 or not self._series:
            return

        max_value = max(max(self._series), self._threshold, 0.01) * 1.2

        def x_at(index: int) -> float:
            if len(self._series) == 1:
                return float(rect.left())
            return rect.left() + (index / (len(self._series) - 1)) * rect.width()

        def y_at(value: float) -> float:
            return rect.bottom() - (value / max_value) * rect.height()

        painter.setPen(QtGui.QPen(QtGui.QColor(Color.BORDER), 1))
        painter.drawRect(rect)

        threshold_y = y_at(self._threshold)
        threshold_pen = QtGui.QPen(QtGui.QColor(Color.WARN_BORDER), 1)
        threshold_pen.setDashPattern([4, 4])
        painter.setPen(threshold_pen)
        painter.drawLine(
            QtCore.QPointF(rect.left(), threshold_y),
            QtCore.QPointF(rect.right(), threshold_y),
        )

        painter.setPen(QtGui.QColor(Color.WARN_INK))
        painter.drawText(
            QtCore.QRectF(rect.left(), threshold_y - 18, rect.width(), 16),
            int(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter),
            f"{self._threshold:g}% threshold",
        )

        path = QtGui.QPainterPath(QtCore.QPointF(x_at(0), y_at(self._series[0])))
        for index, value in enumerate(self._series[1:], start=1):
            path.lineTo(QtCore.QPointF(x_at(index), y_at(value)))

        series_pen = QtGui.QPen(QtGui.QColor(Color.ACCENT), 2)
        painter.setPen(series_pen)
        painter.drawPath(path)

        painter.setBrush(QtGui.QColor(Color.ACCENT))
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        for index, value in enumerate(self._series):
            painter.drawEllipse(QtCore.QPointF(x_at(index), y_at(value)), 2.2, 2.2)

        painter.setPen(QtGui.QColor(Color.TEXT_3))
        painter.drawText(
            QtCore.QRectF(rect.left(), rect.bottom() + 6, rect.width(), 18),
            int(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter),
            "Point",
        )
        painter.drawText(
            QtCore.QRectF(0, rect.top(), rect.left() - 8, rect.height()),
            int(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTop),
            y_axis_label,
        )

    def _paint_trace_plot(self, painter: QtGui.QPainter) -> None:
        y_axis_label = "Bending / %"
        left_margin = _axis_label_margin(painter, y_axis_label, minimum=58)
        rect = self.rect().adjusted(left_margin, 14, -12, -34)
        if rect.width() <= 0 or rect.height() <= 0:
            return

        xs = [point[0] for point in self._trace_points]
        ys = [point[1] for point in self._trace_points]
        x_min = min(xs)
        x_max = max(xs)
        if x_max <= x_min:
            x_max = x_min + 1.0
        y_min = min(0.0, min(ys))
        y_max = max(max(ys), self._threshold, 0.01)
        if y_max <= y_min:
            y_max = y_min + 1.0
        y_max *= 1.08

        def x_at(value: float) -> float:
            return rect.left() + ((value - x_min) / (x_max - x_min)) * rect.width()

        def y_at(value: float) -> float:
            return rect.bottom() - ((value - y_min) / (y_max - y_min)) * rect.height()

        painter.setPen(QtGui.QPen(QtGui.QColor(Color.BORDER), 1))
        painter.drawRect(rect)

        lower, upper = self._assessment_window
        if lower is not None and upper is not None:
            left = max(rect.left(), min(rect.right(), x_at(min(lower, upper))))
            right = max(rect.left(), min(rect.right(), x_at(max(lower, upper))))
            painter.fillRect(
                QtCore.QRectF(left, rect.top(), max(0.0, right - left), rect.height()),
                QtGui.QColor(125, 135, 148, 32),
            )

        for segment in self._exceedance_segments:
            start = _float(segment.get("start_load_N"))
            end = _float(segment.get("end_load_N"))
            if start is None or end is None:
                continue
            left = max(rect.left(), min(rect.right(), x_at(min(start, end))))
            right = max(rect.left(), min(rect.right(), x_at(max(start, end))))
            painter.fillRect(
                QtCore.QRectF(left, rect.top(), max(0.0, right - left), rect.height()),
                QtGui.QColor(217, 95, 95, 42),
            )

        threshold_y = y_at(self._threshold)
        threshold_pen = QtGui.QPen(QtGui.QColor(Color.WARN_BORDER), 1)
        threshold_pen.setDashPattern([4, 4])
        painter.setPen(threshold_pen)
        painter.drawLine(
            QtCore.QPointF(rect.left(), threshold_y),
            QtCore.QPointF(rect.right(), threshold_y),
        )

        path = QtGui.QPainterPath(QtCore.QPointF(x_at(xs[0]), y_at(ys[0])))
        for x_value, y_value in self._trace_points[1:]:
            path.lineTo(QtCore.QPointF(x_at(x_value), y_at(y_value)))

        painter.setPen(QtGui.QPen(QtGui.QColor(Color.ACCENT), 2))
        painter.drawPath(path)

        painter.setPen(QtGui.QColor(Color.TEXT_3))
        painter.drawText(
            QtCore.QRectF(rect.left(), rect.bottom() + 4, rect.width(), 18),
            int(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter),
            "Load / N",
        )
        painter.drawText(
            QtCore.QRectF(0, rect.top(), rect.left() - 6, rect.height()),
            int(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTop),
            y_axis_label,
        )


def _trace_points(points: list[dict[str, object]]) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for point in points:
        x_value = _float(point.get("load_N"))
        y_value = _float(point.get("bending_percent"))
        if x_value is not None and y_value is not None:
            out.append((x_value, y_value))
    return out


class CurveFamilySparkline(QtWidgets.QFrame):
    def __init__(
        self,
        curve_points: list[dict[str, object]] | tuple[dict[str, object], ...],
        *,
        reference_points: list[dict[str, object]] | tuple[dict[str, object], ...] | None = None,
        focus_run_id: str = "",
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._curves = _curve_family_points(curve_points)
        self._reference = _reference_points(reference_points or [])
        self._focus_run_id = str(focus_run_id or "")
        self.setMinimumSize(360, 156)
        self.setObjectName("curveFamilySparkline")

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        y_axis_label = "Stress"
        left_margin = _axis_label_margin(painter, y_axis_label, minimum=48)
        rect = self.rect().adjusted(left_margin, 12, -10, -28)
        if rect.width() <= 0 or rect.height() <= 0 or not self._curves:
            return

        all_points = [point for points in self._curves.values() for point in points]
        all_points.extend(self._reference)
        xs = [point[0] for point in all_points]
        ys = [point[1] for point in all_points]
        x_min, x_max = min(xs), max(xs)
        if x_max <= x_min:
            x_max = x_min + 1.0
        y_min = min(0.0, min(ys))
        y_max = max(0.01, max(ys))
        if y_max <= y_min:
            y_max = y_min + 1.0
        y_max *= 1.08

        def x_at(value: float) -> float:
            return rect.left() + ((value - x_min) / (x_max - x_min)) * rect.width()

        def y_at(value: float) -> float:
            return rect.bottom() - ((value - y_min) / (y_max - y_min)) * rect.height()

        painter.setPen(QtGui.QPen(QtGui.QColor(Color.BORDER), 1))
        painter.drawRect(rect)

        other_pen = QtGui.QPen(QtGui.QColor(120, 130, 140, 105), 1.2)
        focus_pen = QtGui.QPen(QtGui.QColor(Color.ERR_ACCENT), 3.4)
        for run_id, points in sorted(self._curves.items(), key=lambda item: item[0]):
            if len(points) < 2:
                continue
            path = QtGui.QPainterPath(QtCore.QPointF(x_at(points[0][0]), y_at(points[0][1])))
            for x_value, y_value in points[1:]:
                path.lineTo(QtCore.QPointF(x_at(x_value), y_at(y_value)))
            painter.setPen(focus_pen if run_id == self._focus_run_id else other_pen)
            painter.drawPath(path)

        if len(self._reference) >= 2:
            ref_pen = QtGui.QPen(QtGui.QColor(Color.TEXT), 1.8)
            ref_pen.setDashPattern([5, 3])
            painter.setPen(ref_pen)
            path = QtGui.QPainterPath(QtCore.QPointF(x_at(self._reference[0][0]), y_at(self._reference[0][1])))
            for x_value, y_value in self._reference[1:]:
                path.lineTo(QtCore.QPointF(x_at(x_value), y_at(y_value)))
            painter.drawPath(path)

        focus_points = self._curves.get(self._focus_run_id, [])
        if focus_points:
            painter.setBrush(QtGui.QColor(Color.ERR_ACCENT))
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            for x_value, y_value in (focus_points[0], focus_points[-1]):
                painter.drawEllipse(QtCore.QPointF(x_at(x_value), y_at(y_value)), 3.2, 3.2)

        painter.setPen(QtGui.QColor(Color.TEXT_3))
        painter.drawText(
            QtCore.QRectF(rect.left(), rect.bottom() + 4, rect.width(), 18),
            int(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter),
            "Normalised strain / %",
        )
        painter.drawText(
            QtCore.QRectF(0, rect.top(), rect.left() - 6, rect.height()),
            int(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTop),
            y_axis_label,
        )


def _axis_label_margin(painter: QtGui.QPainter, label: str, *, minimum: int) -> int:
    return max(minimum, painter.fontMetrics().horizontalAdvance(label) + 14)


def _float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _curve_family_points(rows: list[dict[str, object]] | tuple[dict[str, object], ...]) -> dict[str, list[tuple[float, float]]]:
    grouped: dict[str, list[tuple[float, float]]] = {}
    for row in rows:
        run_id = str(row.get("run_id") or "")
        x_value = _float(row.get("x"))
        stress = _float(row.get("stress"))
        if not run_id or x_value is None or stress is None:
            continue
        grouped.setdefault(run_id, []).append((x_value, stress))
    return {run_id: sorted(points) for run_id, points in grouped.items() if points}


def _reference_points(rows: list[dict[str, object]] | tuple[dict[str, object], ...]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for row in rows:
        x_value = _float(row.get("x"))
        stress = _float(row.get("stress"))
        if x_value is not None and stress is not None:
            points.append((x_value, stress))
    return sorted(points)
