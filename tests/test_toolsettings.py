"""A run's own tool settings (spec.tools): what is taken and what is refused."""

import pytest

from specimux_cloud.toolsettings import TOOL_SETTINGS, check_tool_settings, parse_tool_pairs, tool_pairs

LAB = {"specimux": {"index-edit-distance": 3},
       "speconsense": {"presample": 500},
       "summarize": {"merge-position-count": 5, "min-merge-overlap": 100, "merge-min-size-ratio": 0.05,
                     "min-len": 150, "min-ric": 3, "select-max-variants": -1, "fasta-fields": "ric,snp"}}


def test_a_labs_own_settings_are_taken_as_given():
    assert check_tool_settings(LAB) == LAB
    # every option the service lists has a setting here, so the list and the test move together
    assert {t: set(o) for t, o in TOOL_SETTINGS.items()} == {t: set(o) for t, o in LAB.items()}
    # an option given as null is not set, and a tool left with none is left out
    assert check_tool_settings({"summarize": {"min-len": None}, "speconsense": {"presample": 0}}) == {
        "speconsense": {"presample": 0}}
    assert check_tool_settings({}) == {}


@pytest.mark.parametrize("bad, says", [
    ("summarize.min-len=150", "tools must be an object"),
    ({"identify": {"vsearch-min-identity": 0.9}}, "unknown tool 'identify'"),
    ({"summarize": ["min-len"]}, "tools.summarize must be an object"),
    ({"summarize": {"output-dir": "/tmp/x"}}, "unknown settings: output-dir"),
    ({"speconsense": {"primers": "/etc/passwd"}}, "unknown settings: primers"),
    ({"specimux": {"index-edit-distance": 11}}, "whole number from 0 to 10"),
    ({"specimux": {"index-edit-distance": "3"}}, "whole number from 0 to 10"),
    ({"specimux": {"index-edit-distance": True}}, "whole number from 0 to 10"),
    ({"speconsense": {"presample": 2.5}}, "whole number from 0 to 100000"),
    ({"summarize": {"merge-min-size-ratio": 1.5}}, "number from 0 to 1"),
    ({"summarize": {"select-max-variants": -2}}, "whole number from -1 to 1000"),
    ({"summarize": {"fasta-fields": "ric; rm -rf /"}}, "letters, digits, commas"),
    ({"summarize": {"fasta-fields": "--source"}}, None),   # dashes are letters of a field list: harmless as a value
])
def test_anything_else_is_refused_and_says_why(bad, says):
    if says is None:
        assert check_tool_settings(bad) == bad
        return
    with pytest.raises(ValueError, match=says):
        check_tool_settings(bad)


def test_settings_typed_as_text_come_out_typed():
    pairs = ["specimux.index-edit-distance=3", "speconsense.presample=500", "summarize.merge-position-count=5",
             "summarize.min-merge-overlap=100", "summarize.merge-min-size-ratio=0.05", "summarize.min-len=150",
             "summarize.min-ric=3", "summarize.select-max-variants=-1", "summarize.fasta-fields=ric,snp"]
    assert parse_tool_pairs(pairs) == LAB
    assert tool_pairs(LAB) == pairs
    assert parse_tool_pairs([]) == {} and tool_pairs({}) == []
    # the tool's own spelling with dashes is fine; the later of two wins
    assert parse_tool_pairs(["summarize.--min-len=150", "summarize.min-len=200"]) == {"summarize": {"min-len": 200}}
    for bad in ("min-len=150", "summarize.min-len", "summarize.min-len=", "summarize.min-len=long",
                "summarize.no-such=1", "summarize.min-len=-5"):
        with pytest.raises(ValueError):
            parse_tool_pairs([bad])
