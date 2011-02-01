import lockless
import multiprocessing
import time

class Philosopher(multiprocessing.Process):
    def __init__(self, name, lfork, rfork, ngrains):
        multiprocessing.Process.__init__(self)
        self.name = name
        self.lfork = lfork
        self.rfork = rfork
        self.count = ngrains
        self.conflicts = []

    @lockless.transactional()
    def eat(self):
        self.conflicts.append(lockless.conflicts())
        self.lfork.pickup()
        self.rfork.pickup()
        self.lfork.drop()
        self.rfork.drop()

    def run(self):
        start = time.time()
        while self.count > 0:
            self.eat()
            self.count -= 1
        print "%s completed in %s (%s conflicts)" % (self.name, time.time() - start, sum(self.conflicts))

class Fork(object):
    def __init__(self):
        self.available = lockless.STMValue("i", 1)

    @lockless.transactional()
    def pickup(self):
        if self.available.value == 0:
            lockless.retry()
        else:
            self.available.value = 0

    @lockless.transactional()
    def drop(self):
        assert self.available.value == 0
        self.available.value = 1

def main():
    n = 10
    forks = [Fork() for _ in xrange(n)]
    philosophers = []
    for i in xrange(0, n):
        p = Philosopher("Philosopher %d" % i, forks[i], forks[(i + 1) % len(forks)], 1000)
        philosophers.append(p)
        p.start()

    for p in philosophers:
        p.join()

if __name__ == "__main__":
    main()
