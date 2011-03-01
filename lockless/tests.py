import random
import multiprocessing
import unittest

from . import auto_retry, STMValue, atomic, retry, STMObject, ConflictError, on_commit, transactional, retries, conflicts

class BankAccount(object):
    def __init__(self, account_number, initial_balance):
        self.account_number = account_number
        self.balance = STMObject(initial_balance) #STMValue("i", initial_balance)

@auto_retry()
#@auto_retry()
def do_trade(accts, count):
    acct1 = acct2 = random.choice(accts)
    while acct1 == acct2:
        acct2 = random.choice(accts)

    # transactify
    with atomic():
        try:
            amt = random.randint(0, acct1.balance.value-1)
        except ValueError:
            retry() # raise ConflictError?

        # try nesting to make sure it doesn't crash
        with atomic():
            acct1.balance.value -= amt
            acct2.balance.value += amt

def trader(accts, count):
    for _ in range(0, count):
        do_trade(accts, count)

class TestBasic(unittest.TestCase):
    def test_main(self):
        n = 10 # num threads
        c = 1000 # num xact
        a = 30 # num accounts
        cash = 100

        accts = []

        for account_number in range(0, a):
            accts.append(BankAccount(account_number, cash))

        processes = []

        for _ in range(0, n):
            processes.append(multiprocessing.Process(target=trader, args=(accts, c)))
            processes[-1].start()

        for p in processes:
            p.join()

        self.check(cash, a, accts)

    @auto_retry()
    def check(self, cash, a, accts):
        nonhundo = False
        with atomic():
            total_cash = cash * a
            for acct in accts:
                if acct.balance.value != 100:
                    nonhundo = True
                total_cash -= acct.balance.value

        self.assertTrue(nonhundo)
        self.assertEqual(0, total_cash)

    def test_pickle(self):
        a = STMObject(128)
        with atomic():
            a.value = "pete"
            self.assertEqual(a.value, "pete")
        # test mutation
        with atomic():
            a.value = [1,2,3]
            self.assertEqual(a.value, [1,2,3])
            a.value.append(7)
            self.assertEqual(a.value, [1,2,3,7])

    @transactional()
    def helper(self):
        on_commit(self.l.append, 1)
        if conflicts() < 3:
            raise ConflictError

    def test_on_commit(self):
        self.l = []
        self.helper()
        self.helper()
        self.helper()
        self.assertEqual(3, sum(self.l))

    def test_exception(self):
        x = STMValue("i",0)
        try:
            with atomic():
                x.value += 1
                raise ValueError
            self.fail()
        except ValueError:
            pass
        with atomic():
            self.assertEqual(x.value, 0)
        

if __name__ == "__main__":
    unittest.main()
