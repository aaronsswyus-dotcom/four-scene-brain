# 真模型接入 + 自动测试 Runbook（HY-3 自主执行）

> 用途：mock 版本（V1–V5）全部交付后，由 HY-3 **自主**完成真 backbone 的「选型 → 门禁 → 接入 → 自动测试 → 测试报告」。
> 依据：`engineering-setup.md` §2 五道门禁、各版本 `oss-list-vX.md`、各分支 `XxxBackbone` 防腐层接口。
> 红线：真 backbone **只在 `branches/<scene>/adapter.py` 内**、**只走 `XxxBackbone` 接口**、**绝不进 common**、**绝不反向控制编排循环**。common 全程零改动。

---

## 1. 目标与产出

**目标**：把某个（些）分支的 mock backbone 替换为真实模型（API/权重），并让其**可自动测试**，最终产出**测试报告**。

**最终产出（每个接入的 backbone 一套）**：
1. `branches/<scene>/backbone_<name>.py`（真 adapter，实现该分支 `XxxBackbone` 接口）
2. `tests/test_<scene>_real.py`（真实接入自动测试，默认 skip，配好凭证才跑）
3. 一份**测试报告**（见 §5 模板）

---

## 2. 通用流程（每个 backbone 必走）

```
T1 许可证 → T2 健康度 → T3 隔离安装 → T4 官方 quickstart → T5 接口探针
   → 实现真 adapter → mock/real 开关 → 自动测试 → 测试报告
```

| 门禁 | 要做什么 | 通过判据 |
|---|---|---|
| **T1 许可证** | 读模型 LICENSE/权重条款，确认可商用/可用 | 条款允许目标用途；不确定 → 标 ⚠️ 并降级备选 |
| **T2 健康度** | 看 star/更新频率/issue 响应/是否官方维护 | 活跃或可接受；停高危 → 降级备选 |
| **T3 隔离安装** | 在**独立 venv**（非 common 环境）装依赖 | 不污染 common 环境；能 import |
| **T4 官方 quickstart** | 跑官方最小示例（Azure/GPU 环境） | 官方示例跑通，产出符合预期 |
| **T5 接口探针** | 写一个最小调用，核对**输入/输出 schema** 与本分支 `XxxBackbone` 接口是否对齐 | 字段能对齐（或 adapter 可转换） |

**任何一关不过 → 不要硬接，降级到 `oss-list-vX.md` 里的备选 backbone，重走流程。**

---

## 3. 分支 backbone 清单（选型入口）

> 每个分支选**主推**，不过关降级备选。API/权重形态以各项目官方为准（T1/T4 时核实）。

| 分支 | 接口 | 主推 | 备选 | 输出形态（adapter 需对齐） |
|---|---|---|---|---|
| robot（物理） | `RobotWAM`/backbone | Isaac GR00T N1.5 | （oss-list-v1） | 关节力矩/动作轨迹 |
| 3d（物理） | `ThreeDBackbone` | TRELLIS | TripoSR / DreamGaussian / Shap-E | mesh/GLB（+PBR） |
| video（像素） | `VideoBackbone` | HunyuanVideo | Wan-2.1 / CogVideoX | frames→mp4 |
| game（像素，双方向） | `GameBackbone` | A: MarioGPT ｜ B: GameGen-O | A: LLM 关卡生成 ｜ B: OASIS / DIAMOND | A: level tile map ｜ B: 动作条件化帧 |

**接口对齐要点（T5 必查）**：
- 输入：文本/图像/点云/动作 是否支持；参数（duration/resolution/seed/task/direction）是否可控。
- 输出：schema 是否与该分支 `XxxBackbone.generate()` 返回结构一致；不一致 → 在 adapter 内转换。
- 确定性：是否支持 seed（影响 Critic 可重复校验）。
- 许可：T1 必须过。

---

## 4. 自动测试框架（让其可自动测试）

### 4.1 mock / real 开关（关键）

`adapter.build_bundle(backbone=...)` 已支持选 backbone。扩展为：
- `backbone="mock"`（默认，CI 用，无凭证也能跑全量测试）
- `backbone="<name>-azure"`（真接入，需凭证；默认在 pytest 里 **skip**，配好凭证才跑）

约定环境变量（真实凭证绝不入库）：
```
FOURSCENE_<BRANCH>_ENDPOINT   # Azure 推理端点
FOURSCENE_<BRANCH>_KEY        # 访问密钥
FOURSCENE_REAL_TESTS=1        # 置 1 才跑真实接入测试，否则 skip
```

### 4.2 真实接入自动测试（tests/test_<scene>_real.py）

每个真 backbone 配一份自动测试，**默认 skip**：

```python
import os, unittest

@unittest.skipUnless(os.getenv("FOURSCENE_REAL_TESTS") == "1", "real backbone tests disabled")
class Test<RealBackbone>(unittest.TestCase):
    def test_generate_schema(self):
        # 调真 backbone.generate(...)，断言返回 schema 与该分支 XxxBackbone 接口一致
    def test_determinism_seed(self):
        # 同 seed 两次调用，断言输出一致（或近似）
    def test_critic_integration(self):
        # 真输出喂该分支 Critic，断言能产出 Verification（不判分高低，只判流程通）
    def test_safety_gate(self):
        # 违规 prompt → SafetyGate BLOCK；正常 prompt → PASS
```

### 4.3 自动回归（CI 建议）

- **默认 CI**：只跑 mock（`FOURSCENE_REAL_TESTS` 未置 1）→ 全量 pytest 绿 + 零 diff。
- **凭证环境**：置 `FOURSCENE_REAL_TESTS=1` + 端点/密钥 → 追加跑 `test_<scene>_real.py`。
- 一键脚本（示例，放 `examples/run_real_tests.sh` 或 CI 配置）：先 mock 全量，再 real 增量。

---

## 5. 测试报告模板（每个 backbone 填一份）

> HY-3 接入完一个 backbone 就填一份，作为 `docs/reports/<branch>_<name>_report.md` 存档。

```markdown
# 真模型接入测试报告：<branch> / <backbone-name>

- 日期 / 执行人（HY-3）/ 环境（Azure 规格 / GPU / region）
- backbone：名称 / 版本 / 来源（repo/endpoint）/ License

## 门禁结果
| 门禁 | 结果 | 说明 |
|---|---|---|
| T1 许可证 | ✅/⚠️/❌ | 条款结论 |
| T2 健康度 | ✅/⚠️/❌ | star/维护情况 |
| T3 隔离安装 | ✅/❌ | venv 是否干净、import 是否成功 |
| T4 官方 quickstart | ✅/❌ | 官方示例是否跑通、产出是否符合预期 |
| T5 接口探针 | ✅/❌ | 输入/输出 schema 与本分支接口是否对齐 |

## 自动测试结果
| 测试 | 结果 | 备注 |
|---|---|---|
| generate schema 对齐 | ✅/❌ | |
| seed 确定性 | ✅/❌ | |
| Critic 集成（流程通） | ✅/❌ | |
| SafetyGate BLOCK/PASS | ✅/❌ | |
| mock 全量回归（不回归） | ✅/❌ | |

## 质量观察（主观，非验收）
- 输出质量 / 时延 / 成本 / 与 mock 的差距 / sim2real 或质量备注

## 结论
- [ ] 可上线（接入 adapter，mock/real 可切换）
- [ ] 需降级备选（原因）
- [ ] 暂不接（原因）
```

---

## 6. 红线重申

1. 🔴 真 backbone 只在 `branches/<scene>/adapter.py` 内，绝不进 common。
2. 🔴 只走该分支 `XxxBackbone` 接口；wam/critic/... 不直接调真 API。
3. 🔴 凭证绝不入库（用环境变量；`.gitignore` 排除任何密钥文件）。
4. 🔴 T1–T5 任一不过 → 降级备选，不硬接。
5. 🔴 真实测试默认 skip，不配凭证不影响 CI 全绿。
6. 🔴 common 全程零改动；零 diff 验收始终通过。
