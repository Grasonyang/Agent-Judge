from __future__ import annotations
import json
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Iterable, List, Optional
from ._record_utils import append_ndjson, read_ndjson


class StateRecorder:
    """Simple append-only newline-delimited JSON recorder for state/events.

    Each record is a JSON object written on its own line to allow streaming
    append and easy recovery. The recorder is thread-safe for append.

    Usage:
        r = StateRecorder("state_record.ndjson")
        r.record({"event": "turn", ...})
        r.flush()
        r.load() -> list of dicts
    """

    def __init__(self, path: str, ensure_dir: bool = True):
        self.path = Path(path)
        if ensure_dir:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        # file handle is opened lazily on first write

    def record(self, obj: Dict[str, Any]) -> None:
        """Append a single JSON record atomically (per-line)."""
        with self._lock:
            append_ndjson(str(self.path), obj)

    def record_many(self, objs: Iterable[Dict[str, Any]]) -> None:
        with self._lock:
            for obj in objs:
                append_ndjson(str(self.path), obj)

    def load(self) -> List[Dict[str, Any]]:
        """Load all records from ndjson file."""
        return read_ndjson(str(self.path))

    def flush(self) -> None:
        # nothing to do since we open/close per write
        return None


def initialize_state_record(path: str, state: Optional[dict] = None, reset: bool = True) -> StateRecorder:
    """Create and optionally reset a recorder file. Records path into state if provided."""
    rec = StateRecorder(path)
    p = rec.path
    if reset and p.exists():
        p.unlink()
    if state is not None:
        state.setdefault("state_record_path", str(p))
    return rec


def load_state_records(path: str) -> List[Dict[str, Any]]:
    rec = StateRecorder(path)
    return rec.load()


def record_agent_event(state: Optional[dict], agent: str, record: Dict[str, Any], sr_path: Optional[str] = None) -> None:
    """Helper to record an agent-scoped record both to the ndjson file and into
    in-memory state under state['agents'][agent]['log'].

    - state: the runtime state dict (may be None when only file path is provided)
    - agent: agent name string
    - record: a dict representing the event (should include at least a 'type' key)
    - sr_path: optional path to state_record file; if omitted, will read from state['state_record_path']
    """
    # determine path
    path = sr_path if sr_path is not None else (state.get("state_record_path") if isinstance(state, dict) else None)
    if path:
        try:
            rec = StateRecorder(path)
            # attach some minimal metadata
            rec.record({"agent": agent, **record})
        except Exception:
            # tolerate recorder failure
            pass

    # write into in-memory state for quick access
    if isinstance(state, dict):
        try:
            agents = state.setdefault("agents", {})
            agent_log = agents.setdefault(agent, {}).setdefault("log", [])
            agent_log.append(record)
        except Exception:
            pass
