import json
import subprocess
import sys
from pathlib import Path

CLI = str(Path(__file__).parent.parent / "scripts" / "cli.py")


def run_cli(args, env_dir=None):
    env = None
    if env_dir:
        env = {**__import__("os").environ, "EMOTIONS_PROFILES_DIR": str(env_dir)}
    result = subprocess.run([sys.executable, CLI] + args, capture_output=True, text=True, env=env)
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    return json.loads(result.stdout)


def test_cli_full_flow(tmp_path):
    out = run_cli([
        "init", "--alias", "test_cli",
        "--big-five", '{"openness":0.7,"conscientiousness":0.6,"extraversion":0.3,"agreeableness":0.8,"neuroticism":0.4}',
        "--enneagram", '{"type":4,"wing":5,"health_level":0.7}',
        "--primary", "big_five",
    ], env_dir=tmp_path)
    pid = out["profile_id"]
    assert pid.startswith("p_")
    assert out["emotion_state"]["valence"] is not None

    out2 = run_cli(["update", "--profile-id", pid, "--text", "我今天非常难过，失去了宠物", "--summary", "测试"], env_dir=tmp_path)
    assert "update_result" in out2
    assert "style_directive" in out2
    assert out2["update_result"]["new_state"]["valence"] < out["emotion_state"]["valence"]
    assert out2["style_directive"]["prompt_fragment"]

    out3 = run_cli(["compose", "--profile-id", pid], env_dir=tmp_path)
    assert "prompt_fragment" in out3
    assert out3["warmth"] > 0

    out4 = run_cli(["trace", "--profile-id", pid], env_dir=tmp_path)
    assert len(out4["history"]) == 1
    assert out4["history"][0]["reason"]

    run_cli(["reset", "--profile-id", pid], env_dir=tmp_path)
    out5 = run_cli(["get", "--profile-id", pid], env_dir=tmp_path)
    assert abs(out5["emotion_state"]["valence"] - out["emotion_state"]["valence"]) < 1e-6


def test_cli_perceive(tmp_path):
    out = run_cli(["perceive", "--text", "我真的很开心！"], env_dir=tmp_path)
    assert out["dominant_emotion"] == "joy"
    assert out["valence"] > 0


def test_cli_multi_turn_emotion_drift(tmp_path):
    out = run_cli([
        "init", "--alias", "drift",
        "--big-five", '{"openness":0.5,"conscientiousness":0.5,"extraversion":0.5,"agreeableness":0.5,"neuroticism":0.5}',
        "--primary", "big_five",
    ], env_dir=tmp_path)
    pid = out["profile_id"]
    init_valence = out["emotion_state"]["valence"]

    r1 = run_cli(["update", "--profile-id", pid, "--text", "我好难过", "--summary", "悲伤"], env_dir=tmp_path)
    v1 = r1["update_result"]["new_state"]["valence"]
    assert v1 < init_valence

    r2 = run_cli(["update", "--profile-id", pid, "--text", "谢谢你，感觉好多了", "--summary", "缓和"], env_dir=tmp_path)
    v2 = r2["update_result"]["new_state"]["valence"]
    assert v2 > v1

    r3 = run_cli(["update", "--profile-id", pid, "--text", "明天有新机会，既期待又紧张", "--summary", "期待"], env_dir=tmp_path)
    assert r3["update_result"]["new_state"]["intensity"] > 0

    trace = run_cli(["trace", "--profile-id", pid], env_dir=tmp_path)
    assert len(trace["history"]) == 3