from contextlib import contextmanager

class LockOrderException(Exception):
    pass

acquired = []
@contextmanager
def acquire(*locks):
    locks = sorted(locks, key=lambda x: id(x))   
    # Check to make sure we're not violating the order of locks already acquired   
    if acquired:
        if max(id(lock) for lock in acquired) >= id(locks[0]):
            raise LockOrderException()
    acquired.extend(locks)
    try:
        for lock in locks:
            lock.acquire()
        yield
    finally:
        for lock in reversed(locks):
            lock.release()
        del acquired[-len(locks):]
