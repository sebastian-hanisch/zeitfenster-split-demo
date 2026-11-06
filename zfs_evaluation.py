"""Kennzahlen, Verdikt-Logik und Bänder. Verdikte sind reine Funktionen (Art, Text): die App ruft st.<Art>(Text), die Tests prüfen jede Zahl im Text."""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from statistics import mean, median

import zfs_algorithm as A
import zfs_constants as C
import zfs_timewindows as T


@dataclass(frozen=True)
class Settings:
    n: int = C.DEFAULT_N
    family: int = C.DEFAULT_FAMILY
    depot: int = C.DEFAULT_DEPOT
    routes: int = C.DEFAULT_ROUTES
    fill: int = C.DEFAULT_FILL
    seed: int = C.DEFAULT_SEED
    width: int = C.DEFAULT_WIDTH             # Platz in LIVE_WIDTHS
    mode: int = C.DEFAULT_MODE               # Platz in MODE_KEYS
    round_windows: bool = C.DEFAULT_ROUND


VIEW_KEYS = ("tour", "tour_rev", "es", "angle", "late", "random")     # Reihenfolgen der Schritt-für-Schritt-Ansicht
VIEW_NAMES = {**C.ORDER_NAMES, "tour_rev": "Kürzeste Rundreise, rückwärts"}


@dataclass(frozen=True, eq=False)
class Analysis:
    settings: Settings
    tw: T.TW
    exact: T.TWExact                     # Optimum über alle zulässigen Tourenpläne
    orders: dict                         # Schlüssel -> Reihenfolge (VIEW_KEYS)
    splits: dict                         # Schlüssel -> TWSplit oder None (nicht zerlegbar)
    arcs: dict                           # Schlüssel -> (zulässige Bögen, Bögen ohne Fenster)
    greedy: dict                         # Schlüssel -> Routen von „Füllen bis voll“ mit Fenstern oder None


# ----------------------------------------------------------------------------------------------------------------------------------- Formate

def de(x: float, digits: int = 2) -> str:
    return f"{x:.{digits}f}".replace(".", ",")


def pct(x: float, digits: int = 1) -> str:
    return f"{de(x, digits)} %"


def signed_pct(x: float, digits: int = 1) -> str:
    """Mit Vorzeichen (echtes Minus); -0,0 wird zu 0,0."""
    text = de(abs(x), digits)
    if float(text.replace(",", ".")) == 0.0:
        return f"{text} %"
    return f"{'+' if x > 0 else '−'}{text} %"


def routes_word(k: int) -> str:
    return f"{k} Route" if k == 1 else f"{k} Routen"


def instances_word(k: int) -> str:
    return f"{k} Instanz" if k == 1 else f"{k} Instanzen"


def gap_percent(cost: float, reference: float) -> float:
    """Mehrkosten gegenüber der Referenz in Prozent der Referenz; unter der Toleranz oder ohne Referenzkosten gibt es keinen Abstand, nie negativ."""
    if reference <= 0 or cost - reference <= C.TOL:
        return 0.0
    return 100.0 * (cost - reference) / reference


def diff_percent(a: float, b: float) -> float:
    """Unterschied (a - b) in Prozent von b; innerhalb der Toleranz 0."""
    if abs(a - b) <= C.TOL or b <= 0:
        return 0.0
    return 100.0 * (a - b) / b


def share_percent(arcs) -> float:
    """Anteil zulässiger Bögen gegen die Bögen ohne Fenster in Prozent."""
    return 100.0 * arcs[0] / arcs[1] if arcs[1] else 0.0


def order_text(order) -> str:
    return " ".join(str(c) for c in order)


def routes_text(routes) -> str:
    return " ‖ ".join("(" + order_text(r) + ")" for r in routes)


def width_text(width) -> str:
    return "keine Fenster" if width is None else f"Breite {de(100 * width, 0)} %"


# ----------------------------------------------------------------------------------------------------------------------------------- Analyse

def build_tw(s: Settings) -> T.TW:
    return T.make_tw(s.n, s.family, s.depot, s.routes, s.seed, s.fill, C.LIVE_WIDTHS[s.width], C.MODE_KEYS[s.mode], s.round_windows)


def analyse(s: Settings) -> Analysis:
    tw = build_tw(s)
    free = T.without_windows(tw)
    orders = {**T.orders_of(tw), "tour_rev": T.tour_order(tw, -1)}
    return Analysis(
        s, tw, T.exact_tw(tw), orders,
        {k: T.split_tw(tw, orders[k]) for k in VIEW_KEYS},
        {k: (T.count_arcs(tw, orders[k]), T.count_arcs(free, orders[k])) for k in VIEW_KEYS},
        {k: T.greedy_tw(tw, orders[k]) for k in VIEW_KEYS},
    )


def split_gap(a: Analysis, key: str):
    """Abstand des Splits dieser Reihenfolge zum Optimum in Prozent, None wenn nicht zerlegbar."""
    sp = a.splits[key]
    return None if sp is None else gap_percent(sp.cost, a.exact.cost)


def order_view(a: Analysis, key: str, lexicographic: bool = False) -> dict:
    """Die Schritt-für-Schritt-Ansicht einer Reihenfolge: Split (optional lexikographisch), Tabelle aller Bögen, gewählter Weg, Fahrpläne."""
    order = a.orders[key]
    sp = T.split_tw(a.tw, order, lexicographic)
    table = T.arc_table(a.tw, order)
    path, pos = [], 0
    if sp is not None:
        for r in sp.routes:
            path.append((pos, pos + len(r)))
            pos += len(r)
    return {"order": order, "split": sp, "table": table, "path": path, "timelines": [] if sp is None else [T.timeline(a.tw, r) for r in sp.routes]}


def width_sweep(s: Settings) -> list[dict]:
    """Dieselbe Instanz und derselbe Bezugsplan bei allen Fensterbreiten der Regler: Optimum, Etiketten, Bögen und Abstand der Reihenfolgen."""
    rows = []
    for w, width in enumerate(C.LIVE_WIDTHS):
        a = analyse(Settings(s.n, s.family, s.depot, s.routes, s.fill, s.seed, w, s.mode, s.round_windows))
        rows.append({
            "width": width, "label": C.WIDTH_LABELS[w], "opt": a.exact.cost, "labels": a.exact.mean_labels, "max_labels": a.exact.max_labels, "states": a.exact.states,
            "orders": {k: {"cost": None if a.splits[k] is None else a.splits[k].cost, "gap": split_gap(a, k), "arcs": a.arcs[k][0], "free": a.arcs[k][1], "share": share_percent(a.arcs[k])} for k in VIEW_KEYS},
        })
    return rows


# ----------------------------------------------------------------------------------------------------------------------------------- Zeitschlupf und Dauer

def duration_of(tw: T.TW, order, sp) -> dict:
    """Wartezeit, Zeitschlupf und späte Abfahrt für die Routen des Strecken-Splits `sp` einer Reihenfolge; dazu der Dauer-Split derselben Reihenfolge (Kosten = kürzeste Dauer je Segment)."""
    if sp is None:
        return {}
    tls = [T.timeline(tw, r) for r in sp.routes]
    dur = T.split_duration(tw, order)
    return {
        "timelines": tls, "length": sp.cost, "early": sum(t.duration_early for t in tls), "late": sum(t.duration_late for t in tls), "wait": sum(t.wait for t in tls),
        "shiftable": sum(t.shift > C.TOL for t in tls), "routes": len(tls),
        "dur_cost": dur[0], "dur_routes": dur[1], "dur_length": T.plan_length(tw, dur[1]), "same_plan": sorted(dur[1]) == sorted(sp.routes),
    }


def duration_view(a: Analysis, key: str) -> dict:
    return duration_of(a.tw, a.orders[key], a.splits[key])


# ----------------------------------------------------------------------------------------------------------------------------------- Bänder

def instance_row(n: int, family: int, depot: int, seed: int, width, mode: str, ref=None, k_ref=None) -> dict:
    """Eine Zeile der Bänder: Optimum und Etiketten (bis 12 Kunden) oder die übergebene Referenz; je Reihenfolge Kosten, Bögen (mit / ohne Fenster) und Routen von „Füllen bis voll“."""
    tw = T.make_tw(n, family, depot, C.BAND_ROUTES, seed, C.BAND_FILL, width, mode)
    free = T.without_windows(tw)
    row = {"n": n, "mode": mode, "width": width, "family": family, "depot": depot, "seed": seed, "cost": {}, "arcs": {}, "greedy": {}}
    if n in C.EXACT_SIZES:
        ex = T.exact_tw(tw)
        row.update(ref=ex.cost, k_ref=len(ex.routes), labels=ex.mean_labels, max_labels=ex.max_labels, states=ex.states)
    else:
        row.update(ref=ref, k_ref=k_ref)
    for key, order in T.orders_of(tw).items():
        sp = T.split_tw(tw, order)
        row["cost"][key] = None if sp is None else sp.cost
        row["arcs"][key] = [T.count_arcs(tw, order), T.count_arcs(free, order)]
        g = T.greedy_tw(tw, order)
        row["greedy"][key] = None if g is None else len(g)
        if key == "es":
            row["routes_es"] = None if sp is None else len(sp.routes)
            if n == C.DURATION_SIZE and sp is not None:
                d = duration_of(tw, order, sp)
                row["duration"] = {k: d[k] for k in ("length", "early", "late", "wait", "shiftable", "routes", "dur_cost", "dur_length", "same_plan")}
    return row


@lru_cache(maxsize=1)
def load_bands() -> dict:
    """Vorberechnete Bänder (generate_precomputed.py); {} wenn die Datei fehlt."""
    path = Path(__file__).with_name(C.BAND_FILE)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def band_rows(n: int, mode: str, width) -> list[dict]:
    """Alle gespeicherten Instanzzeilen einer Größe, eines Bezugsplans und einer Fensterbreite, Zellen in der Reihenfolge von BAND_CELLS."""
    cell_order = {cell: i for i, cell in enumerate(C.BAND_CELLS)}
    rows = [r for r in load_bands().get("rows", []) if r["n"] == n and r["mode"] == mode and r["width"] == width]
    return sorted(rows, key=lambda r: (cell_order[(r["family"], r["depot"])], r["seed"]))


def spread(values: list[float]) -> dict:
    return {"min": min(values), "median": median(values), "mean": mean(values), "max": max(values), "hit": sum(v == 0.0 for v in values), "count": len(values)}


def paired(a: list[float], b: list[float]) -> dict:
    """Gepaarter Vergleich: a billiger / gleich / teurer als b, dazu der Median des Unterschieds in Prozent von b."""
    cheaper = sum(x < y - C.TOL for x, y in zip(a, b))
    more = sum(x > y + C.TOL for x, y in zip(a, b))
    return {"count": len(a), "cheaper": cheaper, "equal": len(a) - cheaper - more, "more": more, "median_diff": median(diff_percent(x, y) for x, y in zip(a, b)) if a else 0.0}


def band_stats(rows: list[dict]) -> dict:
    """Alle Kennzahlen einer Größe, eines Bezugsplans und einer Fensterbreite aus den gespeicherten Zeilen."""
    if not rows:
        return {}
    keys = list(C.ORDER_KEYS)
    gaps, under, undecomposable, shares, greedy = {}, {}, {}, {}, {}
    for k in keys:
        ok = [r for r in rows if r["cost"][k] is not None]
        undecomposable[k] = len(rows) - len(ok)
        gaps[k] = spread([gap_percent(r["cost"][k], r["ref"]) for r in ok]) if ok else None
        under[k] = sum(r["cost"][k] < r["ref"] - C.TOL for r in ok)
        shares[k] = median(share_percent(r["arcs"][k]) for r in rows)
        greedy[k] = median(r["greedy"][k] for r in rows if r["greedy"][k] is not None) if any(r["greedy"][k] is not None for r in rows) else None
    base = [r for r in rows if r["cost"][C.COMPARE_KEY] is not None]
    vs = {k: paired([r["cost"][k] for r in base if r["cost"][k] is not None], [r["cost"][C.COMPARE_KEY] for r in base if r["cost"][k] is not None]) for k in keys if k != C.COMPARE_KEY}
    out = {"count": len(rows), "keys": keys, "gaps": gaps, "under": under, "undecomposable": undecomposable, "shares": shares, "greedy": greedy, "vs": vs,
           "k_ref": median(r["k_ref"] for r in rows)}
    if all("labels" in r for r in rows):
        out["labels"] = {"median": median(r["labels"] for r in rows), "max": max(r["labels"] for r in rows), "max_single": max(r["max_labels"] for r in rows), "states": median(r["states"] for r in rows)}
    return out


def duration_stats(rows: list[dict]) -> dict:
    """Wartezeit, spätes Losfahren und Dauer-Split von „Einfügen nach Split“ über die Zeilen einer Größe (nur bei DURATION_SIZE Kunden gespeichert); {} ohne solche Zeilen."""
    ds = [r["duration"] for r in rows if "duration" in r]
    if not ds:
        return {}
    saving = [100.0 * (d["early"] - d["late"]) / d["early"] for d in ds]
    return {
        "count": len(ds), "wait_share": median(100.0 * d["wait"] / d["early"] for d in ds), "saving_median": median(saving), "saving_mean": mean(saving),
        "shiftable": sum(d["shiftable"] for d in ds), "routes": sum(d["routes"] for d in ds), "changed": sum(not d["same_plan"] for d in ds),
        "dur_gain": median(100.0 * (d["late"] - d["dur_cost"]) / d["late"] for d in ds), "dur_longer": median(100.0 * (d["dur_length"] - d["length"]) / d["length"] for d in ds),
    }


# ----------------------------------------------------------------------------------------------------------------------------------- Verdikte

def verdict_compare(a: Analysis) -> tuple[str, str]:
    """Kernfrage: Was machen die Fenster mit dem Split der kürzesten Rundreise, und was rettet die Reihenfolge?"""
    s, ref = a.settings, a.exact.cost
    width = C.LIVE_WIDTHS[s.width]
    tour, es = a.splits["tour"], a.splits["es"]
    tour_part = "ist nicht zerlegbar" if tour is None else f"kostet {de(tour.cost)} ({pct(split_gap(a, 'tour'))} über dem Optimum)"
    es_part = "ist nicht zerlegbar" if es is None else f"kostet {de(es.cost)} ({pct(split_gap(a, 'es'))} über dem Optimum)"
    head = f"{width_text(width)[0].upper() + width_text(width)[1:]}, Optimum {de(ref)} mit {routes_word(len(a.exact.routes))}. "
    if width is None:
        return "info", head + (f"Ohne Fenster ist es der Split aus Stück 3: Split der kürzesten Rundreise {tour_part}, Einfügen nach Split {es_part}. "
                               f"Es bleiben alle {a.arcs['tour'][1]} Bögen; die Fenster fehlen.")
    share = share_percent(a.arcs["tour"])
    text = (head + f"Der Split der kürzesten Rundreise nutzt {a.arcs['tour'][0]} von {a.arcs['tour'][1]} Bögen ({pct(share, 0)}) und {tour_part}; "
            f"Einfügen nach Split {es_part} bei {a.arcs['es'][0]} von {a.arcs['es'][1]} Bögen.")
    gap_t = split_gap(a, "tour")
    if tour is None:
        return "error", text
    return ("warning" if gap_t is not None and gap_t > C.GAP_WARN else "success"), text


def verdict_split(a: Analysis, key: str, view: dict, lexicographic: bool) -> tuple[str, str]:
    """Verdikt zur Schritt-für-Schritt-Ansicht einer Reihenfolge."""
    name = VIEW_NAMES[key]
    sp = view["split"]
    ok, free = a.arcs[key]
    if sp is None:
        return "error", f"{name}: nicht zerlegbar. Mindestens ein Kunde ist in dieser Reihenfolge allein nicht zulässig erreichbar (Last oder Fenster)."
    gap = gap_percent(sp.cost, a.exact.cost)
    text = f"{name}: {de(sp.cost)} mit {routes_word(len(sp.routes))}, {pct(gap)} über dem Optimum {de(a.exact.cost)}; {ok} von {free} Bögen zulässig ({pct(share_percent((ok, free)), 0)})."
    if lexicographic:
        text += " Lexikographisch: erst die kleinste Routenzahl, dann die kürzeste Strecke."
    if share_percent((ok, free)) < C.ARC_LOW:
        return "warning", text + f" Die Fenster sind für diese Reihenfolge zu eng: weniger als {de(C.ARC_LOW, 0)} % der Bögen bleiben."
    return ("warning" if gap > C.GAP_WARN else "success"), text


def verdict_shrink(rows: list[dict]) -> tuple[str, str]:
    """Der Hilfsgraph schrumpft mit engeren Fenstern; Abstand und Etiketten über die Breiten."""
    narrow, wide = rows[0], rows[-2]            # 5 % und 40 % (die letzte Zeile ist „keine Fenster“)
    t_n, t_w = narrow["orders"]["tour"], wide["orders"]["tour"]
    es_n = narrow["orders"]["es"]
    parts = [f"Anteil zulässiger Bögen der kürzesten Rundreise: {pct(t_w['share'], 0)} bei Breite {wide['label']}, {pct(t_n['share'], 0)} bei {narrow['label']} (ohne Fenster 100 %)."]
    if t_n["gap"] is not None and t_w["gap"] is not None:
        parts.append(f"Abstand der kürzesten Rundreise zum Optimum: {pct(t_w['gap'])} bei {wide['label']}, {pct(t_n['gap'])} bei {narrow['label']}; Einfügen nach Split {pct(es_n['gap']) if es_n['gap'] is not None else 'nicht zerlegbar'} bei {narrow['label']}.")
    kind = "info"
    if t_n["gap"] is not None and t_n["gap"] > C.GAP_WARN:
        kind = "warning"
    return kind, " ".join(parts) + " Ein kleiner Graph heißt nicht, dass der Plan gut ist: die Reihenfolge entscheidet."


def verdict_directions(a: Analysis, rows: list[dict]) -> tuple[str, str]:
    """Rundreise vorwärts gegen rückwärts: dieselbe Länge, aber andere Zeiten."""
    f, b = rows[0], rows[1]
    if f["split"] is None or b["split"] is None:
        who = "vorwärts" if f["split"] is None else "rückwärts"
        return "warning", f"Die kürzeste Rundreise ist {who} gelesen nicht zerlegbar; in der anderen Richtung geht es."
    diff = diff_percent(f["split"].cost, b["split"].cost)
    word = "gleich teuer" if abs(f["split"].cost - b["split"].cost) <= C.TOL else ("vorwärts billiger" if f["split"].cost < b["split"].cost else "rückwärts billiger")
    return ("info" if abs(diff) < C.LEVEL_PP else "warning"), (
        f"Dieselbe Rundreise (Länge {de(A.tsp_tour(a.tw.inst)[0])}) hat vorwärts den Split {de(f['split'].cost)}, rückwärts {de(b['split'].cost)}: {word} "
        f"({signed_pct(diff)}). Die Richtung durch die Fenster zählt, nicht die Länge der Rundreise.")


def verdict_labels(rows: list[dict]) -> tuple[str, str]:
    """Etiketten im exakten Löser über die Breiten (Hypothese des Fachkanons: die Zahl wächst mit den Fenstern)."""
    labelled = [r for r in rows if r["width"] is not None]
    biggest = max(labelled, key=lambda r: r["labels"])
    free = rows[-1]
    return "info", (f"Im exakten Löser liegt die mittlere Zahl der Pareto-Etiketten je Zustand zwischen {de(min(r['labels'] for r in rows))} und {de(max(r['labels'] for r in rows))} "
                    f"(ohne Fenster {de(free['labels'])}); am größten bei Breite {biggest['label']} mit {de(biggest['labels'])}, höchstens {biggest['max_labels']} Etiketten in einem Zustand. "
                    f"Der Split selbst braucht keine: die Reihenfolge legt die Zeit fest, Warten kostet nichts, und die früheste Abfahrt ist immer richtig.")


def verdict_duration(v: dict, key_name: str) -> tuple[str, str]:
    if not v:
        return "error", "Diese Reihenfolge ist nicht zerlegbar; es gibt keinen Fahrplan."
    saved = 100.0 * (v["early"] - v["late"]) / v["early"] if v["early"] else 0.0
    text = (f"{key_name}: Wartezeit {de(v['wait'])} von {de(v['early'])} Gesamtdauer; mit spätem Losfahren {de(v['late'])} ({pct(saved)} weniger); {v['shiftable']} von {v['routes']} Routen lassen sich verschieben. "
            f"Der Dauer-Split dieser Reihenfolge hat Dauer {de(v['dur_cost'])} und Strecke {de(v['dur_length'])} gegen Strecken-Split mit Strecke {de(v['length'])}: "
            + ("derselbe Plan." if v["same_plan"] else "ein anderer Plan."))
    return "info", text


def _gap_part(name: str, s) -> str:
    if s is None:
        return f"{name}: nicht zerlegbar"
    return f"{name} {pct(s['median'])} (Mittel {pct(s['mean'])}, Maximum {pct(s['max'])})"


def verdict_bands(n: int, mode: str, width, stats: dict) -> tuple[str, str]:
    """Bänder: Median der Verfahren und Anteil der Bögen."""
    if not stats:
        return "warning", "Für diese Auswahl liegen keine Bänder vor."
    ref = "Optimum" if n in C.EXACT_SIZES else "Referenz (PyVRP)"
    parts = [_gap_part(C.ORDER_NAMES[k], stats["gaps"][k]) for k in ("tour", "es")]
    text = (f"{instances_word(stats['count'])}, {width_text(width)}, {C.MODES[C.MODE_KEYS.index(mode)]}, {n} Kunden, Abstand zum {ref}: " + "; ".join(parts) + ". "
            f"Zulässige Bögen der Rundreise im Median {pct(stats['shares']['tour'], 0)}, von Einfügen nach Split {pct(stats['shares']['es'], 0)}.")
    gap_t = stats["gaps"]["tour"]
    kind = "warning" if gap_t is not None and gap_t["median"] > C.GAP_WARN else "info"
    if n not in C.EXACT_SIZES:
        text += " Die Referenz ist keine bewiesene Untergrenze."
    return kind, text


def verdict_under(stats: dict) -> tuple[str, str]:
    if not stats or stats["count"] == 0:
        return "info", ""
    under = {k: v for k, v in stats["under"].items() if v}
    if not under:
        return "info", "Kein Verfahren liegt in dieser Auswahl unter der Referenz."
    text = ", ".join(f"{C.ORDER_NAMES[k]}: {v} von {stats['count']}" for k, v in under.items())
    return "info", f"Unter der Referenz liegen: {text}. Die Referenz ist also keine Untergrenze; sie ist die beste bekannte Lösung dieses Laufs."


def verdict_band_labels(stats: dict) -> tuple[str, str]:
    if not stats or "labels" not in stats:
        return "info", ""
    lab = stats["labels"]
    return "info", (f"Pareto-Etiketten je Zustand im exakten Löser: Median der Instanzen {de(lab['median'])}, größter Mittelwert einer Instanz {de(lab['max'])}, "
                    f"größte Zahl in einem einzelnen Zustand {lab['max_single']}; erreichte Zustände im Median {de(lab['states'], 0)}.")


def verdict_band_duration(n: int, mode: str, width, stats: dict) -> tuple[str, str]:
    """Warten und späte Abfahrt über die gespeicherten Instanzen (nur bei DURATION_SIZE Kunden)."""
    if not stats:
        return "info", ""
    return "info", (f"Warten und spätes Losfahren ({n} Kunden, {width_text(width)}, Plan „Einfügen nach Split“, {instances_word(stats['count'])}): Wartezeit im Median {pct(stats['wait_share'])} der Gesamtdauer; "
                    f"spätes Losfahren spart im Median {pct(stats['saving_median'])} der Dauer (Mittel {pct(stats['saving_mean'])}); {stats['shiftable']} von {stats['routes']} Routen lassen sich verschieben. "
                    f"Der Dauer-Split ändert den Plan in {stats['changed']} von {stats['count']} Instanzen; seine Dauer liegt im Median {pct(stats['dur_gain'], 2)} unter der späten Dauer des Strecken-Splits, "
                    f"seine Strecke {pct(stats['dur_longer'], 2)} über dessen Strecke.")
