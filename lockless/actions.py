# Support for side effects
import sys

from . import core

class Action(object):
    def _precommit(self):
        pass

    def _postcommit(self):
        pass

    def _commit(self):
        pass

    def wait_for_update(self, timeout=None):
        return False
    
    def _get_lock_id(self):
        return -sys.maxint

class OnCommitAction(Action):
    def __init__(self, f, args, kwargs):
        self.f = f
        self.args = args
        self.kwargs = kwargs
        self.dirty = True

    def _precommit(self):
        self.committed = False

    def _commit(self):
        self.committed = True

    def _postcommit(self):
        if self.committed:
            self.f(*self.args, **self.kwargs)

def on_commit(f, *args, **kwargs):
    """
    Run an action on commit. Use me for e.g. logging.
    """
    se = OnCommitAction(f, args, kwargs)
    core.Transaction.current().views[se] = se
