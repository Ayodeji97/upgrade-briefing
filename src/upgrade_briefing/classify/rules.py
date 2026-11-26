"""Step 5a — rule-based classifier: keywords first, then the section title.

The cheapest method that is right wins (learning guide, Stage 7). Rules are free, instant and
explainable, so they are the baseline the LLM has to beat.

Each rule returns (label, confident). "confident" means a specific keyword fired. A guess from
the section title alone is not confident, and the hybrid classifier sends those to the LLM.
"""

from __future__ import annotations

import re

# Order matters: the first match wins, and the order follows LABELS' priority
# (breaking > deprecated > new > fix). Fixes are checked before "breaking" phrases like
# "no longer", because "Fixed X so it no longer crashes" is a fix, not a removal.
_FIX_START = re.compile(r"^\s*(fix(ed|es)?|resolved?)\b", re.I)

_BREAKING = re.compile(
    r"\b("
    r"breaking change|(has|have) (now )?been removed|(is|are|was|were) (now )?removed|removed the|"
    r"\bremoves?\b|renamed|now requires|minsdk|min sdk|changed (the )?signature|"
    r"now (throws?|fails?)|will (now )?(throw|fail)|no longer (take|accept|support|available|experimental)|"
    r"is now (a|an) (class|interface)|now (marked|annotated)|must now|instead of returning|"
    r"dropping support|is not supported anymore"
    r")",
    re.I,
)
_DEPRECATED = re.compile(r"\b(deprecate[ds]?|is deprecated|are deprecated|deprecating)\b", re.I)
_NEW = re.compile(
    r"^\s*(add(ed|s)?|introduc(e|ed|es)|new|provide|allow)\b|\bnow supports?\b|\bnew (api|method|class)|"
    r"\bnow available\b|\bsupport for\b",
    re.I,
)
_OTHER = re.compile(r"\bnow depends on\b|\bdepend(s)? on .* \d+\.\d+", re.I)

# Section-title fallback. Free text, so match on substrings.
_SECTION = [
    ("breaking", "breaking"),
    ("behavior", "breaking"),
    ("bug fix", "fix"),
    ("new feature", "new"),
    ("api change", "new"),
    ("dependency", "other"),
    ("known issue", "other"),
]


def classify(text: str, section: str = "") -> tuple[str, bool]:
    if _FIX_START.search(text):
        return "fix", True
    if _DEPRECATED.search(text) and not re.search(r"\bthe deprecated\b.*\bremoved\b", text, re.I):
        return "deprecated", True
    if _BREAKING.search(text):
        return "breaking", True
    if _OTHER.search(text):
        return "other", True
    if _NEW.search(text):
        return "new", True
    s = section.lower()
    for key, label in _SECTION:
        if key in s:
            return label, False
    return "other", False
