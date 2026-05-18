from __future__ import annotations

import asyncio
from pathlib import Path

class HaystackStorage:
    def __init__(self, volume_dir: Path, max_volume_size: int):
        self.volume_dir = volume_dir
        self.volume_dir.mkdir(parents=True, exist_ok=True)
        self.max_volume_size = max_volume_size
        self.volume_id = self._discover_last_volume()
        self.file = None
        self.lock = asyncio.Lock()
        self._open_active_volume()

    def _discover_last_volume(self) -> int:
        volumes = sorted(self.volume_dir.glob("volume_*.dat"))
        if not volumes:
            return 1
        ids = []
        for volume in volumes:
            try:
                ids.append(int(volume.stem.split("_")[1]))
            except Exception:
                pass
        return max(ids) if ids else 1

    def _path(self, volume_id: int) -> Path:
        return self.volume_dir / f"volume_{volume_id}.dat"

    def _open_active_volume(self) -> None:
        self.file = open(self._path(self.volume_id), "ab+")

    def _current_size(self) -> int:
        self.file.seek(0, 2)
        return self.file.tell()

    def _rotate_if_needed(self, incoming_size: int) -> None:
        if self._current_size() + incoming_size <= self.max_volume_size:
            return
        self.file.close()
        self.volume_id += 1
        self._open_active_volume()

    async def append(self, payload: bytes) -> dict[str, int]:
        async with self.lock:
            self._rotate_if_needed(len(payload))
            self.file.seek(0, 2)
            offset = self.file.tell()
            self.file.write(payload)
            self.file.flush()
            return {"volume_id": self.volume_id, "offset": offset, "size": len(payload)}

    def read(self, volume_id: int, offset: int, size: int) -> bytes:
        path = self._path(volume_id)
        with open(path, "rb") as f:
            f.seek(offset)
            data = f.read(size)
        if len(data) != size:
            raise ValueError("Requested range is outside volume")
        return data

    def compact_volume(self, volume_id: int, live_objects: list[dict]) -> list[dict]:
        old_path = self._path(volume_id)
        compacted_path = self.volume_dir / f"volume_{volume_id}_compacted.dat"
        updates = []
        new_offset = 0
        with open(old_path, "rb") as src, open(compacted_path, "wb") as dst:
            for obj in live_objects:
                src.seek(int(obj["offset"]))
                data = src.read(int(obj["size"]))
                dst.write(data)
                updates.append({
                    "object_id": obj["object_id"],
                    "volume_id": volume_id,
                    "offset": new_offset,
                    "size": len(data),
                })
                new_offset += len(data)

        was_active = volume_id == self.volume_id

        if was_active and self.file:
            self.file.close()
            self.file = None

        old_path.unlink()
        compacted_path.rename(old_path)

        if was_active:
            self._open_active_volume()

        return updates
