import multiprocessing

import version_clock
import err

class STMValue(object):
    """ I am the transactional equivalent of a multiprocessing.Value. """
    def __init__(self, *args, **kwargs):
        self._value = multiprocessing.Value(*args, **kwargs)
        self.stm_lock = multiprocessing.RLock()
        self.version = multiprocessing.Value(version_clock.VersionClock.TYPECODE, 0)

    def _get_value(self):
        return core.Transaction.current().get_instance_for(self).value

    def _set_value(self, value):
        core.Transaction.current().get_instance_for(self).value = value

    value = property(_get_value, _set_value)

class STMValueInstance(object):
    """ only interact with this """
    def __init__(self, txn, stm_value):
        self.txn = txn
        self.stm_value = stm_value
        self.temp_value = stm_value._value.value
        self.dirty = False

    def _check(self):
        if self.stm_value.version.value > self.txn.read_version:
            raise err.RetryTransaction

    def _get_value(self):
        self._check()
        return self.temp_value

    def _set_value(self, value):
        self.dirty = True
        self._check()
        self.temp_value = value

    value = property(_get_value, _set_value)

    def _get_lock_id(self):
        return id(self.stm_value.stm_lock)

    def _precommit(self):
        if self.dirty:
            self.stm_value.stm_lock.acquire()
        self._check()

    def _commit(self):
        if self.dirty:
            self.stm_value._value.value = self.temp_value
            self.stm_value.version.value = version_clock.VersionClock.read()

    def _postcommit(self):
        if self.dirty:
            self.stm_value.stm_lock.release()
    
import core
