from __future__ import annotations

from dataclasses import dataclass

from markupsafe import Markup

from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind


@dataclass(frozen=True, slots=True)
class NavigationLinkContext:
    href: str
    label: str

    def __post_init__(self) -> None:
        _require_text("href", self.href)
        _require_text("label", self.label)


@dataclass(frozen=True, slots=True)
class ReportShellContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    report_kind: str
    report_href: str
    page_title: str
    report_title: str
    dataset_name: str
    right_label: str
    archive_href: str
    navigation_links: tuple[NavigationLinkContext, ...]

    def __post_init__(self) -> None:
        if self.projection_plane is not ProjectionPlane.MTDA_BUNDLE_VIEWER:
            raise ValueError("ReportShellContext is only valid for the MTDA bundle viewer projection plane")
        if self.recipe_result_kind is not RecipeResultKind.REPORT_SHELL:
            raise ValueError("ReportShellContext must project the report_shell recipe/result kind")
        for name in (
            "report_kind",
            "report_href",
            "page_title",
            "report_title",
            "dataset_name",
            "archive_href",
        ):
            _require_text(name, getattr(self, name))
        _require_string("right_label", self.right_label)
        if not self.navigation_links:
            raise ValueError("navigation_links must not be empty")


@dataclass(frozen=True, slots=True)
class ReportBodyFragmentContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    fragment_kind: str
    wrapper_tag: str
    wrapper_class: str
    fragment_id_html: Markup
    heading_level: int
    title_html: Markup
    body_html: Markup
    paragraph_class: str
    marker_html: Markup = Markup("")
    purpose_html: Markup = Markup("")
    note_html: Markup = Markup("")
    row_count: int = 0
    data_block_type_html: Markup = Markup("")

    def __post_init__(self) -> None:
        if self.projection_plane not in {ProjectionPlane.TEST, ProjectionPlane.AUDIT}:
            raise ValueError("ReportBodyFragmentContext is only valid for test or audit projection planes")
        _require_kind(self.recipe_result_kind, RecipeResultKind.REPORT_BODY_FRAGMENT, "ReportBodyFragmentContext")
        if self.fragment_kind not in {
            "block",
            "titled_fragment",
            "paragraph",
            "formal_detail",
            "audit_detail",
            "details_block",
            "open_details_block",
            "raw_evidence_note",
            "message_block",
        }:
            raise ValueError("fragment_kind must be a known report body fragment variant")
        if self.wrapper_tag not in {"", "div", "section", "article", "details"}:
            raise ValueError("wrapper_tag must be empty or a known HTML wrapper tag")
        if self.fragment_kind == "block" and not self.wrapper_tag:
            raise ValueError("block fragments require a wrapper_tag")
        if self.fragment_kind in {"block", "titled_fragment"}:
            if not isinstance(self.heading_level, int) or not 1 <= self.heading_level <= 6:
                raise ValueError("heading_level must be an integer from 1 to 6")
        elif self.fragment_kind == "paragraph" and self.heading_level != 0:
            raise ValueError("paragraph fragments must use heading_level 0")
        elif self.fragment_kind in {"formal_detail", "audit_detail"}:
            if self.heading_level != 0:
                raise ValueError("detail fragments must use heading_level 0")
            if not self.wrapper_class:
                raise ValueError("detail fragments require wrapper_class")
            if not self.fragment_id_html:
                raise ValueError("detail fragments require fragment_id_html")
            if self.fragment_kind == "formal_detail" and self.wrapper_tag != "details":
                raise ValueError("formal_detail fragments require details wrapper_tag")
            if self.fragment_kind == "audit_detail":
                if self.wrapper_tag != "div":
                    raise ValueError("audit_detail fragments require div wrapper_tag")
                if not self.data_block_type_html:
                    raise ValueError("audit_detail fragments require data_block_type_html")
        elif self.fragment_kind in {"details_block", "open_details_block"}:
            if self.heading_level != 0:
                raise ValueError("details block fragments must use heading_level 0")
            if self.wrapper_tag != "details":
                raise ValueError("details block fragments require details wrapper_tag")
            if not self.wrapper_class:
                raise ValueError("details block fragments require wrapper_class")
            if not self.title_html:
                raise ValueError("details block fragments require title_html")
            if not self.body_html and not self.purpose_html and not self.note_html:
                raise ValueError("details block fragments require body_html")
        elif self.fragment_kind == "raw_evidence_note":
            if self.heading_level != 0:
                raise ValueError("raw evidence note fragments must use heading_level 0")
            if self.wrapper_tag:
                raise ValueError("raw evidence note fragments must not use wrapper_tag")
            if not self.title_html:
                raise ValueError("raw evidence note fragments require title_html")
            if not self.body_html:
                raise ValueError("raw evidence note fragments require body_html")
        elif self.fragment_kind == "message_block":
            if self.heading_level != 0:
                raise ValueError("message block fragments must use heading_level 0")
            if self.wrapper_tag not in {"div", "section", "article"}:
                raise ValueError("message block fragments require a content wrapper_tag")
            if not self.wrapper_class:
                raise ValueError("message block fragments require wrapper_class")
        if not isinstance(self.row_count, int) or self.row_count < 0:
            raise ValueError("row_count must be a non-negative integer")
        for name in ("wrapper_class", "paragraph_class"):
            _require_string(name, getattr(self, name))
        for name in (
            "fragment_id_html",
            "title_html",
            "body_html",
            "marker_html",
            "purpose_html",
            "note_html",
            "data_block_type_html",
        ):
            _require_markup(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class ReportParagraphContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    body_html: Markup
    paragraph_class: str = ""

    def __post_init__(self) -> None:
        _require_test_or_audit_plane(self.projection_plane, "ReportParagraphContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.REPORT_PARAGRAPH, "ReportParagraphContext")
        _require_markup("body_html", self.body_html)
        _require_string("paragraph_class", self.paragraph_class)


@dataclass(frozen=True, slots=True)
class ReportHeadingFragmentContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    heading_level: int
    title_html: Markup
    body_html: Markup = Markup("")

    def __post_init__(self) -> None:
        _require_test_or_audit_plane(self.projection_plane, "ReportHeadingFragmentContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.REPORT_HEADING_FRAGMENT,
            "ReportHeadingFragmentContext",
        )
        if not isinstance(self.heading_level, int) or not 1 <= self.heading_level <= 6:
            raise ValueError("heading_level must be an integer from 1 to 6")
        _require_markup("title_html", self.title_html)
        _require_markup("body_html", self.body_html)


@dataclass(frozen=True, slots=True)
class ReportContainerBlockContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    wrapper_tag: str
    wrapper_class: str
    fragment_id_html: Markup
    heading_level: int
    title_html: Markup
    body_html: Markup

    def __post_init__(self) -> None:
        _require_test_or_audit_plane(self.projection_plane, "ReportContainerBlockContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.REPORT_CONTAINER_BLOCK,
            "ReportContainerBlockContext",
        )
        if self.wrapper_tag not in {"div", "section", "article"}:
            raise ValueError("wrapper_tag must be div, section, or article")
        if not isinstance(self.heading_level, int) or not 1 <= self.heading_level <= 6:
            raise ValueError("heading_level must be an integer from 1 to 6")
        _require_string("wrapper_class", self.wrapper_class)
        _require_markup("fragment_id_html", self.fragment_id_html)
        _require_markup("title_html", self.title_html)
        _require_markup("body_html", self.body_html)


@dataclass(frozen=True, slots=True)
class ReportDetailsPanelContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    wrapper_class: str
    fragment_id_html: Markup
    title_html: Markup
    marker_html: Markup
    purpose_html: Markup
    body_html: Markup
    note_html: Markup
    open_details: bool = False

    def __post_init__(self) -> None:
        _require_test_or_audit_plane(self.projection_plane, "ReportDetailsPanelContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.REPORT_DETAILS_PANEL, "ReportDetailsPanelContext")
        if not self.wrapper_class:
            raise ValueError("wrapper_class must not be empty")
        if not self.title_html:
            raise ValueError("title_html must not be empty")
        if not self.body_html and not self.purpose_html and not self.note_html:
            raise ValueError("details panel requires body_html, purpose_html, or note_html")
        if not isinstance(self.open_details, bool):
            raise ValueError("open_details must be a boolean")
        _require_string("wrapper_class", self.wrapper_class)
        for name in ("fragment_id_html", "title_html", "marker_html", "purpose_html", "body_html", "note_html"):
            _require_markup(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class ReportMessagePanelContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    wrapper_tag: str
    wrapper_class: str
    fragment_id_html: Markup
    body_html: Markup

    def __post_init__(self) -> None:
        _require_test_or_audit_plane(self.projection_plane, "ReportMessagePanelContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.REPORT_MESSAGE_PANEL, "ReportMessagePanelContext")
        if self.wrapper_tag not in {"div", "section", "article"}:
            raise ValueError("wrapper_tag must be div, section, or article")
        if not self.wrapper_class:
            raise ValueError("wrapper_class must not be empty")
        _require_string("wrapper_class", self.wrapper_class)
        _require_markup("fragment_id_html", self.fragment_id_html)
        _require_markup("body_html", self.body_html)


@dataclass(frozen=True, slots=True)
class ReportRawEvidenceNoteContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    title_html: Markup
    row_count: int
    artifact_scope_html: Markup
    row_suffix_html: Markup
    tail_html: Markup
    paragraph_class: str = "muted"

    def __post_init__(self) -> None:
        _require_test_or_audit_plane(self.projection_plane, "ReportRawEvidenceNoteContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.REPORT_RAW_EVIDENCE_NOTE, "ReportRawEvidenceNoteContext")
        if not isinstance(self.row_count, int) or self.row_count < 0:
            raise ValueError("row_count must be a non-negative integer")
        _require_string("paragraph_class", self.paragraph_class)
        for name in ("title_html", "artifact_scope_html", "row_suffix_html", "tail_html"):
            _require_markup(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class MtdaHandoffPageContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    prefix_html: Markup
    support_path: str
    globals_script: Markup
    suffix_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.MTDA_BUNDLE_VIEWER, "MtdaHandoffPageContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.MTDA_HANDOFF_PAGE, "MtdaHandoffPageContext")
        _require_text("support_path", self.support_path)
        _require_markup("prefix_html", self.prefix_html)
        _require_markup("globals_script", self.globals_script)
        _require_markup("suffix_html", self.suffix_html)


@dataclass(frozen=True, slots=True)
class PlotWrapperContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    title_html: Markup
    spec_path_html: Markup
    spec_json: Markup
    home_path_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.MTDA_BUNDLE_VIEWER, "PlotWrapperContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.MTDA_PLOT_WRAPPER, "PlotWrapperContext")
        for name in ("title_html", "spec_path_html", "spec_json", "home_path_html"):
            _require_markup(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class CompactPlotWrapperContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    title_html: Markup
    package_path_html: Markup
    home_path_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.MTDA_BUNDLE_VIEWER, "CompactPlotWrapperContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.MTDA_COMPACT_PLOT_WRAPPER, "CompactPlotWrapperContext")
        for name in ("title_html", "package_path_html", "home_path_html"):
            _require_markup(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class DatasetPlotStudioContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    title_html: Markup
    title_json: Markup
    package_json: Markup
    home_path_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.MTDA_BUNDLE_VIEWER, "DatasetPlotStudioContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.MTDA_DATASET_PLOT_STUDIO, "DatasetPlotStudioContext")
        for name in ("title_html", "title_json", "package_json", "home_path_html"):
            _require_markup(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class SimpleReportContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    page_title: str
    nav_html: Markup
    heading: str
    body_html: Markup
    table_body_html: Markup | None = None

    def __post_init__(self) -> None:
        if self.projection_plane not in {ProjectionPlane.TEST, ProjectionPlane.AUDIT}:
            raise ValueError("SimpleReportContext is only valid for TEST or AUDIT projection planes")
        if self.projection_plane is ProjectionPlane.TEST:
            _require_kind(self.recipe_result_kind, RecipeResultKind.TEST_REPORT, "SimpleReportContext")
        if self.projection_plane is ProjectionPlane.AUDIT:
            _require_kind(self.recipe_result_kind, RecipeResultKind.AUDIT_REPORT, "SimpleReportContext")
        for name in ("page_title", "heading"):
            _require_text(name, getattr(self, name))
        _require_markup("nav_html", self.nav_html)
        _require_markup("body_html", self.body_html)
        if self.table_body_html is not None:
            _require_markup("table_body_html", self.table_body_html)


@dataclass(frozen=True, slots=True)
class FormalMethodReportContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    page_title: str
    report_state_card_html: Markup
    report_tracker_html: Markup
    sections_html: Markup
    appendix_html: Markup
    formatting_css: Markup
    formatting_script: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.TEST, "FormalMethodReportContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.FORMAL_METHOD_REPORT, "FormalMethodReportContext")
        _require_text("page_title", self.page_title)
        for name in (
            "report_state_card_html",
            "report_tracker_html",
            "sections_html",
            "appendix_html",
            "formatting_css",
            "formatting_script",
        ):
            _require_markup(name, getattr(self, name))

    @property
    def report_style_template(self) -> str:
        return "styles/reports/formal.css.j2"

    @property
    def report_head_script_template(self) -> str:
        return "scripts/reports/formal_vega_bootstrap.js.j2"

    @property
    def report_body_script_template(self) -> str:
        return ""

    @property
    def report_hero_html(self) -> Markup:
        return self.report_state_card_html

    @property
    def report_main_html(self) -> Markup:
        return self.sections_html

    @property
    def report_appendix_html(self) -> Markup:
        return self.appendix_html


@dataclass(frozen=True, slots=True)
class ReportNoteMarkerContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind

    def __post_init__(self) -> None:
        if self.projection_plane not in {ProjectionPlane.TEST, ProjectionPlane.AUDIT}:
            raise ValueError("ReportNoteMarkerContext is only valid for TEST or AUDIT projection planes")
        _require_kind(self.recipe_result_kind, RecipeResultKind.REPORT_NOTE_MARKER, "ReportNoteMarkerContext")


@dataclass(frozen=True, slots=True)
class ReportNoteParagraphContext:
    html: Markup

    def __post_init__(self) -> None:
        _require_markup("html", self.html)


@dataclass(frozen=True, slots=True)
class ReportNoteAsideContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    label_html: Markup
    paragraphs: tuple[ReportNoteParagraphContext, ...]

    def __post_init__(self) -> None:
        if self.projection_plane not in {ProjectionPlane.TEST, ProjectionPlane.AUDIT}:
            raise ValueError("ReportNoteAsideContext is only valid for TEST or AUDIT projection planes")
        _require_kind(self.recipe_result_kind, RecipeResultKind.REPORT_NOTE_ASIDE, "ReportNoteAsideContext")
        _require_markup("label_html", self.label_html)
        if not self.paragraphs:
            raise ValueError("paragraphs must not be empty")
        for paragraph in self.paragraphs:
            if not isinstance(paragraph, ReportNoteParagraphContext):
                raise ValueError("paragraphs must contain ReportNoteParagraphContext values")


@dataclass(frozen=True, slots=True)
class ReportMethodsAppendixItemContext:
    title_html: Markup
    label_html: Markup
    paragraphs: tuple[ReportNoteParagraphContext, ...]

    def __post_init__(self) -> None:
        _require_markup("title_html", self.title_html)
        _require_markup("label_html", self.label_html)
        if not self.paragraphs:
            raise ValueError("paragraphs must not be empty")
        for paragraph in self.paragraphs:
            if not isinstance(paragraph, ReportNoteParagraphContext):
                raise ValueError("paragraphs must contain ReportNoteParagraphContext values")


@dataclass(frozen=True, slots=True)
class ReportMethodsAppendixContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    heading_html: Markup
    lede_html: Markup
    items: tuple[ReportMethodsAppendixItemContext, ...]

    def __post_init__(self) -> None:
        if self.projection_plane not in {ProjectionPlane.TEST, ProjectionPlane.AUDIT}:
            raise ValueError("ReportMethodsAppendixContext is only valid for TEST or AUDIT projection planes")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.REPORT_METHODS_APPENDIX,
            "ReportMethodsAppendixContext",
        )
        _require_markup("heading_html", self.heading_html)
        _require_markup("lede_html", self.lede_html)
        for item in self.items:
            if not isinstance(item, ReportMethodsAppendixItemContext):
                raise ValueError("items must contain ReportMethodsAppendixItemContext values")


@dataclass(frozen=True, slots=True)
class FormalReportStateCardContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    title_html: Markup
    lede_html: Markup
    method_context_html: Markup
    method_boundary_html: Markup
    status_class: str
    quality_label_html: Markup
    completion_label_html: Markup
    required_state_html: Markup
    required_location_html: Markup
    recommended_state_html: Markup
    recommended_location_html: Markup
    data_state_html: Markup
    aggregate_basis_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.TEST, "FormalReportStateCardContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.FORMAL_REPORT_STATE_CARD,
            "FormalReportStateCardContext",
        )
        _require_string("status_class", self.status_class)
        for name in (
            "title_html",
            "lede_html",
            "method_context_html",
            "method_boundary_html",
            "quality_label_html",
            "completion_label_html",
            "required_state_html",
            "required_location_html",
            "recommended_state_html",
            "recommended_location_html",
            "data_state_html",
            "aggregate_basis_html",
        ):
            _require_markup(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class FormalReportTrackerLinkContext:
    section_id_html: Markup
    number: int
    title_html: Markup
    pill_html: Markup

    def __post_init__(self) -> None:
        _require_markup("section_id_html", self.section_id_html)
        if not isinstance(self.number, int) or self.number < 1:
            raise ValueError("number must be a positive integer")
        _require_markup("title_html", self.title_html)
        _require_markup("pill_html", self.pill_html)


@dataclass(frozen=True, slots=True)
class FormalReportTrackerContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    links: tuple[FormalReportTrackerLinkContext, ...]

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.TEST, "FormalReportTrackerContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.FORMAL_REPORT_TRACKER, "FormalReportTrackerContext")
        if not isinstance(self.links, tuple):
            raise ValueError("links must be a tuple")


@dataclass(frozen=True, slots=True)
class FormalReportSectionContext:
    section_class: str
    section_id_html: Markup
    number: int
    title_html: Markup
    pill_html: Markup
    body_html: Markup

    def __post_init__(self) -> None:
        _require_text("section_class", self.section_class)
        _require_markup("section_id_html", self.section_id_html)
        if not isinstance(self.number, int) or self.number < 1:
            raise ValueError("number must be a positive integer")
        _require_markup("title_html", self.title_html)
        _require_markup("pill_html", self.pill_html)
        _require_markup("body_html", self.body_html)


@dataclass(frozen=True, slots=True)
class FormalReportSectionsContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    sections: tuple[FormalReportSectionContext, ...]

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.TEST, "FormalReportSectionsContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.FORMAL_REPORT_SECTIONS, "FormalReportSectionsContext")
        if not isinstance(self.sections, tuple):
            raise ValueError("sections must be a tuple")


@dataclass(frozen=True, slots=True)
class FormalReportSectionPillContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    pill_class: str
    label_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.TEST, "FormalReportSectionPillContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.FORMAL_REPORT_SECTION_PILL,
            "FormalReportSectionPillContext",
        )
        _require_string("pill_class", self.pill_class)
        _require_markup("label_html", self.label_html)


@dataclass(frozen=True, slots=True)
class FormalReportBooleanBadgeContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    badge_class: str
    label_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.TEST, "FormalReportBooleanBadgeContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.FORMAL_REPORT_BOOLEAN_BADGE,
            "FormalReportBooleanBadgeContext",
        )
        _require_string("badge_class", self.badge_class)
        _require_markup("label_html", self.label_html)


@dataclass(frozen=True, slots=True)
class FormalReportDimensionHeaderContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    label_html: Markup
    unit_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.TEST, "FormalReportDimensionHeaderContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.FORMAL_REPORT_DIMENSION_HEADER,
            "FormalReportDimensionHeaderContext",
        )
        _require_markup("label_html", self.label_html)
        _require_markup("unit_html", self.unit_html)


@dataclass(frozen=True, slots=True)
class FormalReportBlockContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    block_id_html: Markup
    title_html: Markup
    content_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.TEST, "FormalReportBlockContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.FORMAL_REPORT_BLOCK, "FormalReportBlockContext")
        for name in ("block_id_html", "title_html", "content_html"):
            _require_markup(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class FormalReportTableCellContext:
    html: Markup

    def __post_init__(self) -> None:
        _require_markup("html", self.html)


@dataclass(frozen=True, slots=True)
class FormalReportTableRowContext:
    cells: tuple[FormalReportTableCellContext, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.cells, tuple):
            raise ValueError("cells must be a tuple")


@dataclass(frozen=True, slots=True)
class FormalReportTableContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    table_class: str
    headers: tuple[FormalReportTableCellContext, ...]
    rows: tuple[FormalReportTableRowContext, ...]

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.TEST, "FormalReportTableContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.FORMAL_REPORT_TABLE, "FormalReportTableContext")
        _require_string("table_class", self.table_class)
        if not self.headers:
            raise ValueError("headers must not be empty")
        if not isinstance(self.rows, tuple):
            raise ValueError("rows must be a tuple")


@dataclass(frozen=True, slots=True)
class FormalReportEvidenceTableContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    table: FormalReportTableContext | None
    empty_table_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.TEST, "FormalReportEvidenceTableContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.FORMAL_REPORT_EVIDENCE_TABLE,
            "FormalReportEvidenceTableContext",
        )
        if self.table is not None and not isinstance(self.table, FormalReportTableContext):
            raise ValueError("table must be a FormalReportTableContext or None")
        _require_markup("empty_table_html", self.empty_table_html)

    @property
    def empty_message_html(self) -> Markup:
        return self.empty_table_html

    @property
    def optional_table_prefix_html(self) -> Markup:
        return Markup("")


@dataclass(frozen=True, slots=True)
class FormalReportFieldValueRowContext:
    row_class: str
    field_html: Markup
    value_html: Markup
    unit_html: Markup

    def __post_init__(self) -> None:
        _require_text("row_class", self.row_class)
        for name in ("field_html", "value_html", "unit_html"):
            _require_markup(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class FormalReportFieldValueTableContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    rows: tuple[FormalReportFieldValueRowContext, ...]

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.TEST, "FormalReportFieldValueTableContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.FORMAL_REPORT_FIELD_VALUE_TABLE,
            "FormalReportFieldValueTableContext",
        )
        if not isinstance(self.rows, tuple):
            raise ValueError("rows must be a tuple")


@dataclass(frozen=True, slots=True)
class FormalReportDetailBlockContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    classes: str
    block_id_html: Markup
    title_html: Markup
    marker_html: Markup
    row_count: int
    body_note_html: Markup
    content_html: Markup
    note_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.TEST, "FormalReportDetailBlockContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.FORMAL_REPORT_DETAIL_BLOCK,
            "FormalReportDetailBlockContext",
        )
        _require_text("classes", self.classes)
        if not isinstance(self.row_count, int) or self.row_count < 0:
            raise ValueError("row_count must be a non-negative integer")
        for name in (
            "block_id_html",
            "title_html",
            "marker_html",
            "body_note_html",
            "content_html",
            "note_html",
        ):
            _require_markup(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class FormalReportFragmentStackContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    fragments: tuple[Markup, ...]

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.TEST, "FormalReportFragmentStackContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.FORMAL_REPORT_FRAGMENT_STACK,
            "FormalReportFragmentStackContext",
        )
        if not isinstance(self.fragments, tuple):
            raise ValueError("fragments must be a tuple")
        for fragment in self.fragments:
            _require_markup("fragments", fragment)


@dataclass(frozen=True, slots=True)
class FormalReportTableSectionContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    paragraph_class: str
    intro_html: Markup
    intro_paragraph_html: Markup
    table: FormalReportTableContext | None
    empty_table_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.TEST, "FormalReportTableSectionContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.FORMAL_REPORT_TABLE_SECTION,
            "FormalReportTableSectionContext",
        )
        _require_string("paragraph_class", self.paragraph_class)
        _require_markup("intro_html", self.intro_html)
        _require_markup("intro_paragraph_html", self.intro_paragraph_html)
        if self.table is not None and not isinstance(self.table, FormalReportTableContext):
            raise ValueError("table must be a FormalReportTableContext or None")
        _require_markup("empty_table_html", self.empty_table_html)

    @property
    def empty_message_html(self) -> Markup:
        return self.empty_table_html

    @property
    def optional_table_prefix_html(self) -> Markup:
        return self.intro_paragraph_html


@dataclass(frozen=True, slots=True)
class FormalReportReviewSectionContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    paragraph_class: str
    intro_html: Markup
    intro_paragraph_html: Markup
    table: FormalReportTableContext | None
    empty_message_html: Markup
    raw_evidence_note: FormalReportRawEvidenceNoteContext

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.TEST, "FormalReportReviewSectionContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.FORMAL_REPORT_REVIEW_SECTION,
            "FormalReportReviewSectionContext",
        )
        _require_string("paragraph_class", self.paragraph_class)
        _require_markup("intro_html", self.intro_html)
        _require_markup("intro_paragraph_html", self.intro_paragraph_html)
        if self.table is not None and not isinstance(self.table, FormalReportTableContext):
            raise ValueError("table must be a FormalReportTableContext or None")
        _require_markup("empty_message_html", self.empty_message_html)
        if not isinstance(self.raw_evidence_note, FormalReportRawEvidenceNoteContext):
            raise ValueError("raw_evidence_note must be a FormalReportRawEvidenceNoteContext")


@dataclass(frozen=True, slots=True)
class FormalReportParagraphContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    paragraph_class: str
    body_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.TEST, "FormalReportParagraphContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.FORMAL_REPORT_PARAGRAPH,
            "FormalReportParagraphContext",
        )
        _require_string("paragraph_class", self.paragraph_class)
        _require_markup("body_html", self.body_html)


@dataclass(frozen=True, slots=True)
class FormalReportRawEvidenceNoteContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    title_html: Markup
    row_count: int

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.TEST, "FormalReportRawEvidenceNoteContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.FORMAL_REPORT_RAW_EVIDENCE_NOTE,
            "FormalReportRawEvidenceNoteContext",
        )
        _require_markup("title_html", self.title_html)
        if not isinstance(self.row_count, int) or self.row_count < 0:
            raise ValueError("row_count must be a non-negative integer")

    @property
    def artifact_scope_html(self) -> Markup:
        return Markup("MTDA report CSV/JSON artifacts")

    @property
    def row_suffix_html(self) -> Markup:
        return Markup("")

    @property
    def tail_html(self) -> Markup:
        return Markup(" and in the Workbench evidence view; it is not duplicated here as a raw debug table.")

    @property
    def paragraph_class(self) -> str:
        return "muted"


@dataclass(frozen=True, slots=True)
class FormalReportRemarksContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    paragraphs: tuple[Markup, ...]
    empty_message_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.TEST, "FormalReportRemarksContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.FORMAL_REPORT_REMARKS,
            "FormalReportRemarksContext",
        )
        if not isinstance(self.paragraphs, tuple):
            raise ValueError("paragraphs must be a tuple")
        for paragraph in self.paragraphs:
            _require_markup("paragraphs", paragraph)
        _require_markup("empty_message_html", self.empty_message_html)


@dataclass(frozen=True, slots=True)
class FormalReportMissingDataContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    table: FormalReportTableContext | None
    empty_message_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.TEST, "FormalReportMissingDataContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.FORMAL_REPORT_MISSING_DATA,
            "FormalReportMissingDataContext",
        )
        if self.table is not None and not isinstance(self.table, FormalReportTableContext):
            raise ValueError("table must be a FormalReportTableContext or None")
        _require_markup("empty_message_html", self.empty_message_html)

    @property
    def optional_table_prefix_html(self) -> Markup:
        return Markup("")


@dataclass(frozen=True, slots=True)
class FormalReportDataUseDeviationsContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    prefix_html: Markup
    table: FormalReportTableContext | None
    empty_message_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.TEST, "FormalReportDataUseDeviationsContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.FORMAL_REPORT_DATA_USE_DEVIATIONS,
            "FormalReportDataUseDeviationsContext",
        )
        _require_markup("prefix_html", self.prefix_html)
        if self.table is not None and not isinstance(self.table, FormalReportTableContext):
            raise ValueError("table must be a FormalReportTableContext or None")
        _require_markup("empty_message_html", self.empty_message_html)

    @property
    def optional_table_prefix_html(self) -> Markup:
        return self.prefix_html


@dataclass(frozen=True, slots=True)
class FormalReportDeviationsSectionContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    section_number: int
    missing_heading_html: Markup
    missing_data_html: Markup
    data_deviations_heading_html: Markup
    data_deviations_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.TEST, "FormalReportDeviationsSectionContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.FORMAL_REPORT_DEVIATIONS_SECTION,
            "FormalReportDeviationsSectionContext",
        )
        if not isinstance(self.section_number, int) or self.section_number < 1:
            raise ValueError("section_number must be a positive integer")
        _require_markup("missing_heading_html", self.missing_heading_html)
        _require_markup("missing_data_html", self.missing_data_html)
        _require_markup("data_deviations_heading_html", self.data_deviations_heading_html)
        _require_markup("data_deviations_html", self.data_deviations_html)


@dataclass(frozen=True, slots=True)
class FormalReportPlotLegendContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    sd_label_html: Markup
    range_label_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.TEST, "FormalReportPlotLegendContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.FORMAL_REPORT_PLOT_LEGEND,
            "FormalReportPlotLegendContext",
        )
        _require_markup("sd_label_html", self.sd_label_html)
        _require_markup("range_label_html", self.range_label_html)


@dataclass(frozen=True, slots=True)
class FormalReportPlotBlockContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    block_id_html: Markup
    label_html: Markup
    fallback_html: Markup
    legend_html: Markup
    spec_json: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.TEST, "FormalReportPlotBlockContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.FORMAL_REPORT_PLOT_BLOCK,
            "FormalReportPlotBlockContext",
        )
        _require_markup("block_id_html", self.block_id_html)
        _require_markup("label_html", self.label_html)
        _require_markup("fallback_html", self.fallback_html)
        _require_markup("legend_html", self.legend_html)
        _require_markup("spec_json", self.spec_json)


@dataclass(frozen=True, slots=True)
class FormalReportAggregateSvgContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    min_path: str
    max_path: str
    mean_path: str
    n_label_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.TEST, "FormalReportAggregateSvgContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.FORMAL_REPORT_AGGREGATE_SVG,
            "FormalReportAggregateSvgContext",
        )
        for name in ("min_path", "max_path", "mean_path"):
            _require_text(name, getattr(self, name))
        _require_markup("n_label_html", self.n_label_html)


@dataclass(frozen=True, slots=True)
class FormalReportFailureBendingSvgContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    width: int
    height: int
    left: int
    top: int
    bottom: int
    plot_width: int
    right: int
    threshold_fill_height: str
    threshold_y: str
    threshold_label_x: int
    threshold_label_y: str
    boxes_html: Markup
    labels_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.TEST, "FormalReportFailureBendingSvgContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.FORMAL_REPORT_FAILURE_BENDING_SVG,
            "FormalReportFailureBendingSvgContext",
        )
        for name in ("width", "height", "left", "top", "bottom", "plot_width", "right", "threshold_label_x"):
            value = getattr(self, name)
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        for name in ("threshold_fill_height", "threshold_y", "threshold_label_y"):
            _require_text(name, getattr(self, name))
        _require_markup("boxes_html", self.boxes_html)
        _require_markup("labels_html", self.labels_html)


@dataclass(frozen=True, slots=True)
class FormalReportPlotNoteContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    message_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.TEST, "FormalReportPlotNoteContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.FORMAL_REPORT_PLOT_NOTE,
            "FormalReportPlotNoteContext",
        )
        _require_markup("message_html", self.message_html)


@dataclass(frozen=True, slots=True)
class AuditTableCellContext:
    html: Markup

    def __post_init__(self) -> None:
        _require_markup("html", self.html)


@dataclass(frozen=True, slots=True)
class AuditTableRowContext:
    cells: tuple[AuditTableCellContext, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.cells, tuple):
            raise ValueError("cells must be a tuple")


@dataclass(frozen=True, slots=True)
class AuditTableContext:
    table_class: str
    headers: tuple[AuditTableCellContext, ...]
    rows: tuple[AuditTableRowContext, ...]

    def __post_init__(self) -> None:
        _require_string("table_class", self.table_class)
        if not self.headers:
            raise ValueError("headers must not be empty")
        if not isinstance(self.rows, tuple):
            raise ValueError("rows must be a tuple")


@dataclass(frozen=True, slots=True)
class AuditRunIndexContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    section_heading_html: Markup
    table: AuditTableContext | None
    empty_message_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditRunIndexContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.AUDIT_RUN_INDEX, "AuditRunIndexContext")
        _require_markup("section_heading_html", self.section_heading_html)
        if self.table is not None and not isinstance(self.table, AuditTableContext):
            raise ValueError("table must be an AuditTableContext or None")
        _require_markup("empty_message_html", self.empty_message_html)


@dataclass(frozen=True, slots=True)
class AuditBadgeContext:
    status_class: str
    label_html: Markup

    def __post_init__(self) -> None:
        _require_text("status_class", self.status_class)
        _require_markup("label_html", self.label_html)


@dataclass(frozen=True, slots=True)
class AuditRunPacketContext:
    run_id_html: Markup
    run_label_html: Markup
    badges: tuple[AuditBadgeContext, ...]
    blocks_html: tuple[Markup, ...]

    def __post_init__(self) -> None:
        _require_markup("run_id_html", self.run_id_html)
        _require_markup("run_label_html", self.run_label_html)
        if not isinstance(self.badges, tuple):
            raise ValueError("badges must be a tuple")
        for badge in self.badges:
            if not isinstance(badge, AuditBadgeContext):
                raise ValueError("badges must contain AuditBadgeContext values")
        if not isinstance(self.blocks_html, tuple):
            raise ValueError("blocks_html must be a tuple")
        for block_html in self.blocks_html:
            _require_markup("blocks_html", block_html)


@dataclass(frozen=True, slots=True)
class AuditRunPacketsContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    section_heading_html: Markup
    packets: tuple[AuditRunPacketContext, ...]

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditRunPacketsContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.AUDIT_RUN_PACKETS, "AuditRunPacketsContext")
        _require_markup("section_heading_html", self.section_heading_html)
        if not isinstance(self.packets, tuple):
            raise ValueError("packets must be a tuple")
        for packet in self.packets:
            if not isinstance(packet, AuditRunPacketContext):
                raise ValueError("packets must contain AuditRunPacketContext values")


@dataclass(frozen=True, slots=True)
class AuditAggregatePacketContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    section_heading_html: Markup
    blocks_html: tuple[Markup, ...]

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditAggregatePacketContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.AUDIT_AGGREGATE_PACKET, "AuditAggregatePacketContext")
        _require_markup("section_heading_html", self.section_heading_html)
        if not isinstance(self.blocks_html, tuple):
            raise ValueError("blocks_html must be a tuple")
        for block_html in self.blocks_html:
            _require_markup("blocks_html", block_html)


@dataclass(frozen=True, slots=True)
class AuditTrackerRunLinkContext:
    anchor_html: Markup
    number: int
    label_html: Markup

    def __post_init__(self) -> None:
        _require_markup("anchor_html", self.anchor_html)
        if not isinstance(self.number, int) or self.number < 1:
            raise ValueError("number must be a positive integer")
        _require_markup("label_html", self.label_html)


@dataclass(frozen=True, slots=True)
class AuditTrackerLinkContext:
    number_html: Markup
    label_html: Markup
    anchor_html: Markup
    pill_html: Markup
    run_links: tuple[AuditTrackerRunLinkContext, ...] = ()

    def __post_init__(self) -> None:
        for name in ("number_html", "label_html", "anchor_html", "pill_html"):
            _require_markup(name, getattr(self, name))
        if not isinstance(self.run_links, tuple):
            raise ValueError("run_links must be a tuple")
        for run_link in self.run_links:
            if not isinstance(run_link, AuditTrackerRunLinkContext):
                raise ValueError("run_links must contain AuditTrackerRunLinkContext values")


@dataclass(frozen=True, slots=True)
class AuditTrackerContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    links: tuple[AuditTrackerLinkContext, ...]

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditTrackerContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.AUDIT_TRACKER, "AuditTrackerContext")
        if not isinstance(self.links, tuple):
            raise ValueError("links must be a tuple")
        for link in self.links:
            if not isinstance(link, AuditTrackerLinkContext):
                raise ValueError("links must contain AuditTrackerLinkContext values")


@dataclass(frozen=True, slots=True)
class AuditProcessOverviewContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    lede_html: Markup
    overview_html: Markup
    table: AuditTableContext

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditProcessOverviewContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.AUDIT_PROCESS_OVERVIEW, "AuditProcessOverviewContext")
        _require_markup("lede_html", self.lede_html)
        _require_markup("overview_html", self.overview_html)
        if not isinstance(self.table, AuditTableContext):
            raise ValueError("table must be an AuditTableContext")


@dataclass(frozen=True, slots=True)
class AuditProcessSummarySentenceContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    sentence_kind: str
    status_html: Markup
    start_policy_html: Markup
    end_policy_html: Markup
    bounded_reduction_html: Markup
    boundary_aligned_aggregation_html: Markup
    endpoints_table_html: Markup
    passed_html: Markup
    warnings_html: Markup
    failed_html: Markup
    final_selection_set_html: Markup
    selection_source_html: Markup
    discharged_run_count_html: Markup
    warning_count_html: Markup
    sentence_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditProcessSummarySentenceContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.AUDIT_PROCESS_SUMMARY_SENTENCE,
            "AuditProcessSummarySentenceContext",
        )
        _require_text("sentence_kind", self.sentence_kind)
        if self.sentence_kind not in {
            "no_summary",
            "readiness",
            "experiment_boundary_resolution",
            "validation",
            "acceptance_final_selection",
            "warnings_residuals",
            "linked_artifacts",
            "default",
        }:
            raise ValueError("sentence_kind must be a known audit process summary variant")
        for name in (
            "status_html",
            "start_policy_html",
            "end_policy_html",
            "bounded_reduction_html",
            "boundary_aligned_aggregation_html",
            "endpoints_table_html",
            "passed_html",
            "warnings_html",
            "failed_html",
            "final_selection_set_html",
            "selection_source_html",
            "discharged_run_count_html",
            "warning_count_html",
            "sentence_html",
        ):
            _require_markup(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class AuditProcessSectionContext:
    section_id_html: Markup
    title_html: Markup
    summary_html: Markup
    evidence_purpose_html: Markup
    table_html: Markup
    evidence_detail_html: Markup

    def __post_init__(self) -> None:
        for name in (
            "section_id_html",
            "title_html",
            "summary_html",
            "evidence_purpose_html",
            "table_html",
            "evidence_detail_html",
        ):
            _require_markup(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class AuditProcessSectionsContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    sections: tuple[AuditProcessSectionContext, ...]

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditProcessSectionsContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.AUDIT_PROCESS_SECTIONS, "AuditProcessSectionsContext")
        if not isinstance(self.sections, tuple):
            raise ValueError("sections must be a tuple")
        for section in self.sections:
            if not isinstance(section, AuditProcessSectionContext):
                raise ValueError("sections must contain AuditProcessSectionContext values")


@dataclass(frozen=True, slots=True)
class AuditDecisionRegisterContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    section_heading_html: Markup
    disposition_summary_heading_html: Markup
    disposition_summary_table_html: Markup
    disposition_heading_html: Markup
    disposition_table_html: Markup
    has_human_overrides: bool
    human_overrides_heading_html: Markup
    human_overrides_table_html: Markup
    has_amendments: bool
    amendments_heading_html: Markup
    amendments_table_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditDecisionRegisterContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.AUDIT_DECISION_REGISTER, "AuditDecisionRegisterContext")
        _require_bool("has_human_overrides", self.has_human_overrides)
        _require_bool("has_amendments", self.has_amendments)
        for name in (
            "section_heading_html",
            "disposition_summary_heading_html",
            "disposition_summary_table_html",
            "disposition_heading_html",
            "disposition_table_html",
            "human_overrides_heading_html",
            "human_overrides_table_html",
            "amendments_heading_html",
            "amendments_table_html",
        ):
            _require_markup(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class AuditBlockCardContext:
    block_id_html: Markup
    title_html: Markup
    status_html: Markup
    purpose_html: Markup
    fragments: tuple[Markup, ...]
    card_html: Markup

    def __post_init__(self) -> None:
        for name in ("block_id_html", "title_html", "status_html", "purpose_html", "card_html"):
            _require_markup(name, getattr(self, name))
        if not isinstance(self.fragments, tuple):
            raise ValueError("fragments must be a tuple")
        for fragment in self.fragments:
            _require_markup("fragments", fragment)


@dataclass(frozen=True, slots=True)
class AuditGroupedRunPacketContext:
    run_id_html: Markup
    packet_heading_html: Markup
    blocks: tuple[AuditBlockCardContext, ...]

    def __post_init__(self) -> None:
        _require_markup("run_id_html", self.run_id_html)
        _require_markup("packet_heading_html", self.packet_heading_html)
        if not isinstance(self.blocks, tuple):
            raise ValueError("blocks must be a tuple")
        for block in self.blocks:
            if not isinstance(block, AuditBlockCardContext):
                raise ValueError("blocks must contain AuditBlockCardContext values")


@dataclass(frozen=True, slots=True)
class AuditGroupedSectionsContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    overview_heading_html: Markup
    intro_html: Markup
    overview: AuditBlockCardContext | None
    run_packets_heading_html: Markup
    run_packets: tuple[AuditGroupedRunPacketContext, ...]
    aggregate_heading_html: Markup
    aggregate_blocks: tuple[AuditBlockCardContext, ...]

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditGroupedSectionsContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.AUDIT_GROUPED_SECTIONS, "AuditGroupedSectionsContext")
        _require_markup("overview_heading_html", self.overview_heading_html)
        _require_markup("intro_html", self.intro_html)
        if self.overview is not None and not isinstance(self.overview, AuditBlockCardContext):
            raise ValueError("overview must be an AuditBlockCardContext or None")
        _require_markup("run_packets_heading_html", self.run_packets_heading_html)
        if not isinstance(self.run_packets, tuple):
            raise ValueError("run_packets must be a tuple")
        for packet in self.run_packets:
            if not isinstance(packet, AuditGroupedRunPacketContext):
                raise ValueError("run_packets must contain AuditGroupedRunPacketContext values")
        _require_markup("aggregate_heading_html", self.aggregate_heading_html)
        if not isinstance(self.aggregate_blocks, tuple):
            raise ValueError("aggregate_blocks must be a tuple")
        for block in self.aggregate_blocks:
            if not isinstance(block, AuditBlockCardContext):
                raise ValueError("aggregate_blocks must contain AuditBlockCardContext values")


@dataclass(frozen=True, slots=True)
class AuditEvidenceTableContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    table: AuditTableContext | None
    empty_message_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditEvidenceTableContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.AUDIT_TABLE, "AuditEvidenceTableContext")
        if self.table is not None and not isinstance(self.table, AuditTableContext):
            raise ValueError("table must be an AuditTableContext or None")
        _require_markup("empty_message_html", self.empty_message_html)

    @property
    def optional_table_prefix_html(self) -> Markup:
        return Markup("")


@dataclass(frozen=True, slots=True)
class AuditRawEvidenceNoteContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    title_html: Markup
    row_count: int

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditRawEvidenceNoteContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.AUDIT_RAW_EVIDENCE_NOTE, "AuditRawEvidenceNoteContext")
        _require_markup("title_html", self.title_html)
        if not isinstance(self.row_count, int) or self.row_count < 0:
            raise ValueError("row_count must be a non-negative integer")

    @property
    def artifact_scope_html(self) -> Markup:
        return Markup("MTDA audit/workbench artifacts")

    @property
    def row_suffix_html(self) -> Markup:
        return Markup(" archived")

    @property
    def tail_html(self) -> Markup:
        return Markup(". It is summarized here to keep the Audit Report reviewable.")

    @property
    def paragraph_class(self) -> str:
        return "muted"


@dataclass(frozen=True, slots=True)
class AuditBlockTableContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    table: AuditTableContext | None
    empty_message_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditBlockTableContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.AUDIT_BLOCK_TABLE, "AuditBlockTableContext")
        if self.table is not None and not isinstance(self.table, AuditTableContext):
            raise ValueError("table must be an AuditTableContext or None")
        _require_markup("empty_message_html", self.empty_message_html)

    @property
    def optional_table_prefix_html(self) -> Markup:
        return Markup("")


@dataclass(frozen=True, slots=True)
class AuditBlockFieldValueRowContext:
    label_html: Markup
    value_html: Markup

    def __post_init__(self) -> None:
        _require_markup("label_html", self.label_html)
        _require_markup("value_html", self.value_html)


@dataclass(frozen=True, slots=True)
class AuditBlockFieldValueTableContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    rows: tuple[AuditBlockFieldValueRowContext, ...]
    empty_message_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditBlockFieldValueTableContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.AUDIT_BLOCK_FIELD_VALUE_TABLE,
            "AuditBlockFieldValueTableContext",
        )
        if not isinstance(self.rows, tuple):
            raise ValueError("rows must be a tuple")
        for row in self.rows:
            if not isinstance(row, AuditBlockFieldValueRowContext):
                raise ValueError("rows must contain AuditBlockFieldValueRowContext values")
        _require_markup("empty_message_html", self.empty_message_html)


@dataclass(frozen=True, slots=True)
class AuditBlockDetailsContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    classes_html: Markup
    block_id_html: Markup
    block_type_html: Markup
    title_html: Markup
    marker_html: Markup
    purpose_html: Markup
    body_html: Markup
    note_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditBlockDetailsContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.AUDIT_BLOCK_DETAILS, "AuditBlockDetailsContext")
        for name in (
            "classes_html",
            "block_id_html",
            "block_type_html",
            "title_html",
            "marker_html",
            "purpose_html",
            "body_html",
            "note_html",
        ):
            _require_markup(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class AuditBlockInlineNoteContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    label_html: Markup
    paragraphs_html: tuple[Markup, ...]

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditBlockInlineNoteContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.AUDIT_BLOCK_INLINE_NOTE,
            "AuditBlockInlineNoteContext",
        )
        _require_markup("label_html", self.label_html)
        if not isinstance(self.paragraphs_html, tuple) or not self.paragraphs_html:
            raise ValueError("paragraphs_html must be a non-empty tuple")
        for paragraph in self.paragraphs_html:
            _require_markup("paragraphs_html", paragraph)


@dataclass(frozen=True, slots=True)
class AuditBlockSummaryPanelContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    title_html: Markup
    table_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditBlockSummaryPanelContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.AUDIT_BLOCK_SUMMARY_PANEL,
            "AuditBlockSummaryPanelContext",
        )
        _require_markup("title_html", self.title_html)
        _require_markup("table_html", self.table_html)

    @property
    def panel_class(self) -> str:
        return "summary-panel"

    @property
    def heading_level(self) -> int:
        return 4

    @property
    def panel_body_html(self) -> Markup:
        return self.table_html


@dataclass(frozen=True, slots=True)
class AuditBlockTechnicalTraceContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    body_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditBlockTechnicalTraceContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.AUDIT_BLOCK_TECHNICAL_TRACE,
            "AuditBlockTechnicalTraceContext",
        )
        _require_markup("body_html", self.body_html)


@dataclass(frozen=True, slots=True)
class AuditBlockTitledFragmentContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    title_html: Markup
    body_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditBlockTitledFragmentContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.AUDIT_BLOCK_TITLED_FRAGMENT,
            "AuditBlockTitledFragmentContext",
        )
        _require_markup("title_html", self.title_html)
        _require_markup("body_html", self.body_html)

    @property
    def heading_level(self) -> int:
        return 4


@dataclass(frozen=True, slots=True)
class AuditBlockParagraphContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    body_html: Markup
    paragraph_class: str = ""

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditBlockParagraphContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.AUDIT_BLOCK_PARAGRAPH,
            "AuditBlockParagraphContext",
        )
        _require_markup("body_html", self.body_html)
        _require_string("paragraph_class", self.paragraph_class)


@dataclass(frozen=True, slots=True)
class AuditBlockAnalysisComparisonContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    title_html: Markup
    body_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditBlockAnalysisComparisonContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.AUDIT_BLOCK_ANALYSIS_COMPARISON,
            "AuditBlockAnalysisComparisonContext",
        )
        _require_markup("title_html", self.title_html)
        _require_markup("body_html", self.body_html)

    @property
    def panel_class(self) -> str:
        return "analysis-comparison"

    @property
    def heading_level(self) -> int:
        return 4

    @property
    def panel_body_html(self) -> Markup:
        return self.body_html


@dataclass(frozen=True, slots=True)
class AuditBlockPlotPanelContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    has_spec: bool
    audit_plot_type_html: Markup
    plot_id_html: Markup
    caption_html: Markup
    warning_html: Markup
    fallback_message_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditBlockPlotPanelContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.AUDIT_BLOCK_PLOT_PANEL, "AuditBlockPlotPanelContext")
        _require_bool("has_spec", self.has_spec)
        for name in (
            "audit_plot_type_html",
            "plot_id_html",
            "caption_html",
            "warning_html",
            "fallback_message_html",
        ):
            _require_markup(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class AuditAppendixDetailContext:
    detail_class: str
    summary_html: Markup
    body_html: Markup
    detail_html: Markup
    detail_id_html: Markup | None = None

    def __post_init__(self) -> None:
        _require_text("detail_class", self.detail_class)
        _require_markup("summary_html", self.summary_html)
        _require_markup("body_html", self.body_html)
        _require_markup("detail_html", self.detail_html)
        if self.detail_id_html is not None:
            _require_markup("detail_id_html", self.detail_id_html)


@dataclass(frozen=True, slots=True)
class AuditEvidenceAppendicesContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    section_heading_html: Markup
    note_html: Markup
    details: tuple[AuditAppendixDetailContext, ...]

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditEvidenceAppendicesContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.AUDIT_EVIDENCE_APPENDICES,
            "AuditEvidenceAppendicesContext",
        )
        _require_markup("section_heading_html", self.section_heading_html)
        _require_markup("note_html", self.note_html)
        if not isinstance(self.details, tuple):
            raise ValueError("details must be a tuple")
        for detail in self.details:
            if not isinstance(detail, AuditAppendixDetailContext):
                raise ValueError("details must contain AuditAppendixDetailContext values")


@dataclass(frozen=True, slots=True)
class AuditArtifactLinksContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    section_heading_html: Markup
    table_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditArtifactLinksContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.AUDIT_ARTIFACT_LINKS, "AuditArtifactLinksContext")
        _require_markup("section_heading_html", self.section_heading_html)
        _require_markup("table_html", self.table_html)


@dataclass(frozen=True, slots=True)
class AuditTechnicalAppendixContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    section_heading_html: Markup
    purpose_html: Markup
    process_sections_html: Markup
    evidence_sections_html: Markup
    process_detail_html: Markup
    evidence_detail_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditTechnicalAppendixContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.AUDIT_TECHNICAL_APPENDIX,
            "AuditTechnicalAppendixContext",
        )
        for name in (
            "section_heading_html",
            "purpose_html",
            "process_sections_html",
            "evidence_sections_html",
            "process_detail_html",
            "evidence_detail_html",
        ):
            _require_markup(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class AuditComponentContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    title_html: Markup
    body_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditComponentContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.AUDIT_COMPONENT, "AuditComponentContext")
        _require_markup("title_html", self.title_html)
        _require_markup("body_html", self.body_html)

    @property
    def heading_level(self) -> int:
        return 3


@dataclass(frozen=True, slots=True)
class AuditComponentMicrocopyContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    microcopy_kind: str
    component_type_html: Markup
    body_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditComponentMicrocopyContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.AUDIT_COMPONENT_MICROCOPY,
            "AuditComponentMicrocopyContext",
        )
        _require_text("microcopy_kind", self.microcopy_kind)
        if self.microcopy_kind not in {
            "chart_hint",
            "chord_endpoint_note",
            "bending_pattern_heading",
            "operation_log_appendix_purpose",
            "inspection_log_appendix_purpose",
            "process_section_evidence_purpose",
            "technical_appendix_purpose",
            "grouped_sections_intro",
            "unsupported_component_note",
        }:
            raise ValueError("microcopy_kind must be a known audit component microcopy variant")
        _require_markup("component_type_html", self.component_type_html)
        _require_markup("body_html", self.body_html)


@dataclass(frozen=True, slots=True)
class AuditValidationSummaryContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    summary_html: Markup
    has_checks: bool
    status_html: Markup
    status_class: str
    checks_html: Markup
    passed_html: Markup
    warnings_html: Markup
    failed_html: Markup
    deviations_table_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditValidationSummaryContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.AUDIT_VALIDATION_SUMMARY,
            "AuditValidationSummaryContext",
        )
        _require_bool("has_checks", self.has_checks)
        _require_string("status_class", self.status_class)
        for name in (
            "summary_html",
            "status_html",
            "checks_html",
            "passed_html",
            "warnings_html",
            "failed_html",
            "deviations_table_html",
        ):
            _require_markup(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class AuditReadinessSummaryContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    summary_html: Markup
    status_html: Markup
    status_class: str
    execution_critical_passed_html: Markup
    execution_critical_total_html: Markup
    missing_total_html: Markup
    blocks_execution_html: Markup
    readiness_table_html: Markup
    missing_inputs_heading_html: Markup
    missing_inputs_table_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditReadinessSummaryContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.AUDIT_READINESS_SUMMARY,
            "AuditReadinessSummaryContext",
        )
        _require_string("status_class", self.status_class)
        for name in (
            "summary_html",
            "status_html",
            "execution_critical_passed_html",
            "execution_critical_total_html",
            "missing_total_html",
            "blocks_execution_html",
            "readiness_table_html",
            "missing_inputs_heading_html",
            "missing_inputs_table_html",
        ):
            _require_markup(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class AuditAcceptanceSummaryContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    summary_html: Markup
    default_selection_html: Markup
    total_runs_html: Markup
    accepted_html: Markup
    accepted_with_warning_html: Markup
    review_required_html: Markup
    excluded_html: Markup
    total_flags_html: Markup
    final_selection_html: Markup
    selection_source_html: Markup
    final_included_html: Markup
    human_decisions_html: Markup
    acceptance_table_html: Markup
    curve_summary_heading_html: Markup
    curve_summary_table_html: Markup
    curve_scores_table_html: Markup
    final_runs_heading_html: Markup
    final_runs_table_html: Markup
    override_ledger_heading_html: Markup
    override_ledger_table_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditAcceptanceSummaryContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.AUDIT_ACCEPTANCE_SUMMARY,
            "AuditAcceptanceSummaryContext",
        )
        for name in (
            "summary_html",
            "default_selection_html",
            "total_runs_html",
            "accepted_html",
            "accepted_with_warning_html",
            "review_required_html",
            "excluded_html",
            "total_flags_html",
            "final_selection_html",
            "selection_source_html",
            "final_included_html",
            "human_decisions_html",
            "acceptance_table_html",
            "curve_summary_heading_html",
            "curve_summary_table_html",
            "curve_scores_table_html",
            "final_runs_heading_html",
            "final_runs_table_html",
            "override_ledger_heading_html",
            "override_ledger_table_html",
        ):
            _require_markup(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class AuditOperationLogComponentContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    title_html: Markup
    purpose_html: Markup
    summary_table_html: Markup
    preview_table_html: Markup
    raw_evidence_note_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditOperationLogComponentContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.AUDIT_OPERATION_LOG_COMPONENT,
            "AuditOperationLogComponentContext",
        )
        for name in ("title_html", "purpose_html", "summary_table_html", "preview_table_html", "raw_evidence_note_html"):
            _require_markup(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class AuditInspectionLogComponentContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    title_html: Markup
    purpose_html: Markup
    summary_table_html: Markup
    preview_table_html: Markup
    raw_evidence_note_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditInspectionLogComponentContext")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.AUDIT_INSPECTION_LOG_COMPONENT,
            "AuditInspectionLogComponentContext",
        )
        for name in ("title_html", "purpose_html", "summary_table_html", "preview_table_html", "raw_evidence_note_html"):
            _require_markup(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class AuditChartComponentContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    title_html: Markup
    chart_id_html: Markup
    chart_hint_html: Markup
    after_chart_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditChartComponentContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.AUDIT_CHART_COMPONENT, "AuditChartComponentContext")
        for name in ("title_html", "chart_id_html", "chart_hint_html", "after_chart_html"):
            _require_markup(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class AuditEvidenceReportContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    page_title: str
    process_overview_html: Markup
    report_tracker_html: Markup
    grouped_sections_html: Markup
    appendix_html: Markup
    vega_specs_json: Markup
    formatting_css: Markup
    formatting_script: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.AUDIT, "AuditEvidenceReportContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.AUDIT_EVIDENCE_REPORT, "AuditEvidenceReportContext")
        _require_text("page_title", self.page_title)
        for name in (
            "process_overview_html",
            "report_tracker_html",
            "grouped_sections_html",
            "appendix_html",
            "vega_specs_json",
            "formatting_css",
            "formatting_script",
        ):
            _require_markup(name, getattr(self, name))

    @property
    def report_style_template(self) -> str:
        return "styles/reports/audit.css.j2"

    @property
    def report_head_script_template(self) -> str:
        return ""

    @property
    def report_body_script_template(self) -> str:
        return "scripts/reports/audit_vega_bootstrap.js.j2"

    @property
    def report_hero_html(self) -> Markup:
        return self.process_overview_html

    @property
    def report_main_html(self) -> Markup:
        return self.grouped_sections_html

    @property
    def report_appendix_html(self) -> Markup:
        return self.appendix_html


@dataclass(frozen=True, slots=True)
class MtdaFinalizationSectionContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    title_html: Markup
    body_html: Markup

    def __post_init__(self) -> None:
        if self.projection_plane not in {ProjectionPlane.TEST, ProjectionPlane.AUDIT}:
            raise ValueError("MtdaFinalizationSectionContext is only valid for the test or audit projection planes")
        _require_kind(
            self.recipe_result_kind,
            RecipeResultKind.MTDA_FINALIZATION_SECTION,
            "MtdaFinalizationSectionContext",
        )
        _require_markup("title_html", self.title_html)
        _require_markup("body_html", self.body_html)


@dataclass(frozen=True, slots=True)
class ExportReadmeContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    page_title: str
    profile_label: Markup
    selected_count: Markup
    selection_source: Markup
    completion_status: Markup
    finalization_state: Markup
    selection_set: Markup
    warning_count: int

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.EXPORT_BUNDLE, "ExportReadmeContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.EXPORT_README, "ExportReadmeContext")
        _require_text("page_title", self.page_title)
        for name in (
            "profile_label",
            "selected_count",
            "selection_source",
            "completion_status",
            "finalization_state",
            "selection_set",
        ):
            _require_markup(name, getattr(self, name))
        if not isinstance(self.warning_count, int) or self.warning_count < 0:
            raise ValueError("warning_count must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class ExportHtmlPageMetadataRowContext:
    key_html: Markup
    value_html: Markup

    def __post_init__(self) -> None:
        _require_markup("key_html", self.key_html)
        _require_markup("value_html", self.value_html)


@dataclass(frozen=True, slots=True)
class ExportHtmlPageContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    title_html: Markup
    metadata_rows: tuple[ExportHtmlPageMetadataRowContext, ...]
    body_html: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.EXPORT_BUNDLE, "ExportHtmlPageContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.EXPORT_HTML_PAGE, "ExportHtmlPageContext")
        _require_markup("title_html", self.title_html)
        if not isinstance(self.metadata_rows, tuple):
            raise ValueError("metadata_rows must be a tuple")
        for row in self.metadata_rows:
            if not isinstance(row, ExportHtmlPageMetadataRowContext):
                raise ValueError("metadata_rows must contain ExportHtmlPageMetadataRowContext values")
        _require_markup("body_html", self.body_html)


@dataclass(frozen=True, slots=True)
class ExportVegaHtmlContext:
    projection_plane: ProjectionPlane
    recipe_result_kind: RecipeResultKind
    title_html: Markup
    spec_json: Markup

    def __post_init__(self) -> None:
        _require_plane(self.projection_plane, ProjectionPlane.EXPORT_BUNDLE, "ExportVegaHtmlContext")
        _require_kind(self.recipe_result_kind, RecipeResultKind.EXPORT_VEGA_HTML, "ExportVegaHtmlContext")
        _require_markup("title_html", self.title_html)
        _require_markup("spec_json", self.spec_json)


def _require_plane(actual: ProjectionPlane, expected: ProjectionPlane, context_name: str) -> None:
    if actual is not expected:
        raise ValueError(f"{context_name} is only valid for the {expected} projection plane")


def _require_test_or_audit_plane(actual: ProjectionPlane, context_name: str) -> None:
    if actual not in {ProjectionPlane.TEST, ProjectionPlane.AUDIT}:
        raise ValueError(f"{context_name} is only valid for TEST or AUDIT projection planes")


def _require_kind(actual: RecipeResultKind, expected: RecipeResultKind, context_name: str) -> None:
    if actual is not expected:
        raise ValueError(f"{context_name} must project the {expected} recipe/result kind")


def _require_markup(name: str, value: Markup) -> None:
    if not isinstance(value, Markup):
        raise ValueError(f"{name} must be an HTML-safe Markup fragment")


def _require_text(name: str, value: str) -> None:
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{name} must be a non-empty string")


def _require_string(name: str, value: str) -> None:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")


def _require_bool(name: str, value: bool) -> None:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean")
