"""FileBufferFlywheel — default Flywheel implementation (contract §8).

S13 record: unified Telemetry intake (kind/data are scene-filled; common only stores).
S14 distill: LOCAL BUFFER ONLY — flushes the in-memory buffer to a JSONL file.
No training happens locally (D4: periodic cloud feedback implements same interface).

Pure stdlib.
"""

import json
import time
from dataclasses import asdict
from pathlib import Path

from common.interfaces.abstract import Flywheel
from common.interfaces.data_objects import Telemetry


class FileBufferFlywheel(Flywheel):
    """Buffers Telemetry in memory; distill() appends to a JSONL file."""

    def __init__(self, buffer_path: str) -> None:
        self._path = Path(buffer_path)
        self._buffer: list = []
        self._distilled_count = 0

    def record(self, telemetry: Telemetry) -> None:
        if not isinstance(telemetry, Telemetry):
            raise TypeError("Flywheel.record expects a Telemetry")
        self._buffer.append(telemetry)

    def distill(self) -> None:
        """Flush buffer to disk (append). Local buffer only — never trains."""
        if not self._buffer:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as f:
            for t in self._buffer:
                row = asdict(t)
                row["_distilled_at"] = time.time()
                f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        self._distilled_count += len(self._buffer)
        self._buffer.clear()

    @property
    def pending(self) -> int:
        return len(self._buffer)

    @property
    def distilled(self) -> int:
        return self._distilled_count


if __name__ == "__main__":
    import tempfile, os
    path = os.path.join(tempfile.gettempdir(), "fsb_flywheel_selftest.jsonl")
    if os.path.exists(path):
        os.remove(path)
    fw = FileBufferFlywheel(path)
    fw.record(Telemetry("tr-1", "sg-1", "torque", {"peak": 1.2}, time.time()))
    fw.record(Telemetry("tr-1", "sg-2", "geometry", {"verts": 100}, time.time()))
    assert fw.pending == 2
    fw.distill()
    assert fw.pending == 0 and fw.distilled == 2
    with open(path, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f]
    assert len(rows) == 2 and rows[0]["trace_id"] == "tr-1"
    fw.distill()  # empty buffer -> no-op
    assert fw.distilled == 2
    try:
        fw.record({"not": "telemetry"})  # type: ignore[arg-type]
        raise AssertionError("should raise TypeError")
    except TypeError:
        pass
    os.remove(path)
    print("[OK] file_buffer self-test passed")
