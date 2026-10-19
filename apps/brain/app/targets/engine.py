"""Deterministic, explainable nutrition targets (PRD A1-A13, ADR-003).

Pure functions only: same inputs and formula version → same numbers. The LLM never
sets or adjusts these values; it can only explain them.
"""

from collections.abc import Mapping

from app.targets import reference
from app.targets.models import (
    Activity,
    DayVariant,
    Flag,
    Goal,
    Persona,
    Physiology,
    Profile,
    Sex,
    Target,
    TargetSet,
)

FORMULA_VERSION = "2026.10-1"

ACTIVITY_FACTOR = {
    Activity.SEDENTARY: 1.2,
    Activity.LIGHT: 1.375,
    Activity.MODERATE: 1.55,
    Activity.VERY: 1.725,
    Activity.EXTRA: 1.9,
}
KCAL_PER_KG = 7700
DEFAULT_PACE = {Goal.LOSE: 0.5, Goal.GAIN: 0.25}
MAX_LOSS_PCT_BW = 0.01  # per week
MAX_GAIN_PCT_BW = 0.005
KCAL_FLOOR = {Sex.FEMALE: 1200, Sex.MALE: 1500}
FAT_PCT = 0.25
KIDNEY_PROTEIN_CAP = 0.8
LOW_CARB_G = 100
TRAINING_DAY_SHIFT = 0.10
MACROS = ("kcal", "protein_g", "carbs_g", "fat_g", "fibre_g")
VISIBLE_BY_PERSONA: dict[Persona, tuple[str, ...] | None] = {
    Persona.BEGINNER: (),  # plate method first, numbers after "graduation"
    Persona.INTERMEDIATE: ("kcal", "protein_g"),
    Persona.ADVANCED: None,  # everything
}


def _r10(x: float) -> float:
    return float(round(x / 10) * 10)


def _protein_per_kg(p: Profile, goal: Goal) -> tuple[float, str]:
    trains = p.training_days_per_week >= 3
    match goal:
        case Goal.RECOMP:
            return 2.0, "recomposition needs high protein to keep muscle while fat drops"
        case Goal.LOSE if trains and p.persona is Persona.ADVANCED:
            return 2.0, "a cut while training hard: high protein protects muscle"
        case Goal.LOSE:
            return 1.6, "a calorie deficit: extra protein keeps you full and protects muscle"
        case Goal.GAIN:
            return (
                (1.8, "building muscle with regular training")
                if trains
                else (1.6, "gaining weight: protein supports lean gain")
            )
        case _:
            return (
                (1.6, "maintaining with regular training")
                if trains
                else (1.2, "maintaining: comfortably above the 0.83 g/kg ICMR minimum")
            )


def compute(p: Profile) -> TargetSet:
    flags: list[Flag] = []
    ref = reference.load()
    bmi = p.weight_kg / (p.height_cm / 100) ** 2
    pregnant_or_lactating = p.physiology is not Physiology.NONE

    # ---- red flags: never block the user, only block aggressive targets
    goal = p.goal
    no_deficit_reasons = []
    if p.age < 18:
        no_deficit_reasons.append("under 18")
    if bmi < 18.5 and goal is Goal.LOSE:
        no_deficit_reasons.append(f"BMI {bmi:.1f} is already below 18.5")
    if pregnant_or_lactating:
        no_deficit_reasons.append("pregnancy or breastfeeding")
    if p.eating_disorder_screen_positive:
        no_deficit_reasons.append("your answers to the eating-habits questions")
    if p.insulin_treated_diabetes and goal in (Goal.LOSE, Goal.RECOMP):
        no_deficit_reasons.append("insulin-treated diabetes")
    if no_deficit_reasons and goal in (Goal.LOSE, Goal.RECOMP):
        goal = Goal.MAINTAIN
    if no_deficit_reasons:
        flags.append(
            Flag(
                code="see_professional",
                severity="block",
                message="We've set maintenance targets because of "
                + ", ".join(no_deficit_reasons)
                + ". Please check any weight-change plan with a doctor or registered dietitian.",
            )
        )

    # ---- energy
    if p.known_tdee_kcal:
        tdee = float(p.known_tdee_kcal)
        tdee_why = f"your own tracked maintenance of {p.known_tdee_kcal:,} kcal"
    else:
        if p.body_fat_pct is not None:
            lbm = p.weight_kg * (1 - p.body_fat_pct / 100)
            bmr = 370 + 21.6 * lbm
            bmr_why = f"BMR {bmr:,.0f} (Katch-McArdle, {lbm:.1f} kg lean mass)"
        else:
            sex_const = 5 if p.sex is Sex.MALE else -161
            bmr = 10 * p.weight_kg + 6.25 * p.height_cm - 5 * p.age + sex_const
            bmr_why = f"BMR {bmr:,.0f} (Mifflin-St Jeor)"
        factor = ACTIVITY_FACTOR[p.activity]
        tdee = bmr * factor
        tdee_why = f"{bmr_why} × {factor} for {p.activity.value} activity = {tdee:,.0f} maintenance"

    kcal = tdee
    goal_why = "kept at maintenance"
    if goal in (Goal.LOSE, Goal.GAIN):
        pace = p.pace_kg_per_week if p.pace_kg_per_week is not None else DEFAULT_PACE[goal]
        cap_pct = MAX_LOSS_PCT_BW if goal is Goal.LOSE else MAX_GAIN_PCT_BW
        cap = round(p.weight_kg * cap_pct, 2)
        if pace > cap:
            flags.append(
                Flag(
                    code="pace_capped",
                    severity="warn",
                    message=f"Pace limited to {cap} kg/week ({cap_pct:.1%} of body weight).",
                )
            )
            pace = cap
        delta = pace * KCAL_PER_KG / 7
        kcal = tdee - delta if goal is Goal.LOSE else tdee + delta
        verb = "minus" if goal is Goal.LOSE else "plus"
        goal_why = f"{verb} {delta:,.0f}/day for {pace} kg/week"
    elif goal is Goal.RECOMP:
        goal_why = "kept at maintenance for recomposition"

    floor = KCAL_FLOOR[p.sex]
    if kcal < min(floor, tdee):
        kcal = min(floor, tdee)
        flags.append(
            Flag(
                code="kcal_floor",
                severity="warn",
                message=f"Raised to the {floor:,} kcal safety floor.",
            )
        )
        goal_why += f", raised to the {floor:,} kcal floor"

    extra_kcal = ref["energy_extra_kcal"].get(p.physiology.value, 0)
    if extra_kcal:
        kcal += extra_kcal
        goal_why += f", plus {extra_kcal} for {p.physiology.value.replace('_', ' ')} (ICMR-NIN)"
    kcal = _r10(kcal)

    # ---- protein (adjusted body weight above BMI 30 avoids inflated targets)
    ref_weight = p.weight_kg
    if bmi > 30:
        ref_weight = 25 * (p.height_cm / 100) ** 2
    per_kg, protein_reason = _protein_per_kg(p, goal)
    if p.kidney_disease:
        per_kg, protein_reason = min(per_kg, KIDNEY_PROTEIN_CAP), "capped for kidney health"
        flags.append(
            Flag(
                code="kidney_protein_cap",
                severity="block",
                message="Protein is capped at 0.8 g/kg because of kidney disease. "
                "Follow your nephrologist's numbers if they differ.",
            )
        )
    protein = per_kg * ref_weight
    protein_why = f"{per_kg} g/kg × {ref_weight:.0f} kg"
    if ref_weight != p.weight_kg:
        protein_why += " (adjusted weight at BMI 25)"
    protein_why += f": {protein_reason}"
    extra_protein = ref["protein_extra_g"].get(p.physiology.value, 0)
    if extra_protein:
        protein += extra_protein
        protein_why += f", plus {extra_protein} g for {p.physiology.value.replace('_', ' ')}"
    protein = (
        max(protein, ref["protein_rda_g_per_kg"] * p.weight_kg) if not p.kidney_disease else protein
    )
    caps = ref["protein_max_pct_energy"]
    max_pct = caps["pregnant"] if p.physiology.value.startswith("pregnant") else caps["default"]
    protein_cap = kcal * max_pct / 4
    if protein > protein_cap:
        protein = protein_cap
        protein_why += f", capped at {max_pct:.0%} of calories"
    protein = round(protein)

    fat = round(kcal * FAT_PCT / 9)
    carbs = round((kcal - protein * 4 - fat * 9) / 4)
    if carbs < LOW_CARB_G:
        flags.append(
            Flag(
                code="low_carb",
                severity="info",
                message=f"Carbs are under {LOW_CARB_G} g; expect lower training energy.",
            )
        )
    fibre = round(kcal / 1000 * ref["fibre_g_per_1000_kcal"])

    targets: dict[str, Target] = {
        "kcal": Target(value=kcal, unit="kcal", why=f"{tdee_why}, {goal_why}."),
        "protein_g": Target(value=protein, unit="g", why=protein_why + "."),
        "fat_g": Target(
            value=fat,
            unit="g",
            why=f"{FAT_PCT:.0%} of calories (within the WHO 15-30% range), "
            "for hormones and vitamin absorption.",
        ),
        "carbs_g": Target(value=carbs, unit="g", why="The calories left after protein and fat."),
        "fibre_g": Target(
            value=fibre,
            unit="g",
            kind="min",
            why=f"{ref['fibre_g_per_1000_kcal']} g per 1,000 kcal ({ref['reference']}).",
        ),
    }
    group = p.sex.value + (
        "" if not pregnant_or_lactating else f", {p.physiology.value.replace('_', ' ')}"
    )
    for key, value in reference.micros(p.sex, p.physiology).items():
        kind = ref["kinds"].get(key, "min")
        label = "Upper limit" if kind == "max" else "Daily allowance"
        targets[key] = Target(
            value=value,
            unit=ref["units"][key],
            kind=kind,
            why=f"{label} for an adult {group} ({ref['reference']}).",
        )

    training_day = rest_day = None
    t = p.training_days_per_week
    if p.persona is Persona.ADVANCED and 0 < t < 7:
        shift = kcal * TRAINING_DAY_SHIFT
        rest_kcal = kcal - shift * t / (7 - t)
        if goal is Goal.LOSE and rest_kcal < floor:
            shift = (kcal - floor) * (7 - t) / t if kcal > floor else 0.0
            rest_kcal = kcal - shift * t / (7 - t)
        if shift:
            training_day = DayVariant(kcal=_r10(kcal + shift), carbs_g=round(carbs + shift / 4))
            rest_day = DayVariant(
                kcal=_r10(rest_kcal), carbs_g=round(carbs - (kcal - rest_kcal) / 4)
            )

    visible = VISIBLE_BY_PERSONA[p.persona]
    return TargetSet(
        formula_version=FORMULA_VERSION,
        reference=ref["reference"] + f" [{ref['status']}]",
        profile=p,
        effective_goal=goal,
        targets=targets,
        training_day=training_day,
        rest_day=rest_day,
        visible=list(targets) if visible is None else list(visible),
        flags=flags,
    )


def apply_overrides(
    ts: TargetSet, overrides: Mapping[str, float], *, clinician_set: bool = False
) -> TargetSet:
    """User or dietitian numbers win (PRD A4). Calorie floors still apply unless clinician-set."""
    unknown = set(overrides) - set(ts.targets)
    if unknown:
        raise ValueError(f"unknown targets: {sorted(unknown)}")
    flags = list(ts.flags)
    targets = dict(ts.targets)
    floor = KCAL_FLOOR[ts.profile.sex]
    for key, value in overrides.items():
        if value < 0:
            raise ValueError(f"{key} must be >= 0")
        if key == "kcal" and value < floor and not clinician_set:
            flags.append(
                Flag(
                    code="kcal_floor",
                    severity="warn",
                    message=f"Your {value:,.0f} kcal was raised to the {floor:,} kcal floor. "
                    "Mark it as set by a clinician to keep it.",
                )
            )
            value = float(floor)
        old = targets[key]
        targets[key] = old.model_copy(
            update={
                "value": value,
                "source": "override",
                "computed_value": old.value,
                "why": "Set by "
                + ("your clinician" if clinician_set else "you")
                + f" (we computed {old.value:g}).",
            }
        )
    m = {k: targets[k].value for k in ("kcal", "protein_g", "carbs_g", "fat_g")}
    implied = m["protein_g"] * 4 + m["carbs_g"] * 4 + m["fat_g"] * 9
    if abs(implied - m["kcal"]) > 0.1 * m["kcal"]:
        flags.append(
            Flag(
                code="macros_mismatch",
                severity="info",
                message=f"Your macros add up to {implied:,.0f} kcal, not {m['kcal']:,.0f}.",
            )
        )
    # Day variants were derived from the computed set; drop them once the user takes over.
    variants_stale = any(k in overrides for k in MACROS)
    return ts.model_copy(
        update={
            "targets": targets,
            "flags": flags,
            "training_day": None if variants_stale else ts.training_day,
            "rest_day": None if variants_stale else ts.rest_day,
        }
    )
