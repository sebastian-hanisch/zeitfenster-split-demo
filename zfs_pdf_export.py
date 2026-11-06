"""PDF-Export des aktuellen Ergebnisses (fpdf2). Kernschriften sind latin-1: Umlaute gehen, Sonderzeichen werden ersetzt."""

from __future__ import annotations

from fpdf import FPDF

import zfs_constants as C
from zfs_evaluation import VIEW_KEYS, VIEW_NAMES, Analysis, Settings, de, gap_percent, pct, share_percent

_REPLACE = {"→": "->", "–": "-", "—": "-", "−": "-", "≤": "<=", "≥": ">=", "·": "*", "×": "x", "„": '"', "“": '"', "²": "2"}


def _s(text) -> str:
    out = str(text).replace("**", "").replace("`", "")
    for old, new in _REPLACE.items():
        out = out.replace(old, new)
    return out.encode("latin-1", "replace").decode("latin-1")


def build_pdf(s: Settings, a: Analysis) -> bytes:
    tw = a.tw
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 9, _s("Zeitfenster und Split"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    width = C.WIDTH_LABELS[s.width]
    pdf.multi_cell(0, 5, _s(f"{s.n} Kunden, Karte: {C.FAMILIES[s.family]}, Depot: {C.DEPOTS[s.depot].lower()}, Zielroutenzahl {s.routes}, Auslastung {s.fill} %, Seed {s.seed}. "
                            f"Fenster: Breite {width} von H, {C.MODES[s.mode].lower()}, {'auf ganze Zahlen gerundet' if s.round_windows else 'nicht gerundet'}. "
                            f"Kapazität {tw.inst.capacity}, Gesamtnachfrage {sum(tw.inst.demand)}, Horizont H = {de(tw.horizon, 1)}, Bedienzeit {int(tw.service)}. Alles simuliert."), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    widths = (70, 26, 34, 24, 36)
    pdf.set_font("Helvetica", "B", 9)
    for w, h in zip(widths, ("Reihenfolge + Split", "Kosten", "Über Optimum", "Routen", "Bögen")):
        pdf.cell(w, 6, _s(h), border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)
    rows = [("Optimum (alle Pläne mit Fenstern)", de(a.exact.cost), pct(0.0), str(len(a.exact.routes)), "-")]
    for k in VIEW_KEYS:
        sp = a.splits[k]
        arcs = f"{a.arcs[k][0]} von {a.arcs[k][1]} ({pct(share_percent(a.arcs[k]), 0)})"
        rows.append((VIEW_NAMES[k], "nicht zerlegbar", "-", "-", arcs) if sp is None else (VIEW_NAMES[k], de(sp.cost), pct(gap_percent(sp.cost, a.exact.cost)), str(len(sp.routes)), arcs))
    for row in rows:
        for w, v in zip(widths, row):
            pdf.cell(w, 5.5, _s(v), border=1)
        pdf.ln()
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 6, _s("Kunden und Zeitfenster"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    for c in range(1, tw.n + 1):
        pdf.cell(0, 5, _s(f"Kunde {c}: Nachfrage {tw.inst.demand[c - 1]}, Fenster [{de(tw.early[c], 1)}; {de(tw.late[c], 1)}]"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(0, 4, _s("Der Split zerlegt eine Reihenfolge aller Kunden in Routen; ein Bogen des Hilfsgraphen existiert nur, wenn Last und alle Zeitfenster gehalten werden. "
                            "Quelle: zeitfenster-split-demo, Sebastian Hanisch."), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
