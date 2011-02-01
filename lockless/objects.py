import multiprocessing
import cPickle as pickle
import hashlib

import base
import constants

class STMObject(base.STMVar):
    """
    I let you share objects between processes.

    Objects are depickled from a shared array on first
    read and are pickled to this array on commit. Even if
    the object has not changed, it will be pickled and the
    hash will be checked. If the hash has changed, then it
    will be written to the shared memory, otherwise it will
    remain untouched.

    """
    def __init__(self, size):
        base.STMVar.__init__(self)
        self._array = multiprocessing.Array("c", size)

    def _set_value(self, value):
        return self._dispatch("_set_value", value)

    def _get_value(self):
        return self._dispatch("_get_value")

    value = property(_get_value, _set_value)

class STMObjectInstance(base.STMInstance):
    def __init__(self, txn, stm_object):
        base.STMInstance.__init__(self, txn, stm_object)
        value = stm_object._array.value
        if len(value) == 0:
            self._hash = self._value = None
        else:
            self._hash = hashlib.sha256(value).digest()
            self._value = pickle.loads(value)
        self._dumped = None

    def _get_value(self):
        self._check()
        return self._value

    def _set_value(self, value):
        self._check()
        self._value = value

    def _precommit(self):
        self._dumped = pickle.dumps(self._value, constants.PICKLE_PROTOCOL)
        self.dirty = hashlib.sha256(self._dumped).digest() == self._hash
        return base.STMInstance._precommit(self)

    def commit(self):
        self.stm_var._array.value = self._dumped
        self._dumped = None
