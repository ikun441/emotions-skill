from models import (
    PersonalityProfile, Models, BigFiveModel, MbtiModel,
    EmotionState, PAD, DiscreteEmotion,
)
from style_composer import StyleComposer
from personality.big_five import BigFive


def test_compose_basic():
    profile = PersonalityProfile(models=Models(BigFiveModel(0.5, 0.5, 0.5, 0.5, 0.5)))
    state = EmotionState(PAD(0.5, 0.3, 0.5), DiscreteEmotion())
    d = StyleComposer().compose(profile, state, BigFive(0.5, 0.5, 0.5, 0.5, 0.5))
    assert 0 <= d.warmth <= 1
    assert 0 <= d.empathy <= 1
    assert 0 <= d.emoji_tendency <= 1
    assert d.prompt_fragment


def test_negative_valence_high_empathy():
    profile = PersonalityProfile(models=Models(
        BigFiveModel(0.5, 0.5, 0.5, 0.8, 0.5),
        MbtiModel("INFP", {"T_F": 0.6}, True, 1.0),
    ))
    state = EmotionState(PAD(-0.6, 0.5, 0.3), DiscreteEmotion(joy=0.1, sadness=0.5))
    state.recompute_derived()
    d = StyleComposer().compose(profile, state, BigFive(0.5, 0.5, 0.5, 0.8, 0.5))
    assert d.empathy > 0.5


def test_extravert_more_emoji():
    profile_e = PersonalityProfile(models=Models(BigFiveModel(0.5, 0.5, 0.9, 0.5, 0.5)))
    profile_i = PersonalityProfile(models=Models(BigFiveModel(0.5, 0.5, 0.1, 0.5, 0.5)))
    state = EmotionState(PAD(0.5, 0.6, 0.5), DiscreteEmotion())
    composer = StyleComposer()
    d_e = composer.compose(profile_e, state, BigFive(0.5, 0.5, 0.9, 0.5, 0.5))
    d_i = composer.compose(profile_i, state, BigFive(0.5, 0.5, 0.1, 0.5, 0.5))
    assert d_e.emoji_tendency > d_i.emoji_tendency


def test_prompt_fragment_is_chinese():
    profile = PersonalityProfile(models=Models(BigFiveModel(0.7, 0.6, 0.4, 0.8, 0.3)))
    state = EmotionState(PAD(-0.4, 0.5, 0.3), DiscreteEmotion(joy=0.2, sadness=0.4))
    state.recompute_derived()
    d = StyleComposer().compose(profile, state, BigFive(0.7, 0.6, 0.4, 0.8, 0.3))
    assert d.prompt_fragment.startswith("请以")