"""A run's own settings for the pipeline's tools (``spec.tools``).

A profile is a named set of settings that ships with specimux-suite. A lab
that has run the tools by hand for years has its own numbers for a few of
their options, and wants a run on the service to use them. ``spec.tools``
carries those: by tool, then by the tool's own long option without the
dashes, the way a suite profile's ``specimux:``, ``speconsense:`` and
``summarize:`` sections name them.

    {"specimux": {"index-edit-distance": 3},
     "speconsense": {"presample": 500},
     "summarize": {"merge-position-count": 5, "min-len": 150, "fasta-fields": "ric,snp"}}

Only the options listed here are taken, each with its own type and limits:
the values end up on a command line, on a machine the service pays for.
The engine passes each one to specimux-suite as ``--set tool.option=value``,
which applies it over the run's profile.
"""

import re
from typing import Any

TOOL_SETTINGS: dict[str, dict[str, dict[str, Any]]] = {
    "specimux": {
        # -e: edits a read's barcode may be from the sheet's and still match.
        # Left out, specimux takes half the distance between the sheet's two
        # closest barcodes, so the tolerance moves with the sheet.
        "index-edit-distance": {"type": "int", "min": 0, "max": 10},
    },
    "speconsense": {
        # reads sampled per specimen before clustering (0: all of them)
        "presample": {"type": "int", "min": 0, "max": 100_000},
    },
    "summarize": {
        "merge-position-count": {"type": "int", "min": 0, "max": 50},
        "min-merge-overlap": {"type": "int", "min": 0, "max": 5000},
        "merge-min-size-ratio": {"type": "number", "min": 0, "max": 1},
        "min-len": {"type": "int", "min": 0, "max": 100_000},
        "min-ric": {"type": "int", "min": 1, "max": 10_000},
        "select-max-variants": {"type": "int", "min": -1, "max": 1000},
        # a preset (default, minimal, qc, full, id-only) or field names
        "fasta-fields": {"type": "text", "pattern": "[A-Za-z0-9_.,-]{1,200}"},
    },
}


def suite_takes_tool_settings() -> bool:
    """Whether the installed specimux-suite has ``--set``."""
    try:
        from specimux_suite.config import parse_tool_settings  # noqa: F401
    except ImportError:
        return False
    return True


def _check_value(name: str, rule: dict, value: Any) -> Any:
    kind = rule["type"]
    if kind == "text":
        if not isinstance(value, str) or not re.fullmatch(rule["pattern"], value):
            raise ValueError(f"{name} may hold letters, digits, commas, dots, dashes and underscores")
        return value
    whole = kind == "int"
    ok = isinstance(value, int) if whole else isinstance(value, (int, float))
    if isinstance(value, bool) or not ok or not rule["min"] <= value <= rule["max"]:
        raise ValueError(f"{name} must be a {'whole number' if whole else 'number'} "
                         f"from {rule['min']} to {rule['max']}")
    return value


def check_tool_settings(tools: Any) -> dict[str, dict[str, Any]]:
    """``spec.tools`` checked: the settings a run will carry. An option
    given as null is not set. Raises ValueError saying what is wrong."""
    if not isinstance(tools, dict):
        raise ValueError(f"tools must be an object with {', '.join(TOOL_SETTINGS)} settings")
    out: dict[str, dict[str, Any]] = {}
    for tool, settings in tools.items():
        if tool not in TOOL_SETTINGS:
            raise ValueError(f"tools: unknown tool {tool!r}; choose from {', '.join(TOOL_SETTINGS)}")
        if not isinstance(settings, dict):
            raise ValueError(f"tools.{tool} must be an object of option: value")
        unknown = sorted(set(settings) - set(TOOL_SETTINGS[tool]))
        if unknown:
            raise ValueError(f"tools.{tool}: unknown settings: {', '.join(unknown)}; "
                             f"the service takes {', '.join(TOOL_SETTINGS[tool])}")
        kept = {option: _check_value(f"tools.{tool}.{option}", TOOL_SETTINGS[tool][option], value)
                for option, value in settings.items() if value is not None}
        if kept:
            out[tool] = kept
    return out


def parse_tool_pairs(items: list[str]) -> dict[str, dict[str, Any]]:
    """``tool.option=value`` items, as typed on a command line or in the
    console's form, as checked ``spec.tools``. Raises ValueError."""
    tools: dict[str, dict[str, Any]] = {}
    for item in items:
        target, sep, value = item.partition("=")
        tool, dot, option = target.strip().partition(".")
        option, value = option.strip().lstrip("-"), value.strip()
        if not sep or not dot or not option or not value:
            raise ValueError(f"A tool setting is tool.option=value, e.g. summarize.min-len=150 (got {item!r})")
        rule = TOOL_SETTINGS.get(tool, {}).get(option)
        if rule is None:
            raise ValueError(f"Unknown tool setting {tool}.{option}; the service takes "
                             + ", ".join(f"{t}.{o}" for t, options in TOOL_SETTINGS.items() for o in options))
        if rule["type"] != "text":
            try:
                value = int(value) if rule["type"] == "int" else float(value)
            except ValueError:
                raise ValueError(f"{tool}.{option} must be a number (got {value!r})") from None
        tools.setdefault(tool, {})[option] = value
    return check_tool_settings(tools)


def tool_pairs(tools: dict) -> list[str]:
    """Checked ``spec.tools`` as ``tool.option=value`` items."""
    return [f"{tool}.{option}={value}" for tool, settings in (tools or {}).items()
            for option, value in settings.items()]
