"""Eigenschaftstests (ORACLE-PLAYBOOK §5): Monotonie in der Fensterbreite, Teilsegmente, Umnummerieren, Gleichheit mit Stück 3 ohne Fenster, Richtungen, Zulässigkeit der erzeugten Pläne."""

import pytest

import zfs_algorithm as A
import zfs_timewindows as T
from zfs_scenario import Instance

ABS = 1e-6


def _case(seed, mode, width=None, n=7, rnd=False):
    return T.make_tw(n, 1, seed % 2, 3, seed, 90, width, mode, rnd)


@pytest.mark.parametrize("mode", ["random", "geo"])
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_wider_windows_never_cost_more_and_never_lose_feasibility(mode, seed):
    costs = [T.exact_tw(_case(seed, mode, w)).cost for w in (0.05, 0.1, 0.2, 0.4, None)]
    assert all(b <= a + ABS for a, b in zip(costs, costs[1:])), costs
    # ein Plan mit engeren Fenstern bleibt mit weiteren zulässig (die Fenster liegen ineinander)
    narrow, wide = _case(seed, mode, 0.1), _case(seed, mode, 0.4)
    for r in T.exact_tw(narrow).routes:
        assert T.route_ok(wide, r)


@pytest.mark.parametrize("seed", [0, 3, 5])
def test_every_contiguous_part_of_a_feasible_route_is_feasible(seed):
    tw = _case(seed, "random", 0.3)
    for r in T.exact_tw(tw).routes + T.split_tw(tw, T.insert_split_order(tw)).routes:
        for i in range(len(r)):
            for j in range(i + 1, len(r) + 1):
                assert T.route_ok(tw, r[i:j])


@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_without_windows_it_is_the_split_of_stueck_3(seed):
    inst = _case(seed, "random").inst
    n = inst.n
    free = T.TW(inst, (0.0,) * (n + 1), (1e9,) * (n + 1), 1e9, 10.0)
    for order in (tuple(range(1, n + 1)), A.tsp_tour(inst)[1], tuple(range(n, 0, -1))):
        assert T.split_tw(free, order).cost == pytest.approx(A.split(inst, order).cost, abs=ABS)
    assert T.exact_tw(free).cost == pytest.approx(A.exact_cvrp(inst).cost, abs=ABS)


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_relabelling_the_customers_changes_nothing(seed):
    tw = _case(seed, "random", 0.2)
    n = tw.n
    perm = list(range(1, n + 1))
    perm = perm[3:] + perm[:3][::-1]                                  # Kunde i heißt danach perm[i-1]
    xy = [tw.inst.xy[0]] + [None] * n
    demand, early, late = [0] * n, [0.0] * (n + 1), [tw.horizon] * (n + 1)
    for old in range(1, n + 1):
        new = perm[old - 1]
        xy[new] = tw.inst.xy[old]
        demand[new - 1] = tw.inst.demand[old - 1]
        early[new], late[new] = tw.early[old], tw.late[old]
    other = T.TW(Instance(tuple(xy), tuple(demand), tw.inst.capacity), tuple(early), tuple(late), tw.horizon, tw.service)
    assert T.exact_tw(other).cost == pytest.approx(T.exact_tw(tw).cost, abs=ABS)
    order = T.insert_split_order(tw)
    assert T.split_tw(other, tuple(perm[c - 1] for c in order)).cost == pytest.approx(T.split_tw(tw, order).cost, abs=ABS)


@pytest.mark.parametrize("seed", [0, 1, 2, 4])
def test_rounded_windows_are_wider_so_the_optimum_does_not_grow(seed):
    assert T.exact_tw(_case(seed, "random", 0.1, rnd=True)).cost <= T.exact_tw(_case(seed, "random", 0.1)).cost + ABS


@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_all_orders_are_decomposable_and_produce_feasible_plans(seed):
    tw = _case(seed, "geo", 0.1, n=8)
    ex = T.exact_tw(tw)
    for key, order in T.orders_of(tw).items():
        assert sorted(order) == list(range(1, tw.n + 1)), key
        res = T.split_tw(tw, order)
        assert res is not None and T.plan_ok(tw, res.routes), key
        assert res.cost >= ex.cost - ABS, key                                  # kein Split unter dem Optimum
        assert T.plan_length(tw, res.routes) == pytest.approx(res.cost, abs=ABS)


@pytest.mark.parametrize("seed", [0, 1])
def test_the_tour_read_backwards_is_the_same_length_and_without_windows_the_same_split(seed):
    tw = _case(seed, "random", None)
    fwd, back = T.tour_order(tw, 1), T.tour_order(tw, -1)
    assert back == fwd[::-1] and A.route_length(tw.inst, fwd) == pytest.approx(A.route_length(tw.inst, back), abs=ABS)
    assert T.split_tw(tw, fwd).cost == pytest.approx(T.split_tw(tw, back).cost, abs=ABS)


def test_the_arc_count_matches_the_arc_table_and_the_split():
    tw = _case(2, "random", 0.2, n=9)
    for order in T.orders_of(tw).values():
        table = T.arc_table(tw, order)
        assert sum(r["ok"] for r in table) == T.count_arcs(tw, order)
        res = T.split_tw(tw, order)
        assert res is not None and res.arcs == T.count_arcs(tw, order)
        # jede Zelle der Tabelle stimmt mit der unabhängigen Prüfung überein
        for r in table:
            assert r["ok"] == T.route_ok(tw, order[r["start"]:r["end"]])
