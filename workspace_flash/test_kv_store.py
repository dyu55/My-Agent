import time
import os
import pytest
from kv_store import KVStore

def test_basic_operations():
    kv = KVStore()
    kv.set("key1", "value1")
    assert kv.get("key1") == "value1"
    kv.delete("key1")
    assert kv.get("key1") is None

def test_ttl_expiration():
    kv = KVStore()
    kv.set("key1", "value1", ttl=0.1)
    assert kv.get("key1") == "value1"
    time.sleep(0.2)
    assert kv.get("key1") is None

def test_transaction_atomicity():
    kv = KVStore()
    kv.set("key1", "original")
    kv.begin()
    kv.set("key1", "changed")
    assert kv.get("key1") == "changed"
    kv.rollback()
    assert kv.get("key1") == "original"

def test_transaction_commit():
    kv = KVStore()
    kv.set("key1", "original")
    kv.begin()
    kv.set("key1", "changed")
    kv.commit()
    assert kv.get("key1") == "changed"

def test_nested_transactions():
    kv = KVStore()
    kv.set("key1", "root")
    kv.begin()
    kv.set("key1", "level1")
    kv.begin()
    kv.set("key1", "level2")
    assert kv.get("key1") == "level2"
    kv.rollback()
    assert kv.get("key1") == "level1"
    kv.commit()
    assert kv.get("key1") == "level1"

def test_json_persistence():
    kv = KVStore()
    filename = "test_store.json"
    kv.set("key1", "value1")
    kv.set("key2", "value2")
    kv.save_to_file(filename)
    
    kv2 = KVStore()
    kv2.load_from_file(filename)
    assert kv2.get("key1") == "value1"
    assert kv2.get("key2") == "value2"
    
    if os.path.exists(filename):
        os.remove(filename)