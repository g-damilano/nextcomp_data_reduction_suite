from __future__ import annotations

from ._tokens import Color as C
from ._tokens import Font as F


def build_global_qss() -> str:
    return f"""
    QWidget {{
        font-family: {F.FAMILY};
        font-size: {F.BODY}pt;
        color: {C.TEXT};
        background: {C.BG};
    }}

    QMainWindow, QMenuBar {{
        background: {C.BG};
    }}
    QWidget#methodRunRoot,
    QScrollArea#methodRunViewport,
    QWidget#methodRunViewportFrame,
    QWidget#methodRunViewportContents,
    QWidget#methodRunColumn {{
        background: {C.BG};
    }}
    QMenuBar {{
        border-bottom: 0;
        padding: 5px 10px 3px 10px;
        min-height: 24px;
    }}
    QMenuBar::item {{
        background: transparent;
        padding: 4px 10px;
        margin-right: 2px;
        color: {C.TEXT};
    }}
    QMenuBar::item:selected {{
        background: {C.SURFACE_3};
        border-radius: 4px;
    }}
    QMenuBar::item:disabled {{
        color: {C.TEXT_3};
    }}
    QMenu {{
        background: {C.SURFACE};
        border: 1px solid {C.BORDER};
        padding: 4px;
        color: {C.TEXT};
    }}
    QMenu::item {{
        padding: 6px 28px 6px 12px;
        border-radius: 4px;
    }}
    QMenu::item:selected {{
        background: {C.SURFACE_3};
    }}
    QMenu::item:disabled {{
        color: {C.TEXT_3};
        background: transparent;
    }}

    QScrollArea {{
        border: none;
        background: {C.BG};
    }}
    QScrollArea#methodRunViewport > QWidget,
    QScrollArea > QWidget > QWidget {{
        background: {C.BG};
    }}

    /* Spotlight card */
    QFrame#spotlight {{
        background: {C.SURFACE};
        border: 1px solid {C.BORDER};
        border-radius: 10px;
    }}
    QStackedWidget#spotlightBody, QStackedWidget#spotlightFoot,
    QWidget#spotlightHead,
    QWidget#setupSpotlight, QWidget#runningSpotlight,
    QWidget#reviewSpotlight, QWidget#finalizeSpotlight {{
        background: {C.SURFACE};
        border: none;
    }}
    QFrame#methodPicker {{
        background: transparent;
        border: none;
    }}
    QFrame#setupInputSummary {{
        background: {C.SURFACE_2};
        border: 1px solid {C.BORDER};
        border-radius: 8px;
    }}
    QFrame#setupInputTile {{
        background: {C.SURFACE};
        border: 1px solid {C.BORDER};
        border-radius: 6px;
    }}
    QFrame#setupInputTile[state="todo"] {{
        background: {C.SURFACE};
        border-color: {C.BORDER};
    }}
    QFrame#setupInputTile[state="now"] {{
        background: {C.INFO_BG};
        border-color: {C.INFO_BORDER};
    }}
    QFrame#setupInputTile[state="ok"] {{
        background: {C.OK_BG};
        border-color: {C.OK_BORDER};
    }}
    QFrame#setupInputTile[state="warn"] {{
        background: {C.WARN_BG};
        border-color: {C.WARN_BORDER};
    }}
    QFrame#setupInputTile[state="err"] {{
        background: {C.ERR_BG};
        border-color: {C.ERR_BORDER};
    }}
    QFrame#setupInputTile QLabel {{
        background: transparent;
    }}
    QLabel#setupInputKey {{
        font-size: {F.CAPS}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        color: {C.TEXT_3};
        background: transparent;
    }}
    QLabel#setupInputValue {{
        font-size: {F.BODY}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        color: {C.TEXT};
        background: transparent;
    }}
    QLabel#setupInputSub {{
        font-size: {F.BODY_SMALL}pt;
        color: {C.TEXT_2};
        background: transparent;
    }}
    QPushButton#setupInputAction {{
        font-size: {F.BODY_SMALL}pt;
    }}
    QLabel#h1 {{
        font-size: {F.H1}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        color: {C.TEXT};
        background: transparent;
    }}
    QLabel#subtitle {{
        font-size: {F.BODY}pt;
        color: {C.TEXT_2};
        background: transparent;
    }}

    /* Task card */
    QFrame.taskCard, QFrame[class="taskCard"] {{
        background: {C.SURFACE_2};
        border: 1px solid {C.BORDER};
        border-radius: 8px;
    }}
    QFrame.taskCard QLabel, QFrame[class="taskCard"] QLabel {{
        background: transparent;
    }}
    QFrame#taskCard QWidget, QFrame.taskCard QWidget, QFrame[class="taskCard"] QWidget,
    QWidget#taskBody {{
        background: transparent;
    }}
    QFrame.taskCard QLabel.title, QFrame[class="taskCard"] QLabel.title {{
        font-size: {F.H_TASK}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        color: {C.TEXT};
    }}
    QLabel#taskWhy {{
        color: {C.TEXT_2};
        font-size: {F.BODY}pt;
        background: transparent;
    }}
    QLabel#badge {{
        font-size: {F.CAPS}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        letter-spacing: 0.5px;
        padding: 2px 8px;
        border-radius: 10px;
    }}
    QLabel#badge[kind="needs"] {{
        background: {C.WARN_BG};
        color: {C.WARN_INK};
        border: 1px solid {C.WARN_BORDER};
    }}
    QLabel#badge[kind="optional"] {{
        background: {C.SURFACE_3};
        color: {C.TEXT_2};
        border: 1px solid {C.BORDER};
    }}
    QLabel#chev {{
        color: {C.TEXT_3};
        font-size: {F.BODY_SMALL}pt;
        background: transparent;
    }}
    QLabel#setupCaps {{
        font-size: {F.CAPS}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        letter-spacing: 0.5px;
        background: transparent;
    }}
    QLabel#setupCaps[kind="ok"] {{
        color: {C.OK_INK};
    }}
    QLabel#setupCaps[kind="warn"] {{
        color: {C.WARN_INK};
    }}
    QLabel#setupChip {{
        font-size: {F.BODY_SMALL}pt;
        padding: 3px 8px;
        border-radius: 10px;
    }}
    QLabel#setupChip[kind="ok"] {{
        background: {C.OK_BG};
        color: {C.OK_INK};
        border: 1px solid {C.OK_BORDER};
    }}
    QLabel#setupChip[kind="neutral"] {{
        background: {C.SURFACE_3};
        color: {C.TEXT_2};
        border: 1px solid {C.BORDER};
    }}
    QLabel#setupEmptyState {{
        background: {C.OK_BG};
        color: {C.OK_INK};
        border: 1px solid {C.OK_BORDER};
        border-radius: 8px;
        padding: 22px;
        font-weight: {F.WEIGHT_SEMIBOLD};
    }}

    /* Pipeline pill */
    QFrame#pipePill, QFrame.pipePill, QFrame[class="pipePill"] {{
        font-size: {F.BODY}pt;
        color: {C.TEXT_3};
        padding: 0;
        border-radius: 3px;
        background: transparent;
        border: 1px solid transparent;
    }}
    QLabel.pipePill, QLabel[class="pipePill"] {{
        font-size: {F.BODY}pt;
        color: {C.TEXT_3};
        padding: 0;
        background: transparent;
        border: none;
    }}
    QFrame#pipePill[state="ok"], QFrame.pipePill[state="ok"], QFrame[class="pipePill"][state="ok"] {{
        color: {C.TEXT_2};
    }}
    QLabel.pipePill[state="ok"], QLabel[class="pipePill"][state="ok"] {{
        color: {C.TEXT_2};
    }}
    QFrame#pipePill[state="todo"], QFrame.pipePill[state="todo"], QFrame[class="pipePill"][state="todo"] {{
        color: {C.TEXT_3};
        background: transparent;
        border-color: transparent;
    }}
    QLabel.pipePill[state="todo"], QLabel[class="pipePill"][state="todo"] {{
        color: {C.TEXT_3};
    }}
    QFrame#pipePill[state="warn"], QFrame.pipePill[state="warn"], QFrame[class="pipePill"][state="warn"] {{
        color: {C.WARN_INK};
        background: transparent;
        border-color: {C.WARN_BORDER};
    }}
    QLabel.pipePill[state="warn"], QLabel[class="pipePill"][state="warn"] {{
        color: {C.WARN_INK};
    }}
    QFrame#pipePill[state="now"], QFrame.pipePill[state="now"], QFrame[class="pipePill"][state="now"] {{
        color: {C.INFO_INK};
        background: {C.INFO_BG};
        border-color: {C.INFO_BORDER};
        font-weight: {F.WEIGHT_SEMIBOLD};
    }}
    QLabel.pipePill[state="now"], QLabel[class="pipePill"][state="now"] {{
        color: {C.INFO_INK};
        font-weight: {F.WEIGHT_SEMIBOLD};
    }}
    QFrame#pipePill[state="err"], QFrame.pipePill[state="err"], QFrame[class="pipePill"][state="err"] {{
        color: {C.ERR_INK};
        background: transparent;
        border-color: {C.ERR_BORDER};
    }}
    QLabel.pipePill[state="err"], QLabel[class="pipePill"][state="err"] {{
        color: {C.ERR_INK};
    }}
    QFrame#pipeDot, QFrame.pipeDot, QFrame[class="pipeDot"] {{
        border-radius: 4px;
        background: {C.TEXT_3};
        border: none;
    }}
    QFrame#pipeDot[state="ok"], QFrame.pipeDot[state="ok"], QFrame[class="pipeDot"][state="ok"] {{
        background: {C.OK_ACCENT};
    }}
    QFrame#pipeDot[state="warn"], QFrame.pipeDot[state="warn"], QFrame[class="pipeDot"][state="warn"] {{
        background: {C.WARN_ACCENT};
    }}
    QFrame#pipeDot[state="now"], QFrame.pipeDot[state="now"], QFrame[class="pipeDot"][state="now"] {{
        background: {C.INFO_ACCENT};
    }}
    QFrame#pipeDot[state="now"][phase="1"], QFrame.pipeDot[state="now"][phase="1"],
    QFrame[class="pipeDot"][state="now"][phase="1"] {{
        background: {C.INFO_BORDER};
    }}
    QFrame#pipeDot[state="err"], QFrame.pipeDot[state="err"], QFrame[class="pipeDot"][state="err"] {{
        background: {C.ERR_ACCENT};
    }}
    QFrame#pipeDot[state="todo"], QFrame.pipeDot[state="todo"], QFrame[class="pipeDot"][state="todo"] {{
        background: {C.BORDER_STRONG};
    }}
    QFrame#pipeConnector, QFrame.pipeConnector, QFrame[class="pipeConnector"] {{
        background: {C.BORDER};
        border: none;
        min-width: 14px;
        max-height: 2px;
    }}
    QFrame#pipeConnector[state="ok"], QFrame.pipeConnector[state="ok"], QFrame[class="pipeConnector"][state="ok"] {{
        background: {C.OK_BORDER};
    }}
    QFrame#pipeConnector[state="warn"], QFrame.pipeConnector[state="warn"], QFrame[class="pipeConnector"][state="warn"] {{
        background: {C.WARN_BORDER};
    }}
    QFrame#pipeConnector[state="now"], QFrame.pipeConnector[state="now"], QFrame[class="pipeConnector"][state="now"] {{
        background: {C.INFO_BORDER};
    }}
    QFrame#pipeConnector[state="err"], QFrame.pipeConnector[state="err"], QFrame[class="pipeConnector"][state="err"] {{
        background: {C.ERR_BORDER};
    }}
    QLabel#crumb {{
        font-size: {F.CAPS}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        color: {C.TEXT_3};
        background: transparent;
    }}

    /* Action bar */
    QFrame#actionBar {{
        background: {C.SURFACE};
        border-top: 1px solid {C.BORDER};
    }}
    QLabel#actionLabel {{
        font-size: {F.BODY}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        color: {C.TEXT};
        background: transparent;
    }}
    QLabel#actionSub {{
        font-size: {F.BODY_SMALL}pt;
        color: {C.TEXT_2};
        background: transparent;
    }}

    /* Primary button */
    QPushButton.primary, QPushButton[class="primary"] {{
        background: {C.ACCENT};
        color: white;
        border: 1px solid {C.ACCENT};
        padding: 8px 18px;
        min-height: 18px;
        border-radius: 4px;
        font-weight: {F.WEIGHT_SEMIBOLD};
    }}
    QPushButton.primary:hover, QPushButton[class="primary"]:hover {{
        background: {C.ACCENT_HOVER};
        border-color: {C.ACCENT_HOVER};
    }}
    QPushButton.primary:disabled, QPushButton[class="primary"]:disabled {{
        background: {C.SURFACE_3};
        color: {C.TEXT_3};
        border-color: {C.BORDER};
    }}

    /* Danger button */
    QPushButton.danger, QPushButton[class="danger"] {{
        background: {C.DANGER};
        color: white;
        border: 1px solid {C.DANGER};
        padding: 6px 14px;
        min-height: 18px;
        border-radius: 4px;
        font-weight: {F.WEIGHT_SEMIBOLD};
    }}
    QPushButton.danger:hover, QPushButton[class="danger"]:hover {{
        background: {C.DANGER_HOVER};
        border-color: {C.DANGER_HOVER};
    }}

    /* Subtle / link buttons */
    QPushButton.subtle, QPushButton[class="subtle"] {{
        background: {C.SURFACE};
        border: 1px solid {C.BORDER};
        color: {C.TEXT_2};
        padding: 6px 12px;
        min-height: 18px;
        border-radius: 4px;
    }}
    QPushButton.subtle:hover, QPushButton[class="subtle"]:hover {{
        background: {C.SURFACE_3};
        color: {C.TEXT};
        border-color: {C.BORDER};
    }}
    QPushButton.link, QPushButton[class="link"] {{
        background: transparent;
        border: none;
        color: {C.ACCENT};
        padding: 0;
        font-size: {F.BODY}pt;
    }}
    QPushButton.link:hover, QPushButton[class="link"]:hover {{
        text-decoration: underline;
        background: transparent;
    }}

    QPushButton {{
        background: {C.SURFACE};
        color: {C.TEXT};
        border: 1px solid {C.BORDER_STRONG};
        padding: 6px 14px;
        min-height: 18px;
        border-radius: 4px;
    }}
    QPushButton:hover {{
        background: {C.SURFACE_3};
    }}
    QPushButton:disabled {{
        color: {C.TEXT_3};
        border-color: {C.BORDER};
        background: {C.SURFACE_3};
    }}
    QFrame.taskCard QPushButton[class="primary"],
    QFrame[class="taskCard"] QPushButton[class="primary"],
    QWidget#taskBody QPushButton[class="primary"] {{
        background: {C.ACCENT};
        color: white;
        border: 1px solid {C.ACCENT};
    }}
    QFrame.taskCard QPushButton[class="primary"]:hover,
    QFrame[class="taskCard"] QPushButton[class="primary"]:hover,
    QWidget#taskBody QPushButton[class="primary"]:hover {{
        background: {C.ACCENT_HOVER};
        border-color: {C.ACCENT_HOVER};
    }}
    QFrame.taskCard QPushButton[class="subtle"],
    QFrame[class="taskCard"] QPushButton[class="subtle"],
    QWidget#taskBody QPushButton[class="subtle"] {{
        background: {C.SURFACE};
        color: {C.TEXT_2};
        border: 1px solid {C.BORDER};
    }}
    QFrame.taskCard QPushButton[class="link"],
    QFrame[class="taskCard"] QPushButton[class="link"],
    QWidget#taskBody QPushButton[class="link"] {{
        background: transparent;
        color: {C.ACCENT};
        border: none;
    }}

    /* Inputs */
    QLineEdit {{
        border: 1px solid {C.BORDER_STRONG};
        background: {C.SURFACE};
        padding: 5px 10px;
        border-radius: 4px;
        color: {C.TEXT};
        selection-background-color: {C.ACCENT};
        selection-color: white;
    }}
    QLineEdit:focus {{
        border-color: {C.ACCENT};
    }}

    /* Tables */
    QTableWidget {{
        background: transparent;
        alternate-background-color: {C.SURFACE_2};
        gridline-color: {C.BORDER};
        font-size: {F.BODY}pt;
        color: {C.TEXT};
        border: 1px solid {C.BORDER};
        border-radius: 4px;
    }}
    QTableWidget::item {{
        padding: 4px 8px;
    }}
    QTableWidget::item:selected {{
        background: {C.ACCENT_SOFT};
        color: {C.TEXT};
    }}
    QHeaderView::section {{
        background: {C.SURFACE_3};
        color: {C.TEXT_2};
        font-weight: {F.WEIGHT_SEMIBOLD};
        font-size: {F.BODY_SMALL}pt;
        padding: 6px 10px;
        border: none;
        border-bottom: 1px solid {C.BORDER};
    }}

    /* Mapping review dialog */
    QLabel#mappingDialogTitle {{
        font-size: {F.H2}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        color: {C.TEXT};
        background: transparent;
    }}
    QFrame#mappingSummary {{
        background: transparent;
        border: none;
    }}
    QFrame#mappingSummaryTile {{
        background: {C.SURFACE_2};
        border: 1px solid {C.BORDER};
        border-radius: 6px;
    }}
    QFrame#mappingSummaryTile[level="ok"] {{
        border-color: {C.OK_BORDER};
    }}
    QFrame#mappingSummaryTile[level="warn"] {{
        border-color: {C.WARN_BORDER};
    }}
    QFrame#mappingSummaryTile[level="err"] {{
        border-color: {C.ERR_BORDER};
    }}
    QLabel#mappingSummaryKey {{
        font-size: {F.CAPS}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        color: {C.TEXT_3};
        background: transparent;
    }}
    QLabel#mappingSummaryValue {{
        font-size: {F.H_TASK}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        color: {C.TEXT};
        background: transparent;
    }}
    QLabel#mappingGuidance {{
        font-size: {F.BODY}pt;
    }}
    QLabel#mappingPreview {{
        background: {C.INFO_BG};
        color: {C.INFO_INK};
        border: 1px solid {C.INFO_BORDER};
        border-radius: 6px;
        padding: 7px 9px;
    }}
    QLabel#mappingConsequence {{
        background: {C.SURFACE};
        color: {C.TEXT_2};
        border: 1px dashed {C.BORDER};
        border-radius: 6px;
        padding: 7px 9px;
    }}
    QFrame#mappingActionPanel {{
        background: {C.SURFACE_2};
        border: 1px solid {C.BORDER};
        border-radius: 6px;
    }}
    QLabel#mappingActionKey {{
        font-size: {F.CAPS}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        color: {C.TEXT_3};
        background: transparent;
    }}
    QListWidget#mappingActionList {{
        background: transparent;
        border: none;
        color: {C.TEXT_2};
    }}
    QListWidget#mappingActionList::item {{
        padding: 2px 0;
    }}
    QTableWidget#mappingIssueTable {{
        background: {C.SURFACE};
    }}

    /* Context line */
    QFrame#decorBottom {{
        background: transparent;
    }}
    QFrame#ctxLine {{
        background: {C.SURFACE};
        border: 1px solid {C.BORDER};
        border-radius: 6px;
    }}
    QFrame#ctxLine QLabel {{
        background: transparent;
    }}
    QLabel#ctxChev {{
        color: {C.TEXT_3};
        background: transparent;
    }}
    QFrame#ctxDetail {{
        background: {C.SURFACE_2};
        border: 1px solid {C.BORDER};
        border-radius: 6px;
    }}
    QLabel.ctxKey, QLabel[class="ctxKey"] {{
        font-size: {F.CAPS}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        color: {C.TEXT_3};
        background: transparent;
    }}
    QFrame.ctxRow, QFrame[class="ctxRow"] {{
        background: transparent;
        border-bottom: 1px dashed {C.BORDER};
    }}
    QFrame.ctxRow QLabel, QFrame[class="ctxRow"] QLabel {{
        background: transparent;
    }}

    /* Running */
    QLabel#runningPhase {{
        font-size: {F.H2}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        background: transparent;
    }}
    QLabel#runningMeta {{
        font-size: {F.BODY_SMALL}pt;
        color: {C.TEXT_3};
        background: transparent;
    }}
    QLabel#runningPct {{
        font-size: {F.PCT}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        background: transparent;
    }}
    QLabel#runningError {{
        background: {C.ERR_BG};
        color: {C.ERR_INK};
        border: 1px solid {C.ERR_BORDER};
        border-radius: 6px;
        padding: 8px 10px;
    }}
    QProgressBar {{
        background: {C.SURFACE_3};
        border: none;
        border-radius: 3px;
        height: 6px;
    }}
    QProgressBar::chunk {{
        background: {C.ACCENT};
        border-radius: 3px;
    }}
    QFrame#runningStageStrip {{
        background: transparent;
        border: none;
    }}
    QLabel#runningStage {{
        font-size: {F.CAPS}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        padding: 3px 6px;
        border-radius: 4px;
        background: {C.SURFACE_2};
        color: {C.TEXT_3};
        border: 1px solid {C.BORDER};
    }}
    QLabel#runningStage[state="done"] {{
        background: {C.OK_BG};
        color: {C.OK_INK};
        border-color: {C.OK_BORDER};
    }}
    QLabel#runningStage[state="now"] {{
        background: {C.INFO_BG};
        color: {C.INFO_INK};
        border-color: {C.INFO_BORDER};
    }}
    QFrame#runningSummary {{
        background: transparent;
        border: none;
    }}
    QFrame#runningSummaryTile {{
        background: {C.SURFACE_2};
        border: 1px solid {C.BORDER};
        border-radius: 6px;
    }}
    QLabel#runningSummaryKey {{
        font-size: {F.CAPS}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        color: {C.TEXT_3};
        background: transparent;
    }}
    QLabel#runningSummaryValue {{
        font-size: {F.BODY_SMALL}pt;
        color: {C.TEXT};
        background: transparent;
    }}
    QLabel#runningTraceHead {{
        font-size: {F.CAPS}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        color: {C.TEXT_3};
        background: transparent;
    }}
    QListWidget#runningTrace {{
        background: {C.SURFACE_2};
        border: 1px solid {C.BORDER};
        border-radius: 6px;
        color: {C.TEXT};
        padding: 4px 6px;
    }}
    QListWidget#runningTrace::item {{
        padding: 2px 0;
    }}

    /* Review */
    QFrame#reviewSummary {{
        background: {C.SURFACE_2};
        border: 1px solid {C.BORDER};
        border-radius: 8px;
    }}
    QFrame#reviewSummaryTile {{
        background: {C.SURFACE};
        border: 1px solid {C.BORDER};
        border-radius: 6px;
    }}
    QFrame#reviewSummaryTile[state="warn"] {{
        background: {C.WARN_BG};
        border-color: {C.WARN_BORDER};
    }}
    QFrame#reviewSummaryTile[state="ok"] {{
        background: {C.OK_BG};
        border-color: {C.OK_BORDER};
    }}
    QLabel#reviewSummaryKey {{
        font-size: {F.CAPS}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        color: {C.TEXT_3};
        background: transparent;
    }}
    QLabel#reviewSummaryValue {{
        font-size: {F.BODY_LARGE}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        color: {C.TEXT};
        background: transparent;
    }}
    QLabel#reviewSummarySub {{
        font-size: {F.BODY_SMALL}pt;
        color: {C.TEXT_2};
        background: transparent;
    }}
    QFrame#acceptanceHeader {{
        background: {C.SURFACE_3};
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        border-bottom: 1px solid {C.BORDER};
    }}
    QLabel#acceptHeaderLabel {{
        font-size: {F.CAPS}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        color: {C.TEXT_3};
        background: transparent;
    }}
    QFrame#acceptanceRow {{
        background: {C.SURFACE};
        border-bottom: 1px solid {C.BORDER};
    }}
    QFrame#acceptanceMainRow {{
        background: transparent;
    }}
    QFrame#acceptanceMainRow[decision="keep"] {{
        background: {C.WARN_BG};
    }}
    QFrame#acceptanceMainRow[decision="remove"] {{
        background: {C.SURFACE_2};
    }}
    QFrame#acceptanceMainRow QLabel {{
        background: transparent;
    }}
    QLabel#acceptRun {{
        min-width: 70px;
        font-weight: {F.WEIGHT_SEMIBOLD};
        color: {C.TEXT};
        background: transparent;
    }}
    QLabel#acceptCall {{
        min-width: 74px;
        color: {C.TEXT_2};
        background: transparent;
    }}
    QLabel#acceptDefects {{
        min-width: 150px;
        font-weight: {F.WEIGHT_SEMIBOLD};
        color: {C.TEXT};
        background: transparent;
    }}
    QLabel#acceptReason {{
        color: {C.TEXT};
        background: transparent;
    }}
    QFrame#acceptanceFlagCluster {{
        background: {C.SURFACE_2};
        border: 1px solid {C.BORDER};
        border-radius: 6px;
        padding: 8px;
    }}
    QLabel#acceptanceFlagTitle {{
        font-size: {F.CAPS}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        color: {C.TEXT_3};
        background: transparent;
    }}
    QLabel#acceptanceFlagLine {{
        color: {C.TEXT};
        background: transparent;
    }}
    QFrame#evidencePane {{
        background: {C.SURFACE_2};
        border-top: 1px dashed {C.BORDER};
    }}
    QFrame#bendingSparkline {{
        background: {C.SURFACE};
        border: 1px solid {C.BORDER};
        border-radius: 6px;
    }}
    QFrame#metricTile {{
        background: {C.SURFACE};
        border: 1px solid {C.BORDER};
        border-radius: 6px;
    }}
    QFrame#metricTile[state="gap"] {{
        background: {C.WARN_BG};
        border: 1px solid {C.WARN_BORDER};
    }}
    QLabel#metricKey {{
        font-size: {F.CAPS}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        color: {C.TEXT_3};
        background: transparent;
    }}
    QLabel#metricValue {{
        font-size: {F.H_TASK}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        color: {C.TEXT};
        background: transparent;
    }}
    QLabel#metricValue[level="warn"] {{
        color: {C.WARN_INK};
    }}
    QLabel#metricSub {{
        font-size: {F.BODY_SMALL}pt;
        color: {C.TEXT_2};
        background: transparent;
    }}
    QLabel#evidenceNarrative {{
        color: {C.TEXT_2};
        background: transparent;
    }}
    QFrame#overrideJustifyRow {{
        background: {C.WARN_BG};
        border-top: 1px solid {C.WARN_BORDER};
    }}
    QLabel#overrideKey {{
        font-size: {F.CAPS}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        color: {C.WARN_INK};
        background: transparent;
    }}
    QLabel#overrideScope {{
        color: {C.TEXT_2};
        background: transparent;
    }}

    /* Finalize */
    QFrame#finalizeSummary {{
        background: {C.SURFACE_2};
        border: 1px solid {C.BORDER};
        border-radius: 8px;
    }}
    QFrame#finalizeSummaryTile {{
        background: {C.SURFACE};
        border: 1px solid {C.BORDER};
        border-radius: 6px;
    }}
    QFrame#finalizeSummaryTile[state="warn"] {{
        background: {C.WARN_BG};
        border-color: {C.WARN_BORDER};
    }}
    QFrame#finalizeSummaryTile[state="ok"] {{
        background: {C.OK_BG};
        border-color: {C.OK_BORDER};
    }}
    QLabel#finalizeSummaryKey {{
        font-size: {F.CAPS}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        color: {C.TEXT_3};
        background: transparent;
    }}
    QLabel#finalizeSummaryValue {{
        font-size: {F.BODY_LARGE}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        color: {C.TEXT};
        background: transparent;
    }}
    QLabel#finalizeSummarySub {{
        font-size: {F.BODY_SMALL}pt;
        color: {C.TEXT_2};
        background: transparent;
    }}
    QFrame#finalizePanel {{
        background: {C.SURFACE_2};
        border: 1px solid {C.BORDER};
        border-radius: 8px;
    }}
    QFrame#finalizePanel QLabel {{
        background: transparent;
    }}
    QLabel#finalizeCaps {{
        font-size: {F.CAPS}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        color: {C.TEXT_3};
        background: transparent;
    }}
    QLabel#finalizeFieldLabel {{
        font-size: {F.BODY_SMALL}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        color: {C.TEXT_2};
        background: transparent;
    }}
    QLabel#finalizeHint, QLabel#finalizePathName {{
        font-size: {F.BODY_SMALL}pt;
        color: {C.TEXT_2};
        background: transparent;
    }}
    QLineEdit#finalizePath {{
        font-size: {F.BODY_SMALL}pt;
        color: {C.TEXT_2};
        background: {C.SURFACE};
        border: 1px solid {C.BORDER};
        border-radius: 4px;
        padding: 6px 8px;
    }}
    QPushButton#finalizeOpenButton {{
        text-align: left;
        background: {C.SURFACE};
        border: 1px solid {C.BORDER};
        border-radius: 6px;
        color: {C.TEXT};
        padding: 9px 14px;
        min-height: 28px;
    }}
    QPushButton#finalizeOpenButton:hover {{
        background: {C.INFO_BG};
        border-color: {C.INFO_BORDER};
        color: {C.INFO_INK};
    }}
    QPushButton#finalizeOpenButton:focus {{
        border-color: {C.ACCENT};
    }}
    QLabel#finalizeToast {{
        background: {C.OK_BG};
        color: {C.OK_INK};
        border: 1px solid {C.OK_BORDER};
        border-radius: 6px;
        padding: 7px 10px;
    }}
    QLabel#finalizeError {{
        background: {C.ERR_BG};
        color: {C.ERR_INK};
        border: 1px solid {C.ERR_BORDER};
        border-radius: 6px;
        padding: 8px 10px;
    }}

    /* Activity log */
    QWidget#activityLogDrawer {{
        background: {C.LOG_BG};
        color: {C.LOG_FG};
        border-left: 1px solid {C.LOG_BORDER};
    }}
    QWidget#activityLogDrawer QLabel {{
        background: transparent;
        color: {C.LOG_FG};
    }}
    QLabel#activityLogTitle {{
        font-size: {F.BODY_LARGE}pt;
        font-weight: {F.WEIGHT_SEMIBOLD};
        color: {C.LOG_FG};
    }}
    QLabel#activityLogCount {{
        font-size: {F.BODY_SMALL}pt;
        color: {C.LOG_TS};
    }}
    QPushButton#logClose {{
        background: transparent;
        border: 1px solid {C.LOG_BORDER};
        border-radius: 5px;
        color: {C.LOG_FG};
        padding: 4px 8px;
        font-size: {F.BODY_SMALL}pt;
    }}
    QPushButton#logClose:hover {{
        background: {C.LOG_HOVER};
    }}
    QPlainTextEdit#activityLog {{
        background: transparent;
        color: {C.LOG_FG};
        border: none;
        font-family: {F.FAMILY_MONO};
        font-size: {F.BODY_SMALL}pt;
    }}

    /* Status bar */
    QStatusBar {{
        background: {C.CANVAS};
        border-top: 1px solid {C.BORDER};
        color: {C.TEXT_2};
        font-size: {F.BODY_SMALL}pt;
    }}
    QStatusBar QLabel {{
        background: transparent;
        color: {C.TEXT_2};
        font-size: {F.BODY_SMALL}pt;
    }}
    QStatusBar QPushButton {{
        background: transparent;
        border: none;
        color: {C.ACCENT};
        padding: 0;
        font-size: {F.BODY_SMALL}pt;
    }}
    """
