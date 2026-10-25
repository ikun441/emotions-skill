"""回复风格调制：依据人格 + 情绪生成 StyleDirective。"""
from __future__ import annotations

from models import StyleDirective, PersonalityProfile, EmotionState, clamp
from personality.base import Personality


class StyleComposer:
    def compose(self, profile: PersonalityProfile, state: EmotionState,
                personality: Personality | None = None) -> StyleDirective:
        bf = profile.models.big_five
        mbti = profile.models.mbti

        A = bf.agreeableness if bf.enabled else 0.5
        E = bf.extraversion if bf.enabled else 0.5
        C = bf.conscientiousness if bf.enabled else 0.5
        T_F = mbti.dimensions.get("T_F", 0.0) if mbti.enabled else 0.0
        J_P = mbti.dimensions.get("J_P", 0.0) if mbti.enabled else 0.0

        joy = state.discrete.joy
        sadness = state.discrete.sadness
        valence = state.valence
        arousal = state.pad.arousal

        warmth = clamp(0.4 + 0.3 * A + 0.3 * max(joy, 1 - sadness), 0, 1)
        empathy = clamp(0.3 + 0.4 * max(0.0, -valence) + 0.3 * max(0.0, T_F), 0, 1)
        emoji_tendency = clamp(0.2 + 0.3 * E + 0.2 * A + 0.3 * max(0.0, arousal - 0.3), 0, 1)

        if C > 0.6 or J_P < -0.2:
            verbosity = "详尽"
        elif (mbti.enabled and J_P > 0.2) or arousal < 0.2:
            verbosity = "简洁"
        else:
            verbosity = "适中"

        tone = self._tone_from(valence, arousal)
        if personality is not None:
            hint = personality.reaction_style().tone_hint
            if hint:
                tone = hint

        prompt = self._build_prompt(tone, warmth, empathy, verbosity, emoji_tendency, valence)

        return StyleDirective(
            tone=tone,
            warmth=round(warmth, 3),
            verbosity=verbosity,
            emoji_tendency=round(emoji_tendency, 3),
            empathy=round(empathy, 3),
            prompt_fragment=prompt,
        )

    def _tone_from(self, valence: float, arousal: float) -> str:
        if valence >= 0:
            return "热烈" if arousal > 0.5 else "轻松"
        return "关切" if arousal > 0.4 else "沉静"

    def _build_prompt(self, tone, warmth, empathy, verbosity, emoji, valence) -> str:
        parts = [f"请以{tone}的语气回复"]
        if empathy > 0.6:
            parts.append("先共情回应用户情绪再给出信息")
        if warmth > 0.7:
            parts.append("语气温暖柔和")
        if emoji > 0.4:
            parts.append("可适当使用 emoji")
        elif emoji < 0.2:
            parts.append("避免使用 emoji")
        parts.append(f"回复{verbosity}")
        if valence < -0.3:
            parts.append("给予鼓励与支持")
        return "，".join(parts) + "。"