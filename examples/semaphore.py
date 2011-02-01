import lockless

class Semaphore(object):
    def __init__(self, value=1):
        self.value = lockless.STMValue("i", value)
        
    @lockless.transactional()
    def acquire(self, blocking=True):
        if self.value.value > 0:
            self.value.value -= 1
            return True
        else:
            if blocking:
                lockless.retry()
            else:
                return False
    
    @lockless.transactional()
    def release(self):
        self.value.value += 1

###

import time
import multiprocessing

def proc(s, n):
    print "acquiring %r" % n
    s.acquire()
    print "acquired %r" % n
    time.sleep(1)
    print "releasing %r" % n
    s.release()

# test
def main():
    s = Semaphore(3)
    ps = []
    for i in xrange(0, 5):
        p = multiprocessing.Process(target=proc, args=(s,i))
        p.start()
        ps.append(p)

    for p in ps:
        p.join()

if __name__ == "__main__":
    main()

