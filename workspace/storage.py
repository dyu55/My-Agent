import json
import os
from typing import List
from models.todo_item import Task

DATA_FILE = "tasks.json"

def save_tasks(tasks: List[Task], filepath: str = DATA_FILE):
    """将任务列表保存到 JSON 文件"""
    data = [task.to_dict() for task in tasks]
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_tasks(filepath: str = DATA_FILE) -> List[Task]:
    """从 JSON 文件加载任务列表"""
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Task.from_dict(item) for item in data]
