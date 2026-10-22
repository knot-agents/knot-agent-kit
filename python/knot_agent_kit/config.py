"""Shared Knot Agent Kit configuration."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping


def default_config_path(
    env: Mapping[str, str] | None = None,
    *,
    platform: str | None = None,
    home: Path | None = None,
) -> Path:
    values = os.environ if env is None else env
    if values.get("KNOT_CONFIG_FILE"):
        return Path(values["KNOT_CONFIG_FILE"]).expanduser().resolve()

    current_platform = os.name if platform is None else platform
    user_home = Path.home() if home is None else home
    if current_platform in {"nt", "win32"}:
        root = Path(values.get("APPDATA", user_home / "AppData" / "Roaming"))
        return root / "Knot" / "agent-kit.json"

    root = Path(values.get("XDG_CONFIG_HOME", user_home / ".config"))
    return root / "knot" / "agent-kit.json"


def read_config(path: Path | None = None) -> dict[str, Any]:
    file = default_config_path() if path is None else path
    try:
        value = json.loads(file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if not isinstance(value, dict):
        return {}
    return value


def write_config(config: Mapping[str, Any], path: Path | None = None) -> None:
    file = default_config_path() if path is None else path
    file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f"{file.name}.", suffix=".tmp", dir=file.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(config, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        if os.name != "nt":
            temporary.chmod(0o600)
        os.replace(temporary, file)
        if os.name != "nt":
            file.chmod(0o600)
    finally:
        temporary.unlink(missing_ok=True)


def resolved_settings(
    config: Mapping[str, Any] | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    saved = {} if config is None else config
    values = os.environ if env is None else env
    return {
        "base_url": str(
            values.get("KNOT_BASE_URL")
            or saved.get("baseUrl")
            or "https://knot.antisla.sh"
        ).rstrip("/"),
        "token": values.get("KNOT_AGENT_TOKEN") or saved.get("token"),
        "checkpoint": saved.get("checkpoint"),
        "agent": saved.get("agent"),
    }
