import pytest
from src.models import Snippet
from datetime import datetime
 def test_snippet_creation():
    snippet = Snippet(name="test", language="python", content="print('hi')"
content="print('hi')")
    assert snippet.name == "test"
    assert snippet.tags == []
    assert snippet.id is None
 def test_snippet_to_dict():
    snippet = Snippet(id=1, name="test", language="python", content="code", content="code", tags=["a", "b"])
    d = snippet.to_dict()
    assert d["name"] == "test"
    assert d["tags"] == ["a", "b"]
    assert d["created_at"] is None
 def test_snippet_with_timestamps():
    now = datetime.now()
    snippet = Snippet(id=2, name="ts_test", language="js", content="console content="console.log()", created_at=now, updated_at=now)
    assert snippet.created_at == now
    assert snippet.updated_at == now
    assert snippet.to_dict()["created_at"] == now.isoformat()