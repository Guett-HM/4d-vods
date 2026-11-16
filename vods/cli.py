"""Single entry point:  python -m vods <command> [options]

  run datalayer   data-layer study (sim/vods_sim.py)
  run samm        SAMM study (sim/samm_sim.py)
  figures         rebuild figures/ and results/summary.json
  validate        physics validation checks -> docs/VALIDATION.md
  check           every published number vs results/ and the documents
  manifest        verify the provenance of results/ (hashes, commands, versions)

Options can also come from a TOML file (--config configs/samm.toml); options given on the
command line win. Every run records what it wrote in results/MANIFEST.json.
"""
import argparse
import os
import subprocess
import sys
import tomllib

from . import RESULTS, RESULTS_QUICK, ROOT, SIM, __version__, provenance

DATALAYER_EXPERIMENTS = ("all", "lattice", "extra", "sensitivity", "spread", "rle", "skew")


def _floats(text):
    return [float(v) for v in str(text).split(",") if v.strip()]


def _merge(args, keys):
    """Command-line values override the TOML config; returns the resolved parameters."""
    params = {}
    if args.config:
        with open(args.config, "rb") as f:
            params.update(tomllib.load(f))
    for k in keys:
        v = getattr(args, k, None)
        if v not in (None, False):
            params[k] = v
    return params


def _run_script(script, argv, env_extra, folder, command, params):
    env = dict(os.environ, **{k: str(v) for k, v in env_extra.items()})
    os.makedirs(folder, exist_ok=True)
    before = provenance.snapshot(folder)
    cmd = [sys.executable, os.path.join(SIM, script), *argv]
    print("$", " ".join(f"{k}={v}" for k, v in env_extra.items()), "python", f"sim/{script}", *argv, flush=True)
    rc = subprocess.run(cmd, env=env, cwd=ROOT).returncode
    if rc == 0:
        written = provenance.record(folder, before, command, params)
        print(f"provenance recorded for {len(written)} file(s) in {os.path.relpath(folder, ROOT)}/MANIFEST.json")
    return rc


def cmd_run_datalayer(args):
    p = _merge(args, ("experiment", "pitches", "trials", "quick"))
    exp = p.get("experiment", "all")
    if exp not in DATALAYER_EXPERIMENTS:
        raise SystemExit(f"unknown experiment {exp!r}; choose from {', '.join(DATALAYER_EXPERIMENTS)}")
    which = exp
    if p.get("pitches") and exp in ("lattice", "extra"):
        which = f"{exp}:{','.join(str(x) for x in _floats(p['pitches']))}"
    env = {}
    if p.get("quick"):
        env["QUICK"] = "1"
    if p.get("trials"):
        env["TRIALS"] = int(p["trials"])
    folder = RESULTS_QUICK if p.get("quick") else RESULTS
    return _run_script("vods_sim.py", [which], env, folder, "python -m vods run datalayer", p)


def cmd_run_samm(args):
    p = _merge(args, ("trials", "na", "sensitivity", "tag", "quick"))
    env = {}
    if p.get("quick"):
        env["QUICK"] = "1"
    if p.get("sensitivity"):
        env["SENS"] = "1"
    if p.get("trials"):
        env["TRIALS"] = int(p["trials"])
    if p.get("na"):
        na = p["na"] if isinstance(p["na"], list) else _floats(p["na"])
        env["NAS"] = ",".join(str(x) for x in na)
    if p.get("tag"):
        env["TAG"] = p["tag"]
    folder = RESULTS_QUICK if p.get("quick") else RESULTS
    return _run_script("samm_sim.py", [], env, folder, "python -m vods run samm", p)


def cmd_figures(args):
    rc = 0
    for script in ("make_figures.py", "make_illustrations.py"):
        before = provenance.snapshot(RESULTS)
        print("$ python", f"sim/{script}", flush=True)
        rc |= subprocess.run([sys.executable, os.path.join(SIM, script)], cwd=ROOT).returncode
        provenance.record(RESULTS, before, "python -m vods figures", {"script": script})
    return rc


def cmd_validate(args):
    from . import validation
    results = validation.run_all()
    for r in results:
        print(("PASS " if r["passed"] else "FAIL ") + r["name"] + ": " + r["measured_text"])
    if args.report:
        validation.write_report(results, args.report)
        print("report written to", os.path.relpath(args.report, ROOT))
    return 0 if all(r["passed"] for r in results) else 1


def cmd_check(args):
    from . import claims
    problems, n = claims.check()
    for msg in problems:
        print("MISMATCH", msg)
    print(f"{n - len(problems)}/{n} published numbers agree with results/ and the documents")
    return 1 if problems else 0


def cmd_manifest(args):
    problems = provenance.verify(RESULTS)
    for msg in problems:
        print("PROBLEM", msg)
    n = len(provenance.load(RESULTS)["files"])
    print(f"{n} result files listed; {len(problems)} problem(s)")
    return 1 if problems else 0


def build_parser():
    ap = argparse.ArgumentParser(prog="python -m vods", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=f"4D-VODS {__version__}")
    sub = ap.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run a simulation study")
    rsub = run.add_subparsers(dest="study", required=True)
    d = rsub.add_parser("datalayer", help="data-layer study (sim/vods_sim.py)")
    d.add_argument("--experiment", choices=DATALAYER_EXPERIMENTS)
    d.add_argument("--pitches", help="comma-separated pitches in um, for lattice/extra")
    d.add_argument("--trials", type=int, help="trials per point (default 2000, quick 60)")
    d.add_argument("--quick", action="store_true", help="smoke run into results_quick/")
    d.add_argument("--config", help="TOML file with any of the options above")
    d.set_defaults(func=cmd_run_datalayer)
    s = rsub.add_parser("samm", help="SAMM study (sim/samm_sim.py)")
    s.add_argument("--trials", type=int, help="frames per point (default 200, quick 8)")
    s.add_argument("--na", help="comma-separated reader NAs, e.g. 0.25,0.45")
    s.add_argument("--sensitivity", action="store_true", help="noise / writing-variability study")
    s.add_argument("--tag", help="suffix for the output file name")
    s.add_argument("--quick", action="store_true", help="smoke run into results_quick/")
    s.add_argument("--config", help="TOML file with any of the options above")
    s.set_defaults(func=cmd_run_samm)

    sub.add_parser("figures", help="rebuild figures and results/summary.json").set_defaults(func=cmd_figures)
    v = sub.add_parser("validate", help="physics validation checks")
    v.add_argument("--report", nargs="?", const=os.path.join(ROOT, "docs", "VALIDATION.md"),
                   help="write a Markdown report (default docs/VALIDATION.md)")
    v.set_defaults(func=cmd_validate)
    sub.add_parser("check", help="published numbers vs results and documents").set_defaults(func=cmd_check)
    sub.add_parser("manifest", help="verify result provenance").set_defaults(func=cmd_manifest)
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)
