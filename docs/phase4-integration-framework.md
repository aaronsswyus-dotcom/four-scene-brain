# 阶段四：真模型接入 — 全分支框架、降级与持续优化

> 用途：阶段四（真模型接入）的**总控设计**，覆盖全分支 robot / 3d / video / game。
> 依据：`common-contract.md`(FROZEN)、`model-integration-runbook.md`(T1–T5)、`oss-list-v1~v5.md`、各分支 `backbone_interface.py`、`common/flywheel`。
> 三条铁律继承不变：①真 backbone 只在 `branches/<scene>/adapter.py` 内；②只走该分支 `XxxBackbone` 接口（robot 例外见 §1.1）；③`common/` 全程零 diff。
>
> **本沙箱边界**：当前沙箱无 GPU/CUDA、无 Azure/模型服务凭证 → 本沙箱只能交付本设计文档 + adapter 骨架规格 + T1/T2 联网核查记录。**真模型推理 / quickstart / 真测试报告须在 Azure/GPU 环境按本蓝图执行**（见 §4 路线图）。

---

## 1. 全分支接入框架与边界

### 1.1 接入缝隙（seam）全景 — 四分支形态不一

| 分支 | seam 形态 | 真模型替换点 | 备注 |
|---|---|---|---|
| **robot**（物理） | **无 `backbone_interface.py`** | 替换 `RobotWAM` 本身（子类化覆盖 `_imagine`），在 `adapter.build_bundle(backbone="groot-azure")` 注入 | 四分支里**唯一"换 WAM 而非换 backbone"**的路径。`RobotWAM` 继承 `PhysicalWorldModelBase`，`_imagine()` 即想象核；真 GR00T 实现一个 `RobotWAM` 子类，返回相同 payload schema（pose/twist/wrench/contact/joint_state/plan）。 |
| **3d**（物理） | `ThreeDBackbone`（task-aware） | 新建 `backbone_trellis.py` 实现 `ThreeDBackbone`，`adapter.build_bundle(backbone="trellis")` 选它 | `config` 必带 `task`∈{text_to_3d,image_to_3d,pointcloud_completion,pbr_texture}；**robot_scene 任务不走 backbone**（V1 内联路径字节级不变）。 |
| **video**（像素） | `VideoBackbone` | 新建 `backbone_hunyuan.py` 实现 `VideoBackbone` | config: duration_s/fps/resolution/seed/retry；返回统一 frames schema。 |
| **game**（像素，双方向） | `GameBackbone`（direction-aware） | `backbone_mariogpt.py`(A) / `backbone_gamegen.py`(B) **stub 已就位**（raise NotImplementedError） | config 必带 `direction`∈{level,worldmodel}；3 个占位 stub 已过接口形态校验，填实现即可。 |

> 关键纠正：`runbook §3` 把 robot 与其他三分支并列写"接口=RobotWAM/backbone"，但 robot **没有独立的 backbone_interface 文件**——`RobotWAM` 既是 WAM 也是 mock backbone。真接入时 GR00T 不经 `XxxBackbone` 抽象，而是直接子类化 `RobotWAM`/`PhysicalWorldModelBase`。这是物理阵营"自研 WAM 唯一"原则的延伸：robot 的 backbone 就是它的 world model。

### 1.2 每分支接入规格

| 分支 | 主推 | 备选 | config 关键字段 | 输出 schema 对齐点（T5 必查） | adapter 改动点 |
|---|---|---|---|---|---|
| robot | Isaac GR00T N1.7 (Apache 2.0 EA) | GR00T N1.5(研究专用) / π0 / Gemini Robotics | 视觉观测 + 指令 + robot embodiment | pose/twist/wrench/contact/joint_state/plan（与 `RobotWAM._imagine` 返回一致） | `adapter.py` 新增 `backbone="groot-azure"` 分支，注入 `RobotWAMReal` |
| 3d | TRELLIS.2 (MIT, 4B, 原生 PBR) | TRELLIS v1 / TripoSR / DreamGaussian / Shap-E | task + source_image/source_points/poly_budget/seed | "task" + 任务专属字段 + "meta"（见 `branches/3d/README.md`） | `adapter.py` 新增 `backbone="trellis"`；robot_scene 不受影响 |
| video | HunyuanVideo 1.5 (Apache 2.0, 8.3B, 14GB VRAM) | Wan-2.1 / CogVideoX | duration_s/fps/resolution/seed | frames/fps/duration_s/resolution/text_prompt/scene_description/camera_motion/refined_times/meta | `adapter.py` 新增 `backbone="hunyuan"` |
| game-A (level) | MarioGPT | LLM 关卡生成（GPT 系规则化） | direction="level" + theme/width/height/n_coins/... | level_map/width/height/entities/theme/text_prompt/... | 填 `backbone_mariogpt.py`（stub 已在） |
| game-B (worldmodel) | OASIS（GameGen-O 不可用，见 §2.3） | DIAMOND / GameNGen | direction="worldmodel" + action/fps/resolution/state_frames | frames/fps/resolution/action_history/current_action/... | 填 `backbone_oasis.py`（stub 已在）；`backbone_gamegen.py` 保留 stub 标"不可用" |

### 1.3 T1–T5 门禁在全分支的执行边界

| 门禁 | 本沙箱可做？ | 通过判据 | 备注 |
|---|---|---|---|
| T1 许可证 | ✅ 联网核查 | 条款允许目标用途（商用/研究） | 见 §2 已核查结果 |
| T2 健康度 | ✅ 联网核查 | star/更新/issue 响应/官方维护 | 本沙箱可记录 |
| T3 隔离安装 | 🟡 部分 | 独立 venv 装依赖、能 import | 轻量 SDK 可装；大权重/需 GPU 的装了跑不了 → 标"需真环境" |
| T4 官方 quickstart | ❌ 需真环境 | 官方最小示例跑通、产出符合预期 | 必须 GPU/Azure |
| T5 接口探针 | ❌ 需真环境 | 输入/输出 schema 与本分支接口对齐 | 需真模型加载 |

→ **本沙箱可预制**：adapter 骨架（基于公开接口形态）+ `test_<scene>_real.py`（默认 skip）+ T1/T2 核查记录。**需真环境**：T3(重)/T4/T5 + 真实 `generate()` + 真测试报告。

### 1.4 mock/real 开关与凭证边界

- `adapter.build_bundle(backbone=...)`：`"mock"`（默认，CI 用）/ `"<name>"`（真接入，需凭证）。
- 环境变量约定（凭证绝不入库）：
  ```
  FOURSCENE_<BRANCH>_ENDPOINT   # Azure 推理端点
  FOURSCENE_<BRANCH>_KEY        # 访问密钥
  FOURSCENE_REAL_TESTS=1        # 置 1 才跑真实接入测试，否则 skip
  ```
- `.gitignore` 排除任何密钥文件（`.env` / `*_key*` / `credentials*`）。
- 默认 CI：只跑 mock → 全量 pytest 绿 + 零 diff；real 测试默认 skip，配凭证才追加跑。

### 1.5 接入形态选择（本地 vs 云端 vs 可调用 API — 关键修正）

> ⚠️ **修正本沙箱前期判断**：本文档初版称"本沙箱做不了真测试"过于悲观。联网核查 + 出网探针后实情：**4 分支里 3 个（video / 3d / game-A）可在本沙箱跑真测试**，仅 game-B / robot 需 GPU/仿真器。关键在**接入形态选择**——`oss-list` 默认想的是"本地权重部署"（形态 A），但**托管 API（形态 B）和本地小模型（形态 C）不需要 GPU**。

四种接入形态 × 分支可行性（本沙箱出网已验证：`fal.run`✅ / `huggingface.co`✅ / `replicate.com`✅，`requests` 2.34.2 可用）：

| 形态 | 含义 | 本沙箱可跑？ | 适用分支 | 方案 / 成本 |
|---|---|---|---|---|
| **A 本地权重+GPU** | 下载权重本地推理 | ❌ 沙箱无 GPU | video(14GB VRAM) / 3d(H100 级) / game-B / robot | HunyuanVideo 1.5 权重 / TRELLIS.2 权重 / OASIS 权重 |
| **B 托管 API（HTTP+key）** | 调厂商/平台 REST API | ✅ **可跑** | **video** / **3d** | fal.ai: HunyuanVideo $0.4/次(~4min) / TRELLIS $0.25–0.35/次(GLB)；Replicate 亦可 |
| **C 本地 CPU 小模型** | 小模型 CPU 推理 | ✅ **可跑** | **game-A** | MarioGPT = distilgpt2(~82M, MIT, `pip install mario-gpt`, CPU 可跑, 内置 Astar 验可玩性) |
| **D 仿真器+GPU** | 策略模型+仿真环境 | ❌ 沙箱无 GPU | robot | GR00T + Isaac Sim（非纯 API 形态，最难） |
| 待定 | 需 GPU 或找托管 API | 🟡 | game-B | OASIS 需 GPU；是否有托管 API 待 T2 核查 |

**结论**：
- 🟢 **video / 3d**：走 fal.ai API（形态 B），本沙箱仅需 `FAL_KEY` 即可跑真测试；T1 ✅(Apache2.0/MIT 商用)、T4(官方 quickstart) 由平台兜底，本沙箱只须过 T5(接口探针)。
- 🟢 **game-A**：走 MarioGPT 本地 CPU（形态 C），**无需任何 key**，仅装 `torch(CPU)+mario-gpt`+联网下权重。零成本首测首选。
- 🟠 **game-B / robot**：需 GPU/仿真器，本沙箱跑不了，待真环境或找托管 API。

→ 阶段四**可立即在沙箱启动 3/4 分支**，无需等 Azure/GPU。建议首测顺序：**game-A(零成本) → video(给 key) → 3d(给 key) → game-B/robot(真环境)**。

### 1.6 common 零 diff 边界（阶段四红线）

阶段四所有改动只在：`branches/<scene>/` + `tests/test_<scene>_real.py` + `docs/reports/<branch>_<name>_report.md` + `examples/run_real_tests.sh`。**`common/` 一行不动**；`test_zero_diff` 必须持续通过。阶段四失败不得回头改 common 解围。

---

## 2. 找不到 / 接不上模型的降级与应对矩阵

### 2.1 失败场景分类（7 类）

| # | 失败场景 | 触发门禁 | 典型表现 |
|---|---|---|---|
| F1 | 找不到合适模型 | 选型前 | 该任务无开源/无 API 模型 |
| F2 | 许可证不过 | T1 | 研究专用 / 禁商用 / 条款不明 |
| F3 | 健康度差 | T2 | 停更 / 高危 issue / 非官方 |
| F4 | 装不上 | T3 | 依赖冲突 / 权重缺失 / 无 GPU 装不了 |
| F5 | quickstart 跑不通 | T4 | 官方示例失败 / 产出异常 |
| F6 | 接口探针失败 | T5 | schema 对不齐 / adapter 无法转换 |
| F7 | 无算力 / 无凭证 | 全局 | 沙箱无 GPU、无 Azure key |

### 2.2 五级降级阶梯（全分支通用）

```
L0 主推 ──失败──▶ L1 备选 ──失败──▶ L2 更轻量/蒸馏模型 ──失败──▶ L3 托管 API 服务 ──失败──▶ L4 保持 mock + 明确标注 gap ──▶ L5 人工裁决 / 暂不接
```

| 级别 | 含义 | 项目状态 |
|---|---|---|
| L0 主推 | `oss-list-vX` 主推 backbone | 接入主线 |
| L1 备选 | 同清单备选 | 接入主线 |
| L2 更轻量 | 蒸馏版/更小参数/更低保真 | 接入但标注降级 |
| L3 托管 API | 走云端 API（Azure/厂商）而非本地权重 | 接入，成本/延迟进 Telemetry |
| L4 mock + gap | 无可接模型，保持 mock，`get_info()` 标 `status="mock-only-gap"` | **不阻塞**，mock 版本(V1–V5)始终是可交付底线 |
| L5 人工裁决 | 记入报告"待用户裁决 + 原因"，不硬接 | 等用户决策 |

**核心原则**：任一门禁不过 → 不硬接，降级重走 T1–T5；全不过 → L4/L5，绝不破坏 mock 底线。阶段四失败不影响 V1–V5 的 mock 交付（继承 `hy3-overnight-master.md` §4 红线）。

### 2.3 每分支降级阶梯（含本沙箱已核查的真实状态）

> 以下 ✅/⚠️/❌ 为本沙箱 **T1 联网核查**结论（2026-07-27）；T2–T5 须真环境补。

**robot**
```
L0 GR00T N1.5      ⚠️ T1: 权重 NVIDIA License = 研究专用，禁商用生产（NVIDIA 论坛确认：预训练数据许可约束）
L0' GR00T N1.7 EA  ✅ T1: Apache 2.0，可商用；但 Early Access（2026-04），生产支持待 GA
L1 π0 / π0.5       🟡 T1/T2 需核查（Physical Intelligence 开源）
L1' Gemini Robotics 1.5  ❌ 不公开（仅选定合作伙伴）
L2 蒻量 VLA / 规则策略
L3 Azure 托管 GR00T 端点
L4 mock RobotWAM + gap   ← 当前状态
```
→ robot 商用生产**目前无可直接部署的开源 backbone**（N1.5 禁商用、N1.7 未 GA）。建议：研究/原型用 N1.7 EA，商用等 GA 或走 π0；当前保持 L4。

**3d**
```
L0 TRELLIS.2 (4B)  ✅ T1: MIT，商用 OK；原生 PBR（直配 pbr_texture 任务）；~3s/H100
L0' TRELLIS v1     ✅ T1: MIT；基础色无 PBR
L1 TripoSR / DreamGaussian / Shap-E  🟡 T2 需核查
L3 厂商 API (Meshy/Tripo3D/Hunyuan3D)
L4 mock + gap
```
→ 3d 是**四分支里接入条件最好的**：TRELLIS.2 MIT + 原生 PBR + 任务完美对齐。建议优先接入。

**video**
```
L0 HunyuanVideo 1.5  ✅ T1: Apache 2.0，商用 OK；8.3B，14GB VRAM（消费级 RTX 4070 可跑！）
L1 Wan-2.1 / CogVideoX  🟡 T2 需核查
L3 Azure 托管 / 腾讯元宝 API
L4 mock + gap
```
→ video 主推**强可用**：Apache 2.0 + 商用 + 低显存门槛（14GB），甚至可本地消费级 GPU 跑，**降级到 L3/L4 的概率低**。

**game-A (level)**
```
L0 MarioGPT         🟡 T2 需核查（2023 模型，GPT-2 基座，社区活跃）
L1 LLM 规则化关卡生成（任意 GPT，结构化 prompt → tile map）
L2 模板/过程化生成（无模型）
L4 mock + gap
```

**game-B (worldmodel)**
```
L0 GameGen-O        ❌ 不可用：GitHub 仓库存在但代码未上传（"期货开源"），无法接入
L0' OASIS           🟡 T2 需核查（实际主推）
L1 DIAMOND / GameNGen  🟡 T2 需核查
L4 mock + gap
```
→ game-B 主推**实际从 L1 起步**（GameGen-O 不可用）。`backbone_gamegen.py` stub 保留并标"不可用-代码未释出"；真接入走 OASIS。

### 2.4 终止态：某分支无任何可接模型

- 保持 mock，`get_info()` 返回 `status="mock-only-gap"`，`adapter.build_bundle(backbone="<name>")` 仍 `raise NotImplementedError` 但 message 带"已评估 N 个候选，均不过门禁，见 `docs/reports/<branch>_<name>_report.md`"。
- 产出报告标"暂不接 + 原因 + 已评估候选清单"，不硬接。
- **项目整体不阻塞**：其他分支照常接入；mock 版本（V1–V5，73 测试绿）始终是可交付底线。这是"大脑=编排器"架构的兜底价值——backbone 缺位不影响编排/契约/飞轮验证。

### 2.5 跨分支共享 foundation 的降级杠杆

- `{robot,3d}` 物理阵营共享 `PhysicalWorldModelBase`；`{video,game}` 像素阵营。
- 若某统一 foundation（如 Cosmos world model）可用，可同时降级/升级两个分支 → 杠杆点。
- 但 **video 数据对 robot 帮助有限**（用户既有判断：警惕视频质量泄漏成物理正确假象）→ 不强行跨阵营蒸馏，共享只在同阵营内（物理阵营内 / 像素阵营内）。

---

## 3. 持续优化方案

### 3.1 优化闭环（数据飞轮，冻结接口承载）

```
真 backbone 产出
   │  更丰富的 Telemetry（真实质量/延迟/成本/安全）
   ▼
Flywheel.record(Telemetry)        ← common/flywheel 冻结接口，零改动
   │
   ▼
distill() → JSONL                 ← 本地 buffer，D4: 周期云端反馈走同一接口
   │
   ▼
离线评估（§3.2 指标）→ 难例抽样 → 微调集
   │
   ▼
云端再训练 / 微调 → 新 backbone 版本
   │
   ▼
过 T1–T5 → adapter 一行换 backbone="<name>-v2" → 灰度（§3.3）→ 回灌
```

**关键**：整个优化环**只经 `Flywheel.record()` 冻结接口**进，**只经 `adapter.build_bundle(backbone=)` 一行**出，`common/` 全程零改动（`FileBufferFlywheel` 已注释：local buffer only, D4 periodic cloud feedback implements same interface）。

### 3.2 评估指标体系（四维 + 回归）

| 维度 | 指标 | 采集点 |
|---|---|---|
| 质量 | Critic 分 / 可玩性(BFS连通) / 几何误差 / 视频时序一致性 | S9 verify + 人工抽检 |
| 延迟 | P50/P95，端到端 S1–S14 | Telemetry `kind=latency` |
| 成本 | 每次调用 token / GPU-时 / \$ | Telemetry `kind=cost` |
| 安全 | SafetyGate BLOCK 率 / DEGRADE 率 | S12 |
| 回归 | 跨版本不退化（同 prompt 集质量分不下降） | A/B（§3.3） |

### 3.3 版本化与 A/B / 灰度

- backbone 版本号进 `get_info()["version"]`；每条 Telemetry 带 `backbone_version`。
- `adapter` 支持同分支多 backbone 并行注册（`backbone="hunyuan-v1"` | `"hunyuan-v2"`）→ A/B 同 prompt 双跑 → Critic 打分 → 选优。
- **灰度三档**：①shadow（跑但不交付，只记 Telemetry）→ ②canary（小比例交付）→ ③main（全量切主）。
- 切主需人工确认（§3.4 人在回路）。

### 3.4 退化检测与再训练触发

- **自动触发条件**（任一满足即提建议）：
  - 质量分滑动窗口（N=100）跌破阈值；
  - 安全 BLOCK 率环比上升 >X%；
  - 延迟 P95 超限；
  - 某类 prompt 失败率上升。
- **触发后**：从 JSONL 抽样难例 → 构造微调集 → 云端再训练 → 新版本过 T1–T5 → 灰度上线。
- **人在回路**：触发只提建议，**切主需人工确认**（避免飞轮自毁 / 数据投毒放大）。

### 3.5 跨分支飞轮杠杆

- 同阵营 foundation 微调一次，两分支同步受益（物理：robot+3d；像素：video+game）。
- V5 跨分支聚合视图 `examples/_flywheel_view.py`（只读 jsonl，kind→branch 分组）提供跨分支健康度看板，不改 `common/flywheel`。
- 跨阵营**不强行蒸馏**（§2.5）。

### 3.6 优化边界与红线

- 飞轮只读 Telemetry，**绝不反向控制编排循环**（继承 runbook 红线）。
- 再训练在云端，本地只 buffer；`common/flywheel` 接口零改动。
- 凭证/权重绝不入库。
- 优化是**增量**：新 backbone 版本经 T1–T5 + 灰度才上线，mock 永远是可回退底线。

---

## 4. 执行路线图（本沙箱 → 真环境）

### 4.1 本沙箱可立即做（无凭证 / 无 GPU）— 本文档即为交付
- ✅ 产出本设计文档（框架 + 降级 + 优化）。
- ✅ T1 联网核查 4 分支主推（见 §2.3 结论）。
- ✅ **game-A MarioGPT 真实现已落地**（2026-07-27）：
  - `branches/game/backbone_mariogpt.py`：stub → real，lazy import `mario_gpt` + anti-corruption layer（SMB tile → 我们的 schema + 强制 1P/1G + 四边封闭 + BFS 走廊）
  - `branches/game/adapter.py`：加 `backbone="mariogpt"` 选项（一行切换，common 零改动）
  - `tests/test_game_real.py`：6 个默认-skip 测试（schema / seed 确定性 / Critic 集成 / SafetyGate / worldmodel 拒绝 / get_info 契约）
  - `.github/workflows/phase4-tests.yml`：4 jobs（mock 回归 / zero-diff / game-A 真测 / video-3d 占位），公开仓库免费 CPU runner
  - `docs/reports/game_mariogpt_report.md`：T1-T5 报告（T1/T2/T5 已核查，T3/T4 + 自动测试待 GitHub Actions 实测）
  - 本地验证：73 passed + 6 skipped（real 默认 skip）+ zero-diff 通过 + common 零改动
- ⏳ video / 3d / game-B / robot 真实现待写（按 §4.2 顺序）。

### 4.2 需真环境（Azure/GPU + 凭证）— 按本蓝图执行
- T3 隔离装 / T4 quickstart / T5 接口探针。
- 真实 `generate()` 实现 + 真测试 + `docs/reports/<branch>_<name>_report.md`。
- 建议接入顺序（按 §2.3 可用性排序）：
  1. ✅ **game-A / MarioGPT**（代码已落地，待 `git push` 后 GitHub Actions 自动跑 `game-real-mariogpt` job 实测）
  2. 🟢 **3d / TRELLIS.2**（MIT + 原生 PBR + 任务对齐最好；走 fal.ai API 需 `FAL_KEY`）
  3. 🟢 **video / HunyuanVideo 1.5**（Apache 2.0 + 14GB VRAM，门槛最低；走 fal.ai API 需 `FAL_KEY`）
  4. 🟠 **game-B / OASIS**（GameGen-O 不可用，走备选；需 GPU）
  5. 🔴 **robot / GR00T N1.7 EA**（商用待 GA，当前研究/原型可用）

### 4.3 用户需提供
1. 选哪个分支先做（或按 §4.2 推荐顺序）；
2. Azure / 模型服务凭证，或确认走本地开源权重（video/3d 可本地消费级 GPU）。

---

### 4.4 执行环境选择（GitHub Actions vs Azure VM）

> 基于 2026-06 GitHub Actions 实际计费核查。仓库 four-scene-brain 为 public（前 3 分支 GitHub 零成本）。

| 环境 | 适用分支 | 成本 | 说明 |
|---|---|---|---|
| **GitHub Actions 标准 CPU runner** | video/3d(经 fal.ai API) + game-A(MarioGPT CPU) | **public 免费无限**；private 2000 min/月免费 | ubuntu-latest 4核16G：装 torch CPU 跑 82M 模型 + HTTP 调 fal.ai；FAL_KEY 放 Secrets |
| GitHub Actions GPU runner | game-B/robot 本地权重 | $0.052/min + **需 Team/Enterprise 付费计划**（public 也要钱） | 贵且需付费计划，不推荐 |
| **Azure GPU VM**（NC/ND 系列） | game-B(OASIS) / robot(GR00T+Isaac Sim) | T4 ~$0.5/h、A100 ~$3-4/h，按需开机 | 跑本地大权重/仿真器专用，用完关省钱 |

**推荐组合（成本最优）**：
- 🟢 **前 3 分支**（video/3d/game-A）→ **GitHub Actions 标准 runner**（public 仓库免费）。FAL_KEY 放 GitHub Secrets，每次 push 自动跑 mock 全量回归 + 真测试增量（配 `FOURSCENE_REAL_TESTS=1` 时）。
- 🟠 **后 2 分支**（game-B/robot）→ **Azure GPU VM 按需**（用完即关，按小时计费）。

**public 仓库 + Secret 安全红线**：
- `pull_request` 触发的 workflow 默认**不继承 secrets**（防恶意 PR 偷 FAL_KEY）→ **真测试只在 `push` 到 main / `workflow_dispatch` 手动触发，不在 PR 触发**。
- `FAL_KEY` / `FOURSCENE_REAL_TESTS` 经 GitHub Secrets 注入，绝不入库（`.gitignore` 已排除密钥文件）。
- mock 全量回归可在 PR 触发（无 secret，安全）。

→ 阶段四 CI 产出物：`.github/workflows/phase4-tests.yml`（mock 回归 job + game-A 真测试 job + video/3d 真测试 job[需 secret] + 零 diff 校验 job）。

## 5. 红线汇总（继承 runbook §6 + 阶段四补充）

1. 🔴 真 backbone 只在 `branches/<scene>/adapter.py` 内（robot 子类化 `RobotWAM`），绝不进 common。
2. 🔴 只走该分支 `XxxBackbone` 接口；wam/critic/... 不直接调真 API。
3. 🔴 凭证绝不入库（环境变量；`.gitignore` 排除密钥文件）。
4. 🔴 T1–T5 任一不过 → 降级备选，不硬接；全不过 → L4 mock + gap，不阻塞项目。
5. 🔴 真实测试默认 skip，不配凭证不影响 CI 全绿。
6. 🔴 common 全程零改动；`test_zero_diff` 始终通过。
7. 🔴 飞轮只读 Telemetry，绝不反向控制编排；再训练在云端，本地只 buffer。
8. 🔴 切主 backbone 需人工确认（人在回路，防飞轮自毁）。

---

## 附：本沙箱 T1 联网核查记录（2026-07-27）

| backbone | 许可证 | 商用 | 状态 | 来源 |
|---|---|---|---|---|
| GR00T N1.5 | NVIDIA License（权重） | ❌ 研究专用 | 可下载 | NVIDIA 论坛：预训练数据许可约束，禁生产部署 |
| GR00T N1.7 EA | Apache 2.0 | ✅（EA） | Early Access 2026-04 | HuggingFace/GitHub；生产支持待 GA |
| TRELLIS.2 | MIT | ✅ | v2 2025-12，4B，原生 PBR | github.com/microsoft/TRELLIS.2 |
| HunyuanVideo 1.5 | Apache 2.0 | ✅ | 2025-11，8.3B，14GB VRAM | HuggingFace/GitHub |
| GameGen-O | — | — | ❌ 期货开源（仓库空） | github.com/GameGen-O/GameGen-O 代码未上传 |
| OASIS / DIAMOND / MarioGPT / π0 | — | — | 🟡 T2 待核查 | — |

> 以上为 T1 抽样核查；T2–T5 须在真环境接入时补全，记入各 `docs/reports/<branch>_<name>_report.md`。
