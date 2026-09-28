"""RG-08: banned-terms linter (tools/banned_terms.py) catches EN + IT terms; CI fails on them."""

import subprocess
import sys
from pathlib import Path

import banned_terms  # tools/ is on pytest's pythonpath
import pytest

TOOL = Path(banned_terms.__file__)


@pytest.mark.parametrize(
    ("text", "lang", "term"),
    [
        ("Guaranteed returns every week", "en", "guaranteed"),
        ("This one is a lock", "en", "lock"),
        ("A risk-free pick", "en", "risk-free"),
        ("Today's sure bet", "en", "sure bet"),
        ("You can't lose with this", "en", "can't lose"),
        ("You can’t lose with this", "en", "can't lose"),  # noqa: RUF001 - curly quote on purpose
        ("Free money on the draw", "en", "free money"),
        ("Our banker of the day", "en", "banker"),
        ("A certain winner", "en", "certain"),
        ("Easy profit from odds", "en", "easy profit"),
        ("Rendimento garantito ogni settimana", "it", "guaranteed"),
        ("Vincita GARANTITA", "it", "guaranteed"),
        ("Scommessa sicura di oggi", "it", "sure bet"),
        ("Giocata senza rischi", "it", "risk-free"),
        ("Non puoi perdere", "it", "can't lose"),
        ("Soldi facili con le quote", "it", "easy profit"),
        ("Il fisso del giorno", "it", "banker"),
        ("Vittoria certa", "it", "certain"),
    ],
)
def test_rg08_catches_banned_terms(text: str, lang: str, term: str) -> None:
    findings = banned_terms.scan_text(text, "ui.json")
    assert (lang, term) in {(f.lang, f.term) for f in findings}


@pytest.mark.parametrize(
    "text",
    [
        "Estimated EV with uncertainty interval",
        "Model probability vs benchmark (observed odds)",
        "Blocked by your limit",
        "Probabilità stimata dal modello; incertezza al 90%",
        "Nessuna opportunità qualificata al momento",
        "Unlocked settings",
    ],
)
def test_rg08_allows_neutral_copy(text: str) -> None:
    assert banned_terms.scan_text(text) == []


def test_rg08_allow_pragma_requires_reason() -> None:
    assert banned_terms.scan_text("lock  // banned-terms-allow: keyboard Caps Lock label") == []
    assert banned_terms.scan_text("lock  // banned-terms-allow:") != []


def test_rg08_python_scans_string_literals_not_code_or_docstrings() -> None:
    source = '''"""Docs may quote the rule: never say guaranteed."""
import threading
_lock = threading.Lock()
MESSAGE = "Rendimento garantito"
'''
    findings = banned_terms.scan_python(source, "copy.py")
    assert [(f.line, f.lang, f.term) for f in findings] == [(4, "it", "guaranteed")]


def test_rg08_cli_fails_on_banned_terms(tmp_path: Path) -> None:
    bad = tmp_path / "en.json"
    bad.write_text('{"cta": "Guaranteed winners"}\n', encoding="utf-8")
    bad_it = tmp_path / "it.json"
    bad_it.write_text('{"cta": "Vincita garantita"}\n', encoding="utf-8")
    good = tmp_path / "ok.json"
    good.write_text('{"cta": "Estimated EV"}\n', encoding="utf-8")

    fail = subprocess.run(
        [sys.executable, str(TOOL), str(bad), str(bad_it)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert fail.returncode == 1
    assert '"Guaranteed"' in fail.stdout
    assert '"garantita"' in fail.stdout

    ok = subprocess.run(
        [sys.executable, str(TOOL), str(good)], capture_output=True, text=True, check=False
    )
    assert ok.returncode == 0, ok.stdout


def test_rg08_repository_is_clean() -> None:
    result = subprocess.run(
        [sys.executable, str(TOOL)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout
