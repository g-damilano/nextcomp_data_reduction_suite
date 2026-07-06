from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from operations.core.operation_contract_registry import get_evidence_contract


SURFACE_ROLE = "wizard_acceptance"
METHOD_ID = "iso14126_2023"


@dataclass(frozen=True, slots=True)
class DiagnosticFinding:
    finding_id: str
    method_id: str
    run_id: str
    defect_type: str
    data_kind: str
    severity: str
    default_decision: str
    evidence_contract_id: str


@dataclass(frozen=True, slots=True)
class DiagnosticEvidencePacket:
    packet_id: str
    finding_id: str
    run_id: str
    method_id: str
    contract_id: str
    values: Mapping[str, Any]
    missing_required_keys: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DiagnosticCard:
    evidence_key: str
    label: str
    value: str
    subtext: str
    state: str = "ok"
    level: str = "info"
    required: bool = True


@dataclass(frozen=True, slots=True)
class DiagnosticPlotContract:
    plot_kind: str
    title: str
    x_axis_label: str
    y_axis_label: str
    required_layers: tuple[str, ...]
    semantic_layers: tuple[str, ...]
    layout_policy: Mapping[str, Any]
    missing_required_keys: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DiagnosticCockpitView:
    view_id: str
    finding: DiagnosticFinding
    evidence_packet: DiagnosticEvidencePacket
    cards: tuple[DiagnosticCard, ...]
    plot_contract: DiagnosticPlotContract
    decision: Mapping[str, Any]
    missing_evidence_policy: Mapping[str, Any]
    surface_role: str = SURFACE_ROLE


@dataclass(frozen=True, slots=True)
class CardSpec:
    evidence_key: str
    label: str
    formatter: str
    required: bool = True
    subtext: str = ""


@dataclass(frozen=True, slots=True)
class ViewSpec:
    view_id: str
    method_id: str
    defect_type: str
    data_kind: str
    surface_role: str
    evidence_contract_id: str
    plot_kind: str
    plot_title: str
    x_axis_label: str
    y_axis_label: str
    required_plot_keys: tuple[str, ...]
    required_layers: tuple[str, ...]
    semantic_layers: tuple[str, ...]
    cards: tuple[CardSpec, ...]
    layout_policy: Mapping[str, Any] = field(default_factory=dict)


class DiagnosticViewRegistry:
    def __init__(self, specs: tuple[ViewSpec, ...]) -> None:
        self._specs = {
            (
                spec.method_id,
                spec.defect_type,
                spec.data_kind,
                spec.surface_role,
                spec.evidence_contract_id,
            ): spec
            for spec in specs
        }

    def resolve(
        self,
        *,
        method_id: str,
        defect_type: str,
        data_kind: str,
        surface_role: str,
        evidence_contract_id: str,
    ) -> ViewSpec | None:
        return self._specs.get((method_id, defect_type, data_kind, surface_role, evidence_contract_id))


def diagnostic_cockpit_from_payload(payload: Mapping[str, Any]) -> DiagnosticCockpitView:
    method_id = str(payload.get("method_id") or METHOD_ID)
    run_id = str(payload.get("run_id") or payload.get("id") or payload.get("run") or "run")
    evidence_kind = str(payload.get("evidence_kind") or _evidence_kind_from_flags(payload)).casefold()
    if evidence_kind == "curve_family":
        return _curve_family_cockpit(payload, method_id=method_id, run_id=run_id)
    if evidence_kind == "bending":
        return _bending_cockpit(payload, method_id=method_id, run_id=run_id)
    if _has_bending_context(payload):
        return _bending_cockpit(payload, method_id=method_id, run_id=run_id)
    return _unsupported_cockpit(payload, method_id=method_id, run_id=run_id)


def _bending_cockpit(payload: Mapping[str, Any], *, method_id: str, run_id: str) -> DiagnosticCockpitView:
    contract_id = get_evidence_contract("bending_diagnostic").contract_id
    values = _bending_values(payload)
    default_decision = _decision_type(payload)
    finding = DiagnosticFinding(
        finding_id=f"{run_id}:sustained_bending",
        method_id=method_id,
        run_id=run_id,
        defect_type="sustained_bending",
        data_kind="bending_percent_curve",
        severity=_primary_severity(payload),
        default_decision=default_decision,
        evidence_contract_id=contract_id,
    )
    spec = diagnostic_view_registry().resolve(
        method_id=method_id,
        defect_type=finding.defect_type,
        data_kind=finding.data_kind,
        surface_role=SURFACE_ROLE,
        evidence_contract_id=contract_id,
    )
    if spec is None:
        return _unsupported_cockpit(payload, method_id=method_id, run_id=run_id)
    missing = tuple(key for key in _required_value_keys(spec) if _missing(values.get(key)))
    packet = DiagnosticEvidencePacket(
        packet_id=f"{finding.finding_id}:packet",
        finding_id=finding.finding_id,
        run_id=run_id,
        method_id=method_id,
        contract_id=contract_id,
        values=values,
        missing_required_keys=missing,
    )
    plot_missing = tuple(key for key in spec.required_plot_keys if _missing(values.get(key)))
    return DiagnosticCockpitView(
        view_id=spec.view_id,
        finding=finding,
        evidence_packet=packet,
        cards=_cards_from_spec(spec, values),
        plot_contract=DiagnosticPlotContract(
            plot_kind=spec.plot_kind,
            title=spec.plot_title,
            x_axis_label=spec.x_axis_label,
            y_axis_label=spec.y_axis_label,
            required_layers=spec.required_layers,
            semantic_layers=spec.semantic_layers,
            layout_policy=spec.layout_policy,
            missing_required_keys=plot_missing,
        ),
        decision=_decision_spec(payload, default_decision=default_decision),
        missing_evidence_policy=_missing_policy(),
    )


def _curve_family_cockpit(payload: Mapping[str, Any], *, method_id: str, run_id: str) -> DiagnosticCockpitView:
    contract_id = get_evidence_contract("curve_family_diagnostic").contract_id
    values = {
        "curve_family.metric": payload.get("curve_family_metric"),
        "curve_family.value": payload.get("curve_family_value"),
        "curve_family.threshold": payload.get("curve_family_threshold"),
        "curve_family.outlier_limit": payload.get("curve_family_outlier_limit"),
        "curve_family.robust_threshold": payload.get("curve_family_robust_threshold"),
        "curve_family.rank": payload.get("curve_family_rank"),
        "curve_family.classification": payload.get("curve_family_classification"),
        "curve_family.reason": payload.get("curve_family_reason"),
        "curve_family.robust_z": payload.get("curve_family_robust_z"),
        "curve_family.masking_risk": payload.get("curve_family_masking_risk"),
        "curve_family.dixon_decision": payload.get("curve_family_dixon_decision"),
        "selection.consequence_summary": _consequence_summary(payload),
        "plot.curve_family_curve": payload.get("curve_family_points"),
    }
    finding = DiagnosticFinding(
        finding_id=f"{run_id}:curve_family",
        method_id=method_id,
        run_id=run_id,
        defect_type="curve_family_outlier",
        data_kind="curve_family_distance",
        severity=_primary_severity(payload),
        default_decision=_decision_type(payload),
        evidence_contract_id=contract_id,
    )
    cards = (
        _card("curve_family.classification", "Scientific call", _display_text(values["curve_family.classification"]), "curve-shape assessment", values, required=False),
        _card("curve_family.metric", "Primary metric", _metric_summary(values["curve_family.metric"], values["curve_family.value"]), _metric_context(values), values),
        _card("curve_family.rank", "Distance rank", _display_text(values["curve_family.rank"]), "rank within assessed cohort", values, required=False),
        _card("curve_family.robust_z", "Robust screen", _robust_screen_text(values), "masking-risk companion evidence", values, required=False),
        _card("curve_family.dixon_decision", "Outlier test", _outlier_test_text(values), "formal upper-tail screen", values, required=False),
        _card("selection.consequence_summary", "Scientist action", _display_text(values["selection.consequence_summary"]), "final report consequence", values),
    )
    packet = DiagnosticEvidencePacket(
        packet_id=f"{finding.finding_id}:packet",
        finding_id=finding.finding_id,
        run_id=run_id,
        method_id=method_id,
        contract_id=contract_id,
        values=values,
        missing_required_keys=tuple(key for key in ("curve_family.metric", "curve_family.value", "selection.consequence_summary") if _missing(values.get(key))),
    )
    return DiagnosticCockpitView(
        view_id="iso14126_curve_family_wizard_acceptance",
        finding=finding,
        evidence_packet=packet,
        cards=cards,
        plot_contract=DiagnosticPlotContract(
            plot_kind="curve_family",
            title="Curve-family comparison",
            x_axis_label="Normalised strain / %",
            y_axis_label="Stress",
            required_layers=("focus_curve", "cohort_curves", "reference_curve"),
            semantic_layers=("all_evaluable_curves", "reference_curve", "outlier_candidate_curves"),
            layout_policy=_compact_layout_policy(),
            missing_required_keys=() if values.get("plot.curve_family_curve") else ("plot.curve_family_curve",),
        ),
        decision=_decision_spec(payload, default_decision=finding.default_decision),
        missing_evidence_policy=_missing_policy(),
    )


def _unsupported_cockpit(payload: Mapping[str, Any], *, method_id: str, run_id: str) -> DiagnosticCockpitView:
    contract_id = get_evidence_contract("validation_check").contract_id
    default_decision = _decision_type(payload)
    finding = DiagnosticFinding(
        finding_id=f"{run_id}:unsupported_diagnostic",
        method_id=method_id,
        run_id=run_id,
        defect_type="unsupported_diagnostic",
        data_kind="unknown",
        severity=_primary_severity(payload),
        default_decision=default_decision,
        evidence_contract_id=contract_id,
    )
    values = {
        "diagnostic.message": payload.get("reason") or payload.get("diagnostic_reason"),
        "selection.consequence_summary": _consequence_summary(payload),
    }
    packet = DiagnosticEvidencePacket(
        packet_id=f"{finding.finding_id}:packet",
        finding_id=finding.finding_id,
        run_id=run_id,
        method_id=method_id,
        contract_id=contract_id,
        values=values,
        missing_required_keys=("diagnostic.view_contract",),
    )
    return DiagnosticCockpitView(
        view_id="unsupported_diagnostic_wizard_acceptance",
        finding=finding,
        evidence_packet=packet,
        cards=(
            DiagnosticCard(
                evidence_key="diagnostic.view_contract",
                label="Diagnostic cockpit",
                value="Evidence unavailable",
                subtext="Missing required evidence: diagnostic.view_contract",
                state="gap",
                level="warn",
            ),
            _card("selection.consequence_summary", "Decision consequence", _display_text(values["selection.consequence_summary"]), "final report selection", values),
        ),
        plot_contract=DiagnosticPlotContract(
            plot_kind="unsupported",
            title="Diagnostic evidence unavailable",
            x_axis_label="",
            y_axis_label="",
            required_layers=(),
            semantic_layers=(),
            layout_policy=_compact_layout_policy(),
            missing_required_keys=("diagnostic.view_contract",),
        ),
        decision=_decision_spec(payload, default_decision=default_decision),
        missing_evidence_policy=_missing_policy(),
    )


def diagnostic_view_registry() -> DiagnosticViewRegistry:
    bending_contract = get_evidence_contract("bending_diagnostic").contract_id
    return DiagnosticViewRegistry(
        (
            ViewSpec(
                view_id="iso14126_bending_wizard_acceptance",
                method_id=METHOD_ID,
                defect_type="sustained_bending",
                data_kind="bending_percent_curve",
                surface_role=SURFACE_ROLE,
                evidence_contract_id=bending_contract,
                plot_kind="bending_evidence",
                plot_title="Bending evidence",
                x_axis_label="Load / N",
                y_axis_label="Bending / %",
                required_plot_keys=("plot.bending_curve", "bending.threshold_percent"),
                required_layers=(
                    "bending_percent_series",
                    "threshold_line",
                    "assessment_window_10_90_fmax",
                    "exceedance_points",
                    "exceedance_segments",
                ),
                semantic_layers=(
                    "bending_percent_series",
                    "context_bending_series",
                    "threshold_line",
                    "threshold_annotation",
                    "assessment_window_10_90_fmax",
                    "exceedance_points",
                    "exceedance_segments",
                    "classification_marker",
                ),
                cards=(
                    CardSpec("bending.classification", "Bending call", "text", subtext="pattern assessment in 10-90% Fmax window"),
                    CardSpec("bending.max_percent", "Peak imbalance", "percent", subtext="maximum opposite-face strain imbalance"),
                    CardSpec("bending.threshold_percent", "Review limit", "percent", subtext="configured ISO 14126 bending threshold"),
                    CardSpec("bending.points_above_threshold", "Persistence", "count", subtext="points above limit in assessment window"),
                    CardSpec("bending.fraction_above_threshold", "Window share", "share_percent", subtext="share of assessed load window"),
                    CardSpec("bending.longest_exceedance_segment", "Longest segment", "text", subtext="contiguous exceedance evidence"),
                    CardSpec("selection.consequence_summary", "Scientist action", "text", subtext="final report consequence"),
                ),
                layout_policy=_compact_layout_policy(),
            ),
        )
    )


def _cards_from_spec(spec: ViewSpec, values: Mapping[str, Any]) -> tuple[DiagnosticCard, ...]:
    return tuple(
        _card(
            card.evidence_key,
            card.label,
            _format_value(values.get(card.evidence_key), card.formatter),
            _card_subtext(card, values),
            values,
            required=card.required,
        )
        for card in spec.cards
    )


def _card_subtext(card: CardSpec, values: Mapping[str, Any]) -> str:
    if card.evidence_key == "bending.fraction_above_threshold":
        points = _int_or_none(values.get("bending.points_above_threshold"))
        total = _int_or_none(values.get("bending.assessed_points"))
        if points is not None and total is not None:
            return f"{points} of {total} assessed points above limit"
    return card.subtext


def _card(
    evidence_key: str,
    label: str,
    value: str,
    subtext: str,
    values: Mapping[str, Any],
    *,
    required: bool = True,
) -> DiagnosticCard:
    if required and _missing(values.get(evidence_key)):
        return DiagnosticCard(
            evidence_key=evidence_key,
            label=label,
            value="Evidence unavailable",
            subtext=f"Missing required evidence: {evidence_key}",
            state="gap",
            level="warn",
            required=required,
        )
    return DiagnosticCard(
        evidence_key=evidence_key,
        label=label,
        value=value,
        subtext=subtext,
        state="ok",
        level="warn" if evidence_key.startswith("bending.") else "info",
        required=required,
    )


def _bending_values(payload: Mapping[str, Any]) -> dict[str, Any]:
    assessed_points = _int_or_none(payload.get("bending_assessed_points"))
    points_above = _int_or_none(payload.get("bending_points_above_threshold"))
    fraction = _float_or_none(payload.get("bending_fraction_above_threshold"))
    if fraction is None and assessed_points and points_above is not None:
        fraction = points_above / assessed_points
    longest = payload.get("bending_longest_segment")
    if _missing(longest):
        longest_points = _int_or_none(payload.get("bending_longest_segment_points"))
        longest_fraction = _float_or_none(payload.get("bending_longest_segment_fraction"))
        longest_type = str(payload.get("bending_longest_segment_classification") or "").strip()
        if longest_points is not None:
            longest = f"{longest_points} point{'s' if longest_points != 1 else ''}"
            if longest_fraction is not None:
                longest += f" ({_display_share_percent(longest_fraction)} of window)"
            if longest_type:
                longest += f" - {longest_type.replace('_', ' ')}"
        elif points_above == 0:
            longest = "0 points - no contiguous exceedance"
    curve = payload.get("bending_trace_points") or payload.get("bending_series")
    classification = (
        payload.get("bending_classification")
        or payload.get("bending_pattern_classification")
        or payload.get("bending_pattern")
        or payload.get("failure_mode")
    )
    return {
        "bending.max_percent": payload.get("bending_peak"),
        "bending.threshold_percent": payload.get("bending_threshold"),
        "bending.points_above_threshold": points_above,
        "bending.assessed_points": assessed_points,
        "bending.fraction_above_threshold": fraction,
        "bending.longest_exceedance_segment": longest,
        "bending.classification": classification,
        "selection.consequence_summary": _consequence_summary(payload),
        "plot.bending_curve": curve,
    }


def _required_value_keys(spec: ViewSpec) -> tuple[str, ...]:
    return tuple(card.evidence_key for card in spec.cards if card.required)


def _format_value(value: Any, formatter: str) -> str:
    if formatter == "percent":
        return _display_percent(value)
    if formatter == "count":
        return _display_count(value)
    if formatter == "fraction":
        return _display_fraction(value)
    if formatter == "share_percent":
        return _display_share_percent(value)
    if formatter == "number":
        return _display_number(value)
    return _display_text(value)


def _display_percent(value: Any) -> str:
    number = _float_or_none(value)
    return "" if number is None else f"{number:.3g}%"


def _display_count(value: Any) -> str:
    number = _int_or_none(value)
    if number is None:
        return ""
    return f"{number:g}"


def _display_fraction(value: Any) -> str:
    number = _float_or_none(value)
    if number is None:
        return ""
    return f"{number:.3g}"


def _display_share_percent(value: Any) -> str:
    number = _float_or_none(value)
    if number is None:
        return ""
    return f"{number * 100:.3g}%"


def _display_number(value: Any) -> str:
    number = _float_or_none(value)
    if number is None:
        return ""
    return f"{number:.3g}"


def _display_text(value: Any) -> str:
    text = str(value or "").replace("_", " ").strip()
    return text


def _threshold_sub(value: Any) -> str:
    threshold = _display_number(value)
    return f"threshold {threshold}" if threshold else "threshold unavailable"


def _metric_context(values: Mapping[str, Any]) -> str:
    reason = _display_text(values.get("curve_family.reason"))
    if reason:
        return reason
    return _threshold_sub(values.get("curve_family.threshold"))


def _metric_summary(metric: Any, value: Any) -> str:
    metric_text = _display_text(metric) or "metric"
    value_text = _display_number(value)
    return f"{metric_text} {value_text}".strip()


def _robust_screen_text(values: Mapping[str, Any]) -> str:
    robust_z = _display_number(values.get("curve_family.robust_z"))
    robust_threshold = _display_number(values.get("curve_family.robust_threshold"))
    masking = values.get("curve_family.masking_risk")
    if robust_z and robust_threshold and masking not in (None, ""):
        return f"z {robust_z} vs {robust_threshold}; masking {_yes_no(masking)}"
    if robust_z and robust_threshold:
        return f"z {robust_z} vs {robust_threshold}"
    if robust_z and masking not in (None, ""):
        return f"z {robust_z}; masking {_yes_no(masking)}"
    if robust_z:
        return f"z {robust_z}"
    if masking not in (None, ""):
        return f"masking {_yes_no(masking)}"
    return ""


def _outlier_test_text(values: Mapping[str, Any]) -> str:
    decision = _display_text(values.get("curve_family.dixon_decision"))
    threshold = _display_number(values.get("curve_family.outlier_limit") or values.get("curve_family.threshold"))
    if decision and threshold:
        return f"{decision}; limit {threshold}"
    return decision or (f"limit {threshold}" if threshold else "")


def _yes_no(value: Any) -> str:
    return "yes" if str(value).strip().casefold() in {"1", "true", "yes", "y"} else "no"


def _compact_layout_policy() -> dict[str, Any]:
    return {
        "prevent_axis_label_clipping": True,
        "minimum_width_px": 360,
        "minimum_height_px": 176,
        "left_axis_margin_px": 44,
        "bottom_axis_margin_px": 34,
        "expanded_view_action": "open_audit_report",
    }


def _decision_spec(payload: Mapping[str, Any], *, default_decision: str) -> dict[str, Any]:
    return {
        "default_decision": default_decision,
        "allowed_actions": ["remove", "keep_with_justification"],
        "override_requires_justification": default_decision == "remove",
        "consequence_summary": _consequence_summary(payload),
        "audit_record_fields": ["run_id", "decision_type", "reason", "reviewer", "final_included"],
    }


def _consequence_summary(payload: Mapping[str, Any]) -> str:
    default_decision = _decision_type(payload)
    if default_decision == "remove":
        return "Excluded from final report unless kept with justification"
    return "Included in final report unless removed by operator"


def _decision_type(payload: Mapping[str, Any]) -> str:
    default_call = str(payload.get("default_call") or payload.get("default") or "").strip().casefold()
    if default_call.startswith("keep"):
        return "keep"
    return "remove"


def _missing_policy() -> dict[str, Any]:
    return {
        "required_missing": "evidence_gap_warning",
        "optional_missing": "omit_or_mark_optional",
        "not_applicable": "explicit_reason",
        "block_silent_na": True,
    }


def _primary_severity(payload: Mapping[str, Any]) -> str:
    flags = payload.get("acceptance_flags")
    if isinstance(flags, list) and flags:
        first = flags[0] if isinstance(flags[0], Mapping) else {}
        return str(first.get("severity") or "review")
    return "review"


def _evidence_kind_from_flags(payload: Mapping[str, Any]) -> str:
    flags = payload.get("acceptance_flags")
    if isinstance(flags, list):
        for flag in flags:
            if not isinstance(flag, Mapping):
                continue
            text = " ".join(str(flag.get(key) or "") for key in ("category", "flag_id", "source", "evidence_refs")).casefold()
            if "curve_family" in text or "curve_shape" in text:
                return "curve_family"
            if "bending" in text:
                return "bending"
    return "bending" if _has_bending_context(payload) else "unsupported"


def _has_bending_context(payload: Mapping[str, Any]) -> bool:
    return any(
        not _missing(payload.get(key))
        for key in (
            "bending_series",
            "bending_trace_points",
            "bending_peak",
            "bending_threshold",
            "bending_points_above_threshold",
            "bending_assessed_points",
            "bending_pattern",
            "bending_classification",
        )
    )


def _missing(value: Any) -> bool:
    return value in (None, "", (), [])


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    number = _float_or_none(value)
    return None if number is None else int(number)
