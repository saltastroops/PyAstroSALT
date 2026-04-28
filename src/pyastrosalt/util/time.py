"""Time providers.

`SystemTimeProvider` should be used instead of `datetime.datetime.now`.
`FakeTimeProvider` is intended for testing only.
"""

from datetime import datetime, timedelta
from typing import Protocol


class TimeProvider(Protocol):
    """Protocol defining a time provider."""

    def now(self) -> datetime:
        """
        Return the current date and time as a naive `datetime.datetime` instance.

        Returns:
            The current date and time.
        """
        ...


class SystemTimeProvider:
    """A time provider.

    This provider be used instead of the `datetime.datetime.now` method.
    """

    def now(self) -> datetime:
        """
        Return the current date and time as a naive `datetime.datetime` instance.

        The time is that returned by `datetime.datetime.now`.

        Returns:
            The current date and time.
        """
        return datetime.now()


class FakeTimeProvider:
    """A time provider for testing.

    The current date and time is set when creating a `FakeTimeProvider` instance. By
    default, it remains constant. However, it can be changed in the following ways:

    1. You can set the `time` property to the desired date and time.
    2. You can set the `tick` property. The value of this property is added to the
       `time` property whenever the `now` method is called.
    """

    def __init__(self):
        """Initialize the provider instance."""
        self.time = datetime.now()
        self.tick = timedelta(seconds=0)

    def now(self) -> datetime:
        """Return the "current date and time" and update that time.

        The value returned is the current value of the `time` property. The value of the
        `tick` property is added to this property.

        Returns:
             The current date and time.
        """
        current_time = self.time
        self.time += self.tick
        return current_time
