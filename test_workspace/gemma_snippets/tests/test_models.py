from src.models import Snippet

def test_snippet_creation():
    s = Snippet(name="Test", language="py", content="print(1)", description="desc", tags=["t1"])
    assert s.name == "Test"
    assert s.tags == ["t1"]
    assert s.id is None