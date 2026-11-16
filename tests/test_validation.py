"""Physics validation: the simulator against closed-form results and independent libraries.
The same checks produce docs/VALIDATION.md (python -m vods validate --report)."""
import pytest

from vods import validation


@pytest.mark.parametrize("check", validation.CHECKS, ids=lambda c: c.__name__)
def test_validation_check(check):
    r = check()
    assert r["passed"], f"{r['title']}: {r['measured_text']} (limit {r['limit_text']})"
