"""Zeitfenster und Split - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Stück 8 der Reihe „Tourenbildung“: Was ändert sich am Split, wenn jeder Kunde ein Zeitfenster hat? Die Demo zeigt den Hilfsgraphen mit Fenstern Schritt für Schritt (welche Bögen fehlen und warum),
wie er mit engeren Fenstern schrumpft, warum die Richtung der Riesentour zählt, was Etiketten und Zeitschlupf bringen und wie sich fünf Reihenfolgen schlagen, live bis 12 Kunden gegen das exakte
Optimum und in vorberechneten Bändern bis 50 Kunden.

Lauffähig mit: streamlit run app.py
"""

from dataclasses import replace

import streamlit as st

import zfs_constants as C
import zfs_timewindows as T
from zfs_evaluation import (
    VIEW_KEYS,
    VIEW_NAMES,
    Settings,
    analyse,
    band_rows,
    band_stats,
    duration_stats,
    de,
    duration_view,
    gap_percent,
    instances_word,
    order_text,
    order_view,
    pct,
    routes_text,
    routes_word,
    share_percent,
    verdict_band_duration,
    verdict_band_labels,
    verdict_bands,
    verdict_compare,
    verdict_directions,
    verdict_duration,
    verdict_labels,
    verdict_shrink,
    verdict_split,
    verdict_under,
    width_sweep,
)
from zfs_layout import dunkles_design, kopf_css
from zfs_pdf_export import build_pdf
from zfs_presets import (
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    sidebar_presets,
    sync_query_params,
)
from zfs_visualization import (
    build_arc_matrix,
    build_band_widths,
    build_bands,
    build_label_chart,
    build_map,
    build_timeline,
    build_width_chart,
)

st.set_page_config(page_title="Zeitfenster und Split – Sebastian Hanisch", layout="wide")


@st.cache_data(show_spinner=False)
def _analysis(settings):
    return analyse(settings)


@st.cache_data(show_spinner=False)
def _sweep(settings):
    return width_sweep(settings)


@st.cache_data(show_spinner=False)
def _view(settings, key, lexicographic):
    return order_view(analyse(settings), key, lexicographic)


@st.cache_data(show_spinner=False)
def _duration(settings, key):
    return duration_view(analyse(settings), key)


@st.cache_data(show_spinner=False)
def _band_stats(n, mode, width):
    return band_stats(band_rows(n, mode, width))


# Fester Kopf: nur der Titel bleibt beim Scrollen oben (Stylesheet in zfs_layout.py).
st.html(kopf_css(dunkles_design()))
with st.container(key="kopf"):
    st.title("⏱️ Zeitfenster und Split")
st.markdown(
    """
**Was ändert sich am Split, wenn jeder Kunde ein Zeitfenster hat?** Der Split (Stücke 1 bis 3) zerlegt eine Reihenfolge aller Kunden, die **Riesentour**, in Routen: ein kürzester Weg in einem Hilfsgraphen,
dessen Bögen mögliche Routen sind. Mit Zeitfenstern ist ein Bogen nur noch da, wenn die Route auch zeitlich geht. Die Demo zeigt, **welche Bögen fehlen und warum**, wie der Graph mit engeren Fenstern
**schrumpft**, warum danach die **Reihenfolge** der Riesentour fast alles entscheidet, und was Etiketten und Zeitschlupf (späteres Losfahren) bringen.

Weiter unten: **🔬 Der Split mit Fenstern Schritt für Schritt**, **🔬 Wie viel schrumpft der Graph?**, **🔬 Die Richtung zählt**, **🔬 Etiketten, Warten und Zeitschlupf**, **🔬 Wie schlagen sich die Reihenfolgen?**,
**🚧 Wo die Annahmen enden**, der Expander **⚠️ Annahmen, Grenzen und bekannte Probleme** und der Expander **📐 Mathematische Formulierung**.
"""
)

with st.expander("So rechnet der Split mit Fenstern", expanded=True):
    st.markdown(
        """
1. **Modell:** Fahrzeit = Entfernung, Bedienzeit 10 je Kunde, Fenster [e, l]: wer vor e ankommt, wartet (kostenlos), nach l geht es nicht. Alle Fahrzeuge fahren zur Zeit 0 los und müssen bis H zurück sein. Kosten = gefahrene Strecke.
2. **Bogen:** Das Segment „Kunden i+1 bis j der Riesentour“ ist ein Bogen, wenn Last, alle Fenster und die Rückkehr bis H gehalten werden. Beim Verlängern genügt eine Prüfung der Ankunftszeit; sobald sie scheitert, scheitern alle längeren Segmente ebenfalls.
3. **Weg:** Der kürzeste Weg von 0 nach n im Hilfsgraphen ist der beste Plan für diese Reihenfolge. Etiketten braucht der Split nicht: die Reihenfolge legt die Zeit fest, und die früheste Abfahrt ist immer richtig.
4. **Wo die Fenster liegen:** Um die Ankunftszeiten eines **Bezugsplans** (zufälliger Plan: „Füllen bis voll“ auf einer Zufallsfolge; geografischer Plan: das Optimum), so hat jede Instanz mindestens einen zulässigen Plan. Die Breite ist ein Anteil von H.
        """
    )

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    sidebar_presets()  # Schnellstart oben, das aktive Preset ist hervorgehoben
    st.header("⚙️ Einstellungen")
    st.markdown("**Instanz**")
    n = st.slider("Kunden n", *bounds("n_slider"), key="n_slider", help=f"Bis n = {C.N_MAX} rechnet die App das exakte Optimum. Größere Instanzen stehen in den vorberechneten Bändern.")
    family = st.selectbox("Art der Karte", list(range(len(C.FAMILIES))), key="family_select", format_func=lambda i: C.FAMILIES[i],
                          help="„Kleine Karte“: ganze Koordinaten 0 bis 16, Nachfragen 1 bis 4. Die beiden anderen: Karte 0 bis 100, Nachfragen 1 bis 10; „In Gruppen“: drei Häufungen von Kunden.")
    depot = st.selectbox("Lage des Depots", list(range(len(C.DEPOTS))), key="depot_select", format_func=lambda i: C.DEPOTS[i])
    routes = st.slider("Zielroutenzahl", *bounds("routes_slider"), key="routes_slider", help="Legt zusammen mit der Auslastung die Kapazität fest.")
    fill = st.slider("Auslastung (%)", *bounds("fill_slider"), step=C.FILL_STEP, key="fill_slider",
                     help="Kapazität = aufgerundet Gesamtnachfrage geteilt durch (Zielroutenzahl mal Auslastung).")
    seed = st.number_input("Zufalls-Seed der Instanz", *bounds("seed_input"), key="seed_input", step=1)
    st.button("🎲 Neue Instanz generieren", width="stretch", on_click=randomize_seed)
    st.markdown("**Zeitfenster**")
    width = st.selectbox("Fensterbreite (Anteil von H)", list(range(len(C.LIVE_WIDTHS))), key="width_select", format_func=lambda i: C.WIDTH_LABELS[i],
                         help="Breite des Fensters jedes Kunden als Anteil des Horizonts H. „keine“: alle Fenster [0, H].")
    mode = st.selectbox("Bezugsplan der Fenster", list(range(len(C.MODES))), key="mode_select", format_func=lambda i: C.MODES[i],
                        help="Die Fenster liegen um die Ankunftszeiten dieses Plans. Zufälliger Plan: „Füllen bis voll“ auf einer Zufallsfolge (die Fenster passen schlecht zur Geografie). Geografischer Plan: das Optimum ohne Fenster.")
    rounding = st.selectbox("Fenster runden", [0, 1], key="round_select", format_func=lambda i: ("Auf ganze Zahlen (Handrechnung)", "Nicht gerundet")[i],
                            help="Anfang abgerundet, Ende und H aufgerundet. Die Bänder und die Messungen der README sind nicht gerundet.")

sync_query_params({"n_slider": int(n), "family_select": int(family), "depot_select": int(depot), "routes_slider": int(routes), "fill_slider": int(fill), "seed_input": int(seed),
                   "width_select": int(width), "mode_select": int(mode), "round_select": int(rounding)})

settings = Settings(int(n), int(family), int(depot), int(routes), int(fill), int(seed), int(width), int(mode), int(rounding) == 0)
a = _analysis(settings)
tw = a.tw
inst = tw.inst
exact = a.exact

# --- Ergebnis ------------------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Ergebnis: Split mit Fenstern")
m1, m2, m3, m4 = st.columns(4)
# Delta immer als „mein Wert minus Referenz“; die Farbe regelt delta_color="inverse" (Vorzeichen-Falle, DEMO-PLAYBOOK §2). Die Differenz aus den angezeigten, gerundeten Werten, damit Zahl und Delta zusammenpassen.
m1.metric("Optimum (alle Pläne mit Fenstern)", de(exact.cost), delta="Referenz", delta_color="off")
for col, key in ((m2, "tour"), (m3, "es")):
    sp = a.splits[key]
    if sp is None:
        col.metric(f"{VIEW_NAMES[key]} + Split", "nicht zerlegbar")
    else:
        col.metric(f"{VIEW_NAMES[key]} + Split", de(sp.cost), delta=f"{round(sp.cost, 2) - round(exact.cost, 2):+.2f} gegen Optimum".replace(".", ","), delta_color="inverse")
m4.metric("Zulässige Bögen der Rundreise", f"{a.arcs['tour'][0]} von {a.arcs['tour'][1]}", delta=pct(share_percent(a.arcs["tour"]), 0), delta_color="off")
st.caption(f"Kapazität {inst.capacity}, Gesamtnachfrage {sum(inst.demand)}, Horizont H = {de(tw.horizon, 1)}, Bedienzeit {int(tw.service)}. Das Optimum fährt {routes_word(len(exact.routes))}: {routes_text(exact.routes)}.")
st.download_button("📄 Ergebnis als PDF", data=build_pdf(settings, a), file_name="zeitfenster-split.pdf", mime="application/pdf", key="pdf_download")

# --- Kernfrage -----------------------------------------------------------------------------------------------------------------------------

st.markdown("## ❓ Kernfrage: Was machen Zeitfenster mit dem Split?")
kind, text = verdict_compare(a)
getattr(st, kind)(text)

st.markdown("---")

# --- Experiment 1 --------------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Der Split mit Fenstern Schritt für Schritt")
st.caption("Wähle eine Reihenfolge der Kunden (die Riesentour). Die Matrix zeigt den Hilfsgraphen: jede Zelle ist ein Segment (erster bis letzter Kunde); grün ist ein Bogen, die anderen Farben zeigen, "
           "warum das Segment fehlt. Die Quadrate markieren den kürzesten Weg, also die Routen des Splits.")
e1, e2 = st.columns([3, 2])
with e1:
    key = st.radio("Reihenfolge", list(VIEW_KEYS), key="order_radio", horizontal=True, format_func=lambda k: VIEW_NAMES[k])
with e2:
    lexi = st.toggle("Lexikographisch (erst Routenzahl, dann Strecke)", key="lex_toggle", help="Kostenpaar (Routen, Strecke): unter allen Zerlegungen mit der kleinsten Routenzahl die kürzeste. Stück 3.")
view = _view(settings, key, bool(lexi))
sp = view["split"]
v1, v2 = st.columns([1, 1])
with v1:
    if sp is None:
        st.markdown(f"**{VIEW_NAMES[key]}: nicht zerlegbar**")
        st.plotly_chart(build_map(tw, []), width="stretch", key="map_view")
    else:
        st.markdown(f"**{VIEW_NAMES[key]} + Split: {de(sp.cost)}** ({routes_word(len(sp.routes))}, {pct(gap_percent(sp.cost, exact.cost))} über dem Optimum)")
        st.plotly_chart(build_map(tw, sp.routes), width="stretch", key="map_view")
with v2:
    rows = ["| Platz | Kunde | Nachfrage | Fenster von | bis |", "|---|---|---|---|---|"]
    for i, c in enumerate(view["order"], start=1):
        rows.append(f"| {i} | {c} | {inst.demand[c - 1]} | {de(tw.early[c], 1)} | {de(tw.late[c], 1)} |")
    st.markdown("\n".join(rows))
    st.caption("Die Riesentour in der gewählten Reihenfolge, mit dem Fenster jedes Kunden.")
st.plotly_chart(build_arc_matrix(view["order"], view["table"], view["path"]), width="stretch", key="arc_matrix")
if sp is not None:
    st.markdown("**Fahrplan der Routen des Splits** (Fahrt, Warten, Bedienung; die violette Linie ist das Zeitfenster und muss die Bedienung enthalten)")
    st.plotly_chart(build_timeline(tw, sp.routes, view["timelines"]), width="stretch", key="timeline")
kind, text = verdict_split(a, key, view, bool(lexi))
getattr(st, kind)(text)

st.markdown("---")

# --- Experiment 2 --------------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Wie viel schrumpft der Graph?")
st.caption("Dieselbe Instanz und derselbe Bezugsplan bei allen Fensterbreiten: Anteil der zulässigen Bögen jeder Reihenfolge und ihr Abstand zum Optimum. Fehlende Punkte: die Reihenfolge ist nicht zerlegbar.")
sweep = _sweep(replace(settings, width=0))
c1, c2 = st.columns(2)
with c1:
    st.markdown("**Zulässige Bögen (% der Bögen ohne Fenster)**")
    st.plotly_chart(build_width_chart(sweep, "orders", "share", "Anteil zulässiger Bögen (%)"), width="stretch", key="chart_share")
with c2:
    st.markdown("**Abstand zum Optimum (%)**")
    st.plotly_chart(build_width_chart(sweep, "orders", "gap", "Abstand zum Optimum (%)"), width="stretch", key="chart_gap")
table = ["| Fensterbreite | Optimum | " + " | ".join(f"{C.ORDER_NAMES[k]}: Bögen / Abstand" for k in C.ORDER_KEYS) + " |", "|---|---|" + "---|" * len(C.ORDER_KEYS)]
for r in sweep:
    cells = [f"{r['orders'][k]['arcs']} von {r['orders'][k]['free']} / " + ("–" if r["orders"][k]["gap"] is None else pct(r["orders"][k]["gap"])) for k in C.ORDER_KEYS]
    table.append(f"| **{r['label']}** | {de(r['opt'])} | " + " | ".join(cells) + " |")
st.markdown("\n".join(table))
kind, text = verdict_shrink(sweep)
getattr(st, kind)(text)

st.markdown("---")

# --- Experiment 3 --------------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Die Richtung zählt")
st.caption("Dieselbe kürzeste Rundreise, einmal vorwärts und einmal rückwärts gelesen, ist dieselbe Strecke, aber eine andere Riesentour: die Zeiten laufen anders durch die Fenster. Einfügen nach Split sieht die Fenster beim Bau.")
rows3 = []
for k in ("tour", "tour_rev", "es"):
    rows3.append({"key": k, "split": a.splits[k], "arcs": a.arcs[k], "order": a.orders[k]})
table = ["| Reihenfolge | Riesentour | Kosten | über Optimum | Routen | Bögen |", "|---|---|---|---|---|---|"]
for r in rows3:
    s3 = r["split"]
    table.append(f"| **{VIEW_NAMES[r['key']]}** | {order_text(r['order'])} | " + ("nicht zerlegbar | – | – | " if s3 is None else f"{de(s3.cost)} | {pct(gap_percent(s3.cost, exact.cost))} | {len(s3.routes)} | ") + f"{r['arcs'][0]} von {r['arcs'][1]} |")
st.markdown("\n".join(table))
pick = st.radio("Wo scheitern die längeren Segmente?", ["tour", "tour_rev", "es"], key="blocked_radio", horizontal=True, format_func=lambda k: VIEW_NAMES[k])
blocked = ["| Beginn bei Kunde | längstes zulässiges Segment | warum das nächste Segment fehlt |", "|---|---|---|"]
for row in T.blocked_segments(tw, a.orders[pick]):
    why = row["blocked"]
    if why is None:
        text_why = "das Ende der Riesentour"
    elif why["reason"] == "load":
        text_why = f"mit Kunde {why['customer']} läge die Last über {inst.capacity}"
    elif why["reason"] == "window":
        text_why = f"Kunde {why['customer']} käme um {de(why['arrival'], 1)} an, sein Fenster schließt um {de(why['late'], 1)}"
    else:
        text_why = f"nach Kunde {why['customer']} läge die Rückkehr bei {de(why['back'], 1)} nach H = {de(tw.horizon, 1)}"
    blocked.append(f"| {a.orders[pick][row['start']]} | {order_text(row['longest']) or '–'} | {text_why} |")
st.markdown("\n".join(blocked))
kind, text = verdict_directions(a, rows3)
getattr(st, kind)(text)

st.markdown("---")

# --- Experiment 4 --------------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Etiketten, Warten und Zeitschlupf")
st.caption("Oben: Der exakte Löser braucht je Zustand (Kundenmenge, letzter Kunde) mehrere Etiketten (Strecke, Zeit), wenn eine längere Strecke früher ankommt. Unten: Warten, Zeitschlupf (um wie viel sich die Abfahrt "
           "verschieben lässt) und spätes Losfahren für die Routen der oben gewählten Reihenfolge.")
st.plotly_chart(build_label_chart(sweep), width="stretch", key="chart_labels")
kind, text = verdict_labels(sweep)
getattr(st, kind)(text)
dv = _duration(settings, key)
if dv:
    table = ["| Route | Kunden | Wartezeit | Zeitschlupf | nutzbare Verschiebung | Dauer früh | Dauer spät |", "|---|---|---|---|---|---|---|"]
    for i, (r, tl) in enumerate(zip(a.splits[key].routes, dv["timelines"]), start=1):
        table.append(f"| {i} | {order_text(r)} | {de(tl.wait)} | {de(tl.slack)} | {de(tl.shift)} | {de(tl.duration_early)} | {de(tl.duration_late)} |")
    st.markdown("\n".join(table))
kind, text = verdict_duration(dv, VIEW_NAMES[key])
getattr(st, kind)(text)

st.markdown("---")

# --- Experiment 5 --------------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Wie schlagen sich die Reihenfolgen?")
st.caption("Feste Instanzen, vorberechnet (generate_precomputed.py): vier Zellen (Kunden zufällig oder in Gruppen, Depot in der Mitte oder in der Ecke) mal 20 Seeds (10 Kunden) oder 8 Seeds, drei Zielrouten, 90 % Auslastung, "
           "nicht gerundete Fenster. Bis 12 Kunden gegen das exakte Optimum, darüber gegen die Referenz PyVRP (5 Sekunden, ein Seed).")
b1, b2, b3 = st.columns(3)
with b1:
    band_n = int(st.radio("Kunden n", list(C.BAND_SIZES), index=2, horizontal=True, key="band_n"))
with b2:
    band_mode = C.MODE_KEYS[C.MODES.index(st.radio("Bezugsplan", list(C.MODES), index=1, horizontal=True, key="band_mode"))]
with b3:
    band_idx = st.radio("Fensterbreite", list(range(len(C.BAND_WIDTHS))), index=1, horizontal=True, key="band_width", format_func=lambda i: "keine" if C.BAND_WIDTHS[i] is None else f"{int(round(100 * C.BAND_WIDTHS[i]))} %")
band_width = C.BAND_WIDTHS[int(band_idx)]
stats = _band_stats(band_n, band_mode, band_width)
if stats:
    st.caption(f"{instances_word(stats['count'])} (alle vier Zellen zusammen). Die Zahlen sind Spannen über Instanzen, kein Satz.")
    st.plotly_chart(build_bands(stats["gaps"], C.ORDER_NAMES, C.ORDER_COLORS, C.ORDER_KEYS), width="stretch", key="band_chart")
    ref_name = "Optimum" if band_n in C.EXACT_SIZES else "Referenz"
    table = [f"| Reihenfolge | Median | Minimum bis Maximum | Mittel | unter der {ref_name} | Bögen (Median) | billiger / gleich / teurer als Rundreise |", "|---|---|---|---|---|---|---|"]
    for k in C.ORDER_KEYS:
        g = stats["gaps"][k]
        vs = "–" if k == C.COMPARE_KEY else (lambda p: f"{p['cheaper']} / {p['equal']} / {p['more']}")(stats["vs"][k])
        if g is None:
            table.append(f"| **{C.ORDER_NAMES[k]}** | nicht zerlegbar | – | – | – | {pct(stats['shares'][k], 0)} | {vs} |")
        else:
            table.append(f"| **{C.ORDER_NAMES[k]}** | {pct(g['median'])} | {pct(g['min'])} bis {pct(g['max'])} | {pct(g['mean'])} | {stats['under'][k]} von {g['count']} | {pct(stats['shares'][k], 0)} | {vs} |")
    st.markdown("\n".join(table))
    st.markdown("**Über alle Fensterbreiten** (Median-Abstand je Reihenfolge)")
    st.plotly_chart(build_band_widths([_band_stats(band_n, band_mode, w) for w in C.BAND_WIDTHS], ["keine" if w is None else f"{int(round(100 * w))} %" for w in C.BAND_WIDTHS]), width="stretch", key="band_widths")
kind, text = verdict_bands(band_n, band_mode, band_width, stats)
getattr(st, kind)(text)
if stats:
    kind, text = verdict_under(stats)
    getattr(st, kind)(text)
    kind, text = verdict_band_labels(stats)
    if text:
        getattr(st, kind)(text)
    kind, text = verdict_band_duration(band_n, band_mode, band_width, duration_stats(band_rows(band_n, band_mode, band_width)))
    if text:
        getattr(st, kind)(text)

st.markdown("---")

# --- Grenzen -------------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| **Fahrzeit = Entfernung, Fenster um einen Bezugsplan** | Echte Fenster liegen nicht um einen Plan; die Instanzen sind erzeugt, nicht gemessen. Aussagen gelten für diese Erzeugung | Solomon-Benchmarks (Stück 9, Folgearbeit) |
| **Ziel Strecke, Warten kostenlos** | Mit Dauer als Ziel ändert spätes Losfahren die Kosten; der Plan kann anders ausfallen | Stück 9 (Dauer und mehrere Ziele); hier nur der Schalter in Experiment 4 |
| **Eine Reihenfolge, ein Split** | Der Split findet den besten Plan nur für die gegebene Reihenfolge; ob es eine gute gibt, entscheidet die Konstruktion der Riesentour | Stück 4 bis 6 (Konstruktion), Stück 11 (Suche) |
| **Keine Flottengrenze** | Mit einer Grenze wäre die Zerlegung mit den wenigsten Routen nötig (Stück 3) | Stück 3 |
| **Symmetrische Entfernungen, Dreiecksungleichung** | Der Abbruch beim Verlängern (Rückkehrzeit wächst) und die Dominanz setzen sie voraus | – |
| **Referenz PyVRP ab 25 Kunden** | Eine gute Lösung, keine bewiesene Untergrenze; einzelne Reihenfolgen liegen darunter | – |
"""
)

with st.expander("⚠️ Annahmen, Grenzen und bekannte Probleme"):
    st.markdown(C.ASSUMPTIONS_MARKDOWN)

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Lesehilfe.** Ein Depot $0$, Kunden $1, \dots, n$ mit Nachfragen $q_i$, Kapazität $Q$, euklidische Entfernungen $d_{ij}$ (Fahrzeit gleich Entfernung), Bedienzeit $s$, Fenster $[e_i, l_i]$, Horizont $H$.

| Symbol | Bedeutung |
|---|---|
| $\sigma = (\sigma_1, \dots, \sigma_n)$ | die Riesentour (Reihenfolge aller Kunden) |
| $a_k$ | Beginn der Bedienung bei dem $k$-ten Kunden einer Route: $a_k = \max(e_{c_k},\, a_{k-1} + s + d_{c_{k-1} c_k})$, $a_0 = -s$ mit $c_0 = 0$ |
| Bogen $(i, j)$ | die Route $\sigma_{i+1}, \dots, \sigma_j$, falls $\sum q \le Q$, $a_k \le l_{c_k}$ für alle $k$ und $a_{\text{letzter}} + s + d_{\text{letzter},0} \le H$ |

**Split mit Fenstern.** Kürzester Weg von $0$ nach $n$ im azyklischen Hilfsgraphen mit den Bögen $(i, j)$ und den Kosten $\sum d$ der Route. Weil sich jede Route beim Verlängern nur verspätet
(Dreiecksungleichung, Bedienzeit, Warten kostet nichts), ist ein Segment, das scheitert, mit jeder Verlängerung unzulässig: die Schleife über $j$ bricht beim ersten Verstoß ab.

**Dominanz.** Teilsegmente zulässiger Routen sind zulässig. Das Minimum des Splits über alle Reihenfolgen ist das Optimum des Tourenplanungsproblems mit Fenstern (Stück 1); die Tests prüfen es gegen die Aufzählung
aller Reihenfolgen (bis 7 Kunden). Ebenso ist „Füllen bis voll“ (Stück 3) mit Fenstern optimal in der Routenzahl.

**Etiketten.** Im exakten Löser (Held-Karp über Kundenmengen) gehört zu jedem Zustand (Menge $S$, letzter Kunde $l$) eine Liste von Etiketten (Strecke, Zeit); ein Etikett $(d, t)$ dominiert $(d', t')$, wenn $d \le d'$ und
$t \le t'$. Die Liste ist die Pareto-Front.

**Zeitschlupf.** Für eine zulässige Route ist $F_0 = \min\big(H - \text{Rückkehr},\ \min_k (W_k + l_{c_k} - a_k)\big)$ mit $W_k$ der Wartezeit bis einschließlich $k$ (Savelsbergh): um so viel lässt sich die Abfahrt verschieben, ohne ein
Fenster zu verletzen. Nutzbar ist $\min(F_0, W)$ mit $W$ der gesamten Wartezeit; die Dauer sinkt um diese Verschiebung.

**Literatur.** Kürzeste-Wege-Zerlegung auf der Riesentour: Beasley (1983); Split nach Prins (2004), mit Zeitfenstern nach Vidal, Crainic, Gendreau und Prins (2013); Konstruktionsverfahren und Benchmarks für Zeitfenster: Solomon (1987);
Zeitschlupf und Dauerminimierung: Savelsbergh (1985, 1992); Referenzlöser: PyVRP (Wouda, Lan, Kool). Alle wurden nur als Titel oder Abstract gesehen; die Demo übernimmt keine Zahl daraus.
        """
    )

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zu den Demos: [Interaktive Demos](https://sebastianhanisch.net/demos.html)."
)
