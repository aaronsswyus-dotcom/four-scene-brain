# 真模型接入测试报告：game / MarioGPT

- **日期**：2026-07-27
- **执行人**：HY-3（自主执行）
- **环境**：本地沙箱（设计 + T1/T2 核查）；GitHub Actions ubuntu-latest CPU runner（T3-T5 + 自动测试，待 push 后实测）
- **backbone**：MarioGPT（shyamsn97/mario-gpt，NeurIPS 2023）
  - 名称：mario-gpt
  - 版本：PyPI 最新（最后 release 2023-08）
  - 来源：https://github.com/shyamsn97/mario-gpt
  - 底座：distilgpt2（~82M 参数，HuggingFace 公开权重）
  - License：MIT（mario-gpt 仓库）+ Apache 2.0（distilgpt2 权重）
  - 接入形态：C 本地 CPU 小模型（无需 GPU、无需 API key、无需 Azure）

## 门禁结果

| 门禁 | 结果 | 说明 |
|---|---|---|
| **T1 许可证** | ✅ | mario-gpt 仓库 MIT License；distilgpt2 权重 Apache 2.0；均允许商用。已核实 LICENSE 文件与 HuggingFace 模型卡。 |
| **T2 健康度** | ⚠️ | shyamsn97/mario-gpt：NeurIPS 2023 论文配套代码，40 commits，最后更新 2023-08-03。维护已停滞但有官方 HuggingFace demo（multimodalart/mariogpt space）、社区使用记录可查。判定为"稳定但不再更新"，功能完整可用，无已知 critical bug。 |
| **T3 隔离安装** | ✅ 实测通过 | `pip install mario-gpt "transformers==4.35.2"`（Ubuntu 3.11 runner，torch 2.13 + transformers 4.35.2 + tokenizers 0.15.2 均有预编译 wheel，一次装好）。于 run #11（2026-07-27）实测成功。 |
| **T4 官方 quickstart** | ✅ 实测通过 | README 示例 `MarioLM().sample(prompts=[...], num_steps=..., temperature=...)` → `out.level` 在 CI 真实跑通（6 测试全过）。adapter 实现与官方 API 一致。 |
| **T5 接口探针** | ✅ 设计层 | `out.level` 是 `List[str]`（每行一个元素，14 行高 × num_steps 列宽）。adapter 内 `_normalize_smb_level` 做 SMB tile → 我们的 schema（# . P G C E H）映射 + 强制四边封闭 + 1P/1G + BFS 走廊，输出与 `MockGameBackbone` 的 level schema 完全对齐。 |

## 自动测试结果

> **2026-07-27 run #11（commit `849a609`）全绿**：6 个真测试 ✅ 全过；mock 回归 ✅；zero-diff ✅。Phase 4 第一个真 backbone 在 CI 闭环。

| 测试 | 结果 | 备注 |
|---|---|---|
| generate schema 对齐 | ✅ 通过 | `test_1_generate_schema`：level_map/width/height/entities/theme/text_prompt 字段齐 + 1P/1G |
| seed 确定性 | ✅ 通过 | `test_2_determinism_seed`：同 seed 两次，level_map bit-identical（torch.manual_seed 控制） |
| Critic 集成（流程通） | ✅ 通过 | `test_3_critic_integration`：真输出喂 GameCritic，产出 Verification 对象（修复了 SubGoal 字段名 bug） |
| SafetyGate BLOCK/PASS | ✅ 通过 | `test_4_safety_gate`：gore prompt → BLOCK；正常 prompt + 合规尺寸 → PASS |
| worldmodel 拒绝 | ✅ 通过 | `test_5_worldmodel_raises`：MarioGPT level-only，worldmodel → NotImplementedError |
| get_info 契约 | ✅ 通过 | `test_6_get_info_contract`：status=="real" + license 以 MIT 开头 |
| mock 全量回归（不回归） | ✅ 通过 | 73 passed + 6 skipped（real 默认 skip）；zero-diff 通过；common/ 零改动 |

## 质量观察（主观，非验收）

- **输出质量**：distilgpt2 ~82M 是小模型，生成的 SMB 关卡在"结构合理性"上不如大模型，但 anti-corruption layer 强制了 1P/1G + 四边封闭 + BFS 走廊，保证 GameCritic 的 HARD 检查（可玩性）通过。SOFT 检查（theme/entity 关键词与 prompt 重叠）取决于 `_translate_prompt` 的关键词匹配质量。
- **时延**：CPU 上单次 generate() 预计 30-90s（distilgpt2 + num_steps=16-32）。首次运行还要下载 ~82M 权重（HuggingFace 缓存，后续秒级）。
- **成本**：$0（本地 CPU / GitHub Actions 公开仓库免费 runner）。
- **与 mock 的差距**：mock 是确定性 sha256 布图，关卡结构人工可控但缺乏多样性；MarioGPT 输出有真实的"模型风格"多样性，但需要 anti-corruption layer 兜底结构正确性。这正是"mock 作 V1–V5 baseline + real 作 Phase 4 增量"分层的设计意图。
- **sim2real / 质量备注**：MarioGPT 的 tile 分布反映 SMB 训练数据的偏置（管道/砖块多），可能与用户中文 prompt 的"草地/金币"语义对齐度不高。优化方向：在 `_translate_prompt` 里做更精细的中英文关键词映射，或后续飞轮收集 (prompt, level, critic_score) 三元组微调。

## 实测迭代记录

### 第 1 次 push（commit `c923b03`，仅 CI 修复）
- Job1 mock-regression ✅、Job2 zero-diff ✅、Job3 game-real ❌、Job4 skip。
- **失败根因**：`backbone_mariogpt.py` 使用 `MarioLM(lm_path="distilgpt2", ...)`，但 mario-gpt 只在 `lm_path=None` 时才加载微调好的 `shyamsn97/Mario-GPT2-700-context-length`；传 `distilgpt2` 会加载基础模型并在 `add_cross_attention` 处快速崩溃。
- **修复**：`MarioLM()` 无路径参数；`__init__` 默认 `lm_path=None`；`num_steps = 14*width`（避免生成 1 行退化关卡）。

### 第 2 次 push（commit `07abb8e`，MarioGPT 修复）
- Job1 ✅、Job2 ✅、Job3 ❌、Job4 skip。
- **失败根因**：`mario-gpt` import 时报 `ImportError: cannot import name 'AutoModelWithLMHead' from 'transformers'`。`mario-gpt` 未 pin transformers，CI 装到最新版（5.14.1），而 `AutoModelWithLMHead` 在 transformers>=4.40 被移除。
- **修复**：在 `.github/workflows/phase4-tests.yml` 的 `game-real-mariogpt` job 中把 transformers 钉到 `4.35.2`（仍保留 `AutoModelWithLMHead`，与 Ubuntu 3.11 预编译 wheel 兼容）。同时在 `backbone_mariogpt.py` 的 ImportError 提示中明确给出该 pin 命令。

### 第 3 次 push（commit `849a609`，test_3 SubGoal 字段修复）
- run #11（2026-07-27T00:52Z）**全绿 success** ✅。
- Job1 mock-regression ✅、Job2 zero-diff ✅、Job3 game-real ✅（6/6）、Job4 skip。
- **最后一处挂的根因**：`test_3_critic_integration` 用 `SubGoal(subgoal_id=..., summary=..., predecessors=...)`，但 `SubGoal` 真实字段是 `id / success_criteria / depends_on`（frozen 契约，common/ 不改）。改测试参数即可，不动 common（零 diff 守住）。
- **结果**：game-A MarioGPT 真模型在 GitHub Actions 上 **6/6 全过**，Phase 4 第一个真 backbone 闭环。

## 结论

- [x] 可上线（接入 adapter，mock/real 可切换）—— **代码已落地 + 已实测通过（run #11 success）**：
  - `branches/game/backbone_mariogpt.py`（stub → real，lazy import + anti-corruption layer）
  - `branches/game/adapter.py`（加 `backbone="mariogpt"` 选项）
  - `tests/test_game_real.py`（6 个默认-skip 测试，CI push main 时全跑通）
  - `.github/workflows/phase4-tests.yml`（`game-real-mariogpt` job 实测 success）
- [x] T1–T5 全部 ✅（T1 MIT/Apache ✅、T2 stale-but-stable ⚠️、T3 隔离安装 ✅、T4 quickstart ✅、T5 接口对齐 ✅）
- [ ] 需降级备选（原因）—— 不适用
- [ ] 暂不接（原因）—— 不适用

**下一步**：`docs/phase4-integration-framework.md` §4.2 的 game-A 状态升级为"已实测通过"；video/3d 真接入（fal.ai，待 FAL_KEY + 说"可以开发"）与 robot GR00T（Azure GPU）为后续 Phase 4 分支。

## T1 联网核查记录（2026-07-27）

| 项 | 值 | 来源 |
|---|---|---|
| 仓库 | https://github.com/shyamsn97/mario-gpt | WebFetch 核实 |
| License | MIT | 仓库 LICENSE 文件 |
| 底座模型 | distilgpt2（HuggingFace） | README + 论文 |
| 底座 License | Apache 2.0 | HuggingFace 模型卡 |
| 论文 | NeurIPS 2023, arXiv:2302.05981 | README |
| Python 版本 | 3.8+ | README Requirements |
| 安装命令 | `pip install mario-gpt` | README Installation |
| 主 API | `MarioLM().sample(prompts=[...], num_steps=N, temperature=T, use_tqdm=False)` | README Generating Levels |
| 输出 | `out.level`（List[str]）、`out.img`（PIL）、`out.run_astar()`（可玩性验证，需 Java） | README |
| 默认 num_steps | 1400（生成 100 列 × 14 行大关卡） | README 示例 |
| 推荐 temperature | 2.0+（越高越随机但更可玩） | README |
| 确定性控制 | `torch.manual_seed(seed)`（模型权重固定，sampling 随机性来自 torch RNG） | 标准 transformers 用法 |
