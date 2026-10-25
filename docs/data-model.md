# emotions-skill 数据模型与接口文档

## 1. 核心数据结构

### 1.1 PersonalityProfile（人格档案，持久化根对象）

```jsonc
{
  "schema_version": "1.0",
  "profile_id": "p_8f3c...e21",
  "alias": "default",
  "created_at": "2026-10-25T15:30:00+08:00",
  "updated_at": "2026-10-25T15:35:12+08:00",
  "models": {
    "big_five": { "openness": 0.75, "conscientiousness": 0.68, "extraversion": 0.45, "agreeableness": 0.82, "neuroticism": 0.35, "enabled": true, "weight": 1.0 },
    "enneagram": { "type": 4, "wing": 5, "health_level": 0.65, "enabled": true, "weight": 1.0 },
    "mbti": { "type": "INFJ", "dimensions": { "E_I": -0.30, "S_N": 0.60, "T_F": 0.40, "J_P": -0.20 }, "enabled": false, "weight": 0.5 }
  },
  "primary_model": "big_five",
  "emotion_state": {
    "pad": { "pleasure": 0.50, "arousal": 0.30, "dominance": 0.60 },
    "discrete": { "joy": 0.55, "sadness": 0.10, "anger": 0.05, "fear": 0.10, "surprise": 0.15, "disgust": 0.05 },
    "valence": 0.40,
    "intensity": 0.30,
    "last_updated_at": "2026-10-25T15:35:12+08:00"
  },
  "config": {
    "decay_lambda": 0.02,
    "learning_rate": 0.30,
    "history_limit": 50,
    "store_raw_input": false
  },
  "history": [
    {
      "turn_id": 1,
      "timestamp": "2026-10-25T15:31:00+08:00",
      "signal": { "valence": -0.6, "arousal": 0.5, "dominant_emotion": "sadness", "intensity": 0.6, "triggers": ["难过", "失去"] },
      "emotion_delta": { "pad": { "pleasure": -0.12, "arousal": 0.08, "dominance": -0.05 }, "discrete": { "sadness": 0.10 } },
      "modulate_coeff": { "sensitivity": 0.85, "pos_gain": 0.72, "neg_gain": 0.85 },
      "reason": "用户表达悲伤(难过/失去)；高神经质(N=0.35→sensitivity=0.85)放大负向；主导维度:neuroticism",
      "summary": "用户倾诉失去宠物的难过"
    }
  ]
}
```

### 1.2 字段约束

| 路径 | 类型 | 约束 |
|------|------|------|
| `models.big_five.*` (5 维) | float | ∈ [0, 1] |
| `models.enneagram.type` | int | ∈ [1, 9] |
| `models.enneagram.wing` | int | ∈ [1, 9]，可为 null |
| `models.enneagram.health_level` | float | ∈ [0, 1] |
| `models.mbti.dimensions.*` | float | ∈ [-1, 1] |
| `emotion_state.pad.*` | float | ∈ [-1, 1] |
| `emotion_state.discrete.*` | float | ≥ 0，六项和 ≈ 1 |
| `config.decay_lambda` | float | > 0 |
| `config.learning_rate` | float | ∈ (0, 1] |

---

### 1.3 EmotionSignal（情绪感知输出，非持久化）

```jsonc
{
  "valence": -0.6,          // [-1,1] 正负效价
  "arousal": 0.5,           // [0,1]  唤醒强度
  "dominant_emotion": "sadness",  // joy|sadness|anger|fear|surprise|disgust|neutral
  "intensity": 0.6,         // [0,1]
  "triggers": ["难过", "失去"],   // 命中的关键词
  "modifiers": { "negation": false, "intensifier": 1.2 }  // 否定/强度修饰
}
```

### 1.4 UpdateResult（情绪引擎输出，非持久化）

```jsonc
{
  "new_state": { /* EmotionState */ },
  "decayed_state": { /* 衰减后、更新前的状态 */ },
  "delta": { "pad": { "pleasure": -0.12, "arousal": 0.08, "dominance": -0.05 }, "discrete": { "sadness": 0.10 } },
  "modulate_coeff": { "sensitivity": 0.85, "pos_gain": 0.72, "neg_gain": 0.85 },
  "reason": "用户表达悲伤...；主导维度:neuroticism"
}
```

### 1.5 StyleDirective（风格调制输出，返回宿主）

```jsonc
{
  "tone": "温暖",
  "warmth": 0.78,
  "verbosity": "适中",
  "emoji_tendency": 0.35,
  "empathy": 0.82,
  "prompt_fragment": "请以温暖、共情的语气回复，先回应用户的悲伤情绪，语气柔和，可少量使用 emoji，内容适度详尽。"
}
```

---

## 2. 对外接口（CLI）

Skill 通过 Bash 调用 `python scripts/cli.py <command> [options]`。所有命令输出 JSON 到 stdout。

### 2.1 init — 初始化档案

```bash
python scripts/cli.py init \
  --alias default \
  --big-five '{"openness":0.75,"conscientiousness":0.68,"extraversion":0.45,"agreeableness":0.82,"neuroticism":0.35}' \
  --enneagram '{"type":4,"wing":5,"health_level":0.65}' \
  --mbti '{"type":"INFJ","dimensions":{"E_I":-0.3,"S_N":0.6,"T_F":0.4,"J_P":-0.2}}' \
  --primary big_five
```
输出：`{ "profile_id": "...", "path": "..." }`

### 2.2 perceive — 情绪感知

```bash
python scripts/cli.py perceive --text "我今天真的很难过，失去了陪伴多年的宠物"
```
输出：`EmotionSignal`（见 1.3）

### 2.3 update — 情绪更新（感知+衰减+调制+持久化）

```bash
python scripts/cli.py update \
  --profile-id p_8f3c...e21 \
  --text "我今天真的很难过，失去了陪伴多年的宠物" \
  --summary "用户倾诉失去宠物的难过"
```
输出：
```jsonc
{
  "update_result": { /* UpdateResult */ },
  "style_directive": { /* StyleDirective */ },
  "emotion_context": "当前情绪：悲伤(valence=-0.12, intensity=0.38)；人格：INFJ/大五偏内向高宜人。"
}
```

### 2.4 compose — 仅生成风格指令（不更新状态）

```bash
python scripts/cli.py compose --profile-id p_8f3c...e21
```
输出：`StyleDirective`（见 1.5）

### 2.5 get — 读取档案

```bash
python scripts/cli.py get --profile-id p_8f3c...e21
```
输出：`PersonalityProfile`

### 2.6 reset — 重置情绪至基线

```bash
python scripts/cli.py reset --profile-id p_8f3c...e21
```

### 2.7 trace — 导出可复现轨迹

```bash
python scripts/cli.py trace --profile-id p_8f3c...e21
```
输出：完整 `history` + 最终状态，用于评测复现。

---

## 3. 内部模块接口（Python）

```python
# personality/base.py
class Personality(ABC):
    def baseline_pad(self) -> PAD: ...
    def modulate(self, signal: EmotionSignal) -> ModulateCoeff: ...
    def reaction_style(self) -> ReactionStyle: ...

# emotion_engine.py
class EmotionEngine:
    def decay(self, state: EmotionState, elapsed_min: float, p: Personality) -> EmotionState: ...
    def update(self, decayed: EmotionState, signal: EmotionSignal, p: Personality) -> UpdateResult: ...

# perceiver.py
class Perceiver:
    def perceive(self, text: str) -> EmotionSignal: ...

# style_composer.py
class StyleComposer:
    def compose(self, p: Personality, state: EmotionState) -> StyleDirective: ...

# storage.py
class Storage:
    def load(self, profile_id: str) -> PersonalityProfile: ...
    def save(self, profile: PersonalityProfile) -> None: ...  # 原子写
    def append_history(self, profile_id: str, entry: HistoryEntry) -> None: ...
```

---

## 4. 情绪关键词词典格式（data/lexicon/emotion_words.json）

```jsonc
{
  "joy":      { "weight": 1.0, "words": ["开心", "快乐", "高兴", "兴奋", "happy", "joy", "glad", ...] },
  "sadness":  { "weight": 1.0, "words": ["难过", "伤心", "悲伤", "失落", "sad", "upset", ...] },
  "anger":    { "weight": 1.0, "words": ["生气", "愤怒", "恼火", "气死", "angry", "mad", ...] },
  "fear":     { "weight": 1.0, "words": ["害怕", "担心", "恐惧", "焦虑", "afraid", "anxious", ...] },
  "surprise": { "weight": 0.8, "words": ["惊讶", "震惊", "没想到", "wow", "surprised", ...] },
  "disgust":  { "weight": 0.8, "words": ["恶心", "讨厌", "反感", "disgusting", "gross", ...] },
  "intensifiers": { "非常": 1.3, "极其": 1.6, "特别": 1.2, "有点": 0.7, "稍微": 0.6, "really": 1.3, "very": 1.3 },
  "negations":    ["不", "没", "别", "无", "not", "no", "never"],
  "valence_map":  { "joy": 1, "surprise": 0.2, "sadness": -1, "anger": -0.8, "fear": -0.7, "disgust": -0.8 }
}
```