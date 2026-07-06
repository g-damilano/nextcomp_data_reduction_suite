__all__ = [
    "MethodRunWindow",
    "MethodRunController",
    "MethodRunWizardState",
    "WizardScenario",
]


def __getattr__(name: str):
    if name == "MethodRunController":
        from ui.method_run_wizard.controller import MethodRunController

        return MethodRunController
    if name == "MethodRunWindow":
        from ui.method_run_wizard.window import MethodRunWindow

        return MethodRunWindow
    if name in {"MethodRunWizardState", "WizardScenario"}:
        from ui.method_run_wizard.state import MethodRunWizardState, WizardScenario

        return {
            "MethodRunWizardState": MethodRunWizardState,
            "WizardScenario": WizardScenario,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
