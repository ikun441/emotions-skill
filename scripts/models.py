"""emotions-skill 核心数据模型。纯标准库 dataclass + 类型注解。"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional


def clamp(value: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def minutes_between(t1: str, t2: str) -> float:
    try:
        return abs((parse_iso(t1) - parse_iso(t2)).total_seconds()) / 60.0
    except Exception:
        return 0.0


def gen_profile_id() -> str:
    return "p_" + uuid.uuid4().hex[:12]


@dataclass
class PAD:
    pleasure: float = 0.0
    arousal: float = 0.0
    dominance: float = 0.0

    def clamp(self) -> "PAD":
        return PAD(
            clamp(self.pleasure, -1, 1),
            clamp(self.arousal, 0, 1),
            clamp(self.dominance, -1, 1),
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "PAD":
        return cls(d.get("pleasure", 0.0), d.get("arousal", 0.0), d.get("dominance", 0.0))


@dataclass
class DiscreteEmotion:
    joy: float = 1 / 6
    sadness: float = 1 / 6
    anger: float = 1 / 6
    fear: float = 1 / 6
    surprise: float = 1 / 6
    disgust: float = 1 / 6

    _FIELDS = ("joy", "sadness", "anger", "fear", "surprise", "disgust")

    def values(self) -> list[float]:
        return [getattr(self, f) for f in self._FIELDS]

    def normalize(self) -> "DiscreteEmotion":
        vals = [max(0.0, v) for v in self.values()]
        total = sum(vals)
        if total <= 1e-9:
            n = 1 / 6
            return DiscreteEmotion(n, n, n, n, n, n)
        normed = [v / total for v in vals]
        return DiscreteEmotion(*normed)

    def dominant(self) -> str:
        return max(self._FIELDS, key=lambda f: getattr(self, f))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "DiscreteEmotion":
        n = 1 / 6
        return cls(
            d.get("joy", n), d.get("sadness", n), d.get("anger", n),
            d.get("fear", n), d.get("surprise", n), d.get("disgust", n),
        ).normalize()


@dataclass
class EmotionState:
    pad: PAD = field(default_factory=PAD)
    discrete: DiscreteEmotion = field(default_factory=DiscreteEmotion)
    valence: float = 0.0
    intensity: float = 0.0
    last_updated_at: str = ""

    def recompute_derived(self) -> "EmotionState":
        self.valence = self.pad.pleasure
        self.intensity = abs(self.pad.arousal)
        return self

    def to_dict(self) -> dict:
        return {
            "pad": self.pad.to_dict(),
            "discrete": self.discrete.to_dict(),
            "valence": round(self.valence, 6),
            "intensity": round(self.intensity, 6),
            "last_updated_at": self.last_updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EmotionState":
        return cls(
            PAD.from_dict(d.get("pad", {})),
            DiscreteEmotion.from_dict(d.get("discrete", {})),
            d.get("valence", 0.0),
            d.get("intensity", 0.0),
            d.get("last_updated_at", ""),
        )


@dataclass
class EmotionSignal:
    valence: float = 0.0
    arousal: float = 0.0
    dominant_emotion: str = "neutral"
    intensity: float = 0.0
    triggers: list[str] = field(default_factory=list)
    modifiers: dict = field(default_factory=dict)

    def to_pad(self) -> PAD:
        return PAD(self.valence, clamp(self.arousal, 0, 1), clamp(0.5 + 0.3 * self.valence, -1, 1))

    def to_discrete(self) -> DiscreteEmotion:
        base = DiscreteEmotion()
        if self.dominant_emotion in DiscreteEmotion._FIELDS and self.intensity > 1e-9:
            d = {f: (1 / 6) for f in DiscreteEmotion._FIELDS}
            d[self.dominant_emotion] += self.intensity
            base = DiscreteEmotion(**d).normalize()
        return base

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "EmotionSignal":
        return cls(
            d.get("valence", 0.0), d.get("arousal", 0.0),
            d.get("dominant_emotion", "neutral"), d.get("intensity", 0.0),
            d.get("triggers", []), d.get("modifiers", {}),
        )


@dataclass
class ModulateCoeff:
    sensitivity: float = 1.0
    pos_gain: float = 1.0
    neg_gain: float = 1.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ModulateCoeff":
        return cls(d.get("sensitivity", 1.0), d.get("pos_gain", 1.0), d.get("neg_gain", 1.0))


@dataclass
class UpdateResult:
    new_state: EmotionState
    decayed_state: EmotionState
    delta_pad: PAD
    delta_discrete: DiscreteEmotion
    modulate_coeff: ModulateCoeff
    reason: str

    def to_dict(self) -> dict:
        return {
            "new_state": self.new_state.to_dict(),
            "decayed_state": self.decayed_state.to_dict(),
            "delta": {
                "pad": self.delta_pad.to_dict(),
                "discrete": self.delta_discrete.to_dict(),
            },
            "modulate_coeff": self.modulate_coeff.to_dict(),
            "reason": self.reason,
        }


@dataclass
class StyleDirective:
    tone: str = "平和"
    warmth: float = 0.5
    verbosity: str = "适中"
    emoji_tendency: float = 0.2
    empathy: float = 0.5
    prompt_fragment: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ReactionStyle:
    tone_hint: str = ""
    creativity: float = 0.5
    structure: float = 0.5
    empathy_bias: float = 0.5
    directness: float = 0.5


@dataclass
class BigFiveModel:
    openness: float = 0.5
    conscientiousness: float = 0.5
    extraversion: float = 0.5
    agreeableness: float = 0.5
    neuroticism: float = 0.5
    enabled: bool = True
    weight: float = 1.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "BigFiveModel":
        return cls(
            d.get("openness", 0.5), d.get("conscientiousness", 0.5),
            d.get("extraversion", 0.5), d.get("agreeableness", 0.5),
            d.get("neuroticism", 0.5), d.get("enabled", True), d.get("weight", 1.0),
        )


@dataclass
class EnneagramModel:
    type: int = 9
    wing: Optional[int] = None
    health_level: float = 0.7
    enabled: bool = True
    weight: float = 1.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "EnneagramModel":
        return cls(
            d.get("type", 9), d.get("wing"), d.get("health_level", 0.7),
            d.get("enabled", True), d.get("weight", 1.0),
        )


@dataclass
class MbtiModel:
    type: str = "INFP"
    dimensions: dict = field(default_factory=lambda: {"E_I": 0.0, "S_N": 0.0, "T_F": 0.0, "J_P": 0.0})
    enabled: bool = False
    weight: float = 0.5

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "MbtiModel":
        return cls(
            d.get("type", "INFP"),
            d.get("dimensions", {"E_I": 0.0, "S_N": 0.0, "T_F": 0.0, "J_P": 0.0}),
            d.get("enabled", False), d.get("weight", 0.5),
        )


@dataclass
class Models:
    big_five: BigFiveModel = field(default_factory=BigFiveModel)
    enneagram: EnneagramModel = field(default_factory=EnneagramModel)
    mbti: MbtiModel = field(default_factory=MbtiModel)

    def to_dict(self) -> dict:
        return {"big_five": self.big_five.to_dict(), "enneagram": self.enneagram.to_dict(), "mbti": self.mbti.to_dict()}

    @classmethod
    def from_dict(cls, d: dict) -> "Models":
        return cls(
            BigFiveModel.from_dict(d.get("big_five", {})),
            EnneagramModel.from_dict(d.get("enneagram", {})),
            MbtiModel.from_dict(d.get("mbti", {})),
        )


@dataclass
class ProfileConfig:
    decay_lambda: float = 0.02
    learning_rate: float = 0.3
    history_limit: int = 50
    store_raw_input: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ProfileConfig":
        return cls(
            d.get("decay_lambda", 0.02), d.get("learning_rate", 0.3),
            d.get("history_limit", 50), d.get("store_raw_input", False),
        )


@dataclass
class HistoryEntry:
    turn_id: int
    timestamp: str
    signal: EmotionSignal
    emotion_delta_pad: PAD
    emotion_delta_discrete: DiscreteEmotion
    modulate_coeff: ModulateCoeff
    reason: str
    summary: str = ""
    user_input: str = ""

    def to_dict(self) -> dict:
        return {
            "turn_id": self.turn_id,
            "timestamp": self.timestamp,
            "signal": self.signal.to_dict(),
            "emotion_delta": {"pad": self.emotion_delta_pad.to_dict(), "discrete": self.emotion_delta_discrete.to_dict()},
            "modulate_coeff": self.modulate_coeff.to_dict(),
            "reason": self.reason,
            "summary": self.summary,
            **({"user_input": self.user_input} if self.user_input else {}),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "HistoryEntry":
        delta = d.get("emotion_delta", {})
        return cls(
            d.get("turn_id", 0), d.get("timestamp", ""),
            EmotionSignal.from_dict(d.get("signal", {})),
            PAD.from_dict(delta.get("pad", {})),
            DiscreteEmotion.from_dict(delta.get("discrete", {})),
            ModulateCoeff.from_dict(d.get("modulate_coeff", {})),
            d.get("reason", ""), d.get("summary", ""), d.get("user_input", ""),
        )


@dataclass
class PersonalityProfile:
    schema_version: str = "1.0"
    profile_id: str = ""
    alias: str = "default"
    created_at: str = ""
    updated_at: str = ""
    models: Models = field(default_factory=Models)
    primary_model: str = "big_five"
    emotion_state: EmotionState = field(default_factory=EmotionState)
    config: ProfileConfig = field(default_factory=ProfileConfig)
    history: list[HistoryEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "profile_id": self.profile_id,
            "alias": self.alias,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "models": self.models.to_dict(),
            "primary_model": self.primary_model,
            "emotion_state": self.emotion_state.to_dict(),
            "config": self.config.to_dict(),
            "history": [h.to_dict() for h in self.history],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PersonalityProfile":
        return cls(
            d.get("schema_version", "1.0"),
            d.get("profile_id", ""),
            d.get("alias", "default"),
            d.get("created_at", ""),
            d.get("updated_at", ""),
            Models.from_dict(d.get("models", {})),
            d.get("primary_model", "big_five"),
            EmotionState.from_dict(d.get("emotion_state", {})),
            ProfileConfig.from_dict(d.get("config", {})),
            [HistoryEntry.from_dict(h) for h in d.get("history", [])],
        )