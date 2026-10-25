# emotions-skill 🧠❤️

> 让 AI 拥有拟人化且可记忆的情绪与人格 —— 基于 大五人格(OCEAN) / 九型人格(Enneagram) / MBTI 的情绪状态机

[![tests](https://img.shields.io/badge/tests-46%20passed-brightgreen)]()
[![python](https://img.shields.io/badge/python-3.9%2B-blue)]()
[![deps](https://img.shields.io/badge/dependencies-stdlib%20only-success)]()
[![license](https://img.shields.io/badge/license-MIT-lightgrey)]()

## ✨ 项目简介

**emotions-skill** 是一个 [CodeArts Skill](https://developer.huaweicloud.com/competition/information/1300000350/introduction)，为 AI/Agent 建立可持久化的 **"人格 + 情绪"状态机**：

- 每轮对话后，**感知用户情绪 → 人格调制 → 更新情绪数值 → 持久化**
- 下一轮对话前，**读取人格类型与情绪状态 → 生成个性化回复风格指令**
- 输出可直接注入 LLM `system prompt` 的中文风格指令 + 可解释的情绪变化原因

**解决的核心问题**：AI 回复风格千篇一律、缺乏情绪记忆与人格连续性。

---

## 🎯 核心特性

| 特性 | 说明 |
|------|------|
| **三种人格模型** | 大五人格(OCEAN) / 九型人格(Enneagram) / MBTI，可独立或加权组合 |
| **双表征情绪** | PAD 连续模型（计算）+ Ekman 六离散情绪（展示/风格映射），互相可转换 |
| **情绪衰减** | 无刺激时情绪向人格基线指数收敛，高神经质者衰减更慢（情绪余波更久） |
| **人格调制** | 不同人格对同一刺激反应不同（高神经质→波动大，外向→正向放大，情感型→共情强） |
| **跨对话记忆** | 情绪与人格档案持久化为 JSON（原子写入），重启后连续 |
| **风格调制** | 依据人格+情绪输出语气/共情/emoji倾向/详略的中文指令片段 |
| **可解释** | 每次更新输出 `reason`（触发词+调制系数+主导维度） |
| **确定性** | v1 纯确定性算法，相同输入→相同输出，便于评测复现 |
| **零依赖** | 算法核心仅用 Python 标准库 |

---

## 🏗️ 架构

```
┌─────────────────────────────────────────────────────────────┐
│                      宿主 LLM / Agent                        │
│   (读取 style_directive + emotion_context 生成最终回复)       │
└───────────────▲─────────────────────────────┬───────────────┘
                │ style_directive              │ user_input
┌───────────────┴─────────────────────────────┴───────────────┐
│                     emotions-skill                          │
│  ┌──────────┐   ┌──────────────┐   ┌────────────────────┐   │
│  │ 情绪感知  │──▶│  情绪引擎     │──▶│  回复风格调制器     │   │
│  │Perceiver │   │  Engine      │   │  StyleComposer     │   │
│  └──────────┘   └──────┬───────┘   └────────────────────┘   │
│                        │ 调制                                  │
│  ┌──────────────────────────────────────────┐                │
│  │        人格模型层 Personality              │                │
│  │  ┌────────┐ ┌──────────┐ ┌─────┐         │                │
│  │  │ BigFive │ │Enneagram │ │ MBTI│         │                │
│  │  └────────┘ └──────────┘ └─────┘         │                │
│  └──────────────────────────────────────────┘                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │            持久化层 Storage (JSON 原子读写)            │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

**单轮数据流**：`load → decay(衰减) → perceive(感知) → modulate(人格调制) → update(更新) → compose(风格) → save(持久化)`

---

## 🚀 快速开始

### 环境要求

- Python 3.9+（仅标准库，无需安装任何依赖）

### 1. 初始化人格档案

```bash
python3 scripts/cli.py init --alias default \
  --big-five '{"openness":0.75,"conscientiousness":0.68,"extraversion":0.45,"agreeableness":0.82,"neuroticism":0.35}' \
  --enneagram '{"type":4,"wing":5,"health_level":0.65}' \
  --mbti '{"type":"INFJ","dimensions":{"E_I":-0.3,"S_N":0.6,"T_F":0.4,"J_P":-0.2}}' \
  --primary big_five
```

### 2. 每轮对话后更新情绪

```bash
python3 scripts/cli.py update --profile-id <profile_id> \
  --text "我今天真的很难过，失去了陪伴多年的宠物" \
  --summary "用户倾诉失去宠物的难过"
```

输出：
```jsonc
{
  "update_result": {
    "delta": { "pad": { "pleasure": -0.21, "arousal": 0.15, "dominance": 0.04 } },
    "modulate_coeff": { "sensitivity": 0.72, "pos_gain": 0.82, "neg_gain": 0.97 },
    "reason": "用户情绪:sadness(难过/失去); 敏感性=0.72; 负向增益=0.97; 人格=Composite(BigFive,Enneagram4)"
  },
  "style_directive": {
    "tone": "创意", "warmth": 0.82, "empathy": 0.78,
    "prompt_fragment": "请以创意的语气回复，先共情回应用户情绪再给出信息，语气温暖柔和，回复详尽，给予鼓励与支持。"
  },
  "emotion_context": "当前情绪：sadness(valence=+0.21, intensity=0.59)；人格：Composite(BigFive,Enneagram4)。"
}
```

### 3. 对话前生成风格指令

```bash
python3 scripts/cli.py compose --profile-id <profile_id>
```

### 4. 其他命令

```bash
python3 scripts/cli.py perceive --text "我真的很开心！"   # 单独测试情绪感知
python3 scripts/cli.py get --profile-id <id>              # 读取档案
python3 scripts/cli.py trace --profile-id <id>            # 导出可复现轨迹
python3 scripts/cli.py reset --profile-id <id>            # 重置情绪至基线
python3 scripts/cli.py list                               # 列出所有档案
```

---

## 📂 项目结构

```
emotions-skill/
├── SKILL.md                          # Skill 主文件（frontmatter + 工作流）
├── AGENTS.md                         # 项目规范
├── references/                       # Skill 参考文档
│   ├── personality-models.md         # 三种人格模型详解与风格调制
│   ├── emotion-model.md              # 情绪模型（PAD/离散/映射表/衰减）
│   └── algorithms.md                 # 算法速查
├── scripts/                          # 算法实现（Python 标准库）
│   ├── models.py                     # 数据类与序列化
│   ├── personality/                  # 人格模型
│   │   ├── base.py                   # 抽象基类 + CompositePersonality
│   │   ├── big_five.py               # 大五人格 (OCEAN)
│   │   ├── enneagram.py              # 九型人格
│   │   └── mbti.py                   # MBTI
│   ├── perceiver.py                  # 情绪感知（关键词词典法）
│   ├── emotion_engine.py             # 情绪引擎（衰减/更新/映射）
│   ├── style_composer.py             # 回复风格调制
│   ├── storage.py                    # 持久化（JSON 原子写）
│   └── cli.py                        # 命令行入口
├── data/
│   ├── lexicon/emotion_words.json    # 中英文情绪关键词词典
│   └── profiles/                     # 人格档案存储（运行时生成）
├── docs/                             # 开发文档
│   ├── PRD.md                        # 产品需求文档
│   ├── design.md                     # 技术设计文档
│   ├── data-model.md                 # 数据模型与接口
│   └── algorithm-spec.md             # 算法规格（数学定义）
├── examples/trace_example.json       # 可复现对话轨迹示例
└── tests/                            # 单元测试（46 个，全部通过）
```

---

## 🧮 算法要点

### 情绪衰减（对话前）

```
decayed = baseline + (current - baseline) × exp(-λ_eff × Δt)
λ_eff = λ × (1 - 0.3 × N)    # 高神经质者衰减更慢
```

### 人格调制

| 模型 | 敏感性 m_s | 正向增益 m_p | 负向增益 m_n |
|------|-----------|-------------|-------------|
| 大五 | 0.5+N | 0.5+0.5E | 0.5+N |
| 九型 | 1.2-health | 1.0 | 1.0 |
| MBTI | 0.6+0.4·\|T_F\| | 0.6+0.3·max(0,E_I) | 0.6+0.3·\|T_F\| |

### 情绪更新

```
ΔP = signal.P × m_s × η × (m_p if valence≥0 else m_n)
new_pad = clamp(decayed.pad + Δ, [-1,1])
new_discrete = normalize((1-α) × decayed.discrete + α × signal.discrete)
```

> 完整数学定义见 [docs/algorithm-spec.md](docs/algorithm-spec.md)。

---

## 🧪 测试

```bash
python3 -m pytest tests/ -v
```

```
46 passed in 0.97s
```

覆盖：数据模型序列化、三种人格模型、情绪感知（中英文/否定/强度/标点）、情绪引擎（衰减/更新/确定性/不变量）、风格调制、持久化（原子写/历史滚动）、CLI 端到端集成。

---

## 📊 端到端演示

以 INFJ / 大五偏内向高宜人 / 九型4w5 人格经历 3 轮对话：

| 轮次 | 用户输入 | 情绪 ΔP | 当前 valence | 主情绪 | 风格 |
|------|----------|---------|-------------|--------|------|
| 1 | "失去宠物，很难过" | -0.21 | +0.21 | sadness | 温暖共情 |
| 2 | "谢谢你，感觉好了一些" | +0.18 | +0.39 | joy | 温暖柔和 |
| 3 | "新机会，期待又紧张" | +0.03 | +0.42 | joy | 鼓励详尽 |

valence 逐步回升，体现**情绪记忆**与**人格调制**（高神经质放大负向 Δ）。

---

## 📖 文档

| 文档 | 内容 |
|------|------|
| [docs/PRD.md](docs/PRD.md) | 产品需求：背景/目标/用户故事/功能需求/验收标准 |
| [docs/design.md](docs/design.md) | 技术设计：架构/数据流/模块设计/决策 |
| [docs/data-model.md](docs/data-model.md) | 数据模型与接口：档案结构/CLI命令/Python接口 |
| [docs/algorithm-spec.md](docs/algorithm-spec.md) | 算法规格：衰减/感知/调制/更新的数学定义 |

---

## 🔒 安全说明

- `history` 默认仅存情绪向量 + 摘要（`store_raw_input=false`），不长期留存用户原文。
- 持久化采用原子写入（写 `.tmp` → `os.replace`），避免半写损坏。
- 所有数值 clamp 到约定域（PAD∈[-1,1]，离散归一化）。

---

## 🗺️ 里程碑

- [x] **M0** 开发文档
- [x] **M1** 算法核心实现（46 测试通过）
- [x] **M2** SKILL.md 工作流 + references
- [x] **M3** 示例与可复现轨迹
- [ ] **M4** 打包上传华为云 Skills Marketplace

---

## 📄 许可证

MIT License

---

## 🏆 赛事

华为云开发者大赛（[competition/1300000350](https://developer.huaweicloud.com/competition/information/1300000350/introduction)）