from models import (
    PAD, DiscreteEmotion, EmotionState, EmotionSignal, ModulateCoeff,
    BigFiveModel, EnneagramModel, MbtiModel, Models, PersonalityProfile,
    ProfileConfig, HistoryEntry, clamp,
)


def test_clamp():
    assert clamp(1.5) == 1.0
    assert clamp(-1.5) == -1.0
    assert clamp(0.3) == 0.3
    assert clamp(0.5, 0, 1) == 0.5
    assert clamp(-0.1, 0, 1) == 0.0


def test_pad_clamp():
    p = PAD(1.5, -0.2, 2.0).clamp()
    assert p.pleasure == 1.0
    assert p.arousal == 0.0
    assert p.dominance == 1.0


def test_discrete_normalize():
    d = DiscreteEmotion(2.0, 1.0, 0.0, 1.0, 1.0, 1.0).normalize()
    assert abs(sum(d.values()) - 1.0) < 1e-6
    assert all(v >= 0 for v in d.values())


def test_discrete_dominant():
    d = DiscreteEmotion(0.5, 0.1, 0.1, 0.1, 0.1, 0.1)
    assert d.dominant() == "joy"


def test_emotion_state_recompute():
    s = EmotionState(PAD(0.6, 0.4, 0.5))
    s.recompute_derived()
    assert s.valence == 0.6
    assert s.intensity == 0.4


def test_signal_to_pad():
    sig = EmotionSignal(valence=-0.5, arousal=0.7, dominant_emotion="sadness", intensity=0.7)
    pad = sig.to_pad()
    assert pad.pleasure == -0.5
    assert pad.arousal == 0.7


def test_profile_roundtrip():
    p = PersonalityProfile(
        profile_id="p_test", alias="t", created_at="2026-01-01T00:00:00+08:00",
        updated_at="2026-01-01T00:00:00+08:00",
        models=Models(
            BigFiveModel(0.7, 0.6, 0.4, 0.8, 0.3),
            EnneagramModel(4, 5, 0.65),
            MbtiModel("INFJ", {"E_I": -0.3, "S_N": 0.6, "T_F": 0.4, "J_P": -0.2}, True, 0.8),
        ),
        primary_model="big_five",
    )
    d = p.to_dict()
    p2 = PersonalityProfile.from_dict(d)
    assert p2.profile_id == "p_test"
    assert p2.models.big_five.openness == 0.7
    assert p2.models.enneagram.type == 4
    assert p2.models.mbti.type == "INFJ"
    assert p2.primary_model == "big_five"


def test_history_entry_roundtrip():
    e = HistoryEntry(
        turn_id=1, timestamp="2026-01-01T00:00:00+08:00",
        signal=EmotionSignal(valence=-0.6, arousal=0.5, dominant_emotion="sadness", intensity=0.6, triggers=["难过"]),
        emotion_delta_pad=PAD(-0.1, 0.05, -0.03),
        emotion_delta_discrete=DiscreteEmotion(0.0, 0.1, 0.0, 0.0, 0.0, 0.0),
        modulate_coeff=ModulateCoeff(0.85, 0.72, 0.85),
        reason="test", summary="测试",
    )
    d = e.to_dict()
    e2 = HistoryEntry.from_dict(d)
    assert e2.turn_id == 1
    assert e2.signal.valence == -0.6
    assert e2.reason == "test"