"""GitHub Actions CI integration utilities.

This module provides utilities for improving log output when running in GitHub Actions,
including log grouping, annotations, and job summaries.
"""

import logging
import os
from contextlib import contextmanager
from pathlib import Path

log = logging.getLogger(__name__)


def is_github_actions() -> bool:
    """Check if we're running in a GitHub Actions environment."""
    return os.environ.get("GITHUB_ACTIONS") == "true"


@contextmanager
def log_group(title: str):
    """
    Context manager for GitHub Actions log grouping.

    Creates a collapsible group in the GitHub Actions log output.
    When not running in GitHub Actions, this is a no-op.

    Usage:
        with log_group("Running tests"):
            # verbose output here will be collapsed by default
            run_tests()
    """
    if is_github_actions():
        print(f"::group::{title}", flush=True)
    try:
        yield
    finally:
        if is_github_actions():
            print("::endgroup::", flush=True)


def annotation(
    level: str,
    message: str,
    file: str | Path | None = None,
    line: int | None = None,
    end_line: int | None = None,
    title: str | None = None,
):
    """
    Emit a GitHub Actions annotation.

    Annotations appear in the workflow summary and can be associated with
    specific files and line numbers.

    Args:
        level: One of "error", "warning", or "notice"
        message: The annotation message
        file: Optional file path to associate with the annotation
        line: Optional line number
        end_line: Optional end line number for multi-line annotations
        title: Optional title for the annotation
    """
    if not is_github_actions():
        return

    params = []
    if file:
        params.append(f"file={file}")
    if line is not None:
        params.append(f"line={line}")
    if end_line is not None:
        params.append(f"endLine={end_line}")
    if title:
        params.append(f"title={title}")

    param_str = ",".join(params)
    if param_str:
        print(f"::{level} {param_str}::{message}", flush=True)
    else:
        print(f"::{level}::{message}", flush=True)


def error(message: str, **kwargs):
    """Emit an error annotation."""
    annotation("error", message, **kwargs)


def warning(message: str, **kwargs):
    """Emit a warning annotation."""
    annotation("warning", message, **kwargs)


def notice(message: str, **kwargs):
    """Emit a notice annotation."""
    annotation("notice", message, **kwargs)


class GitHubActionsHandler(logging.Handler):
    """
    Logging handler that emits GitHub Actions annotations for warnings and errors.

    Add this handler to automatically convert Python logging warnings and errors
    into GitHub Actions annotations that appear in the workflow summary.

    Usage:
        if ci.is_github_actions():
            logging.getLogger().addHandler(ci.GitHubActionsHandler())
    """

    def emit(self, record: logging.LogRecord):
        if not is_github_actions():
            return

        message = record.getMessage()
        title = record.name

        if record.levelno >= logging.ERROR:
            error(message, title=title)
        elif record.levelno >= logging.WARNING:
            warning(message, title=title)


class JobSummary:
    """
    Helper for writing GitHub Actions job summaries.

    Job summaries appear as rich markdown in the workflow run summary page.

    Usage:
        summary = JobSummary()
        summary.add_heading("Test Results", level=2)
        summary.add_table(
            headers=["Test", "Status"],
            rows=[["Test1", "✅"], ["Test2", "❌"]]
        )
        summary.write()
    """

    def __init__(self):
        self._content: list[str] = []

    def add_raw(self, content: str):
        """Add raw markdown content."""
        self._content.append(content)

    def add_heading(self, text: str, level: int = 2):
        """Add a markdown heading."""
        self._content.append(f"{'#' * level} {text}\n")

    def add_paragraph(self, text: str):
        """Add a paragraph of text."""
        self._content.append(f"{text}\n")

    def add_table(self, headers: list[str], rows: list[list[str]]):
        """Add a markdown table."""
        # Header row
        self._content.append("| " + " | ".join(headers) + " |")
        # Separator row
        self._content.append("| " + " | ".join(["---"] * len(headers)) + " |")
        # Data rows
        for row in rows:
            self._content.append("| " + " | ".join(str(cell) for cell in row) + " |")
        self._content.append("")  # Empty line after table

    def add_collapsible(self, summary: str, details: str):
        """Add a collapsible details section."""
        self._content.append(f"<details><summary>{summary}</summary>\n")
        self._content.append(details)
        self._content.append("</details>\n")

    def add_code_block(self, code: str, language: str = ""):
        """Add a fenced code block."""
        self._content.append(f"```{language}")
        self._content.append(code)
        self._content.append("```\n")

    def write(self):
        """Write the summary to the GitHub Actions job summary file."""
        summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
        if not summary_file:
            log.debug("GITHUB_STEP_SUMMARY not set, skipping job summary")
            return

        with open(summary_file, "a") as f:
            f.write("\n".join(self._content))
            f.write("\n")

    def __str__(self) -> str:
        return "\n".join(self._content)
