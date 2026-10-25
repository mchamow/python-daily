"""The domain: tasks and the file that holds them, as plain dataclasses."""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum, auto

SCHEMA_VERSION = 1


class Priority(StrEnum):
    # auto() on a StrEnum gives the lowercased member name: Priority.HIGH == "high".
    LOW = auto()
    NORMAL = auto()
    HIGH = auto()


class TaskNotFound(LookupError):
    def __init__(self, task_id: int) -> None:
        super().__init__(f"no task #{task_id}")


@dataclass(slots=True)
class Task:
    id: int
    title: str
    created: datetime
    priority: Priority = Priority.NORMAL
    tags: list[str] = field(default_factory=list)  # never `= []`: that one list would be shared
    due: date | None = None
    done: datetime | None = None


@dataclass(slots=True)
class TodoFile:
    version: int = SCHEMA_VERSION
    next_id: int = 1  # ids are never reused, so '#7' always means the same task
    tasks: list[Task] = field(default_factory=list)

    def add(
        self,
        title: str,
        *,
        now: datetime,
        priority: Priority = Priority.NORMAL,
        tags: list[str] | None = None,
        due: date | None = None,
    ) -> Task:
        if not title.strip():
            raise ValueError("a task needs a title")
        task = Task(self.next_id, title.strip(), now, priority, tags or [], due)
        self.tasks.append(task)
        self.next_id += 1
        return task

    def find(self, task_id: int) -> Task:
        # next() with a default is the idiomatic FirstOrDefault.
        task = next((t for t in self.tasks if t.id == task_id), None)
        if task is None:
            raise TaskNotFound(task_id)
        return task

    def remove(self, task_ids: list[int]) -> list[Task]:
        doomed = [self.find(task_id) for task_id in task_ids]  # raises before changing anything
        self.tasks = [t for t in self.tasks if t not in doomed]
        return doomed

    def clear_done(self) -> list[Task]:
        done = [t for t in self.tasks if t.done]
        self.tasks = [t for t in self.tasks if not t.done]
        return done


_RANK = {Priority.HIGH: 0, Priority.NORMAL: 1, Priority.LOW: 2}


def sort_key(task: Task) -> tuple[bool, int, date, int]:
    """Open before done, then priority, then soonest due date (none goes last), then oldest."""
    return (task.done is not None, _RANK[task.priority], task.due or date.max, task.id)
