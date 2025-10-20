"""Judge package init

To align with ADK CLI expectations (which access ``package.agent.root_agent``),
expose the ``agent`` submodule as an attribute while avoiding eager imports
of agent objects at top-level.
"""

from importlib import import_module as _import_module

# Expose submodule so `judge.agent` is accessible as an attribute of the package
try:
    agent = _import_module(__name__ + ".agent")
except Exception:  # During some tooling imports, the agent module may not load
    agent = None

# Keep a placeholder for compatibility; actual root_agent lives in judge.agent
root_agent = None

__all__ = ["agent", "root_agent"]
