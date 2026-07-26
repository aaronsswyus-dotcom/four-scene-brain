"""Scene3DExporter — S12 for 3d: Executable(mesh spec) -> placeholder GLB Delivery.

Writes a REAL, spec-valid glTF-2.0 binary (.glb) using pure stdlib
(json + struct). Placeholder quality: box meshes, no materials/textures.
Telemetry kind='geometry' with vertex/face counts (contract §8).
"""

import json
import struct
import time
from pathlib import Path

from common.interfaces.abstract import Executor
from common.interfaces.data_objects import Executable, Delivery


def _build_glb(scene_nodes: list) -> bytes:
    bin_data = bytearray()
    buffer_views, accessors, meshes, nodes = [], [], [], []

    for i, node in enumerate(scene_nodes):
        verts = node["mesh"]["vertices"]
        faces = node["mesh"]["faces"]
        # positions (float32, VEC3), 4-byte aligned by construction
        pos_offset = len(bin_data)
        for v in verts:
            bin_data += struct.pack("<3f", *[float(x) for x in v])
        buffer_views.append({"buffer": 0, "byteOffset": pos_offset,
                             "byteLength": len(verts) * 12, "target": 34962})
        mins = [min(v[k] for v in verts) for k in range(3)]
        maxs = [max(v[k] for v in verts) for k in range(3)]
        accessors.append({"bufferView": len(buffer_views) - 1, "componentType": 5126,
                          "count": len(verts), "type": "VEC3",
                          "min": [float(x) for x in mins], "max": [float(x) for x in maxs]})
        pos_acc = len(accessors) - 1
        # indices (uint16, SCALAR), pad to 4-byte alignment first
        while len(bin_data) % 4:
            bin_data += b"\x00"
        idx_offset = len(bin_data)
        flat = [i2 for f in faces for i2 in f]
        for idx in flat:
            bin_data += struct.pack("<H", idx)
        buffer_views.append({"buffer": 0, "byteOffset": idx_offset,
                             "byteLength": len(flat) * 2, "target": 34963})
        accessors.append({"bufferView": len(buffer_views) - 1, "componentType": 5123,
                          "count": len(flat), "type": "SCALAR"})
        meshes.append({"name": node["name"], "primitives": [
            {"attributes": {"POSITION": pos_acc}, "indices": len(accessors) - 1}]})
        nodes.append({"name": node["name"], "mesh": i})

    while len(bin_data) % 4:
        bin_data += b"\x00"
    gltf = {
        "asset": {"version": "2.0", "generator": "four-scene-brain V1 placeholder exporter"},
        "scene": 0, "scenes": [{"nodes": list(range(len(nodes)))}],
        "nodes": nodes, "meshes": meshes,
        "buffers": [{"byteLength": len(bin_data)}],
        "bufferViews": buffer_views, "accessors": accessors,
    }
    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    while len(json_bytes) % 4:
        json_bytes += b" "
    total = 12 + 8 + len(json_bytes) + 8 + len(bin_data)
    out = struct.pack("<4sII", b"glTF", 2, total)
    out += struct.pack("<II", len(json_bytes), 0x4E4F534A) + json_bytes   # JSON chunk
    out += struct.pack("<II", len(bin_data), 0x004E4942) + bytes(bin_data)  # BIN chunk
    return out


class Scene3DExporter(Executor):
    """Executor implementation; artifact = path to the written .glb file."""

    def __init__(self, output_dir: str = "output/3d") -> None:
        self.output_dir = Path(output_dir)

    def execute(self, executable: Executable) -> Delivery:
        p = executable.payload or {}
        nodes = p.get("scene_nodes", [])
        glb = _build_glb(nodes)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        task = p.get("task")   # None -> V1 robot_scene
        ts = int(time.time() * 1_000_000)
        # V4 generative -> model_<task>_<ts>.glb ; V1 robot_scene -> scene_<ts>.glb
        fname = f"model_{task}_{ts}.glb" if task else f"scene_{ts}.glb"
        path = self.output_dir / fname
        path.write_bytes(glb)
        faces_total = sum(len(n["mesh"]["faces"]) for n in nodes)
        telemetry = {"vertices": p.get("total_vertices", 0),
                     "faces": faces_total, "nodes": len(nodes),
                     "detail": p.get("detail", "normal"),
                     "glb_bytes": len(glb)}
        if task:   # enrich generative telemetry (flywheel can group by task)
            telemetry.update({"task": task,
                              "representation": p.get("representation", "mesh"),
                              "textured": p.get("texture") is not None})
        return Delivery(
            target="3d",
            artifact=str(path),
            meta={
                "glb_bytes": len(glb),
                "telemetry_kind": "geometry",
                "telemetry_data": telemetry,
            },
        )


if __name__ == "__main__":
    import tempfile, os
    box = {"vertices": [[x, y, z] for x in (0, 1) for y in (0, 1) for z in (0, 1)],
           "faces": [[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1],
                     [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]]}
    ex = Scene3DExporter(os.path.join(tempfile.gettempdir(), "fsb_glb_test"))
    d = ex.execute(Executable("geometry", {
        "scene_nodes": [{"name": "unit_box", "mesh": box}], "total_vertices": 8}, {}))
    data = Path(d.artifact).read_bytes()
    magic, version, length = struct.unpack("<4sII", data[:12])
    assert magic == b"glTF" and version == 2 and length == len(data)
    jlen, jtype = struct.unpack("<II", data[12:20])
    assert jtype == 0x4E4F534A
    doc = json.loads(data[20:20 + jlen])
    assert doc["asset"]["version"] == "2.0" and doc["meshes"][0]["name"] == "unit_box"
    assert d.meta["telemetry_kind"] == "geometry"
    os.remove(d.artifact)
    print("[OK] 3d exporter self-test passed (valid GLB header + JSON chunk)")
