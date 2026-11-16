"""Properties the physics and the decoders must have, whatever the exact numbers."""
import math

import numpy as np
import pytest

import samm_sim as S
import vods_sim as V


def _samm_frame(rd, theta, mirror=False, noise=0.02, seed=0):
    rng = np.random.default_rng(seed)
    levels = rng.integers(0, 4, (S.N, S.N))
    levels[S.ROLE == 1] = S.PILOT[S.ROLE == 1]
    R = rd.render(levels, (theta, 1.0, 0.0, 0.0), np.zeros((S.N, S.N)))
    img = rd.image(R, 1.0) + rng.normal(0, noise, (rd.nc, rd.nc))
    if mirror:                      # frame read from the back of the glass
        img = img[:, ::-1]
    est, _ = rd.decode(img)
    data = S.ROLE == 0
    return 1.0 if est is None else float(np.mean(est[data] != levels[data]))


@pytest.fixture(scope="module")
def reader():
    return S.Reader(0.45, round(1.4 * S.LAM / 0.45, 3))


@pytest.mark.parametrize("deg", [0, 90, 180, 270, 37])
@pytest.mark.parametrize("mirror", [False, True], ids=["front", "mirrored"])
def test_samm_decodes_any_orientation(reader, deg, mirror):
    assert _samm_frame(reader, math.radians(deg), mirror) == 0.0


def test_samm_errors_grow_with_camera_noise():
    rd = S.Reader(0.45, round(0.9 * S.LAM / 0.45, 3))
    ser = [np.mean([_samm_frame(rd, 0.3 + i, noise=nz, seed=i) for i in range(4)]) for nz in (0.01, 0.04, 0.08)]
    assert ser[0] <= ser[1] < ser[2]


def test_data_layer_errors_grow_as_pitch_shrinks():
    ser = []
    for p in (0.8, 0.5, 0.2):
        t, e = V.run_lattice(p, 64_000, trials=12, seed=5)
        ser.append(np.mean(t != e))
    assert ser[0] <= ser[1] < ser[2]


def test_same_seed_same_result():
    a = V.run_lattice(0.5, 64_000, trials=3, seed=9)
    b = V.run_lattice(0.5, 64_000, trials=3, seed=9)
    assert all(np.array_equal(x, y) for x, y in zip(a, b))


def test_gray_coded_samm_levels_cost_one_bit_per_adjacent_error():
    gray = [n ^ (n >> 1) for n in range(4)]
    assert all(bin(gray[i] ^ gray[i + 1]).count("1") == 1 for i in range(3))
