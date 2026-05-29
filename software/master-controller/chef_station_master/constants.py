"""Timing and module constants for the Chef Station master controller."""

MAIN_PHASE_SECONDS = 150
GARNISH_PHASE_SECONDS = 30
TOTAL_GAME_SECONDS = MAIN_PHASE_SECONDS + GARNISH_PHASE_SECONDS

MAIN_PHASE_MODULES = ("simon", "chop", "pan", "pot_temp")
GARNISH_PHASE_MODULES = ("garnish",)
ALL_MODULES = MAIN_PHASE_MODULES + GARNISH_PHASE_MODULES

MODULE_LABELS = {
    "simon": "Simon",
    "chop": "Chop Speed",
    "pan": "Pan Motion",
    "pot_temp": "Pot Balance",
    "garnish": "Garnish",
}

RESULT_LINES = (
    (90, "EXECUTIVE CHEF ENERGY"),
    (80, "LINE COOK LEGEND"),
    (65, "SOUS CHEF IN TRAINING"),
    (45, "PREP COOK PROMISING"),
    (0, "DISH PIT REDEMPTION ARC"),
)
