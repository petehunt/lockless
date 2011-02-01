import contextlib
import time
import random

import core
import err
import constants

@contextlib.contextmanager
def atomic():
    """
    Execute a block of code atomically. If the transaction cannot complete,
    err.TransactionError is raised.
    """
    try:
        yield core.Transaction.start()
        core.Transaction.current().commit()
    finally:
        core.Transaction.exit()

_retries = 0
_tries = 0
_auto_retry_depth = 0

def auto_retry(initial_sleep_time=constants.DEFAULT_INITIAL_SLEEP_TIME,
               jitter=constants.DEFAULT_JITTER,
               backoff_factor=constants.DEFAULT_BACKOFF_FACTOR,
               no_delay_tries=constants.DEFAULT_NO_DELAY_TRIES,
               max_tries=constants.DEFAULT_MAX_TRIES,
               ):
    """ Decorator to automatically retry transactions with exponential backoff """
    def _d(f):
        def _f(*args, **kwargs):
            global _tries, _retries, _auto_retry_depth

            # should be called from outside of a transaction
            try:
                # check for nesting

                _auto_retry_depth += 1

                if _auto_retry_depth > 1:
                    return f(*args, **kwargs)

                sleep_time = initial_sleep_time
                _tries = 0
                _retries = 0

                while True:
                    _tries += 1
                    try:
                        return f(*args, **kwargs)
                    except err.ConflictError:
                        # When two transactions conflict, do exponential backoff.

                        if not max_tries is None and _tries > max_tries:
                            raise

                        if _tries > no_delay_tries:
                            t = max(0, sleep_time * random.uniform(1.0-jitter, 1.0+jitter))
                            time.sleep(t)
                            sleep_time *= backoff_factor
                    except err.RetryTransaction:
                        # The functionality of RetryTransaction is that the
                        # constructor will block until one of the values changes
                        _retries += 1
            finally:
                _auto_retry_depth -= 1
        return _f
    return _d

def transactional(*args, **kwargs):
    """
    Decorator to mark a function as transactional. You can use this instead of
    with blocks and auto_retry.
    """
    def _d(f):
        @auto_retry(*args, **kwargs)
        def _f(*args, **kwargs):
            with atomic():
                return f(*args, **kwargs)
        return _f
    return _d

def retry():
    """ Force the transaction to abort """
    raise err.RetryTransaction()

def retries():
    """ Returns the number of retries that have occured. Similar to orElse """
    global _retries
    return _retries

def conflicts():
    """ Returns the number of conflicts that have occurred. Useful for debugging """
    global _tries
    return _tries
