"""人格模型抽象基类与组合模型。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from models import PAD, EmotionSignal, ModulateCoeff, ReactionStyle


class Personality(ABC):
    @abstractmethod
    def baseline_pad(self) -> PAD:
        ...

    @abstractmethod
    def modulate(self, signal: EmotionSignal) -> ModulateCoeff:
        ...

    @abstractmethod
    def reaction_style(self) -> ReactionStyle:
        ...

    def decay_lambda_factor(self) -> float:
        return 1.0

    def name(self) -> str:
        return self.__class__.__name__


class CompositePersonality(Personality):
    def __init__(self, members: list[tuple[Personality, float]], primary: Personality | None = None):
        total = sum(w for _, w in members) or 1.0
        self.members = [(p, w / total) for p, w in members]
        self.primary = primary or (self.members[0][0] if self.members else None)

    def baseline_pad(self) -> PAD:
        if not self.members:
            return PAD()
        p = sum(w * m.baseline_pad().pleasure for m, w in self.members)
        a = sum(w * m.baseline_pad().arousal for m, w in self.members)
        d = sum(w * m.baseline_pad().dominance for m, w in self.members)
        return PAD(p, a, d)

    def modulate(self, signal: EmotionSignal) -> ModulateCoeff:
        if not self.members:
            return ModulateCoeff()
        s = sum(w * m.modulate(signal).sensitivity for m, w in self.members)
        pg = sum(w * m.modulate(signal).pos_gain for m, w in self.members)
        ng = sum(w * m.modulate(signal).neg_gain for m, w in self.members)
        return ModulateCoeff(s, pg, ng)

    def reaction_style(self) -> ReactionStyle:
        if self.primary:
            return self.primary.reaction_style()
        return ReactionStyle()

    def decay_lambda_factor(self) -> float:
        if not self.members:
            return 1.0
        return sum(w * m.decay_lambda_factor() for m, w in self.members)

    def name(self) -> str:
        return "Composite(" + ",".join(m.name() for m, _ in self.members) + ")"