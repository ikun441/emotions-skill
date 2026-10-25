"""大五人格（OCEAN）模型。"""
from __future__ import annotations

from models import PAD, EmotionSignal, ModulateCoeff, ReactionStyle
from personality.base import Personality


class BigFive(Personality):
    def __init__(self, openness=0.5, conscientiousness=0.5, extraversion=0.5,
                 agreeableness=0.5, neuroticism=0.5):
        self.O = openness
        self.C = conscientiousness
        self.E = extraversion
        self.A = agreeableness
        self.N = neuroticism

    def baseline_pad(self) -> PAD:
        return PAD(
            0.5 + 0.3 * (self.A - self.N),
            0.5 + 0.2 * (self.E - 0.5),
            0.5 + 0.2 * (self.C - self.N),
        )

    def modulate(self, signal: EmotionSignal) -> ModulateCoeff:
        return ModulateCoeff(
            sensitivity=0.5 + self.N,
            pos_gain=0.5 + 0.5 * self.E,
            neg_gain=0.5 + self.N,
        )

    def decay_lambda_factor(self) -> float:
        return 1.0 - 0.3 * self.N

    def reaction_style(self) -> ReactionStyle:
        return ReactionStyle(
            tone_hint="创意" if self.O > 0.6 else ("务实" if self.O < 0.4 else "平衡"),
            creativity=self.O,
            structure=self.C,
            empathy_bias=0.4 + 0.4 * self.A,
            directness=0.7 - 0.4 * self.A,
        )

    def name(self) -> str:
        return "BigFive"