"""Every number quoted in the README, the project page and the documents matches the results."""
import pytest

from vods import claims


def test_published_numbers_match_results_and_texts():
    problems, n = claims.check()
    assert n > 30
    assert problems == [], "\n".join(problems)


def test_every_quoted_claim_is_cited_somewhere():
    for c in claims.load()["claims"]:
        if c["snippets"]:
            assert c["cited_in"], f"{c['id']} has snippets but no citing file"


@pytest.mark.parametrize("claim_id", ["apsk16_density_300nm", "samm_density_045"])
def test_check_detects_a_changed_result(monkeypatch, claim_id):
    real = claims.values

    def shifted(registry=None):
        v = real(registry)
        v[claim_id] *= 1.05            # pretend a rerun moved this number by 5%
        return v

    monkeypatch.setattr(claims, "values", shifted)
    problems, _ = claims.check()
    assert any(p.startswith(claim_id) for p in problems)
