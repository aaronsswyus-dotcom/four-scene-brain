# four-scene-brain

> **brain = Orchestrator**：模态无关的编排内核，把人类语言/机器自观输入路由到四个世界模型分支（robot / game / 3d / video），生成内容经 Critic 校验，遥测汇入数据飞轮。
> 自研范围：**通用主干编排层 + 统一接口 + 跨分支数据飞轮**；其余全部由开源模型组装（经防腐层接入）。

## 当前状态：V1 已交付（common + robot + 3d robot作业场景）

| 版本 | 组合 | 状态 |
|---|---|---|
| **V1** | common + robot + 3d（robot 作业场景） | ✅ **本仓库当前版本** |
| V2 | + video | 计划 |
| V3 | + game | 计划 |
| V4 | + 完整独立 3D | 计划 |
| V5 | 全场景集成 | 计划 |

## ⚠️ 边界声明（V1 DoD #7）

**V1 验证的是编排内核 + 接口契约 + 数据飞轮，不证明单场景物理可行性。**
所有 backbone 均为 mock（真 GR00T / DreamGaussian 后续走 Azure，接入前过 `docs/engineering-setup.md` §2 五道门禁）。mock 的「假设可达」≠ 真实物理可达（sim2real 缺口）。

## 快速开始（Python 3.13，零三方运行时依赖）

```bash
# robot 最小闭环：复合 DAG（抓杯→移动→放置）+ S9 重试 + SafetyGate BLOCK/DEGRADE
python -m examples.robot_demo

# 3d 最小闭环：机器人作业客厅场景 → 占位 GLB + 跨分支 DAG（3d→robot）
python -m examples.3d_scene_demo

# 冻结验收
python -m tests.test_contract     # 反射契约测试：接口/字段/枚举一字不改
python -m tests.test_zero_diff    # 零 diff 验收：新增 mock5 场景，common 零改动
```

## 结构

```
common/               # 冻结内核（纯 stdlib，v1.0.0，写一次永不改）
├── interfaces/       #   数据对象 + 8 个抽象接口（唯一交换语言）
├── orchestrator/     #   S1–S14 状态机（DAG/重试/SafetyGate/异常映射）
├── registry/         #   BranchBundle 插件注册与解析
├── memory/           #   InMemoryMemory（S6 默认实现）
└── flywheel/         #   FileBufferFlywheel（S13/S14，本地只缓冲不训）
branches/
├── _physical/        #   物理阵营共享 WAM 先验基类（场景侧，非 common）
├── robot/            #   V1 ✅ 机器人分支（全 mock，零力矩执行）
├── 3d/               #   V1 ✅ robot 作业场景（占位 GLB 导出）
├── video/ game/      #   V2/V3 占位
examples/             # 两个最小闭环 demo
tests/                # 契约测试 + 零 diff 验收
docs/                 # 冻结契约与全部设计文档（见 docs/README.md 索引）
```

## 三条铁律

1. **写一次，永冻结**：common 合入后零改动，新场景只加 `branches/<scene>/`。
2. **场景即插件**：common 无场景名/backbone 名/模态 if-else，差异全走 opaque payload + meta。
3. **唯一交换语言**：common 与场景之间只交换 `docs/common-contract.md` §4/§5 定义的对象与签名。

权威契约：`docs/common-contract.md`（v1.0-FROZEN）。
