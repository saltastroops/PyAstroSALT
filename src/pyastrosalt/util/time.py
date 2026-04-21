from datetime import datetime, timedelta
from typing import Protocol


class TimeProvider(Protocol):
    def now(self) -> datetime:
        raise NotImplementedError


class SystemTimeProvider:
    def now(self) -> datetime:
        return datetime.now()


class FakeTimeProvider:
    def __init__(self):
        self.time = datetime.now()
        self.tick = timedelta(seconds=0)

    def now(self) -> datetime:
        current_time = self.time
        self.time += self.tick
        return current_time
