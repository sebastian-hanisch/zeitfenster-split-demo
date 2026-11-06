"""Randfälle: n = 1 und 2, Kunde auf dem Depot mit Fenster [0, 0], Rückkehr genau bei H, nicht zerlegbare Reihenfolgen, Bedienzeit 0, Warten über die ganze Route."""

import pytest

import zfs_timewindows as T
from zfs_scenario import Instance


def _tw(xy, demand, capacity, early, late, horizon, service=10.0):
    return T.TW(Instance(tuple(xy), tuple(demand), capacity), tuple(early), tuple(late), horizon, service)


def test_one_customer():
    tw = _tw(((0.0, 0.0), (5.0, 0.0)), (3,), 5, (0.0, 0.0), (100.0, 100.0), 100.0)
    res = T.split_tw(tw, (1,))
    assert res.cost == pytest.approx(10.0) and res.routes == ((1,),) and res.arcs == 1
    assert T.exact_tw(tw).routes == ((1,),) and T.exact_tw(tw).cost == pytest.approx(10.0)


def test_two_customers_one_vehicle_each_when_the_capacity_is_tight():
    tw = _tw(((0.0, 0.0), (5.0, 0.0), (0.0, 5.0)), (3, 3), 5, (0.0,) * 3, (100.0,) * 3, 100.0)
    assert T.split_tw(tw, (1, 2)).routes == ((1,), (2,)) and T.count_arcs(tw, (1, 2)) == 2
    assert len(T.greedy_tw(tw, (1, 2))) == 2


def test_customer_on_the_depot_with_a_zero_width_window():
    tw = _tw(((0.0, 0.0), (0.0, 0.0)), (1,), 5, (0.0, 0.0), (50.0, 0.0), 50.0)
    assert T.route_ok(tw, (1,)) and T.split_tw(tw, (1,)).cost == pytest.approx(0.0)


def test_return_exactly_at_the_horizon_is_feasible_and_a_hair_later_is_not():
    xy = ((0.0, 0.0), (5.0, 0.0))
    assert T.route_ok(_tw(xy, (1,), 5, (0.0, 0.0), (100.0, 100.0), 20.0), (1,))              # 5 + 10 + 5 = 20
    late = _tw(xy, (1,), 5, (0.0, 0.0), (100.0, 100.0), 19.99)
    assert not T.route_ok(late, (1,)) and T.split_tw(late, (1,)) is None and T.greedy_tw(late, (1,)) is None


def test_a_customer_that_cannot_be_served_alone_makes_everything_unsolvable():
    tw = _tw(((0.0, 0.0), (50.0, 0.0), (1.0, 0.0)), (1, 1), 5, (0.0, 0.0, 0.0), (100.0, 10.0, 100.0), 200.0)       # Kunde 1 ist 50 weit weg, sein Fenster endet bei 10
    assert T.split_tw(tw, (1, 2)) is None and T.split_tw(tw, (2, 1)) is None
    ex = T.exact_tw(tw)
    assert ex.cost == float("inf") and ex.routes == ()


def test_service_time_zero():
    tw = _tw(((0.0, 0.0), (5.0, 0.0), (10.0, 0.0)), (1, 1), 5, (0.0, 0.0, 0.0), (100.0, 5.0, 10.0), 100.0, service=0.0)
    assert T.route_ok(tw, (1, 2)) and T.split_tw(tw, (1, 2)).cost == pytest.approx(20.0)
    assert T.timeline(tw, (1, 2)).back == pytest.approx(20.0)


def test_waiting_over_the_whole_route_is_counted_and_shiftable():
    # Kunde bei 5, Fenster [40, 60], H = 100: Ankunft 5, Warten bis 40 (35), Bedienung bis 50, Rückkehr 55
    tw = _tw(((0.0, 0.0), (5.0, 0.0)), (1,), 5, (0.0, 40.0), (100.0, 60.0), 100.0)
    tl = T.timeline(tw, (1,))
    assert tl.wait == pytest.approx(35.0) and tl.back == pytest.approx(55.0)
    assert tl.slack == pytest.approx(45.0)                                             # min(H - Rückkehr = 45, Wartezeit 35 + Fensterende 60 - Beginn 40 = 55)
    assert tl.shift == pytest.approx(35.0) and tl.duration_late == pytest.approx(20.0)  # nur die Wartezeit lässt sich wegschieben: Abfahrt zur Zeit 35


def test_orders_cover_every_customer_for_all_families():
    for family in (0, 1, 2):
        tw = T.make_tw(6, family, 1, 2, 5, 90, 0.2, "geo")
        for order in T.orders_of(tw).values():
            assert sorted(order) == list(range(1, 7))
