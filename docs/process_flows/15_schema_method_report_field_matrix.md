# Schema, Method, and Report Field Matrix

## Scope

This document maps the compression MTDP schema fields into their main downstream responsibilities: MTDP validity, method readiness, ISO method execution, formal report completion, ISO deviation handling, and failure-analysis reporting.

This is not a replacement for the schema YAML. It is a navigation matrix for development and review.

## Source anchors

| Flow area | Code anchor |
|---|---|
| Compression schema | `src/mtdp_enrichment/schema_library/mechanical/compression/0.3.0.yaml` |
| Schema model | `src/mtdp_enrichment/package/schema.py` |
| Field definition model | `src/mtdp_enrichment/models/field_definition.py` |
| ISO 14126 method inputs | `src/methods/iso14126/method_inputs.yaml` |
| ISO 14126 resolve recipe | `src/methods/iso14126/resolve_recipe.yaml` |
| Report value resolver | `src/reporting/completion/report_value_resolver.py` |
| Report engine ISO additions | `src/reporting/core/report_engine.py` |

---

## L2 — Field responsibility layers

```mermaid
flowchart TB
    SchemaField["Compression schema field"] --> MTDPValidity["MTDP validation"]
    SchemaField --> Storage["Archive storage route"]
    SchemaField --> UISection["UI metadata section"]
    SchemaField --> ImportAliases["YAML/parser import aliases"]
    SchemaField --> MethodRole["Method mapping/readiness role"]
    SchemaField --> ReportRole["Formal report role"]
    SchemaField --> ISOStatus["ISO-compliant/deviation value status"]

    MTDPValidity --> Package[".mtdp package"]
    Storage --> Package
    Package --> Readiness["method_inputs readiness"]
    Package --> Resolve["resolve_recipe map_scalar/map_channel"]
    Package --> ReportResolver["ReportValueResolver"]
    ISOStatus --> Deviations["deviations_from_standard / missing ISO-controlled choice details"]
```

## Gate distinction

| Gate | Meaning |
|---|---|
| MTDP required | Field must exist for package export. |
| Method execution-critical | Field/channel must exist for method execution. |
| Report required | Field is required for formal report completion. |
| Report recommended | Missing field is surfaced but does not necessarily block formal use. |
| ISO compliant/deviation | Specific controlled values determine whether a report value is standard-compliant or a deviation. |
| Failure-analysis required for accepted runs | Field may be required only for runs included in final report statistics. |

---

## L2 — Dataset field groups

```mermaid
flowchart TB
    Dataset["Dataset fields"] --> Overview["Overview"]
    Dataset --> TestID["Test Identification"]
    Dataset --> Material["Material Identification"]
    Dataset --> Prep["Specimen Preparation"]
    Dataset --> Fixture["Loading Fixture"]
    Dataset --> Conditions["Test Conditions"]
    Dataset --> Measurement["Measurement Method"]
    Dataset --> Remarks["Deviations / Remarks"]

    Overview --> SampleType["sample_type required"]
    TestID --> LoadingMethod["loading_method required report field"]
    TestID --> SpecimenType["specimen_type required report field"]
    Measurement --> StrainMethod["strain_measurement_method required report field"]
    Conditions --> Speed["speed_of_testing recommended"]
```

## Dataset matrix

| Field group | Key fields | Storage | Report role / importance | Method relevance |
|---|---|---|---|---|
| Overview | `sample_type`, `treatment`, `material_label` | `dataset_json` | sample type required; treatment/material recommended | Group identity and report identity. |
| Test Identification | `test_id`, `report_operator`, `loading_method`, `loading_method_other`, `specimen_type`, `specimen_type_other` | `dataset_json.report.test_identification.*` | loading method and specimen type required; operator/test ID recommended | Loading/specimen type influence ISO report/deviation status. |
| Material Identification | material type, matrix, reinforcement, manufacturer, code, source, form, history | `dataset_json.report.material.*` | mostly recommended | Report completeness. |
| Specimen Preparation | cutting direction, fibre orientation, layup, preparation, end tabs, surface preparation, notes | `dataset_json.report.specimen_preparation.*` | mostly recommended | Report completeness; end-tab context. |
| Loading Fixture | fixture type, standard reference, manufacturer/design, alignment, notes | `dataset_json.report.fixture.*` | fixture type/design/alignment recommended | Report completeness and method context. |
| Test Conditions | conditioning, temperature, humidity, conditioning time, environment, speed | `dataset_json.report.test_conditions.*` | mostly recommended | Speed is report-completeness readiness input. |
| Measurement Method | strain measurement method, location, acquisition system, sampling rate, notes | `dataset_json.report.measurement.*` | strain measurement method required; others recommended/optional | Strain method is report-completeness readiness input. |
| Deviations / Remarks | deviations from standard, remarks | `dataset_json.report.*` | optional | ISO explanation context. |

---

## L3 — ISO-controlled dataset choices

```mermaid
flowchart TB
    Controlled["ISO-controlled dataset fields"] --> Loading["loading_method"]
    Controlled --> Specimen["specimen_type"]

    Loading --> Method1["method_1_shear_loading<br/>ISO-compliant"]
    Loading --> Method2["method_2_combined_loading<br/>ISO-compliant"]
    Loading --> LoadingOther["other_specified<br/>deviation, detail required"]
    LoadingOther --> LoadingDetail["loading_method_other"]

    Specimen --> TypeA["type_a<br/>ISO-compliant"]
    Specimen --> TypeB1["type_b1<br/>ISO-compliant"]
    Specimen --> TypeB2["type_b2<br/>ISO-compliant"]
    Specimen --> SpecimenOther["other_specified<br/>deviation, detail required"]
    SpecimenOther --> SpecimenDetail["specimen_type_other"]
```

## Controlled-choice contract

| Field | ISO-compliant values | Deviation value | Detail field |
|---|---|---|---|
| `loading_method` | `method_1_shear_loading`, `method_2_combined_loading` | `other_specified` | `loading_method_other`, required when other specified. |
| `specimen_type` | `type_a`, `type_b1`, `type_b2` | `other_specified` | `specimen_type_other`, required when other specified. |

---

## L2 — Run field groups

```mermaid
flowchart TB
    RunFields["Run fields"] --> Geometry["Specimen Geometry"]
    RunFields --> Acquisition["Run Acquisition Inputs"]
    RunFields --> ChannelSummary["Channel / Preamble Summary"]
    RunFields --> Failure["User Validity / Failure Observation"]

    Geometry --> SpecimenName["specimen_name required"]
    Geometry --> Width["width required / method critical"]
    Geometry --> Thickness["thickness required / method critical"]
    Geometry --> Gauge["gauge_length conditional if extension-derived strain"]

    Acquisition --> TestSpeed["test_speed → speed_of_testing"]
    Acquisition --> Date["test_date → date_of_measurement"]
    Acquisition --> Instrument["instrument model/id/location/load cell/source software"]

    Failure --> PrimaryMode["primary_failure_mode required for accepted runs"]
    Failure --> Location["failure_location required for accepted runs"]
    Failure --> Validity["validity affects acceptance"]
    Failure --> ReviewNotes["failure notes / rejection reason / images"]
```

## Run matrix

| Field group | Key fields | Storage | Report / method role |
|---|---|---|---|
| Specimen Geometry | `specimen_name`, `sample_id`, `width`, `thickness`, `gauge_length`, unsupported/tab dimensions | `token_preamble` | specimen name, width, thickness are package/report-critical; width/thickness are method execution-critical. |
| Acquisition Inputs | `operator`, `instrument_model`, `instrument_id`, `instrument_location`, `load_cell`, `test_speed`, `test_date`, `source_software` | mostly `provenance` | report metadata, report completeness, acquisition context. |
| Channel / Preamble Summary | `run_notes` | provenance | optional report notes. |
| Failure Observation | `primary_failure_mode`, `failure_location`, `invalid_specimen_reason`, `visible_buckling_or_bending_observation`, `failure_image_reference`, `validity`, `requires_review`, `rejection_reason` | mostly `token_preamble` | failure analysis, acceptance, ISO report completion for accepted/final runs. |

---

## L3 — Method-critical fields/channels

```mermaid
flowchart TB
    MethodCritical["ISO 14126 execution-critical requirements"] --> Width["width → width_mm"]
    MethodCritical --> Thickness["thickness → thickness_mm"]
    MethodCritical --> Load["load channel → load_N"]
    MethodCritical --> Front["front_strain channel → front_strain_raw"]
    MethodCritical --> Rear["rear_strain channel → rear_strain_raw"]
    MethodCritical --> Gauge["gauge_length if strain_source == extension_derived"]

    Width --> Area["area_mm2"]
    Thickness --> Area
    Load --> Stress["stress_MPa"]
    Area --> Stress
    Front --> Mean["mean_strain"]
    Rear --> Mean
    Mean --> Modulus["compressive_modulus_MPa"]
    Mean --> FailureStrain["compressive_failure_strain"]
    Front --> Bending["bending_diagnostic"]
    Rear --> Bending
    Load --> Bending
```

## Method-critical matrix

| Requirement | Source role | Method field | Scope | Expected unit | Downstream use |
|---|---|---|---|---|---|
| `iso14126.geometry.width` | width | `specimen.width_mm` | per run | mm | area, stress, strength. |
| `iso14126.geometry.thickness` | thickness | `specimen.thickness_mm` | per run | mm | area, stress, strength. |
| `iso14126.channel.load` | load | `channel.load_N` | per run | N | stress curve, strength, bending window. |
| `iso14126.channel.front_strain` | front_strain | `channel.front_strain` | per run | mm/mm | mean strain, bending, modulus, failure strain. |
| `iso14126.channel.rear_strain` | rear_strain | `channel.rear_strain` | per run | mm/mm | mean strain, bending, modulus, failure strain. |
| `iso14126.geometry.gauge_length_if_extension_strain` | gauge_length | `specimen.gauge_length_mm` | per run | mm | only required when strain source is extension-derived. |

---

## L3 — Report value precedence

```mermaid
flowchart TB
    Catalog["Report field catalog"] --> Resolver["ReportValueResolver.resolve"]
    Overrides["report overrides"] --> Resolver
    Metadata["source MTDP metadata"] --> Resolver
    Base["method/base rows"] --> Resolver
    MethodOutputs["method outputs"] --> Resolver
    Defaults["report defaults"] --> Resolver

    Resolver --> Merge["_merge_by_precedence"]
    Merge --> Values["report_values_used"]
    Catalog --> Missing["_missing_rows"]
    Values --> Missing
    Missing --> Completion["report_completion_status"]
```

## Report-value precedence

1. Report overrides.
2. Source MTDP metadata.
3. Base method/report rows.
4. Method outputs.
5. Report defaults.

This precedence matters: a report override can intentionally supply or correct a formal field without mutating the source MTDP or recalculating method outputs.

---

## L4 — Field lifecycle contract

| Field class | MTDP storage | Method execution | Report use | Special risk |
|---|---|---|---|---|
| Dataset identity | `dataset.json` | Usually not execution-critical | formal identity and grouping | sample type is required for package grouping. |
| ISO controlled choices | `dataset.json.report.test_identification` | not calculation-critical | required report fields and deviation logic | other-specified requires detail. |
| Specimen geometry | token preamble | width/thickness critical | formal geometry and calculated values | numeric/unit coercion and parser-token fallback. |
| Acquisition metadata | provenance or dataset JSON | not calculation-critical | report completion | first available run may satisfy report value. |
| Failure observation | token preamble | not calculation-critical | failure analysis and acceptance | required for accepted/final runs; default not recorded can hide missing observation. |
| Numeric channels | normalized CSV channels | load/front/rear strain critical | curves/results | parser/channel classification and mapping quality. |

## Open residuals

1. A generated CSV table listing every schema field with field_id, scope, storage, report_role, report_importance, method_role, and aliases would be valuable for automated review.
2. The schema has `required_for_accepted_runs` report importance values; report-completion logic should be checked for consistent treatment.
3. First-run metadata fallback for run-scoped report fields should be reviewed where dataset-level value would be more appropriate.
4. Controlled-choice status is implemented both in schema value maps and report engine ISO helpers; ensure they remain aligned.
