from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def block_real_model_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    def guarded(original):
        def invoke(*args, **kwargs):
            command = args[0] if args else kwargs.get("args", ())
            parts = shlex.split(command) if isinstance(command, str) else command
            executable = kwargs.get("executable") or (parts[0] if parts else "")
            if Path(executable).name in {"agy", "codex"}:
                raise AssertionError(f"未攔截的真實模型指令：{executable}")
            return original(*args, **kwargs)

        return invoke

    monkeypatch.setattr(subprocess, "Popen", guarded(subprocess.Popen))
    monkeypatch.setattr(subprocess, "run", guarded(subprocess.run))
