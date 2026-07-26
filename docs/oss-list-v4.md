# V4 开源项目清单 + 3DBackbone Adapter 接口规范（2026-07-26 · V4 启动前定稿）

> 依据：common-contract §2/§10 红线、`v4-development-plan.md`（3d 扩展为全量多任务）、engineering-setup §2 五道门禁。
> 结论先行：**V4 本机运行时零三方依赖（同前各版本）；所有 backbone 全 mock；真模型推迟到 Azure 阶段再过门禁接入。**
> **一个分支多任务**：robot_scene/text_to_3d/image_to_3d/pointcloud_completion/pbr_texture 经统一 `ThreeDBackbone` 接口对齐。

---

## 1. V4 本机实际使用（现在就装/用）

| 项目 | 用途 | 层 | 许可 | 状态 |
|---|---|---|---|---|
| Python 3.13 stdlib | common + 3d 分支全部实现 | common + branches | PSF | ✅ 唯一运行时依赖 |
| pytest | 测试 | 仅开发依赖 | MIT | ✅ 已装 |

**就这两项。** common 红线：零三方依赖；3d 分支 V4 也全 mock，同样零三方依赖。

---

## 2. 3d backbone 候选（V4 全 mock，Azure 阶段接入）

| 优先级 | 项目 | GitHub | 覆盖任务 | License | V4 处置 | T1 门禁风险 |
|---|---|---|---|---|---|---|
| **主推** | **TRELLIS**（微软） | [microsoft/TRELLIS](https://github.com/microsoft/TRELLIS) | text_to_3d / image_to_3d / pbr_texture（统一最强） | MIT（⚠️ 权重条款复核） | mock（adapter 预留替换点） | ⚠️ 权重/商用需核实 |
| 备选 1 | **TripoSR** | [VAST-AI-Research/TripoSR](https://github.com/VAST-AI-Research/TripoSR) | image_to_3d（单图快转 3D，最贴） | MIT | 备选（image 任务切换） | ⚠️ 需复核 |
| 备选 2 | **DreamGaussian** | [jiaxiang-ren/dreamgaussian](https://github.com/jiaxiang-ren/dreamgaussian) | text/image_to_3d（V1 已用 mock，学术） | MIT | 备选（TRELLIS 不过关时） | ⚠️ 维护趋缓，T2 复核 |
| 备选 3 | **Shap-E / Point-E** | [openai/shap-e](https://github.com/openai/shap-e) | text_to_3d / pointcloud | MIT | 备选（text/点云任务） | ⚠️ 需复核 |
| 参考 | **Stable Fast 3D (SF3D)** | Stability AI | image_to_3d（带 UV/材质） | Stability Community License | 参考 | ⚠️ 社区许可商用需复核 |
| 点云补全专选 | **PoinTr / PCN** | 学术 | pointcloud_completion | ⚠️ 需复核 | 备选（补全任务） | ⚠️ 需复核 |

**决策逻辑**：
- **首选 TRELLIS**（微软、活跃、一个模型覆盖 text/image→3D + PBR，最省 adapter 工作量）；T1（权重/商用）不过关 → 按任务降级：image_to_3d→**TripoSR**，text_to_3d→**Shap-E**，通用→**DreamGaussian**。
- 点云补全生态分散（PoinTr/PCN 等学术项目），mock 阶段接口对齐即可，真接入时再单独立项评估。
- V4 mock 阶段所有候选经统一 `ThreeDBackbone` 接口对齐（见 §4），切换成本最低。

---

## 3. V4 与 V1/V2/V3 的开源差异

| 维度 | V1（robot+3d） | V2（video） | V3（game） | V4（完整 3D） |
|---|---|---|---|---|
| backbone | GR00T / DreamGaussian | HunyuanVideo / Wan-2.1 | MarioGPT / GameGen-O | **TRELLIS / TripoSR / DreamGaussian / Shap-E** |
| 输入 | 物理指令 | 文本 | 文本(+动作) | **文本 / 图像 / 点云** |
| 输出 | 力矩 / GLB 占位 | mp4 | level JSON / replay | **mesh / GLB（含 PBR）** |
| payload | pose/wrench | frames/fps | level_map / frames+action | **geometry/semantics/texture/task** |
| 阵营 | 物理（共享 PhysicalWAM） | 像素（独立） | 像素（独立） | **物理（共享 PhysicalWAM）** |
| 分支关系 | 新建 | 新建 | 新建 | **扩展 V1 的 3d** |

---

## 4. 3DBackbone Adapter 接口规范（不同开源项目间如何对接）

### 4.1 统一 adapter 接口（所有 3d backbone 必须实现，任务感知）

```python
# branches/3d/backbone_interface.py（V4 新增，不进 common）
class ThreeDBackbone(ABC):
    """3D backbone adapter interface — all 3d backbones must implement this.

    ANTI-CORRUPTION LAYER. The branch talks to this interface, NEVER to the raw
    backbone API. One interface covers ALL tasks via config["task"].
    """

    @abstractmethod
    def generate(self, prompt: str, config: dict) -> dict:
        """Generate 3D content.

        Args:
            prompt: text description
            config: {
                "task": "robot_scene"|"text_to_3d"|"image_to_3d"|
                        "pointcloud_completion"|"pbr_texture",   # 必选
                "source_image": str | None,        # image_to_3d 输入（占位引用）
                "source_pointcloud": dict | None,  # pointcloud_completion 输入
                "representation": "gaussians"|"pointcloud"|"mesh"|"glb",
                "poly_budget": int, "seed": int | None, "retry": int,
            }

        Returns（必含 "task" + "meta"，其余按任务）:
            {"task": str, "representation": str,
             "geometry": {"vertices": int, "faces": int, "manifold": bool, "bbox": [...]},
             "semantics": [...], "texture": {...} | None,
             "source": str, "scene_description": str, "meta": {...}}
        """
        ...

    @abstractmethod
    def get_info(self) -> dict:
        """Return backbone metadata: name, version, license, capabilities, tasks."""
        ...
```

### 4.2 Mock 实现（V4 默认）

```python
# branches/3d/backbone_mock.py
class Mock3DBackbone(ThreeDBackbone):
    """Deterministic mock for V4, covers ALL tasks.

    sha256(prompt+task) → 确定性 geometry（manifold=True, vertices/faces>0, bbox 非退化）；
    retry 时提升 manifold/语义对齐（模拟细化）。
    """
```

### 4.3 真 backbone adapter（Azure 阶段实现，V4 只做接口定义）

```python
# branches/3d/backbone_trellis.py     # 主推（TRELLIS on Azure）
# branches/3d/backbone_triposr.py     # image_to_3d 备选
# branches/3d/backbone_dreamgaussian.py  # 备选（V1 沿用）
# 全部 raise NotImplementedError 直到过 T1–T5 门禁
```

---

## 5. Adapter 集成模式（E1–E6 合规）

```
branches/3d/
├── adapter.py                  # 唯一入口：register(registry) + task/backbone 选择
├── backbone_interface.py       # ThreeDBackbone 抽象接口（防腐层核心，任务感知）
├── backbone_mock.py            # Mock 实现（V4 默认，多任务）
├── backbone_trellis.py         # 主推（Azure 阶段实现）
├── backbone_triposr.py         # image 备选
├── wam.py                      # 3dWAM（继承 PhysicalWorldModelBase，调 backbone，传 task）
├── critic.py                   # 3dCritic（按 task 分派校验）
└── ...（V1 已有：primitives/mapper/executor(占位GLB)/safety_gate/scene_objects/README）
```

**关键规则**：
- `wam.py` 的 `predict_next_state` 内部调用 `backbone.generate(prompt, config)`（config 含 task），**不直接调任何 backbone API**。
- `adapter.py` 的 `build_bundle(task="text_to_3d", backbone="mock", safety_mode="audit")` 决定任务 + backbone + 审核模式。
- 换任务/换 backbone 只改 `adapter.py` 参数，**wam/critic/primitives/mapper/executor 全不动**。
- backbone 异常在 adapter 内捕获，翻译成 common 异常类型。
- **不删 V1 robot_scene 能力**：Mock3DBackbone 对 `task="robot_scene"` 保持 V1 行为。

---

## 6. 接口对齐检查清单（换真 backbone 前必查）

| 检查项 | Mock | TRELLIS | TripoSR | DreamGaussian | 备注 |
|---|---|---|---|---|---|
| text_to_3d | ✅ | ✅ | ⚠️ 弱 | ✅ | 需确认输出格式 |
| image_to_3d | ✅ | ✅ | ✅ 强 | ✅ | 需确认 |
| pointcloud_completion | ✅ | ⚠️ 需确认 | ❌ | ⚠️ 需确认 | 或专选 PoinTr |
| pbr_texture | ✅ | ✅ 强 | ⚠️ 弱 | ⚠️ 需确认 | TRELLIS 优势 |
| 输出：GLB/mesh 可导出 | ✅ | ⚠️ 需确认 | ⚠️ 需确认 | ⚠️ 需确认 | adapter 转换 |
| 输出：确定性（seed） | ✅ | ⚠️ 需确认 | ⚠️ 需确认 | ⚠️ 需确认 | 影响 Critic |
| 许可：商用可用 | N/A | ⚠️ T1 门禁 | ⚠️ T1 门禁 | ✅ MIT | **关键风险** |

---

## 7. V4 开发顺序（依赖关系）

```
P0 scene_objects.py 扩展（物体/材质/属性关键词，双语）
   ↓
P1 backbone_interface.py（ThreeDBackbone 抽象接口，任务感知）
   ↓
P2 backbone_mock.py（Mock 实现，多任务，V4 默认；robot_scene 保持 V1 行为）
   ↓
P3 wam.py（3dWAM 继承 PhysicalWorldModelBase，调 backbone，传 task）
   ↓
P4 critic.py（3dCritic 按 task 分派校验）
   ↓
P5 primitives.py / P6 mapper.py / P7 executor.py + safety_gate.py（任务分派）
   ↓
P8 adapter.py（register + task/backbone/safety_mode 选择）+ V1 robot_scene 回归
   ↓
P9 demo（多任务）+ 零 diff 验收
```

**关键**：P0–P2 是接口定义 + mock，P3–P9 是基于接口的实现。换真 backbone 时只新增 `backbone_<name>.py`，其他全不动。

---

## 8. 红线重申

1. 🔴 **common 零改动**——3d 扩展所有代码都在 `branches/3d/` 内；任务分支只在 3d 内部（payload/config/meta）。
2. 🔴 **backbone 只在 adapter**——wam/critic/... 不直接调 backbone API，走 `ThreeDBackbone` 接口。
3. 🔴 **T1–T5 门禁必过**——接真 TRELLIS / TripoSR 前必须验证许可证/健康度/隔离安装/quickstart/接口探针。
4. 🔴 **V4 不装任何大模型**——全 mock，真模型走 Azure。
5. 🔴 **不新增 target**——仍是 `target="3d"`，扩展不新建分支。
6. 🔴 **V1 robot_scene 不回归**——扩展不得破坏已交付能力。
