"""Vorberechnete Bänder (zfs_bands.json): Aufbau, Vollständigkeit, Stimmigkeit der Zeilen, Referenzdatei und frische Nachrechnung einzelner Zeilen (Stichprobe)."""

import json
from pathlib import Path

import pytest

import zfs_constants as C
import zfs_evaluation as ev
import zfs_timewindows as T

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / C.BAND_FILE).read_text(encoding="utf-8"))
REFS = json.loads((ROOT / C.REFS_FILE).read_text(encoding="utf-8"))["refs"]
ROWS = DATA["rows"]
PER_GROUP = {10: 80, 12: 32, 25: 32, 50: 32}


def test_every_group_is_there_with_the_right_number_of_instances():
    for n in C.BAND_SIZES:
        for mode in C.MODE_KEYS:
            for width in C.BAND_WIDTHS:
                rows = ev.band_rows(n, mode, width)
                assert len(rows) == PER_GROUP[n] == len(C.BAND_CELLS) * len(C.BAND_SEEDS[n]), (n, mode, width)
                assert {(r["family"], r["depot"]) for r in rows} == set(C.BAND_CELLS) and sorted({r["seed"] for r in rows}) == list(C.BAND_SEEDS[n])
    assert len(ROWS) == sum(PER_GROUP.values()) * len(C.MODE_KEYS) * len(C.BAND_WIDTHS) == 1760


def test_rows_have_all_fields_and_sane_values():
    for r in ROWS:
        assert set(r["cost"]) == set(C.ORDER_KEYS) == set(r["arcs"]) == set(r["greedy"])
        assert r["ref"] is not None and r["ref"] > 0 and r["k_ref"] >= 1
        for k in C.ORDER_KEYS:
            assert r["cost"][k] is not None, (r["n"], r["seed"], k)                       # in keiner Zelle ist eine Reihenfolge nicht zerlegbar
            a, free = r["arcs"][k]
            assert 1 <= a <= free
            assert a >= r["n"]                                                              # mindestens die Ein-Kunden-Bögen
        if r["width"] is None:
            assert all(r["arcs"][k][0] == r["arcs"][k][1] for k in C.ORDER_KEYS)             # ohne Fenster fehlt kein Bogen, den die Last erlaubt
        if r["n"] in C.EXACT_SIZES:
            assert r["labels"] >= 1.0 and r["states"] > 0 and r["max_labels"] >= 1
            assert all(r["cost"][k] >= r["ref"] - C.TOL for k in C.ORDER_KEYS)             # das exakte Optimum ist eine Untergrenze
        else:
            assert "labels" not in r


def test_the_reference_file_covers_every_large_instance_and_matches_the_rows():
    large = [r for r in ROWS if r["n"] not in C.EXACT_SIZES]
    assert len(large) == 640 and len(REFS) == 640
    for r in large:
        key = f"{r['n']}|{r['mode']}|{r['width']}|{r['family']}|{r['depot']}|{r['seed']}"
        assert REFS[key] == [r["ref"], r["k_ref"]]


@pytest.mark.parametrize("pick", [0, 77, 160, 301, 420, 555, 777, 900, 1111, 1200, 1300, 1400, 1250])
def test_a_fresh_recomputation_equals_the_stored_row(pick):
    r = ROWS[pick]
    if r["n"] == 50:
        pytest.skip("n = 50 rechnet je Zeile bis zu einer halben Minute; die Stichprobe deckt 10 bis 25 ab")
    fresh = ev.instance_row(r["n"], r["family"], r["depot"], r["seed"], r["width"], r["mode"], r["ref"] if r["n"] not in C.EXACT_SIZES else None, r["k_ref"] if r["n"] not in C.EXACT_SIZES else None)
    assert fresh["cost"] == pytest.approx(r["cost"]) and fresh["arcs"] == r["arcs"] and fresh["greedy"] == r["greedy"]
    assert fresh["ref"] == pytest.approx(r["ref"])


def test_the_stored_windows_come_from_the_documented_generation():
    # Stichprobe: die Fenster einer gespeicherten Instanz sind die der Erzeugung (Breite als Anteil von H, um die Ankunftszeiten des Bezugsplans)
    r = next(x for x in ROWS if x["n"] == 10 and x["mode"] == "geo" and x["width"] == 0.2)
    tw = T.make_tw(10, r["family"], r["depot"], C.BAND_ROUTES, r["seed"], C.BAND_FILL, 0.2, "geo")
    assert tw.horizon > 0 and all(tw.late[c] - tw.early[c] <= 0.2 * tw.horizon + 1e-9 for c in range(1, 11))
    assert T.plan_ok(tw, T.exact_tw(tw).routes)


def test_band_stats_counts_and_ordering():
    stats = ev.band_stats(ev.band_rows(25, "geo", 0.2))
    assert stats["count"] == 32 and stats["keys"] == list(C.ORDER_KEYS)
    assert all(stats["gaps"][k]["min"] <= stats["gaps"][k]["median"] <= stats["gaps"][k]["max"] for k in C.ORDER_KEYS)
    assert all(v["cheaper"] + v["equal"] + v["more"] == 32 for v in stats["vs"].values()) and C.COMPARE_KEY not in stats["vs"]
    assert ev.band_stats([]) == {}
    assert "labels" not in stats and "labels" in ev.band_stats(ev.band_rows(12, "geo", 0.2))


def test_duration_stats_only_for_ten_customers():
    assert ev.duration_stats(ev.band_rows(25, "geo", 0.2)) == {} and ev.duration_stats([]) == {}
    d = ev.duration_stats(ev.band_rows(10, "random", 0.2))
    assert d["count"] == 80 and d["shiftable"] <= d["routes"] and 0 <= d["changed"] <= 80
