"""Orakel für die Zeitfenster-Bausteine: ein unabhängiger Rechenweg (eigene Fahrplansimulation mit math.dist, Aufzählung aller Zerlegungen, Teilmengen mit Permutationen) gegen Split, Zulässigkeit,
Füllen bis voll und das exakte Optimum (Held-Karp mit Etiketten). Dazu die Dominanz: das Minimum des Splits über alle Reihenfolgen ist das Optimum."""

import itertools
import math

import pytest

import zfs_timewindows as T

ABS = 1e-6
CASES = [(n, fam, dep, seed, width, mode, rnd) for n in (5, 6) for fam in (0, 1) for dep in (0, 1) for seed in (0, 1, 2) for width, mode, rnd in ((0.1, "random", False), (0.3, "geo", True), (0.05, "geo", False), (None, "random", False))]


def oracle_route(tw, route):
    """(zulässig, Länge) einer Route mit eigener Simulation: Wegzeit aus math.dist, Beginn = max(Ankunft, Fensteranfang)."""
    xy, q = tw.inst.xy, tw.inst.demand
    t, pos, load, length = 0.0, 0, 0, 0.0
    for c in route:
        d = math.dist(xy[pos], xy[c])
        length += d
        load += q[c - 1]
        t = max(tw.early[c], t + d)
        if t > tw.late[c] + 1e-9 or load > tw.inst.capacity:
            return False, length
        t += tw.service
        pos = c
    back = math.dist(xy[pos], xy[0])
    return t + back <= tw.horizon + 1e-9, length + back


def oracle_compositions(tw, order):
    """Alle Zerlegungen der Reihenfolge in aufeinanderfolgende Routen: Liste (Routenzahl, Länge) der zulässigen."""
    n = len(order)
    out = []
    for mask in range(1 << (n - 1)):
        cuts = [0] + [i + 1 for i in range(n - 1) if mask >> i & 1] + [n]
        total, ok = 0.0, True
        for a, b in zip(cuts, cuts[1:]):
            feasible, length = oracle_route(tw, order[a:b])
            if not feasible:
                ok = False
                break
            total += length
        if ok:
            out.append((len(cuts) - 1, total))
    return out


def oracle_optimum(tw):
    """Optimum über Kundenmengen: je Teilmenge die beste zulässige Reihenfolge (alle Permutationen), dann Mengenzerlegung."""
    n = tw.n
    best = {}
    for mask in range(1, 1 << n):
        customers = [c for c in range(1, n + 1) if mask >> (c - 1) & 1]
        value = math.inf
        for perm in itertools.permutations(customers):
            ok, length = oracle_route(tw, perm)
            if ok and length < value:
                value = length
        best[mask] = value
    part = [math.inf] * (1 << n)
    part[0] = 0.0
    for mask in range(1, 1 << n):
        sub = mask
        while sub:
            if sub & (mask & -mask) and part[mask ^ sub] + best[sub] < part[mask]:
                part[mask] = part[mask ^ sub] + best[sub]
            sub = (sub - 1) & mask
    return part[-1]


def _tw(n, fam, dep, seed, width, mode, rnd):
    return T.make_tw(n, fam, dep, 2, seed, 90, width, mode, rnd)


@pytest.mark.parametrize("case", CASES[::3])
def test_split_equals_the_enumeration_of_all_compositions(case):
    tw = _tw(*case)
    for order in (tuple(range(1, tw.n + 1)), tuple(range(tw.n, 0, -1)), T.insert_split_order(tw)):
        res = T.split_tw(tw, order)
        comps = oracle_compositions(tw, order)
        if not comps:
            assert res is None
            continue
        assert res.cost == pytest.approx(min(c[1] for c in comps), abs=ABS)
        lex = T.split_tw(tw, order, lexicographic=True)
        best_k = min(c[0] for c in comps)
        assert len(lex.routes) == best_k and lex.cost == pytest.approx(min(c[1] for c in comps if c[0] == best_k), abs=ABS)
        greedy = T.greedy_tw(tw, order)
        assert greedy is not None and len(greedy) == best_k                       # Füllen bis voll ist optimal in der Routenzahl
        assert all(oracle_route(tw, r)[0] for r in res.routes) and [c for r in res.routes for c in r] == list(order)


@pytest.mark.parametrize("case", CASES[1::4])
def test_route_check_matches_the_independent_simulation(case):
    tw = _tw(*case)
    for r in range(1, 4):
        for route in itertools.permutations(range(1, tw.n + 1), r):
            assert T.route_ok(tw, route) == oracle_route(tw, route)[0]


@pytest.mark.parametrize("case", [c for c in CASES if c[0] == 5][::2])
def test_exact_optimum_equals_the_subset_enumeration_and_dominance(case):
    tw = _tw(*case)
    ex = T.exact_tw(tw)
    opt = oracle_optimum(tw)
    assert ex.cost == pytest.approx(opt, abs=ABS)
    assert T.plan_ok(tw, ex.routes) and T.plan_length(tw, ex.routes) == pytest.approx(ex.cost, abs=ABS)
    # Dominanz: das Minimum des Splits über alle Reihenfolgen ist das Optimum, und keine Reihenfolge ist besser
    best = math.inf
    for order in itertools.permutations(range(1, tw.n + 1)):
        res = T.split_tw(tw, order)
        if res is not None:
            assert res.cost >= ex.cost - ABS
            best = min(best, res.cost)
    assert best == pytest.approx(ex.cost, abs=ABS)


def test_labels_are_pareto_fronts_of_at_least_one_label():
    tw = _tw(6, 1, 0, 3, 0.4, "random", False)
    ex = T.exact_tw(tw)
    assert ex.mean_labels >= 1.0 and ex.max_labels >= 1 and ex.states > 0
    free = T.exact_tw(T.without_windows(tw))
    assert free.mean_labels == pytest.approx(1.0)                                # ohne Fenster dominiert die kürzeste Strecke immer (früheste Zeit folgt)
