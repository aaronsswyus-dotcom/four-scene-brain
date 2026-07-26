# branches/3d — 3D 分支（V1 · 仅 robot 作业场景 · 全 mock）

> target=`3d` ｜ modality=`geometry` ｜ **V1 范围 = robot 的 3D 作业场景**（机器人所处/操作的物理环境）
> 完整独立 3D（文生3D / 概念图→GLB / 点云补全 / PBR）归 **V4**，届时扩展本分支，**common 零改动**。
> backbone：V1 全 mock，真 DreamGaussian/TRELLIS 走 Azure（先过 engineering-setup §2 门禁）。

## State.payload 结构（分支冻结）

```
representation: gaussians | pointcloud | mesh
semantics:      {objects:[...], walkable:bool, walkable_area_m2:float}
# mock 附加：layout(物体摆放) / fidelity / refined_times
```

## 成功判定（Critic · V1 场景向）

**可行走性 + 几何保真（`goal.constraints.min_fidelity`，默认 0.7）+ 文本-场景对齐**（如「含桌子/杯子/可通行」）。
判定来源写入 `Verification.meta.verification_source`。

## 导出（Exporter = Executor 实现）

纯 stdlib（json+struct）写出 **规范合法的 glTF-2.0 二进制（.glb）占位文件**（盒体网格、无材质），路径即 `Delivery.artifact`。

## 与 robot 的共享

只共享 `branches/_physical/base.py` 的 `PhysicalWorldModelBase`（WAM 物理先验，想象层）；执行层各自实现（robot=力矩，3d=mesh→GLB）。

## 导入说明

目录名 `3d` 以数字开头，外部加载用 `importlib.import_module('branches.3d.adapter')`；包内使用相对导入。

## 文件

| 文件 | 接口 | 说明 |
|---|---|---|
| wam.py | WorldModel | mock 场景想象（继承 PhysicalWorldModelBase），retry 提升保真 |
| critic.py | Critic | 可行走+保真+对齐三检查 |
| primitives.py | PrimitiveLibrary | floor / place_object |
| mapper.py | Mapper | 基元 → 盒体 mesh 场景谱 |
| exporter.py | Executor | mesh 谱 → 占位 GLB 文件 |
| safety_gate.py | SafetyGate | 资源上限 sanity（>100 万顶点 BLOCK） |
| adapter.py | — | 防腐层 + `register(registry)`，backbone 唯一替换点 |
