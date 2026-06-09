from pydantic import BaseModel


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    tag_ids: list[int] | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    completed: bool | None = None
    tag_ids: list[int] | None = None


class TaskResponse(BaseModel):
    id: int
    title: str
    description: str | None
    completed: bool
    user_id: int

    class Config:
        orm_mode = True


class TagCreate(BaseModel):
    name: str


class TagResponse(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True