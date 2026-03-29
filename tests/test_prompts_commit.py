"""Tests for commit prompt budgeting and skip classification."""

from __future__ import annotations

import pytest

from gitsummary.llm.base import SkippableLLMError
from gitsummary.llm.prompts_commit import build_commit_analysis_prompt


def test_notebook_diff_is_skipped(simple_commit) -> None:
    diff = """diff --git a/notebook.ipynb b/notebook.ipynb
index 1111111..2222222 100644
--- a/notebook.ipynb
+++ b/notebook.ipynb
@@ -1 +1 @@
-{"cells":[]}
+{"cells":["huge"]}
"""
    with pytest.raises(SkippableLLMError) as exc_info:
        build_commit_analysis_prompt(simple_commit, diff)

    assert exc_info.value.reason == "notebook_diff"


def test_binary_diff_is_skipped(simple_commit) -> None:
    diff = """diff --git a/image.png b/image.png
index 1111111..2222222 100644
Binary files a/image.png and b/image.png differ
"""
    with pytest.raises(SkippableLLMError) as exc_info:
        build_commit_analysis_prompt(simple_commit, diff)

    assert exc_info.value.reason == "binary_diff"


def test_long_source_lines_are_trimmed(simple_commit) -> None:
    diff = (
        "diff --git a/src/app.py b/src/app.py\n"
        "index 1111111..2222222 100644\n"
        "--- a/src/app.py\n"
        "+++ b/src/app.py\n"
        "@@ -1 +1 @@\n"
        "+"
        + ("x" * 10_000)
        + "\n"
    )

    prompt = build_commit_analysis_prompt(simple_commit, diff)

    assert "line truncated" in prompt
    assert len(prompt.encode("utf-8")) < 200_000
