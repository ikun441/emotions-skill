# emotions-skill 技术设计文档（HLD/LLD）

## 1. 总体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      宿主 LLM / Agent                        │
│   (读取 style_directive + emotion_context 生成最终回复)       │
└───────────────▲─────────────────────────────┬───────────────┘
                │ style_directive              │ user_input
                │ emotion_context             │ ai_reply
┌───────────────┴─────────────────────────────┴───────────────┐
│                     emotions-skill                          │
│                                                              │
│  ┌──────────┐   ┌──────────────┐   ┌────────────────────┐   │
│  │ 情绪感知  │──▶│  情绪引擎     │──▶│  回复风格调制器     │   │
│  │ Perceiver│   │  Engine      │   │  StyleComposer     │   │
│  └──────────┘   └──────┬───────┘   └────────────────────┘   │
│                        │                                      │
│                        │ 调制                                  │
│                        ▼                                      │
│  ┌──────────────────────────────────┐                        │
│  │        人格模型层 Personality      │                        │
│  │  ┌────────┐ ┌──────────┐ ┌─────┐ │                        │
│  │  │ BigFive │ │ Enneagram│ │ MBTI│ │                        │
│  │  └────────┘ └──────────┘ └─────┘ │                        │
│  └──────────────────────────────────┘                        │
│                        │                                      │
│                        ▼                                      │
│  ┌──────────────────────────────────────────────────────┐    │
│  │            持久化层 Storage (JSON 原子读写)            │    │
│  │            data/profiles/<profile_id>.json             │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

### 1.1 分层职责

| 层 | 模块 | 职责 |
|----|------|------|
| 感知层 | `Perceiver` | 从用户文本提取情绪信号（valence/arousal/离散情绪/强度/触发词） |
| 引擎层 | `EmotionEngine` | 衰减 → 感知 → 人格调制 → 更新，输出 Δ 与新状态 |
| 人格层 | `BigFive` / `Enneagram` / `MBTI` | 提供基线情绪、调制系数、反应敏感性 |
| 调制层 | `StyleComposer` | 依据人格 + 情绪生成 `style_directive`（中文指令片段） |
| 持久层 | `Storage` | 档案 JSON 原子读写、history 追加 |

---

## 2. 核心数据流（单轮对话）

```
对话开始
   │
   ▼
[1] Storage.load(profile_id) ──▶ PersonalityProfile (含历史情绪)
   │
   ▼
[2] EmotionEngine.decay(state, elapsed_time, personality)
    ── 衰减：state 向 personality.baseline 收敛
   │
   ▼
[3] Perceiver.perceive(user_input)
    ── 输出 EmotionSignal{valence, arousal, dominant, intensity, triggers}
   │
   ▼
[4] EmotionEngine.update(decayed_state, signal, personality)
    ├── 人格调制系数 = personality.modulate(signal)
    ├── delta = signal × modulate_coeff × learning_rate
    ├── new_state = clamp(decayed_state + delta)
    └── 输出 UpdateResult{new_state, delta, reason, modulate_coeff}
   │
   ▼
[5] StyleComposer.compose(personality, new_state)
    ── 输出 StyleDirective{tone, warmth, verbosity, emoji_tendency, empathy, prompt_fragment}
   │
   ▼
[6] Storage.save(profile_id, updated_profile)  ── 原子写入 + history.append
   │
   ▼
返回给宿主：{ style_directive, emotion_context, update_result }
```

---

## 3. 模块详细设计

### 3.1 人格模型层

#### 3.1.1 BigFive（大五人格 OCEAN）

- 五维度：`openness(O)`、`conscientiousness(C)`、`extraversion(E)`、`agreeableness(A)`、`neuroticism(N)`，均 ∈ [0,1]。
- **基线情绪**：由 E/A/N 推导 PAD 基线：
  - `baseline.pleasure = 0.5 + 0.3*(A - N)`
  - `baseline.arousal = 0.5 + 0.2*(E - 0.5)`
  - `baseline.dominance = 0.5 + 0.2*(C - N)`
- **调制系数**：
  - 情绪敏感性 `sensitivity = 0.5 + N`（高神经质者情绪波动更大）
  - 正向放大 `pos_gain = 0.5 + 0.5*E`（外向者正向情绪增益更高）
  - 负向放大 `neg_gain = 0.5 + N`
- **反应风格**：高 O → 回复更具创意/隐喻；高 C → 结构化/条理；低 A → 更直接。

#### 3.1.2 Enneagram（九型人格）

- 主型 `type ∈ 1..9`，翼型 `wing`，健康水平 `health ∈ [0,1]`（1=健康，0=失健）。
- 每型预置：核心恐惧、核心欲望、基线 PAD、压力/安全方向（整合/解离）。
- **调制**：
  - `sensitivity = 1.2 - health`（健康水平越低，情绪越易波动）
  - 压力下走向解离方向，情绪向该型基线偏移；安全下走向整合方向。
- **反应风格**：按类型映射语气（如 4 号→感性诗意，5 号→理性克制，8 号→直接有力）。

#### 3.1.3 MBTI

- 四维度倾向：`E_I, S_N, T_F, J_P ∈ [-1,1]`（负=内向/感觉/思考/判断，正=外向/直觉/情感/感知）。
- **基线**：`arousal` 随 E_I 升高；`pleasure` 基线中性。
- **调制**：
  - `sensitivity = 0.6 + 0.4*|T_F|`（情感型 F 情绪反应更强）
  - 回复风格：N→抽象/愿景，S→具体/细节，F→共情优先，T→逻辑优先，P→开放/探索，J→结论/计划。

#### 3.1.4 组合模型

当多种模型同时启用时：
- 基线情绪 = 加权平均（权重可配，默认等权）。
- 调制系数 = 各模型调制系数的加权平均。
- 反应风格 = 以"主模型"风格为准，其余作为微调。

---

### 3.2 情绪引擎 EmotionEngine

#### 3.2.1 情绪表征

双表征，互相可转换：

- **PAD 连续**：`{pleasure, arousal, dominance} ∈ [-1,1]^3`
- **离散六情绪**：`{joy, sadness, anger, fear, surprise, disgust}`，归一化（和为 1）。
- `valence = pleasure`，`intensity = |arousal|`。

#### 3.2.2 衰减函数

每次对话前，根据距上次更新的时间间隔 `Δt`（分钟）衰减：

```
decayed = baseline + (current - baseline) * exp(-λ * Δt)
```

- `λ`（衰减率）默认 `0.02`（约 35 分钟衰减至 50%），可由人格调制（高 N 者 λ 更小，情绪持续更久）。
- 离散情绪同步按比例衰减后归一化。

#### 3.2.3 更新函数

```
modulate = personality.modulate(signal)        # 调制系数向量
delta_pad = signal.to_pad() * modulate.sensitivity * lr
delta_pad.pleasure *= modulate.pos_gain  (if signal.valence > 0)
delta_pad.pleasure *= modulate.neg_gain  (if signal.valence < 0)
new_pad = clamp(decayed.pad + delta_pad, -1, 1)
new_discrete = blend(decayed.discrete, signal.discrete, alpha=intensity*modulate.sensitivity)
```

- `lr`（学习率）默认 `0.3`。
- `reason` 记录：触发词 + 调制系数 + 哪个人格维度主导。

#### 3.2.4 PAD ↔ 离散映射

采用 Mehrabian 映射表（见 `references/emotion-model.md`），离散情绪由 PAD 反查最近原型 + 信号直接注入。

---

### 3.3 情绪感知 Perceiver

v1 采用**关键词词典 + 规则**方案（纯标准库，无外部依赖）：

1. 情绪关键词词典（中英文，按六情绪 + 正负效价分组，带权重）。
2. 强度修饰词（"非常/有点/极其" → 倍率）。
3. 否定/转折处理（"不高兴" → 翻转效价）。
4. 标点/重复字符增强（"！！！" → arousal ↑）。
5. 输出 `EmotionSignal`。

> v2 预留语义分析接口（可接入 embedding 相似度），通过 `perceive_strategy` 配置切换。

---

### 3.4 回复风格调制 StyleComposer

输入：`personality` + `emotion_state`，输出 `StyleDirective`：

| 字段 | 说明 | 取值来源 |
|------|------|----------|
| `tone` | 语气 | 由情绪 valence + 人格反应风格决定（温暖/冷静/热烈/克制/严肃/轻松） |
| `warmth` | 共情温度 [0,1] | `0.4 + 0.3*agreeableness + 0.3*max(joy,1-sadness)` |
| `verbosity` | 回复详略 | 高 C/J → 详尽；高 P/低 arousal → 简洁 |
| `emoji_tendency` | emoji 倾向 [0,1] | 高 E/A + 高 arousal → 更高 |
| `empathy` | 共情强度 [0,1] | 用户负效价时升高，受 F 维度放大 |
| `prompt_fragment` | 中文指令片段 | 拼接上述为可直接注入 system prompt 的自然语言 |

`prompt_fragment` 示例：
> "请以温暖、略带共情的语气回复，语气轻松，可适当使用 emoji，保持简洁，先回应用户情绪再给出信息。"

---

### 3.5 持久化 Storage

- 路径：`data/profiles/<profile_id>.json`（可配置根目录）。
- **原子写入**：写 `*.tmp` → `os.replace` 为目标文件，避免半写损坏。
- `history` 保留最近 N 条（默认 50），超出滚动丢弃最早；每条仅存情绪向量 + 摘要（不存原文，可配 `store_raw=false`）。
- 读取时校验 schema 版本，不兼容则备份后重建。

---

## 4. 目录结构

```
emotions-skill/
├── SKILL.md                      # Skill 主文件（frontmatter + 工作流）
├── references/                   # Skill 参考文档（被 SKILL.md 引用）
│   ├── personality-models.md     # 三种人格模型详解
│   ├── emotion-model.md          # 情绪模型（PAD/离散/映射表）
│   └── algorithms.md             # 衰减/更新/调制算法说明
├── scripts/                      # 算法实现（Python，标准库）
│   ├── personality/
│   │   ├── big_five.py
│   │   ├── enneagram.py
│   │   ├── mbti.py
│   │   └── base.py               # Personality 抽象基类
│   ├── emotion_engine.py         # 情绪引擎
│   ├── perceiver.py              # 情绪感知
│   ├── style_composer.py         # 风格调制
│   ├── storage.py                # 持久化
│   ├── models.py                 # 数据类（dataclass）
│   └── cli.py                    # 命令行入口（供 Skill 调用）
├── data/
│   ├── profiles/                 # 人格档案存储（运行时生成）
│   └── lexicon/                  # 情绪关键词词典
│       └── emotion_words.json
├── docs/                         # 开发文档
│   ├── PRD.md
│   ├── design.md                 # 本文件
│   ├── data-model.md             # 数据模型与接口
│   └── algorithm-spec.md         # 算法规格（数学定义）
├── examples/
│   └── trace_example.json        # 可复现对话轨迹示例
└── tests/                        # 单元测试
    └── ...
```

---

## 5. 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 实现语言 | Python 3（标准库） | 算法可读性强、无重型依赖、易复现；Skill 可通过 Bash 调用 `python scripts/cli.py` |
| 情绪表征 | PAD + 离散双表征 | PAD 适合连续计算，离散适合可解释展示与风格映射 |
| 情绪感知 | 关键词词典（v1） | 零依赖、确定性、可复现；v2 预留语义接口 |
| 确定性 vs 随机 | v1 纯确定性 | 评测可复现；v2 可加可控随机 |
| 持久化 | 单 JSON 文件 + 原子写 | 简单可靠，符合 Skill 轻量要求 |
| 人格组合 | 加权平均 + 主模型风格 | 灵活且可解释 |

---

## 6. 风险与对策

| 风险 | 对策 |
|------|------|
| 关键词词典覆盖不足导致感知失灵 | 词典分层 + 未知输入回退中性信号 + v2 语义兜底 |
| 情绪数值发散/卡死 | clamp 到 [-1,1] + 衰减回归基线 + intensity 上限 |
| 多模型组合风格冲突 | 主模型优先 + 其余微调（见 3.1.4） |
| 持久化并发写损坏 | 原子写 + 文件锁（v1 单进程可省） |