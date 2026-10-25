from models import EmotionSignal, PAD
from personality.big_five import BigFive
from personality.enneagram import Enneagram
from personality.mbti import MBTI
from personality.base import CompositePersonality


def test_big_five_baseline():
    bf = BigFive(0.5, 0.5, 0.5, 0.5, 0.5)
    b = bf.baseline_pad()
    assert abs(b.pleasure - 0.5) < 1e-6
    assert abs(b.arousal - 0.5) < 1e-6


def test_big_five_modulate():
    bf_high_n = BigFive(0.5, 0.5, 0.5, 0.5, 0.9)
    sig = EmotionSignal(valence=-1.0, intensity=0.5)
    coeff = bf_high_n.modulate(sig)
    assert coeff.sensitivity > 1.0
    assert coeff.neg_gain > 1.0

    bf_low_n = BigFive(0.5, 0.5, 0.5, 0.5, 0.1)
    coeff2 = bf_low_n.modulate(sig)
    assert coeff2.sensitivity < coeff.sensitivity


def test_big_five_decay_factor():
    bf = BigFive(0.5, 0.5, 0.5, 0.5, 0.9)
    assert bf.decay_lambda_factor() < 1.0
    bf_low = BigFive(0.5, 0.5, 0.5, 0.5, 0.0)
    assert abs(bf_low.decay_lambda_factor() - 1.0) < 1e-6


def test_enneagram_baseline():
    en4 = Enneagram(4, 5, 0.7)
    b = en4.baseline_pad()
    assert b.pleasure < 0.5
    en7 = Enneagram(7, None, 0.8)
    b7 = en7.baseline_pad()
    assert b7.pleasure > 0.5


def test_enneagram_modulate_health():
    en_unhealthy = Enneagram(4, 5, 0.2)
    en_healthy = Enneagram(4, 5, 0.9)
    sig = EmotionSignal(valence=-0.5, intensity=0.5)
    assert en_unhealthy.modulate(sig).sensitivity > en_healthy.modulate(sig).sensitivity


def test_enneagram_stress_shift():
    en = Enneagram(4, 5, 0.5, current_arousal=0.8)
    b_stress = en.baseline_pad()
    en2 = Enneagram(4, 5, 0.5, current_arousal=0.2)
    b_calm = en2.baseline_pad()
    assert b_stress.pleasure <= b_calm.pleasure


def test_mbti_modulate():
    infp = MBTI({"E_I": -0.4, "S_N": 0.6, "T_F": 0.5, "J_P": 0.2}, "INFP")
    sig = EmotionSignal(valence=0.5, intensity=0.5)
    coeff = infp.modulate(sig)
    assert coeff.sensitivity > 0.6
    assert coeff.pos_gain < 0.7


def test_composite():
    bf = BigFive(0.7, 0.6, 0.3, 0.8, 0.4)
    en = Enneagram(4, 5, 0.7)
    comp = CompositePersonality([(bf, 1.0), (en, 1.0)], primary=bf)
    b = comp.baseline_pad()
    bf_b = bf.baseline_pad()
    en_b = en.baseline_pad()
    expected_p = 0.5 * bf_b.pleasure + 0.5 * en_b.pleasure
    assert abs(b.pleasure - expected_p) < 1e-6
    sig = EmotionSignal(valence=-0.5, intensity=0.5)
    assert comp.modulate(sig).sensitivity > 0
    assert comp.reaction_style().tone_hint == bf.reaction_style().tone_hint