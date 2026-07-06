from __future__ import annotations

from statistics import median

from acceptance.curve_family.models import AlignedCurve, ReferenceCurve


def pointwise_median_reference(
    aligned_curves: list[AlignedCurve],
    *,
    curve_family_id: str,
    reference_id: str = "pointwise_median_reference",
) -> ReferenceCurve | None:
    if not aligned_curves:
        return None
    x_common = aligned_curves[0].x_common
    y_reference: list[float | None] = []
    n_observations: list[int] = []
    for index in range(len(x_common)):
        values = [
            curve.y_aligned[index]
            for curve in aligned_curves
            if index < len(curve.y_aligned) and curve.y_aligned[index] is not None
        ]
        numeric = [float(value) for value in values if value is not None]
        n_observations.append(len(numeric))
        y_reference.append(float(median(numeric)) if numeric else None)
    return ReferenceCurve(
        curve_family_id=curve_family_id,
        reference_id=reference_id,
        x_common=x_common,
        y_reference=tuple(y_reference),
        reference_type="pointwise_median",
        n_observations=tuple(n_observations),
    )
