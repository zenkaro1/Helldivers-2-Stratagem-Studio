"""Minimal persistent MCP client for VectorCraft (stdio, headless or attached)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

CLI = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "ArtCraft" / "VectorCraft" / "vectorcraft-cli.exe"


class Session:
    def __init__(self, headless: bool = True, attach_port: str | None = None):
        args = [str(CLI), "mcp"]
        if headless:
            args.append("--headless")
        elif attach_port:
            args += ["--connect", f"127.0.0.1:{attach_port}"]
        self.proc = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        self._id = 0
        self._send("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "dsh-vectorcraft", "version": "0.1"},
        })
        self._recv()

    def _send(self, method: str, params: dict | None = None) -> int:
        self._id += 1
        payload = {"jsonrpc": "2.0", "id": self._id, "method": method}
        if params is not None:
            payload["params"] = params
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()
        return self._id

    def _recv(self) -> dict:
        while True:
            line = self.proc.stdout.readline()
            if not line:
                err = self.proc.stderr.read() if self.proc.stderr else ""
                raise RuntimeError(f"VectorCraft MCP closed: {err[-2000:]}")
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if "id" in message:
                return message

    def request(self, method: str, params: dict | None = None) -> dict:
        self._send(method, params)
        return self._recv()

    def tools(self) -> list[dict]:
        return self.request("tools/list", {})["result"]["tools"]

    def call(self, name: str, arguments: dict | None = None) -> dict:
        response = self.request("tools/call", {"name": name, "arguments": arguments or {}})
        if "error" in response:
            raise RuntimeError(json.dumps(response["error"], ensure_ascii=False))
        result = response.get("result", {})
        texts = [b.get("text", "") for b in result.get("content", []) if b.get("type") == "text"]
        joined = "\n".join(texts)
        try:
            return json.loads(joined)
        except ValueError:
            return {"text": joined, "raw": result, "isError": result.get("isError")}

    def close(self) -> None:
        try:
            self.proc.stdin.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            self.proc.terminate()
        except Exception:  # noqa: BLE001
            pass


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    session = Session(headless=True)
    try:
        for tool in session.tools():
            print(tool["name"], "|", (tool.get("description") or "")[:110])
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
