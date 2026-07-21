from dataclasses import dataclass, field, asdict
from typing import Optional
import time


@dataclass
class Task:
    id: int
    title: str
    done: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


class TaskStore:
    def __init__(self):
        self._tasks: dict[int, Task] = {}
        self._next_id: int = 1

    def get_all(self) -> list[dict]:
        return [t.to_dict() for t in self._tasks.values()]

    def get(self, task_id: int) -> Optional[Task]:
        return self._tasks.get(task_id)

    def create(self, title: str) -> Task:
        if not title or not title.strip():
            raise ValueError("Title cannot be empty")
        task = Task(id=self._next_id, title=title.strip())
        self._tasks[self._next_id] = task
        self._next_id += 1
        return task

    def delete(self, task_id: int) -> bool:
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False
