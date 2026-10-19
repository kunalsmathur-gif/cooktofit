"""Loads the versioned micronutrient reference (ICMR-NIN 2020)."""

import json
from functools import cache
from importlib.resources import files
from typing import Any

from app.targets.models import Physiology, Sex

REFERENCE_FILE = "icmr_nin_2020.json"


@cache
def load() -> dict[str, Any]:
    raw = files("app.targets").joinpath("data", REFERENCE_FILE).read_text(encoding="utf-8")
    data: dict[str, Any] = json.loads(raw)
    return data


def micros(sex: Sex, physiology: Physiology) -> dict[str, float]:
    ref = load()
    values: dict[str, float] = dict(ref["adult"][sex.value])
    if physiology.value.startswith("pregnant"):
        values |= ref["physiology"]["pregnant"]
    elif physiology.value.startswith("lactating"):
        values |= ref["physiology"]["lactating"]
    return values
