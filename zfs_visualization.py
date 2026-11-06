"""Plotly-Abbildungen. Alle Achsen sind gesperrt (fixedrange), damit Touch-Geräte beim Scrollen nicht am Diagramm hängen bleiben."""

import plotly.graph_objects as go

import zfs_constants as C


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height=380):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.2), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def _fmt(x: float) -> str:
    return f"{x:.1f}".replace(".", ",")


def build_map(tw, routes, title_prefix="Route"):
    """Karte: Depot als Quadrat, Kunden als Kreise (Größe = Nachfrage, Beschriftung = Nummer, Hover = Fenster), jede Route eine Farbe. Gleicher Maßstab in x und y über scaleanchor."""
    inst = tw.inst
    xs = [p[0] for p in inst.xy]
    ys = [p[1] for p in inst.xy]
    pad = 0.08 * max(max(xs) - min(xs), max(ys) - min(ys), 1.0)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[min(xs) - pad, max(xs) + pad], y=[min(ys) - pad, max(ys) + pad], mode="markers", marker=dict(opacity=0), hoverinfo="skip", showlegend=False))
    for r, route in enumerate(routes):
        pts = [inst.xy[0]] + [inst.xy[c] for c in route] + [inst.xy[0]]
        fig.add_trace(go.Scatter(x=[p[0] for p in pts], y=[p[1] for p in pts], mode="lines", line=dict(color=C.ROUTE_COLORS[r % len(C.ROUTE_COLORS)], width=3),
                                 name=f"{title_prefix} {r + 1} (Last {inst.load(route)} von {inst.capacity})", hoverinfo="skip"))
    customers = list(range(1, inst.n + 1))
    fig.add_trace(go.Scatter(
        x=[inst.xy[c][0] for c in customers], y=[inst.xy[c][1] for c in customers], mode="markers+text", text=[str(c) for c in customers], textposition="top center",
        marker=dict(size=[9 + 2.5 * inst.demand[c - 1] for c in customers], color="rgba(150,150,150,0.55)", line=dict(color="#555", width=1)),
        customdata=[[inst.demand[c - 1], _fmt(tw.early[c]), _fmt(tw.late[c])] for c in customers],
        hovertemplate="Kunde %{text}: Nachfrage %{customdata[0]}, Fenster [%{customdata[1]}; %{customdata[2]}]<extra></extra>", name="Kunden (Größe = Nachfrage)"))
    fig.add_trace(go.Scatter(x=[inst.xy[0][0]], y=[inst.xy[0][1]], mode="markers", marker=dict(symbol="square", size=15, color="#222"), name="Depot", hoverinfo="skip"))
    fig.update_yaxes(scaleanchor="x", scaleratio=1, showgrid=False, zeroline=False, showticklabels=False)
    fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False)
    return _base(fig, 380)


def build_arc_matrix(order, table, path):
    """Hilfsgraph als Matrix: Zeile = erster Kunde des Segments, Spalte = letzter Kunde des Segments (beide in der Reihenfolge der Riesentour). Farbe = zulässig oder der Grund,
    warum das Segment fehlt; Quadrate markieren den gewählten Weg (die Routen des Splits)."""
    n = len(order)
    code = {"ok": 1, "load": 2, "window": 3, "return": 4}
    z = [[None] * n for _ in range(n)]
    text = [[""] * n for _ in range(n)]
    for row in table:
        i, j = row["start"], row["end"] - 1
        key = "ok" if row["ok"] else row["reason"]
        z[i][j] = code[key]
        who = f" (an Kunde {row['culprit']})" if not row["ok"] else ""
        text[i][j] = f"Kunden {', '.join(str(c) for c in order[i:j + 1])}: {C.ARC_TEXT[key]}{who}"
    scale = [[0.0, C.ARC_COLORS["ok"]], [0.25, C.ARC_COLORS["ok"]], [0.25, C.ARC_COLORS["load"]], [0.5, C.ARC_COLORS["load"]], [0.5, C.ARC_COLORS["window"]], [0.75, C.ARC_COLORS["window"]],
             [0.75, C.ARC_COLORS["return"]], [1.0, C.ARC_COLORS["return"]]]
    labels = [str(c) for c in order]
    fig = go.Figure(go.Heatmap(z=z, x=list(range(n)), y=list(range(n)), text=text, hovertemplate="%{text}<extra></extra>", colorscale=scale, zmin=0.5, zmax=4.5, showscale=False, xgap=2, ygap=2))
    for key in ("ok", "load", "window", "return"):
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", marker=dict(size=10, color=C.ARC_COLORS[key], symbol="square"), name=C.ARC_TEXT[key]))
    if path:
        fig.add_trace(go.Scatter(x=[e - 1 for _, e in path], y=[s for s, _ in path], mode="markers", marker=dict(size=16, symbol="square-open", color="#111", line=dict(width=3)), name="gewählter Weg", hoverinfo="skip"))
    fig.update_xaxes(tickmode="array", tickvals=list(range(n)), ticktext=labels, title_text="letzter Kunde des Segments", side="bottom")
    fig.update_yaxes(tickmode="array", tickvals=list(range(n)), ticktext=labels, title_text="erster Kunde des Segments", autorange="reversed")
    return _base(fig, 420)


def build_timeline(tw, routes, timelines):
    """Fahrplan: je Kunde eine Zeile; Fahrt (grau), Warten (hell), Bedienung (Routenfarbe) und das Zeitfenster als Linie mit Endmarken; letzte Zeile je Route: Rückfahrt zum Depot."""
    fig = go.Figure()
    ylabels, travel, wait, serve, win = [], [], [], [], []
    for r, (route, tl) in enumerate(zip(routes, timelines), start=1):
        t = 0.0
        for row in tl.rows:
            y = f"R{r}: Kunde {row['customer']}"
            ylabels.append(y)
            travel.append((y, t, row["raw"] - t))
            wait.append((y, row["raw"], row["wait"]))
            serve.append((y, row["start"], tw.service, r))
            win.append((y, row["early"], row["late"]))
            t = row["start"] + tw.service
        y = f"R{r}: zurück"
        ylabels.append(y)
        travel.append((y, t, tl.back - t))
    fig.add_trace(go.Bar(y=[v[0] for v in travel], x=[v[2] for v in travel], base=[v[1] for v in travel], orientation="h", marker_color="rgba(120,120,120,0.6)", name="Fahrt", hovertemplate="Fahrt %{x:.1f}<extra></extra>"))
    fig.add_trace(go.Bar(y=[v[0] for v in wait], x=[v[2] for v in wait], base=[v[1] for v in wait], orientation="h", marker_color="rgba(216,161,58,0.35)", marker_line=dict(color="#d8a13a", width=1), name="Warten", hovertemplate="Warten %{x:.1f}<extra></extra>"))
    fig.add_trace(go.Bar(y=[v[0] for v in serve], x=[v[2] for v in serve], base=[v[1] for v in serve], orientation="h", marker_color=[C.ROUTE_COLORS[(v[3] - 1) % len(C.ROUTE_COLORS)] for v in serve], name="Bedienung", hovertemplate="Bedienung ab %{base:.1f}<extra></extra>"))
    for y, lo, hi in win:
        fig.add_trace(go.Scatter(x=[lo, hi], y=[y, y], mode="lines+markers", line=dict(color="#7b5ea7", width=3), marker=dict(symbol="line-ns", size=14, color="#7b5ea7", line=dict(width=3)), showlegend=False,
                                 hovertemplate="Fenster [" + _fmt(lo) + "; " + _fmt(hi) + "]<extra></extra>"))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines+markers", line=dict(color="#7b5ea7", width=3), marker=dict(symbol="line-ns", size=14, color="#7b5ea7"), name="Zeitfenster"))
    fig.add_vline(x=tw.horizon, line=dict(color="#c0504d", width=1.5, dash="dash"), annotation_text=f"H = {_fmt(tw.horizon)}", annotation_position="top left", annotation_font_size=11)
    fig.update_layout(barmode="overlay")
    fig.update_yaxes(categoryorder="array", categoryarray=ylabels, autorange="reversed")
    fig.update_xaxes(title_text="Zeit")
    return _base(fig, max(300, 26 * len(ylabels) + 120))


def build_width_chart(rows, key, value, title):
    """Eine Kennzahl der Reihenfolgen über der Fensterbreite (Linien je Reihenfolge); `value` ist "share" (Anteil zulässiger Bögen) oder "gap" (Abstand zum Optimum); nicht zerlegbare Punkte fehlen."""
    fig = go.Figure()
    for k in C.ORDER_KEYS:
        ys = [r["orders"][k][value] for r in rows]
        fig.add_trace(go.Scatter(x=[r["label"] for r in rows], y=ys, mode="lines+markers", name=C.ORDER_NAMES[k], line=dict(color=C.ORDER_COLORS[k], width=3), marker=dict(size=7), connectgaps=False))
    fig.update_xaxes(title_text="Fensterbreite (Anteil von H)")
    fig.update_yaxes(title_text=title, rangemode="tozero")
    return _base(fig, 340)


def build_label_chart(rows):
    """Mittlere und größte Zahl der Pareto-Etiketten je Zustand im exakten Löser über der Fensterbreite."""
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[r["label"] for r in rows], y=[r["labels"] for r in rows], marker_color="#2F6B65", name="Mittel je Zustand", hovertemplate="%{x}: Mittel %{y:.2f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=[r["label"] for r in rows], y=[r["max_labels"] for r in rows], mode="markers", marker=dict(size=10, symbol="diamond", color="#c0504d"), name="Maximum eines Zustands"))
    fig.update_xaxes(title_text="Fensterbreite (Anteil von H)")
    fig.update_yaxes(title_text="Etiketten je Zustand", rangemode="tozero")
    return _base(fig, 320)


def build_bands(gaps_by_key, names, colors, keys):
    """Median des Abstands zur Referenz in Prozent je Reihenfolge, mit Spanne (Minimum bis Maximum) als Fehlerbalken; nicht zerlegbare Reihenfolgen fehlen."""
    keys = [k for k in keys if gaps_by_key.get(k)]
    fig = go.Figure(go.Bar(
        x=[names[k] for k in keys], y=[gaps_by_key[k]["median"] for k in keys], marker_color=[colors[k] for k in keys],
        error_y=dict(type="data", symmetric=False, array=[gaps_by_key[k]["max"] - gaps_by_key[k]["median"] for k in keys], arrayminus=[gaps_by_key[k]["median"] - gaps_by_key[k]["min"] for k in keys]),
        hovertemplate="%{x}: Median %{y:.1f} %<extra></extra>", name="Median (Balken: Minimum bis Maximum)"))
    fig.update_yaxes(title_text="Abstand zur Referenz (%)", rangemode="tozero")
    fig.update_xaxes(tickangle=-25)
    fig = _base(fig, 400)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=120))
    return fig


def build_band_widths(stats_by_width, labels):
    """Median-Abstand je Reihenfolge über allen Fensterbreiten einer Größe und eines Bezugsplans."""
    fig = go.Figure()
    for k in C.ORDER_KEYS:
        fig.add_trace(go.Scatter(x=labels, y=[s["gaps"][k]["median"] if s and s["gaps"][k] else None for s in stats_by_width], mode="lines+markers", name=C.ORDER_NAMES[k],
                                 line=dict(color=C.ORDER_COLORS[k], width=3), marker=dict(size=7), connectgaps=False))
    fig.update_xaxes(title_text="Fensterbreite (Anteil von H)")
    fig.update_yaxes(title_text="Median-Abstand zur Referenz (%)", rangemode="tozero")
    return _base(fig, 340)
