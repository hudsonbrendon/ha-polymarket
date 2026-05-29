"""Structural consistency checks for the translation files (pure, no HA)."""

import json
import re
from pathlib import Path

COMPONENT = Path(__file__).resolve().parent.parent / "custom_components" / "polymarket"
TRANS = COMPONENT / "translations"
LOCALES = ("en", "es", "pt", "pt-BR")


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _entity_keys(data):
    keys = set()
    for platform, entities in data.get("entity", {}).items():
        for key in entities:
            keys.add(f"{platform}.{key}")
    return keys


def test_all_translation_files_are_valid_json():
    for loc in LOCALES:
        _load(TRANS / f"{loc}.json")
    _load(COMPONENT / "strings.json")


def test_every_locale_has_config_options_entity_sections():
    for loc in LOCALES:
        data = _load(TRANS / f"{loc}.json")
        assert "config" in data, loc
        assert "options" in data, loc
        assert "entity" in data, loc


def test_locales_share_the_same_entity_keys():
    base = _entity_keys(_load(TRANS / "en.json"))
    assert base, "en.json has no entity keys"
    for loc in LOCALES:
        assert _entity_keys(_load(TRANS / f"{loc}.json")) == base, loc
    assert _entity_keys(_load(COMPONENT / "strings.json")) == base


def test_code_translation_keys_have_english_names():
    english = _load(TRANS / "en.json")["entity"]

    def keys_in(filename):
        text = (COMPONENT / filename).read_text(encoding="utf-8")
        return set(re.findall(r'_attr_translation_key\s*=\s*"([^"]+)"', text))

    for key in keys_in("sensor.py"):
        assert key in english.get("sensor", {}), f"sensor.{key} missing in en.json"
    for key in keys_in("binary_sensor.py"):
        assert key in english.get("binary_sensor", {}), (
            f"binary_sensor.{key} missing in en.json"
        )
