import pytest
import os
from src.database import Database
from src.models import Snippet

@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test.db"
    db = Database(str(db_file))
    return db

def test_add_and_get_snippet(temp_db):
    s = Snippet(name="Test", language="python", content="print(1)", description="desc", tags=["a", "b"])
    sid = temp_db.add_snippet(s)
    
    retrieved = temp_db.get_snippet(sid)
    assert retrieved is not None
    assert retrieved.name == "Test"
    assert retrieved.tags == ["a", "b"]

def test_update_snippet(temp_db):
    s = Snippet(name="Old", language="py", content="old", description="desc", tags=[])
    sid = temp_db.add_snippet(s)
    
    temp_db.update_snippet(sid, {"name": "New"})
    updated = temp_db.get_snippet(sid)
    assert updated.name == "New"

def test_delete_snippet(temp_db):
    s = Snippet(name="Del", language="py", content="del", description="desc", tags=[])
    sid = temp_db.add_snippet(s)
    
    assert temp_db.delete_snippet(sid) is True
    assert temp_db.get_snippet(sid) is None