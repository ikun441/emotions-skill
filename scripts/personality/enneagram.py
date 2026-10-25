"""九型人格（Enneagram）模型。"""
from __future__ import annotations

from models import PAD, EmotionSignal, ModulateCoeff, ReactionStyle
from personality.base import Personality

BASELINE_TABLE = {
    1: PAD(0.30, 0.40, 0.60),
    2: PAD(0.60, 0.50, 0.40),
    3: PAD(0.50, 0.60, 0.70),
    4: PAD(0.20, 0.50, 0.30),
    5: PAD(0.30, 0.20, 0.50),
    6: PAD(0.30, 0.50, 0.30),
    7: PAD(0.70, 0.70, 0.50),
    8: PAD(0.50, 0.60, 0.80),
    9: PAD(0.50, 0.20, 0.40),
}

DISINTEGRATE = {1: 4, 2: 8, 3: 9, 4: 2, 5: 7, 6: 3, 7: 1, 8: 5, 9: 6}
INTEGRATE = {1: 7, 2: 4, 3: 6, 4: 1, 5: 8, 6: 9, 7: 5, 8: 2, 9: 3}

TONE_TABLE = {
    1: "严谨", 2: "温暖", 3: "高效", 4: "感性", 5: "克制",
    6: "谨慎", 7: "活泼", 8: "直接", 9: "平和",
}


class Enneagram(Personality):
    def __init__(self, type: int = 9, wing: int | None = None, health_level: float = 0.7,
                 stress_arousal_threshold: float = 0.65, current_arousal: float = 0.0):
        self.type = type
        self.wing = wing
        self.health = health_level
        self.stress_threshold = stress_arousal_threshold
        self.current_arousal = current_arousal

    def baseline_pad(self) -> PAD:
        base = BASELINE_TABLE.get(self.type, PAD(0.5, 0.3, 0.5))
        if self.current_arousal > self.stress_threshold:
            base = PAD(
                base.pleasure - 0.15,
                min(1.0, base.arousal + 0.15),
                base.dominance - 0.10,
            )
        if self.wing and self.wing != self.type:
            wing_base = BASELINE_TABLE.get(self.wing, base)
            base = PAD(
                0.7 * base.pleasure + 0.3 * wing_base.pleasure,
                0.7 * base.arousal + 0.3 * wing_base.arousal,
                0.7 * base.dominance + 0.3 * wing_base.dominance,
            )
        return base

    def modulate(self, signal: EmotionSignal) -> ModulateCoeff:
        return ModulateCoeff(
            sensitivity=1.2 - self.health,
            pos_gain=1.0,
            neg_gain=1.0,
        )

    def reaction_style(self) -> ReactionStyle:
        return ReactionStyle(
            tone_hint=TONE_TABLE.get(self.type, "平和"),
            creativity=0.6 if self.type in (4, 7) else 0.4,
            structure=0.7 if self.type in (1, 3, 6) else 0.4,
            empathy_bias=0.7 if self.type in (2, 4, 9) else 0.4,
            directness=0.7 if self.type in (8, 3) else 0.4,
        )

    def name(self) -> str:
        return f"Enneagram{self.type}"