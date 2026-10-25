from models import EmotionState, PAD, DiscreteEmotion, EmotionSignal
from emotion_engine import EmotionEngine
from personality.big_five import BigFive


def test_decay_converges_to_baseline():
    bf = BigFive(0.5, 0.5, 0.5, 0.5, 0.5)
    engine = EmotionEngine()
    state = EmotionState(PAD(0.9, 0.8, 0.7), DiscreteEmotion())
    decayed = engine.decay(state, 1000, bf)
    baseline = bf.baseline_pad()
    assert abs(decayed.pad.pleasure - baseline.pleasure) < 0.01


def test_decay_zero_time_no_change():
    bf = BigFive(0.5, 0.5, 0.5, 0.5, 0.5)
    engine = EmotionEngine()
    state = EmotionState(PAD(0.9, 0.8, 0.7), DiscreteEmotion())
    decayed = engine.decay(state, 0, bf)
    assert abs(decayed.pad.pleasure - 0.9) < 1e-6


def test_update_negative_signal_lowers_valence():
    bf = BigFive(0.5, 0.5, 0.5, 0.5, 0.5)
    engine = EmotionEngine()
    state = EmotionState(PAD(0.5, 0.3, 0.5), DiscreteEmotion())
    state.recompute_derived()
    sig = EmotionSignal(valence=-0.8, arousal=0.6, dominant_emotion="sadness", intensity=0.7, triggers=["难过"])
    result = engine.update(state, sig, bf)
    assert result.new_state.valence < state.valence
    assert "sadness" in result.reason


def test_update_positive_signal_raises_valence():
    bf = BigFive(0.5, 0.5, 0.5, 0.5, 0.5)
    engine = EmotionEngine()
    state = EmotionState(PAD(0.3, 0.3, 0.5), DiscreteEmotion())
    sig = EmotionSignal(valence=0.8, arousal=0.5, dominant_emotion="joy", intensity=0.7, triggers=["开心"])
    result = engine.update(state, sig, bf)
    assert result.new_state.valence > state.valence


def test_deterministic():
    bf = BigFive(0.7, 0.6, 0.4, 0.8, 0.3)
    engine = EmotionEngine()
    state = EmotionState(PAD(0.5, 0.3, 0.5), DiscreteEmotion())
    sig = EmotionSignal(valence=-0.6, arousal=0.5, dominant_emotion="sadness", intensity=0.6, triggers=["难过"])
    r1 = engine.update(state, sig, bf)
    r2 = engine.update(state, sig, bf)
    assert r1.new_state.pad.pleasure == r2.new_state.pad.pleasure
    assert r1.new_state.discrete.joy == r2.new_state.discrete.joy


def test_pad_discrete_roundtrip():
    pad = PAD(0.8, 0.6, 0.5)
    discrete = EmotionEngine.pad_to_discrete(pad)
    assert abs(sum(discrete.values()) - 1.0) < 1e-6
    assert discrete.dominant() == "joy"


def test_high_neuroticism_larger_negative_delta():
    bf_high_n = BigFive(0.5, 0.5, 0.5, 0.5, 0.9)
    bf_low_n = BigFive(0.5, 0.5, 0.5, 0.5, 0.1)
    engine = EmotionEngine()
    state = EmotionState(PAD(0.5, 0.3, 0.5), DiscreteEmotion())
    sig = EmotionSignal(valence=-0.8, arousal=0.6, dominant_emotion="sadness", intensity=0.7)
    r_high = engine.update(state, sig, bf_high_n)
    r_low = engine.update(state, sig, bf_low_n)
    assert abs(r_high.delta_pad.pleasure) > abs(r_low.delta_pad.pleasure)


def test_clamp_invariants():
    bf = BigFive(0.5, 0.5, 0.5, 0.5, 0.9)
    engine = EmotionEngine(learning_rate=1.0)
    state = EmotionState(PAD(0.9, 0.9, 0.9), DiscreteEmotion())
    sig = EmotionSignal(valence=-1.0, arousal=1.0, dominant_emotion="sadness", intensity=1.0)
    result = engine.update(state, sig, bf)
    assert -1.0 <= result.new_state.pad.pleasure <= 1.0
    assert 0.0 <= result.new_state.pad.arousal <= 1.0
    assert -1.0 <= result.new_state.pad.dominance <= 1.0
    assert abs(sum(result.new_state.discrete.values()) - 1.0) < 1e-6