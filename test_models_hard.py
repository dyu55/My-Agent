#!/usr/bin/env python3
"""
Model Hard Benchmark Test Runner for MyAgent
Evaluates models against 50 highly challenging edge-case Python coding questions.
Uses dynamic sandboxed execution of generated code against unit tests to determine correctness.
Includes a 70-second sleep between requests to respect rate limits.
"""

import os
import sys
import time
import json
import re
import multiprocessing
from datetime import datetime

# Adjust working directory to project root
os.chdir('/Users/donglingyu/Documents/MyAgent')
from dotenv import load_dotenv
load_dotenv()

from utils.model_provider import ModelManager

# Define the 50 extremely hard Python coding tasks
TEST_TASKS = [
    # ================= Category 1: Metaprogramming & Object Model =================
    {
        "id": "descriptor_validation",
        "category": "Metaprogramming",
        "prompt": "Implement a Python descriptor class named `StrictType` that checks type at runtime. It should accept a type (e.g., int, str) and an optional validator callable in its constructor. It must support inheritance (descriptors defined on base classes must work on subclasses) and must NOT leak memory (use `weakref` to track instance values). Raise TypeError if the type is incorrect, and ValueError if the validator returns False.",
        "test_code": """
import weakref
class Person:
    name = StrictType(str)
    age = StrictType(int, validator=lambda x: x >= 0)
class Employee(Person):
    pass
p = Employee()
p.name = "Alice"
p.age = 30
assert p.name == "Alice"
assert p.age == 30
try:
    p.name = 123
    assert False, "Should raise TypeError"
except TypeError:
    pass
try:
    p.age = -5
    assert False, "Should raise ValueError"
except ValueError:
    pass
"""
    },
    {
        "id": "metaclass_singleton_registry",
        "category": "Metaprogramming",
        "prompt": "Create a metaclass named `RegistrySingleton` that automatically registers all defined subclasses in a global directory attribute `_subclasses` of the metaclass (keys are class names), enforces the singleton pattern on each subclass individually, and provides a class method `reset_singleton()` on each subclass to discard the current instance.",
        "test_code": """
class A(metaclass=RegistrySingleton): pass
class B(metaclass=RegistrySingleton): pass
assert "A" in RegistrySingleton._subclasses
assert "B" in RegistrySingleton._subclasses
assert A() is A()
assert B() is B()
assert A() is not B()
old_a = A()
A.reset_singleton()
assert A() is not old_a
"""
    },
    {
        "id": "dynamic_property_interceptor",
        "category": "Metaprogramming",
        "prompt": "Create a class named `DynamicChain` where any attribute access that is not explicitly defined returns a callable/chainable object. Accessing nested attributes and calling the final chain returns a string representation of the dot-notation path. E.g., `obj.foo.bar.baz()` returns 'foo.bar.baz'. It should support arbitrary depth and not store state on the class level so that multiple chains don't conflict.",
        "test_code": """
obj = DynamicChain()
assert obj.foo.bar.baz() == "foo.bar.baz"
assert obj.x.y() == "x.y"
assert obj.a.b.c.d.e() == "a.b.c.d.e"
"""
    },
    {
        "id": "custom_mro_resolver",
        "category": "Metaprogramming",
        "prompt": "Write a function named `c3_mro(class_hierarchy: dict, target_class: str) -> list` that manually implements the C3 linearization algorithm to resolve the Method Resolution Order (MRO) of a target class given a dict mapping class names to lists of their direct base class names. The base object class is 'object' and has MRO ['object'].",
        "test_code": """
hierarchy = {
    "C": ["A", "B"],
    "A": ["O"],
    "B": ["O"],
    "O": ["object"],
    "object": []
}
mro = c3_mro(hierarchy, "C")
assert mro == ["C", "A", "B", "O", "object"], f"Expected MRO got {mro}"
"""
    },
    {
        "id": "abstract_final_enforcer",
        "category": "Metaprogramming",
        "prompt": "Implement a metaclass named `Enforcer` that prevents a class from being subclassed if it is decorated with a custom `@final` decorator, and prevents instantiation of a class if it contains any methods decorated with a custom `@abstractmethod` decorator. Do not use the built-in `abc` module.",
        "test_code": """
# Implementation of final and abstractmethod decorators should be included in their code
class AbstractClass(metaclass=Enforcer):
    @abstractmethod
    def run(self): pass
try:
    obj = AbstractClass()
    assert False, "Should raise TypeError on instantiating abstract"
except TypeError:
    pass

@final
class FinalClass(metaclass=Enforcer):
    pass
try:
    class SubFinal(FinalClass): pass
    assert False, "Should raise TypeError on subclassing final"
except TypeError:
    pass
"""
    },
    {
        "id": "descriptor_computed_caching",
        "category": "Metaprogramming",
        "prompt": "Create a descriptor class named `CachedComputed` that caches computed properties but automatically invalidates and recalculates them if and only if any of the specified dependent attributes (passed to constructor as a list of strings) change on the instance.",
        "test_code": """
class Circle:
    def __init__(self, r):
        self.r = r
        self.color = "blue"
    area = CachedComputed(lambda self: 3.14 * self.r * self.r, depend_on=['r'])
c = Circle(2)
assert c.area == 12.56
c.color = "red"
assert c.area == 12.56  # cache still valid
c.r = 3
assert c.area == 28.26  # cache invalidated and updated
"""
    },
    {
        "id": "namespace_jail",
        "category": "Metaprogramming",
        "prompt": "Write a metaclass named `JailedMeta` that checks all methods defined on a class. If any method attempts to read from global variables (i.e., variables not declared local, parameter, or in `self`), it raises `SecurityError` during class loading. You must implement a custom SecurityError class.",
        "test_code": """
global_var_test = 42
try:
    class BadClass(metaclass=JailedMeta):
        def bad_method(self):
            return global_var_test
    assert False, "Should have raised SecurityError"
except SecurityError:
    pass
"""
    },
    {
        "id": "dynamic_operator_overload",
        "category": "Metaprogramming",
        "prompt": "Implement a class named `FlexNumber` that dynamically overloads basic arithmetic operators (`+`, `-`, `*`) using behavior functions passed as a dictionary at construction time. E.g., `ops = {'+': lambda x, y: x * y}` makes `+` do multiplication.",
        "test_code": """
ops = {"+": lambda x, y: x * y, "-": lambda x, y: x + y}
n1 = FlexNumber(5, ops)
n2 = FlexNumber(3, ops)
assert n1 + n2 == 15
assert n1 - n2 == 8
"""
    },

    # ================= Category 2: Concurrency & Asyncio =================
    {
        "id": "async_rate_limiter",
        "category": "Concurrency",
        "prompt": "Implement an asyncio-based rate limiter class named `AsyncRateLimiter` using the token bucket algorithm. It must support the async context manager (`async with`) and respect fractional token replenishment based on actual time elapsed (using `asyncio.get_event_loop().time()`). Construct with `rate` (tokens per second) and `capacity` (max tokens).",
        "test_code": """
import asyncio
async def main_test():
    limiter = AsyncRateLimiter(rate=2, capacity=2)
    t0 = asyncio.get_event_loop().time()
    async with limiter: pass
    async with limiter: pass
    t1 = asyncio.get_event_loop().time()
    assert t1 - t0 < 0.1
    async with limiter: pass
    t2 = asyncio.get_event_loop().time()
    assert t2 - t0 >= 0.4
asyncio.run(main_test())
"""
    },
    {
        "id": "thread_safe_ring_buffer",
        "category": "Concurrency",
        "prompt": "Implement a thread-safe circular Ring Buffer class named `RingBuffer` of a fixed capacity. It should support blocking `put` (blocks if buffer is full) and blocking `get` (blocks if buffer is empty) with lock-based synchronization, handling condition notifications correctly.",
        "test_code": """
import threading
import time
buf = RingBuffer(capacity=3)
results = []
def consumer():
    for _ in range(4):
        results.append(buf.get())
t = threading.Thread(target=consumer)
t.start()
time.sleep(0.1)
buf.put(10)
buf.put(20)
buf.put(30)
buf.put(40)
t.join(timeout=1)
assert results == [10, 20, 30, 40]
"""
    },
    {
        "id": "async_priority_task_queue",
        "category": "Concurrency",
        "prompt": "Implement an async priority queue class named `AsyncPriorityQueue`. It should store items with priority (lower number = higher priority). If a task with the same key (passed as a string to put) is added again, it should update its priority and item in-place instead of creating a duplicate entry. Support async `put(item, priority, key)` and async `get()` returning the item.",
        "test_code": """
import asyncio
async def test_queue():
    q = AsyncPriorityQueue()
    await q.put(item="task1", priority=10, key="A")
    await q.put(item="task2", priority=5, key="B")
    await q.put(item="task1_updated", priority=2, key="A")
    first = await q.get()
    second = await q.get()
    assert first == "task1_updated"
    assert second == "task2"
asyncio.run(test_queue())
"""
    },
    {
        "id": "async_event_loop_monitor",
        "category": "Concurrency",
        "prompt": "Write a function `monitor_loop(loop, threshold=0.05, callback=None)` that returns an async task monitoring the active asyncio event loop. If any task blocks the event loop synchronously for longer than `threshold` seconds, it should invoke `callback` (a normal function) passing the duration of the block. Use asyncio tasks to implement.",
        "test_code": """
import asyncio
import time
called = []
def my_callback(duration):
    called.append(duration)
async def test_monitor():
    loop = asyncio.get_event_loop()
    task = loop.create_task(monitor_loop(loop, threshold=0.05, callback=my_callback))
    await asyncio.sleep(0.01)
    time.sleep(0.1)  # synchronous block
    await asyncio.sleep(0.01)
    task.cancel()
    try: await task
    except asyncio.CancelledError: pass
    assert len(called) >= 1
    assert called[0] >= 0.05
asyncio.run(test_monitor())
"""
    },
    {
        "id": "deadlock_detector",
        "category": "Concurrency",
        "prompt": "Create a lock class named `DeadlockLock` that wraps standard `threading.Lock` but detects potential deadlocks. If a thread attempts to acquire a lock that would create a cycle in the lock dependency graph (where dependency means holding lock A while waiting for lock B), raise a custom `DeadlockPotentialError` exception instead of blocking. Define `DeadlockPotentialError`.",
        "test_code": """
class DeadlockPotentialError(Exception): pass
# This verification verifies if cycle is detected. We can simulate thread holding locks.
import threading
import time

l1 = DeadlockLock()
l2 = DeadlockLock()
errors = []

def thread1_func():
    with l1:
        time.sleep(0.2)
        try:
            with l2: pass
        except DeadlockPotentialError as e:
            errors.append(e)

def thread2_func():
    time.sleep(0.1)
    with l2:
        try:
            with l1: pass
        except DeadlockPotentialError as e:
            errors.append(e)

t1 = threading.Thread(target=thread1_func)
t2 = threading.Thread(target=thread2_func)
t1.start()
t2.start()
t1.join()
t2.join()
assert len(errors) >= 1
"""
    },
    {
        "id": "async_gather_with_concurrency",
        "category": "Concurrency",
        "prompt": "Write a function `gather_with_concurrency(limit, *aws)` that behaves like `asyncio.gather` but limits the number of active coroutines running concurrently to `limit`. It should return a list of results in the original order.",
        "test_code": """
import asyncio
async def worker(val, log_list):
    log_list.append(f"start_{val}")
    await asyncio.sleep(0.05)
    log_list.append(f"end_{val}")
    return val * 2

async def main_test():
    log_list = []
    res = await gather_with_concurrency(2, worker(1, log_list), worker(2, log_list), worker(3, log_list))
    assert res == [2, 4, 6]
    # Verify concurrency limit (first two start before third starts)
    assert log_list[0].startswith("start_")
    assert log_list[1].startswith("start_")
    assert log_list[2].startswith("end_") or log_list[3].startswith("end_")
asyncio.run(main_test())
"""
    },
    {
        "id": "atomic_state_updater",
        "category": "Concurrency",
        "prompt": "Implement an atomic state updater class `AtomicDict` which has `get(key)` and `update(key, expected_val, new_val) -> bool`. The `update` method must atomize the operation using optimistic locking (retry / Compare-And-Swap) without using standard lock objects like threading.Lock on update, instead using a single lock or spin-lock/atomic constructs inside. (Hint: can simulate atomic updates in Python via thread-safe atomic types or local mutex loops).",
        "test_code": """
import threading
ad = AtomicDict()
ad.data = {"counter": 0}  # initialize data
# Verify counter increment by 10 threads
def worker():
    for _ in range(100):
        while True:
            cur = ad.get("counter")
            if ad.update("counter", cur, cur + 1):
                break

threads = [threading.Thread(target=worker) for _ in range(10)]
for t in threads: t.start()
for t in threads: t.join()
assert ad.get("counter") == 1000
"""
    },
    {
        "id": "async_retry_with_backoff",
        "category": "Concurrency",
        "prompt": "Create a decorator named `async_retry` for async functions. It should accept `exceptions` (tuple of exception classes), `max_retries` (int), `base_delay` (float), `backoff_factor` (float), and `jitter` (bool). It must retry on specified exceptions with exponential backoff and randomized jitter (+/- 10% of delay).",
        "test_code": """
import asyncio
import time
attempts = 0
@async_retry(exceptions=(ValueError,), max_retries=3, base_delay=0.01, backoff_factor=2, jitter=True)
async def fail_twice():
    global attempts
    attempts += 1
    if attempts < 3:
        raise ValueError("temporary error")
    return "success"

async def test_run():
    global attempts
    attempts = 0
    res = await fail_twice()
    assert res == "success"
    assert attempts == 3
asyncio.run(test_run())
"""
    },

    # ================= Category 3: Parsers & String Manipulation =================
    {
        "id": "json_parser_without_json",
        "category": "Parsers",
        "prompt": "Write a JSON parser function `parse_json(s: str) -> dict` that parses objects, arrays, strings with escaped characters (like \\n, \\t, \\\"), numbers (integers and floats), booleans, and nulls into Python primitives without using the standard `json` library or `eval`/`exec`.",
        "test_code": """
parsed = parse_json('{"a": [1, true, "hello\\\\nworld"], "b": null, "c": 3.14}')
assert parsed == {"a": [1, True, "hello\\nworld"], "b": None, "c": 3.14}
"""
    },
    {
        "id": "cron_expression_parser",
        "category": "Parsers",
        "prompt": "Write a function `next_cron_run(cron_expr: str, start_time: datetime) -> datetime` that parses a standard 5-field cron expression (minute hour day-of-month month day-of-week) and returns the next execution `datetime` strictly after `start_time`. Support numbers, list comma `,`, range `-`, and step `/`.",
        "test_code": """
from datetime import datetime
start = datetime(2026, 5, 20, 12, 0)
# cron: every 15 mins, between 9 and 17
next_run = next_cron_run("*/15 9-17 * * *", start)
assert next_run == datetime(2026, 5, 20, 12, 15)

start_late = datetime(2026, 5, 20, 17, 50)
next_run_day = next_cron_run("*/15 9-17 * * *", start_late)
assert next_run_day == datetime(2026, 5, 21, 9, 0)
"""
    },
    {
        "id": "markdown_table_to_json",
        "category": "Parsers",
        "prompt": "Write a function `parse_markdown_table(md: str) -> list[dict]` that parses markdown table syntax including alignments, empty cells, and escaped pipe characters (`\\|`) into a list of dictionaries mapping headers to row values. Ignore separator rows (rows with hyphens).",
        "test_code": """
md_table = '''
| Name | Age | Job |
| :--- | :---: | ---: |
| Alice | 30 | Engineer \\| Principal |
| Bob |  | Developer |
'''
res = parse_markdown_table(md_table.strip())
assert len(res) == 2
assert res[0] == {"Name": "Alice", "Age": "30", "Job": "Engineer | Principal"}
assert res[1] == {"Name": "Bob", "Age": "", "Job": "Developer"}
"""
    },
    {
        "id": "regex_parser_simplified",
        "category": "Parsers",
        "prompt": "Implement a simplified regex matcher `match_pattern(pattern: str, text: str) -> bool` that supports matching simple characters, wildcard `.`, zero-or-more `*`, zero-or-one `?`, and one-or-more `+`. It must match the ENTIRE text.",
        "test_code": """
assert match_pattern("ab*c", "abbbbc") is True
assert match_pattern("ab*c", "ac") is True
assert match_pattern("a.c", "abc") is True
assert match_pattern("a?c", "ac") is True
assert match_pattern("a+c", "abbbc") is True
assert match_pattern("a+c", "ac") is False
"""
    },
    {
        "id": "html_entity_decode_encoder",
        "category": "Parsers",
        "prompt": "Write a function `decode_html_entities(s: str) -> str` that decodes HTML entities (both decimal `&#60;`, hexadecimal `&#x3C;`, and common named ones like `&lt;`, `&gt;`, `&amp;`, `&quot;`, `&apos;`) without importing the standard `html` library.",
        "test_code": """
decoded = decode_html_entities("&lt;hello &amp; &#x27;world&#x27;&gt;")
assert decoded == "<hello & 'world'>"
"""
    },
    {
        "id": "csv_dialect_sniffer",
        "category": "Parsers",
        "prompt": "Write a function `parse_csv_dynamic(csv_data: str) -> list[list[str]]` that automatically sniffs the separator (either `,`, `;`, or `\\t`) and parses rows correctly, supporting quotes to handle separators inside fields.",
        "test_code": """
data1 = 'Name;Age;Job\\nAlice;30;"Engineer; Principal"\\nBob;25;Developer'
res = parse_csv_dynamic(data1)
assert len(res) == 3
assert res[1] == ["Alice", "30", "Engineer; Principal"]
"""
    },
    {
        "id": "url_query_parser",
        "category": "Parsers",
        "prompt": "Write a function `parse_query_string(qs: str) -> dict` that parses query parameters including percentage-decoded strings, lists (duplicate keys), and nested objects in bracket syntax (e.g. `filters[price][lt]=100`). E.g., `a=1&a=2&b[c]=3` -> `{'a': ['1', '2'], 'b': {'c': '3'}}`.",
        "test_code": """
res = parse_query_string("a=1&a=2&filters[price][lt]=100&name=John%20Doe")
assert res == {
    "a": ["1", "2"],
    "filters": {"price": {"lt": "100"}},
    "name": "John Doe"
}
"""
    },
    {
        "id": "tar_header_parser",
        "category": "Parsers",
        "prompt": "Parse a 512-byte tar archive header block (USTAR/POSIX format) and extract filename, file size, file mode, and link flag without importing the `tarfile` module. Size is stored in octal string. Return a dict with keys: 'name', 'size', 'mode', 'typeflag'. Ensure fields are stripped of null bytes.",
        "test_code": """
# Create a mock 512-byte block
block = bytearray(512)
block[0:10] = b"testfile.txt\\x00"
block[100:108] = b"0000644\\x00"  # mode
block[124:136] = b"00000000144\\x00"  # size in octal (100 in decimal)
block[156:157] = b"0"  # regular file typeflag
res = parse_tar_header(bytes(block))
assert res["name"] == "testfile.txt"
assert res["mode"] == 0o644
assert res["size"] == 100
assert res["typeflag"] == "0"
"""
    },
    {
        "id": "sql_where_clause_parser",
        "category": "Parsers",
        "prompt": "Write a parser `parse_where(sql: str) -> dict` that converts a SQL WHERE clause containing comparison operators (`=`, `<`, `>`), parenthesis, and `AND`/`OR` operators into an AST dictionary. E.g., `a = 1 AND (b = 2 OR c = 'text')` -> `{'op': 'AND', 'left': {'op': '=', 'left': 'a', 'right': '1'}, 'right': {'op': 'OR', 'left': {'op': '=', 'left': 'b', 'right': '2'}, 'right': {'op': '=', 'left': 'c', 'right': "'text'"}}}`.",
        "test_code": """
ast = parse_where("a = 1 AND (b = 2 OR c = 'text')")
assert ast == {
    'op': 'AND',
    'left': {'op': '=', 'left': 'a', 'right': '1'},
    'right': {
        'op': 'OR',
        'left': {'op': '=', 'left': 'b', 'right': '2'},
        'right': {'op': '=', 'left': 'c', 'right': "'text'"}
    }
}
"""
    },

    # ================= Category 4: Algorithmic & Data Structures =================
    {
        "id": "segment_tree_lazy",
        "category": "Algorithms",
        "prompt": "Implement a Segment Tree class `SegmentTree` with Lazy Propagation for an array of integers. It must support range sum updates (add value to range [L, R]) and range sum queries (return sum of range [L, R]) in O(log N) time complexity.",
        "test_code": """
st = SegmentTree([1, 3, 5, 7, 9, 11])
assert st.query(1, 3) == 15  # 3 + 5 + 7
st.update(1, 4, 2)            # add 2 to indices 1 to 4 -> [1, 5, 7, 9, 11, 11]
assert st.query(1, 3) == 21  # 5 + 7 + 9
"""
    },
    {
        "id": "trie_wildcard_search",
        "category": "Algorithms",
        "prompt": "Implement a Trie (Prefix Tree) class `WildcardTrie` supporting insertion of words and a wildcard search where the character '.' matches any single character. Methods: `insert(word: str)` and `search(word: str) -> bool`.",
        "test_code": """
trie = WildcardTrie()
trie.insert("bad")
trie.insert("dad")
trie.insert("mad")
assert trie.search("pad") is False
assert trie.search("bad") is True
assert trie.search(".ad") is True
assert trie.search("b..") is True
"""
    },
    {
        "id": "lru_lfu_hybrid_cache",
        "category": "Algorithms",
        "prompt": "Implement a hybrid LFU/LRU cache class `LFUCache` with capacity N. It should discard the Least Frequently Used (LFU) item first on overflow. If there is a tie, discard the Least Recently Used (LRU) item among the tied ones. Both `get(key)` and `put(key, val)` must run in O(1) average time complexity.",
        "test_code": """
cache = LFUCache(2)
cache.put(1, 1)
cache.put(2, 2)
assert cache.get(1) == 1
cache.put(3, 3)      # 2 is LFU (freq 1, 1 has freq 2). Evicts 2.
assert cache.get(2) == -1
assert cache.get(3) == 3
cache.put(4, 4)      # Both 1 and 3 have freq 2. 1 is LRU because 3 was updated last. Evicts 1.
assert cache.get(1) == -1
assert cache.get(4) == 4
"""
    },
    {
        "id": "red_black_tree",
        "category": "Algorithms",
        "prompt": "Implement insertion in a Red-Black Tree. Create a `RedBlackTree` class with `insert(val)` and verify correctness by checking that standard RBT properties are maintained after insertion (root is black, no red-red violations, all paths have equal black height). Define a verification method `is_valid_rbt(self) -> bool`.",
        "test_code": """
rbt = RedBlackTree()
for val in [10, 20, 30, 15, 25, 5]:
    rbt.insert(val)
assert rbt.is_valid_rbt() is True
"""
    },
    {
        "id": "consistent_hashing_ring",
        "category": "Algorithms",
        "prompt": "Implement a consistent hashing ring class `ConsistentHashRing` with virtual nodes. It should support adding nodes (`add_node(node_name: str, num_replicas: int = 5)`), removing nodes (`remove_node(node_name: str)`), and retrieving the closest node for a given key (`get_node(key: str) -> str`). Use standard hashlib md5 or sha256 for hashing.",
        "test_code": """
ring = ConsistentHashRing()
ring.add_node("nodeA", num_replicas=3)
ring.add_node("nodeB", num_replicas=3)
node1 = ring.get_node("my_key_1")
node2 = ring.get_node("my_key_2")
assert node1 in ["nodeA", "nodeB"]
ring.remove_node("nodeA")
assert ring.get_node("my_key_1") == "nodeB"
"""
    },
    {
        "id": "shortest_path_dijkstra_bidirectional",
        "category": "Algorithms",
        "prompt": "Implement a bidirectional Dijkstra's algorithm for finding the shortest path in a weighted graph. The graph is represented as a dictionary mapping node names to lists of tuples `(neighbor_name, weight)`. Implement `bidirectional_dijkstra(graph: dict, start: str, end: str) -> tuple[float, list[str]]` which returns a tuple of the path cost and the list of node names along the shortest path.",
        "test_code": """
graph = {
    "A": [("B", 1), ("C", 4)],
    "B": [("A", 1), ("C", 2), ("D", 5)],
    "C": [("A", 4), ("B", 2), ("D", 1)],
    "D": [("B", 5), ("C", 1)]
}
cost, path = bidirectional_dijkstra(graph, "A", "D")
assert cost == 4
assert path == ["A", "B", "C", "D"]
"""
    },
    {
        "id": "strongly_connected_components",
        "category": "Algorithms",
        "prompt": "Implement Tarjan's algorithm to find all strongly connected components in a directed graph. The graph is represented as a dictionary mapping node IDs (integers) to lists of neighbor IDs. Write `tarjan_scc(graph: dict) -> list[list[int]]` returning the components.",
        "test_code": """
graph = {
    0: [1],
    1: [2],
    2: [0, 3],
    3: [4],
    4: [5, 7],
    5: [6],
    6: [4, 7],
    7: []
}
sccs = tarjan_scc(graph)
# Sort components to verify
sccs_sorted = sorted([sorted(c) for c in sccs])
assert [0, 1, 2] in sccs_sorted
assert [4, 5, 6] in sccs_sorted
assert [3] in sccs_sorted
assert [7] in sccs_sorted
"""
    },
    {
        "id": "k_dimensional_tree",
        "category": "Algorithms",
        "prompt": "Implement a 2D KD-Tree for nearest neighbor search. Implement a class `KDTree` constructed with a list of 2D points (tuples of float/int). It must support a query method `nearest_neighbor(target: tuple[float, float]) -> tuple[float, float]` that returns the closest point according to Euclidean distance in O(log N) average time.",
        "test_code": """
points = [(2, 3), (5, 4), (9, 6), (4, 7), (8, 1), (7, 2)]
kdtree = KDTree(points)
assert kdtree.nearest_neighbor((9, 2)) == (8, 1)
assert kdtree.nearest_neighbor((3, 4)) == (2, 3)
"""
    },
    {
        "id": "min_heap_custom_comparator",
        "category": "Algorithms",
        "prompt": "Implement a binary Min-Heap class `CustomHeap` that accepts a custom comparator function during construction (e.g. `CustomHeap(lambda x, y: x['val'] < y['val'])`). It must support O(log N) operations: `push(item)` and `pop()` returning the item with highest priority (smallest comparator value).",
        "test_code": """
heap = CustomHeap(lambda x, y: len(x) < len(y))
heap.push("orange")
heap.push("apple")
heap.push("banana")
heap.push("pear")
assert heap.pop() == "pear"
assert heap.pop() == "apple"
"""
    },

    # ================= Category 5: Numeric, Financial & Math Edge Cases =================
    {
        "id": "precise_financial_allocator",
        "category": "Numeric",
        "prompt": "Implement a financial allocator function `allocate_funds(total_amount: str, weights: list[int]) -> list[str]` using exact Decimal numbers. It must divide `total_amount` (a string representing dollar amount) among the weights proportion, ensuring that the allocated shares sum EXACTLY to `total_amount` down to the cent ($0.01), distributing any remainder cents to the highest-weight items first (or in index order to resolve ties). All inputs/outputs must be strings.",
        "test_code": """
from decimal import Decimal
allocs = allocate_funds("0.10", [1, 1, 1])
assert len(allocs) == 3
# Must sum exactly to 0.10
assert sum(Decimal(x) for x in allocs) == Decimal("0.10")
assert sorted(allocs, reverse=True) == ["0.04", "0.03", "0.03"]
"""
    },
    {
        "id": "matrix_determinant_recursive",
        "category": "Numeric",
        "prompt": "Write a function `matrix_determinant(matrix: list[list[float]]) -> float` that computes the determinant of an N x N matrix recursively using cofactor expansion, handling exact edge cases and float precision.",
        "test_code": """
m = [
    [1.0, 2.0, 3.0, 4.0],
    [5.0, 6.0, 7.0, 8.0],
    [9.0, 10.0, 11.0, 12.0],
    [13.0, 14.0, 15.0, 16.0]
]
# Det of linearly dependent matrix is 0
assert abs(matrix_determinant(m)) < 1e-9

m2 = [
    [3, 8, 4, 6],
    [0, 2, 5, 2],
    [0, 0, 7, 3],
    [0, 0, 0, 5]
]
# Det of upper triangular is product of diagonal: 3*2*7*5 = 210
assert abs(matrix_determinant(m2) - 210) < 1e-9
"""
    },
    {
        "id": "ieee754_float_converter",
        "category": "Numeric",
        "prompt": "Implement a 32-bit single precision IEEE 754 float converter. Write two functions: `float_to_bin32(f: float) -> str` returning a 32-char binary string, and `bin32_to_float(b: str) -> float` converting it back. Handle special cases like positive/negative infinity, NaN (raise ValueError or return float('nan')), and subnormal (denormalized) numbers.",
        "test_code": """
import math
# Normal number: 0.15625 -> 00111110001000000000000000000000
assert float_to_bin32(0.15625) == "00111110001000000000000000000000"
assert bin32_to_float("00111110001000000000000000000000") == 0.15625

# Subnormal: 1e-40 -> converted to 0.0 or correct subnormal float representation
val = bin32_to_float("00000000000000000000000000000001")
assert val > 0.0
"""
    },
    {
        "id": "fraction_arithmetic_class",
        "category": "Numeric",
        "prompt": "Implement a custom rational number class `ExactFraction` supporting addition, subtraction, multiplication, and division, automatically reducing the fraction to its lowest terms. Do not import standard module `fractions`.",
        "test_code": """
f1 = ExactFraction(1, 3)
f2 = ExactFraction(1, 6)
res = f1 + f2
assert res.num == 1 and res.den == 2
assert str(f1 * 3) == "1"
"""
    },
    {
        "id": "arbitrary_precision_multiplication",
        "category": "Numeric",
        "prompt": "Implement the Karatsuba multiplication algorithm to multiply two extremely large integers represented as strings. Write `karatsuba_multiply(num1: str, num2: str) -> str` returning the product string. Do not use Python's built-in large integer multiplication directly (i.e. do not use `int(num1) * int(num2)` in the core computation, implement Karatsuba split-and-combine).",
        "test_code": """
n1 = "12345678901234567890"
n2 = "98765432109876543210"
expected = str(int(n1) * int(n2))
assert karatsuba_multiply(n1, n2) == expected
"""
    },
    {
        "id": "vector_similarity_sparse",
        "category": "Numeric",
        "prompt": "Compute the Cosine Similarity between two sparse vectors represented as dictionaries `{dimension_index: value}`. Implement `sparse_cosine_similarity(v1: dict, v2: dict) -> float` optimized for memory and speed (only process overlapping non-zero dimensions). Return 0.0 if vectors are orthogonal or empty.",
        "test_code": """
v1 = {1: 2.0, 3: 5.0, 999999: 4.0}
v2 = {1: 1.0, 4: 9.0, 999999: 3.0}
# overlap: dimension 1 and 999999.
# dot = 2*1 + 4*3 = 14
# mag1 = sqrt(4 + 25 + 16) = sqrt(45)
# mag2 = sqrt(1 + 81 + 9) = sqrt(91)
# cos = 14 / sqrt(45 * 91)
import math
expected = 14.0 / math.sqrt(45 * 91)
assert abs(sparse_cosine_similarity(v1, v2) - expected) < 1e-9
"""
    },
    {
        "id": "numerical_integrator_simpson",
        "category": "Numeric",
        "prompt": "Implement the Adaptive Simpson's Method for numerical integration of a function. Write `adaptive_simpson(f, a: float, b: float, tol: float) -> float` where `f` is a callable mathematical function, `a` and `b` are bounds, and `tol` is the error tolerance.",
        "test_code": """
import math
# Integrate sin(x) from 0 to pi. Expected result is 2.0
val = adaptive_simpson(math.sin, 0, math.pi, 0.0001)
assert abs(val - 2.0) < 0.001
"""
    },
    {
        "id": "fixed_point_math",
        "category": "Numeric",
        "prompt": "Implement a 16.16 fixed-point arithmetic library. Write functions `fp_add(x: int, y: int) -> int`, `fp_sub(x: int, y: int) -> int`, `fp_mul(x: int, y: int) -> int`, and `fp_div(x: int, y: int) -> int`. Numbers are represented as raw 32-bit signed integers where the lower 16 bits represent the fractional part. E.g., `1.0` is represented as `1 << 16` (65536). Handle round-to-nearest behavior on multiplication and division.",
        "test_code": """
# 1.5 is 98304, 2.0 is 131072
x = 1.5 * 65536
y = 2.0 * 65536
assert fp_add(int(x), int(y)) == int(3.5 * 65536)
assert fp_mul(int(x), int(y)) == int(3.0 * 65536)
assert fp_div(int(x), int(y)) == int(0.75 * 65536)
"""
    },

    # ================= Category 6: Memory, Garbage Collection & System Internals =================
    {
        "id": "cyclic_ref_garbage_collector",
        "category": "System",
        "prompt": "Create a dummy cycle detector mimicking standard garbage collection for reference cycles. Implement class `GNode` with a `ref_to(other)` list of links. Write `find_and_break_cycles(nodes: list[GNode]) -> int` which identifies cycles of unreachable objects (nodes that cannot be reached from any node outside the cycle) and breaks them by clearing their reference links, returning the number of broken links.",
        "test_code": """
# Create a cycle: A -> B -> A
a = GNode()
b = GNode()
a.ref_to.append(b)
b.ref_to.append(a)
# Both are unreachable from outside.
broken = find_and_break_cycles([a, b])
assert broken >= 1
assert len(a.ref_to) == 0 or len(b.ref_to) == 0
"""
    },
    {
        "id": "weakref_valued_cache",
        "category": "System",
        "prompt": "Implement a cache class `WeakValueCache` that maps keys to values, but stores values using weak references. When a value is no longer referenced anywhere else outside the cache, it must be automatically removed from the cache. Methods: `set(key, value)` and `get(key)` returning value or None.",
        "test_code": """
class ValueObj:
    def __init__(self, name): self.name = name

cache = WeakValueCache()
obj = ValueObj("hello")
cache.set("a", obj)
assert cache.get("a") is obj

# Delete external reference
del obj
import gc; gc.collect()
assert cache.get("a") is None
"""
    },
    {
        "id": "memory_buffer_view_slicer",
        "category": "System",
        "prompt": "Write a function `inplace_replace(buffer: bytearray, old_seq: bytes, new_seq: bytes)` that replaces all occurrences of `old_seq` with `new_seq` inside `buffer` IN-PLACE without creating any copies of the original buffer, by using `memoryview` where possible to slice and shift byte segments. The length of `old_seq` and `new_seq` are equal.",
        "test_code": """
buf = bytearray(b"hello world hello!")
inplace_replace(buf, b"hello", b"happy")
assert buf == bytearray(b"happy world happy!")
"""
    },
    {
        "id": "custom_import_hook",
        "category": "System",
        "prompt": "Write a custom import hook class `DynamicImportHook` and register it in `sys.meta_path`. It must intercept imports of modules starting with prefix `dynamic_` (e.g. `import dynamic_user`). When imported, it dynamically creates a module with a class having a single method `greet() -> str` returning the module name.",
        "test_code": """
import sys
# Create and register the hook
hook = DynamicImportHook()
sys.meta_path.insert(0, hook)
try:
    import dynamic_test_module
    obj = dynamic_test_module.DynamicClass()
    assert obj.greet() == "dynamic_test_module"
finally:
    # clean up hook
    if hook in sys.meta_path:
        sys.meta_path.remove(hook)
    if "dynamic_test_module" in sys.modules:
        del sys.modules["dynamic_test_module"]
"""
    },
    {
        "id": "context_manager_suppress",
        "category": "System",
        "prompt": "Create a context manager class `ExceptionFilter` that accepts a callable filter function. If an exception is raised inside the block, the manager passes it to the filter. If filter returns True, suppress it. If False, reraise it. If it returns another Exception instance, raise that instead.",
        "test_code": """
called = []
with ExceptionFilter(lambda e: isinstance(e, ValueError)):
    raise ValueError("suppressed")

try:
    with ExceptionFilter(lambda e: TypeError("transformed") if isinstance(e, ValueError) else False):
        raise ValueError("original")
    assert False, "Should have raised TypeError"
except TypeError as e:
    assert str(e) == "transformed"
"""
    },
    {
        "id": "object_size_estimator",
        "category": "System",
        "prompt": "Write a function `deep_size_of(obj) -> int` that recursively estimates the total memory footprint of any Python object (dicts, lists, sets, custom objects) using `sys.getsizeof`. It must handle circular references correctly without entering infinite recursion.",
        "test_code": """
lst = [1, 2]
lst.append(lst)  # create circle
size = deep_size_of(lst)
assert size > 0
# should not crash with infinite recursion
"""
    },
    {
        "id": "bytecode_analyzer_simple",
        "category": "System",
        "prompt": "Write a function `has_global_lookups(func) -> bool` that parses the bytecode of the given function `func` using Python's standard `dis` module, and returns True if the function performs any global variable lookups (e.g., uses LOAD_GLOBAL or similar operations), otherwise False.",
        "test_code": """
# Test function with only local variables
def local_func(x):
    y = x + 1
    return y

# Test function with global variable usage
GLOBAL_TEST_VAR = 10
def global_func(x):
    return x + GLOBAL_TEST_VAR

assert has_global_lookups(local_func) is False
assert has_global_lookups(global_func) is True
"""
    },
    {
        "id": "signal_timeout_context",
        "category": "System",
        "prompt": "Create a context manager class `TimeoutContext` that uses Unix signals (`signal.SIGALRM`) to enforce a strict timeout in seconds on a CPU-bound block. Raise a custom `TimeoutException` if the block takes longer than the timeout. Support nested contexts or resetting signal handler on exit.",
        "test_code": """
import time
class TimeoutException(Exception): pass
# Check timeout execution
try:
    with TimeoutContext(seconds=0.1):
        while True:
            pass  # CPU bound spin
    assert False, "Should have raised TimeoutException"
except TimeoutException:
    pass

# Check success before timeout
with TimeoutContext(seconds=0.5):
    time.sleep(0.01)
"""
    }
]

MODELS = [
    ('gemma-4-26b-a4b-it', '26b'),
    ('gemma-4-31b-it', '31b'),
    ('gemini-2.5-flash', '2.5-flash'),
]

def log(msg):
    print(msg)
    sys.stdout.flush()

def extract_python_code(response: str) -> str:
    """Extract code inside ```python ``` blocks, fallback to whole string if no blocks found."""
    pattern = r"```python\s*([\s\S]*?)\s*```"
    matches = re.findall(pattern, response)
    if matches:
        return "\n".join(matches)
    # If no ```python block, try cleaning markdown quotes or return response directly
    cleaned = response.replace("```", "")
    return cleaned

def _sandbox_run(code_str, test_code_str, queue):
    """Executes the code block + test block in a clean namespace inside a child process."""
    try:
        # Build local context
        namespace = {}
        # Pre-compile to raise syntax errors early
        compiled_code = compile(code_str, "<model_code>", "exec")
        exec(compiled_code, namespace)
        
        compiled_test = compile(test_code_str, "<test_code>", "exec")
        exec(compiled_test, namespace)
        queue.put((True, None))
    except Exception as e:
        queue.put((False, f"{type(e).__name__}: {str(e)}"))

def verify_code(code_str: str, test_code_str: str, timeout: int = 5) -> tuple[bool, str | None]:
    """Runs verification in a separate process with a strict timeout."""
    queue = multiprocessing.Queue()
    p = multiprocessing.Process(target=_sandbox_run, args=(code_str, test_code_str, queue))
    p.start()
    p.join(timeout)
    if p.is_alive():
        p.terminate()
        p.join()
        return False, "TimeoutError: Execution timed out (infinite loop or hang)"
    if not queue.empty():
        return queue.get()
    return False, "UnknownError: Verification failed without exception"

def run_single_task(manager, model_name, task) -> dict:
    """Query model for a single task and verify code correctness."""
    prompt = (
        f"{task['prompt']}\n\n"
        "Instructions:\n"
        "1. Write the code inside a single ```python and ``` block.\n"
        "2. Do not use external libraries that are not in the Python standard library.\n"
        "3. Ensure the classes, functions, and exceptions requested are named EXACTLY as specified."
    )
    
    for attempt in range(3):
        try:
            start_time = time.time()
            response = manager.chat(prompt, timeout=120)
            elapsed = time.time() - start_time
            
            code = extract_python_code(response)
            
            # Sandbox test the code
            success, error_msg = verify_code(code, task["test_code"])
            
            return {
                "success": success,
                "error": error_msg,
                "elapsed": round(elapsed, 2),
                "attempts": attempt + 1,
                "response_len": len(response),
                "code": code,
                "response": response
            }
        except Exception as e:
            err = str(e)
            log(f"  Attempt {attempt+1} API error: {err[:150]}")
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                log("  [Rate Limit Hit] Waiting 70s before retry...")
                time.sleep(70)
            else:
                time.sleep(5)
                
    return {
        "success": False,
        "error": "API failed after 3 attempts",
        "attempts": 3,
        "elapsed": 0.0
    }

def main():
    log("=" * 70)
    log("MYAGENT HARD MODEL BENCHMARK RUNNER")
    log(f"Tasks: {len(TEST_TASKS)} | Models: {len(MODELS)}")
    log("=" * 70)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_filename = f"test_progress_hard_{timestamp}.json"
    
    total_runs = len(TEST_TASKS) * len(MODELS)
    current_run = 0
    results = {mid: {} for _, mid in MODELS}
    
    manager = ModelManager()
    
    for model_name, model_id in MODELS:
        log(f"\nSwitching to Model: {model_name} ({model_id})")
        manager.set_model("gemini", model_name)
        
        # Verify connection
        if not manager.health_check():
            log(f"⚠️ Health check failed for {model_name}! Trying to run anyway...")
            
        for task in TEST_TASKS:
            current_run += 1
            log(f"[{current_run}/{total_runs}] Model: {model_id} | Task: {task['id']} ({task['category']})")
            
            res = run_single_task(manager, model_name, task)
            results[model_id][task["id"]] = res
            
            if res["success"]:
                log(f"  ✅ Correct! ({res['elapsed']}s)")
            else:
                log(f"  ❌ Fail: {res.get('error') or 'Incorrect behavior'} ({res['elapsed']}s)")
                
            # Save progress incrementally after each task
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
                
            # Respect Gemini rate limit: Sleep 70 seconds
            if current_run < total_runs:
                log("  Sleeping 70 seconds to respect rate limits...")
                time.sleep(70)
                
    log("\n" + "=" * 70)
    log("BENCHMARK COMPLETED")
    log("=" * 70)
    log(f"Detailed progress saved to {output_filename}")
    
    # Simple summary
    for model_id, tasks_res in results.items():
        correct_count = sum(1 for r in tasks_res.values() if r.get("success"))
        total = len(tasks_res)
        rate = (correct_count / total * 100) if total > 0 else 0
        log(f"{model_id}: {correct_count}/{total} Passed ({rate:.1f}%)")

if __name__ == "__main__":
    main()
