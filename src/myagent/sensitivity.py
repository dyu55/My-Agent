from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum


class Sensitivity(IntEnum):
    PUBLIC = 0
    INTERNAL = 1
    CONFIDENTIAL = 2
    SECRET = 3


_PATTERNS = {
    Sensitivity.SECRET: [
        r"-----BEGIN [A-Z ]+PRIVATE KEY-----",
        r"\b(?:sk|ghp|github_pat|xox[baprs])_[A-Za-z0-9_-]{12,}",
        r"(?i)\b(?:password|passwd|secret|api[_ -]?key|token)\s*[:=]\s*[^\s]{8,}",
    ],
    Sensitivity.CONFIDENTIAL: [
        r"\b\d{3}-\d{2}-\d{4}\b",
        r"\b(?:\d[ -]*?){13,19}\b",
        r"(?i)\b(?:private|confidential|internal[- ]only)\b",
    ],
    Sensitivity.INTERNAL: [r"(?i)\b(?:proprietary|unreleased|non-public|私有|内部|未发布)\b"],
}


@dataclass(frozen=True)
class Finding:
    level: Sensitivity
    label: str
    start: int
    end: int


@dataclass(frozen=True)
class Assessment:
    level: Sensitivity
    findings: tuple[Finding, ...]
    route: str
    redacted_text: str

    @property
    def external_allowed(self) -> bool:
        return self.route == "external_allowed"


def assess(text: str) -> Assessment:
    findings = []
    for level, patterns in _PATTERNS.items():
        for pattern in patterns:
            findings.extend(
                Finding(level, pattern, match.start(), match.end())
                for match in re.finditer(pattern, text)
            )
    level = max((finding.level for finding in findings), default=Sensitivity.PUBLIC)
    route = {
        Sensitivity.PUBLIC: "external_allowed",
        Sensitivity.INTERNAL: "local_preferred",
        Sensitivity.CONFIDENTIAL: "local_only",
        Sensitivity.SECRET: "block_external",
    }[level]
    redacted = text
    for finding in sorted(findings, key=lambda item: item.start, reverse=True):
        if finding.level >= Sensitivity.CONFIDENTIAL:
            redacted = redacted[: finding.start] + "[REDACTED]" + redacted[finding.end :]
    return Assessment(level, tuple(findings), route, redacted)
