"""Savings (Clarke und Wright, 1964), parallele Fassung (aus savings-gegen-split-demo, Stück 4 der Linie, kopiert, umbenannt und gekürzt auf das, was dieses Stück braucht).

Ersparnis eines Paares (i, j): s(i, j) = d(0,i) + d(0,j) - d(i,j). Die Paare mit s > 0 werden in absteigender Ersparnis abgearbeitet (Gleichstand: kleineres i, dann kleineres j); ein Paar legt
zwei Routen zusammen, wenn i und j in verschiedenen Routen stehen, beide am Rand ihrer Route (erster oder letzter Kunde) und die Last in ein Fahrzeug passt; Routen dürfen dabei umgedreht werden.
Das Verfahren dient hier nur dazu, bei den Bändern ab 25 Kunden den Bezugsplan zu liefern, um den die Zeitfenster gelegt werden."""

import numpy as np

from zfs_scenario import Instance, distance_matrix

SAME_ROUTE, NO_END, CAPACITY, MERGED = "same", "no_end", "capacity", "merged"


def savings_list(inst: Instance) -> list[tuple[float, int, int]]:
    """Alle Paare i < j mit s(i, j) > 0, absteigend nach Ersparnis, Gleichstand: kleinere Nummern zuerst."""
    D = distance_matrix(inst)
    iu, ju = np.triu_indices(inst.n, 1)
    d0 = D[0][1:]
    s = d0[iu] + d0[ju] - D[iu + 1, ju + 1]
    order = np.lexsort((ju + 1, iu + 1, -s))
    return [(float(s[k]), int(iu[k] + 1), int(ju[k] + 1)) for k in order if s[k] > 0]


def _merge(inst: Instance, routes, where, load, i: int, j: int) -> str:
    """Ein Paar abarbeiten (verändert routes, where und load); Rückgabe: der Ausgang."""
    ri, rj = where[i], where[j]
    if ri == rj:
        return SAME_ROUTE
    a, b = routes[ri], routes[rj]
    if not ((a[0] == i or a[-1] == i) and (b[0] == j or b[-1] == j)):
        return NO_END
    if load[ri] + load[rj] > inst.capacity:
        return CAPACITY
    if a[-1] == i and b[0] == j:
        new = a + b
    elif a[0] == i and b[-1] == j:
        new = b + a
    elif a[0] == i and b[0] == j:
        new = a[::-1] + b
    else:
        new = a + b[::-1]
    routes[ri] = new
    load[ri] += load[rj]
    del routes[rj], load[rj]
    for c in new:
        where[c] = ri
    return MERGED


def savings_routes(inst: Instance) -> tuple[tuple[int, ...], ...]:
    """Die Routen der parallelen Savings (jeder Kunde fährt zuerst allein)."""
    routes = {i: [i] for i in range(1, inst.n + 1)}
    where = {i: i for i in routes}
    load = {i: inst.demand[i - 1] for i in routes}
    for _, i, j in savings_list(inst):
        _merge(inst, routes, where, load, i, j)
    return tuple(tuple(r) for r in routes.values())
