from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from operations.core.operation import Operation
from operations.core.operation_context import OperationContext, OperationRun
from operations.core.operation_result import OperationResult


class MapChannelOperation(Operation):
    operation_id = "map_channel"

    def run(self, context: OperationContext, step: Mapping[str, Any]) -> list[OperationResult]:
        output = str(step.get("output") or step.get("role") or "")
        mapping_key = str(step.get("from_mapping") or output)
        channel_name = _mapping_lookup(context.mapping, "channels", mapping_key)
        required = bool(step.get("required", True))
        transform = _channel_transform(step)
        raw_output = _optional_text(step.get("raw_output") or step.get("preserve_raw_output"))
        results: list[OperationResult] = []
        for run_id, run in context.runs.items():
            warnings: list[str] = []
            if not output:
                warnings.append("map_channel step is missing output/role.")
            if not channel_name and required:
                warnings.append(f"Mapping does not define channel '{mapping_key}'.")
                channel = None
            else:
                channel = run.source_run.channel(str(channel_name)) if channel_name else None
                if channel is None:
                    if not required:
                        results.append(
                            OperationResult(
                                operation_id=self.operation_id,
                                operation_type=self.operation_id,
                                phase=context.phase,
                                run_id=run_id,
                                status="ok",
                                inputs={"mapping_key": mapping_key, "channel": channel_name},
                                parameters=_map_channel_parameters(required, transform, raw_output),
                                outputs={output: None},
                                units={output: None},
                                evidence={"normalized_package_path": run.source_run.normalized_package_path},
                                audit_view_hint="resolve_mapping_table",
                            )
                        )
                        continue
                    warnings.append(f"Run {run_id} does not contain channel '{channel_name}'.")
            if channel is not None and output:
                raw_values = list(channel.values)
                mapped_values, transform_warnings = _apply_channel_transform(raw_values, transform)
                warnings.extend(transform_warnings)
                if raw_output and raw_output != output:
                    run.series[raw_output] = raw_values
                    run.units[raw_output] = channel.unit
                run.series[output] = mapped_values
                run.units[output] = channel.unit
            output_payload = _map_channel_output_payload(
                output=output,
                raw_output=raw_output,
                channel=channel,
            )
            unit_payload = {output: channel.unit if channel else None}
            if raw_output and raw_output != output:
                unit_payload[raw_output] = channel.unit if channel else None
            results.append(
                OperationResult(
                    operation_id=self.operation_id,
                    operation_type=self.operation_id,
                    phase=context.phase,
                    run_id=run_id,
                    status="warning" if warnings else "ok",
                    inputs={"mapping_key": mapping_key, "channel": channel_name},
                    parameters=_map_channel_parameters(required, transform, raw_output),
                    outputs=output_payload,
                    units=unit_payload,
                    evidence={
                        "normalized_package_path": run.source_run.normalized_package_path,
                        "transform": transform,
                        "formula": _map_channel_formula(output, channel_name, transform, raw_output),
                    },
                    audit_view_hint="resolve_mapping_table",
                    warnings=tuple(warnings),
                )
            )
        return results


class MapScalarOperation(Operation):
    operation_id = "map_scalar"

    def run(self, context: OperationContext, step: Mapping[str, Any]) -> list[OperationResult]:
        output = str(step.get("output") or step.get("role") or "")
        mapping_key = str(step.get("from_mapping") or output)
        token_name = _mapping_lookup(context.mapping, "fields", mapping_key)
        numeric = bool(step.get("numeric", True))
        required = bool(step.get("required", True))
        results: list[OperationResult] = []
        for run_id, run in context.runs.items():
            warnings: list[str] = []
            token = run.source_run.token(str(token_name)) if token_name else None
            if not output:
                warnings.append("map_scalar step is missing output/role.")
            if not token_name and required:
                warnings.append(f"Mapping does not define field '{mapping_key}'.")
            if token is None and token_name and required:
                warnings.append(f"Run {run_id} does not contain token '{token_name}'.")
            value: object | None = None
            unit: str | None = None
            if token is not None:
                value = token.numeric if numeric else token.value
                unit = token.unit
                if numeric and value is None:
                    warnings.append(f"Token '{token.name}' is not numeric.")
                if output and value is not None:
                    run.scalars[output] = value
                    run.units[output] = unit
            results.append(
                OperationResult(
                    operation_id=self.operation_id,
                    operation_type=self.operation_id,
                    phase=context.phase,
                    run_id=run_id,
                    status="warning" if warnings else "ok",
                    inputs={"mapping_key": mapping_key, "token": token_name},
                    parameters={"numeric": numeric, "required": required},
                    outputs={output: {"value": value, "unit": unit} if output else None},
                    units={output: unit if output else None},
                    evidence={"normalized_package_path": run.source_run.normalized_package_path},
                    audit_view_hint="resolve_mapping_table",
                    warnings=tuple(warnings),
                )
            )
        return results


class DeriveAreaOperation(Operation):
    operation_id = "derive_area"

    def run(self, context: OperationContext, step: Mapping[str, Any]) -> list[OperationResult]:
        width_key = str(step.get("width", "width_mm"))
        thickness_key = str(step.get("thickness", "thickness_mm"))
        output = str(step.get("output", "area_mm2"))
        results: list[OperationResult] = []
        for run_id, run in context.runs.items():
            warnings: list[str] = []
            width = _numeric_scalar(run, width_key)
            thickness = _numeric_scalar(run, thickness_key)
            area = None
            if width is None or thickness is None:
                warnings.append("Cannot derive area because width or thickness is missing.")
            else:
                area = width * thickness
                run.scalars[output] = area
                run.units[output] = str(step.get("unit", "mm^2"))
            results.append(
                OperationResult(
                    operation_id=self.operation_id,
                    operation_type="derive_area",
                    phase=context.phase,
                    run_id=run_id,
                    status="warning" if warnings else "ok",
                    inputs={"width": width_key, "thickness": thickness_key},
                    parameters={},
                    outputs={output: area},
                    units={output: run.units.get(output)},
                    evidence={"formula": f"{output} = {width_key} * {thickness_key}"},
                    audit_view_hint="geometry_area",
                    warnings=tuple(warnings),
                )
            )
        return results


class DeriveSeriesMeanOperation(Operation):
    operation_id = "derive_series_mean"

    def run(self, context: OperationContext, step: Mapping[str, Any]) -> list[OperationResult]:
        raw_inputs = step.get("inputs", ()) or ()
        if isinstance(raw_inputs, Mapping):
            raw_inputs = raw_inputs.get("series", ()) or ()
        inputs = [str(item) for item in raw_inputs]
        parameters = step.get("parameters", {})
        parameters = parameters if isinstance(parameters, Mapping) else {}
        mode = str(parameters.get("mode") or step.get("mode") or "arithmetic_mean")
        output = str(step.get("output", "mean_series"))
        abs_outputs = _abs_outputs(step, parameters, inputs)
        results: list[OperationResult] = []
        for run_id, run in context.runs.items():
            warnings: list[str] = []
            series_list = [run.series.get(name) for name in inputs]
            abs_series_by_output: dict[str, list[float | None]] = {name: [] for name in abs_outputs}
            if not inputs or any(series is None for series in series_list):
                warnings.append(f"Cannot derive {output}; one or more input series are missing.")
                mean_values: list[float | None] = []
            elif mode not in {"arithmetic_mean", "mean_absolute"}:
                warnings.append(f"Unsupported mean series mode: {mode}.")
                mean_values = []
            else:
                max_len = max(len(series or []) for series in series_list)
                mean_values = []
                for index in range(max_len):
                    context.check_cancelled()
                    values = [
                        series[index]
                        for series in series_list
                        if series is not None and index < len(series) and series[index] is not None
                    ]
                    if len(values) == len(series_list):
                        mean_inputs = [abs(value) for value in values] if mode == "mean_absolute" else values
                        mean_values.append(sum(mean_inputs) / len(mean_inputs))
                    else:
                        mean_values.append(None)
                    if mode == "mean_absolute":
                        for output_name, source_series in zip(abs_outputs, series_list):
                            value = source_series[index] if source_series is not None and index < len(source_series) else None
                            abs_series_by_output[output_name].append(None if value is None else abs(value))
                run.series[output] = mean_values
                run.units[output] = _first_unit(run, inputs)
                for output_name, abs_values in abs_series_by_output.items():
                    run.series[output_name] = abs_values
                    source_index = abs_outputs.index(output_name)
                    run.units[output_name] = run.units.get(inputs[source_index])
            output_payload: dict[str, Any] = {output: {"point_count": len(mean_values)}}
            for output_name, abs_values in abs_series_by_output.items():
                output_payload[output_name] = {"point_count": len(abs_values)}
            results.append(
                OperationResult(
                    operation_id=self.operation_id,
                    operation_type="construct_mean_series",
                    phase=context.phase,
                    run_id=run_id,
                    status="warning" if warnings else "ok",
                    inputs={"series": inputs},
                    parameters={"mode": mode, "absolute_outputs": abs_outputs},
                    outputs=output_payload,
                    units={output: run.units.get(output), **{name: run.units.get(name) for name in abs_outputs}},
                    evidence={
                        "formula": _mean_formula(output, inputs, mode),
                        "mode": mode,
                        "raw_series_refs": inputs,
                        "absolute_series_refs": abs_outputs,
                        "sample_points": _mean_sample_points(inputs, series_list, abs_outputs, abs_series_by_output, mean_values),
                    },
                    audit_view_hint="mean_absolute_strain_construction" if mode == "mean_absolute" else "mean_strain_construction",
                    warnings=tuple(warnings),
                )
            )
        return results


class DeriveSeriesByScalarOperation(Operation):
    operation_id = "derive_series_by_scalar"

    def run(self, context: OperationContext, step: Mapping[str, Any]) -> list[OperationResult]:
        numerator_key = str(step.get("numerator"))
        denominator_key = str(step.get("denominator"))
        output = str(step.get("output"))
        output_unit = str(step.get("unit", "")) or None
        results: list[OperationResult] = []
        for run_id, run in context.runs.items():
            warnings: list[str] = []
            numerator = run.series.get(numerator_key)
            denominator = _numeric_scalar(run, denominator_key)
            derived: list[float | None] = []
            if numerator is None:
                warnings.append(f"Numerator series '{numerator_key}' is missing.")
            if denominator is None or denominator == 0:
                warnings.append(f"Denominator scalar '{denominator_key}' is missing or zero.")
            if numerator is not None and denominator not in (None, 0):
                derived = [None if value is None else value / float(denominator) for value in numerator]
                run.series[output] = derived
                run.units[output] = output_unit
                inspect_x = step.get("inspect_with_x")
                if inspect_x and str(inspect_x) in run.series:
                    inspection = context.inspector.inspect_curve(
                        run.series[str(inspect_x)],
                        derived,
                        scope=f"{output}_whole_curve",
                        inspection_id=f"inspect_{run_id}_stress_strain_curve",
                        curve_id=f"{run_id}_stress_strain",
                        run_id=run_id,
                        x_channel=str(inspect_x),
                        y_channel=output,
                    )
                    inspection_refs = (context.record_inspection(inspection),)
                else:
                    inspection_refs = ()
            else:
                inspection_refs = ()
            results.append(
                OperationResult(
                    operation_id=self.operation_id,
                    operation_type="derive_stress" if output == "stress_MPa" else self.operation_id,
                    phase=context.phase,
                    run_id=run_id,
                    status="warning" if warnings else "ok",
                    inputs={"numerator": numerator_key, "denominator": denominator_key},
                    parameters={"mode": "series_divided_by_scalar"},
                    outputs={output: {"unit": output_unit, "point_count": len(derived)}},
                    units={output: output_unit},
                    evidence={"formula": f"{output} = {numerator_key} / {denominator_key}"},
                    inspection_refs=inspection_refs,
                    audit_view_hint="stress_construction",
                    warnings=tuple(warnings),
                )
            )
        return results


def _mapping_lookup(mapping: Mapping[str, Any], section: str, key: str) -> Any:
    payload = mapping.get(section, {})
    if isinstance(payload, Mapping):
        value = payload.get(key)
        if isinstance(value, Mapping):
            return value.get("name") or value.get("token") or value.get("channel")
        return value
    return None


def _channel_transform(step: Mapping[str, Any]) -> str:
    return str(step.get("transform") or step.get("value_transform") or "identity").strip().casefold()


def _optional_text(value: Any) -> str:
    return str(value).strip() if value not in (None, "") else ""


def _map_channel_parameters(required: bool, transform: str, raw_output: str) -> dict[str, Any]:
    parameters: dict[str, Any] = {"required": required, "transform": transform}
    if raw_output:
        parameters["raw_output"] = raw_output
    return parameters


def _map_channel_output_payload(
    *,
    output: str,
    raw_output: str,
    channel: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        output: {"unit": channel.unit, "point_count": channel.point_count} if channel else None,
    }
    if raw_output and raw_output != output:
        payload[raw_output] = {"unit": channel.unit, "point_count": channel.point_count} if channel else None
    return payload


def _apply_channel_transform(values: list[Any], transform: str) -> tuple[list[Any], tuple[str, ...]]:
    if transform in {"", "identity", "none"}:
        return list(values), ()
    if transform not in {"absolute", "abs", "magnitude"}:
        return list(values), (f"Unsupported channel transform '{transform}'; copied source values unchanged.",)

    mapped: list[float | None] = []
    invalid: list[tuple[int, Any]] = []
    invalid_count = 0
    for index, value in enumerate(values):
        if value in (None, ""):
            mapped.append(None)
            continue
        try:
            mapped.append(abs(float(value)))
        except (TypeError, ValueError):
            mapped.append(None)
            invalid_count += 1
            if len(invalid) < 5:
                invalid.append((index, value))
    if invalid_count == 0:
        return mapped, ()
    sample = ", ".join(f"index {index}: {value!r}" for index, value in invalid)
    suffix = f" Examples: {sample}." if sample else ""
    return mapped, (f"Absolute channel transform skipped {invalid_count} non-numeric value(s).{suffix}",)


def _map_channel_formula(output: str, channel_name: Any, transform: str, raw_output: str) -> str:
    channel_ref = f"channel:{channel_name}" if channel_name else "mapped channel"
    if transform in {"absolute", "abs", "magnitude"}:
        formula = f"{output} = abs({channel_ref})"
    else:
        formula = f"{output} = {channel_ref}"
    if raw_output and raw_output != output:
        formula = f"{formula}; {raw_output} preserves original signed values"
    return formula


def _numeric_scalar(run: OperationRun, key: str) -> float | None:
    value = run.scalars.get(key)
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _first_unit(run: OperationRun, keys: list[str]) -> str | None:
    for key in keys:
        if run.units.get(key):
            return run.units[key]
    return None


def _abs_outputs(step: Mapping[str, Any], parameters: Mapping[str, Any], inputs: list[str]) -> list[str]:
    raw_outputs = step.get("absolute_outputs") or step.get("abs_outputs") or parameters.get("absolute_outputs") or parameters.get("abs_outputs")
    if isinstance(raw_outputs, Mapping):
        return [str(raw_outputs.get(input_name) or "") for input_name in inputs if raw_outputs.get(input_name)]
    if isinstance(raw_outputs, list):
        return [str(item) for item in raw_outputs]
    return []


def _mean_formula(output: str, inputs: list[str], mode: str) -> str:
    if mode == "mean_absolute":
        return f"{output} = mean({', '.join(f'abs({name})' for name in inputs)})"
    return f"{output} = arithmetic mean of {', '.join(inputs)}"


def _mean_sample_points(
    inputs: list[str],
    series_list: list[list[float | None] | None],
    abs_outputs: list[str],
    abs_series_by_output: dict[str, list[float | None]],
    mean_values: list[float | None],
) -> list[dict[str, Any]]:
    max_len = max((len(series or []) for series in series_list), default=0)
    if max_len == 0:
        return []
    candidate_indices = [0, 1, 2, 29, max_len // 2, max_len - 1]
    samples: list[dict[str, Any]] = []
    seen: set[int] = set()
    for index in candidate_indices:
        if index < 0 or index in seen:
            continue
        seen.add(index)
        row: dict[str, Any] = {"point_index": index}
        for name, series in zip(inputs, series_list):
            row[name] = _series_at(series or [], index)
        for name in abs_outputs:
            row[name] = _series_at(abs_series_by_output.get(name, []), index)
        row["mean"] = _series_at(mean_values, index)
        samples.append(row)
    return samples


def _series_at(series: list[float | None], index: int) -> float | None:
    return series[index] if index < len(series) else None
