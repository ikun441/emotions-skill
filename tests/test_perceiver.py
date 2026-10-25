from perceiver import Perceiver


def test_perceive_joy():
    p = Perceiver()
    sig = p.perceive("我今天非常开心，太棒了！")
    assert sig.dominant_emotion == "joy"
    assert sig.valence > 0
    assert sig.intensity > 0


def test_perceive_sadness():
    p = Perceiver()
    sig = p.perceive("我很难过，失去了陪伴多年的宠物")
    assert sig.dominant_emotion == "sadness"
    assert sig.valence < 0
    assert "难过" in sig.triggers


def test_perceive_anger():
    p = Perceiver()
    sig = p.perceive("我真的好愤怒，气死了！！！")
    assert sig.dominant_emotion == "anger"
    assert sig.valence < 0
    assert sig.arousal > 0.5


def test_perceive_fear():
    p = Perceiver()
    sig = p.perceive("我好害怕，特别担心明天的考试")
    assert sig.dominant_emotion == "fear"
    assert sig.valence < 0


def test_perceive_negation():
    p = Perceiver()
    sig = p.perceive("我今天不开心")
    assert sig.dominant_emotion != "joy" or sig.valence <= 0


def test_perceive_intensifier():
    p = Perceiver()
    sig_normal = p.perceive("我难过")
    sig_intense = p.perceive("我非常难过")
    assert sig_intense.intensity >= sig_normal.intensity


def test_perceive_punct_boost():
    p = Perceiver()
    sig_plain = p.perceive("我生气")
    sig_excl = p.perceive("我生气！！！")
    assert sig_excl.intensity >= sig_plain.intensity


def test_perceive_neutral():
    p = Perceiver()
    sig = p.perceive("今天天气不错")
    assert sig.intensity >= 0.0
    assert sig.valence >= -1.0


def test_perceive_empty():
    p = Perceiver()
    sig = p.perceive("")
    assert sig.valence == 0.0
    assert sig.intensity == 0.0


def test_perceive_english():
    p = Perceiver()
    sig = p.perceive("I am so happy and excited today!")
    assert sig.dominant_emotion == "joy"
    assert sig.valence > 0