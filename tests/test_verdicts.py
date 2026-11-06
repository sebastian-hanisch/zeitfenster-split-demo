"""Verdikte sind reine Funktionen: jede Zahl im Text stammt aus der Rechnung, Art und Wortlaut folgen den Schwellen."""

import pytest

import zfs_constants as C
import zfs_evaluation as ev

HAND = ev.Settings(6, 0, 0, 2, 90, 0, 3, 0, True)            # Voreinstellung = Handinstanz
NO_WINDOWS = ev.Settings(6, 0, 0, 2, 90, 0, len(C.LIVE_WIDTHS) - 1, 0, True)


def test_formats():
    assert ev.de(3.14159) == "3,14" and ev.pct(12.345) == "12,3 %" and ev.signed_pct(-0.04) == "0,0 %" and ev.signed_pct(2.5) == "+2,5 %" and ev.signed_pct(-2.5) == "−2,5 %"
    assert ev.routes_word(1) == "1 Route" and ev.routes_word(3) == "3 Routen" and ev.instances_word(1) == "1 Instanz"
    assert ev.gap_percent(10.0, 10.0) == 0.0 and ev.gap_percent(9.0, 10.0) == 0.0 and ev.gap_percent(11.0, 10.0) == pytest.approx(10.0)
    assert ev.diff_percent(11.0, 10.0) == pytest.approx(10.0) and ev.share_percent((5, 20)) == 25.0 and ev.share_percent((0, 0)) == 0.0
    assert ev.width_text(None) == "keine Fenster" and ev.width_text(0.2) == "Breite 20 %"


def test_compare_verdict_with_windows_warns_and_names_the_numbers():
    kind, text = ev.verdict_compare(ev.analyse(HAND))
    assert kind == "warning"
    assert "Breite 30 %" in text and "Optimum 53,79 mit 2 Routen" in text and "10 von 15 Bögen (67 %)" in text and "67,99 (26,4 % über dem Optimum)" in text and "53,79 (0,0 % über dem Optimum)" in text


def test_compare_verdict_without_windows_is_information():
    kind, text = ev.verdict_compare(ev.analyse(NO_WINDOWS))
    assert kind == "info" and text.startswith("Keine Fenster, Optimum") and "alle 15 Bögen" in text


def test_split_verdict_levels():
    a = ev.analyse(HAND)
    kind, text = ev.verdict_split(a, "tour", ev.order_view(a, "tour"), False)
    assert kind == "warning" and "10 von 15 Bögen zulässig (67 %)" in text and "3 Routen" in text
    kind, text = ev.verdict_split(a, "es", ev.order_view(a, "es"), True)
    assert kind == "success" and "Lexikographisch" in text and "0,0 % über dem Optimum" in text


def test_split_verdict_warns_when_the_windows_are_too_tight_for_the_order():
    a = ev.analyse(ev.Settings(8, 1, 1, 3, 90, 23, 1, 1, False))                # Fenster 10 %, geografisch: die Rundreise behält 9 von 18 Bögen
    kind, text = ev.verdict_split(a, "tour", ev.order_view(a, "tour"), False)
    assert kind == "warning" and "9 von 18 Bögen" in text
    # eine Reihenfolge mit weniger als 30 % der Bögen bekommt den Zusatz (künstlich über die Schwelle prüfen)
    view = ev.order_view(a, "tour")
    a2 = ev.Analysis(a.settings, a.tw, a.exact, a.orders, a.splits, {**a.arcs, "tour": (3, 18)}, a.greedy)
    assert "zu eng" in ev.verdict_split(a2, "tour", view, False)[1]


def test_split_verdict_for_an_undecomposable_order():
    tw_a = ev.analyse(HAND)
    broken = ev.Analysis(tw_a.settings, tw_a.tw, tw_a.exact, tw_a.orders, {**tw_a.splits, "late": None}, tw_a.arcs, tw_a.greedy)
    view = {"split": None, "order": broken.orders["late"], "table": [], "path": [], "timelines": []}
    kind, text = ev.verdict_split(broken, "late", view, False)
    assert kind == "error" and "nicht zerlegbar" in text


def test_shrink_and_label_verdicts():
    rows = ev.width_sweep(HAND)
    assert [r["label"] for r in rows] == list(C.WIDTH_LABELS) and rows[-1]["orders"]["tour"]["share"] == 100.0
    kind, text = ev.verdict_shrink(rows)
    assert "Anteil zulässiger Bögen der kürzesten Rundreise" in text and kind in ("info", "warning")
    kind, text = ev.verdict_labels(rows)
    assert kind == "info" and "Pareto-Etiketten" in text and "(ohne Fenster 1,00)" in text


def test_direction_verdict_compares_forward_and_backward():
    a = ev.analyse(HAND)
    rows = [{"key": k, "split": a.splits[k]} for k in ("tour", "tour_rev", "es")]
    kind, text = ev.verdict_directions(a, rows)
    assert kind == "warning" and "vorwärts den Split 67,99, rückwärts 61,16" in text and "rückwärts billiger" in text and "Länge 47,41" in text


def test_duration_verdict_reports_waiting_and_the_duration_split():
    a = ev.analyse(HAND)
    kind, text = ev.verdict_duration(ev.duration_view(a, "tour"), "Kürzeste Rundreise")
    assert kind == "info" and "Wartezeit 33,13 von 161,12" in text and "129,99" in text and "derselbe Plan" in text
    assert ev.verdict_duration({}, "x")[0] == "error"


def test_band_verdicts_without_data_and_with_data():
    assert ev.verdict_bands(25, "geo", 0.1, {})[0] == "warning"
    stats = ev.band_stats(ev.band_rows(25, "geo", 0.1))
    kind, text = ev.verdict_bands(25, "geo", 0.1, stats)
    assert "32 Instanzen" in text and "Die Referenz ist keine bewiesene Untergrenze" in text and kind == "warning"
    assert ev.verdict_bands(10, "geo", 0.1, ev.band_stats(ev.band_rows(10, "geo", 0.1)))[1].count("keine bewiesene Untergrenze") == 0
    assert ev.verdict_band_labels(ev.band_stats(ev.band_rows(12, "random", 0.4)))[1].startswith("Pareto-Etiketten je Zustand")
    assert ev.verdict_band_labels(stats)[1] == ""
    assert "Unter der Referenz liegen" in ev.verdict_under(ev.band_stats(ev.band_rows(25, "geo", 0.05)))[1]
