from myagent.sensitivity import Sensitivity, assess


def test_public():
    assert assess("Explain a Python loop").level == Sensitivity.PUBLIC


def test_internal():
    assert assess("Review this proprietary repository").route == "local_preferred"


def test_secret():
    assessment = assess("api_key=sk-123456789012345678")
    assert assessment.level == Sensitivity.SECRET
    assert "[REDACTED]" in assessment.redacted_text
