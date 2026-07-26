# V3 开源项目清单 + GameBackbone Adapter 接口规范（2026-07-26 · V3 启动前定稿）

> 依据：common-contract §2/§10 红线、`v3-development-plan.md`（**D-V3-1 已拍板：A/B 双方向**）、engineering-setup §2 五道门禁。
> 结论先行：**V3 本机运行时零三方依赖（同 V1/V2）；所有 backbone 全 mock；真模型推迟到 Azure 阶段再过门禁接入。**
> **双方向分开选型**：方向 A（关卡生成）与方向 B（交互式 world model）的 backbone 是不同物种。

---

## 1. V3 本机实际使用（现在就装/用）

| 项目 | 用途 | 层 | 许可 | 状态 |
|---|---|---|---|---|
| Python 3.13 stdlib | common + game 分支全部实现 | common + branches | PSF | ✅ 唯一运行时依赖 |
| pytest | 测试 | 仅开发依赖 | MIT | ✅ 已装 |

**就这两项。** common 红线：零三方依赖；game 分支 V3 也全 mock，同样零三方依赖。

---

## 2. game backbone 候选（V3 全 mock，Azure 阶段接入）

### 方向 A · level（可玩关卡生成）

| 优先级 | 项目 | GitHub | 类型 | License | V3 处置 | T1 门禁风险 |
|---|---|---|---|---|---|---|
| **主推** | **MarioGPT** | [shyamsn97/mario-gpt](https://github.com/shyamsn97/mario-gpt) | 文本→2D 平台关卡（GPT，SMB 风格 tile map） | ⚠️ 需复核 | mock（adapter 预留替换点） | ⚠️ 研究代码，商用条款需核实 |
| 备选 | **GameGen-O（转关卡）** | （腾讯，研究预览） | 开放世界游戏视频生成 → adapter 抽取 tile map | ⚠️ 需复核 | 备选 | ⚠️ 偏视频，转关卡成本高；许可需核实 |
| 备选 | **LLM 关卡生成** | （通用 LLM 走 Azure） | 文本→结构化 level JSON | 视所选模型 | 备选 | 视所选模型许可 |

> 方向 A 的开放模型生态较窄（多为研究代码），**T1 许可 + 输出格式是否可控（tile map vs 视频）是两个关键复核点**。

### 方向 B · worldmodel（交互式游戏推演）

| 优先级 | 项目 | GitHub | 类型 | License | V3 处置 | T1 门禁风险 |
|---|---|---|---|---|---|---|
| **主推** | **GameGen-O** | （腾讯，研究预览） | 开放世界游戏**视频**生成（契约 §13 预留示例） | ⚠️ 需复核 | mock（adapter 预留替换点） | ⚠️ 是否开放权重 + 商用条款均需核实 |
| 备选 1 | **OASIS** | [etched-ai/...] | Minecraft 交互式 world model（开放权重） | ⚠️ 需复核 | 备选（GameGen-O 不过关时切换） | ⚠️ 许可 + 是否真"交互式"需 T4/T5 验证 |
| 备选 2 | **DIAMOND** | [eloialonso/diamond](https://github.com/eloialonso/diamond) | 扩散 world model（Atari 风格 action-conditioned） | ⚠️ 需复核 | 备选（动作条件化最贴合 B） | ⚠️ 许可需核实 |
| 参考（不开放） | GameNGen / Genie | Google | 神经游戏引擎 / 生成式交互环境 | — | 仅作技术参考 | ❌ 未开放权重 |

**决策逻辑**：
- 方向 B 首选 **GameGen-O**（契约预留、腾讯系、开放世界游戏生成最贴题）；T1（许可/开放权重）不过关 → 切 **OASIS**；OASIS 资源/交互性不达标 → 切 **DIAMOND**（action-conditioned 最贴"交互式推演"语义）。
- 方向 A 首选 **MarioGPT**（唯一直接产出 2D 平台 tile map 的开放方案）；不过关 → LLM 关卡生成（结构化 JSON，可控性最高）。
- V3 mock 阶段所有候选经统一 `GameBackbone` 接口对齐（见 §4），切换成本最低。

---

## 3. V3 与 V1/V2 的开源差异

| 维度 | V1（robot + 3d） | V2（video） | V3（game · 双方向） |
|---|---|---|---|
| backbone | GR00T / DreamGaussian | HunyuanVideo / Wan-2.1 | **A: MarioGPT 等 ｜ B: GameGen-O / OASIS / DIAMOND** |
| 输入 | 物理指令 | 文本 prompt | **A: 文本 prompt ｜ B: 文本 + 玩家动作** |
| 输出 | 关节力矩 / mesh/GLB | 视频帧 / mp4 | **A: tile map / level JSON ｜ B: 动作条件化帧序列** |
| payload | pose/twist/wrench/joint_state | frames/fps/duration/resolution | **A: level_map/entities/theme ｜ B: frames/action_history/current_action** |
| SafetyGate | 力矩/限位 | 内容审核（NSFW/暴力/版权） | **内容审核（gore/explicit），双模式** |
| 阵营 | 物理（共享 PhysicalWorldModelBase） | 像素（独立） | **像素（独立，内部分两个 direction）** |

---

## 4. GameBackbone Adapter 接口规范（不同开源项目间如何对接）

### 4.1 统一 adapter 接口（所有 game backbone 必须实现，方向感知）

```python
# branches/game/backbone_interface.py（V3 新增，不进 common）
class GameBackbone(ABC):
    """Game backbone adapter interface — all game backbones must implement this.

    This is the ANTI-CORRUPTION LAYER. The rest of the branch (wam/critic/...)
    talks to this interface, NEVER to the raw backbone API.
    One interface covers BOTH directions via config["direction"].
    """

    @abstractmethod
    def generate(self, prompt: str, config: dict) -> dict:
        """Generate game content from text prompt (+ optional action).

        Args:
            prompt: text description
            config: {
                "direction": "level" | "worldmodel",   # 必选
                # level 方向:
                "theme": str, "width": int, "height": int,
                "n_coins": int, "n_enemies": int,
                # worldmodel 方向:
                "action": str, "state_frames": list,
                "fps": int, "resolution": [w, h],
                # 通用:
                "retry": int,        # S9 重试计数（mock 用它收敛质量）
                "seed": int | None,  # 确定性
            }

        Returns（必含 "direction" + "meta"，其余按方向）:
            level:      {"direction":"level","level_map":[...],"width":int,
                         "height":int,"entities":[...],"theme":str,
                         "scene_description":str,"meta":{...}}
            worldmodel: {"direction":"worldmodel","frames":[...],"fps":int,
                         "resolution":[w,h],"action_history":[...],
                         "current_action":str,"scene_description":str,"meta":{...}}
        """
        ...

    @abstractmethod
    def get_info(self) -> dict:
        """Return backbone metadata: name, version, license, capabilities, directions."""
        ...
```

### 4.2 Mock 实现（V3 默认）

```python
# branches/game/backbone_mock.py
class MockGameBackbone(GameBackbone):
    """Deterministic mock for V3, covers BOTH directions.

    level:      sha256(prompt) → 确定性 tile map（保证起点可达终点；retry 提升可达性）
    worldmodel: sha256(prompt+action) → 确定性帧序列（动作→帧差非零且方向合理；retry 提升一致性）
    """
```

### 4.3 真 backbone adapter（Azure 阶段实现，V3 只做接口定义）

```python
# branches/game/backbone_gamegen.py        # 方向 B 主推（GameGen-O on Azure）
# branches/game/backbone_oasis.py          # 方向 B 备选（OASIS）
# branches/game/backbone_mariogpt.py       # 方向 A 主推（MarioGPT）
# 全部 raise NotImplementedError 直到过 T1–T5 门禁
```

---

## 5. Adapter 集成模式（E1–E6 合规）

```
branches/game/
├── adapter.py                  # 唯一入口：register(registry) + direction/backbone 选择
├── backbone_interface.py       # GameBackbone 抽象接口（防腐层核心，方向感知）
├── backbone_mock.py            # Mock 实现（V3 默认，双方向）
├── backbone_gamegen.py         # 方向 B 主推（Azure 阶段实现）
├── backbone_oasis.py           # 方向 B 备选
├── backbone_mariogpt.py        # 方向 A 主推
├── wam.py                      # GameWAM（WorldModel，调 backbone，传 direction）
├── critic.py                   # GameCritic（按 direction 分派校验）
└── ...
```

**关键规则**：
- `wam.py` 的 `predict_next_state` 内部调用 `backbone.generate(prompt, config)`（config 含 direction），**不直接调任何 backbone API**。
- `adapter.py` 的 `build_bundle(direction="level", backbone="mock", safety_mode="audit")` 决定方向 + backbone + 审核模式。
- 换方向/换 backbone 只改 `adapter.py` 参数，**wam/critic/primitives/mapper/executor 全不动**。
- backbone 异常在 adapter 内捕获，翻译成 common 异常类型。

---

## 6. 接口对齐检查清单（换真 backbone 前必查）

| 检查项 | Mock | GameGen-O(B) | OASIS(B) | MarioGPT(A) | 备注 |
|---|---|---|---|---|---|
| 方向 A：输出 tile map / level JSON | ✅ | ⚠️ 需转 | ❌ 不适合 | ⚠️ 需确认 | 格式是关键 |
| 方向 B：action 条件化生成 | ✅ | ⚠️ 需确认 | ⚠️ 需确认 | ❌ 不适合 | B 的核心 |
| 输出：确定性（seed） | ✅ | ⚠️ 需确认 | ⚠️ 需确认 | ⚠️ 需确认 | 影响 Critic |
| 输入：retry 收敛 | ✅ | N/A（真模型靠 Critic 判） | 同左 | 同左 | mock 专属 |
| 许可：商用可用 | N/A | ⚠️ T1 门禁 | ⚠️ T1 门禁 | ⚠️ T1 门禁 | **关键风险** |
| 开放权重可下 | N/A | ⚠️ 需确认 | ⚠️ 需确认 | ⚠️ 需确认 | T3 隔离安装前提 |

---

## 7. V3 开发顺序（依赖关系）

```
P0 scene_objects.py（关键词，双语，不依赖 backbone）
   ↓
P1 backbone_interface.py（GameBackbone 抽象接口，方向感知）
   ↓
P2 backbone_mock.py（Mock 实现，双方向，V3 默认）
   ↓
P3 wam.py（GameWAM 调 backbone.generate，传 direction）
   ↓
P4 critic.py（GameCritic 按 direction 分派校验）
   ↓
P5 primitives.py / P6 mapper.py / P7 executor.py + safety_gate.py（方向分派，不依赖 backbone）
   ↓
P8 adapter.py（register + direction/backbone/safety_mode 选择）
   ↓
P9 demo（双方向）+ 零 diff 验收
```

**关键**：P0–P2 是接口定义 + mock，P3–P9 是基于接口的实现。换真 backbone 时只新增 `backbone_<name>.py`，其他全不动。

---

## 8. 红线重申

1. 🔴 **common 零改动**——game 分支所有代码都在 `branches/game/` 内；方向分支只在 game 内部（payload/config/meta）。
2. 🔴 **backbone 只在 adapter**——wam/critic/... 不直接调 backbone API，走 `GameBackbone` 接口。
3. 🔴 **T1–T5 门禁必过**——接真 GameGen-O / OASIS / MarioGPT 前必须验证许可证/健康度/隔离安装/quickstart/接口探针。
4. 🔴 **V3 不装任何大模型**——全 mock，真模型走 Azure。
5. 🔴 **不新增 target**——两个方向共用一个 `target="game"`，不破坏"四场景"框架。
