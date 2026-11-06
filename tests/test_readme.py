"""README und App erzählen dasselbe: der Annahmentext der App steht wörtlich in der README, die Pflichtabschnitte sind da, keine Platzhalter."""

import re
from pathlib import Path

import zfs_constants as C

README = (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")


def test_the_assumptions_text_of_the_app_is_in_the_readme_verbatim():
    assert C.ASSUMPTIONS_MARKDOWN in README


def test_readme_has_the_required_sections_in_order():
    headings = re.findall(r"^## (.+)$", README, flags=re.M)
    wanted = ["Kernfrage", "Modell", "Methodik", "Befunde (gemessen, keine Behauptungen)", "Ehrliche Grenzen", "Befunde und Korrekturen gegenüber dem Plan",
              "Verifikation", "Tests", "Dateistruktur", "Bewusst nicht umgesetzt", "Lokal ausführen", "Tests ausführen"]
    positions = [headings.index(h) for h in wanted]
    assert positions == sorted(positions)


def test_readme_has_no_placeholders_left():
    assert "{TESTS}" not in README and "{ASSUMPTIONS}" not in README and "TODO:" not in README.replace("<!-- TODO nach dem Deploy", "")


def test_every_file_in_the_structure_table_exists():
    root = Path(__file__).resolve().parent.parent
    table = README.split("## Dateistruktur")[1].split("## Bewusst nicht umgesetzt")[0]
    for name in re.findall(r"^\| `([^`]+)` \|", table, flags=re.M):
        assert (root / name.rstrip("/")).exists(), name
