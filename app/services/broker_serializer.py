import json
from typing import Any

import msgpack


class BrokerSerializer:
    @staticmethod
    def encode(data: dict[str, Any], fmt: str) -> str | bytes:
        if fmt == "msgpack":
            return msgpack.packb(data, use_bin_type=True)

        return json.dumps(data)

    @staticmethod
    def decode(data: str | bytes, fmt: str) -> dict[str, Any]:
        if fmt == "msgpack":
            if isinstance(data, str):
                data = data.encode("utf-8")

            return msgpack.unpackb(data, raw=False)

        if isinstance(data, bytes):
            data = data.decode("utf-8")

        return json.loads(data)