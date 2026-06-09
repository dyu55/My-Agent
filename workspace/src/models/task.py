from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table, Text
from sqlalchemy.orm import relationship
from .user import Base  # 假设 Base 在 user.py 中定义并导出，确保所有模型使用同一基类

# 多对多关联表
task_tag = Table(
    'task_tag',
    Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)

class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    completed = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # 关系
    owner = relationship('User', back_populates='tasks')
    tags = relationship('Tag', secondary=task_tag, back_populates='tasks')

class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)

    # 关系
    tasks = relationship('Task', secondary=task_tag, back_populates='tags')
