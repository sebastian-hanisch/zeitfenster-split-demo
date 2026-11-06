"""Kern (aus riesentour-split-demo, split-gegen-fuellen-demo, Stück 1 und 3 der Linie, kopiert, umbenannt und gekürzt: ohne „Füllen bis voll“, ohne Flottengrenze).

Split einer Riesentour, Hilfsgraph, exakter Löser, kürzeste Rundreise. Das Savings-Verfahren selbst steht in zfs_savings.py.

Jede Regel ist eine eigene Funktion mit expliziten Ein- und Ausgaben (DEMO-PLAYBOOK §1b). Gleichstandsregeln (alle deterministisch):
- Split: unter gleich teuren Zerlegungen gewinnt die mit dem kleinsten Startknoten des letzten Bogens, also mit den längeren Routen am Ende
  der Reihenfolge (Verbesserung nur, wenn sie um mehr als TOL besser ist).
- Held-Karp: bei gleichen Werten der kleinste Kunde; die Rundreise wird in der Richtung ausgegeben, deren Folge lexikographisch kleiner ist.
- Exakter Löser: Routen werden so gedreht, dass der kleinere Endkunde vorn steht, und nach ihrem ersten Kunden sortiert."""

import math
from dataclasses import dataclass

import numpy as np

import zfs_constants as C
from zfs_scenario import Instance, distance_matrix


@dataclass(frozen=True)
class SplitResult:
    cost: float
    routes: tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class Arc:
    start: int                    # Knoten i des Hilfsgraphen: die ersten i Kunden der Reihenfolge sind bedient
    end: int
    customers: tuple[int, ...]
    load: int
    cost: float


@dataclass(frozen=True)
class ExactResult:
    cost: float
    routes: tuple[tuple[int, ...], ...]


# ----------------------------------------------------------------------------------------------------------------------------------------- Routen

def route_length(inst: Instance, route) -> float:
    """Länge Depot, Kunden in dieser Reihenfolge, Depot. Eine leere Route kostet nichts."""
    route = tuple(route)
    if not route:
        return 0.0
    D = distance_matrix(inst)
    return float(D[0][route[0]] + sum(D[a][b] for a, b in zip(route, route[1:])) + D[route[-1]][0])


def plan_length(inst: Instance, routes) -> float:
    return float(sum(route_length(inst, r) for r in routes))


def is_feasible_plan(inst: Instance, routes) -> bool:
    """Unabhängiger Prüfer: jeder Kunde genau einmal, keine Route über der Kapazität."""
    seen = [c for r in routes for c in r]
    return sorted(seen) == list(range(1, inst.n + 1)) and all(inst.load(r) <= inst.capacity for r in routes)


def concatenate(routes) -> tuple[int, ...]:
    return tuple(c for r in routes for c in r)


# ----------------------------------------------------------------------------------------------------------------------------------------- Split

def split_arcs(inst: Instance, order) -> list[Arc]:
    """Alle Bögen des Hilfsgraphen: Bogen i -> j bedient die Kunden order[i:j] als eine Route, wenn deren Last in das Fahrzeug passt."""
    D = distance_matrix(inst)
    order = tuple(order)
    arcs = []
    for i in range(len(order)):
        load = 0
        inner = 0.0
        for j in range(i, len(order)):
            c = order[j]
            load += inst.demand[c - 1]
            if load > inst.capacity:
                break
            inner = D[0][c] if j == i else inner + D[order[j - 1]][c]
            arcs.append(Arc(i, j + 1, order[i:j + 1], load, float(inner + D[c][0])))
    return arcs


def split(inst: Instance, order) -> SplitResult:
    """Optimale Zerlegung einer Reihenfolge in Routen: kürzester Weg von 0 nach n im azyklischen Hilfsgraphen (Dynamische Programmierung in Reihenfolge)."""
    order = tuple(order)
    n = len(order)
    best = [math.inf] * (n + 1)
    pred: list[Arc | None] = [None] * (n + 1)
    best[0] = 0.0
    for arc in split_arcs(inst, order):          # nach Startknoten aufsteigend: best[arc.start] ist hier schon endgültig
        value = best[arc.start] + arc.cost
        if value < best[arc.end] - C.TOL:
            best[arc.end] = value
            pred[arc.end] = arc
    routes = []
    node = n
    while node > 0:
        arc = pred[node]
        routes.append(arc.customers)
        node = arc.start
    routes.reverse()
    return SplitResult(float(best[n]), tuple(routes))


# ----------------------------------------------------------------------------------------------------------------------------------------- exakt

def _held_karp(inst: Instance):
    """dp[S, l]: kürzester Weg vom Depot über die Kundenmenge S (Bitmaske, Kunde c = Bit c - 1), der in l endet; closed[S]: Rundweg über S."""
    D = distance_matrix(inst)
    n = inst.n
    size = 1 << n
    dp = np.full((size, n), np.inf)
    for c in range(n):
        dp[1 << c, c] = D[0][c + 1]
    for S in range(1, size):
        for last in range(n):
            value = dp[S, last]
            if not (S >> last) & 1 or value == math.inf:
                continue
            for nxt in range(n):
                if (S >> nxt) & 1:
                    continue
                S2 = S | (1 << nxt)
                candidate = value + D[last + 1][nxt + 1]
                if candidate < dp[S2, nxt]:
                    dp[S2, nxt] = candidate
    closed = np.full(size, np.inf)
    closed[0] = 0.0
    for S in range(1, size):
        closed[S] = min(dp[S, l] + D[l + 1][0] for l in range(n) if (S >> l) & 1)
    return dp, closed


def _route_of(inst: Instance, dp: np.ndarray, S: int) -> tuple[int, ...]:
    """Beste Reihenfolge der Kundenmenge S (Rückverfolgung im Held-Karp-Feld)."""
    D = distance_matrix(inst)
    n = inst.n
    last = min((l for l in range(n) if (S >> l) & 1), key=lambda l: (dp[S, l] + D[l + 1][0], l))
    order = [last + 1]
    current = S
    while current & (current - 1):
        previous = current ^ (1 << last)
        before = min((q for q in range(n) if (previous >> q) & 1), key=lambda q: (dp[previous, q] + D[q + 1][last + 1], q))
        order.append(before + 1)
        current, last = previous, before
    order.reverse()
    return tuple(order)


def _canonical(route: tuple[int, ...]) -> tuple[int, ...]:
    return route if route[0] <= route[-1] else route[::-1]


def tsp_tour(inst: Instance) -> tuple[float, tuple[int, ...]]:
    """Kürzeste Rundreise durch das Depot und alle Kunden (Held-Karp) als Länge und Kundenfolge ab dem Depot, in der lexikographisch kleineren Richtung."""
    dp, closed = _held_karp(inst)
    full = (1 << inst.n) - 1
    route = _route_of(inst, dp, full)
    return float(closed[full]), min(route, route[::-1])


def exact_cvrp(inst: Instance) -> ExactResult:
    """Kleinste Gesamtlänge aller zulässigen Tourenpläne (unbegrenzte Flotte): beste Route je Kundenmenge (Held-Karp), dann Mengenzerlegung über Teilmengen."""
    n = inst.n
    size = 1 << n
    dp, closed = _held_karp(inst)
    load = [0] * size
    for S in range(1, size):
        low = (S & -S).bit_length() - 1
        load[S] = load[S & (S - 1)] + inst.demand[low]
    best = [math.inf] * size
    parent = [0] * size
    best[0] = 0.0
    for S in range(1, size):
        low = S & -S
        sub = S
        while sub:
            if sub & low and load[sub] <= inst.capacity:
                value = best[S ^ sub] + closed[sub]
                if value < best[S] - C.TOL:
                    best[S] = value
                    parent[S] = sub
            sub = (sub - 1) & S
    routes = []
    S = size - 1
    while S:
        sub = parent[S]
        routes.append(_canonical(_route_of(inst, dp, sub)))
        S ^= sub
    routes.sort(key=lambda r: r[0])
    return ExactResult(float(best[size - 1]), tuple(routes))
