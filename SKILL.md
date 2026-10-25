---
name: emotions-skill
description: 让 AI 拥有拟人化且可记忆的情绪与人格。基于大五人格(OCEAN)、九型人格(Enneagram)、MBTI 三种模型建立 AI 人格画像，每轮对话后更新情绪数值并持久化，下一轮对话前读取人格类型与情绪状态生成个性化回复风格指令。当用户希望让 AI/Agent 具备情绪记忆、人格连续性、个性化语气、共情回复，或提到"拟人化情绪""人格模型""情绪状态机""MBTI/大五/九型人格""情绪记忆"时触发本 skill。输出可直接注入 LLM system prompt 的中文风格指令与情绪上下文。
allowed-tools: Read, Write, Bash
---

# emotions-skill：拟人化情绪与人格 Skill

赋予 AI 可持久化的"人格 + 情绪"状态机：每轮对话后更新情绪数值，下一轮读取人格与情绪生成匹配的回复风格。

## 核心能力

1. **人格建模**：大五人格(OCEAN) / 九型人格(Enneagram) / MBTI，可独立或组合使用。
2. **情绪状态机**：PAD 连续模型 + Ekman 六离散情绪双表征，含时间衰减与人格调制。
3. **跨对话记忆**：情绪与人格档案持久化为 JSON，重启后连续。
4. **风格调制**：依据人格 + 当前情绪，输出可直接拼接至 system prompt 的中文指令片段。

## 何时触发

- 用户想让 AI/Agent 有"情绪""人格""性格""人设"且能记忆。
- 提到"拟人化""共情""个性化语气""情绪记忆""人格连续性"。
- 明确提到"大五人格""九型人格""MBTI""OCEAN""Enneagram"。
- 需要每轮对话更新情绪数值并持久化。

## 工作流

### Step 0：确认运行环境

读取 `scripts/` 是否存在算法实现。若仅需要文档/设计，直接引用 `docs/` 下文档。若需要实际运行情绪引擎，确认本机有 Python 3（`python3 --version`）。

### Step 1：建立或加载人格档案

- 若 `data/profiles/` 下无档案 → 执行 `init`：
  - 询问/确认用户希望的人格模型（大五/九型/MBTI/组合）。
  - 大五：可通过 5 个问题快速估测或直接给定 5 维度值。
  - 九型：给定主型(1–9)+翼型+健康水平。
  - MBTI：给定 16 型或 4 维度倾向。
  - 参考 [references/personality-models.md](references/personality-models.md) 了解各模型含义与取值。
- 若已有档案 → 执行 `get` 读取，向用户简述当前人格与情绪状态。

```bash
python3 scripts/cli.py init --alias default \
  --big-five '{"openness":0.75,"conscientiousness":0.68,"extraversion":0.45,"agreeableness":0.82,"neuroticism":0.35}' \
  --enneagram '{"type":4,"wing":5,"health_level":0.65}' \
  --primary big_five
```

### Step 2：对话前——读取情绪与人格，生成风格指令

每轮用户输入到来时，先读取档案当前情绪，生成 `style_directive` 注入 system prompt：

```bash
python3 scripts/cli.py compose --profile-id <id>
```

将返回的 `prompt_fragment` 拼接到 LLM 的 system prompt 末尾，使回复语气与当前人格/情绪匹配。

### Step 3：对话后——感知并更新情绪

AI 回复完成后，用本轮用户输入更新情绪并持久化：

```bash
python3 scripts/cli.py update --profile-id <id> \
  --text "用户本轮输入" --summary "本轮话题摘要"
```

返回包含：
- `update_result`：情绪 Δ、调制系数、可解释 reason（**务必向用户展示 reason，体现可解释性**）。
- `style_directive`：下一轮可用的风格指令。
- `emotion_context`：可读的情绪上下文摘要。

### Step 4：可复现与调试

- 展示情绪变化轨迹：`python3 scripts/cli.py trace --profile-id <id>`。
- 重置情绪至基线：`python3 scripts/cli.py reset --profile-id <id>`。
- 单独测试感知：`python3 scripts/cli.py perceive --text "..."`。

## 算法要点（详见 references）

- **衰减**：每轮前情绪向人格基线指数收敛，`decayed = baseline + (cur - baseline)·exp(-λ·Δt)`；高神经质者衰减更慢。见 [references/algorithms.md](references/algorithms.md)。
- **调制**：人格决定敏感性/正负向增益。如高神经质(N)→情绪波动大；外向(E)→正向增益高；情感型(F)→共情强。
- **更新**：`Δ = signal × modulate × η`，正负向分别用 m_p/m_n 放大，clamp 到 [-1,1]。
- **风格**：由 (valence, arousal) 象限 + 人格反应风格查表得到语气/共情/emoji 倾向/详略。

## 数据与持久化

- 档案路径：`data/profiles/<profile_id>.json`（原子写入）。
- 词典：`data/lexicon/emotion_words.json`（中英文情绪关键词 + 强度修饰 + 否定词）。
- `history` 仅存情绪向量 + 摘要（默认不存原文），保留最近 50 条。
- 完整数据结构见 [../docs/data-model.md](../docs/data-model.md)。

## 输出规范

每次 `update` 后，向用户展示一个简洁的情绪变化卡片：

```
🧭 情绪更新
  输入情绪：悲伤 (valence=-0.6, intensity=0.6)  触发词：难过/失去
  情绪变化 Δ：愉悦 -0.12 · 唤醒 +0.08 · 支配 -0.05
  调制系数：敏感性 0.85 · 负向增益 0.85（高神经质放大）
  当前状态：valence=+0.28 · intensity=0.38 · 主情绪：喜
  风格指令：请以温暖、共情的语气回复，先回应用户情绪……
```

## 约束

- v1 算法纯确定性（相同输入→相同输出），便于评测复现。
- 算法核心仅用 Python 标准库，无重型依赖。
- 不替代底层 LLM，仅输出风格指令与情绪上下文。
- 不做医疗/心理咨询诊断。