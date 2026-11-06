"""Presets: Vollständigkeit, gültige Werte, Standard-Preset = Standardeinstellungen; die Zahlen in den Hilfetexten stehen in test_claims.py."""

import zfs_constants as C
import zfs_evaluation as ev
import zfs_presets as P


def _settings(preset: dict) -> ev.Settings:
    return ev.Settings(preset["n"], preset["family"], preset["depot"], preset["routes"], preset["fill"], preset["seed"], preset["width"], preset["mode"], preset["round"] == 0)


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP)
    for name, preset in C.PRESETS.items():
        assert set(preset) == set(P.PRESET_KEYS), name
        assert C.PRESET_HELP[name]


def test_preset_values_are_inside_the_control_bounds():
    for name, preset in C.PRESETS.items():
        for key, state_key in P.PRESET_KEYS.items():
            spec = P.SETTING_SPECS[state_key]
            assert spec.lo <= preset[key] <= spec.hi, (name, key)
        assert (preset["fill"] - C.FILL_MIN) % C.FILL_STEP == 0, name              # Auslastung liegt auf dem Raster des Reglers


def test_default_preset_equals_the_default_settings():
    assert _settings(next(iter(C.PRESETS.values()))) == ev.Settings()


def test_setting_specs_cover_every_preset_key():
    assert set(P.PRESET_KEYS.values()) == set(P.SETTING_SPECS)


def test_every_preset_has_a_distinct_configuration():
    assert len({tuple(sorted(p.items())) for p in C.PRESETS.values()}) == len(C.PRESETS)


def test_band_constants_are_consistent_with_the_live_limit():
    assert max(C.BAND_SIZES) > C.N_MAX and C.N_MAX in C.BAND_SIZES and set(C.BAND_SEEDS) == set(C.BAND_SIZES)
    assert set(C.EXACT_SIZES) <= set(C.BAND_SIZES) and max(C.EXACT_SIZES) == C.N_MAX
    assert set(C.BAND_WIDTHS) <= set(C.LIVE_WIDTHS) and len(C.LIVE_WIDTHS) == len(C.WIDTH_LABELS)
    assert C.FILL_MIN <= C.BAND_FILL <= C.FILL_MAX and C.ROUTES_MIN <= C.BAND_ROUTES <= C.ROUTES_MAX
