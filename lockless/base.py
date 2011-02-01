import multiprocessing

import version_clock
import err

class STMVar(object):
    def __init__(self):
        self.stm_lock = multiprocessing.RLock()
        self.version = multiprocessing.Value(version_clock.VersionClock.TYPECODE, 0)
        
    def _dispatch(self, method_name, *args, **kwargs):
        import core # TODO: only do this once?
        return getattr(core.Transaction.current().get_instance_for(self),
                       method_name)(*args, **kwargs)

class STMInstance(object):
    def __init__(self, txn, stm_var):
        self.txn = txn
        self.stm_var = stm_var
        self.dirty = False

    def _check(self):
        if self.stm_var.version.value > self.txn.read_version:
            raise err.ConflictError

    def _get_lock_id(self):
        return id(self.stm_var.stm_lock)

    def _precommit(self):
        if self.dirty:
            self.stm_var.stm_lock.acquire()
        self._check()

    def _commit(self):
        if self.dirty:
            self.commit()
            self.stm_var.version.value = version_clock.VersionClock.read()

    def _postcommit(self):
        if self.dirty:
            self.stm_var.stm_lock.release()

    def commit(self):
        raise NotImplementedError
