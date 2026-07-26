"""InMemoryMemory — default zero-dependency Memory implementation (contract §8).

Real Mem0/cloud implementations replace this via the SAME Memory interface;
common stays unchanged.

Retrieval v0: naive token-overlap scoring (stdlib only). Good enough for the
minimal closed loop; NOT a semantic search claim.
"""

from common.interfaces.abstract import Memory


class InMemoryMemory(Memory):
    """dict/list-backed Memory. read = token-overlap top_k; write = append."""

    def __init__(self) -> None:
        self._items: list = []

    def read(self, query: str, top_k: int = 5) -> list:
        q_tokens = set(str(query).lower().split())
        if not q_tokens or not self._items:
            return list(self._items[-top_k:]) if not q_tokens else []
        scored = []
        for item in self._items:
            text = " ".join(str(v) for v in item.values()).lower()
            score = len(q_tokens & set(text.split()))
            if score > 0:
                scored.append((score, self._items.index(item), item))
        scored.sort(key=lambda x: (-x[0], -x[1]))
        return [item for _, _, item in scored[:top_k]]

    def write(self, item: dict) -> None:
        if not isinstance(item, dict):
            raise TypeError("Memory.write expects a dict")
        self._items.append(dict(item))

    def __len__(self) -> int:
        return len(self._items)


if __name__ == "__main__":
    m = InMemoryMemory()
    m.write({"goal": "grasp red cup", "score": 0.9})
    m.write({"goal": "place cup on tray", "score": 0.8})
    m.write({"goal": "unrelated note about weather", "score": 0.1})
    hits = m.read("grasp the red cup", top_k=2)
    assert hits and hits[0]["goal"] == "grasp red cup", hits
    assert len(m) == 3
    try:
        m.write("not a dict")  # type: ignore[arg-type]
        raise AssertionError("should raise TypeError")
    except TypeError:
        pass
    print("[OK] in_memory self-test passed")
