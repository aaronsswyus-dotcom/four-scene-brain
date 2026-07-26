# V2 开源项目清单 + Backbone Adapter 接口规范（2026-07-26 · V2 启动前定稿）

> 依据：common-contract §2/§10 红线、v2-development-plan.md、engineering-setup §2 五道门禁。
> 结论先行：**V2 本机运行时零三方依赖（跟 V1 一样）；所有 backbone 全 mock；真模型推迟到 Azure 阶段再过门禁接入。**

---

## 1. V2 本机实际使用（现在就装/用）

| 项目 | 用途 | 层 | 许可 | 状态 |
|---|---|---|---|---|
| Python 3.13 stdlib | common + video 分支全部实现 | common + branches | PSF | ✅ 唯一运行时依赖 |
| pytest | 测试 | 仅开发依赖 | MIT | ✅ 已装 |

**就这两项。** common 红线：零三方依赖；video 分支 V2 也全 mock，因此同样零三方依赖。

---

## 2. video backbone 候选（V2 全 mock，Azure 阶段接入）

| 优先级 | 项目 | GitHub | star | License | V2 处置 | T1 门禁风险 |
|---|---|---|---|---|---|---|
| **主推** | **HunyuanVideo** | [Tencent-Hunyuan/HunyuanVideo](https://github.com/Tencent-Hunyuan/HunyuanVideo) | 10k+ | Tencent Hunyuan Community License | mock（adapter 预留替换点） | ⚠️ **需复核商用条款**——社区许可可能有商用限制 |
| 备选 1 | **Wan-2.1** | [Wan-Video/Wan2.1](https://github.com/Wan-Video/Wan2.1) | 8k+ | Apache-2.0 | 备选（HunyuanVideo T1 不过关时切换） | ✅ 许可最干净 |
| 备选 2 | **CogVideoX** | [THUDM/CogVideo](https://github.com/THUDM/CogVideo) | 8k+ | Apache-2.0 | 备选（参数较小 2B，跑得动） | ✅ 许可干净 |

**决策逻辑**：
- 如果 HunyuanVideo 的 T1 许可证门禁（商用条款）过不了 → 切 Wan-2.1（Apache-2.0，最干净）
- 如果 Wan-2.1 资源要求太高 → 切 CogVideoX（2B 参数，跑得动）
- V2 mock 阶段三者接口结构对齐（见 §4），切换成本最低

---

## 3. V2 与 V1 的开源差异

| 维度 | V1（robot + 3d） | V2（video） |
|---|---|---|
| backbone | GR00T / DreamGaussian | **HunyuanVideo / Wan-2.1 / CogVideoX** |
| 输入 | 物理指令（抓取/移动/放置） | **文本 prompt** |
| 输出 | 关节力矩 / mesh/GLB | **视频帧 / mp4** |
| payload | pose/twist/wrench/contact/joint_state | **frames/fps/duration/text_prompt/resolution** |
| SafetyGate | 力矩/限位/禁撞区 | **内容审核（NSFW/暴力/版权）** |
| 阵营 | 物理（共享 PhysicalWorldModelBase） | **像素（独立实现）** |

---

## 4. Backbone Adapter 接口规范（不同开源项目间如何对接）

### 4.1 统一 adapter 接口（所有 video backbone 必须实现）

```python
# branches/video/backbone_interface.py（V2 新增，不进 common）
class VideoBackbone(ABC):
    """Video backbone adapter interface — all video backbones must implement this.

    This is the ANTI-CORRUPTION LAYER. The rest of the branch (wam/critic/...)
    talks to this interface, NEVER to the raw backbone API.
    """

    @abstractmethod
    def generate(self, prompt: str, config: dict) -> dict:
        """Generate video from text prompt.

        Args:
            prompt: text description
            config: {
                "duration_s": float,      # target duration
                "fps": int,               # target fps
                "resolution": [w, h],     # target resolution
                "seed": int | None,       # random seed for determinism
            }

        Returns:
            {
                "frames": list[list[list[int]]],  # [T][H][W][C] pixel array
                "fps": int,                        # actual fps
                "duration_s": float,               # actual duration
                "resolution": [w, h],              # actual resolution
                "scene_description": str,          # backbone's scene understanding
                "camera_motion": str,              # backbone's camera description
                "meta": dict,                      # backbone-specific extra info
            }
        """
        ...

    @abstractmethod
    def get_info(self) -> dict:
        """Return backbone metadata: name, version, license, capabilities."""
        ...
```

### 4.2 Mock 实现（V2 默认）

```python
# branches/video/backbone_mock.py
class MockVideoBackbone(VideoBackbone):
    """Deterministic mock for V2. Returns solid-color frames."""
    def generate(self, prompt: str, config: dict) -> dict:
        # ... deterministic mock logic ...
        pass
```

### 4.3 HunyuanVideo adapter（Azure 阶段实现，V2 只做接口定义）

```python
# branches/video/backbone_hunyuan.py
class HunyuanVideoBackbone(VideoBackbone):
    """HunyuanVideo adapter — calls Azure-hosted HunyuanVideo API.

    MUST pass T1-T5 gates before implementation.
    T1: Verify Hunyuan Community License allows commercial use.
    """
    def generate(self, prompt: str, config: dict) -> dict:
        # Azure API call → translate response to unified format
        pass
```

### 4.4 Wan-2.1 adapter（备选，接口预留）

```python
# branches/video/backbone_wan.py
class Wan21Backbone(VideoBackbone):
    """Wan-2.1 adapter — fallback if HunyuanVideo T1 gate fails."""
    pass
```

---

## 5. Adapter 集成模式（E1–E6 合规）

```
branches/video/
├── adapter.py                  # 唯一入口：register(registry) + backbone 选择
├── backbone_interface.py       # VideoBackbone 抽象接口（防腐层核心）
├── backbone_mock.py            # Mock 实现（V2 默认）
├── backbone_hunyuan.py         # HunyuanVideo adapter（Azure 阶段实现）
├── backbone_wan.py             # Wan-2.1 adapter（备选）
├── wam.py                      # VideoWAM（WorldModel 实现，调用 backbone）
├── critic.py                   # VideoCritic（校验 backbone 输出）
└── ...
```

**关键规则**：
- `wam.py` 的 `predict_next_state` 内部调用 `backbone.generate()`，**不直接调 HunyuanVideo API**
- `adapter.py` 的 `build_bundle(backbone="mock")` 决定用哪个 backbone
- 换 backbone 只改 `adapter.py` 的一行参数，**wam/critic/primitives/mapper/executor 全不动**
- backbone 异常在 adapter 内捕获，翻译成 common 的异常类型（TimeoutError/ConnectionError/etc）

---

## 6. 接口对齐检查清单（换真 backbone 前必查）

| 检查项 | Mock | HunyuanVideo | Wan-2.1 | 备注 |
|---|---|---|---|---|
| 输入：text prompt | ✅ | ✅ | ✅ | 都支持 |
| 输入：duration/fps/resolution 指定 | ✅ | ⚠️ 需确认 | ⚠️ 需确认 | T5 门禁时验证 |
| 输出：frames 数组 [T][H][W][C] | ✅ | ⚠️ 需确认格式 | ⚠️ 需确认格式 | 可能需 adapter 转换 |
| 输出：scene_description | ✅ | ⚠️ 需确认 | ⚠️ 需确认 | 可能需额外调用 |
| 输出：确定性（seed） | ✅ | ⚠️ 需确认 | ⚠️ 需确认 | 影响 Critic 校验 |
| 许可：商用可用 | N/A | ⚠️ T1 门禁 | ✅ Apache-2.0 | **HunyuanVideo 关键风险** |

---

## 7. V2 开发顺序（依赖关系）

```
P0 scene_objects.py（关键词词汇表，不依赖 backbone）
   ↓
P1 backbone_interface.py（定义 VideoBackbone 抽象接口）
   ↓
P2 backbone_mock.py（Mock 实现，V2 默认）
   ↓
P3 wam.py（VideoWAM 调用 backbone.generate）
   ↓
P4 critic.py（VideoCritic 校验 backbone 输出）
   ↓
P5 primitives.py / mapper.py / executor.py / safety_gate.py（独立，不依赖 backbone）
   ↓
P6 adapter.py（register + backbone 选择）
   ↓
P7 demo + P8 零 diff 验收
```

**关键**：P0–P2 是接口定义 + mock，P3–P7 是基于接口的实现。换真 backbone 时只新增 `backbone_hunyuan.py`，其他全不动。

---

## 8. 红线重申

1. 🔴 **common 零改动**——video 分支所有代码都在 `branches/video/` 内。
2. 🔴 **backbone 只在 adapter**——wam/critic/... 不直接调 backbone API，走 `VideoBackbone` 接口。
3. 🔴 **T1–T5 门禁必过**——接真 HunyuanVideo 前必须验证许可证/健康度/隔离安装/quickstart/接口探针。
4. 🔴 **V2 不装任何大模型**——全 mock，真模型走 Azure。
