import time

from . import version_clock
from . import err
from . import refs
from . import constants

class Transaction(object):
    """
    One per thread. Non-nestable (?)
    """

    _current = None
    _depth = 0
    VIEW_CLASSES = {
        refs.STMValue: refs.STMValueView,
        refs.STMArray: refs.STMArrayView,
        refs.STMObject: refs.STMObjectView,
        }
    
    def __init__(self):
        """ start the transaction """
        self.read_version = version_clock.VersionClock.read()
        self.views = {}

    def commit(self):
        # if we are nested, don't commit
        if self._depth > 1:
            return

        views = sorted(self.views.values(),
                           key=lambda x: x._get_lock_id())
        acquired = []
        try:
            for view in views:
                acquired.append(view)
                view._precommit()
            for view in views:
                view._commit()
        finally:
            for view in reversed(acquired):
                view._postcommit()

    def get_view_for(self, stm_ref):
        if stm_ref not in self.views:
            self.views[stm_ref] = self.VIEW_CLASSES[type(stm_ref)](self, stm_ref)
        return self.views[stm_ref]

    def wait_for_update(self, timeout=constants.DEFAULT_WAIT_TIMEOUT):
        while True:
            for stm_ref in self.views.keys():
                if stm_ref.wait_for_update(0):
                    return
            time.sleep(timeout)

    @classmethod
    def start(cls):
        if cls._current is None:
            cls._current = cls()
        cls._depth += 1
        return cls._current

    @classmethod
    def current(cls):
        if cls._current is None:
            raise err.NoTransactionError
        return cls._current

    @classmethod
    def exit(cls):
        if cls._current is None:
            raise err.NoTransactionError
        cls._depth -= 1
        if cls._depth == 0:
            cls._current = None
