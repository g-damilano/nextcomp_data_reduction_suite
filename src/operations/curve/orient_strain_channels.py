from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from operations.core.operation import Operation
from operations.core.operation_context import OperationContext
from operations.core.operation_result import OperationResult


class OrientStrainChannelsOperation(Operation):
    operation_id = "orient_strain_channels"

    def run(self, context: OperationContext, step: Mapping[str, Any]) -> list[OperationResult]:
        inputs = _mapping(step.get("inputs", {}))
        outputs = _mapping(step.get("outputs", {}))
        parameters = _mapping(step.get("parameters", {}))
        mapping_orientation = _mapping(context.mapping.get("strain_orientation", {}))
        if not isinstance(inputs, Mapping):
            inputs = {}
        if not isinstance(outputs, Mapping):
            outputs = {}
        front_key = str(inputs.get("front") or step.get("front") or "front_strain_raw")
        rear_key = str(inputs.get("rear") or step.get("rear") or "rear_strain_raw")
        load_key = str(inputs.get("load") or step.get("load") or "load_N")
        front_output = str(outputs.get("front_strain_oriented") or outputs.get("front") or step.get("front_output") or "front_strain_oriented")
        rear_output = str(outputs.get("rear_strain_oriented") or outputs.get("rear") or step.get("rear_output") or "rear_strain_oriented")
        mode = str(
            mapping_orientation.get("mode")
            or parameters.get("mode")
            or step.get("policy")
            or "auto_detect_from_load_correlation"
        )
        if mode == "auto":
            mode = "auto_detect_from_load_correlation"
        if mode == "manual_multiplier":
            mode = "manual"
        loading_region = str(parameters.get("loading_region", "rising_pre_failure"))
        confidence_threshold = float(parameters.get("confidence_threshold", 0.85))
        preserve_raw = bool(parameters.get("preserve_raw", True))
        results: list[OperationResult] = []

        for run_id, run in context.runs.items():
            warnings: list[str] = []
            front = run.series.get(front_key)
            rear = run.series.get(rear_key)
            load = run.series.get(load_key)
            front_oriented: list[float | None] = []
            rear_oriented: list[float | None] = []
            front_multiplier: int | None = None
            rear_multiplier: int | None = None
            front_correlation: float | None = None
            rear_correlation: float | None = None
            front_magnitude_correlation: float | None = None
            rear_magnitude_correlation: float | None = None
            front_transform: str | None = None
            rear_transform: str | None = None
            confidence = "unknown"
            decision = ""
            evidence: dict[str, Any] = {
                "mode": mode,
                "loading_region": loading_region,
                "loading_region_used": loading_region,
                "preserve_raw": preserve_raw,
                "raw_inputs": {"front": front_key, "rear": rear_key, "load": load_key},
                "oriented_outputs": {"front": front_output, "rear": rear_output},
                "raw_series_refs": {"front": front_key, "rear": rear_key, "load": load_key},
                "oriented_series_refs": {"front": front_output, "rear": rear_output},
            }

            if front is None or rear is None:
                warnings.append("Cannot orient strain channels because front or rear input series is missing.")
            elif mode == "manual":
                front_multiplier = _manual_multiplier(mapping_orientation, "front_multiplier")
                rear_multiplier = _manual_multiplier(mapping_orientation, "rear_multiplier")
                if front_multiplier is None or rear_multiplier is None:
                    warnings.append("Manual strain orientation requires front_multiplier and rear_multiplier.")
                else:
                    confidence = "manual"
                    front_transform = "multiply"
                    rear_transform = "multiply"
                    reason = str(mapping_orientation.get("reason") or "manual mapping override")
                    decision = f"manual orientation applied: front {front_multiplier:+d}, rear {rear_multiplier:+d}; {reason}"
                    front_oriented = _apply_multiplier(front, front_multiplier)
                    rear_oriented = _apply_multiplier(rear, rear_multiplier)
            elif mode == "magnitude_compression_positive":
                front_multiplier = None
                rear_multiplier = None
                front_transform = "magnitude"
                rear_transform = "magnitude"
                confidence = "policy"
                decision = "magnitude_compression_positive policy applied"
                front_oriented = [None if value is None else abs(value) for value in front]
                rear_oriented = [None if value is None else abs(value) for value in rear]
            elif mode == "auto_detect_from_load_correlation":
                if load is None:
                    warnings.append("Auto strain orientation requires a load series.")
                else:
                    indices = _loading_region_indices(load, loading_region)
                    front_decision = _auto_orientation_decision(load, front, indices, confidence_threshold)
                    rear_decision = _auto_orientation_decision(load, rear, indices, confidence_threshold)
                    front_correlation = front_decision["correlation"]
                    rear_correlation = rear_decision["correlation"]
                    front_magnitude_correlation = front_decision["magnitude_correlation"]
                    rear_magnitude_correlation = rear_decision["magnitude_correlation"]
                    front_multiplier = front_decision["multiplier"]
                    rear_multiplier = rear_decision["multiplier"]
                    front_transform = front_decision["transform"]
                    rear_transform = rear_decision["transform"]
                    confidence = _combined_confidence(str(front_decision["confidence"]), str(rear_decision["confidence"]))
                    if front_transform is None or rear_transform is None:
                        warnings.append("Strain orientation could not be inferred from load correlation.")
                        decision = "orientation ambiguous; no oriented series written"
                    else:
                        front_oriented = _apply_orientation(front, str(front_transform), front_multiplier)
                        rear_oriented = _apply_orientation(rear, str(rear_transform), rear_multiplier)
                        decision = _decision_text(front_transform, front_multiplier, rear_transform, rear_multiplier, confidence)
                        if confidence != "high":
                            warnings.append("Strain orientation inferred with low confidence.")
                    evidence["loading_region_indices"] = {
                        "count": len(indices),
                        "first": indices[0] if indices else None,
                        "last": indices[-1] if indices else None,
                    }
            else:
                warnings.append(f"Unsupported strain orientation mode: {mode}")

            if front_oriented and rear_oriented:
                run.series[front_output] = front_oriented
                run.series[rear_output] = rear_oriented
                run.units[front_output] = run.units.get(front_key)
                run.units[rear_output] = run.units.get(rear_key)
            evidence.update(
                {
                    "decision": decision,
                    "front_multiplier": front_multiplier,
                    "rear_multiplier": rear_multiplier,
                    "front_sign_multiplier": front_multiplier,
                    "rear_sign_multiplier": rear_multiplier,
                    "front_orientation_transform": front_transform,
                    "rear_orientation_transform": rear_transform,
                    "front_correlation_with_load": front_correlation,
                    "rear_correlation_with_load": rear_correlation,
                    "front_magnitude_correlation_with_load": front_magnitude_correlation,
                    "rear_magnitude_correlation_with_load": rear_magnitude_correlation,
                    "confidence": confidence,
                    "point_count": max(len(front or ()), len(rear or ())),
                    "front_sign_flips": _sign_flip_count(front or [], front_oriented),
                    "rear_sign_flips": _sign_flip_count(rear or [], rear_oriented),
                    "sample_points": _sample_points(front or [], rear or [], front_oriented, rear_oriented),
                    "warnings": warnings,
                }
            )

            results.append(
                OperationResult(
                    operation_id=self.operation_id,
                    operation_type=self.operation_id,
                    phase=context.phase,
                    run_id=run_id,
                    status="warning" if warnings else "ok",
                    inputs={"front": front_key, "rear": rear_key, "load": load_key},
                    parameters={
                        "mode": mode,
                        "loading_region": loading_region,
                        "confidence_threshold": confidence_threshold,
                        "preserve_raw": preserve_raw,
                    },
                    outputs={
                        front_output: {"point_count": len(front_oriented)},
                        rear_output: {"point_count": len(rear_oriented)},
                        "front_multiplier": front_multiplier,
                        "rear_multiplier": rear_multiplier,
                        "front_sign_multiplier": front_multiplier,
                        "rear_sign_multiplier": rear_multiplier,
                        "front_orientation_transform": front_transform,
                        "rear_orientation_transform": rear_transform,
                        "front_correlation_with_load": front_correlation,
                        "rear_correlation_with_load": rear_correlation,
                        "front_magnitude_correlation_with_load": front_magnitude_correlation,
                        "rear_magnitude_correlation_with_load": rear_magnitude_correlation,
                        "confidence": confidence,
                    },
                    units={
                        front_output: run.units.get(front_output),
                        rear_output: run.units.get(rear_output),
                    },
                    evidence=evidence,
                    audit_view_hint="strain_orientation_overlay",
                    warnings=tuple(warnings),
                )
            )
        return results


def _sign_flip_count(
    raw: list[float | None],
    oriented: list[float | None],
) -> int:
    return sum(
        1
        for raw_value, oriented_value in zip(raw, oriented)
        if raw_value is not None and oriented_value is not None and raw_value != oriented_value
    )


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _manual_multiplier(mapping_orientation: Mapping[str, Any], key: str) -> int | None:
    value = mapping_orientation.get(key)
    if value in (-1, "-1"):
        return -1
    if value in (1, "+1", "1"):
        return 1
    return None


def _loading_region_indices(load: list[float | None], loading_region: str) -> list[int]:
    valid = [(index, abs(value)) for index, value in enumerate(load) if value is not None]
    if len(valid) < 3:
        return [index for index, _value in valid]
    max_index, max_load = max(valid, key=lambda item: item[1])
    if loading_region == "rising_pre_failure":
        lower = max_load * 0.10
        upper = max_load * 0.90
        return [index for index, value in valid if index <= max_index and lower <= value <= upper]
    return [index for index, _value in valid if index <= max_index]


def _correlation_for_indices(
    load: list[float | None],
    strain: list[float | None],
    indices: list[int],
) -> float | None:
    pairs = [
        (abs(load[index]), strain[index])
        for index in indices
        if index < len(load)
        and index < len(strain)
        and load[index] is not None
        and strain[index] is not None
    ]
    if len(pairs) < 3:
        return None
    return _pearson([pair[0] for pair in pairs], [pair[1] for pair in pairs])


def _pearson(x_values: list[float], y_values: list[float]) -> float | None:
    x_mean = sum(x_values) / len(x_values)
    y_mean = sum(y_values) / len(y_values)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
    x_denominator = sum((x - x_mean) ** 2 for x in x_values)
    y_denominator = sum((y - y_mean) ** 2 for y in y_values)
    denominator = (x_denominator * y_denominator) ** 0.5
    if denominator == 0:
        return None
    return numerator / denominator


def _multiplier_from_correlation(correlation: float | None) -> int | None:
    if correlation is None:
        return None
    return 1 if correlation >= 0 else -1


def _confidence(
    front_correlation: float | None,
    rear_correlation: float | None,
    threshold: float,
) -> str:
    values = [abs(value) for value in (front_correlation, rear_correlation) if value is not None]
    if len(values) != 2:
        return "ambiguous"
    return "high" if min(values) >= threshold else "low"


def _apply_multiplier(series: list[float | None], multiplier: int) -> list[float | None]:
    return [None if value is None else value * multiplier for value in series]


def _auto_orientation_decision(
    load: list[float | None],
    strain: list[float | None],
    indices: list[int],
    threshold: float,
) -> dict[str, Any]:
    correlation = _correlation_for_indices(load, strain, indices)
    magnitude_correlation = _correlation_for_indices(load, [None if value is None else abs(value) for value in strain], indices)
    sign_indices = list(range(0, max(indices) + 1)) if indices else indices
    sign_variable = _has_mixed_signs(strain, sign_indices)
    if sign_variable and magnitude_correlation is not None and abs(magnitude_correlation) >= threshold:
        return {
            "transform": "magnitude",
            "multiplier": None,
            "correlation": correlation,
            "magnitude_correlation": magnitude_correlation,
            "confidence": "high",
        }
    multiplier = _multiplier_from_correlation(correlation)
    if multiplier is None:
        return {
            "transform": None,
            "multiplier": None,
            "correlation": correlation,
            "magnitude_correlation": magnitude_correlation,
            "confidence": "ambiguous",
        }
    confidence = "high" if abs(correlation or 0.0) >= threshold else "low"
    return {
        "transform": "multiply",
        "multiplier": multiplier,
        "correlation": correlation,
        "magnitude_correlation": magnitude_correlation,
        "confidence": confidence,
    }


def _has_mixed_signs(series: list[float | None], indices: list[int]) -> bool:
    signs = {
        1 if value > 0 else -1
        for index in indices
        if index < len(series)
        for value in [series[index]]
        if value is not None and abs(value) > 1e-15
    }
    return len(signs) > 1


def _combined_confidence(front: str, rear: str) -> str:
    if front == "ambiguous" or rear == "ambiguous":
        return "ambiguous"
    if front == "high" and rear == "high":
        return "high"
    if front == "manual" and rear == "manual":
        return "manual"
    return "low"


def _apply_orientation(
    series: list[float | None],
    transform: str,
    multiplier: int | None,
) -> list[float | None]:
    if transform == "magnitude":
        return [None if value is None else abs(value) for value in series]
    if transform == "multiply" and multiplier is not None:
        return _apply_multiplier(series, multiplier)
    return []


def _decision_text(
    front_transform: str | None,
    front_multiplier: int | None,
    rear_transform: str | None,
    rear_multiplier: int | None,
    confidence: str,
) -> str:
    front_decision = _transform_text(front_transform, front_multiplier)
    rear_decision = _transform_text(rear_transform, rear_multiplier)
    return f"front strain {front_decision}; rear strain {rear_decision}; confidence {confidence}"


def _transform_text(transform: str | None, multiplier: int | None) -> str:
    if transform == "magnitude":
        return "converted to magnitude"
    if transform == "multiply":
        return "inverted" if multiplier == -1 else "preserved"
    return "unresolved"


def _sample_points(
    front: list[float | None],
    rear: list[float | None],
    front_oriented: list[float | None],
    rear_oriented: list[float | None],
) -> list[dict[str, Any]]:
    if not front and not rear:
        return []
    candidate_indices = [0, 1, 2, 29, len(front) // 2, max(len(front), len(rear)) - 1]
    seen: set[int] = set()
    samples: list[dict[str, Any]] = []
    for index in candidate_indices:
        if index < 0 or index in seen:
            continue
        seen.add(index)
        samples.append(
            {
                "point_index": index,
                "front_raw": _value_at(front, index),
                "rear_raw": _value_at(rear, index),
                "front_oriented": _value_at(front_oriented, index),
                "rear_oriented": _value_at(rear_oriented, index),
            }
        )
    return samples


def _value_at(series: list[float | None], index: int) -> float | None:
    return series[index] if index < len(series) else None
