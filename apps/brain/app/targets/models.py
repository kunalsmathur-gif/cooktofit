from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Sex(StrEnum):
    MALE = "male"
    FEMALE = "female"


class Activity(StrEnum):
    SEDENTARY = "sedentary"  # desk job, little walking
    LIGHT = "light"  # on feet some of the day, or exercise 1-3x/week
    MODERATE = "moderate"  # exercise 3-5x/week
    VERY = "very"  # hard exercise 6-7x/week
    EXTRA = "extra"  # physical job plus training


class Goal(StrEnum):
    LOSE = "lose"
    MAINTAIN = "maintain"
    GAIN = "gain"
    RECOMP = "recomp"


class Persona(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class Physiology(StrEnum):
    NONE = "none"
    PREGNANT_T1 = "pregnant_t1"
    PREGNANT_T2 = "pregnant_t2"
    PREGNANT_T3 = "pregnant_t3"
    LACTATING_0_6 = "lactating_0_6m"
    LACTATING_7_12 = "lactating_7_12m"


class Profile(BaseModel):
    """Everything the engine needs. Snapshotted with each target set."""

    model_config = ConfigDict(frozen=True)

    sex: Sex
    age: int = Field(ge=13, le=100)
    height_cm: float = Field(ge=120, le=230)
    weight_kg: float = Field(ge=30, le=250)
    activity: Activity
    goal: Goal
    persona: Persona = Persona.INTERMEDIATE
    pace_kg_per_week: float | None = Field(default=None, ge=0, le=1.5)
    body_fat_pct: float | None = Field(default=None, ge=3, le=60)
    known_tdee_kcal: int | None = Field(default=None, ge=1000, le=6000)
    training_days_per_week: int = Field(default=0, ge=0, le=7)
    physiology: Physiology = Physiology.NONE
    kidney_disease: bool = False
    insulin_treated_diabetes: bool = False
    eating_disorder_screen_positive: bool = False


Kind = Literal["goal", "min", "max"]


class Target(BaseModel):
    model_config = ConfigDict(frozen=True)

    value: float
    unit: str
    kind: Kind = "goal"
    why: str
    source: Literal["computed", "override"] = "computed"
    computed_value: float | None = None  # kept when overridden


class Flag(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    severity: Literal["info", "warn", "block"]
    message: str


class DayVariant(BaseModel):
    model_config = ConfigDict(frozen=True)

    kcal: float
    carbs_g: float


class TargetSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    formula_version: str
    reference: str
    profile: Profile
    effective_goal: Goal
    targets: dict[str, Target]
    training_day: DayVariant | None = None
    rest_day: DayVariant | None = None
    visible: list[str]
    flags: list[Flag]
