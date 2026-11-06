# Zeitfenster und Split – Streamlit-Demo

<!-- TODO nach dem Deploy: direkt hierher den Live-Link setzen (Leerzeile davor und danach):
**[→ Demo live ausprobieren](https://sebastianhanisch-zeitfenster-split-demo.streamlit.app/)** -->

Achtes Stück der **Tourenbildung**-Linie in der „Konzepte“-Reihe für die Website „Sebastian Hanisch – Operations Research und Machine Learning“ (Verfahren: **Riesentour und Split**, ein Verfahren mit wachsendem Beispiel). Stück 1 ([riesentour-split-demo](https://github.com/sebastian-hanisch/riesentour-split-demo)) zeigt, dass eine Reihenfolge aller Kunden genügt, weil der **Split** sie optimal in Routen zerlegt; Stück 2 ([riesentouren-erzeugen-demo](https://github.com/sebastian-hanisch/riesentouren-erzeugen-demo)) baut solche Reihenfolgen, Stück 3 ([split-gegen-fuellen-demo](https://github.com/sebastian-hanisch/split-gegen-fuellen-demo)) vergleicht den Split mit „Füllen bis voll“, Stück 4 ([savings-gegen-split-demo](https://github.com/sebastian-hanisch/savings-gegen-split-demo)) und Stück 5 ([savings-varianten-demo](https://github.com/sebastian-hanisch/savings-varianten-demo)) legen Routen zusammen, Stück 6 ([sweep-cluster-first-demo](https://github.com/sebastian-hanisch/sweep-cluster-first-demo)) bildet erst Gruppen. Dieses Stück fragt: **Was ändert sich am Split, wenn jeder Kunde ein Zeitfenster hat?** (Stück 7 ist ein optionales Stück und wurde nicht gebaut.)

## Kernfrage

Wächst der Hilfsgraph des Splits, wenn Zeitfenster dazukommen, und was entscheidet dann über den Plan? Die Demo zeigt den Hilfsgraphen mit Fenstern Schritt für Schritt (welche Bögen fehlen und warum), wie er mit engeren Fenstern **schrumpft**, warum die **Richtung** der Riesentour zählt, was Pareto-Etiketten im exakten Löser und der Zeitschlupf (späteres Losfahren) bringen und wie sich fünf Reihenfolgen (kürzeste Rundreise, Winkelfolge, Fensterende, Zufall, Einfügen nach Split) schlagen, live bis 12 Kunden gegen das exakte Optimum und in vorberechneten Bändern bis 50 Kunden gegen PyVRP.

## Modell

Wie in den Stücken 1 bis 6: ein Depot, n Kunden mit ganzzahliger Nachfrage, gleiche Fahrzeuge der Kapazität Q (ohne Flottengrenze), euklidische Entfernungen; die Kapazität folgt aus der **Auslastung** (aufgerundet Gesamtnachfrage geteilt durch Zielroutenzahl mal Auslastung, mindestens die größte Nachfrage). **Neu:** Fahrzeit gleich Entfernung, Bedienzeit 10 je Kunde, Zeitfenster [e, l] (wer vor e ankommt, wartet kostenlos; nach l geht es nicht), Abfahrt aller Fahrzeuge zur Zeit 0, Rückkehr bis H; Kosten sind die gefahrene Strecke. **Fenster:** um die Ankunftszeiten eines **Bezugsplans** gelegt (zufälliger Plan: „Füllen bis voll“ auf einer Zufallsfolge; geografischer Plan: das Optimum ohne Fenster bis 12 Kunden, darüber Savings), Breite gleich Anteil von H (H gleich 1,25 mal die späteste Rückkehr des Bezugsplans); so hat jede Instanz mindestens einen zulässigen Plan. **Bogen:** das Segment „Kunden i+1 bis j der Riesentour“ ist ein Bogen, wenn Last, alle Fenster und die Rückkehr bis H gehalten werden; beim Verlängern genügt eine O(1)-Prüfung der Ankunftszeit, und scheitert sie, scheitern alle längeren Segmente ebenfalls. **Split:** kürzester Weg im azyklischen Hilfsgraphen, optional lexikographisch (Routenzahl, dann Strecke). **Exaktes Optimum:** je Kundenmenge die kürzeste zulässige Route (Held–Karp mit Pareto-Etiketten (Strecke, Zeit)), dann Mengenzerlegung. **Zeitschlupf:** um wie viel sich die Abfahrt verschieben lässt, ohne ein Fenster zu verletzen (nach Savelsbergh); nutzbar ist das Minimum aus Schlupf und Wartezeit. Formeln stehen im 📐-Expander der App.

## Methodik

- **Kern** (`zfs_algorithm.py`, `zfs_scenario.py`, `zfs_routing.py`, `zfs_savings.py`): aus den Stücken 1 und 6 kopiert und umbenannt (Split ohne Fenster, Held–Karp, kürzeste Rundreise, Winkelfolge, Savings als Bezugsplan ab 25 Kunden).
- **Zeitfenster** (`zfs_timewindows.py`): neu: Erzeugung der Fenster, Zulässigkeitsprüfung, Split mit Fenstern (optional lexikographisch), Bogentabelle mit Gründen, längste zulässige Segmente, „Füllen bis voll“ mit Fenstern, Reihenfolgen (Rundreise, Winkelfolge, Fensterende, Zufall, Einfügen nach Split), exaktes Optimum mit Pareto-Etiketten, Fahrplan, Zeitschlupf, Dauer-Split.
- **Fünf Experimente:** der Split mit Fenstern Schritt für Schritt (Bogenmatrix, Fahrplan); wie viel schrumpft der Graph; die Richtung zählt; Etiketten, Warten und Zeitschlupf; Bänder über feste Instanzen.
- **Bänder** (`zfs_bands.json`, erzeugt von `generate_precomputed.py`): vier Zellen (Kunden zufällig oder in Gruppen, Depot in der Mitte oder in der Ecke) mal 20 Seeds (n = 10, also 80 Instanzen) oder 8 Seeds (n = 12, 25, 50, also je 32), drei Zielrouten, Auslastung 90 %, beide Bezugspläne, fünf Fensterbreiten (5, 10, 20, 40 % und keine), nicht gerundete Fenster. Bis n = 12 ist die Referenz das exakte Optimum, bei n = 25 und 50 die Referenz PyVRP 0.14.1 aus `zfs_refs.json` (5 Sekunden je Instanz, ein Seed, einmal gerechnet; die Tests rechnen PyVRP nicht).

## Befunde (gemessen, keine Behauptungen)

Alle Zahlen sind Messungen an festen Seeds (Abstand zum Optimum beziehungsweise zur PyVRP-Referenz in Prozent, Median über die Instanzen; „gepaart“ heißt Einfügen nach Split billiger / gleich / teurer als die Rundreise auf denselben Instanzen; vier Zellen zusammen), nachgerechnet in `tests/test_claims.py` und `tests/test_bands.py`. Fensterbreite 5 / 10 / 20 / 40 % / keine; „geo“ heißt Bezugsplan geografisch, „zufällig“ Bezugsplan zufällig. Ab 25 Kunden ist die Referenz PyVRP (keine bewiesene Untergrenze).

- **Der Hilfsgraph schrumpft.** Anteil der zulässigen Bögen der kürzesten Rundreise gegen die Bögen ohne Fenster (Median): n = 50 geo **19 / 25 / 34 / 53 %**, n = 25 geo 29 / 33 / 46 / 66 %, n = 50 zufällig 12 / 14 / 18 / 31 %. Bei Einfügen nach Split bleiben mehr Bögen: n = 50 geo 59 / 57 / 56 / 60 %, zufällig 51 / 55 / 57 / 61 %, weil benachbarte Kunden dort auch zeitlich benachbart sind. **Nicht zerlegbar** kommt in keiner Zelle vor (jeder Kunde hat ein Fenster, das der Bezugsplan erfüllt).
- **Die kürzeste Rundreise ist unter engen Fenstern eine schlechte Riesentour.** Rundreise + Split, Abstand zum Optimum beziehungsweise zur Referenz, Breite 5 / 10 / 20 / 40 % / keine: n = 10 geo 46,8 / 43,5 / 24,3 / 12,2 / 2,4; n = 12 geo 68,9 / 51,6 / 25,4 / 15,0 / 1,9, zufällig 38,5 / 44,1 / 30,1 / 18,2 / 1,9; n = 25 geo **183,7 / 122,6 / 70,2 / 28,6 / 6,0**, zufällig 103,9 / 94,8 / 71,5 / 37,4 / 6,0; n = 50 geo **225,6 / 144,2 / 83,8 / 37,4 / 7,7**, zufällig 167,5 / 167,1 / 141,1 / 74,5 / 7,9. Der Grund ist die Routenzahl: „Füllen bis voll“ auf dieser Folge braucht bei n = 25 geo (Median) 13 / 9,5 / 7 / 5 / 3 Routen, die Referenz 3.
- **Nach dem Fensterende zu sortieren hilft nicht.** n = 25 geo, Breite 5 / 10 / 20 / 40 % / keine: Fensterende 299,2 / 244,3 / 203,3 / 180,5 / 143,1; Winkelfolge (Stück 6) 212,6 / 171,5 / 110,5 / 77,1 / 32,6; Zufall 261,6 / 253,9 / 218,7 / 184,3 / 145,5. Wer nur die Zeit sortiert, wirft den Weg weg.
- **Einfügen nach Split (Stück 4) sieht die Fenster beim Bau.** Abstand: n = 10 geo 0,0 / 0,0 / 0,6 / 1,2 / 0,0; n = 12 zufällig 2,5 / 2,4 / 2,4 / 2,1 / 1,0; n = 25 geo **0,0 / 0,5 / 4,9 / 7,7 / 3,3**, zufällig 8,7 / 14,9 / 9,9 / 7,2 / 3,3; n = 50 geo **0,2 / 9,7 / 17,1 / 18,8 / 8,3**, zufällig 17,1 / 20,8 / 20,1 / 14,3 / 8,3. Gepaart gegen die Rundreise (n = 25 geo): 32 / 0 / 0, 32 / 0 / 0, 31 / 0 / 1, 29 / 0 / 3, ohne Fenster nur 21 / 0 / 11 (n = 50 geo: 32 / 0 / 0 bei den drei engen Breiten, 25 / 0 / 7 bei 40 %, ohne Fenster 13 / 0 / 19).
- **Die Referenz ist keine Untergrenze.** Einfügen nach Split liegt bei n = 25 geo in 7 / 3 / 1 / 0 von 32 Instanzen (Breite 5 / 10 / 20 / 40 %) unter der PyVRP-Lösung, ohne Fenster in 1; zufällig 1 / 0 / 0 / 0; n = 50 geo 3 / 0 / 0 / 0, ohne Fenster bei Rundreise und Einfügen je 1.
- **Etiketten wachsen kaum.** Mittlere Zahl der Pareto-Etiketten je Zustand im exakten Löser: Median der Instanzen 1,00 bis 1,12 über alle Breiten und beide Bezugspläne bei n = 10 und 12, ohne Fenster genau 1,00; der größte Mittelwert einer Instanz 1,54 (n = 12, zufällig, 40 %), die größte Zahl in einem einzelnen Zustand 6. Die Fachkanon-Hypothese „die Etikettenzahl wächst mit den Zeitfenstern“ ist für diese Instanzen nicht bestätigt; der Split selbst braucht keine Etiketten.
- **Warten und spätes Losfahren (n = 10, Plan Einfügen nach Split, 80 Instanzen).** Bezugsplan zufällig, Breite 5 / 10 / 20 / 40 %: Wartezeit 20,8 / 20,5 / 16,7 / 10,5 % der Gesamtdauer (Median); spätes Losfahren spart im Median 4,9 / 6,8 / 10,1 / 10,4 % der Dauer; verschiebbar 224 / 204 / 171 / 123 Routen; der Dauer-Split ändert den Plan in 30 / 24 / 12 / 3 von 80 Instanzen. Bezugsplan geografisch: Wartezeit und Ersparnis im Median 0,0 %, Plan geändert in 1 / 2 / 5 / 2 von 80. Die Dauer des Dauer-Splits liegt im Median 0,00 % unter der späten Dauer des Strecken-Splits.
- **Handinstanz** (n = 6, Karte klein, Depot in der Mitte, Fenster auf ganze Zahlen gerundet, Breite 30 %, zufälliger Plan, H = 97, Kapazität 11): Die kürzeste Rundreise 1 6 5 4 3 2 käme bei Kunde 3 um 24,63 an, das Fenster schließt um 24; das Segment (4 3 2) fehlt, der Split kostet **67,99** mit (1 6 5), (4), (3 2) bei 10 von 15 Bögen. Das Optimum **53,79** fährt (1 6 5) und (3 4 2); rückwärts gelesen kostet die Rundreise 61,16; Einfügen nach Split baut 3 4 2 1 6 5 und trifft das Optimum. Die Richtung der Tour zählt, nicht ihre Länge (47,41 in beiden Richtungen).

## Ehrliche Grenzen

- Die Aussagen gelten für die gemessenen Größen (10, 12, 25, 50 Kunden), drei Zielrouten, 90 % Auslastung, die zwei Kartenarten der Bänder und die erzeugten Fenster (um einen Bezugsplan gelegt); sie sind keine Aussagen über echte Fenster, echte Daten oder andere Zielroutenzahlen.
- Ab 25 Kunden ist die Referenz PyVRP (5 Sekunden, ein Seed), eine gute Lösung und keine bewiesene Untergrenze; einzelne Reihenfolgen liegen darunter. Ob die Referenz auf einer anderen Maschine denselben Wert gäbe, ist nicht geprüft; deshalb stehen die Werte in `zfs_refs.json`.
- Die kürzeste Rundreise ist exakt bis 12 Kunden, darüber eine Heuristik (2-opt und Or-opt ab der Winkelfolge); die gelesene Richtung der Rundreise ist die lexikographisch kleinere (die App zeigt auch die andere).
- Der Split ist optimal für die gegebene Reihenfolge, nicht für das Problem. Die Aussage über eine Reihenfolge ist keine über „den“ Split; Savings mit Zeitfenstern, Dauer als Ziel, Solomon-Instanzen und Suche fehlen.
- „Gleichauf“ heißt hier: die Mediane liegen weniger als einen Prozentpunkt auseinander.
- Die Bänder rechnen mit nicht gerundeten Fenstern, die Voreinstellung der App (Handinstanz) mit gerundeten; das Runden macht die Fenster etwas weiter.
- Die Fall-Demo [vrp_demo](https://sebastianhanisch-vrp-demo.streamlit.app/) rechnet ebenfalls VRP mit Zeitfenstern; ihre Zahlen werden nicht übernommen. Keine Zahl aus der Literatur wird übernommen.
- Die Diagramme wurden im Browser angesehen und per Rauchtest bedient, nicht mit echtem Mausklick auf einzelne Punkte geprüft.

### Annahmen, Grenzen und bekannte Probleme (Text wie in der App)

**Annahmen**
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
- Die Diagramme wurden im Browser nur angesehen und per Rauchtest bedient, nicht mit echtem Mausklick auf einzelne Punkte geprüft.

## Befunde und Korrekturen gegenüber dem Plan

- **Phase-0-Zahlen reproduziert:** Alle Zahlen der Planung (exaktes Optimum, Etiketten, Zustände, Bögen und Splitkosten je Reihenfolge) kommen aus dem neuen Kern identisch heraus; eine Stichprobe von 81 Instanzen der Planung (n = 10 und 12) hatte 0 Abweichungen. Die 1760 Zeilen der Bänder stimmen mit den Rohdaten der Planung bis auf 10 Zeilen überein: In einer Instanz (n = 50, Kunden in Gruppen, Depot in der Mitte, Seed 300007) haben zwei Kunden denselben Winkel; die Planung sortierte dort nach der Nummer, der Kern nach Abstand und dann Nummer (die Regel aus Stück 6). Es betrifft nur die Winkelfolge in dieser Instanz bei allen fünf Breiten und beiden Bezugsplänen; die Mediane der README sind unverändert.
- **Plan-Angabe berichtigt:** Der Plan nannte für Einfügen nach Split „51 bis 72 % der Bögen“ bei n = 50; richtig sind 51 bis 61 % bei n = 50; die Spanne 51 bis 72 % gilt für n = 25 und 50 zusammen. Die Rundreise bei n = 12, Breite 5 %, geografisch (im Plan „–“) liegt bei 68,9 %.
- **Preset-Standard:** Die Voreinstellung ist die Handinstanz mit gerundeten Fenstern (nachrechenbar); der Regler „Fenster runden“ steht deshalb in den Einstellungen, während die Bänder nicht gerundet rechnen (der Plan nannte gerundete Fenster für alle Zellen; die Messungen der Planung waren nicht gerundet und bleiben so vergleichbar).
- **Port:** 9444 statt des im Plan gewählten 9443: Der Port 9443 war lokal belegt (eine bestehende Verbindung), und der Vorschau-Start wich aus. 9440 hat laut anderer Planung SVG-Konsolenfehler gezeigt, 9441 und 9442 gehören dem Umstauen.
- **Exaktes Optimum ohne Rückverfolgung:** Der Löser der Planung gab nur die Kosten zurück; hier trägt jedes Etikett seinen Vorgänger, damit die App die Routen des Optimums zeigen kann. Die Tests prüfen die Routen auf Zulässigkeit und Länge.

## Verifikation

- **Handwerte:** die Handinstanz auf einer Geraden mit Fenstern (Zulässigkeit, Split beider Reihenfolgen, Bögen, Gründe, längste Segmente, Füllen bis voll, Fahrplan mit Warten, Zeitschlupf, Dauer-Split) (`tests/test_timewindows_hand.py`).
- **Orakel:** Split gegen die Aufzählung aller Zerlegungen mit eigener Fahrplansimulation; Zulässigkeitsprüfung gegen die Simulation; das exakte Optimum gegen die Aufzählung aller Kundenmengen mit Permutationen; Dominanz (Minimum des Splits über alle Reihenfolgen gleich Optimum); „Füllen bis voll“ gegen die kleinste Routenzahl der Aufzählung (`tests/test_oracle_tw.py`).
- **Eigenschaften:** weitere Fenster nie teurer; Teilsegmente zulässiger Routen sind zulässig; ohne Fenster gleich Stück 3; Umnummerieren; gerundete Fenster nie teurer; alle Reihenfolgen zerlegbar und zulässig; Rundreise rückwärts gleich lang (`tests/test_properties.py`).
- **Randfälle:** ein und zwei Kunden, Kunde auf dem Depot, Rückkehr genau bei H, nicht zerlegbare Instanz, Bedienzeit 0, Warten über die ganze Route (`tests/test_edge_cases.py`).
- **Verdikte:** jede Verzweigung und jede Zahl im Text (`tests/test_verdicts.py`).
- **Zahlen der README und der Preset-Hilfen:** `tests/test_claims.py`; die vorberechneten Bänder auf Aufbau, Referenzdatei und gegen eine frische Rechnung einer Stichprobe (`tests/test_bands.py`).
- **Oberfläche:** AppTest-Rauchtest (jeder Button, jeder Regler am Minimum und Maximum), Reihenfolgen, Fensterbreiten, Bezugspläne, Bänder, PDF (`tests/test_app.py`, `tests/test_experiments.py`), Footer, Layout, Laufzeit-Importe.

## Tests

210 Tests. Laufzeit lokal etwa vier Minuten.

## Dateistruktur

| Datei | Zweck |
|---|---|
| `.github/workflows/tests.yml` | CI: Push, Pull Request, wöchentlicher Canary |
| `.gitignore` | venv, Caches, Streamlit-Secrets |
| `.streamlit/config.toml` | Streamlit-Einstellungen (keine Nutzungsstatistik) |
| `app.py` | Streamlit-App |
| `generate_precomputed.py` | erzeugt `zfs_bands.json` (Teile lassen sich parallel rechnen) und trägt mit `refs` PyVRP-Referenzen in `zfs_refs.json` ein |
| `requirements-dev.txt` | Laufzeit plus pytest |
| `requirements.txt` | Laufzeit-Bibliotheken (ungepinnt) |
| `zfs_algorithm.py` | Kern aus Stück 1: Split ohne Fenster, Hilfsgraph, exakter Löser, Held–Karp, kürzeste Rundreise |
| `zfs_bands.json` | vorberechnete Bänder (1760 Instanzzeilen) |
| `zfs_constants.py` | Regler-Grenzen, Bänder, Reihenfolgen, Farben, Presets, Annahmentext |
| `zfs_evaluation.py` | Analyse, Bänder, Kennzahlen, Verdikt-Logik |
| `zfs_layout.py` | Fester Kopf und Tabellenregel (Stylesheet) |
| `zfs_pdf_export.py` | PDF-Export des Ergebnisses |
| `zfs_presets.py` | Permalink, Presets (Schnellstart in der Seitenleiste), Zufalls-Seed-Button |
| `zfs_refs.json` | PyVRP-Referenzen (25 und 50 Kunden) |
| `zfs_routing.py` | Winkelfolge, kürzeste Rundreise exakt und Heuristik (aus Stück 6) |
| `zfs_savings.py` | Savings als Bezugsplan ab 25 Kunden (aus Stück 4) |
| `zfs_scenario.py` | Instanzen (aus Stück 1, mit Auslastung als Parameter) |
| `zfs_timewindows.py` | Zeitfenster: Erzeugung, Split, Bögen, Etiketten, Fahrplan, Zeitschlupf |
| `zfs_visualization.py` | Plotly-Abbildungen (Achsen gesperrt) |
| `tests/` | Handinstanz, Orakel, Eigenschaften, Randfälle, Verdikte, Claims, Bänder, Presets, Layout, AppTest, Footer, Laufzeit-Importe |

## Bewusst nicht umgesetzt

- **Savings und Sweep mit Zeitfenstern:** nur Reihenfolgen für den Split; Konstruktionsverfahren mit Fenstern nach Solomon (1987) sind nicht gebaut.
- **Dauer als Zielfunktion, mehrere Ziele, Flottengrenze:** Stück 9 der Linie; hier nur der Dauer-Split derselben Reihenfolge als Vorschau.
- **Solomon-Instanzen:** die Fenster sind erzeugt, nicht gemessen.
- **Suche** (Nachbarschaften, Anpassung der Riesentour): Stück 11; die Fall-Demo [vrp_demo](https://sebastianhanisch-vrp-demo.streamlit.app/) rechnet VRP mit Zeitfenstern und Suche.
- **Asymmetrische Entfernungen und verschiedene Fahrzeugtypen:** nur symmetrische Entfernungen und gleiche Fahrzeuge.
- **Instanzen über 12 Kunden live:** größere Instanzen stehen nur in den vorberechneten Bändern.

## Lokal ausführen

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

## Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Gebaut mit Streamlit, Plotly, NumPy und fpdf2.

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zu den Demos: [Interaktive Demos](https://sebastianhanisch.net/demos.html).
