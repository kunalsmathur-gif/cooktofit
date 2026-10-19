import pytest

from app.targets.engine import FORMULA_VERSION, apply_overrides, compute
from app.targets.models import Activity, Goal, Persona, Physiology, Profile, Sex


def profile(**kw: object) -> Profile:
    base: dict[str, object] = {
        "sex": Sex.MALE,
        "age": 30,
        "height_cm": 175,
        "weight_kg": 75,
        "activity": Activity.MODERATE,
        "goal": Goal.MAINTAIN,
    }
    return Profile.model_validate(base | kw)


def v(ts: object, key: str) -> float:
    return ts.targets[key].value  # type: ignore[attr-defined, no-any-return]


def codes(ts: object) -> set[str]:
    return {f.code for f in ts.flags}  # type: ignore[attr-defined]


def test_maintenance_male_hand_checked() -> None:
    # BMR 10*75 + 6.25*175 - 5*30 + 5 = 1698.75; x1.55 = 2633 -> 2630
    ts = compute(profile())
    assert v(ts, "kcal") == 2630
    assert v(ts, "protein_g") == 90  # 1.2 g/kg
    assert v(ts, "fat_g") == 73  # 25% of kcal / 9
    assert v(ts, "carbs_g") == 403  # remainder
    assert v(ts, "fibre_g") == 53  # ICMR ~40 g per 2000 kcal
    assert ts.formula_version == FORMULA_VERSION
    assert "Mifflin-St Jeor" in ts.targets["kcal"].why
    assert ts.flags == []


def test_macros_add_up_to_calories() -> None:
    for goal in Goal:
        ts = compute(profile(goal=goal))
        implied = v(ts, "protein_g") * 4 + v(ts, "carbs_g") * 4 + v(ts, "fat_g") * 9
        assert abs(implied - v(ts, "kcal")) <= 10


def test_weight_loss_deficit() -> None:
    # BMR 600 + 1000 - 150 - 161 = 1289; x1.375 = 1772; -550 for 0.5 kg/wk -> 1220
    ts = compute(
        profile(
            sex=Sex.FEMALE, height_cm=160, weight_kg=60, activity=Activity.LIGHT, goal=Goal.LOSE
        )
    )
    assert v(ts, "kcal") == 1220
    assert v(ts, "protein_g") == 96  # 1.6 g/kg
    assert "0.5 kg/week" in ts.targets["kcal"].why


def test_calorie_floor() -> None:
    ts = compute(
        profile(
            sex=Sex.FEMALE,
            age=50,
            height_cm=150,
            weight_kg=50,
            activity=Activity.SEDENTARY,
            goal=Goal.LOSE,
        )
    )
    assert v(ts, "kcal") == 1200
    assert "kcal_floor" in codes(ts)


def test_pace_capped_at_one_percent() -> None:
    ts = compute(profile(weight_kg=70, goal=Goal.LOSE, pace_kg_per_week=1.0))
    assert "pace_capped" in codes(ts)
    assert "0.7 kg/week" in ts.targets["kcal"].why


@pytest.mark.parametrize(
    "kw",
    [
        {"age": 16, "goal": Goal.LOSE},
        {"height_cm": 175, "weight_kg": 55, "goal": Goal.LOSE},  # BMI 18.0
        {"eating_disorder_screen_positive": True, "goal": Goal.LOSE},
        {"insulin_treated_diabetes": True, "goal": Goal.RECOMP},
        {"sex": Sex.FEMALE, "physiology": Physiology.LACTATING_0_6, "goal": Goal.LOSE},
    ],
)
def test_red_flags_force_maintenance(kw: dict[str, object]) -> None:
    ts = compute(profile(**kw))
    assert ts.effective_goal is Goal.MAINTAIN
    assert any(f.severity == "block" for f in ts.flags)


def test_pregnancy_adds_energy_protein_and_iron() -> None:
    base = compute(profile(sex=Sex.FEMALE, height_cm=160, weight_kg=60))
    preg = compute(
        profile(sex=Sex.FEMALE, height_cm=160, weight_kg=60, physiology=Physiology.PREGNANT_T2)
    )
    assert v(preg, "kcal") - v(base, "kcal") == 350
    assert v(preg, "protein_g") > v(base, "protein_g")
    assert (v(base, "iron_mg"), v(preg, "iron_mg")) == (29, 40)


def test_verified_icmr_values() -> None:
    men, women = compute(profile()), compute(profile(sex=Sex.FEMALE))
    assert (v(men, "magnesium_mg"), v(women, "magnesium_mg")) == (385, 325)
    assert (v(men, "iron_mg"), v(women, "iron_mg")) == (19, 29)
    assert v(men, "potassium_mg") == 3500
    lact = compute(profile(sex=Sex.FEMALE, physiology=Physiology.LACTATING_7_12))
    assert v(lact, "calcium_mg") == 1200


def test_advanced_cut_with_katch_mcardle_and_day_split() -> None:
    ts = compute(
        profile(
            age=35,
            height_cm=178,
            weight_kg=80,
            body_fat_pct=18,
            goal=Goal.LOSE,
            persona=Persona.ADVANCED,
            training_days_per_week=4,
        )
    )
    # LBM 65.6 -> BMR 1787; x1.55 = 2770; -550 -> 2220
    assert v(ts, "kcal") == 2220
    assert "Katch-McArdle" in ts.targets["kcal"].why
    assert v(ts, "protein_g") == 160  # 2.0 g/kg
    assert ts.training_day and ts.rest_day
    weekly = 4 * ts.training_day.kcal + 3 * ts.rest_day.kcal
    assert abs(weekly / 7 - v(ts, "kcal")) <= 10  # same weekly total
    assert ts.training_day.kcal > ts.rest_day.kcal
    assert ts.rest_day.kcal >= 1500
    assert set(ts.visible) == set(ts.targets)


def test_known_tdee_wins() -> None:
    ts = compute(profile(known_tdee_kcal=2900, persona=Persona.ADVANCED))
    assert v(ts, "kcal") == 2900
    assert "tracked maintenance" in ts.targets["kcal"].why


def test_kidney_disease_caps_protein() -> None:
    ts = compute(profile(goal=Goal.RECOMP, kidney_disease=True))
    assert v(ts, "protein_g") == 60  # 0.8 g/kg
    assert "kidney_protein_cap" in codes(ts)


def test_obese_protein_uses_adjusted_weight() -> None:
    ts = compute(profile(height_cm=170, weight_kg=110, goal=Goal.MAINTAIN))
    assert v(ts, "protein_g") < 1.2 * 110
    assert "adjusted weight" in ts.targets["protein_g"].why


def test_persona_visibility() -> None:
    assert compute(profile(persona=Persona.BEGINNER)).visible == []
    assert compute(profile(persona=Persona.INTERMEDIATE)).visible == ["kcal", "protein_g"]


def test_micros_present_with_sodium_as_limit() -> None:
    ts = compute(profile())
    for key in ("iron_mg", "calcium_mg", "vitamin_b12_ug", "vitamin_d_ug", "folate_ug"):
        assert ts.targets[key].kind == "min"
    assert ts.targets["sodium_mg"].kind == "max"


def test_deterministic() -> None:
    assert compute(profile()) == compute(profile())


def test_overrides_win_and_keep_computed_value() -> None:
    ts = apply_overrides(compute(profile()), {"protein_g": 200})
    t = ts.targets["protein_g"]
    assert (t.value, t.source, t.computed_value) == (200, "override", 90)
    assert "macros_mismatch" in codes(ts)


def test_override_below_floor_needs_clinician() -> None:
    base = compute(profile())
    assert apply_overrides(base, {"kcal": 1100}).targets["kcal"].value == 1500
    assert apply_overrides(base, {"kcal": 1100}, clinician_set=True).targets["kcal"].value == 1100


def test_override_rejects_unknown_and_negative() -> None:
    base = compute(profile())
    with pytest.raises(ValueError, match="unknown"):
        apply_overrides(base, {"vibes": 1})
    with pytest.raises(ValueError, match=">= 0"):
        apply_overrides(base, {"kcal": -5})


def test_override_drops_stale_day_split() -> None:
    ts = compute(profile(persona=Persona.ADVANCED, training_days_per_week=4))
    assert ts.training_day is not None
    assert apply_overrides(ts, {"kcal": 2500}).training_day is None
