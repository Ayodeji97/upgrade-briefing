"""Version parsing for AndroidX versions like "2.7.0", "2.8.0-alpha01" or "2.7.0-rc03".

Why this exists: the core RAG trick in this project is *metadata filtering*. To answer
"what changed between 2.6.1 and 2.7.0?", we keep only the release-note entries whose
version is in the range (2.6.1, 2.7.0]. Strings don't sort correctly ("2.10.0" < "2.9.0"
as text), so each version gets an integer `version_key` that sorts the right way and can
be stored in Weaviate and filtered with plain `>` / `<=`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Pre-release channels in release order. A stable release comes after all its pre-releases.
CHANNEL_RANK = {"alpha": 1, "beta": 2, "rc": 3, "stable": 4}

_VERSION_RE = re.compile(
    r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:-(?P<channel>alpha|beta|rc)(?P<num>\d+))?$"
)


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int
    patch: int
    channel_rank: int  # 1=alpha, 2=beta, 3=rc, 4=stable
    pre_num: int  # e.g. 3 for "rc03"; 0 for stable

    @property
    def channel(self) -> str:
        return next(k for k, v in CHANNEL_RANK.items() if v == self.channel_rank)

    @property
    def is_stable(self) -> bool:
        return self.channel_rank == CHANNEL_RANK["stable"]

    @property
    def key(self) -> int:
        """One sortable integer, e.g. 2.7.0-rc03 -> 2_007_000_303.

        Layout: major | minor (3 digits) | patch (3 digits) | channel (1 digit) | pre_num (2 digits).
        """
        return (
            self.major * 1_000_000_000
            + self.minor * 1_000_000
            + self.patch * 1_000
            + self.channel_rank * 100
            + self.pre_num
        )

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        return base if self.is_stable else f"{base}-{self.channel}{self.pre_num:02d}"


def parse_version(text: str) -> Version:
    """Parse "2.7.0-rc03" into a Version. Raises ValueError for anything else."""
    m = _VERSION_RE.match(text.strip())
    if not m:
        raise ValueError(f"Not an AndroidX version: {text!r}")
    channel = m.group("channel") or "stable"
    return Version(
        major=int(m.group("major")),
        minor=int(m.group("minor")),
        patch=int(m.group("patch")),
        channel_rank=CHANNEL_RANK[channel],
        pre_num=int(m.group("num") or 0),
    )


def is_version(text: str) -> bool:
    return _VERSION_RE.match(text.strip()) is not None
