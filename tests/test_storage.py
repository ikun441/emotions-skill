from models import (
    PersonalityProfile, Models, BigFiveModel, ProfileConfig,
    HistoryEntry, EmotionSignal, PAD, DiscreteEmotion, ModulateCoeff,
)
from storage import Storage


def test_save_load_roundtrip(tmp_path):
    storage = Storage(tmp_path)
    profile = PersonalityProfile(
        profile_id="p_test", alias="t",
        models=Models(BigFiveModel(0.7, 0.6, 0.4, 0.8, 0.3)),
    )
    storage.save(profile)
    assert storage.exists("p_test")
    loaded = storage.load("p_test")
    assert loaded.profile_id == "p_test"
    assert loaded.models.big_five.openness == 0.7


def test_append_history(tmp_path):
    storage = Storage(tmp_path)
    profile = PersonalityProfile(profile_id="p_h", models=Models(BigFiveModel()))
    storage.save(profile)
    entry = HistoryEntry(
        turn_id=1, timestamp="2026-01-01T00:00:00+08:00",
        signal=EmotionSignal(valence=-0.5),
        emotion_delta_pad=PAD(-0.1, 0, 0), emotion_delta_discrete=DiscreteEmotion(),
        modulate_coeff=ModulateCoeff(), reason="test",
    )
    storage.append_history(profile, entry)
    loaded = storage.load("p_h")
    assert len(loaded.history) == 1
    assert loaded.history[0].reason == "test"


def test_history_limit(tmp_path):
    storage = Storage(tmp_path)
    profile = PersonalityProfile(
        profile_id="p_lim", models=Models(BigFiveModel()),
        config=ProfileConfig(history_limit=3),
    )
    storage.save(profile)
    for i in range(5):
        entry = HistoryEntry(
            turn_id=i + 1, timestamp="2026-01-01T00:00:00+08:00",
            signal=EmotionSignal(), emotion_delta_pad=PAD(),
            emotion_delta_discrete=DiscreteEmotion(), modulate_coeff=ModulateCoeff(),
            reason=f"r{i}",
        )
        storage.append_history(profile, entry)
    loaded = storage.load("p_lim")
    assert len(loaded.history) == 3
    assert loaded.history[0].turn_id == 3


def test_atomic_write_no_tmp_left(tmp_path):
    storage = Storage(tmp_path)
    profile = PersonalityProfile(profile_id="p_atom", models=Models(BigFiveModel()))
    storage.save(profile)
    assert not (tmp_path / "p_atom.json.tmp").exists()
    assert (tmp_path / "p_atom.json").exists()


def test_list_and_delete(tmp_path):
    storage = Storage(tmp_path)
    profile = PersonalityProfile(profile_id="p_del", models=Models(BigFiveModel()))
    storage.save(profile)
    assert "p_del" in storage.list_profiles()
    storage.delete("p_del")
    assert not storage.exists("p_del")