import pytest
import os import tempfile
from src.database import SnippetDB
from src.models import Snippet
 @pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        path = f.name
    db = SnippetDB(path)
    yield db
    db.close()
    os.unlink(path)
 def test_add_and_get(temp_db: SnippetDB):
    snippet = Snippet(name="hello", language="bash", content="echo hi", tag
tags=["test"])
    added = temp_db.add(snippet)
    assert added.id is not None
    fetched = temp_db.get(added.id)
    assert fetched is not None
    assert fetched.name == "hello"
    assert fetched.tags == ["test"]
 def test_search(temp_db: SnippetDB):
    temp_db.add(Snippet(name="py_script", language="python", content="x=1", content="x=1", tags=["py"]))
    temp_db.add(Snippet(name="js_script", language="javascript", content="v content="var x=1", tags=["js"]))
    results = temp_db.search("py")
    assert len(results) >= 1
    assert results[0].name == "py_script"
 def test_update_and_delete(temp_db: SnippetDB):
    added = temp_db.add(Snippet(name="old", language="c", content="int x;", x;", tags=[]))
    added.name = "new"
    updated = temp_db.update(added)
    assert updated.name == "new"
    assert temp_db.delete(added.id)
    assert temp_db.get(added.id) is None
 def test_list_all(temp_db: SnippetDB):
    assert temp_db.list_all() == []
    temp_db.add(Snippet(name="a", language="py", content="a"))
    temp_db.add(Snippet(name="b", language="js", content="b"))
    assert len(temp_db.list_all()) == 2