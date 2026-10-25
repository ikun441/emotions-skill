"""情绪感知：从用户文本提取情绪信号（关键词词典法）。"""
from __future__ import annotations

import json
import math
from pathlib import Path

from models import EmotionSignal

EMOTIONS = ("joy", "sadness", "anger", "fear", "surprise", "disgust")


class Perceiver:
    def __init__(self, lexicon_path: str | Path | None = None):
        if lexicon_path is None:
            project_root = Path(__file__).parent.parent
            lexicon_path = project_root / "data" / "lexicon" / "emotion_words.json"
        self.lexicon_path = Path(lexicon_path)
        self.lexicon = self._load_lexicon()

    def _load_lexicon(self) -> dict:
        with open(self.lexicon_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def perceive(self, text: str) -> EmotionSignal:
        if not text or not text.strip():
            return EmotionSignal()

        scores = {e: 0.0 for e in EMOTIONS}
        triggers: list[str] = []

        for emotion in EMOTIONS:
            entry = self.lexicon.get(emotion, {})
            weight = entry.get("weight", 1.0)
            for word in entry.get("words", []):
                idx = text.find(word)
                while idx != -1:
                    if not self._is_negated(text, idx):
                        intens = self._get_intensifier(text, idx)
                        scores[emotion] += weight * intens
                        triggers.append(word)
                    idx = text.find(word, idx + len(word))

        punct_boost = self._punct_boost(text)
        max_score = max(scores.values())

        if max_score <= 1e-9:
            return EmotionSignal(modifiers={"punct_boost": round(punct_boost, 3), "neutral": True})

        total_score = sum(scores.values())
        discrete = {e: (scores[e] / total_score if total_score > 1e-9 else 1 / 6) for e in EMOTIONS}

        dominant = max(EMOTIONS, key=lambda e: discrete[e])
        valence_map = self.lexicon.get("valence_map", {})
        valence = sum(valence_map.get(e, 0.0) * discrete[e] for e in EMOTIONS)

        tau = 1.0
        intensity = min(1.0, (max_score / tau) * punct_boost)
        high_arousal = dominant in ("anger", "fear", "surprise")
        arousal = min(1.0, intensity * (1.0 if high_arousal else 0.7))

        unique_triggers = list(dict.fromkeys(triggers))[:10]
        return EmotionSignal(
            valence=round(valence, 6),
            arousal=round(arousal, 6),
            dominant_emotion=dominant,
            intensity=round(intensity, 6),
            triggers=unique_triggers,
            modifiers={"punct_boost": round(punct_boost, 3)},
        )

    def _is_negated(self, text: str, idx: int) -> bool:
        window = text[max(0, idx - 3):idx]
        for neg in self.lexicon.get("negations", []):
            if neg in window:
                return True
        return False

    def _get_intensifier(self, text: str, idx: int) -> float:
        window = text[max(0, idx - 4):idx]
        best = 1.0
        for word, factor in self.lexicon.get("intensifiers", {}).items():
            if word in window and factor > best:
                best = factor
        return best

    def _punct_boost(self, text: str) -> float:
        r = text.count("！") + text.count("!") + text.count("？") + text.count("?")
        if r == 0:
            return 1.0
        return min(2.0, 1.0 + 0.1 * r)