"""Erzeugt zfs_bands.json: die Bänder über feste Instanzen (Split der Reihenfolgen Rundreise, Winkelfolge, Fensterende, Zufall und Einfügen nach Split mit Zeitfenstern).

Je Größe (10, 12, 25, 50 Kunden), Bezugsplan (zufällig, geografisch) und Fensterbreite (5, 10, 20, 40 % und keine) rechnet dieses Skript vier Zellen (Kunden zufällig oder in Gruppen, Depot in der Mitte
oder in der Ecke) mal 20 Seeds (10 Kunden) oder 8 Seeds (sonst). Bis 12 Kunden ist die Referenz das exakte Optimum (Held-Karp mit Pareto-Etiketten); bei 25 und 50 Kunden steht die Referenz PyVRP in
zfs_refs.json (einmal gerechnet mit `refs`, 5 Sekunden je Instanz, ein Seed; ein Lauf für 25 Kunden dauert rund 15 Minuten, für 50 Kunden rund 28 Minuten je Bezugsplan).

Aufruf (Teile können parallel laufen):
    python generate_precomputed.py rows 12 geo --out part_12_geo.json       # Größe, Bezugsplan
    python generate_precomputed.py merge part_*.json                       # zu zfs_bands.json zusammenführen
    python generate_precomputed.py refs 25 geo                              # nur mit installiertem PyVRP 0.14.1: Referenzen berechnen und in zfs_refs.json eintragen"""

import argparse
import importlib
import json
import time
from pathlib import Path

import zfs_constants as C
import zfs_timewindows as T
from zfs_evaluation import instance_row

TARGET = Path(__file__).with_name(C.BAND_FILE)
REFS = Path(__file__).with_name(C.REFS_FILE)


def ref_key(n, mode, width, family, depot, seed) -> str:
    return f"{n}|{mode}|{width}|{family}|{depot}|{seed}"


def load_refs() -> dict:
    return json.loads(REFS.read_text(encoding="utf-8"))["refs"] if REFS.exists() else {}


def pyvrp_ref(tw: T.TW):
    """Referenz PyVRP (Strecke, Routenzahl; None bei unzulässigem Ergebnis)."""
    mod, stop = importlib.import_module("pyvrp"), importlib.import_module("pyvrp.stop")
    inst, scale = tw.inst, C.PYVRP_SCALE
    m = mod.Model()
    locs = [m.add_location(x=x * scale, y=y * scale) for x, y in inst.xy]
    horizon = int(round(tw.horizon * scale))
    m.add_depot(location=locs[0], tw_early=0, tw_late=horizon)
    m.add_vehicle_type(num_available=inst.n, capacity=[inst.capacity], tw_early=0, tw_late=horizon)
    for c in range(1, inst.n + 1):
        m.add_client(location=locs[c], delivery=[inst.demand[c - 1]], service_duration=int(round(tw.service * scale)), tw_early=int(round(tw.early[c] * scale)), tw_late=int(round(tw.late[c] * scale)))
    for i in range(inst.n + 1):
        for j in range(inst.n + 1):
            if i != j:
                d = int(round(tw.D[i][j] * scale))
                m.add_edge(locs[i], locs[j], distance=d, duration=d)
    best = m.solve(stop=stop.MaxRuntime(C.PYVRP_SECONDS), seed=C.PYVRP_SEED, display=False).best
    return (best.distance() / scale if best.is_feasible() else None), best.num_routes()


def build_rows(n: int, mode: str) -> list[dict]:
    refs, rows, start = load_refs(), [], time.time()
    for width in C.BAND_WIDTHS:
        for family, depot in C.BAND_CELLS:
            for seed in C.BAND_SEEDS[n]:
                ref = k_ref = None
                if n not in C.EXACT_SIZES:
                    ref, k_ref = refs[ref_key(n, mode, width, family, depot, seed)]
                rows.append(instance_row(n, family, depot, seed, width, mode, ref, k_ref))
        print("rows", n, mode, width, f"{time.time() - start:.0f} s", flush=True)
    return rows


def compute_refs(n: int, mode: str) -> None:
    data = json.loads(REFS.read_text(encoding="utf-8")) if REFS.exists() else {"meta": {}, "refs": {}}
    for width in C.BAND_WIDTHS:
        for family, depot in C.BAND_CELLS:
            for seed in C.BAND_SEEDS[n]:
                tw = T.make_tw(n, family, depot, C.BAND_ROUTES, seed, C.BAND_FILL, width, mode)
                data["refs"][ref_key(n, mode, width, family, depot, seed)] = list(pyvrp_ref(tw))
        print("refs", n, mode, width, flush=True)
    REFS.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["rows", "merge", "refs"])
    ap.add_argument("args", nargs="+")
    ap.add_argument("--out")
    args = ap.parse_args()
    if args.kind == "merge":
        rows = []
        for f in args.args:
            rows += json.loads(Path(f).read_text(encoding="utf-8"))["rows"]
        rows.sort(key=lambda r: (r["n"], r["mode"], -1 if r["width"] is None else r["width"], r["family"], r["depot"], r["seed"]))
        meta = {"seeds": {str(n): [s[0], s[-1]] for n, s in C.BAND_SEEDS.items()}, "widths": [w for w in C.BAND_WIDTHS], "exact_max": 12,
                "source": f"Instanzen aus make_tw; Referenz bis 12 Kunden das exakte Optimum, darüber PyVRP aus {C.REFS_FILE}"}
        TARGET.write_text(json.dumps({"meta": meta, "rows": rows}, ensure_ascii=False), encoding="utf-8")
        print("geschrieben:", TARGET.name, len(rows), "Zeilen")
    elif args.kind == "refs":
        compute_refs(int(args.args[0]), args.args[1])
    else:
        Path(args.out).write_text(json.dumps({"rows": build_rows(int(args.args[0]), args.args[1])}, ensure_ascii=False), encoding="utf-8")
        print("geschrieben:", args.out)
