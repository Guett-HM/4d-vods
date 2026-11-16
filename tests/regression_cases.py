"""Fixed-seed reference values for tests/test_regression.py.

The simulator must give the same answers tomorrow as today: any change in these numbers
means the physics or the random streams changed, and the published results would no longer
reproduce. After an intentional change, regenerate the reference with
    python tests/regression_cases.py
and explain the change in CHANGELOG.md.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "sim"))

import samm_sim as S  # noqa: E402
import vods_sim as V  # noqa: E402

REFERENCE = os.path.join(HERE, "data", "regression.json")


def compute():
    out = {}
    t, e = V.run_lattice(0.5, 64_000, trials=10, seed=123)
    out["wedge_p500_errors"] = int(np.sum(t != e))
    out["wedge_p500_symbol_sum"] = int(np.sum(t))
    t, e = V.run_lattice(0.3, 64_000, trials=10, seed=123, G=V.build_templates(0.3, "apsk16"), fab_jitter=0.1)
    out["apsk16_p300_errors"] = int(np.sum(t != e))
    G = V.build_templates(0.3, "apsk16")
    out["apsk16_template_energy"] = float(np.sum(np.abs(G.astype(np.complex128)) ** 2))
    c = G.shape[1] // 2
    out["apsk16_template_centre_re"] = float(G[5, c, c].real)
    out["apsk16_template_centre_im"] = float(G[5, c, c].imag)
    rng = np.random.default_rng(7)
    rd = S.Reader(0.45, round(1.1 * S.LAM / 0.45, 3))
    x, y, ok, err = S.trial(rd, rng)
    out["samm_trial_errors"] = int(np.sum(x != y))
    out["samm_trial_aligned"] = bool(ok)
    out["samm_trial_max_cell_error"] = float(err)
    out["samm_trial_level_sum"] = int(np.sum(x))
    out["rle_symbols_text"] = V.rle_symbols(b"4D-VODS " * 64 + bytes(512))
    return out


if __name__ == "__main__":
    os.makedirs(os.path.dirname(REFERENCE), exist_ok=True)
    with open(REFERENCE, "w") as f:
        json.dump(compute(), f, indent=1)
        f.write("\n")
    print("reference written to", REFERENCE)
