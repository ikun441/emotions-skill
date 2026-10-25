# 算法说明（Skill 速查）

本文件供 SKILL.md 引用，给出情绪引擎的算法要点。完整数学定义见 [../docs/algorithm-spec.md](../docs/algorithm-spec.md)。

---

## 1. 单轮处理流水

```
load 档案 → decay(衰减) → perceive(感知用户输入) → modulate(人格调制) → update(更新) → compose(风格) → save(持久化)
```

## 2. 衰减（对话前）

```
decayed = baseline + (current - baseline) * exp(-λ_eff * Δt)
λ_eff = λ * (1 - 0.3 * N)        # 高神经质衰减更慢
```

## 3. 感知（用户文本 → 信号）

- 关键词匹配（中英文，按六情绪分组，带权重）。
- 强度修饰词倍率（"非常"×1.3，"有点"×0.7）。
- 否定词翻转效价（窗口=2词）。
- 标点增强（"！！！"→arousal↑）。
- 无命中 → 中性信号。

## 4. 人格调制（信号 → 调制系数）

| 模型 | 敏感性 m_s | 正向增益 m_p | 负向增益 m_n |
|------|-----------|-------------|-------------|
| 大五 | 0.5+N | 0.5+0.5E | 0.5+N |
| 九型 | 1.2-health | 1.0 | 1.0 |
| MBTI | 0.6+0.4·\|T_F\| | 0.6+0.3·max(0,E_I) | 0.6+0.3·\|T_F\| |

多模型组合：基线与系数均按 `weight` 加权平均。

## 5. 更新（衰减态 + 信号 → 新态）

```
ΔP = signal.P * m_s * η * (m_p if valence≥0 else m_n)
ΔA = signal.A * m_s * η
ΔD = signal.D * m_s * η
new_pad = clamp(decayed.pad + (ΔP,ΔA,ΔD), [-1,1])

α = intensity * m_s
new_discrete = normalize((1-α)*decayed.discrete + α*signal.discrete)
```

- η（学习率）默认 0.3。
- reason 记录触发词 + 调制系数 + 主导维度。

## 6. 风格调制（人格 + 情绪 → 指令）

| 字段 | 公式要点 |
|------|----------|
| warmth | 0.4 + 0.3·A(宜人) + 0.3·max(喜, 1−悲) |
| empathy | 0.3 + 0.4·max(0,−valence) + 0.3·max(0,T_F) |
| emoji_tendency | 0.2 + 0.3·E + 0.2·A + 0.3·max(0,arousal−0.3) |
| verbosity | 高C/J→详尽；高P/低arousal→简洁；否则适中 |
| tone | (valence,arousal)象限+人格风格查表 |

`prompt_fragment`：将上述拼为中文自然语言指令，直接注入 LLM system prompt。

## 7. 不变量

- PAD 分量 clamp 到 [-1,1]；arousal ∈ [0,1]。
- 离散六情绪归一化（Σ=1）。
- 确定性：相同 (profile, text, Δt) → 相同输出。
- history 不超过 history_limit（默认 50）。