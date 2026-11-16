"""Every result file is listed in results/MANIFEST.json with an unchanged hash."""
import json
import os

from vods import RESULTS, cli, provenance


def test_every_result_has_unchanged_provenance():
    assert provenance.verify(RESULTS) == []


def test_manifest_entries_are_complete():
    files = provenance.load(RESULTS)["files"]
    assert files, "empty manifest"
    for name, entry in files.items():
        for key in ("sha256", "command", "parameters", "commit", "environment"):
            assert key in entry, f"{name}: missing {key}"


def test_configs_parse_and_match_cli_options(tmp_path):
    import tomllib
    cfg_dir = os.path.join(os.path.dirname(RESULTS), "configs")
    for fn in sorted(os.listdir(cfg_dir)):
        with open(os.path.join(cfg_dir, fn), "rb") as f:
            cfg = tomllib.load(f)
        allowed = {"experiment", "pitches", "trials", "quick", "na", "sensitivity", "tag"}
        assert set(cfg) <= allowed, f"{fn}: unknown keys {set(cfg) - allowed}"


def test_cli_parser_and_config_merge(tmp_path):
    cfg = tmp_path / "c.toml"
    cfg.write_text('trials = 50\nna = [0.25]\n')
    args = cli.build_parser().parse_args(["run", "samm", "--config", str(cfg), "--trials", "7"])
    params = cli._merge(args, ("trials", "na", "sensitivity", "tag", "quick"))
    assert params == {"trials": 7, "na": [0.25]}       # command line wins over the file


def test_summary_json_is_valid():
    with open(os.path.join(RESULTS, "summary.json")) as f:
        s = json.load(f)
    assert "rows" in s and len(s["rows"]) == 8
