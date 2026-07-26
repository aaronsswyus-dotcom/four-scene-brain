# branches/video — 视频分支（V2 · 全 mock）

> target=`video` ｜ modality=`pixel` ｜ backbone：V2 全 mock，真 HunyuanVideo / Wan-2.1 走 Azure（接入前过 engineering-setup §2 T1–T5 门禁）
> ⚠️ **边界声明**：V2 验证编排内核 + 接口 + 飞轮在**像素阵营**同样成立，**不证明视频质量**。mock 生成的是纯色占位帧，真质量靠 HunyuanVideo on Azure。

## 阵营差异（vs robot/3d）

video 属**像素阵营**，**不继承** `PhysicalWorldModelBase`（物理先验不适用），独立实现全部接口。backbone 通过 `VideoBackbone` 防腐层接入，换真模型只改 `adapter.py` 一行。

## State.payload 结构（分支冻结，为将来换真 HunyuanVideo 定死）

```
frames:            list      # 占位帧 [T]（mock 用 prompt-hash 纯色帧，采样上限 12）
frame_count:       int       # 逻辑总帧数 = round(duration_s * fps)
fps:               int       # 帧率（默认 24）
duration_s:        float     # 时长（秒，默认 5.0）
resolution:        [w, h]    # 分辨率（默认 640x480）
text_prompt:       str       # 文本描述（驱动生成）
scene_description: str       # backbone 场景理解（"cat run in grass"）
camera_motion:     str       # 镜头（zoom/pan/tilt/static）
refined_times:     int       # 重试细化次数
meta:              dict       # backbone 附加（color/quality_score/seed）
```

## 成功判定（Critic）

**硬指标优先**：duration 在目标 ±20% 内、fps ≥ 目标、resolution ≥ 目标（宽高均需达标）。
**软指标次之**：text-video 语义对齐（prompt 关键词 ∩ scene_description）。
判定来源写入 `Verification.meta.verification_source`（duration/fps/resolution/alignment/schema/hard_metrics+alignment）。

## SafetyGate（双模式，adapter 内可配置）

| 模式 | 检查 | 结果 |
|---|---|---|
| `audit`（默认） | text_prompt 含 NSFW/暴力/版权关键词 | **BLOCK**（降级 re-map 修不了，保持 BLOCK） |
| `audit` | 分辨率 < 240p 或时长 < 0.5s | **DEGRADE**（降级 re-map 钳制到安全下限 ≥240p/≥0.5s → 重检 PASS） |
| `audit` | 一切正常 | PASS |
| `passthrough` | 无检查 | PASS |

> **内容质量 vs 内容合规分离**：Critic 管质量，SafetyGate 管合规，互不混淆。关键词表保守（宁可漏不可错杀）。

## Backbone 接入（防腐层）

`wam.py` 只通过 `VideoBackbone.generate(prompt, config)` 调 backbone，**不直接调任何模型 API**。
- `backbone="mock"`（V2 默认）→ `MockVideoBackbone`（确定性纯色帧，retry 收敛 duration）
- `backbone="hunyuan-azure"` / `"wan-azure"` / `"cogvideox-azure"` → `NotImplementedError`（T1–T5 门禁未过）

换真 backbone：新增 `backbone_hunyuan.py`（实现 `VideoBackbone`）+ 改 `adapter.py` 一行，其余文件全不动。

## 文件

| 文件 | 接口 | 说明 |
|---|---|---|
| scene_objects.py | — | 视频关键词词汇表（动作/主体/场景/镜头），WAM+Critic 共用 |
| backbone_interface.py | VideoBackbone | 防腐层抽象接口（所有 backbone 必实现） |
| backbone_mock.py | VideoBackbone | Mock 实现，确定性纯色帧 + retry 收敛 duration |
| wam.py | WorldModel | VideoWAM，注入 backbone，转发 retry 触发细化 |
| critic.py | Critic | duration/fps/resolution 硬指标 + 语义对齐 |
| primitives.py | PrimitiveLibrary | cut/fade/overlay/zoom；video_spec 塞进 primitive.meta 透传 |
| mapper.py | Mapper | 基元 → 视频 Executable；degrade 时钳制到安全下限 |
| executor.py | Executor | 写**最小合法 mp4**（ftyp+mdat 占位，纯 stdlib） |
| safety_gate.py | SafetyGate | 双模式（audit/passthrough） |
| adapter.py | — | 防腐层 + `register(registry, backbone, safety_mode)`，backbone 唯一替换点 |
