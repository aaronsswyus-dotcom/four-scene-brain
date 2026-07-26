# branches/robot — 机器人分支（V1 · 全 mock）

> target=`robot` ｜ modality=`physical` ｜ backbone：V1 全 mock，真 GR00T 走 Azure（接入前过 engineering-setup §2 门禁）
> ⚠️ **边界声明**：V1 验证编排内核 + 接口 + 飞轮，**不证明物理可行性**。mock「假设可达」≠ 真实可达（sim2real）。

## State.payload 结构（分支冻结，为将来换真 GR00T 定死）

```
pose:        SE3  {xyz:[x,y,z], quat:[w,x,y,z]}
twist:       {linear:[vx,vy,vz], angular:[wx,wy,wz]}
wrench:      {force:[fx,fy,fz], torque:[tx,ty,tz]}
contact:     {in_contact:bool, points:[...]}
joint_state: {angles_rad:[...], torques_nm:[...]}    # 灵巧手 DOF=7(mock)
# mock 附加：plan(基元计划) / peak_contact_force_n / refined_times
```

## 成功判定（Critic）

**force-torque 阈值优先**（`goal.constraints.force_threshold_n`，默认 8.0N），视觉确认次之。
判定来源写入 `Verification.meta.verification_source`。

## SafetyGate（physical 强制）

| 检查 | 阈值 | 结果 |
|---|---|---|
| 力矩上限 | >20 Nm | BLOCK |
| 力矩偏高 | >8 Nm | DEGRADE（减半重映射一次） |
| 关节限位 | \|angle\|>3.0 rad | BLOCK |
| 禁撞区 | 基座 ±0.1m 盒 | BLOCK |

## 文件

| 文件 | 接口 | 说明 |
|---|---|---|
| wam.py | WorldModel | mock WAM（继承 PhysicalWorldModelBase），retry 时轨迹细化降力 |
| critic.py | Critic | 力/力矩阈值 + 视觉确认 |
| primitives.py | PrimitiveLibrary | plan → grasp/move/place/open/push |
| mapper.py | Mapper | 基元 → 关节力矩 Executable，支持 degrade 减半 |
| executor.py | Executor | **零力矩 mock**（只记录不下发） |
| safety_gate.py | SafetyGate | 上表四检查 |
| adapter.py | — | 防腐层 + `register(registry)`，backbone 唯一替换点 |
