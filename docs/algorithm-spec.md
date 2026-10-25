# emotions-skill 算法规格说明（数学定义）

> 本文档给出所有算法的精确数学定义，确保实现可复现、可评测。符号约定：向量用粗体小写（**p**），标量用斜体小写（*x*）。

---

## 1. 符号表

| 符号 | 含义 | 取值域 |
|------|------|--------|
| **s** = (P, A, D) | PAD 情绪向量 | P,D ∈ [-1,1], A ∈ [0,1] |
| **b** | 人格基线 PAD | 同 **s** |
| **d** = (d_J, d_S, d_A, d_F, d_U, d_G) | 离散六情绪（喜/悲/怒/惧/惊/厌） | d_i ≥ 0, Σd_i = 1 |
| *v* | 效价 valence | [-1,1] |
| *k* | 强度 intensity | [0,1] |
| λ | 衰减率 | > 0，默认 0.02 |
| η | 学习率 | (0,1]，默认 0.3 |
| Δt | 距上次更新分钟数 | ≥ 0 |
| *m* = (m_s, m_p, m_n) | 调制系数（敏感性/正向增益/负向增益） | 各 ∈ [0,2] |

---

## 2. 情绪衰减 Decay

对话前，将当前情绪向人格基线 **b** 衰减收敛：

$$
\mathbf{s}_{decayed} = \mathbf{b} + (\mathbf{s}_{cur} - \mathbf{b}) \cdot e^{-\lambda_{eff} \cdot \Delta t}
$$

其中有效衰减率受人格调制（高神经质者情绪持续更久）：

$$
\lambda_{eff} = \lambda \cdot (1 - 0.3 \cdot N)
$$

离散情绪同步衰减（保持归一化）：

$$
\mathbf{d}_{decayed} = \text{normalize}\big(\mathbf{d}_{baseline} + (\mathbf{d}_{cur} - \mathbf{d}_{baseline}) \cdot e^{-\lambda_{eff} \cdot \Delta t}\big)
$$

---

## 3. 情绪感知 Perceive

输入用户文本 *T*，输出信号 ( *v*, *k*, **d**_sig, triggers )。

### 3.1 关键词匹配

对每个情绪类别 *c* ∈ {J,S,A,F,U,G}，统计命中词加权得分：

$$
score_c = \sum_{w \in T \cap Lex_c} weight_c(w) \cdot intensifier(w) \cdot \mathbb{1}[\text{not negated}(w)]
$$

- `intensifier(w)`：由强度修饰词倍率（默认 1.0）。
- `negated(w)`：检查词前窗口内是否存在否定词（窗口=2 字/词）。

### 3.2 信号合成

$$
\mathbf{d}_{sig} = \text{softmax}(\mathbf{score}) \quad;\quad
v = \sum_c valence_c \cdot d_{sig,c} \quad;\quad
k = \min\big(1,\; \max_c score_c / \tau \big)
$$

- *τ*（命中阈值）默认 1.0。
- 标点增强：`！？` 重复数 *r* → *k* ← min(1, *k* · (1 + 0.1·*r*))。
- 无任何命中 → 中性信号：*v*=0, *k*=0, **d**_sig 均匀。

### 3.3 信号转 PAD

$$
\mathbf{s}_{sig} = (v,\; k,\; 0.5 + 0.3 v)
$$

---

## 4. 人格调制 Modulate

### 4.1 大五人格

基线：
$$
\mathbf{b} = \big(0.5 + 0.3(A - N),\; 0.5 + 0.2(E - 0.5),\; 0.5 + 0.2(C - N)\big)
$$

调制系数：
$$
m_s = 0.5 + N \quad;\quad m_p = 0.5 + 0.5E \quad;\quad m_n = 0.5 + N
$$

### 4.2 九型人格

查表得该型基线 **b**_type 与解离/整合方向。调制：
$$
m_s = 1.2 - health \quad;\quad m_p = m_n = 1.0
$$
压力下（当前 *A* > 阈值）基线向解离型偏移：**b** ← 0.7·**b**_type + 0.3·**b**_disintegrate。

### 4.3 MBTI

$$
m_s = 0.6 + 0.4|T\_F| \quad;\quad m_p = 0.6 + 0.3 \cdot \max(0, E\_I) \quad;\quad m_n = 0.6 + 0.3 \cdot |T\_F|
$$

### 4.4 多模型组合

设启用模型集 *M*，权重 *w_i*，归一化 *W* = Σ*w_i*：

$$
\mathbf{b} = \frac{1}{W}\sum_{i \in M} w_i \mathbf{b}_i \quad;\quad
m_* = \frac{1}{W}\sum_{i \in M} w_i m_{*,i}
$$

---

## 5. 情绪更新 Update

### 5.1 PAD 更新

$$
\Delta P = s_{sig,P} \cdot m_s \cdot \eta \cdot \begin{cases} m_p & v \ge 0 \\ m_n & v < 0 \end{cases}
$$
$$
\Delta A = s_{sig,A} \cdot m_s \cdot \eta \quad;\quad \Delta D = s_{sig,D} \cdot m_s \cdot \eta
$$

$$
\mathbf{s}_{new} = \text{clamp}_{[-1,1]}(\mathbf{s}_{decayed} + (\Delta P, \Delta A, \Delta D))
$$

### 5.2 离散情绪更新

混合系数 *α* = *k* · *m_s*：

$$
\mathbf{d}_{new} = \text{normalize}\big((1-\alpha)\,\mathbf{d}_{decayed} + \alpha\,\mathbf{d}_{sig}\big)
$$

### 5.3 派生量

$$
v_{new} = P_{new} \quad;\quad k_{new} = |A_{new}|
$$

### 5.4 可解释 reason

`reason` = f"用户情绪:{dominant}({triggers}); 敏感性={m_s:.2f}; {'正向' if v>=0 else '负向'}增益={m_p/m_n:.2f}; 主导维度:{top_dim}"

---

## 6. PAD ↔ 离散映射（Mehrabian 简化表）

| 情绪 | P | A | D |
|------|---|---|---|
| joy (喜) | +0.90 | +0.50 | +0.50 |
| sadness (悲) | -0.70 | -0.20 | -0.50 |
| anger (怒) | -0.60 | +0.70 | +0.60 |
| fear (惧) | -0.60 | +0.60 | -0.50 |
| surprise (惊) | +0.20 | +0.90 | -0.20 |
| disgust (厌) | -0.60 | +0.20 | +0.40 |

PAD → 离散：对每个原型计算余弦相似度，取最近者（保留相似度作为强度）。离散 → PAD：加权平均原型坐标。

---

## 7. 风格调制 StyleCompose

| 输出字段 | 公式 |
|----------|------|
| warmth | `clamp(0.4 + 0.3·A_bigfive + 0.3·max(d_J, 1-d_S))` |
| empathy | `clamp(0.3 + 0.4·max(0,-v) + 0.3·max(0,T_F))` （用户负效价时升高，F 维度放大） |
| emoji_tendency | `clamp(0.2 + 0.3·E + 0.2·A + 0.3·max(0,A_pad-0.3))` |
| verbosity | 高 C 或 J_P<0 → "详尽"；高 P 或 A_pad<0.2 → "简洁"；否则 "适中" |
| tone | 由 (valence, arousal) 象限 + 人格反应风格查表：如 (负,高)→"关切"，(正,高)→"热烈"，(负,低)→"沉静"，(正,低)→"轻松" |

`prompt_fragment` 由上述字段模板拼接为自然语言中文指令。

---

## 8. 边界与不变量（实现须校验）

1. 所有 PAD 分量 clamp 到 [-1,1]；arousal 额外 clamp 到 [0,1]。
2. 离散六情绪每次更新后归一化（Σ=1，容差 1e-6）。
3. Δt=0 时退化为纯更新（不衰减）；无信号时退化为纯衰减。
4. 相同 (profile, text, Δt) → 相同输出（确定性）。
5. `history` 长度不超过 `history_limit`，超出丢弃最早条目。