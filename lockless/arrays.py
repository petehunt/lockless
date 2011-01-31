import multiprocessing

import version_clock
import err

class STMArray(object):
    def __init__(self, *args, **kwargs):
        self._array = multiprocessing.Array(*args, **kwargs)
        self.stm_lock = multiprocessing.RLock()
        self.version = multiprocessing.Value(version_clock.VersionClock.TYPECODE, 0)

    def __setitem__(self, *args, **kwargs):
        return core.Transaction.current().get_instance_for(self).__setitem__(*args, **kwargs)

    def __getitem__(self, *args, **kwargs):
        return core.Transaction.current().get_instance_for(self).__getitem__(*args, **kwargs)

    def __setslice__(self, *args, **kwargs):
        return core.Transaction.current().get_instance_for(self).__setslice__(*args, **kwargs)

    def __getslice__(self, *args, **kwargs):
        return core.Transaction.current().get_instance_for(self).__getslice__(*args, **kwargs)

class STMArrayInstance(object):
    """ only interact with this """
    def __init__(self, txn, stm_array):
        self.txn = txn
        self.stm_array = stm_array
        self.temp_array = stm_array._array.get_obj()._type_ * stm_array._array.get_obj()._length_
        self.temp_array = self.temp_array(*stm_array._array)
        self.dirty = False

    def _check(self):
        if self.stm_array.version.value > self.txn.read_version:
            raise err.RetryTransaction

    def __setitem__(self, *args, **kwargs):
        self.dirty = True
        self._check()
        return self.temp_array.__setitem__(*args, **kwargs)

    def __getitem__(self, *args, **kwargs):
        self._check()
        return self.temp_array.__getitem__(*args, **kwargs)

    def __setslice__(self, *args, **kwargs):
        self.dirty = True
        self._check()
        return self.temp_array.__setslice__(*args, **kwargs)

    def __getslice__(self, *args, **kwargs):
        self._check()
        return self.temp_array.__getslice__(*args, **kwargs)

    def _get_lock_id(self):
        return id(self.stm_array.stm_lock)

    def _precommit(self):
        if self.dirty:
            self.stm_array.stm_lock.acquire()
        self._check()

    def _commit(self):
        if self.dirty:
            self.stm_array._array[:] = self.temp_array
            self.stm_array.version.value = version_clock.VersionClock.read()

    def _postcommit(self):
        if self.dirty:
            self.stm_array.stm_lock.release()

import core
