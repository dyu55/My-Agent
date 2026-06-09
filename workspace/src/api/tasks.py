from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from src.api.auth import get_db, get_current_user
from src.models.task import Task, Tag, task_tag as TaskTag
from src.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from src.schemas.user import UserResponse

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
)


@router.get("/", response_model=List[TaskResponse])
def list_tasks(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    获取当前用户的所有任务。
    """
    tasks = db.query(Task).filter(Task.user_id == current_user.id).all()
    return tasks


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    创建新任务（属于当前用户）。
    """
    # 处理标签：如果提供了 tag_ids，则关联已有标签或创建新标签？
    # 为了简单，这里假设 tag_ids 是已存在的标签 ID 列表（由用户提供）
    # 如果标签不存在则抛出 404？由业务决定，这里简单处理为忽略无效标签。
    tag_ids = task_data.tag_ids or []
    existing_tags = db.query(Tag).filter(Tag.id.in_(tag_ids)).all()
    if len(existing_tags) != len(tag_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more tag IDs are invalid.",
        )
    
    new_task = Task(
        title=task_data.title,
        description=task_data.description,
        completed=False,
        user_id=current_user.id,
    )
    db.add(new_task)
    db.flush()  # 获取新任务的 ID
    
    # 建立多对多关系
    for tag in existing_tags:
        db.add(TaskTag(task_id=new_task.id, tag_id=tag.id))
    
    db.commit()
    db.refresh(new_task)
    return new_task


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    获取单个任务，仅限当前用户的任务。
    """
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id,
    ).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return task


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    更新任务（标题、描述、完成状态、标签等）。
    """
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id,
    ).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    
    # 更新标量字段（仅当提供非 None 时才更新）
    if task_data.title is not None:
        task.title = task_data.title
    if task_data.description is not None:
        task.description = task_data.description
    if task_data.completed is not None:
        task.completed = task_data.completed
    
    # 处理标签更新（如果提供了 tag_ids）
    if task_data.tag_ids is not None:
        # 验证所有标签 ID 是否存在
        existing_tags = db.query(Tag).filter(Tag.id.in_(task_data.tag_ids)).all()
        if len(existing_tags) != len(task_data.tag_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more tag IDs are invalid.",
            )
        # 删除旧的关联
        db.query(TaskTag).filter(TaskTag.task_id == task.id).delete()
        # 创建新的关联
        for tag in existing_tags:
            db.add(TaskTag(task_id=task.id, tag_id=tag.id))
    
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    删除任务，仅限当前用户的任务。
    """
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id,
    ).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    db.delete(task)
    db.commit()
    return None
