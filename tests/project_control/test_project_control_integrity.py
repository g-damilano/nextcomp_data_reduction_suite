from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CONTROL = ROOT / "docs" / "project_control"


def test_project_control_records_exist() -> None:
    required = [
        "README.md",
        "BACKLOG.md",
        "STAGE_LEDGER.yaml",
        "OPEN_RISKS.md",
        "COMPLETION_CRITERIA.md",
        "TESTING_POLICY.md",
        "SCAFFOLD_CLASSIFICATION.yaml",
        "CLUSTER_LEDGER.yaml",
        "CLUSTER_VALIDATION_PROTOCOL.md",
        "CLUSTER_VALIDATION_REPORT_TEMPLATE.md",
        "CROSS_IMPACT_MATRIX.md",
        "stage_records/STAGE_10_OPERATOR_REPORTING_MATURATION.md",
        "stage_records/STAGE_10_5_GENERIC_REPORTING_ENGINE.md",
        "stage_records/STAGE_11_OPERATOR_EVIDENCE_SURFACES.md",
        "stage_records/STAGE_12_HUMAN_ACCEPTANCE_OVERRIDE.md",
        "stage_records/STAGE_13_AUDIT_TEST_REPORT_SURFACE_CONSOLIDATION.md",
        "stage_records/STAGE_14_CURVE_FAMILY_ACCEPTANCE.md",
        "stage_records/STAGE_14_5_CLUSTER_VALIDATION.md",
        "stage_records/STAGE_15_OPERATOR_SURFACE_CLUSTER_CLOSURE.md",
        "stage_records/STAGE_16_FOUNDATION_CLUSTER_CLOSURE.md",
        "stage_records/STAGE_17_INPUT_METADATA_REPORT_COMPLETENESS.md",
        "stage_records/STAGE_17_5_METADATA_DEDUP_MARKER_CLOSURE.md",
        "stage_records/STAGE_18_REPORT_COMPLETION_AUTHORING.md",
        "stage_records/STAGE_19_REPORT_AUTHORING_FINALIZATION.md",
        "stage_records/STAGE_20_METHOD_INPUT_BINDING_COMPATIBILITY.md",
        "stage_records/STAGE_21_MTDA_FINALIZATION_AMENDMENT.md",
        "stage_records/STAGE_22_PRODUCTION_EXPORT.md",
        "stage_records/STAGE_23_REPORT_AUDIT_RC_SURFACE_CLOSURE.md",
        "stage_records/STAGE_24_REPORT_AUDIT_RC_CONTENT_CLOSURE.md",
        "stage_records/STAGE_25_EXPERIMENT_BOUNDARY_RESOLUTION.md",
        "stage_records/STAGE_25_RC_PACKAGING_UAT.md",
    ]

    for relative in required:
        assert (CONTROL / relative).exists(), relative


def test_stage_ledger_has_required_fields_for_each_stage() -> None:
    ledger = yaml.safe_load((CONTROL / "STAGE_LEDGER.yaml").read_text(encoding="utf-8"))

    assert ledger["stage_ledger_schema"] == "project.stage_ledger.v0_1"
    assert ledger["verification_command"] == "python -m pytest -q"
    assert "Generated MTDP/MTDA" in ledger["generated_artifact_policy"]

    required_stage_keys = {
        "id",
        "title",
        "status",
        "implemented_files",
        "tests",
        "artifacts",
        "known_gaps",
        "next_actions",
    }
    for stage in ledger["stages"]:
        assert required_stage_keys <= set(stage), stage["id"]

    stages = {stage["id"]: stage for stage in ledger["stages"]}
    assert stages["stage_10_operator_reporting_maturation"]["status"] == "implemented_architecturally_partial"
    assert stages["stage_10_5_generic_reporting_engine"]["status"] == "verified"
    assert stages["stage_11_operator_evidence_surfaces"]["status"] == "verified"
    assert stages["stage_12_human_acceptance_override"]["status"] == "implemented_with_residuals"
    assert stages["stage_13_audit_test_report_surface_consolidation"]["status"] == "verified"
    assert stages["stage_14_curve_family_acceptance"]["status"] == "verified"
    assert stages["stage_14_5_cluster_validation"]["status"] == "validated_closed_with_residuals"
    assert stages["stage_15_operator_surface_cluster_closure"]["status"] == "validated_closed_with_residuals"
    assert stages["stage_16_foundation_cluster_closure"]["status"] == "validated_closed"
    assert stages["stage_17_input_metadata_report_completeness"]["status"] == "implemented_with_residuals"
    assert stages["stage_17_5_metadata_dedup_marker_closure"]["status"] == "validated_closed_with_residuals"
    assert stages["stage_18_report_completion_authoring"]["status"] == "validated_closed_with_residuals"
    assert stages["stage_19_report_authoring_finalization"]["status"] == "validated_closed_with_residuals"
    assert stages["stage_20_method_input_binding_compatibility"]["status"] == "validated_closed_with_residuals"
    assert stages["stage_21_mtda_finalization_amendment"]["status"] == "validated_closed_with_residuals"
    assert stages["stage_22_production_export"]["status"] == "validated_closed_with_residuals"
    assert stages["stage_23_report_audit_rc_surface_closure"]["status"] == "validated_closed_with_residuals"
    assert stages["stage_24_report_audit_rc_content_closure"]["status"] == "validated_closed_with_residuals"
    assert stages["stage_25_experiment_boundary_resolution"]["status"] == "validated_closed_with_residuals"
    assert stages["stage_25_rc_packaging_uat"]["status"] == "validated_closed_with_residuals"
    assert "src/reporting/core/" in stages["stage_10_5_generic_reporting_engine"]["implemented_files"]
    assert "docs/project_control/" in stages["stage_10_5_generic_reporting_engine"]["implemented_files"]
    assert "src/reporting/renderers/html_renderer.py" in stages["stage_11_operator_evidence_surfaces"]["implemented_files"]
    assert "tests/method_run/test_stage14_5_cluster_validation.py" in stages["stage_14_5_cluster_validation"]["tests"]
    assert "tests/method_run/test_stage15_operator_surface_cluster.py" in stages["stage_15_operator_surface_cluster_closure"]["tests"]
    assert "tests/mtdp/test_stage16_input_package_cluster.py" in stages["stage_16_foundation_cluster_closure"]["tests"]
    assert "tests/method_run/test_stage16_method_execution_cluster.py" in stages["stage_16_foundation_cluster_closure"]["tests"]
    assert "tests/mtdp/test_stage17_metadata_sections.py" in stages["stage_17_input_metadata_report_completeness"]["tests"]
    assert "tests/method_run/test_stage17_report_completeness_metadata.py" in stages["stage_17_input_metadata_report_completeness"]["tests"]
    assert "tests/mtdp/test_stage17_5_metadata_dedup.py" in stages["stage_17_5_metadata_dedup_marker_closure"]["tests"]
    assert "tests/reporting/test_report_completion.py" in stages["stage_18_report_completion_authoring"]["tests"]
    assert "tests/mtdp/test_stage18_metadata_completion_ui.py" in stages["stage_18_report_completion_authoring"]["tests"]
    assert "tests/reporting/test_report_authoring_view_model.py" in stages["stage_19_report_authoring_finalization"]["tests"]
    assert "tests/method_run/test_stage20_method_input_binding_compatibility.py" in stages["stage_20_method_input_binding_compatibility"]["tests"]
    assert "tests/method_run/test_stage21_mtda_finalization.py" in stages["stage_21_mtda_finalization_amendment"]["tests"]
    assert "tests/method_run/test_stage22_production_export.py" in stages["stage_22_production_export"]["tests"]
    assert "tests/export/test_export_service.py" in stages["stage_22_production_export"]["tests"]
    assert "tests/method_run/test_stage23_report_rc_surfaces.py" in stages["stage_23_report_audit_rc_surface_closure"]["tests"]
    assert "metadata/surface_manifest.json" in stages["stage_23_report_audit_rc_surface_closure"]["artifacts"]
    assert "tests/method_run/test_stage24_report_audit_rc_content.py" in stages["stage_24_report_audit_rc_content_closure"]["tests"]
    assert "metadata/software/validation.json:report_quality_gate" in stages["stage_24_report_audit_rc_content_closure"]["artifacts"]
    assert "tests/method_run/test_stage25_experiment_boundary_resolution.py" in stages["stage_25_experiment_boundary_resolution"]["tests"]
    assert "audit/boundary_resolution.json" in stages["stage_25_experiment_boundary_resolution"]["artifacts"]
    assert "tests/release/test_stage25_rc_packaging.py" in stages["stage_25_rc_packaging_uat"]["tests"]
    assert "release_candidate/rc_release_manifest.json" in stages["stage_25_rc_packaging_uat"]["artifacts"]


def test_cluster_ledger_records_foundation_cluster_closure() -> None:
    ledger = yaml.safe_load((CONTROL / "CLUSTER_LEDGER.yaml").read_text(encoding="utf-8"))

    clusters = {cluster["id"]: cluster for cluster in ledger["clusters"]}
    input_cluster = clusters["cluster_input_package"]
    method_cluster = clusters["cluster_method_execution"]

    assert input_cluster["status"] == "validated_closed"
    assert input_cluster["validation_stage"] == "stage_16_foundation_cluster_closure"
    assert input_cluster["validation_report"] == "docs/project_control/stage_records/STAGE_16_FOUNDATION_CLUSTER_CLOSURE.md"
    assert "schema_metadata_survives_package_generation" in input_cluster["required_scenarios"]
    assert "provenance.json" in input_cluster["artifacts_inspected"]

    assert method_cluster["status"] == "validated_closed"
    assert method_cluster["validation_stage"] == "stage_16_foundation_cluster_closure"
    assert method_cluster["validation_report"] == "docs/project_control/stage_records/STAGE_16_FOUNDATION_CLUSTER_CLOSURE.md"
    assert "mapping_failure_caught_before_resolve" in method_cluster["required_scenarios"]
    assert "metadata/provenance.json" in method_cluster["artifacts_inspected"]


def test_cluster_ledger_records_input_metadata_report_completeness() -> None:
    ledger = yaml.safe_load((CONTROL / "CLUSTER_LEDGER.yaml").read_text(encoding="utf-8"))

    clusters = {cluster["id"]: cluster for cluster in ledger["clusters"]}
    cluster = clusters["cluster_input_metadata_report_completeness"]

    assert cluster["status"] == "validated_closed_with_residuals"
    assert cluster["validation_stage"] == "stage_19_report_authoring_finalization"
    assert cluster["validation_report"] == "docs/project_control/stage_records/STAGE_19_REPORT_AUTHORING_FINALIZATION.md"
    assert "mtdp_export_reload_preserves_expanded_metadata" in cluster["required_scenarios"]
    assert "report_values_resolve_by_report_role" in cluster["required_scenarios"]
    assert "metadata_sections_reference_canonical_fields_without_duplication" in cluster["required_scenarios"]
    assert "report_value_source_precedence_and_provenance" in cluster["required_scenarios"]
    assert "operator_can_author_report_only_overrides_without_json_editing" in cluster["required_scenarios"]
    assert "report/report_values_used.csv" in cluster["artifacts_inspected"]
    assert "report/report_field_catalog_resolved.json" in cluster["artifacts_inspected"]
    assert "audit/audit_report.json:report_completion" in cluster["artifacts_inspected"]


def test_cluster_ledger_records_method_input_binding_compatibility() -> None:
    ledger = yaml.safe_load((CONTROL / "CLUSTER_LEDGER.yaml").read_text(encoding="utf-8"))

    clusters = {cluster["id"]: cluster for cluster in ledger["clusters"]}
    cluster = clusters["cluster_method_input_binding_compatibility"]

    assert cluster["status"] == "validated_closed_with_residuals"
    assert cluster["validation_stage"] == "stage_20_method_input_binding_compatibility"
    assert cluster["validation_report"] == "docs/project_control/stage_records/STAGE_20_METHOD_INPUT_BINDING_COMPATIBILITY.md"
    assert "schema_method_compatibility_is_recorded_separately_from_readiness" in cluster["required_scenarios"]
    assert "mapping/mapping_profile_used.json" in cluster["artifacts_inspected"]
    assert "compatibility/schema_method_compatibility_report.json" in cluster["artifacts_inspected"]


def test_cluster_ledger_records_mtda_finalization_amendment() -> None:
    ledger = yaml.safe_load((CONTROL / "CLUSTER_LEDGER.yaml").read_text(encoding="utf-8"))

    clusters = {cluster["id"]: cluster for cluster in ledger["clusters"]}
    cluster = clusters["cluster_mtda_finalization_amendment"]

    assert cluster["status"] == "validated_closed_with_residuals"
    assert cluster["validation_stage"] == "stage_21_mtda_finalization_amendment"
    assert cluster["validation_report"] == "docs/project_control/stage_records/STAGE_21_MTDA_FINALIZATION_AMENDMENT.md"
    assert "report_only_override_updates_report_audit_checksums_provenance" in cluster["required_scenarios"]
    assert "finalization/finalization_report.json" in cluster["artifacts_inspected"]
    assert "checksums.json" in cluster["artifacts_inspected"]


def test_cluster_ledger_records_product_export_closure() -> None:
    ledger = yaml.safe_load((CONTROL / "CLUSTER_LEDGER.yaml").read_text(encoding="utf-8"))

    clusters = {cluster["id"]: cluster for cluster in ledger["clusters"]}
    cluster = clusters["cluster_product_export"]

    assert cluster["status"] == "validated_closed_with_residuals"
    assert cluster["validation_stage"] == "stage_22_production_export"
    assert cluster["validation_report"] == "docs/project_control/stage_records/STAGE_22_PRODUCTION_EXPORT.md"
    assert "full_html_export_includes_reports_tables_figures_manifest" in cluster["required_scenarios"]
    assert "export_manifest.json" in cluster["artifacts_inspected"]
    assert "figures/aggregate_stress_strain.html" in cluster["artifacts_inspected"]


def test_cluster_ledger_records_report_audit_rc_surface_closure() -> None:
    ledger = yaml.safe_load((CONTROL / "CLUSTER_LEDGER.yaml").read_text(encoding="utf-8"))

    clusters = {cluster["id"]: cluster for cluster in ledger["clusters"]}
    cluster = clusters["cluster_report_audit_rc_surface"]

    assert cluster["status"] == "validated_closed_with_residuals"
    assert cluster["validation_stage"] == "stage_24_report_audit_rc_content_closure"
    assert cluster["validation_report"] == "docs/project_control/stage_records/STAGE_24_REPORT_AUDIT_RC_CONTENT_CLOSURE.md"
    assert "surface_manifest_indexes_test_report_audit_report_workbench_and_export_status" in cluster["required_scenarios"]
    assert "report_quality_gate_records_test_and_audit_rc_status" in cluster["required_scenarios"]
    assert "source_method_mapping_final_selection_and_gate_statuses_agree_across_surfaces" in cluster["required_scenarios"]
    assert "metadata/surface_manifest.json" in cluster["artifacts_inspected"]
    assert "metadata/software/validation.json:report_quality_gate" in cluster["artifacts_inspected"]
    assert "dataset/04_reports/test_report.json:aggregate_plot_spec" in cluster["artifacts_inspected"]


def test_cluster_ledger_records_rc_packaging_uat_closure() -> None:
    ledger = yaml.safe_load((CONTROL / "CLUSTER_LEDGER.yaml").read_text(encoding="utf-8"))

    clusters = {cluster["id"]: cluster for cluster in ledger["clusters"]}
    cluster = clusters["cluster_rc_packaging_uat"]

    assert cluster["status"] == "validated_closed_with_residuals"
    assert cluster["validation_stage"] == "stage_25_rc_packaging_uat"
    assert cluster["validation_report"] == "docs/project_control/stage_records/STAGE_25_RC_PACKAGING_UAT.md"
    assert "source_mode_resource_resolution_finds_registry_methods_mappings_schemas_and_assets" in cluster["required_scenarios"]
    assert "packaged_layout_simulation_resolves_bundled_resources" in cluster["required_scenarios"]
    assert "release_candidate/rc_release_manifest.json" in cluster["artifacts_inspected"]
    assert "docs/release/RC_UAT_SMOKE_SCRIPT.md" in cluster["artifacts_inspected"]


def test_cluster_ledger_records_boundary_resolution_closure() -> None:
    ledger = yaml.safe_load((CONTROL / "CLUSTER_LEDGER.yaml").read_text(encoding="utf-8"))

    clusters = {cluster["id"]: cluster for cluster in ledger["clusters"]}
    cluster = clusters["cluster_experiment_boundary_resolution"]

    assert cluster["status"] == "validated_closed_with_residuals"
    assert cluster["validation_stage"] == "stage_25_experiment_boundary_resolution"
    assert cluster["validation_report"] == "docs/project_control/stage_records/STAGE_25_EXPERIMENT_BOUNDARY_RESOLUTION.md"
    assert "run006_endpoint_uses_slope_break_pre_negative_policy" in cluster["required_scenarios"]
    assert "aggregation_uses_experiment_progress_from_resolved_boundaries" in cluster["required_scenarios"]
    assert "audit/boundary_resolution.json" in cluster["artifacts_inspected"]
    assert "method_outputs/boundaries.csv" in cluster["artifacts_inspected"]


def test_cluster_ledger_records_selection_reporting_closure() -> None:
    ledger = yaml.safe_load((CONTROL / "CLUSTER_LEDGER.yaml").read_text(encoding="utf-8"))

    assert ledger["cluster_ledger_schema"] == "project.cluster_ledger.v0_1"
    assert ledger["verification_command"] == "python -m pytest -q"
    clusters = {cluster["id"]: cluster for cluster in ledger["clusters"]}
    cluster = clusters["cluster_selection_reporting_scientific_assessment"]

    assert cluster["status"] == "validated_closed_with_residuals"
    assert cluster["validation_stage"] == "stage_14_5_cluster_validation"
    assert "human_removes_accepted_run" in cluster["required_scenarios"]
    assert "curve_family_flag_propagation" in cluster["required_scenarios"]
    assert "report/aligned_curves.csv" in cluster["artifacts_inspected"]
    assert cluster["validation_report"] == "docs/project_control/stage_records/STAGE_14_5_CLUSTER_VALIDATION.md"


def test_cluster_ledger_records_operator_surface_closure() -> None:
    ledger = yaml.safe_load((CONTROL / "CLUSTER_LEDGER.yaml").read_text(encoding="utf-8"))

    clusters = {cluster["id"]: cluster for cluster in ledger["clusters"]}
    cluster = clusters["cluster_operator_surface"]

    assert cluster["status"] == "validated_closed_with_residuals"
    assert cluster["validation_stage"] == "stage_15_operator_surface_cluster_closure"
    assert cluster["validation_report"] == "docs/project_control/stage_records/STAGE_15_OPERATOR_SURFACE_CLUSTER_CLOSURE.md"
    assert "mapping_bindings_are_operator_readable" in cluster["required_scenarios"]
    assert "metadata/software/method_outputs.json:final_report_runs" in cluster["artifacts_inspected"]


def test_backlog_records_residual_wizard_and_acceptance_gaps() -> None:
    backlog = (CONTROL / "BACKLOG.md").read_text(encoding="utf-8")

    assert "GAP-003 - Wizard UX Maturity" in backlog
    assert "GAP-006 - Human Acceptance Overrides and Selection Editing" in backlog
    assert "GAP-016 - Output Surface Separation" in backlog
    assert "GAP-018 - Curve-Family Evidence Surfaces" in backlog
    assert "GAP-019 - Cluster Validation Discipline" in backlog
    assert "validated_closed_with_residuals_stage15" in backlog
    assert "GAP-020 - Foundation Cluster Validation" in backlog
    assert "validated_closed_stage16" in backlog
    assert "GAP-009 - ISO Report Completeness" in backlog
    assert "validated_closed_with_residuals_stage19" in backlog
    assert "GAP-021 - Method Input Binding and Schema Compatibility" in backlog
    assert "validated_closed_with_residuals_stage20" in backlog
    assert "GAP-022 - MTDA Finalization and Archive Amendment" in backlog
    assert "validated_closed_with_residuals_stage21" in backlog
    assert "GAP-014 - Production Export" in backlog
    assert "validated_closed_with_residuals_stage22" in backlog
    assert "GAP-023 - Second Method Proof" in backlog
    assert "deferred_stage23" in backlog
    assert "validated_closed_with_residuals_stage24" in backlog
    assert "report/report_quality_gate.json" in backlog
    assert "GAP-024 - RC Packaging and UAT Operationalization" in backlog
    assert "validated_closed_with_residuals_stage25" in backlog
    assert "validated_closed_with_residuals_stage25_boundary" in backlog
    assert "GAP-025 - Experiment Boundary Resolution" in backlog
    assert "rc_release_manifest.json" in backlog
    assert "reconciled_stage14" in backlog
    assert "reconciled_stage14_5" in backlog
    assert "partially_reconciled_stage12" in backlog
    assert "python -m pytest -q" in backlog


def test_legacy_scaffolds_are_classified_outside_active_architecture() -> None:
    classification = yaml.safe_load(
        (CONTROL / "SCAFFOLD_CLASSIFICATION.yaml").read_text(encoding="utf-8")
    )
    items = {item["path"]: item for item in classification["items"]}

    for path in [
        "src/parsing/columns/header_tokenizer.py",
        "src/method_binding/channel_resolver.py",
    ]:
        item = items[path]
        assert item["classification"] == "obsolete_deferred_scaffold"
        assert item["active_architecture"] is False
        source = (ROOT / path).read_text(encoding="utf-8")
        assert "docs/project_control/SCAFFOLD_CLASSIFICATION.yaml" in source
