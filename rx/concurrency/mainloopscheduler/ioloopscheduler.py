import logging
from datetime import datetime, timedelta

from tornado import ioloop

from rx.disposables import Disposable, SingleAssignmentDisposable, \
    CompositeDisposable
from rx.concurrency.scheduler import Scheduler

log = logging.getLogger("Rx")

class IOLoopScheduler(Scheduler):
    """A scheduler that schedules work via the Tornado I/O main event loop.

    http://tornado.readthedocs.org/en/latest/ioloop.html
    """

    def __init__(self, loop):
        self.handle = None
        self.loop = loop

    def schedule(self, action, state=None):
        scheduler = self
        disposable = SingleAssignmentDisposable()

        def interval():
            disposable.disposable = action(scheduler, state)

        self.handle = self.loop.add_callback(interval)

        def dispose():
            self.loop.remove_timeout(self.handle)

        return CompositeDisposable(disposable, Disposable(dispose))

    def schedule_relative(self, duetime, action, state=None):
        """Schedules an action to be executed at duetime.

        Keyword arguments:
        duetime -- {timedelta} Relative time after which to execute the action.
        action -- {Function} Action to be executed.

        Returns {Disposable} The disposable object used to cancel the scheduled
        action (best effort)."""

        scheduler = self
        seconds = IOLoopScheduler.normalize(duetime)
        if seconds == 0:
            return scheduler.schedule(action, state)

        disposable = SingleAssignmentDisposable()
        def interval():
            disposable.disposable = action(scheduler, state)

        log.debug("timeout: %s", seconds)
        self.handle = self.loop.call_later(seconds, interval)

        def dispose():
            self.loop.remove_timeout(self.handle)

        return CompositeDisposable(disposable, Disposable(dispose))

    def schedule_absolute(self, duetime, action, state=None):
        """Schedules an action to be executed at duetime.

        Keyword arguments:
        duetime -- {datetime} Absolute time after which to execute the action.
        action -- {Function} Action to be executed.

        Returns {Disposable} The disposable object used to cancel the scheduled
        action (best effort)."""

        return self.schedule_relative(duetime - self.now(), action, state)

    def default_now(self):
        return self.loop.time()

    @classmethod
    def normalize(cls, timespan):
        """Eventloop operates with seconds as floats"""
        nospan = 0

        if isinstance(timespan, timedelta):
            seconds = timespan.seconds+timespan.microseconds/1000000.0

        elif isinstance(timespan, datetime):
            seconds = timespan.totimestamp()
        else:
            seconds = timespan

        if not timespan or timespan < nospan:
            seconds = nospan

        return seconds

