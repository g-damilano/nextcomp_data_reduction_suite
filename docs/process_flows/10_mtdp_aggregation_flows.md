# Aggregation [MTDP] Process Flows

## Scope

This document describes the current MTDP aggregation/package-building process. The goal is to make explicit how raw inputs become a validated `.mtdp` archive.

This document should be expanded over time into finer drill-downs for parser behaviour, schema inference, sidecar reconciliation, bundle editing, validation, archive layout, and reprocessing.

## Source anchors

| Flow area | Code anchor |
|---|---|
| Main aggregation UI | `src/mtdp_enrichment/ui/main_window.py` |
| Parser gateway | `src/mtdp_enrichment/parsing_gateway/parser_adapter.py` |
| Grouping engine | `src/mtdp_enrichment/grouping/sample_type_grouper.py` |
| Bundle editing UI | `src/mtdp_enrichment/ui/bundle_builder.py` |
| Package writer | `src/mtdp_enrichment/package/mtdp_package.py` |
| Schema package model | `src/mtdp_enrichment/package/schema.py` |
| Sidecar importer | `src/mtdp_enrichment/enrichment_import/` |
| Image evidence gateway | `src/mtdp_enrichment/image_gateway/` |
| Supplemental files | `src/mtdp_enrichment/supplemental/` |

---

## L1 — MTDP aggregation overview

```mermaid
flowchart TB
    Input["Input sources<br/>folder · raw files · same-stem YAML · existing .mtdp"] --> Intake["MainWindow intake"]

    Intake --> Parse["ParserAdapter<br/>parse raw files"]
    Parse --> Infer["SchemaRegistry<br/>infer schema"]
    Infer --> Group["SampleTypeGrouper<br/>propose groups"]
    Group --> Bundle["BundleBuilder<br/>operator grouping review"]

    Bundle --> Metadata["SchemaForm<br/>dataset + run metadata"]
    Bundle --> YAML["Sidecar YAML import / rematch"]
    Bundle --> Images["Run image evidence"]
    Bundle --> Supplemental["Supplemental files"]

    Metadata --> Validate["Validate bundle"]
    YAML --> Validate
    Images --> Validate
    Supplemental --> Validate

    Validate --> Export["GroupExporter / MTDPPackageWriter"]
    Export --> MTDP["Validated .mtdp archive"]
```

### Flow reading

The MTDP stage is not analysis. It is a package preparation and evidence aggregation workflow. Its main output is a portable package containing raw sources, normalized data, metadata, evidence, provenance, and checksums.

---

## L2 — Input routing and proposal generation

```mermaid
flowchart TB
    Drop["Drop / select paths"] --> Dedupe["Deduplicate paths"]

    Dedupe --> TargetCheck{"Dropped onto existing group?"}
    TargetCheck -->|Yes| ResolveForBundle["Resolve raw files / folders / YAML sidecars"]
    ResolveForBundle --> AddToBundle["Add source file to selected group"]
    AddToBundle --> ParseOne["Parse one raw file"]
    ParseOne --> InferOne["Infer schema"]
    InferOne --> BuildOne["Build GroupingInput"]
    BuildOne --> AddRun["BundleBuilder.add_input_to_bundle"]

    TargetCheck -->|No| SingleFolder{"Single folder?"}
    SingleFolder -->|Yes| OpenFolder["Open folder"]
    OpenFolder --> Prepare["Prepare source folder"]
    Prepare --> Index["FolderIndex.open + UI folder scan"]
    Index --> ProposeFolder["Propose folder bundles"]

    SingleFolder -->|No| Sources{"Raw files or matching YAML sidecars?"}
    Sources -->|Yes| ResolveSources["Resolve dropped source files"]
    ResolveSources --> CommonFolder["Find common source folder"]
    CommonFolder --> LoadSources["Load source files as proposal"]

    Sources -->|No| Package{"Any .mtdp package?"}
    Package -->|Yes| LoadExisting["Load existing package for reprocessing"]
    Package -->|No| Unsupported["Show unsupported drop message"]

    ProposeFolder --> GroupingInputs["Build grouping inputs from paths"]
    LoadSources --> GroupingInputs
    GroupingInputs --> ParseMany["Parse supported files"]
    ParseMany --> InferMany["Infer schema per file"]
    InferMany --> Proposal["Load grouping proposal"]
    Proposal --> Grouper["SampleTypeGrouper.propose"]
    Grouper --> BundleBuilder["BundleBuilder.load_proposal"]
```

### Current behaviour

- Folders are scanned recursively for parser-supported raw files.
- Raw-file drops can include same-stem YAML sidecars.
- Existing `.mtdp` archives can be opened for review/reprocessing.
- Drops onto a specific group add resolved source files into that group rather than starting a new proposal.

### Follow-up drill-downs required

- Parser-supported suffix logic and parser selection.
- Same-stem YAML resolution and failure diagnostics.
- Existing `.mtdp` reprocessing extraction path.
- Folder index role and persistent suggestion behaviour.

---

## L2 — Parser gateway boundary

```mermaid
flowchart LR
    RawFile["Raw file<br/>.csv / .txt / .dat"] --> CanParse["ParserAdapter.can_parse"]
    CanParse --> ParserClass["Configured parser class<br/>DelimitedMechanicalCsvParser"]
    ParserClass --> Parse["parser_class(path).parse"]
    Parse --> ParsedRecord["ParsedSampleRecord"]

    ParsedRecord --> Preamble["preamble_tokens"]
    ParsedRecord --> Channels["channels / series data"]
    ParsedRecord --> Source["source_file / sample_id hints"]
```

### Current boundary contract

The enrichment UI treats parsing as an external parsing-suite responsibility. It consumes structured `ParsedSampleRecord` outputs and does not inspect raw files directly. This boundary is important for parser-hardening work because parser changes should preserve the structured contract expected by grouping, validation, normalization, and package writing.

### Follow-up drill-downs required

- Numeric parsing strategy.
- Delimiter detection.
- Header/preamble detection.
- Channel table detection.
- Locale-aware number handling.
- Parser diagnostics and raw-value preservation.

---

## L2 — Grouping proposal

```mermaid
flowchart TB
    Inputs["GroupingInput list"] --> Config["schema.dataset_grouping config"]
    Config --> Enabled{"Grouping enabled?"}
    Enabled -->|No| AllUnassigned["All inputs unassigned"]
    Enabled -->|Yes| Each["For each input"]

    Each --> Priority["Try configured source_priority"]
    Priority --> Sidecar["sidecar_field"]
    Priority --> Token["parsed_token"]
    Priority --> Filename["filename_pattern"]
    Priority --> Folder["folder_name"]

    Sidecar --> Candidate{"Candidate found?"}
    Token --> Candidate
    Filename --> Candidate
    Folder --> Candidate

    Candidate -->|No| Unassigned["Unassigned run"]
    Candidate -->|Yes| Canonical["Canonicalize sample name"]
    Canonical --> Assignment["ProposedRunAssignment<br/>key · display · confidence · reason · evidence"]

    Assignment --> GroupByKey["Group assignments by bundle key"]
    GroupByKey --> Bundles["ProposedBundle list"]
    Bundles --> MergeSuggestions["Fuzzy suggested merges"]
    MergeSuggestions --> Proposal["GroupingProposal"]
```

### Current responsibility

The grouping engine proposes structure; it does not finalize correctness. The operator can move, merge, unassign, restore, rename, or delete groups in the BundleBuilder.

### Follow-up drill-downs required

- BundleBuilder editing operations.
- Multi-selection drag/drop behaviour.
- Manual correction counts.
- Unassigned-run semantics.
- Suggested merge UI and evidence.

---

## L2 — Operator enrichment and evidence review

```mermaid
flowchart TB
    Selection["Operator selects bundle / run(s)"] --> SaveCurrent["Save current visible form values"]
    SaveCurrent --> LoadBundle["Load dataset form"]
    SaveCurrent --> LoadRun["Load run form or bulk-edit form"]
    SaveCurrent --> LoadImages["Load run image panel"]
    SaveCurrent --> YAMLStatus["Update YAML status"]

    LoadBundle --> EditDataset["Edit dataset fields"]
    LoadRun --> EditRun["Edit run fields"]
    LoadImages --> ImageDialog["Manage image evidence"]
    YAMLStatus --> Rematch["Review / re-match YAML"]

    Rematch --> ImportSidecar["Import sidecar YAML"]
    ImportSidecar --> MappingProfile["Select/save mapping profile"]
    MappingProfile --> ApplyProfile["Apply mapping profile to one or many runs"]
    ApplyProfile --> Conflicts["Clear or retain sidecar conflicts"]

    EditDataset --> SaveAgain["Save current forms"]
    EditRun --> SaveAgain
    ImageDialog --> SaveAgain
    Conflicts --> SaveAgain
    SaveAgain --> Dirty["Mark package state dirty"]
```

### Current responsibility

This stage enriches the package before export. It should not silently treat analysis decisions as package-preparation decisions. Human review here concerns data aggregation, source matching, metadata, YAML reconciliation, and evidence attachment.

### Follow-up drill-downs required

- Difference between package-preparation review and analysis acceptance review.
- Sidecar conflict lifecycle.
- Image evidence roles and metrology-use flags.
- Supplemental file scopes and archive destinations.

---

## L2 — Validation and export

```mermaid
flowchart TB
    ExportIntent["Validate / Export selected / Export all ready"] --> Save["Save current forms"]
    Save --> Bundle["Selected bundle or each bundle"]
    Bundle --> Defaults["Ensure dataset defaults<br/>sample_type · sample_type_key"]
    Defaults --> DatasetValidation["schema.validate_dataset_fields"]
    DatasetValidation --> RunLoop["For each run"]

    RunLoop --> ExistingFields["package_writer._existing_fields<br/>parser tokens"]
    ExistingFields --> RunValidation["schema.validate_run_fields"]
    RunValidation --> Normalization["package_writer.normalizer.normalize"]
    Normalization --> SidecarGate{"Sidecar conflicts?"}
    SidecarGate -->|Yes| ConflictError["run_validation.add_error"]
    SidecarGate -->|No| StatusUpdate["run.status = ready / needs input"]
    ConflictError --> StatusUpdate

    StatusUpdate --> BundleStatus["bundle.status = ready / needs input"]
    BundleStatus --> ExportGate{"Validation OK?"}
    ExportGate -->|No| NeedsInput["Show missing/issue message"]
    ExportGate -->|Yes| Write["_write_bundle"]
    Write --> PackageWriter["MTDPPackageWriter.create_dataset_package"]
    PackageWriter --> MTDP["Validated .mtdp"]
```

### Current gate meaning

A bundle is exportable only if:

- Dataset fields validate.
- At least one run exists.
- Every run validates against schema requirements.
- Normalized table generation validates.
- Sidecar conflicts have been resolved or confirmed.

### Follow-up drill-downs required

- Exact schema field importance and report-importance interaction.
- Validation message grouping.
- Normalization validation events.
- Export-all behaviour and partial export reporting.

---

## L3 — MTDP archive writing

```mermaid
flowchart TB
    Create["create_dataset_package"] --> RunGate{"Runs present and IDs unique?"}
    RunGate -->|No| ValidationError["Return ValidationResult error"]
    RunGate -->|Yes| CoerceDataset["Coerce dataset user values"]

    CoerceDataset --> ValidateDataset["Validate dataset fields"]
    ValidateDataset --> DatasetJSON["Build dataset.json + run_order"]
    DatasetJSON --> Manifest["manifest.json"]
    Manifest --> Schema["schema.json"]
    Schema --> Provenance["Initialize provenance.json"]

    Provenance --> SourceIdentity["Build source identities"]
    SourceIdentity --> GroupEvents["Grouping / removal events"]
    GroupEvents --> RunLoop["For each RunInput"]

    RunLoop --> CoerceRun["Coerce run enrichment"]
    CoerceRun --> Existing["Existing parser fields"]
    Existing --> ValidateRun["Validate run fields"]
    ValidateRun --> Normalize["Normalize parsed table"]
    Normalize --> CSV["Write normalized CSV"]
    CSV --> RawMember["Add raw member"]
    RawMember --> RunProv["Build run provenance"]
    RunProv --> OptionalEvidence["YAML · images · supplemental files"]

    OptionalEvidence --> MappingProfileEvents["Mapping profile events"]
    MappingProfileEvents --> DatasetSupplemental["Dataset supplemental files"]
    DatasetSupplemental --> Checksums["checksums.json"]
    Checksums --> ZipWrite["Write zip archive"]
    ZipWrite --> ValidatePackage["Validate completed package"]
```

## L4 — MTDP archive contract matrix

| Member / area | Producer | Purpose |
|---|---|---|
| `manifest.json` | `build_manifest(schema)` | Identifies package/schema metadata. |
| `schema.json` | `schema.to_dict()` | Embeds the schema used for packaging. |
| `dataset.json` | `_build_dataset_json` | Stores dataset-level metadata and run order. |
| `raw/<run_id>.*` | `_add_run` | Preserves raw source files. |
| `normalized/<run_id>.csv` | `TokenizedCsvWriter.write_string` | Stores normalized run table and metadata rows. |
| `provenance.json` | `MTDPPackageWriter` | Records grouping, parsing, normalization, source identity, supplemental events. |
| `checksums.json` | `build_checksums(files)` | Provides archive integrity metadata. |
| `supplemental/<run_id>.yaml` | `_add_optional_run_evidence` | Preserves YAML sidecar used for prefill/reconciliation. |
| `images/...` | `_image_member_name` | Preserves run image evidence. |
| `supplemental/...` | `_add_general_supplemental_file` | Preserves additional documents/calibration/mapping support files. |

## Known missing drill-downs

The following should be documented next:

1. Parser internals and numeric parsing behaviour.
2. MTDP schema field lifecycle from raw token to report-role metadata.
3. YAML sidecar reconciliation and conflict resolution.
4. BundleBuilder editing operations.
5. MTDP package validation internals.
6. Reprocessing existing `.mtdp` packages.
