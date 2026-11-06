"""Konstanten: Regler-Grenzen, feste Annahmen, Farben und Presets."""

N_MIN, N_MAX, DEFAULT_N = 6, 12, 6
SEED_MAX, DEFAULT_SEED = 999999, 0
ROUTES_MIN, ROUTES_MAX, DEFAULT_ROUTES = 2, 4, 2
FILL_MIN, FILL_MAX, FILL_STEP, DEFAULT_FILL = 60, 100, 2, 90   # Auslastung in Prozent: Kapazität = aufgerundet Gesamtnachfrage / (Zielroutenzahl · Auslastung)
CLUSTERS, CLUSTER_SIGMA = 3, 7.0              # Familie „In Gruppen“
FAMILIES = ("Kleine Karte (ganze Zahlen)", "Zufällig verteilt (0 bis 100)", "In Gruppen (0 bis 100)")
FAMILY_KEYS = ("small", "random", "clustered")
DEFAULT_FAMILY = 0
DEPOTS = ("In der Mitte", "In der Ecke")
DEFAULT_DEPOT = 0

# Zeitfenster
SERVICE = 10.0                                # Bedienzeit je Kunde; Fahrzeit = Entfernung
LIVE_WIDTHS = (0.05, 0.1, 0.2, 0.3, 0.4, None)  # Fensterbreite als Anteil des Horizonts H; None = [0, H] (keine Fenster)
WIDTH_LABELS = ("5 %", "10 %", "20 %", "30 %", "40 %", "keine")
DEFAULT_WIDTH = 3
MODES = ("Zufälliger Plan", "Geografischer Plan")   # Bezugsplan, um dessen Ankunftszeiten die Fenster liegen
MODE_KEYS = ("random", "geo")
DEFAULT_MODE = 0
DEFAULT_ROUND = True                          # Fenster auf ganze Zahlen runden (Handrechnung)
TOL = 1e-9                                    # Gleichstände und Gleichheit von Kosten: absolut
GAP_WARN = 5.0                                # Abstand in Prozent, ab dem das Verdikt warnt
LEVEL_PP = 1.0                                # „gleichauf“: Unterschied der Mediane unter einem Prozentpunkt
ARC_LOW = 30.0                                # Anteil zulässiger Bögen in Prozent, unter dem das Verdikt „Fenster zu eng für diese Reihenfolge“ sagt

# Reihenfolgen im Vergleich
ORDER_KEYS = ("tour", "angle", "late", "random", "es")
ORDER_NAMES = {
    "tour": "Kürzeste Rundreise",
    "angle": "Winkelfolge",
    "late": "Fensterende",
    "random": "Zufall",
    "es": "Einfügen nach Split",
}
COMPARE_KEY = "tour"                          # die gepaarten Zählungen der Bänder vergleichen mit Rundreise + Split

# Bänder (vorberechnet, zfs_bands.json): feste Instanzen, vier Zellen (Kunden zufällig/Gruppen mal Depot Mitte/Ecke), je Bezugsplan und Fensterbreite
BAND_FILE = "zfs_bands.json"
REFS_FILE = "zfs_refs.json"                   # PyVRP-Referenzen für 25 und 50 Kunden (einmal gerechnet, siehe generate_precomputed.py)
BAND_SIZES = (10, 12, 25, 50)
BAND_WIDTHS = (0.05, 0.1, 0.2, 0.4, None)
BAND_CELLS = ((1, 0), (2, 0), (1, 1), (2, 1))
BAND_ROUTES, BAND_FILL = 3, 90
EXACT_SIZES = (10, 12)                        # Referenz = exaktes Optimum; sonst PyVRP (5 s, ein Seed)
BAND_SEEDS = {10: tuple(range(300000, 300020)), 12: tuple(range(300000, 300008)), 25: tuple(range(300000, 300008)), 50: tuple(range(300000, 300008))}
PYVRP_SECONDS, PYVRP_SEED, PYVRP_SCALE = 5, 1, 100
DURATION_SIZE = 10                            # bei dieser Größe stehen in den Zeilen Wartezeit, späte Abfahrt und Dauer-Split von „Einfügen nach Split“

COLOR_OPT = "#c0504d"
ROUTE_COLORS = ("#2F6B65", "#c0504d", "#4c78a8", "#d8a13a", "#7b5ea7", "#8c564b", "#17becf", "#e377c2")
ORDER_COLORS = {"tour": "#2F6B65", "angle": "#d8a13a", "late": "#999999", "random": "#c9a98a", "es": "#4c78a8"}
ARC_COLORS = {"ok": "#2F6B65", "load": "#bdbdbd", "window": "#c0504d", "return": "#d8a13a"}
ARC_TEXT = {"ok": "zulässig", "load": "Last über der Kapazität", "window": "ein Fenster geschlossen", "return": "Rückkehr nach H"}

# Presets (die Zahlen in den Hilfetexten prüft tests/test_claims.py); das erste ist die Voreinstellung
PRESETS = {
    "Die Richtung zählt (n = 6, Handrechnung)": {"n": 6, "family": 0, "depot": 0, "routes": 2, "fill": 90, "seed": 0, "width": 3, "mode": 0, "round": 0},
    "Enge Fenster: die Rundreise versagt (n = 8, Depot in der Ecke)": {"n": 8, "family": 1, "depot": 1, "routes": 3, "fill": 90, "seed": 23, "width": 1, "mode": 1, "round": 1},
    "Ohne Fenster: der Split aus Stück 3 (n = 8, Depot in der Ecke)": {"n": 8, "family": 1, "depot": 1, "routes": 3, "fill": 90, "seed": 23, "width": 5, "mode": 1, "round": 1},
    "Mehrere Etiketten je Zustand (n = 12)": {"n": 12, "family": 2, "depot": 1, "routes": 3, "fill": 90, "seed": 300004, "width": 4, "mode": 0, "round": 1},
    "Spätes Losfahren ändert den Plan (n = 10)": {"n": 10, "family": 1, "depot": 0, "routes": 3, "fill": 90, "seed": 18, "width": 2, "mode": 0, "round": 1},
}
PRESET_HELP = {
    "Die Richtung zählt (n = 6, Handrechnung)": "Von Hand nachrechenbar (Fenster auf ganze Zahlen): Die kürzeste Rundreise 1 6 5 4 3 2 käme bei Kunde 3 um 24,63 an, das Fenster schließt um 24; das Segment (4 3 2) fehlt. Der Split kostet 67,99 (+26,4 %) mit (1 6 5), (4), (3 2); das Optimum 53,79 fährt (1 6 5) und (3 4 2). Rückwärts gelesen kostet die Rundreise 61,16; Einfügen nach Split trifft das Optimum.",
    "Enge Fenster: die Rundreise versagt (n = 8, Depot in der Ecke)": "Fenster 10 % von H um das Optimum. Das Optimum 412,35 hat 3 Routen. Der Split der kürzesten Rundreise kostet 933,73 (+126,4 %, 7 Routen, 9 von 18 Bögen), rückwärts gelesen 517,11 (+25,4 %); Einfügen nach Split trifft das Optimum bei 16 von 21 Bögen.",
    "Ohne Fenster: der Split aus Stück 3 (n = 8, Depot in der Ecke)": "Dieselbe Karte ohne Fenster ([0, H] für alle): alle 18 Bögen sind da, die Rundreise liegt 17,1 % über dem Optimum 412,35 (4 Routen), Einfügen nach Split trifft es. Beide Richtungen der Rundreise sind gleich teuer.",
    "Mehrere Etiketten je Zustand (n = 12)": "Fenster 40 % von H um einen zufälligen Plan. Der exakte Löser braucht im Mittel 1,54 Etiketten je Zustand, höchstens 5 in einem Zustand; das Optimum 344,48 hat 3 Routen, der Split der Rundreise liegt 57,1 % darüber, Einfügen nach Split trifft es.",
    "Spätes Losfahren ändert den Plan (n = 10)": "Fenster 20 % von H um einen zufälligen Plan. Einfügen nach Split fährt 4 Routen mit 216,38 Wartezeit von 734,38 Gesamtdauer; spätes Losfahren spart 20,1 % der Dauer (586,44). Der Dauer-Split derselben Reihenfolge fährt 5 Routen: Dauer 576,90 bei Strecke 463,27 statt 418,00.",
}

# Text des Expanders „Annahmen, Grenzen und bekannte Probleme“; derselbe Text steht in der README (tests/test_readme.py vergleicht beide)
ASSUMPTIONS_MARKDOWN = """**Annahmen**
- Ein Depot, beliebig viele gleiche Fahrzeuge (die Flottengrenze fehlt), euklidische und symmetrische Entfernungen; Fahrzeit gleich Entfernung, Bedienzeit 10 je Kunde, Abfahrt aller Fahrzeuge zur Zeit 0, Rückkehr bis H. Jeder Kunde wird genau einmal von einem Fahrzeug bedient, seine Nachfrage ist nicht teilbar. Kosten sind die gefahrene Strecke; Warten kostet nichts.
- Alles ist simuliert: Karten aus Zufallszahlen, kein Straßennetz, keine echten Aufträge. Die Fenster sind erzeugt: Breite = Anteil von H um die Ankunftszeiten eines Bezugsplans (zufälliger Plan: „Füllen bis voll“ auf einer Zufallsfolge; geografischer Plan: das Optimum ohne Fenster bis 12 Kunden, darüber Savings); H = 1,25 mal die späteste Rückkehr des Bezugsplans. So ist jede Instanz lösbar. Echte Fenster liegen anders.
- „Kürzeste Rundreise“ ist exakt bis 12 Kunden, darüber eine Heuristik (2-opt und Or-opt ab der Winkelfolge, nie unter der kürzesten Rundreise). „Einfügen nach Split“ fügt die Kunden in absteigender Entfernung vom Depot an der Stelle mit den kleinsten Split-Kosten mit Fenstern ein.

**Grenzen**
- Live rechnet die App bis zu 12 Kunden mit exaktem Optimum. Die Bänder gelten für 10 Kunden (80 feste Instanzen je Bezugsplan und Fensterbreite) und für 12, 25 und 50 Kunden (je 32) bei drei Zielrouten, 90 % Auslastung, nicht gerundeten Fenstern und fünf Fensterbreiten (5, 10, 20, 40 % und keine) für beide Bezugspläne.
- Die Referenz PyVRP 0.14.1 (5 Sekunden, ein Seed, Version fest) ist eine gute Lösung, keine Untergrenze: einzelne Reihenfolgen liegen darunter, Abstände zur Referenz sind keine Abstände zum Optimum. Die Referenzen stehen in `zfs_refs.json`; die Tests rechnen PyVRP nicht.
- Der Split ist optimal für die gegebene Reihenfolge, nicht für das Problem. Savings mit Zeitfenstern, Dauer als Ziel, Solomon-Instanzen und Suche sind nicht gebaut (Stücke 9 und 11 der Reihe).
- Der Zeitschlupf ist ein Fahrplanwerkzeug (Experiment 4); als Zielfunktion steht nur der Schalter „Dauer-Split“ derselben Reihenfolge.

**Bekannte Probleme und Unsicherheiten**
- Die Bänder sind Spannen über feste Instanzen, keine Trends und keine Aussagen über andere Kartenarten, Zielroutenzahlen oder echte Fenster.
- Die Fachkanon-Hypothese, die Etikettenzahl wachse mit den Zeitfenstern, ist an diesen Instanzen nicht bestätigt (Mittel höchstens 1,54 je Zustand); das gilt für diese Erzeugung der Fenster und bis 12 Kunden.
- Bei gleichen Kosten entscheidet die Regel „kleinster Startknoten des letzten Bogens“ (Split) und „kleinste Stelle“ (Einfügen); andere Regeln ergeben andere, gleich teure Pläne.
- Die Rechenzeiten (Größenordnung) sind eine Messung unter Windows, nicht festgeschrieben.
- Die Diagramme wurden im Browser nur angesehen und per Rauchtest bedient, nicht mit echtem Mausklick auf einzelne Punkte geprüft."""
