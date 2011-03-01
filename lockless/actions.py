# Support for side effects

from . import core

class Action(object):
    def __init__(self, f, args, kwargs):
        self.f = f
        self.args = args
        self.kwargs = kwargs
        self.dirty = True

    def _precommit(self):
        pass

    def _postcommit(self):
        pass

    def _commit(self):
        self.f(*self.args, **self.kwargs)

    def wait_for_update(self, timeout=None):
        return False
    
    def _get_lock_id(self):
        return 0

def on_commit(f, *args, **kwargs):
    """
    Run an action on commit. Use me for e.g. logging.
    """
    se = Action(f, args, kwargs)
    core.Transaction.current().views[se] = se
