# AGENTS.md — emotions-skill 项目规范

## 项目简介

emotions-skill 是一个 CodeArts Skill，通过大五人格(OCEAN)、九型人格(Enneagram)、MBTI 三种模型为 AI 建立可持久化的"人格 + 情绪"状态机，使 AI 情绪拟人化且具备跨对话记忆。

赛事：华为云开发者大赛（competition/1300000350）。

## 开发文档索引

| 文档 | 内容 |
|------|------|
| [docs/PRD.md](docs/PRD.md) | 产品需求：背景、目标、用户故事、功能/非功能需求、验收标准 |
| [docs/design.md](docs/design.md) | 技术设计：架构、数据流、模块设计、目录结构、决策 |
| [docs/data-model.md](docs/data-model.md) | 数据模型与接口：档案结构、CLI 命令、Python 模块接口、词典格式 |
| [docs/algorithm-spec.md](docs/algorithm-spec.md) | 算法规格：衰减/感知/调制/更新的数学定义与不变量 |
| [SKILL.md](SKILL.md) | Skill 主文件：frontmatter + 工作流（触发/初始化/对话前/对话后） |
| [references/personality-models.md](references/personality-models.md) | 三种人格模型详解与风格调制 |
| [references/emotion-model.md](references/emotion-model.md) | 情绪模型：PAD/离散/映射表/衰减 |
| [references/algorithms.md](references/algorithms.md) | 算法速查（供 Skill 引用） |

## 技术栈

- **算法实现**：Python 3（仅标准库，无重型依赖）
- **Skill 形态**：SKILL.md（frontmatter）+ references/ + scripts/
- **持久化**：JSON 单文件，原子写入（写 .tmp → os.replace）
- **确定性**：v1 纯确定性算法，相同输入→相同输出（便于评测复现）

## 目录结构

```
emotions-skill/
├── SKILL.md                  # Skill 主文件
├── AGENTS.md                 # 本文件
├── references/               # Skill 参考文档
├── scripts/                  # 算法实现（Python）  [M1 待实现]
│   ├── personality/          # big_five/enneagram/mbti/base
│   ├── emotion_engine.py
│   ├── perceiver.py
│   ├── style_composer.py
│   ├── storage.py
│   ├── models.py
│   └── cli.py
├── data/
│   ├── profiles/             # 人格档案（运行时生成）
│   └── lexicon/emotion_words.json
├── docs/                     # 开发文档
├── examples/                 # 可复现轨迹示例
└── tests/                    # 单元测试 [M1]
```

## 构建与测试命令

```bash
# 运行算法 CLI（M1 实现后）
python3 scripts/cli.py init --alias default --big-five '{...}'
python3 scripts/cli.py update --profile-id <id> --text "..."
python3 scripts/cli.py compose --profile-id <id>
python3 scripts/cli.py trace --profile-id <id>

# 单元测试（M1 实现后）
python3 -m pytest tests/ -v

# 上传 Skill 到华为云 Skills Marketplace（M4）
# 通过 uploadUserSkillToHuawei 工具：skillZip=本目录, skillName=emotions-skill, scene=通用场景
```

## 编码约定

- Python：类型注解 + dataclass，纯标准库，无外部依赖。
- 所有数值 clamp 到约定域（PAD∈[-1,1]，离散归一化）。
- 每次情绪更新必须输出可解释 `reason`。
- 持久化用原子写（临时文件 + os.replace）。
- 不存储用户对话原文长期留存（history 仅存情绪向量 + 摘要）。
- 不添加注释除非逻辑非显然。

## 里程碑

- M0 开发文档 ✅
- M1 算法核心实现（scripts/） ✅ 46 测试通过
- M2 SKILL.md 工作流完善 + references ✅
- M3 示例与可复现轨迹 ✅
- M4 打包上传华为云 Skills Marketplace