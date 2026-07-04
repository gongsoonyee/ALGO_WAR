from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

VALID_MOVES = {"UP", "DOWN", "LEFT", "RIGHT"}
SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "pow": pow,
    "range": range,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}


class LocalAgentRuntime:
    def __init__(self, code: str):
        self.error: str | None = None
        self.agent: Any = None
        self.next_move = None
        namespace = {"__builtins__": SAFE_BUILTINS}
        try:
            exec(code, namespace, namespace)
            if "Agent" in namespace:
                self.agent = namespace["Agent"]()
                self.next_move = self.agent.next_move
            elif "next_move" in namespace:
                self.next_move = namespace["next_move"]
            else:
                self.error = "missing next_move"
        except Exception as exc:
            self.error = str(exc)

    def move(self, state: dict[str, Any]) -> str:
        if self.next_move is None:
            return "UP"
        try:
            move = str(self.next_move(state)).upper()
        except Exception:
            return "UP"
        return move if move in VALID_MOVES else "UP"


RUNNER_TEMPLATE = r'''
import json
import sys

USER_CODE = {code!r}
STATE = json.loads({state!r})

namespace = {{"__builtins__": {{
    "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
    "enumerate": enumerate, "float": float, "int": int, "len": len,
    "list": list, "max": max, "min": min, "pow": pow, "range": range,
    "round": round, "set": set, "sorted": sorted, "str": str, "sum": sum,
    "tuple": tuple, "zip": zip,
}}}}

try:
    exec(USER_CODE, namespace, namespace)
    if "Agent" in namespace:
        agent = namespace["Agent"]()
        move = agent.next_move(STATE)
    elif "next_move" in namespace:
        move = namespace["next_move"](STATE)
    else:
        move = "UP"
    print(json.dumps({{"move": str(move).upper()}}))
except Exception as exc:
    print(json.dumps({{"move": "UP", "error": str(exc)}}))
'''


def get_move(code: str, state: dict[str, Any], timeout: float = 0.25) -> tuple[str, str | None, float]:
    script = RUNNER_TEMPLATE.format(code=code, state=json.dumps(state, ensure_ascii=False))
    with tempfile.TemporaryDirectory() as tmp:
        runner = Path(tmp) / "runner.py"
        runner.write_text(script, encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, str(runner)],
                text=True,
                capture_output=True,
                timeout=timeout,
                cwd=tmp,
            )
        except subprocess.TimeoutExpired:
            return "UP", "timeout", timeout

    elapsed = 0.0
    raw = proc.stdout.strip() or "{}"
    try:
        payload = json.loads(raw.splitlines()[-1])
    except json.JSONDecodeError:
        return "UP", "invalid output", elapsed

    move = str(payload.get("move", "UP")).upper()
    if move not in VALID_MOVES:
        move = "UP"
    return move, payload.get("error"), elapsed
