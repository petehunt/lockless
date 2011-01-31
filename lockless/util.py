import contextlib
import time
import random

import core
import err
import constants

@contextlib.contextmanager
def atomic():
    try:
        yield core.Transaction.start()
        core.Transaction.current().commit()
    finally:
        core.Transaction.exit()

def auto_retry(initial_sleep_time=constants.DEFAULT_INITIAL_SLEEP_TIME,
               jitter=constants.DEFAULT_JITTER,
               backoff_factor=constants.DEFAULT_BACKOFF_FACTOR,
               no_delay_tries=constants.DEFAULT_NO_DELAY_TRIES,
               max_tries=constants.DEFAULT_MAX_TRIES,
               ):
    def _d(f):
        def _f(*args, **kwargs):
            sleep_time = initial_sleep_time
            tries = 0

            while True:
                tries += 1
                try:
                    return f(*args, **kwargs)
                except err.RetryTransaction:
                    if tries > max_tries:
                        raise

                    if tries > no_delay_tries:
                        t = max(0, sleep_time * random.uniform(1.0-jitter, 1.0+jitter))
                        time.sleep(t)
                        sleep_time *= backoff_factor

        return _f
    return _d

def transact(*args, **kwargs):
    def _d(f):
        @auto_retry(*args, **kwargs)
        def _f(*args, **kwargs):
            with atomic():
                return f(*args, **kwargs)
        return _f
    return _d

def retry():
    raise err.RetryTransaction()