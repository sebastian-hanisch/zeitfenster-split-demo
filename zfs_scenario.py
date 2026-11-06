"""Szenario (aus riesentour-split-demo, Stück 1 der Linie, kopiert, umbenannt und um die Auslastung als Parameter ergänzt): ein Depot, n Kunden mit Nachfrage, eine Fahrzeugkapazität, euklidische Entfernungen. Alles simuliert.

Index 0 ist das Depot, die Kunden heißen 1 bis n. Die Instanz ist hashbar (Tupel), damit Streamlit sie cachen kann."""

from dataclasses import dataclass
from functools import lru_cache
import math

import numpy as np

import zfs_constants as C


@dataclass(frozen=True)
class Instance:
    xy: tuple[tuple[float, float], ...]   # xy[0] = Depot, xy[i] = Kunde i
    demand: tuple[int, ...]               # demand[i - 1] = Nachfrage von Kunde i
    capacity: int

    @property
    def n(self) -> int:
        return len(self.demand)

    def load(self, customers) -> int:
        return sum(self.demand[c - 1] for c in customers)

    @property
    def min_routes(self) -> int:
        return math.ceil(sum(self.demand) / self.capacity)


@lru_cache(maxsize=512)
def distance_matrix(inst: Instance) -> np.ndarray:
    pts = np.array(inst.xy, dtype=float)
    return np.sqrt(((pts[:, None, :] - pts[None, :, :]) ** 2).sum(-1))


def make_instance(n: int, family: int, depot: int, routes: int, seed: int, fill_pct: int = 90) -> Instance:
    """Deterministisch aus (n, Familie, Depotlage, Zielroutenzahl, Seed): gleiche Eingabe, gleiche Instanz.

    Familie 0: ganze Koordinaten 0 bis 16, Nachfragen 1 bis 4; 1: gleichverteilt 0 bis 100 (eine Nachkommastelle), Nachfragen 1 bis 10;
    2: drei Häufungen (Streuung 7) um zufällige Mittelpunkte, Nachfragen 1 bis 10. Kapazität: Gesamtnachfrage geteilt durch (Zielroutenzahl mal Auslastung), die Auslastung in Prozent (Voreinstellung 90),
    aufgerundet, mindestens die größte Nachfrage; die Mindestroutenzahl ist also meist die Zielroutenzahl."""
    rng = np.random.default_rng(seed)
    key = C.FAMILY_KEYS[family]
    if key == "small":
        pts = rng.integers(0, 17, size=(n, 2)).astype(float)
        dem = rng.integers(1, 5, size=n)
        center, corner = (8.0, 8.0), (0.0, 0.0)
    else:
        if key == "random":
            pts = rng.uniform(0, 100, size=(n, 2))
        else:
            centers = rng.uniform(15, 85, size=(C.CLUSTERS, 2))
            label = rng.integers(0, C.CLUSTERS, size=n)
            pts = np.clip(centers[label] + rng.normal(0, C.CLUSTER_SIGMA, size=(n, 2)), 0, 100)
        pts = np.round(pts, 1)
        dem = rng.integers(1, 11, size=n)
        center, corner = (50.0, 50.0), (0.0, 0.0)
    dep = center if depot == 0 else corner
    capacity = max(int(math.ceil(dem.sum() / (routes * (fill_pct / 100)))), int(dem.max()))
    xy = ((dep[0], dep[1]),) + tuple((float(x), float(y)) for x, y in pts)
    return Instance(xy, tuple(int(d) for d in dem), capacity)
