from __future__ import annotations

import os
from dataclasses import dataclass
from html import escape

from markupsafe import Markup

from html_renderer.context_models import (
    ReportMethodsAppendixContext,
    ReportMethodsAppendixItemContext,
    ReportNoteAsideContext,
    ReportNoteMarkerContext,
    ReportNoteParagraphContext,
)
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind
from html_renderer.render import (
    render_report_methods_appendix,
    render_report_note_aside,
    render_report_note_marker,
)


REPORT_FORMATTING_CSS = """
/* nav + main keep the same width as the header card; notes stay inline as bounded popovers */
.layout { grid-template-columns: 310px minmax(0, 1fr); }
@media (max-width: 1280px){ .layout { grid-template-columns: 310px minmax(0,1fr); } }

/* nav active-section highlight, in the report's brand */
.report-tracker a.active { background: #eef7fc; color: var(--brand); font-weight: 700;
  box-shadow: inset 3px 0 0 var(--brand); }
/* active run-packet sublink: keep it legible at the smaller sublist size */
.report-tracker-sublist a.active { background: #eef7fc; color: var(--brand); font-weight: 700;
  box-shadow: inset 2px 0 0 var(--brand); }
.report-tracker-sublist a.active span, .report-tracker-sublist a.active b { color: var(--brand); }

/* the audit-block becomes the positioning context for its inline note popover */
.audit-block.note-anchor { position: relative; }
.audit-block.note-anchor h3 { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

/* the "i" marker beside the h3 */
.note-marker { display: inline-flex; align-items: center; justify-content: center;
  width: 18px; height: 18px; padding: 0; border: 0; font-family: Arial, Helvetica, sans-serif;
  font-size: 11px; line-height: 1; font-weight: 700; font-style: normal;
  color: var(--brand); background: #eef7fc; border: 1px solid #cfe3f0; border-radius: 50%;
  cursor: help; vertical-align: middle; }
.note-marker:focus-visible { outline: 2px solid var(--brand); outline-offset: 2px; }

/* note popover: kept inside the content column, opened from the inline info control */
aside.note {
  position: absolute; top: 30px; left: 0;
  width: min(460px, calc(100% - 24px));
  max-width: calc(100% - 24px);
  max-height: min(60vh, 440px); overflow: auto;
  /* reset inherited type, match report body */
  font-family: Arial, Helvetica, sans-serif; font-weight: 400; font-style: normal;
  font-size: 12.5px; line-height: 1.5; letter-spacing: normal; text-align: left;
  color: var(--muted);
  background: var(--soft); border: 1px solid var(--line); border-left: 3px solid var(--brand);
  border-radius: 10px; padding: 12px 14px;
  box-shadow: 0 10px 30px rgba(15, 32, 48, .18);
  opacity: 0; transform: translateY(-6px); pointer-events: none; z-index: 60;
  transition: opacity .25s ease, transform .25s ease; }
aside.note::before { content: ""; position: absolute; top: -7px; left: 16px;
  border: 7px solid transparent; border-top: 0; border-bottom: 7px solid var(--soft);
  filter: drop-shadow(0 -1px 0 var(--line)); }
aside.note.visible { opacity: 0; transform: translateY(-6px); pointer-events: none; }
.note-anchor h3:hover ~ aside.note, .note-anchor h3:focus-within ~ aside.note,
.note-anchor summary:hover ~ .detail-body aside.note, .note-anchor summary:focus-within ~ .detail-body aside.note,
.note-anchor.open aside.note, aside.note:hover {
  opacity: 1; transform: translateY(0); pointer-events: auto; }
aside.note .note-label { font-size: 10.5px; text-transform: uppercase; letter-spacing: .08em;
  color: var(--brand); font-weight: 700; margin-bottom: 6px; }
aside.note p { margin: 0 0 8px; } aside.note p:last-child { margin-bottom: 0; }
aside.note code { background: #e7eef4; }

/* print appendix hidden on screen */
.methods-appendix { display: none; }

/* ---- narrow screens: keep the note inside the scrollable content width ---- */
@media (max-width: 1280px){
  aside.note {
    width: min(420px, calc(100% - 16px));
    max-width: calc(100% - 16px);
  }
}
@media (prefers-reduced-motion: reduce){ aside.note { transition: none; } }

/* ---- print: drop notes in place, render the methods appendix ---- */
@media print {
  .layout { grid-template-columns: 1fr; }
  aside.note, .note-marker { display: none !important; }
  .report-tracker a.active { box-shadow: none; background: transparent; }
  .methods-appendix { display: block; break-before: page; }
  .methods-appendix h2 { font-size: 19px; margin: 0 0 6px; }
  .methods-appendix .appendix-lede { color: var(--muted); font-size: 13px; margin: 0 0 16px; }
  .methods-appendix .appendix-item { break-inside: avoid; margin: 0 0 16px; }
  .methods-appendix .appendix-item h3 { font-size: 14px; margin: 0 0 4px; }
  .methods-appendix .appendix-item .ref { font-size: 11px; color: var(--muted); font-weight: 400; }
  .methods-appendix .appendix-item p { font-size: 12.5px; margin: 0 0 7px; }
}

@media print {
  .layout { display: block; }
  .report-tracker { display: none !important; }
}
"""


REPORT_FORMATTING_SCRIPT = """
<script>
/* ===== GRAFTED: scrollspy nav + inline note popovers ===== */
(function(){
  function init(){
    var links=[].slice.call(document.querySelectorAll('.report-tracker a[href^="#"]'));
    var map={}; var targets=[];
    links.forEach(function(a){
      var id=a.getAttribute('href').slice(1);
      var t=document.getElementById(id);
      if(t){ map[id]=a; targets.push(t); }
    });
    var visible={};
    // Pick the active target: the element whose top has most recently crossed
    // a trigger line near the top of the viewport. This prefers a child
    // run-packet over its parent section (the child's top crossed last).
    function activeId(){
      var line=(window.innerHeight||document.documentElement.clientHeight)*0.18;
      var best=null,bestTop=-1e9;
      for(var id in visible){ if(!visible[id])continue;
        var t=document.getElementById(id).getBoundingClientRect().top;
        if(t<=line && t>bestTop){ bestTop=t; best=id; }
      }
      if(best) return best;
      var fy=1e9;
      for(var id2 in visible){ if(!visible[id2])continue;
        var y=document.getElementById(id2).getBoundingClientRect().top;
        if(y<fy){fy=y;best=id2;} }
      return best;
    }
    // a run-packet also lights its parent section link
    function activeSet(id){
      var set={}; if(!id) return set;
      set['#'+id]=1;
      var el=document.getElementById(id);
      if(el && el.classList.contains('run-packet')) set['#run_wise_evidence_packets']=1;
      return set;
    }
    var obs=new IntersectionObserver(function(es){
      es.forEach(function(e){ visible[e.target.id]=e.isIntersecting; });
      var set=activeSet(activeId());
      links.forEach(function(a){
        a.classList.toggle('active', !!set[a.getAttribute('href')]); });
    },{rootMargin:'-8% 0px -45% 0px', threshold:0});
    targets.forEach(function(t){obs.observe(t);});

    // marker tap / keyboard (narrow screens)
    function setOpen(anchor, isOpen){
      if(!anchor)return;
      anchor.classList.toggle('open', isOpen);
      var marker=anchor.querySelector('.note-marker');
      if(marker) marker.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    }
    document.querySelectorAll('.note-marker').forEach(function(m){
      var a=m.closest('.note-anchor');
      if(!a)return;
      function tog(ev){ ev.preventDefault();
        var next=!a.classList.contains('open');
        document.querySelectorAll('.note-anchor.open').forEach(function(o){ if(o!==a)setOpen(o,false); });
        setOpen(a,next); }
      m.addEventListener('click',tog);
      m.addEventListener('keydown',function(e){
        if(e.key==='Enter'||e.key===' ')tog(e);
        if(e.key==='Escape')setOpen(a,false); });
    });
    document.addEventListener('click',function(e){
      if(!e.target.closest('.note-anchor'))
        document.querySelectorAll('.note-anchor.open').forEach(function(o){setOpen(o,false);});
    });
  }
  if(document.readyState!=='loading') init();
  else document.addEventListener('DOMContentLoaded', init);
})();
</script>
"""


@dataclass(frozen=True)
class NoteParagraph:
    role: str
    html: str


@dataclass(frozen=True)
class CollectedNote:
    title: str
    label: str
    paragraphs: tuple[NoteParagraph, ...]


class ReportNoteCollector:
    def __init__(self, *, projection_plane: ProjectionPlane = ProjectionPlane.TEST) -> None:
        if projection_plane not in {ProjectionPlane.TEST, ProjectionPlane.AUDIT}:
            raise ValueError("ReportNoteCollector is only valid for TEST or AUDIT projection planes")
        self.projection_plane = projection_plane
        self.items: list[CollectedNote] = []

    def add(self, *, title: str, paragraphs: list[NoteParagraph]) -> str:
        clean = [paragraph for paragraph in paragraphs if paragraph.html.strip()]
        if not clean:
            return ""
        label = note_label(clean)
        note = CollectedNote(title=title, label=label, paragraphs=tuple(clean))
        self.items.append(note)
        return render_note_aside(note, projection_plane=self.projection_plane)


def note_text(role: str, text: str) -> NoteParagraph:
    return NoteParagraph(role=role, html=escape(text.strip()))


def note_html(role: str, inner_html: str) -> NoteParagraph:
    return NoteParagraph(role=role, html=inner_html.strip())


def note_label(paragraphs: list[NoteParagraph] | tuple[NoteParagraph, ...]) -> str:
    roles = {paragraph.role for paragraph in paragraphs}
    ordered: list[str] = []
    for role, label in (
        ("definition", "Definition"),
        ("method", "Method"),
        ("figure", "Figure"),
    ):
        if role in roles:
            ordered.append(label)
    return " & ".join(ordered) if ordered else "Method"


def _legacy_renderer_enabled() -> bool:
    return os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy"


def render_note_marker(*, projection_plane: ProjectionPlane = ProjectionPlane.TEST) -> str:
    if _legacy_renderer_enabled():
        return _legacy_render_note_marker()
    return render_report_note_marker(
        ReportNoteMarkerContext(
            projection_plane=projection_plane,
            recipe_result_kind=RecipeResultKind.REPORT_NOTE_MARKER,
        )
    )


def _legacy_render_note_marker() -> str:
    return '<button type="button" class="note-marker" aria-label="Show method note" aria-expanded="false">i</button>'


def render_note_aside(note: CollectedNote, *, projection_plane: ProjectionPlane = ProjectionPlane.TEST) -> str:
    if _legacy_renderer_enabled():
        return _legacy_render_note_aside(note)
    return render_report_note_aside(
        ReportNoteAsideContext(
            projection_plane=projection_plane,
            recipe_result_kind=RecipeResultKind.REPORT_NOTE_ASIDE,
            label_html=Markup(escape(note.label)),
            paragraphs=_note_paragraph_contexts(note.paragraphs),
        )
    )


def _legacy_render_note_aside(note: CollectedNote) -> str:
    paragraphs = "".join(f"<p>{paragraph.html}</p>" for paragraph in note.paragraphs)
    return (
        '<aside class="note" role="note">'
        f'<div class="note-label">{escape(note.label)}</div>'
        f"{paragraphs}</aside>"
    )


def render_methods_appendix(
    collector: ReportNoteCollector,
    *,
    projection_plane: ProjectionPlane = ProjectionPlane.TEST,
) -> str:
    if _legacy_renderer_enabled():
        return _legacy_render_methods_appendix(collector)
    return render_report_methods_appendix(
        ReportMethodsAppendixContext(
            projection_plane=projection_plane,
            recipe_result_kind=RecipeResultKind.REPORT_METHODS_APPENDIX,
            heading_html=Markup("Appendix A \u2014 Methods &amp; definitions"),
            lede_html=Markup(
                "Method and definitional context for the sections above, "
                "collected for the printed record."
            ),
            items=tuple(
                ReportMethodsAppendixItemContext(
                    title_html=Markup(escape(note.title)),
                    label_html=Markup(escape(note.label.lower())),
                    paragraphs=_note_paragraph_contexts(note.paragraphs),
                )
                for note in collector.items
            ),
        )
    )


def _legacy_render_methods_appendix(collector: ReportNoteCollector) -> str:
    items = []
    for index, note in enumerate(collector.items, start=1):
        paragraphs = "".join(f"<p>{paragraph.html}</p>" for paragraph in note.paragraphs)
        items.append(
            '<div class="appendix-item">'
            f"<h3>A.{index} {escape(note.title)} "
            f'<span class="ref">({escape(note.label.lower())})</span></h3>'
            f"{paragraphs}</div>"
        )
    return (
        '<section class="methods-appendix" aria-hidden="true">'
        "<h2>Appendix A — Methods &amp; definitions</h2>"
        '<p class="appendix-lede">Method and definitional context for the sections above, '
        "collected for the printed record.</p>"
        f"{''.join(items)}</section>"
    )


def _note_paragraph_contexts(paragraphs: tuple[NoteParagraph, ...]) -> tuple[ReportNoteParagraphContext, ...]:
    return tuple(ReportNoteParagraphContext(html=Markup(paragraph.html)) for paragraph in paragraphs)
