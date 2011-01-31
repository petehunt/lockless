import random
from lockless import *
import multiprocessing

class BankAccount(object):
    def __init__(self, account_number, initial_balance):
        self.account_number = account_number
        self.balance = STMArray("i", 1) #STMValue("i", initial_balance)
        with atomic():
            self.balance[0] = initial_balance

@auto_retry()
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

@auto_retry()
def dump(cash, a, accts):
    with atomic():
        total_cash = cash * a
        for acct in accts:
            print(acct.balance[0])
            total_cash -= acct.balance[0]

    assert total_cash == 0, "Failed! %d" % total_cash

if __name__ == "__main__":
    main()
