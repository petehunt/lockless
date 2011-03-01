import multiprocessing
import cPickle as pickle
import hashlib

from . import base
from .. import constants

class STMObject(base.STMRef):
    """
    I let you share objects between processes.

    Objects are depickled from a shared array on first
    read and are pickled to this array on commit. Even if
    the object has not changed, it will be pickled and the
    hash will be checked. If the hash has changed, then it
    will be written to the shared memory, otherwise it will
    remain untouched.

    """
    def __init__(self, value=None, size=constants.DEFAULT_OBJECT_SIZE):
        base.STMRef.__init__(self)
        self._array = multiprocessing.Array("c", size)
        self._array.raw = pickle.dumps(value, constants.PICKLE_PROTOCOL)

    def _set_value(self, value):
        return self._dispatch("_set_value", value)

    def _get_value(self):
        return self._dispatch("_get_value")

    value = property(_get_value, _set_value)

class STMObjectView(base.STMView):
    def __init__(self, txn, stm_object):
        base.STMView.__init__(self, txn, stm_object)
        value = stm_object._array.raw
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
        self.dirty = hashlib.sha256(self._dumped).digest() != self._hash
        return base.STMView._precommit(self)

    def commit(self):
        self.stm_ref._array.raw = self._dumped
        self._dumped = None

    def _postcommit(self):
        base.STMView._postcommit(self)
        self.dirty = False
