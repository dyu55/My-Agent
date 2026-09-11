from myagent.sensitivity import Sensitivity, assess
def test_public(): assert assess('Explain a Python loop').level == Sensitivity.PUBLIC
def test_internal(): assert assess('Review this proprietary repository').route == 'local_preferred'
def test_secret():
 a=assess('api_key=sk-123456789012345678'); assert a.level==Sensitivity.SECRET and '[REDACTED]' in a.redacted_text
