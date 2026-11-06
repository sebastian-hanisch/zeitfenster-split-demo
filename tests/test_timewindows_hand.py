"""Handwerte der Zeitfenster-Bausteine an der Handinstanz `line` (siehe conftest.py): Zulässigkeit, Split, Bögen, Gründe, Füllen bis voll, Fahrplan, Zeitschlupf, exaktes Optimum."""

import pytest

import zfs_timewindows as T

ABS = 1e-9


def test_route_feasibility_by_hand(line):
    assert T.route_ok(line, (1, 2)) and T.route_ok(line, (2, 3)) and T.route_ok(line, (1, 3)) and T.route_ok(line, (3,))
    assert not T.route_ok(line, (2, 1))                       # Kunde 1 käme um 25 an, Fenster bis 20
    assert not T.route_ok(line, (1, 2, 3))                    # Last 12 über 8
    assert T.plan_ok(line, [(1,), (2, 3)]) and not T.plan_ok(line, [(1,), (2,)])   # Kunde 3 fehlt


def test_split_of_the_two_orders_by_hand(line):
    a = T.split_tw(line, (1, 2, 3))
    assert a.cost == pytest.approx(40.0, abs=ABS) and a.routes == ((1,), (2, 3)) and a.arcs == 5
    b = T.split_tw(line, (2, 1, 3))
    assert b.cost == pytest.approx(50.0, abs=ABS) and b.routes == ((2,), (1, 3)) and b.arcs == 4


def test_arc_counts_and_the_arcs_without_windows(line):
    free = T.without_windows(line)
    assert T.count_arcs(line, (1, 2, 3)) == 5 and T.count_arcs(free, (1, 2, 3)) == 5
    assert T.count_arcs(line, (2, 1, 3)) == 4 and T.count_arcs(free, (2, 1, 3)) == 5           # (2 1) fehlt wegen des Fensters von Kunde 1


def test_arc_table_gives_the_reason_of_every_missing_segment(line):
    rows = {(r["start"], r["end"]): r for r in T.arc_table(line, (2, 1, 3))}
    assert rows[(0, 2)]["reason"] == "window" and rows[(0, 2)]["culprit"] == 1 and not rows[(0, 2)]["ok"]
    assert rows[(0, 3)]["reason"] == "window" and rows[(0, 3)]["culprit"] == 1                   # folgt aus dem kürzeren Segment
    assert rows[(1, 3)]["ok"] and rows[(2, 3)]["ok"] and rows[(0, 1)]["ok"]
    full = {(r["start"], r["end"]): r for r in T.arc_table(line, (1, 2, 3))}
    assert full[(0, 3)]["reason"] == "load" and full[(0, 3)]["culprit"] == 3


def test_return_after_the_horizon_is_its_own_reason(line):
    tight = T.TW(line.inst, line.early, line.late, 50.0, 10.0)                              # (2 3) und (1 3) kehren erst um 55 zurück
    rows = {(r["start"], r["end"]): r for r in T.arc_table(tight, (1, 2, 3))}
    assert rows[(1, 3)]["reason"] == "return" and rows[(1, 3)]["culprit"] == 3 and rows[(2, 3)]["reason"] == "return"
    assert T.split_tw(tight, (1, 2, 3)) is None                                             # Kunde 3 allein kehrt um 55 zurück: nicht zerlegbar


def test_blocked_segments_name_the_arrival_against_the_window_end(line):
    rows = T.blocked_segments(line, (2, 1, 3))
    first = rows[0]
    assert first["longest"] == (2,) and first["blocked"]["reason"] == "window" and first["blocked"]["customer"] == 1
    assert first["blocked"]["arrival"] == pytest.approx(25.0) and first["blocked"]["late"] == 20.0
    assert rows[1]["longest"] == (1, 3) and rows[1]["blocked"] is None
    assert T.blocked_segments(line, (1, 2, 3))[0]["blocked"]["reason"] == "load"


def test_greedy_fill_with_windows_counts_routes(line):
    assert T.greedy_tw(line, (1, 2, 3)) == ((1, 2), (3,))              # (1 2 3) wegen der Last nicht; 3 allein
    assert T.greedy_tw(line, (2, 1, 3)) == ((2,), (1, 3))              # (2 1) wegen des Fensters nicht
    assert len(T.greedy_tw(line, (2, 1, 3))) == len(T.split_tw(line, (2, 1, 3), lexicographic=True).routes)


def test_lexicographic_split_takes_the_fewest_routes_then_the_shortest(line):
    lex = T.split_tw(line, (1, 2, 3), lexicographic=True)
    assert len(lex.routes) == 2 and lex.cost == pytest.approx(40.0)


def test_timeline_with_waiting_and_slack_by_hand(line):
    tl = T.timeline(line, (2, 3))
    assert [r["raw"] for r in tl.rows] == [10.0, 25.0] and [r["start"] for r in tl.rows] == [10.0, 30.0] and [r["wait"] for r in tl.rows] == [0.0, 5.0]
    assert tl.back == pytest.approx(55.0) and tl.wait == pytest.approx(5.0)
    assert tl.slack == pytest.approx(5.0)                              # min(H - Rückkehr = 5, 20 - 10 = 10, 5 + 40 - 30 = 15)
    assert tl.shift == pytest.approx(5.0) and tl.duration_early == pytest.approx(55.0) and tl.duration_late == pytest.approx(50.0)
    # spätes Losfahren zur Zeit 5 von Hand: Kunde 2 um 15, Kunde 3 um 30 (kein Warten), zurück um 55, Dauer 50
    assert T.timeline(line, (1, 2)).shift == 0.0 and T.timeline(line, (1, 2)).wait == 0.0


def test_duration_split_prefers_the_shorter_duration(line):
    cost, routes = T.split_duration(line, (1, 2, 3))
    # von Hand: (1) Dauer 20, (2 3) Dauer 50 bei spätem Losfahren (früh 55), (1 2) Dauer 40, (3) Dauer 50 (früh 55), (2) Dauer 30; beste Zerlegung (1) + (2 3) = 70
    assert routes == ((1,), (2, 3)) and cost == pytest.approx(70.0)
