"""_flywheel_view — V5 P0: cross-branch telemetry aggregation view.

Reads the JSONL that FileBufferFlywheel.distill() appends to (contract §8) and
groups rows by Telemetry.kind, mapping each kind to its owning branch. This is a
READ-ONLY view living on the examples/ side — it NEVER touches common/flywheel
(the frozen kernel only stores Telemetry; V5 does the grouping outside).

Each JSONL row is a serialised Telemetry:
    {trace_id, subgoal_id, kind, data, ts, _distilled_at}

Kind -> branch map (the four scenes each fill their own `telemetry_kind`):
    torque   -> robot   (V1 physical camp)
    geometry -> 3d      (V1 robot_scene + V4 full 3D)
    video    -> video   (V2 pixel camp)
    game     -> game    (V3 pixel camp)

Pure stdlib. Zero third-party dependencies.

Run:  python -m examples._flywheel_view   (self-test with a synthetic jsonl)
"""

import json
from pathlib import Path

# kind -> branch (scenes own their kind; this map lives outside common on purpose)
KIND_TO_BRANCH = {
    "torque": "robot",
    "geometry": "3d",
    "video": "video",
    "game": "game",
}


def _extract_score(data: dict):
    """Best-effort score pull from opaque telemetry_data (None if scene didn't fill one)."""
    if not isinstance(data, dict):
        return None
    for key in ("score", "critic_score", "quality"):
        v = data.get(key)
        if isinstance(v, (int, float)):
            return float(v)
    return None


def aggregate_by_branch(jsonl_path) -> dict:
    """Group flywheel Telemetry rows by kind (=branch). Read-only.

    Returns a dict keyed by kind:
        {
          "<kind>": {
              "branch": str,               # mapped scene name (or "unknown:<kind>")
              "count": int,                # number of Telemetry rows
              "traces": [trace_id, ...],   # unique trace ids (sorted)
              "subgoals": [subgoal_id, ...],
              "avg_score": float | None,   # mean of any scores found in data
          },
          ...
        }
    Missing file -> {} (nothing distilled yet).
    """
    path = Path(jsonl_path)
    if not path.exists():
        return {}

    groups: dict = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue  # skip malformed lines defensively
        kind = row.get("kind", "delivery")
        g = groups.setdefault(kind, {
            "branch": KIND_TO_BRANCH.get(kind, f"unknown:{kind}"),
            "count": 0,
            "_traces": set(),
            "_subgoals": [],
            "_scores": [],
        })
        g["count"] += 1
        tid = row.get("trace_id")
        if tid:
            g["_traces"].add(tid)
        sid = row.get("subgoal_id")
        if sid:
            g["_subgoals"].append(sid)
        score = _extract_score(row.get("data", {}))
        if score is not None:
            g["_scores"].append(score)

    # finalise: convert working sets/lists into stable public shape
    agg: dict = {}
    for kind, g in groups.items():
        scores = g["_scores"]
        agg[kind] = {
            "branch": g["branch"],
            "count": g["count"],
            "traces": sorted(g["_traces"]),
            "subgoals": g["_subgoals"],
            "avg_score": round(sum(scores) / len(scores), 4) if scores else None,
        }
    return agg


def print_summary(agg: dict) -> None:
    """Human-readable cross-branch flywheel summary."""
    if not agg:
        print("[flywheel-view] 无 Telemetry（缓冲未落盘或路径不存在）")
        return
    total = sum(g["count"] for g in agg.values())
    branches = sorted({g["branch"] for g in agg.values()})
    print("-" * 64)
    print(f"[跨分支飞轮聚合] 共 {total} 条 Telemetry，覆盖 {len(agg)} 种 kind / "
          f"{len(branches)} 个分支：{branches}")
    print("-" * 64)
    print(f"{'kind':<12}{'branch':<10}{'count':>6}{'traces':>8}{'avg_score':>12}")
    for kind in sorted(agg):
        g = agg[kind]
        score = "n/a" if g["avg_score"] is None else f"{g['avg_score']:.4f}"
        print(f"{kind:<12}{g['branch']:<10}{g['count']:>6}{len(g['traces']):>8}{score:>12}")
    print("-" * 64)


if __name__ == "__main__":
    import tempfile, os, time

    path = os.path.join(tempfile.gettempdir(), "fsb_flywheel_view_selftest.jsonl")
    if os.path.exists(path):
        os.remove(path)

    # synthesise a cross-branch jsonl: robot(torque)x2, 3d(geometry)x1, video x1, game x1
    rows = [
        {"trace_id": "tr-a", "subgoal_id": "sg-1", "kind": "torque",
         "data": {"peak_torque_nm": 2.0, "score": 0.9}, "ts": time.time()},
        {"trace_id": "tr-a", "subgoal_id": "sg-2", "kind": "torque",
         "data": {"peak_torque_nm": 1.5, "score": 0.8}, "ts": time.time()},
        {"trace_id": "tr-a", "subgoal_id": "sg-3", "kind": "geometry",
         "data": {"vertices": 100, "task": "text_to_3d"}, "ts": time.time()},
        {"trace_id": "tr-b", "subgoal_id": "sg-1", "kind": "video",
         "data": {"duration_s": 5.0}, "ts": time.time()},
        {"trace_id": "tr-b", "subgoal_id": "sg-2", "kind": "game",
         "data": {"direction": "level"}, "ts": time.time()},
    ]
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    # add a malformed line to prove defensive parsing
    with open(path, "a", encoding="utf-8") as f:
        f.write("{not json}\n")

    agg = aggregate_by_branch(path)
    assert set(agg) == {"torque", "geometry", "video", "game"}, agg
    assert agg["torque"]["count"] == 2 and agg["torque"]["branch"] == "robot"
    assert agg["torque"]["traces"] == ["tr-a"]
    assert agg["torque"]["avg_score"] == 0.85          # (0.9 + 0.8) / 2
    assert agg["geometry"]["branch"] == "3d" and agg["geometry"]["avg_score"] is None
    assert agg["video"]["branch"] == "video" and agg["game"]["branch"] == "game"

    # missing file -> empty dict
    assert aggregate_by_branch(path + ".nope") == {}

    print_summary(agg)
    os.remove(path)
    print("[OK] _flywheel_view self-test passed (group by kind/branch + avg_score + defensive)")
