# Lockless for multiprocessing

# TODO: hybrid process/thread pools
# TODO: futures-based generators, integrate into pools
# TODO: transactional i/o?
# TODO: support DB-API?

import multiprocessing
import contextlib
import time

INITIAL_SLEEP_TIME = 0.01
JITTER = .25 # percentage of current sleep time

class VersionClock(object):
    TYPECODE = "i"

    def __init__(self):
        self.lock = multiprocessing.RLock()
        self.value = multiprocessing.Value("i", 0)

    def _read(self):
        with self.lock:
            self.value.value += 1
            return self.value.value

    @classmethod
    def read(cls):
        return cls.GLOBAL._read()

VersionClock.GLOBAL = VersionClock()

class RetryTransaction(Exception):
    pass

class NoTransactionException(Exception):
    pass

class STMValue(object):
    """ hidden """
    def __init__(self, *args, **kwargs):
        self._value = multiprocessing.Value(*args, **kwargs)
        self.stm_lock = multiprocessing.RLock()
        self.version = multiprocessing.Value(VersionClock.TYPECODE, 0)

    def _get_value(self):
        return Transaction.current().get_instance_for(self).value

    def _set_value(self, value):
        Transaction.current().get_instance_for(self).value = value

    value = property(_get_value, _set_value)

class STMArray(object):
    def __init__(self, *args, **kwargs):
        self._array = multiprocessing.Array(*args, **kwargs)
        self.stm_lock = multiprocessing.RLock()
        self.version = multiprocessing.Value(VersionClock.TYPECODE, 0)

    def __setitem__(self, *args, **kwargs):
        return Transaction.current().get_instance_for(self).__setitem__(*args, **kwargs)

    def __getitem__(self, *args, **kwargs):
        return Transaction.current().get_instance_for(self).__getitem__(*args, **kwargs)

    def __setslice__(self, *args, **kwargs):
        return Transaction.current().get_instance_for(self).__setslice__(*args, **kwargs)

    def __getslice__(self, *args, **kwargs):
        return Transaction.current().get_instance_for(self).__getslice__(*args, **kwargs)

class STMValueInstance(object):
    """ only interact with this """
    def __init__(self, txn, stm_value):
        self.txn = txn
        self.stm_value = stm_value
        self.temp_value = stm_value._value.value
        self.dirty = False

    def _check(self):
        if self.stm_value.version.value > self.txn.read_version:
            raise RetryTransaction

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
            self.stm_value.version.value = VersionClock.read()

    def _postcommit(self):
        if self.dirty:
            self.stm_value.stm_lock.release()
    
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
            raise RetryTransaction

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
            self.stm_array.version.value = VersionClock.read()

    def _postcommit(self):
        if self.dirty:
            self.stm_array.stm_lock.release()

class Transaction(object):
    """
    One per thread. Non-nestable (?)
    """

    _current = None
    _depth = 0
    
    def __init__(self):
        """ start the transaction """
        self.read_version = VersionClock.read()
        self.instances = {}

    def commit(self):
        instances = sorted(self.instances.values(),
                           key=lambda x: x._get_lock_id())
        acquired = []
        try:
            for instance in instances:
                acquired.append(instance)
                instance._precommit()
            for instance in instances:
                instance._commit()
        finally:
            for instance in reversed(acquired):
                instance._postcommit()

    def get_instance_for(self, x):
        if x not in self.instances:
            if isinstance(x, STMValue):
                self.instances[x] = STMValueInstance(self, x)
            else:
                self.instances[x] = STMArrayInstance(self, x)
        return self.instances[x]

    @classmethod
    def start(cls):
        if cls._current is None:
            cls._current = cls()
        cls._depth += 1
        return cls._current

    @classmethod
    def current(cls):
        if cls._current is None:
            raise NoTransactionException
        return cls._current

    @classmethod
    def exit(cls):
        if cls._current is None:
            raise NoTransactionException
        cls._depth -= 1
        if cls._depth == 0:
            cls._current = None

@contextlib.contextmanager
def atomic():
    try:
        yield Transaction.start()
        Transaction.current().commit()
    finally:
        Transaction.exit()

def auto_retry(f):
    def _f(*args, **kwargs):
        sleep_time = INITIAL_SLEEP_TIME
        while True:
            try:
                return f(*args, **kwargs)
            except RetryTransaction:
                t = max(0, sleep_time * random.uniform(1.0-JITTER, 1.0+JITTER))
                #print "sleeping %s" % t
                time.sleep(t)
                sleep_time *= 2.0

    return _f

def transact(f):
    @auto_retry
    def _f(*args, **kwargs):
        with atomic():
            return f(*args, **kwargs)
    return _f

def retry():
    raise RetryTransaction()

### test code ###
import random

class BankAccount(object):
    def __init__(self, account_number, initial_balance):
        self.account_number = account_number
        self.balance = STMArray("i", 1) #STMValue("i", initial_balance)
        with atomic():
            self.balance[0] = initial_balance

@auto_retry
def do_trade(accts, count):
    acct1 = acct2 = random.choice(accts)
    while acct1 == acct2:
        acct2 = random.choice(accts)

    # transactify
    with atomic():
        try:
            amt = random.randint(0, acct1.balance[0]-1)
        except ValueError:
            retry()

        acct1.balance[0] -= amt
        acct2.balance[0] += amt

def trader(accts, count):
    for _ in range(0, count):
        do_trade(accts, count)

def main(n=10, c=1000, a=10, cash=100):
    accts = []

    for account_number in range(0, a):
        accts.append(BankAccount(account_number, cash))

    processes = []

    for _ in range(0, n):
        processes.append(multiprocessing.Process(target=trader, args=(accts, c)))
        processes[-1].start()

    for p in processes:
        p.join()

    dump(cash, a, accts)

@auto_retry
def dump(cash, a, accts):
    with atomic():
        total_cash = cash * a
        for acct in accts:
            print(acct.balance[0])
            total_cash -= acct.balance[0]

    assert total_cash == 0, "Failed! %d" % total_cash

if __name__ == "__main__":
    main()
