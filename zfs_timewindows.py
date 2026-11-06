"""Zeitfenster (Stück 8 der Linie Tourenbildung): Split mit Fenstern, Bogenprüfung, exaktes Optimum mit Pareto-Etiketten, Fahrplan, Wartezeit und Zeitschlupf.

Modell: Fahrzeit = Entfernung, Bedienzeit S je Kunde, Zeitfenster [e_i, l_i] (Ankunft vor e_i: warten, nach l_i: unzulässig), Depotfenster [0, H], Abfahrt zur Zeit 0, gleiche Fahrzeuge, keine
Flottengrenze. Kosten = gefahrene Strecke (Warten kostet nichts). Eine Route ist zulässig, wenn die Last nicht über Q liegt und alle Fenster und H gehalten werden.

Fenster: um die Ankunftszeiten eines Bezugsplans gelegt (Bezug „zufällig“: Füllen bis voll auf einer Zufallsfolge; Bezug „geografisch“: das CVRP-Optimum bis 12 Kunden, darüber Savings), Breite = Anteil
`width` von H (H = 1,25 mal späteste Rückkehr des Bezugsplans); bei width = None gilt [0, H] für alle. So hat jede Instanz mindestens einen zulässigen Plan.

Gleichstandsregeln (deterministisch): Split: unter gleich teuren Zerlegungen gewinnt die mit dem kleinsten Startknoten des letzten Bogens (eine Verbesserung zählt nur, wenn sie um mehr als TOL besser ist);
Einfügen nach Split: die kleinste Stelle gewinnt; exaktes Optimum: der erste gefundene Wert gewinnt (Etiketten nach Strecke, dann Zeit; Teilmengen von der niedrigsten Maske)."""

import math
import random
from dataclasses import dataclass

import zfs_algorithm as A
import zfs_constants as C
import zfs_routing as R
import zfs_savings as S
from zfs_scenario import Instance, distance_matrix, make_instance

INF = math.inf


@dataclass(frozen=True)
class TW:
    """Instanz mit Zeitfenstern; Platz 0 der Listen ist das Depot (early 0, late H)."""
    inst: Instance
    early: tuple[float, ...]
    late: tuple[float, ...]
    horizon: float
    service: float = C.SERVICE

    @property
    def n(self) -> int:
        return self.inst.n

    @property
    def D(self):
        return distance_matrix(self.inst)


# ----------------------------------------------------------------------------------------------------------------------------------------- Erzeugung

def arrival_schedule(inst: Instance, route, service: float = C.SERVICE) -> tuple[list[float], float]:
    """Frühester Fahrplan einer Route ohne Fenster: Ankunftszeiten (ohne Warten) und Rückkehrzeit."""
    D = distance_matrix(inst)
    t, prev, out = 0.0, 0, []
    for c in route:
        arr = t + D[prev][c]
        out.append(arr)
        t, prev = arr + service, c
    return out, t + D[prev][0]


def next_fit(inst: Instance, order) -> tuple[tuple[int, ...], ...]:
    """„Füllen bis voll“ nach der Last (Stück 3): eine neue Route beginnt, sobald der nächste Kunde nicht mehr passt."""
    out, cur, load = [], [], 0
    for c in order:
        if cur and load + inst.demand[c - 1] > inst.capacity:
            out.append(tuple(cur))
            cur, load = [], 0
        cur.append(c)
        load += inst.demand[c - 1]
    return tuple(out) + ((tuple(cur),) if cur else ())


def reference_plan(inst: Instance, seed: int, mode: str) -> tuple[tuple[int, ...], ...]:
    """Bezugsplan, um dessen Ankunftszeiten die Fenster liegen: „random“ (Füllen bis voll auf einer Zufallsfolge) oder „geo“ (CVRP-Optimum bis 12 Kunden, sonst Savings)."""
    if mode == "random":
        order = list(range(1, inst.n + 1))
        random.Random(seed * 7919 + inst.n).shuffle(order)
        return next_fit(inst, order)
    return A.exact_cvrp(inst).routes if inst.n <= R.EXACT_MAX else S.savings_routes(inst)


def windows_around(inst: Instance, ref_routes, width, service: float = C.SERVICE) -> TW:
    """Fenster der Breite `width` (Anteil von H) um die Ankunftszeiten des Bezugsplans; width None: [0, H]."""
    arrival, end = {}, 0.0
    for r in ref_routes:
        arrs, back = arrival_schedule(inst, r, service)
        end = max(end, back)
        arrival.update(zip(r, arrs))
    H = 1.25 * end
    n = inst.n
    if width is None:
        early, late = [0.0] * (n + 1), [H] * (n + 1)
    else:
        half = width * H / 2
        early = [0.0] + [max(0.0, arrival[c] - half) for c in range(1, n + 1)]
        late = [H] + [min(H, arrival[c] + half) for c in range(1, n + 1)]
    return TW(inst, tuple(float(e) for e in early), tuple(float(x) for x in late), float(H), service)


def rounded(tw: TW) -> TW:
    """Fenster auf ganze Zahlen (Anfang abgerundet, Ende aufgerundet, H aufgerundet): für die Handrechnung."""
    return TW(tw.inst, tuple(float(math.floor(e)) for e in tw.early), tuple(float(math.ceil(x)) for x in tw.late), float(math.ceil(tw.horizon)), tw.service)


def make_tw(n: int, family: int, depot: int, routes: int, seed: int, fill: int, width, mode: str = "random", round_windows: bool = False) -> TW:
    """Deterministisch aus den Eingaben: gleiche Eingabe, gleiche Instanz."""
    inst = make_instance(n, family, depot, routes, seed, fill)
    tw = windows_around(inst, reference_plan(inst, seed, mode), width)
    return rounded(tw) if round_windows else tw


def without_windows(tw: TW) -> TW:
    """Dieselbe Instanz mit Fenstern [0, H] (Bögen ohne Fenster)."""
    n = tw.n
    return TW(tw.inst, (0.0,) * (n + 1), (tw.horizon,) * (n + 1), tw.horizon, tw.service)


# ----------------------------------------------------------------------------------------------------------------------------------------- Zulässigkeit

def arrive(tw: TW, t: float, a: int, c: int):
    """Beginn der Bedienung bei c nach Abfahrt von a zur Zeit t (mit Warten bis zum Fensteranfang); None bei Verspätung."""
    arr = max(tw.early[c], t + tw.D[a][c])
    return arr if arr <= tw.late[c] + C.TOL else None


def route_ok(tw: TW, route) -> bool:
    """Unabhängiger Prüfer: Last, alle Fenster und Rückkehr bis H."""
    load, t, prev = 0, 0.0, 0
    for c in route:
        load += tw.inst.demand[c - 1]
        arr = arrive(tw, t, prev, c)
        if arr is None or load > tw.inst.capacity:
            return False
        t, prev = arr + tw.service, c
    return t + tw.D[prev][0] <= tw.horizon + C.TOL


def plan_ok(tw: TW, routes) -> bool:
    seen = sorted(c for r in routes for c in r)
    return seen == list(range(1, tw.n + 1)) and all(route_ok(tw, r) for r in routes)


def plan_length(tw: TW, routes) -> float:
    return A.plan_length(tw.inst, routes)


# ----------------------------------------------------------------------------------------------------------------------------------------- Split mit Fenstern

@dataclass(frozen=True)
class TWSplit:
    cost: float
    routes: tuple[tuple[int, ...], ...]
    arcs: int                       # Zahl der zulässigen Bögen (Segmente)


def _less(a, b) -> bool:
    return a[0] < b[0] or (a[0] == b[0] and a[1] < b[1] - C.TOL)


def split_tw(tw: TW, order, lexicographic: bool = False):
    """Optimaler Split einer Reihenfolge: kürzester Weg im azyklischen Hilfsgraphen, Bogen i -> j (Kunden order[i:j]) nur, wenn das Segment Last und Zeitfenster hält. Die Zeitprüfung beim Verlängern
    kostet O(1); die Rückkehrzeit wächst beim Verlängern (Dreiecksungleichung, Bedienzeit, Warten), deshalb sind längere Segmente nach dem ersten Verstoß ebenfalls unzulässig und die Schleife bricht ab.
    lexikographisch: kleinste Routenzahl, dann kleinste Strecke. Rückgabe: TWSplit, oder None, wenn die Reihenfolge nicht zerlegbar ist."""
    order = tuple(order)
    n = len(order)
    best = [(INF, INF)] * (n + 1)
    best[0] = (0, 0.0)
    pred = [None] * (n + 1)
    D = tw.D
    arcs = 0
    for i in range(n):
        if best[i][0] == INF:
            continue
        load, t, prev, dist = 0, 0.0, 0, 0.0
        for j in range(i, n):
            c = order[j]
            load += tw.inst.demand[c - 1]
            if load > tw.inst.capacity:
                break
            arr = arrive(tw, t, prev, c)
            if arr is None:
                break
            dist += D[prev][c]
            t, prev = arr + tw.service, c
            if t + D[c][0] > tw.horizon + C.TOL:
                break
            arcs += 1
            cost = dist + D[c][0]
            cand = (best[i][0] + 1, best[i][1] + cost) if lexicographic else (0, best[i][1] + cost)
            if _less(cand, best[j + 1]):
                best[j + 1] = cand
                pred[j + 1] = i
    if best[n][0] == INF:
        return None
    routes, node = [], n
    while node > 0:
        i = pred[node]
        routes.append(tuple(order[i:node]))
        node = i
    routes.reverse()
    return TWSplit(float(best[n][1]), tuple(routes), arcs)


def count_arcs(tw: TW, order) -> int:
    """Zahl der zulässigen Bögen (Segmente) einer Reihenfolge, unabhängig davon, ob das Ende erreichbar ist."""
    order = tuple(order)
    n = len(order)
    arcs = 0
    for i in range(n):
        load, t, prev = 0, 0.0, 0
        for j in range(i, n):
            c = order[j]
            load += tw.inst.demand[c - 1]
            if load > tw.inst.capacity:
                break
            arr = arrive(tw, t, prev, c)
            if arr is None:
                break
            t, prev = arr + tw.service, c
            if t + tw.D[c][0] > tw.horizon + C.TOL:
                break
            arcs += 1
    return arcs


def arc_table(tw: TW, order) -> list[dict]:
    """Alle Segmente (i, j) mit i < j <= n: zulässig oder nicht, mit Grund. Gründe: "load" (Last über Q), "window" (der Kunde `culprit` käme nach seinem Fensterende), "return" (Rückkehr nach H).
    Wer bei einem Segment scheitert, scheitert auch bei jedem längeren (Teilsegmente zulässiger Routen sind zulässig): `culprit` ist der Kunde, an dem das kürzere Segment scheitert."""
    order = tuple(order)
    n = len(order)
    rows = []
    for i in range(n):
        load, t, prev = 0, 0.0, 0
        stop = None
        for j in range(i, n):
            c = order[j]
            if stop is None:
                load += tw.inst.demand[c - 1]
                if load > tw.inst.capacity:
                    stop = ("load", c)
                else:
                    arr = arrive(tw, t, prev, c)
                    if arr is None:
                        stop = ("window", c)
                    else:
                        t, prev = arr + tw.service, c
                        if t + tw.D[c][0] > tw.horizon + C.TOL:
                            stop = ("return", c)
            rows.append({"start": i, "end": j + 1, "ok": stop is None, "reason": None if stop is None else stop[0], "culprit": None if stop is None else stop[1]})
    return rows


def blocked_segments(tw: TW, order) -> list[dict]:
    """Je Startplatz i das längste zulässige Segment und der Grund, warum das nächste nicht mehr geht (mit Ankunftszeit gegen Fensterende bei „window“)."""
    order = tuple(order)
    n = len(order)
    out = []
    for i in range(n):
        load, t, prev, last = 0, 0.0, 0, i
        reason = None
        for j in range(i, n):
            c = order[j]
            load += tw.inst.demand[c - 1]
            if load > tw.inst.capacity:
                reason = {"reason": "load", "customer": c}
                break
            raw = t + tw.D[prev][c]
            arr = arrive(tw, t, prev, c)
            if arr is None:
                reason = {"reason": "window", "customer": c, "arrival": float(raw), "late": tw.late[c]}
                break
            t, prev = arr + tw.service, c
            if t + tw.D[c][0] > tw.horizon + C.TOL:
                reason = {"reason": "return", "customer": c, "back": float(t + tw.D[c][0])}
                break
            last = j + 1
        out.append({"start": i, "longest": order[i:last], "blocked": reason})
    return out


def greedy_tw(tw: TW, order):
    """Füllen bis voll mit Fenstern: eine neue Route beginnt, sobald der nächste Kunde die Route unzulässig macht. Routen oder None, wenn ein Kunde allein unzulässig ist."""
    routes, cur = [], []
    for c in order:
        if cur and not route_ok(tw, cur + [c]):
            routes.append(tuple(cur))
            cur = []
        if not route_ok(tw, cur + [c]):
            return None
        cur.append(c)
    if cur:
        routes.append(tuple(cur))
    return tuple(routes)


# ----------------------------------------------------------------------------------------------------------------------------------------- Reihenfolgen

def tour_order(tw: TW, direction: int = 1) -> tuple[int, ...]:
    """Kürzeste Rundreise als Riesentour (exakt bis 12 Kunden, sonst Heuristik ab der Winkelfolge), gelesen nach dem Depot in der Richtung `direction` (+1: lexikographisch kleinere Richtung)."""
    inst = tw.inst
    if inst.n <= R.EXACT_MAX:
        route = A.tsp_tour(inst)[1]
    else:
        ang = R.angular_order(inst)
        route = R.tsp_heuristic(inst, ang, ang)[1]
    return tuple(route) if direction > 0 else tuple(route[::-1])


def insert_split_order(tw: TW) -> tuple[int, ...]:
    """Einfügen nach Split mit Fenstern: Kunden in absteigender Entfernung vom Depot, jeder an der Stelle mit den kleinsten Split-Kosten (Fenster eingerechnet)."""
    seq = sorted(range(1, tw.n + 1), key=lambda c: (-tw.D[0][c], c))
    order: list[int] = []
    for c in seq:
        best = None
        for p in range(len(order) + 1):
            trial = order[:p] + [c] + order[p:]
            res = split_tw(tw, trial)
            if res is not None and (best is None or res.cost < best[0] - 1e-12):
                best = (res.cost, trial)
        order = best[1]
    return tuple(order)


def orders_of(tw: TW) -> dict[str, tuple[int, ...]]:
    """Die Reihenfolgen des Vergleichs: kürzeste Rundreise, Winkelfolge, Fensterende, Zufall, Einfügen nach Split."""
    inst = tw.inst
    base = list(range(1, inst.n + 1))
    rnd = base[:]
    random.Random(inst.demand[0] * 1000 + inst.n).shuffle(rnd)
    return {"tour": tour_order(tw), "angle": R.angular_order(inst), "late": tuple(sorted(base, key=lambda c: (tw.late[c], c))), "random": tuple(rnd), "es": insert_split_order(tw)}


# ----------------------------------------------------------------------------------------------------------------------------------------- exakt

@dataclass(frozen=True)
class TWExact:
    cost: float
    routes: tuple[tuple[int, ...], ...]
    mean_labels: float              # mittlere Zahl der Pareto-Etiketten je (Menge, letzter Kunde)
    max_labels: int
    states: int                     # erreichte Zustände (Menge, letzter Kunde)


def pareto(labels) -> list:
    """Nicht dominierte Etiketten (Strecke, Zeit, Vorgänger): aufsteigend nach Strecke, die Zeit muss dabei fallen."""
    out, best_t = [], INF
    for lab in sorted(labels, key=lambda x: (x[0], x[1])):
        if lab[1] < best_t - C.TOL:
            out.append(lab)
            best_t = lab[1]
    return out


def exact_tw(tw: TW) -> TWExact:
    """Exaktes Optimum (Strecke): je Kundenmenge die kürzeste zulässige Route (Held-Karp mit Pareto-Etiketten (Strecke, Zeit)), dann Mengenzerlegung. Die Zahl der Etiketten je Zustand wird mitgezählt."""
    n = tw.n
    D = tw.D
    q = tw.inst.demand
    size = 1 << n
    load = [0] * size
    for Sx in range(1, size):
        low = (Sx & -Sx).bit_length() - 1
        load[Sx] = load[Sx & (Sx - 1)] + q[low]
    labels: dict = {}                                       # (Menge, letzter) -> Liste (Strecke, Zeit nach Bedienung, Vorgänger-Schlüssel)
    for c in range(1, n + 1):
        arr = arrive(tw, 0.0, 0, c)
        if arr is not None and q[c - 1] <= tw.inst.capacity:
            labels[(1 << (c - 1), c)] = [(D[0][c], arr + tw.service, None)]
    best_route: dict = {}
    n_labels = n_states = max_labels = 0
    for Sx in range(1, size):
        if load[Sx] > tw.inst.capacity:
            continue
        for last in range(1, n + 1):
            labs = labels.get((Sx, last))
            if not labs:
                continue
            n_states += 1
            n_labels += len(labs)
            max_labels = max(max_labels, len(labs))
            for idx, (dist, t, _) in enumerate(labs):
                if t + D[last][0] <= tw.horizon + C.TOL:
                    total = dist + D[last][0]
                    if total < best_route.get(Sx, (INF,))[0]:
                        best_route[Sx] = (total, (Sx, last, idx))
            for nxt in range(1, n + 1):
                if Sx >> (nxt - 1) & 1:
                    continue
                S2 = Sx | (1 << (nxt - 1))
                if load[S2] > tw.inst.capacity:
                    continue
                new = []
                for idx, (dist, t, _) in enumerate(labs):
                    arr = arrive(tw, t, last, nxt)
                    if arr is not None:
                        new.append((dist + D[last][nxt], arr + tw.service, (Sx, last, idx)))
                if new:
                    labels[(S2, nxt)] = pareto(labels.get((S2, nxt), []) + new)
    part = [INF] * size
    part[0] = 0.0
    parent = [0] * size
    for Sx in range(1, size):
        low = Sx & -Sx
        sub = Sx
        while sub:
            if sub & low and sub in best_route and part[Sx ^ sub] + best_route[sub][0] < part[Sx] - C.TOL:
                part[Sx] = part[Sx ^ sub] + best_route[sub][0]
                parent[Sx] = sub
            sub = (sub - 1) & Sx
    if part[size - 1] == INF:                                   # mindestens ein Kunde ist allein nicht zulässig erreichbar
        return TWExact(INF, (), n_labels / n_states if n_states else 0.0, max_labels, n_states)
    routes = []
    Sx = size - 1
    while Sx:
        sub = parent[Sx]
        key = best_route[sub][1]
        route = []
        while key is not None:
            route.append(key[1])
            key = labels[(key[0], key[1])][key[2]][2]
        routes.append(tuple(route[::-1]))
        Sx ^= sub
    routes.sort(key=lambda r: r[0])
    return TWExact(float(part[size - 1]), tuple(routes), n_labels / n_states if n_states else 0.0, max_labels, n_states)


# ----------------------------------------------------------------------------------------------------------------------------------------- Fahrplan, Wartezeit, Zeitschlupf

@dataclass(frozen=True)
class Timeline:
    rows: tuple[dict, ...]          # je Kunde: customer, raw (Ankunft ohne Warten), start (Beginn der Bedienung), wait, early, late
    back: float                     # Rückkehr zum Depot
    wait: float                     # Wartezeit insgesamt
    slack: float                    # Zeitschlupf am Depot: um wie viel sich die Abfahrt verschieben lässt, ohne ein Fenster oder H zu verletzen (Rest der Wartezeit eingerechnet)
    shift: float                    # tatsächlich nutzbare Verschiebung: min(Schlupf, Wartezeit) – nur Wartezeit lässt sich wegschieben
    duration_early: float           # Dauer bei Abfahrt zur Zeit 0
    duration_late: float            # Dauer bei spätestmöglicher Abfahrt


def timeline(tw: TW, route) -> Timeline:
    """Frühester Fahrplan einer zulässigen Route: Ankünfte, Beginn der Bedienung, Wartezeiten, Rückkehr; dazu Zeitschlupf (Savelsbergh) und die Dauer bei spätem Losfahren."""
    t, prev, wait_total, rows = 0.0, 0, 0.0, []
    for c in route:
        raw = t + tw.D[prev][c]
        start = max(raw, tw.early[c])
        wait_total += start - raw
        rows.append({"customer": c, "raw": float(raw), "start": float(start), "wait": float(start - raw), "early": tw.early[c], "late": tw.late[c]})
        t, prev = start + tw.service, c
    back = t + tw.D[prev][0]
    best, cum = tw.horizon - back, 0.0
    for row in rows:
        cum += row["wait"]
        best = min(best, cum + (row["late"] - row["start"]))
    shift = max(0.0, min(best, wait_total))
    return Timeline(tuple(rows), float(back), float(wait_total), float(best), float(shift), float(back), float(back - shift))


def split_duration(tw: TW, order):
    """Split mit Kosten = kürzeste Dauer je Segment (spätes Losfahren); Rückgabe (Summe der Dauern, Routen) oder None."""
    order = tuple(order)
    n = len(order)
    best = [INF] * (n + 1)
    best[0] = 0.0
    pred = [None] * (n + 1)
    for i in range(n):
        if best[i] == INF:
            continue
        for j in range(i, n):
            seg = order[i:j + 1]
            if not route_ok(tw, seg):
                if sum(tw.inst.demand[c - 1] for c in seg) > tw.inst.capacity:
                    break
                continue
            d = timeline(tw, seg).duration_late
            if best[i] + d < best[j + 1] - C.TOL:
                best[j + 1], pred[j + 1] = best[i] + d, i
    if best[n] == INF:
        return None
    routes, node = [], n
    while node > 0:
        routes.append(order[pred[node]:node])
        node = pred[node]
    return float(best[n]), tuple(routes[::-1])
