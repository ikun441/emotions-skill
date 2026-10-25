"""emotions-skill 命令行入口。用法见 docs/data-model.md §2。"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
from models import (
    BigFiveModel, EnneagramModel, MbtiModel, Models, PersonalityProfile,
    EmotionState, HistoryEntry, now_iso, gen_profile_id, minutes_between,
)
from personality.big_five import BigFive
from personality.enneagram import Enneagram
from personality.mbti import MBTI
from personality.base import CompositePersonality, Personality
from perceiver import Perceiver
from emotion_engine import EmotionEngine
from style_composer import StyleComposer
from storage import Storage


def build_personality(profile: PersonalityProfile) -> Personality:
    members = []
    primary = None
    m = profile.models
    if m.big_five.enabled:
        bf = m.big_five
        p = BigFive(bf.openness, bf.conscientiousness, bf.extraversion, bf.agreeableness, bf.neuroticism)
        members.append((p, bf.weight))
        if profile.primary_model == "big_five":
            primary = p
    if m.enneagram.enabled:
        en = m.enneagram
        p = Enneagram(en.type, en.wing, en.health_level)
        members.append((p, en.weight))
        if profile.primary_model == "enneagram":
            primary = p
    if m.mbti.enabled:
        mb = m.mbti
        p = MBTI(mb.dimensions, mb.type)
        members.append((p, mb.weight))
        if profile.primary_model == "mbti":
            primary = p
    if not members:
        return BigFive()
    if len(members) == 1:
        return members[0][0]
    return CompositePersonality(members, primary)


def _init_state(profile: PersonalityProfile) -> PersonalityProfile:
    p = build_personality(profile)
    baseline = p.baseline_pad()
    discrete = EmotionEngine.pad_to_discrete(baseline)
    profile.emotion_state = EmotionState(baseline, discrete)
    profile.emotion_state.recompute_derived()
    profile.emotion_state.last_updated_at = now_iso()
    return profile


def cmd_init(args):
    bf = BigFiveModel.from_dict(json.loads(args.big_five)) if args.big_five else BigFiveModel(enabled=False)
    en = EnneagramModel.from_dict(json.loads(args.enneagram)) if args.enneagram else EnneagramModel(enabled=False)
    mb = MbtiModel.from_dict(json.loads(args.mbti)) if args.mbti else MbtiModel(enabled=False)
    profile = PersonalityProfile(
        profile_id=gen_profile_id(), alias=args.alias,
        created_at=now_iso(), updated_at=now_iso(),
        models=Models(bf, en, mb), primary_model=args.primary,
    )
    profile = _init_state(profile)
    storage = Storage()
    storage.save(profile)
    print(json.dumps({
        "profile_id": profile.profile_id, "alias": profile.alias,
        "path": str(storage._path(profile.profile_id)),
        "emotion_state": profile.emotion_state.to_dict(),
    }, ensure_ascii=False, indent=2))


def cmd_perceive(args):
    perceiver = Perceiver()
    signal = perceiver.perceive(args.text)
    print(json.dumps(signal.to_dict(), ensure_ascii=False, indent=2))


def cmd_update(args):
    storage = Storage()
    profile = storage.load(args.profile_id)
    p = build_personality(profile)
    engine = EmotionEngine(profile.config.decay_lambda, profile.config.learning_rate)
    perceiver = Perceiver()
    composer = StyleComposer()

    last_ts = profile.emotion_state.last_updated_at
    elapsed = minutes_between(now_iso(), last_ts) if last_ts else 0.0
    decayed = engine.decay(profile.emotion_state, elapsed, p)
    signal = perceiver.perceive(args.text)
    result = engine.update(decayed, signal, p)
    directive = composer.compose(profile, result.new_state, p)

    profile.emotion_state = result.new_state
    profile.updated_at = now_iso()
    turn_id = (profile.history[-1].turn_id + 1) if profile.history else 1
    entry = HistoryEntry(
        turn_id=turn_id, timestamp=now_iso(), signal=signal,
        emotion_delta_pad=result.delta_pad, emotion_delta_discrete=result.delta_discrete,
        modulate_coeff=result.modulate_coeff, reason=result.reason,
        summary=args.summary or "",
        user_input=args.text if profile.config.store_raw_input else "",
    )
    storage.append_history(profile, entry)

    dominant = result.new_state.discrete.dominant()
    emotion_context = (
        f"当前情绪：{dominant}(valence={result.new_state.valence:.2f}, "
        f"intensity={result.new_state.intensity:.2f})；人格：{p.name()}。"
    )
    print(json.dumps({
        "update_result": result.to_dict(),
        "style_directive": directive.to_dict(),
        "emotion_context": emotion_context,
    }, ensure_ascii=False, indent=2))


def cmd_compose(args):
    storage = Storage()
    profile = storage.load(args.profile_id)
    p = build_personality(profile)
    composer = StyleComposer()
    directive = composer.compose(profile, profile.emotion_state, p)
    print(json.dumps(directive.to_dict(), ensure_ascii=False, indent=2))


def cmd_get(args):
    storage = Storage()
    profile = storage.load(args.profile_id)
    print(json.dumps(profile.to_dict(), ensure_ascii=False, indent=2))


def cmd_reset(args):
    storage = Storage()
    profile = storage.load(args.profile_id)
    profile = _init_state(profile)
    profile.updated_at = now_iso()
    storage.save(profile)
    print(json.dumps({"profile_id": profile.profile_id, "reset": True,
                      "emotion_state": profile.emotion_state.to_dict()}, ensure_ascii=False, indent=2))


def cmd_trace(args):
    storage = Storage()
    profile = storage.load(args.profile_id)
    print(json.dumps({
        "profile_id": profile.profile_id, "alias": profile.alias,
        "final_emotion_state": profile.emotion_state.to_dict(),
        "history": [h.to_dict() for h in profile.history],
    }, ensure_ascii=False, indent=2))


def cmd_list(args):
    storage = Storage()
    ids = storage.list_profiles()
    print(json.dumps({"profiles": ids}, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="emotions-skill CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="初始化人格档案")
    p_init.add_argument("--alias", default="default")
    p_init.add_argument("--big-five", default=None)
    p_init.add_argument("--enneagram", default=None)
    p_init.add_argument("--mbti", default=None)
    p_init.add_argument("--primary", default="big_five")
    p_init.set_defaults(func=cmd_init)

    p_per = sub.add_parser("perceive", help="情绪感知")
    p_per.add_argument("--text", required=True)
    p_per.set_defaults(func=cmd_perceive)

    p_upd = sub.add_parser("update", help="情绪更新")
    p_upd.add_argument("--profile-id", required=True)
    p_upd.add_argument("--text", required=True)
    p_upd.add_argument("--summary", default="")
    p_upd.set_defaults(func=cmd_update)

    p_comp = sub.add_parser("compose", help="生成风格指令")
    p_comp.add_argument("--profile-id", required=True)
    p_comp.set_defaults(func=cmd_compose)

    p_get = sub.add_parser("get", help="读取档案")
    p_get.add_argument("--profile-id", required=True)
    p_get.set_defaults(func=cmd_get)

    p_reset = sub.add_parser("reset", help="重置情绪至基线")
    p_reset.add_argument("--profile-id", required=True)
    p_reset.set_defaults(func=cmd_reset)

    p_trace = sub.add_parser("trace", help="导出可复现轨迹")
    p_trace.add_argument("--profile-id", required=True)
    p_trace.set_defaults(func=cmd_trace)

    p_list = sub.add_parser("list", help="列出所有档案")
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()