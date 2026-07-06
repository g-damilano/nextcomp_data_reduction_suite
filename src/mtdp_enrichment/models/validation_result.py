from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    message: str
    field: str | None = None
    code: str | None = None


@dataclass(slots=True)
class ValidationResult:
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def add_error(self, message: str, *, field: str | None = None, code: str | None = None) -> None:
        self.errors.append(ValidationIssue(message=message, field=field, code=code))

    def add_warning(self, message: str, *, field: str | None = None, code: str | None = None) -> None:
        self.warnings.append(ValidationIssue(message=message, field=field, code=code))

    def extend(self, other: "ValidationResult") -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)

    def messages(self) -> list[str]:
        return [issue.message for issue in self.errors + self.warnings]

