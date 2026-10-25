"""情绪引擎：衰减、更新、PAD↔离散映射。"""
from __future__ import annotations

import math

from models import (
    PAD, DiscreteEmotion, EmotionState, EmotionSignal,
    ModulateCoeff, UpdateResult, clamp, now_iso,
)
from personality.base import Personality

PAD_PROTOTYPES: dict[str, tuple[float, float, float]] = {
    "joy": (0.90, 0.50, 0.50),
    "sadness": (-0.70, -0.20, -0.50),
    "anger": (-0.60, 0.70, 0.60),
    "fear": (-0.60, 0.60, -0.50),
    "surprise": (0.20, 0.90, -0.20),
    "disgust": (-0.60, 0.20, 0.40),
}


class EmotionEngine:
    def __init__(self, decay_lambda: float = 0.02, learning_rate: float = 0.3):
        self.decay_lambda = decay_lambda
        self.learning_rate = learning_rate

    def decay(self, state: EmotionState, elapsed_min: float, personality: Personality) -> EmotionState:
        baseline = personality.baseline_pad()
        lam_eff = self.decay_lambda * personality.decay_lambda_factor()
        factor = math.exp(-lam_eff * max(0.0, elapsed_min))

        new_pad = PAD(
            baseline.pleasure + (state.pad.pleasure - baseline.pleasure) * factor,
            baseline.arousal + (state.pad.arousal - baseline.arousal) * factor,
            baseline.dominance + (state.pad.dominance - baseline.dominance) * factor,
        ).clamp()

        base_discrete = self.pad_to_discrete(baseline)
        dvals = {}
        for f in DiscreteEmotion._FIELDS:
            cur = getattr(state.discrete, f)
            base = getattr(base_discrete, f)
            dvals[f] = base + (cur - base) * factor
        new_discrete = DiscreteEmotion(**dvals).normalize()

        new_state = EmotionState(new_pad, new_discrete)
        new_state.recompute_derived()
        new_state.last_updated_at = state.last_updated_at
        return new_state

    def update(self, decayed: EmotionState, signal: EmotionSignal, personality: Personality) -> UpdateResult:
        coeff = personality.modulate(signal)
        eta = self.learning_rate
        sig_pad = signal.to_pad()

        gain = coeff.pos_gain if signal.valence >= 0 else coeff.neg_gain
        delta_p = sig_pad.pleasure * coeff.sensitivity * eta * gain
        delta_a = sig_pad.arousal * coeff.sensitivity * eta
        delta_d = sig_pad.dominance * coeff.sensitivity * eta

        new_pad = PAD(
            clamp(decayed.pad.pleasure + delta_p, -1, 1),
            clamp(decayed.pad.arousal + delta_a, 0, 1),
            clamp(decayed.pad.dominance + delta_d, -1, 1),
        )

        alpha = min(1.0, signal.intensity * coeff.sensitivity)
        sig_discrete = signal.to_discrete()
        dvals = {}
        for f in DiscreteEmotion._FIELDS:
            dvals[f] = (1 - alpha) * getattr(decayed.discrete, f) + alpha * getattr(sig_discrete, f)
        new_discrete = DiscreteEmotion(**dvals).normalize()

        new_state = EmotionState(new_pad, new_discrete)
        new_state.recompute_derived()
        new_state.last_updated_at = now_iso()

        ddvals = {f: getattr(new_discrete, f) - getattr(decayed.discrete, f) for f in DiscreteEmotion._FIELDS}
        delta_discrete = DiscreteEmotion(**ddvals)

        reason = self._build_reason(signal, coeff, personality)
        return UpdateResult(new_state, decayed, PAD(delta_p, delta_a, delta_d), delta_discrete, coeff, reason)

    def _build_reason(self, signal: EmotionSignal, coeff: ModulateCoeff, personality: Personality) -> str:
        direction = "正向" if signal.valence >= 0 else "负向"
        gain = coeff.pos_gain if signal.valence >= 0 else coeff.neg_gain
        triggers = "/".join(signal.triggers[:3]) if signal.triggers else "无"
        return (
            f"用户情绪:{signal.dominant_emotion}({triggers}); "
            f"敏感性={coeff.sensitivity:.2f}; {direction}增益={gain:.2f}; "
            f"人格={personality.name()}"
        )

    @staticmethod
    def pad_to_discrete(pad: PAD) -> DiscreteEmotion:
        a_signed = 2 * pad.arousal - 1
        target = (pad.pleasure, a_signed, pad.dominance)
        norm_t = math.sqrt(sum(t * t for t in target)) or 1e-9
        sims = {}
        for emo, proto in PAD_PROTOTYPES.items():
            dot = sum(t * p for t, p in zip(target, proto))
            norm_p = math.sqrt(sum(p * p for p in proto)) or 1e-9
            sims[emo] = dot / (norm_t * norm_p)
        min_sim = min(sims.values())
        shifted = {e: s - min_sim + 1e-6 for e, s in sims.items()}
        total = sum(shifted.values())
        return DiscreteEmotion(**{e: shifted[e] / total for e in DiscreteEmotion._FIELDS}).normalize()

    @staticmethod
    def discrete_to_pad(discrete: DiscreteEmotion) -> PAD:
        p = a = d = 0.0
        for emo, proto in PAD_PROTOTYPES.items():
            w = getattr(discrete, emo)
            p += w * proto[0]
            a += w * proto[1]
            d += w * proto[2]
        return PAD(p, (a + 1) / 2, d).clamp()