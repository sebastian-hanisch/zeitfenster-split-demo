"""Jede Zahl der README und der Preset-Hilfen wird aus den Bändern beziehungsweise der Rechnung nachgerechnet und muss im Text stehen (DEMO-PLAYBOOK §1b)."""

from functools import lru_cache
from pathlib import Path

import pytest

import zfs_algorithm as A
import zfs_constants as C
import zfs_evaluation as ev
import zfs_timewindows as T

README = (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
W = C.BAND_WIDTHS
W4 = C.BAND_WIDTHS[:4]


@lru_cache(maxsize=None)
def stat(n, mode, width):
    return ev.band_stats(ev.band_rows(n, mode, width))


def fmt(x, digits=1):
    return ev.de(x, digits)


def line(values, digits=1, sep=" / "):
    return sep.join(fmt(v, digits) for v in values)


def gaps(n, mode, key, widths=W):
    return [round(stat(n, mode, w)["gaps"][key]["median"], 1) for w in widths]


def shares(n, mode, key, widths=W4):
    return [round(stat(n, mode, w)["shares"][key]) for w in widths]


def check(values, expected, digits=1):
    assert list(values) == pytest.approx(list(expected), abs=0.051 if digits else 0.5), (list(values), list(expected))
    assert line(expected, digits) in README, line(expected, digits)


# --- Hilfsgraph schrumpft ---------------------------------------------------------------------------------------------------------------

def test_arc_shares_of_the_tour_and_of_insertion():
    check(shares(50, "geo", "tour"), (19, 25, 34, 53), 0)
    check(shares(25, "geo", "tour"), (29, 33, 46, 66), 0)
    check(shares(50, "random", "tour"), (12, 14, 18, 31), 0)
    check(shares(50, "geo", "es"), (59, 57, 56, 60), 0)
    check(shares(50, "random", "es"), (51, 55, 57, 61), 0)
    assert min(min(shares(n, m, "es")) for n in (25, 50) for m in C.MODE_KEYS) == 51 and max(max(shares(n, m, "es")) for n in (25, 50) for m in C.MODE_KEYS) == 72
    assert min(shares(50, "geo", "es") + shares(50, "random", "es")) == 51 and max(shares(50, "geo", "es") + shares(50, "random", "es")) == 61
    assert all(sum(stat(n, m, w)["undecomposable"].values()) == 0 for n in C.BAND_SIZES for m in C.MODE_KEYS for w in W)       # nie nicht zerlegbar


def test_the_shortest_tour_as_giant_tour():
    check(gaps(10, "geo", "tour"), (46.8, 43.5, 24.3, 12.2, 2.4))
    check(gaps(12, "geo", "tour"), (68.9, 51.6, 25.4, 15.0, 1.9))
    check(gaps(12, "random", "tour"), (38.5, 44.1, 30.1, 18.2, 1.9))
    check(gaps(25, "geo", "tour"), (183.7, 122.6, 70.2, 28.6, 6.0))
    check(gaps(25, "random", "tour"), (103.9, 94.8, 71.5, 37.4, 6.0))
    check(gaps(50, "geo", "tour"), (225.6, 144.2, 83.8, 37.4, 7.7))
    check(gaps(50, "random", "tour"), (167.5, 167.1, 141.1, 74.5, 7.9))
    assert [stat(25, "geo", w)["greedy"]["tour"] for w in W] == [13, 9.5, 7, 5, 3] and all(stat(25, "geo", w)["k_ref"] == 3 for w in W)
    assert "13 / 9,5 / 7 / 5 / 3 Routen" in README


def test_other_orders_do_not_help():
    check(gaps(25, "geo", "late"), (299.2, 244.3, 203.3, 180.5, 143.1))
    check(gaps(25, "geo", "angle"), (212.6, 171.5, 110.5, 77.1, 32.6))
    check(gaps(25, "geo", "random"), (261.6, 253.9, 218.7, 184.3, 145.5))


def test_insertion_after_split_with_windows():
    check(gaps(10, "geo", "es"), (0.0, 0.0, 0.6, 1.2, 0.0))
    check(gaps(12, "random", "es"), (2.5, 2.4, 2.4, 2.1, 1.0))
    check(gaps(25, "geo", "es"), (0.0, 0.5, 4.9, 7.7, 3.3))
    check(gaps(25, "random", "es"), (8.7, 14.9, 9.9, 7.2, 3.3))
    check(gaps(50, "geo", "es"), (0.2, 9.7, 17.1, 18.8, 8.3))
    check(gaps(50, "random", "es"), (17.1, 20.8, 20.1, 14.3, 8.3))
    paired = [tuple(stat(25, "geo", w)["vs"]["es"][k] for k in ("cheaper", "equal", "more")) for w in W]
    assert paired == [(32, 0, 0), (32, 0, 0), (31, 0, 1), (29, 0, 3), (21, 0, 11)]
    for p in ("32 / 0 / 0, 32 / 0 / 0, 31 / 0 / 1, 29 / 0 / 3", "21 / 0 / 11", "13 / 0 / 19", "25 / 0 / 7"):
        assert p in README
    paired50 = [tuple(stat(50, "geo", w)["vs"]["es"][k] for k in ("cheaper", "equal", "more")) for w in W]
    assert paired50 == [(32, 0, 0), (32, 0, 0), (32, 0, 0), (25, 0, 7), (13, 0, 19)]


def test_the_reference_is_not_a_lower_bound():
    assert [stat(25, "geo", w)["under"]["es"] for w in W4] == [7, 3, 1, 0] and stat(25, "geo", None)["under"]["es"] == 1
    assert [stat(25, "random", w)["under"]["es"] for w in W4] == [1, 0, 0, 0]
    assert [stat(50, "geo", w)["under"]["es"] for w in W4] == [3, 0, 0, 0] and stat(50, "geo", None)["under"]["es"] == 1 and stat(50, "geo", None)["under"]["tour"] == 1
    assert "7 / 3 / 1 / 0 von 32" in README and "3 / 0 / 0 / 0" in README


def test_labels_in_the_exact_solver():
    meds = [stat(n, m, w)["labels"]["median"] for n in (10, 12) for m in C.MODE_KEYS for w in W]
    assert round(min(meds), 2) == 1.00 and round(max(meds), 2) == 1.12
    assert all(stat(n, m, None)["labels"]["median"] == 1.0 and stat(n, m, None)["labels"]["max_single"] == 1 for n in (10, 12) for m in C.MODE_KEYS)
    assert round(max(stat(n, m, w)["labels"]["max"] for n in (10, 12) for m in C.MODE_KEYS for w in W), 2) == 1.54
    assert max(stat(n, m, w)["labels"]["max_single"] for n in (10, 12) for m in C.MODE_KEYS for w in W) == 6
    for text in ("1,00 bis 1,12", "1,54 (n = 12, zufällig, 40 %)", "einem einzelnen Zustand 6"):
        assert text in README


def test_waiting_and_late_departure():
    rand = [ev.duration_stats(ev.band_rows(10, "random", w)) for w in W4]
    geo = [ev.duration_stats(ev.band_rows(10, "geo", w)) for w in W4]
    check([d["wait_share"] for d in rand], (20.8, 20.5, 16.7, 10.5))
    check([d["saving_median"] for d in rand], (4.9, 6.8, 10.1, 10.4))
    assert [d["shiftable"] for d in rand] == [224, 204, 171, 123] and [d["changed"] for d in rand] == [30, 24, 12, 3] and rand[0]["count"] == 80
    assert [d["changed"] for d in geo] == [1, 2, 5, 2] and all(d["wait_share"] == 0.0 and d["saving_median"] == 0.0 for d in geo)
    assert all(d["dur_gain"] == 0.0 for d in rand + geo)
    for text in ("224 / 204 / 171 / 123", "30 / 24 / 12 / 3 von 80", "1 / 2 / 5 / 2 von 80"):
        assert text in README
    free = ev.duration_stats(ev.band_rows(10, "random", None))
    assert free["shiftable"] == 0 and free["changed"] == 0


# --- Handinstanz und Presets -------------------------------------------------------------------------------------------------------------

def _preset(name):
    p = C.PRESETS[name]
    return ev.analyse(ev.Settings(p["n"], p["family"], p["depot"], p["routes"], p["fill"], p["seed"], p["width"], p["mode"], p["round"] == 0))


def _help(name):
    return C.PRESET_HELP[name]


def test_hand_preset():
    name = "Die Richtung zählt (n = 6, Handrechnung)"
    a = _preset(name)
    h = _help(name)
    assert a.tw.horizon == 97 and a.tw.inst.capacity == 11 and a.orders["tour"] == (1, 6, 5, 4, 3, 2)
    assert a.splits["tour"].cost == pytest.approx(67.99, abs=0.005) and a.splits["tour"].routes == ((1, 6, 5), (4,), (3, 2)) and a.arcs["tour"] == (10, 15)
    assert a.exact.cost == pytest.approx(53.79, abs=0.005) and a.exact.routes == ((1, 6, 5), (3, 4, 2))
    assert a.splits["tour_rev"].cost == pytest.approx(61.16, abs=0.005) and a.splits["es"].cost == pytest.approx(53.79, abs=0.005) and a.orders["es"] == (3, 4, 2, 1, 6, 5)
    assert ev.split_gap(a, "tour") == pytest.approx(26.4, abs=0.05)
    blocked = T.blocked_segments(a.tw, a.orders["tour"])[3]                                                    # Beginn bei Kunde 4
    assert blocked["longest"] == (4,) and blocked["blocked"]["customer"] == 3 and blocked["blocked"]["arrival"] == pytest.approx(24.63, abs=0.005) and blocked["blocked"]["late"] == 24
    assert A.tsp_tour(a.tw.inst)[0] == pytest.approx(47.41, abs=0.005)
    for text in ("24,63", "um 24", "67,99", "26,4 %", "(1 6 5), (4), (3 2)", "53,79", "(3 4 2)", "61,16"):
        assert text in h, text
    for text in ("24,63", "67,99", "53,79", "61,16", "47,41", "3 4 2 1 6 5", "10 von 15", "H = 97", "Kapazität 11"):
        assert text in README, text


def test_narrow_windows_preset():
    name = "Enge Fenster: die Rundreise versagt (n = 8, Depot in der Ecke)"
    a, h = _preset(name), _help(name)
    assert a.exact.cost == pytest.approx(412.35, abs=0.005) and len(a.exact.routes) == 3
    assert a.splits["tour"].cost == pytest.approx(933.73, abs=0.005) and len(a.splits["tour"].routes) == 7 and a.arcs["tour"] == (9, 18) and ev.split_gap(a, "tour") == pytest.approx(126.4, abs=0.05)
    assert a.splits["tour_rev"].cost == pytest.approx(517.11, abs=0.005) and ev.split_gap(a, "tour_rev") == pytest.approx(25.4, abs=0.05)
    assert a.splits["es"].cost == pytest.approx(412.35, abs=0.005) and a.arcs["es"] == (16, 21)
    for text in ("412,35", "933,73", "126,4 %", "7 Routen", "9 von 18", "517,11", "25,4 %", "16 von 21"):
        assert text in h, text


def test_no_windows_preset():
    name = "Ohne Fenster: der Split aus Stück 3 (n = 8, Depot in der Ecke)"
    a, h = _preset(name), _help(name)
    assert a.arcs["tour"] == (18, 18) and ev.split_gap(a, "tour") == pytest.approx(17.1, abs=0.05) and len(a.splits["tour"].routes) == 4 and a.exact.cost == pytest.approx(412.35, abs=0.005)
    assert a.splits["es"].cost == pytest.approx(412.35, abs=0.005) and a.splits["tour"].cost == pytest.approx(a.splits["tour_rev"].cost)
    for text in ("alle 18 Bögen", "17,1 %", "412,35", "4 Routen"):
        assert text in h, text


def test_labels_preset():
    name = "Mehrere Etiketten je Zustand (n = 12)"
    a, h = _preset(name), _help(name)
    assert a.exact.mean_labels == pytest.approx(1.54, abs=0.005) and a.exact.max_labels == 5
    assert a.exact.cost == pytest.approx(344.48, abs=0.005) and len(a.exact.routes) == 3 and ev.split_gap(a, "tour") == pytest.approx(57.1, abs=0.05) and ev.split_gap(a, "es") == 0.0
    for text in ("1,54 Etiketten", "höchstens 5", "344,48", "3 Routen", "57,1 %"):
        assert text in h, text


def test_late_departure_preset():
    name = "Spätes Losfahren ändert den Plan (n = 10)"
    a, h = _preset(name), _help(name)
    v = ev.duration_view(a, "es")
    assert v["routes"] == 4 and v["wait"] == pytest.approx(216.38, abs=0.005) and v["early"] == pytest.approx(734.38, abs=0.005) and v["late"] == pytest.approx(586.44, abs=0.005)
    assert 100 * (v["early"] - v["late"]) / v["early"] == pytest.approx(20.1, abs=0.05) and len(v["dur_routes"]) == 5 and not v["same_plan"]
    assert v["dur_cost"] == pytest.approx(576.90, abs=0.005) and v["dur_length"] == pytest.approx(463.27, abs=0.005) and v["length"] == pytest.approx(418.00, abs=0.005)
    for text in ("4 Routen", "216,38", "734,38", "20,1 %", "586,44", "5 Routen", "576,90", "463,27", "418,00"):
        assert text in h, text
