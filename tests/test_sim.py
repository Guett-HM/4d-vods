"""Fast sanity tests for the simulator (run with: pytest -q tests)."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sim"))

import samm_sim as S  # noqa: E402
import vods_sim as V  # noqa: E402


def test_split_byte_covers_all_states():
    seen = {V.split_byte(b) for b in range(256)}
    assert len(seen) == 256
    assert V.split_byte(0b01000011) == (0b010, 0b00, 0b01, 1)   # 'C' from the original concept notes


def test_pupil_is_band_limited_at_na_over_lambda():
    opt = V.Optics(0.5, 1)
    f = np.fft.fftfreq(opt.N, d=opt.dx)
    FX, FY = np.meshgrid(f, f)
    fr = np.hypot(FX, FY)
    assert not np.any(opt.pupil & (fr > V.NA / V.LAM + 1e-9))
    assert np.all(opt.pupil[fr < 0.99 * V.NA / V.LAM])


def test_image_spectrum_has_no_energy_beyond_cutoff():
    opt = V.Optics(0.5, 3)
    delta = np.zeros((opt.N, opt.N), complex)
    delta[opt.N // 2, opt.N // 2] = 1.0
    E = np.fft.ifft2(np.fft.fft2(delta) * opt.pupil)
    spec = np.abs(np.fft.fft2(E))
    assert spec[~opt.pupil].max() < 1e-9 * spec.max()


def test_mutual_information_of_perfect_channel():
    x = np.repeat(np.arange(8), 100)
    assert abs(V.mutual_info(x, x, 8) - 3.0) < 1e-9
    rng = np.random.default_rng(0)
    y = rng.integers(0, 8, x.size)
    assert V.mutual_info(x, y, 8) < 0.2


def test_on_media_rle_symbol_count():
    assert V.rle_symbols(bytes(4096)) == 13          # 1 symbol + 12 doubling glyphs
    assert V.rle_symbols(b"abc") == 3
    assert V.rle_symbols(b"aaaaa") == 4              # 4 = [a]+2 glyphs, 1 = [a]


def test_gray_code_adjacent_levels_differ_by_one_bit():
    gray = [n ^ (n >> 1) for n in range(8)]
    for a, b in zip(gray, gray[1:] + gray[:1]):
        assert bin(a ^ b).count("1") == 1


def test_wedge_lattice_is_error_free_at_large_pitch():
    t, e = V.run_lattice(0.8, 640_000, trials=3, seed=1)
    assert np.all(t == e)


def test_samm_frame_decodes_at_unknown_rotation():
    rng = np.random.default_rng(11)
    na = 0.45
    rd = S.Reader(na, round(1.4 * S.LAM / na, 3))
    for _ in range(3):
        x, y, ok, err = S.trial(rd, rng)
        assert ok and err < 0.5
        assert np.mean(x != y) < 0.01


def test_samm_frame_layout_counts():
    assert int(np.sum(S.ROLE == 2)) == 36
    assert int(np.sum(S.ROLE == 1)) == 32
    assert int(np.sum(S.ROLE == 0)) == 508


def test_wilson_interval():
    lo, hi = S.wilson(120, 120)
    assert 0.96 < lo < 0.975 and hi == 1.0
    lo, hi = S.wilson(0, 10)
    assert lo == 0.0 and 0.25 < hi < 0.35
