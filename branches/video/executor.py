"""VideoExecutor — S12 execution: write a PLACEHOLDER mp4 (no real rendering).

Pure stdlib: emits a structurally-valid ISO-BMFF container (an `ftyp` box +
an `mdat` box holding placeholder frame metadata). This is a mock artifact — it
proves the delivery/telemetry path, NOT video quality. Real frames come from
HunyuanVideo on Azure later.

Delivery.meta carries telemetry_kind='video' + telemetry_data (contract §8:
the scene fills kind/data, common stores).

Pure stdlib. Zero third-party dependencies.
"""

import hashlib
import json
import struct
import time
from pathlib import Path

from common.interfaces.abstract import Executor
from common.interfaces.data_objects import Executable, Delivery

OUTPUT_DIR = Path("output/video")


def _box(box_type: str, payload: bytes) -> bytes:
    """ISO-BMFF box: [uint32 size][4-char type][payload]."""
    return struct.pack(">I", 8 + len(payload)) + box_type.encode("ascii") + payload


def _mp4_bytes(spec: dict) -> bytes:
    ftyp = _box("ftyp", b"isom" + struct.pack(">I", 0x200) + b"isom" + b"iso2" + b"mp41")
    manifest = json.dumps({"placeholder": True, "spec": spec}, ensure_ascii=False).encode("utf-8")
    mdat = _box("mdat", manifest)
    return ftyp + mdat


class VideoExecutor(Executor):
    def execute(self, executable: Executable) -> Delivery:
        p = executable.payload or {}
        spec = p.get("video_spec", {})
        prompt = p.get("text_prompt", "")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        name = f"video_{hashlib.sha1(prompt.encode('utf-8')).hexdigest()[:8]}.mp4"
        path = OUTPUT_DIR / name
        blob = _mp4_bytes(spec)
        path.write_bytes(blob)

        return Delivery(
            target="video",
            artifact={"mp4_path": str(path), "bytes": len(blob),
                      "resolution": p.get("resolution"),
                      "duration_s": p.get("duration_s"),
                      "primitive_sequence": spec.get("primitive_sequence", []),
                      "placeholder": True},
            meta={
                "telemetry_kind": "video",
                "telemetry_data": {
                    "duration_s": p.get("duration_s"),
                    "resolution": p.get("resolution"),
                    "fps": spec.get("fps"),
                    "degraded": (executable.meta or {}).get("degraded", False),
                    "bytes": len(blob),
                    "executed_at": time.time(),
                },
            },
        )


if __name__ == "__main__":
    ex = VideoExecutor()
    e = Executable("pixel", {
        "video_spec": {"fps": 24, "resolution": [640, 480], "primitive_sequence": ["cut", "fade"]},
        "text_prompt": "a cat running on the grass",
        "resolution": [640, 480], "duration_s": 5.0,
    }, {"degraded": False})
    d = ex.execute(e)
    assert d.target == "video" and d.meta["telemetry_kind"] == "video"
    assert d.artifact["placeholder"] is True

    # verify a legal mp4 header was written
    blob = Path(d.artifact["mp4_path"]).read_bytes()
    assert blob[4:8] == b"ftyp", "missing ftyp box"
    assert blob[8:12] == b"isom", "wrong major brand"
    assert b"mdat" in blob, "missing mdat box"
    print(f"[OK] video executor self-test passed -> {d.artifact['mp4_path']} ({d.artifact['bytes']} bytes)")
