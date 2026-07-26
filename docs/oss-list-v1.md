# V1 开源项目清单（2026-07-26 · 开发启动前定稿）

> 依据：common-contract §2/§10 红线（common 纯 stdlib）、v1-development-plan §6、engineering-setup §2 五道测试门禁。
> 结论先行：**V1 本机运行时零三方依赖；所有 backbone 全 mock；真模型全部推迟到 Azure 阶段再过门禁接入。**

## 1. V1 本机实际使用（现在就装/用）

| 项目 | 用途 | 层 | 许可 | 状态 |
|---|---|---|---|---|
| Python 3.13 stdlib（dataclasses/abc/enum/json/uuid/time/pathlib） | common 全部实现 | common | PSF | ✅ 唯一运行时依赖 |
| pytest | 契约测试 + 单元测试 | 仅开发依赖（不进 common 运行期） | MIT | ✅ 装入隔离 venv |

**就这两项。** common 红线：零三方依赖；branches 在 V1 也全 mock，因此同样零三方依赖。

## 2. backbone 候选（V1 全 mock，Azure 阶段接入，接入前必过 T1–T5 门禁）

| 分支 | 候选 backbone | GitHub 热度/维护 | 许可 | V1 处置 |
|---|---|---|---|---|
| robot | NVIDIA Isaac GR00T N1.5 | ~4k+ star，NVIDIA 官方维护 | Apache-2.0（模型权重 NVIDIA license，需 T1 复核） | mock（`branches/robot/wam.py` 内 MockWAM，adapter 预留替换点） |
| 3d（robot 作业场景） | DreamGaussian | ~4k star，学术项目（维护趋缓，T2 需复核） | MIT | mock（`branches/3d/adapter.py` 内 Mock3DBackbone） |
| 3d 备选 | TRELLIS（微软） | ~9k star，活跃 | MIT | V4 再评估，V1 不动 |
| （V2 预告）video | HunyuanVideo | ~10k star | Tencent Hunyuan Community License | V2 再过门禁 |
| （V3 预告）game | GameGen-O / GameNGen 系 | 研究型 | 待查 | V3 再过门禁 |

## 3. 基础设施类候选（V1 用 stdlib 默认实现，后续同接口替换）

| 能力 | V1 实现 | 后续可替换开源项目 | 替换方式 |
|---|---|---|---|
| Memory (S6) | InMemoryMemory（dict） | Mem0（~30k star，Apache-2.0） | 实现同一 `Memory` 接口，common 零改动 |
| Flywheel (S13/S14) | FileBufferFlywheel（jsonl 落盘） | 云端回灌管道（Azure） | 实现同一 `Flywheel` 接口 |
| S3/S4 意图解析 | 规则/模板解析（D1 拍板） | LLM 插件（可选） | Orchestrator 可选注入，非必需 |

## 4. 纪律重申

1. 任何真 backbone 接入前必过 engineering-setup §2 的 T1 许可证 → T2 健康度 → T3 隔离安装 → T4 官方 quickstart → T5 接口探针。
2. backbone 只出现在 `branches/<scene>/adapter`（防腐层）内，绝不进 common，绝不反向控制编排循环（E1–E6）。
3. V1 本机不装任何大模型/GPU 依赖（红线）。
