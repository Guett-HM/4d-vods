"""Fixed seeds must give the stored reference values (see tests/regression_cases.py)."""
import json
import math

import pytest
from regression_cases import REFERENCE, compute

with open(REFERENCE) as f:
    EXPECTED = json.load(f)


@pytest.fixture(scope="module")
def actual():
    return compute()


@pytest.mark.parametrize("key", sorted(EXPECTED))
def test_regression_value(actual, key):
    exp, got = EXPECTED[key], actual[key]
    if isinstance(exp, float):
        assert math.isclose(got, exp, rel_tol=1e-5, abs_tol=1e-7), f"{key}: {got} != {exp}"
    else:
        assert got == exp, f"{key}: {got} != {exp}"
