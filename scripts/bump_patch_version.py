"""Bump the patch version in `gitsummary/__init__.py`.

This is intended for CI automation on merges to `main`.
It does NOT create tags or GitHub Releases.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SemVer:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> "SemVer":
        m = re.match(r"^(?P<maj>\d+)\.(?P<min>\d+)\.(?P<pat>\d+)$", value.strip())
        if not m:
            raise ValueError(f"Invalid SemVer (expected X.Y.Z): {value!r}")
        return cls(int(m.group("maj")), int(m.group("min")), int(m.group("pat")))

    def bump_patch(self) -> "SemVer":
        return SemVer(self.major, self.minor, self.patch + 1)

    def to_string(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


VERSION_LINE_RE = re.compile(
    r'^(?P<prefix>[ \t]*__version__[ \t]*=[ \t]*")(?P<ver>\d+\.\d+\.\d+)(?P<suffix>")[ \t]*$',
    flags=re.MULTILINE,
)


def bump_file(path: Path) -> tuple[str, str]:
    """Return (old_version, new_version) after bumping patch in file content."""
    content = path.read_text(encoding="utf-8")
    matches = list(VERSION_LINE_RE.finditer(content))
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one __version__ assignment in {path}, found {len(matches)}."
        )

    m = matches[0]
    old = SemVer.parse(m.group("ver"))
    new = old.bump_patch()
    updated = (
        content[: m.start()]
        + f'{m.group("prefix")}{new.to_string()}{m.group("suffix")}'
        + content[m.end() :]
    )
    path.write_text(updated, encoding="utf-8")
    return old.to_string(), new.to_string()


def main(argv: list[str]) -> int:
    target = Path(argv[1]) if len(argv) > 1 else Path("gitsummary/__init__.py")
    old, new = bump_file(target)
    print(f"old_version={old}")
    print(f"new_version={new}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))


