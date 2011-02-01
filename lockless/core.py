import version_clock
import err
import values
import arrays
import objects
import constants

class Transaction(object):
    """
    One per thread. Non-nestable (?)
    """

    _current = None
    _depth = 0
    INSTANCE_CLASSES = {
        values.STMValue: values.STMValueInstance,
        arrays.STMArray: arrays.STMArrayInstance,
        objects.STMObject: objects.STMObjectInstance,
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

    def get_instance_for(self, stm_var):
        if stm_var not in self.instances:
            self.instances[stm_var] = self.INSTANCE_CLASSES[type(stm_var)](self, stm_var)
        return self.instances[stm_var]

    def wait_for_update(self, timeout=constants.DEFAULT_WAIT_TIMEOUT):
        while True:
            for stm_var in self.instances.keys():
                if stm_var.wait_for_update(timeout):
                    return

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
