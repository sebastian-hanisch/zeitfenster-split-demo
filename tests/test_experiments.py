"""Die fünf Experimente der App per AppTest: Schritt für Schritt (Reihenfolge, lexikographisch), Schrumpfen, Richtung, Etiketten und Zeitschlupf, Bänder; dazu das PDF."""

import os
from pathlib import Path

from streamlit.testing.v1 import AppTest

import zfs_constants as C
import zfs_evaluation as ev
from zfs_pdf_export import build_pdf

APP = str(Path(__file__).resolve().parent.parent / "app.py")
TIMEOUT = int(os.environ.get("APPTEST_TIMEOUT", "300"))
SETTING_KEYS = {"n": "n_slider", "family": "family_select", "depot": "depot_select", "routes": "routes_slider", "fill": "fill_slider", "seed": "seed_input",
                "width": "width_select", "mode": "mode_select", "round": "round_select"}
HAND = "Die Richtung zählt (n = 6, Handrechnung)"


def _app(preset=None) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    if preset:
        at.session_state["permalink_loaded"] = True
        for key, state_key in SETTING_KEYS.items():
            at.session_state[state_key] = C.PRESETS[preset][key]
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
    return at


def _texts(at):
    return " ".join([x.value for x in at.success] + [x.value for x in at.info] + [x.value for x in at.warning] + [x.value for x in at.error])


def test_the_hand_preset_shows_the_hand_numbers_in_the_verdicts():
    text = _texts(_app(HAND))
    assert "kostet 67,99 (26,4 % über dem Optimum)" in text and "10 von 15 Bögen (67 %)" in text and "Optimum 53,79 mit 2 Routen" in text


def test_every_order_can_be_chosen_and_the_lexicographic_toggle_works():
    at = _app(HAND)
    for key in ev.VIEW_KEYS:
        at.radio(key="order_radio").set_value(key).run()
        assert not at.exception, key
        assert ev.VIEW_NAMES[key] in _texts(at)
    at.toggle(key="lex_toggle").set_value(True).run()
    assert not at.exception and "Lexikographisch" in _texts(at)


def test_every_window_width_and_both_reference_plans_render():
    at = _app()
    for mode in range(len(C.MODES)):
        at.selectbox(key="mode_select").set_value(mode).run()
        for width in range(len(C.LIVE_WIDTHS)):
            at.selectbox(key="width_select").set_value(width).run()
            assert not at.exception, (mode, width)
    at.selectbox(key="round_select").set_value(1).run()
    assert not at.exception


def test_without_windows_the_text_says_so():
    at = _app()
    at.selectbox(key="width_select").set_value(len(C.LIVE_WIDTHS) - 1).run()
    assert not at.exception and "Keine Fenster" in _texts(at)


def test_the_direction_experiment_names_the_blocking_customer():
    at = _app(HAND)
    at.radio(key="blocked_radio").set_value("tour").run()
    assert not at.exception
    tables = [m.value for m in at.markdown if m.value.startswith("| Beginn bei Kunde")]
    assert tables and "Kunde 3 käme um 24,6 an, sein Fenster schließt um 24,0" in tables[0]


def test_the_largest_live_size_works_with_the_widest_windows():
    at = _app()
    at.slider(key="n_slider").set_value(12).run()
    assert not at.exception
    at.selectbox(key="width_select").set_value(4).run()
    assert not at.exception and "Etiketten" in _texts(at)


def test_band_selection_for_every_size_plan_and_width():
    at = _app()
    for n in C.BAND_SIZES:
        at.radio(key="band_n").set_value(n).run()
        assert not at.exception, n
        for mode in C.MODES:
            at.radio(key="band_mode").set_value(mode).run()
            assert not at.exception, (n, mode)
            for idx in range(len(C.BAND_WIDTHS)):
                at.radio(key="band_width").set_value(idx).run()
                assert not at.exception, (n, mode, idx)
                assert f"{n} Kunden, Abstand zum" in _texts(at)


def test_pdf_download_button_exists_and_the_pdf_is_built_for_every_preset():
    assert len(_app().get("download_button")) == 1
    for preset in C.PRESETS.values():
        s = ev.Settings(preset["n"], preset["family"], preset["depot"], preset["routes"], preset["fill"], preset["seed"], preset["width"], preset["mode"], preset["round"] == 0)
        data = build_pdf(s, ev.analyse(s))
        assert data[:5] == b"%PDF-" and len(data) > 1500
