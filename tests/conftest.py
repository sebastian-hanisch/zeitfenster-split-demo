"""Gemeinsame Fixtures: die Handinstanz mit Zeitfenstern, an der jede Einheit von Hand geprüft wird (DEMO-PLAYBOOK §1b)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zfs_scenario import Instance  # noqa: E402
from zfs_timewindows import TW  # noqa: E402


@pytest.fixture
def line():
    """Handinstanz auf einer Geraden: Depot (0,0), Kunden 1 (5,0), 2 (10,0), 3 (15,0), Nachfrage je 4, Kapazität 8 (höchstens zwei je Route), Bedienzeit 10, H = 60.
    Fenster: Kunde 1 [0, 20], Kunde 2 [0, 20], Kunde 3 [30, 40].

    Von Hand (Entfernungen 5, 10, 15; d12 = d23 = 5, d13 = 10):
    - Route (1 2): Beginn 5, 20, Rückkehr 40, Länge 20. Route (2 1): Kunde 1 käme um 25 an, Fenster bis 20: unzulässig.
    - Route (2 3): Beginn 10, dann Ankunft 25, Warten bis 30, Rückkehr 55, Länge 30. Route (1 3): Beginn 5, Ankunft 25, Warten bis 30, Rückkehr 55, Länge 30.
    - Einzelrouten (1): 10, (2): 20, (3): 30 (Ankunft 15, Warten bis 30, Rückkehr 55).
    - Reihenfolge 1 2 3: Bögen (1), (1 2), (2), (2 3), (3) = 5; Split (1) + (2 3) = 40 (die Alternativen (1 2) + (3) = 50 und alles allein = 60).
    - Reihenfolge 2 1 3: Bögen (2), (1), (1 3), (3) = 4 von 5; Split (2) + (1 3) = 50. Optimum über alle Reihenfolgen: 40."""
    inst = Instance(((0.0, 0.0), (5.0, 0.0), (10.0, 0.0), (15.0, 0.0)), (4, 4, 4), 8)
    return TW(inst, (0.0, 0.0, 0.0, 30.0), (60.0, 20.0, 20.0, 40.0), 60.0, 10.0)
