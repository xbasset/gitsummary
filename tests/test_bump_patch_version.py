from __future__ import annotations

from pathlib import Path

from scripts.bump_patch_version import bump_file


def test_bump_patch_version_updates_init_py(tmp_path: Path) -> None:
    path = tmp_path / "__init__.py"
    path.write_text('__version__ = "0.3.0"\n', encoding="utf-8")

    old, new = bump_file(path)

    assert old == "0.3.0"
    assert new == "0.3.1"
    assert path.read_text(encoding="utf-8") == '__version__ = "0.3.1"\n'


