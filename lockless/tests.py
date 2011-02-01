import random
import multiprocessing
import unittest

from lockless import auto_retry, STMValue, atomic, retry

class BankAccount(object):
    def __init__(self, account_number, initial_balance):
        self.account_number = account_number
        self.balance = STMValue("i", initial_balance)

@auto_retry()
def do_trade(accts, count):
    acct1 = acct2 = random.choice(accts)
    while acct1 == acct2:
        acct2 = random.choice(accts)

    # transactify
    with atomic():
        try:
            amt = random.randint(0, acct1.balance.value-1)
        except ValueError:
            retry()

        acct1.balance.value -= amt
        acct2.balance.value += amt

def trader(accts, count):
    for _ in range(0, count):
        do_trade(accts, count)

class TestBasic(unittest.TestCase):
    def test_main(self):
        n = 10
        c = 100
        a = 10
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

if __name__ == "__main__":
    unittest.main()
