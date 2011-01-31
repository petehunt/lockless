import version_clock
import err
import values
import arrays

class Transaction(object):
    """
    One per thread. Non-nestable (?)
    """

    _current = None
    _depth = 0
    INSTANCE_CLASSES = {
        values.STMValue: values.STMValueInstance,
        arrays.STMArray: arrays.STMArrayInstance,
        }
    
    def __init__(self):
        """ start the transaction """
        self.read_version = version_clock.VersionClock.read()
        self.instances = {}

    def commit(self):
        instances = sorted(self.instances.values(),
                           key=lambda x: x._get_lock_id())
        acquired = []
        try:
            for instance in instances:
                acquired.append(instance)
                instance._precommit()
            for instance in instances:
                instance._commit()
        finally:
            for instance in reversed(acquired):
                instance._postcommit()

    def get_instance_for(self, x):
        if x not in self.instances:
            self.instances[x] = self.INSTANCE_CLASSES[type(x)](self, x)
        return self.instances[x]

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
