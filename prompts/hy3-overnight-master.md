# HY-3 过夜主开发包（V3 → V4 → V5 依次开发 + 测试 + 模型接入）

> 用途：这是给 HY-3 的**总控入口**。你（HY-3）今晚按本文件**依次**开发 V3、V4、V5，每个版本开发完按其 `hy3-vX-dev-prompts.md` 执行、按 `acceptance-test-plan.md` 验收，全部完成后按 `model-integration-runbook.md` 做真模型接入与自动测试并产出报告。
> 用户不在线（已睡觉）。**遇到问题先按本文件与各专业文档自主决策；只有当必须改 common 或必须推翻已冻结决策时，才停下来在报告里记录"待用户裁决"，继续推进其余不受影响的部分。**

---

## 0. 你的身份与最高原则（先读，违反=返工）

- 你是**实现工程师，不是设计者**。所有架构决策已冻结在 `docs/common-contract.md`。
- **三条铁律**：
  1. **common 写一次永冻结**：你只能新增/扩展 `branches/<scene>/`、`examples/`、`tests/`、`docs/`、`prompts/`，**绝不改 `common/` 任何一行**。
  2. **场景即插件**：common 不出现任何场景/backbone 名、无模态 if/else；场景/任务/方向差异只走 `payload`+`meta`+`config`。
  3. **唯一交换语言**：common 与分支只交换 `common-contract.md` §4/§5 定义的对象与签名。
- **纯 Python stdlib，零三方运行时依赖**；pytest 是唯一开发依赖。
- **每个分支文件含 `__main__` 自测**；backbone 全 mock（真模型只在最后 §4 阶段接）。

---

## 1. 总顺序（严格按此推进）

```
阶段一：V3（game 双方向）   → 开发 + 验收
阶段二：V4（完整 3D 多任务） → 开发 + 验收（含 V1 robot_scene 回归）
阶段三：V5（集成 + 跨分支飞轮 + 发布）→ 开发 + 验收（含全量回归）
阶段四：真模型接入（可选，若时间/条件允许）→ 门禁 + 自动测试 + 报告
全程：每个版本 git commit；common 始终零 diff。
```

> 依赖关系：V3 与 V4 互不依赖（可顺序做）；**V5 依赖 V3、V4 都完成**（复用其分支）。阶段四依赖 V3/V4/V5 全交付。

---

## 2. 每个版本的"开发 + 验收"固定动作

对每个版本 V ∈ {V3, V4, V5}，严格按以下闭环：

1. **读上下文**：打开 `prompts/hy3-vX-dev-prompts.md` 的 §A 清单，先读前 5–6 份必读文件。
2. **按 P0–Px 开发**：严格按该文件 §B 主提示词 + §C/§D 阶段提示词，逐阶段实现 + 每文件 `__main__` 自测。
3. **验收**：打开 `docs/acceptance-test-plan.md` 对应版本章节，逐项打勾（单元自测/分支 pytest/demo 闭环/零 diff/DoD）。
4. **不回归**：跑 `python -m pytest tests/ -v` 全绿 + `python -m tests.test_zero_diff` 通过。
5. **提交**：`git add` 该版本改动 + `git commit`（信息注明版本与内容）。
6. **记录**：把实际测试计数、demo 结果、遇到的问题记入当晚报告（见 §5）。

### 版本入口速查
| 版本 | 开发提示词 | 开发文档 | 开源清单 | 验收章节 |
|---|---|---|---|---|
| V3 game 双方向 | `prompts/hy3-v3-dev-prompts.md` | `docs/v3-development-plan.md` | `docs/oss-list-v3.md` | acceptance-test-plan §1 |
| V4 完整 3D 多任务 | `prompts/hy3-v4-dev-prompts.md` | `docs/v4-development-plan.md` | `docs/oss-list-v4.md` | acceptance-test-plan §2 |
| V5 集成+飞轮 | `prompts/hy3-v5-dev-prompts.md` | `docs/v5-development-plan.md` | `docs/oss-list-v5.md` | acceptance-test-plan §3 |

---

## 3. 通用测试命令

```bash
PY="C:/Users/aaron/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
cd four-scene-brain
$PY -m pytest tests/ -v          # 全量 pytest（每版本后必须全绿）
$PY -m tests.test_zero_diff      # 零 diff 验收（common 必须无 diff）
$PY -m examples.<scene>_demo     # 场景闭环 demo（按版本）
git status --porcelain -- common/   # 必须为空（common 零改动）
```

**红线自检（每版本提交前）**：`git status --porcelain -- common/` 输出必须为空；非空 → 说明泄漏，立即回读 `common-contract.md` §11，用 payload/meta/新实现解决，**不改 common**。

---

## 4. 阶段四：真模型接入 + 自动测试 + 报告（可选）

mock 版本全部交付后，若时间与条件允许，按 `docs/model-integration-runbook.md` 执行：
1. **选 1 个分支的 1 个主推 backbone**（建议从 video/HunyuanVideo 或 3d/TRELLIS 起步，生态较成熟）。
2. 过 **T1–T5 门禁**（许可证/健康度/隔离安装/quickstart/接口探针）。
3. 实现 `branches/<scene>/backbone_<name>.py` + `tests/test_<scene>_real.py`（默认 skip）。
4. 配 mock/real 开关 + 环境变量（凭证绝不入库）。
5. 填**测试报告**（runbook §5 模板），存为 `docs/reports/<branch>_<name>_report.md`。

> 若任一门禁不过：降级备选 backbone 重试；全不过则在报告里记录"待用户裁决 + 原因"，不硬接。**阶段四失败不影响阶段一/二/三的 mock 交付。**

---

## 5. 当晚报告（你醒来后给用户看的）

在仓库根写 `docs/reports/overnight_<日期>.md`，含：
1. **每版本状态**：V3/V4/V5 各自「完成/部分/阻塞」+ 实际 pytest 计数 + demo 结果 + 零 diff 结果。
2. **commit 列表**：今晚所有 commit hash + 一句话。
3. **遇到的问题与决策**：你自主做的判断 + 必须留给用户裁决的项（尤其任何"想改 common"的冲动及原因）。
4. **阶段四（若做）**：接入的 backbone + 门禁结果 + 自动测试结果 + 测试报告链接。
5. **下一步建议**：给用户的 1–3 条可执行建议。

---

## 6. 硬红线（任何时刻违反=立即停止该分支并记录）

- 🔴 改 `common/` 任何一行。
- 🔴 在 common/orchestrator 写场景/任务/方向名或模态 if/else。
- 🔴 分支互相 import / 共享 payload 结构知识（跨分支只经 SubGoal DAG + State 串联）。
- 🔴 装任何三方运行时库 / 大模型（除阶段四在独立 venv）。
- 🔴 真凭证写入仓库。
- 🔴 破坏已交付版本（V1/V2 及先前完成的 V3/V4）能力。

**开始：从阶段一 V3 的 `prompts/hy3-v3-dev-prompts.md` §A 上下文清单读起。**
