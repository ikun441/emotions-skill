"""MBTI 人格模型。"""
from __future__ import annotations

from models import PAD, EmotionSignal, ModulateCoeff, ReactionStyle
from personality.base import Personality


class MBTI(Personality):
    def __init__(self, dimensions: dict | None = None, type_str: str = "INFP"):
        d = dimensions or {}
        self.E_I = d.get("E_I", 0.0)
        self.S_N = d.get("S_N", 0.0)
        self.T_F = d.get("T_F", 0.0)
        self.J_P = d.get("J_P", 0.0)
        self.type_str = type_str

    def baseline_pad(self) -> PAD:
        return PAD(
            0.5,
            clamp(0.4 + 0.2 * self.E_I, 0, 1),
            0.5 + 0.1 * self.J_P,
        )

    def modulate(self, signal: EmotionSignal) -> ModulateCoeff:
        tf_abs = abs(self.T_F)
        return ModulateCoeff(
            sensitivity=0.6 + 0.4 * tf_abs,
            pos_gain=0.6 + 0.3 * max(0.0, self.E_I),
            neg_gain=0.6 + 0.3 * tf_abs,
        )

    def reaction_style(self) -> ReactionStyle:
        return ReactionStyle(
            tone_hint="直觉" if self.S_N > 0.2 else ("具体" if self.S_N < -0.2 else "平衡"),
            creativity=0.5 + 0.3 * self.S_N,
            structure=0.5 - 0.3 * self.J_P,
            empathy_bias=0.5 + 0.3 * max(0.0, self.T_F),
            directness=0.5 - 0.2 * self.T_F,
        )

    def name(self) -> str:
        return f"MBTI_{self.type_str}"


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))