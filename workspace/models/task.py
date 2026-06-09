import json
from datetime import datetime


class Task:
    """任务数据模型类，表示一个待办任务项"""
    
    def __init__(self, task_id: int, description: str, status: str = 'pending',
                 priority: int = 0, deadline: str = None, created_at: str = None):
        """
        初始化任务对象
        
        Args:
            task_id: 任务唯一ID
            description: 任务描述
            status: 任务状态，'pending' 或 'completed'
            priority: 优先级，0-5，0表示无优先级
            deadline: 截止日期，格式 'YYYY-MM-DD' 或 None
            created_at: 创建时间，自动生成
        """
        self.id = task_id
        self.description = description
        self.status = status if status in ('pending', 'completed') else 'pending'
        self.priority = max(0, min(5, int(priority)))
        self.deadline = deadline
        self.created_at = created_at if created_at else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def to_dict(self) -> dict:
        """将任务对象序列化为字典"""
        return {
            'id': self.id,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'deadline': self.deadline,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """从字典反序列化创建任务对象"""
        return cls(
            task_id=data['id'],
            description=data['description'],
            status=data.get('status', 'pending'),
            priority=data.get('priority', 0),
            deadline=data.get('deadline'),
            created_at=data.get('created_at')
        )
    
    def to_json(self) -> str:
        """将任务对象序列化为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str):
        """从JSON字符串反序列化创建任务对象"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def __repr__(self) -> str:
        return f"Task(id={self.id}, desc='{self.description}', status={self.status}, priority={self.priority})"
