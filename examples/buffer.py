import lockless

class Buffer(object):
    def __init__(self, *args, **kwargs):
        self.obj = lockless.STMObject([], *args, **kwargs)
        
    @lockless.transactional()
    def put(self, item):
        self.obj.value.append(item)

    @lockless.transactional()
    def get(self):
        if len(self.obj.value) == 0:
            lockless.retry()
        else:
            return self.obj.value.pop(0)

###
import multiprocessing
import time

def sender(b):
    for i in xrange(0, 10):
        print "sending %d" % i
        b.put(i)

@lockless.auto_retry()
def receive(n, b, flag):
    with lockless.atomic():
        x = b.get()
        flag.value = max(flag.value, x)
    print "%d received %d" % (n,x)

def receiver(n, b, flag):
    while True:
       receive(n,b, flag)
       time.sleep(1.0)

@lockless.transactional()
def wait_till_complete(v, n):
    if v.value != n:
        lockless.retry()

def main():
    b = Buffer()
    flag = lockless.STMValue("i", 0)

    s = multiprocessing.Process(target=sender, args=(b,))
    s.start()

    for i in xrange(0,5):
        multiprocessing.Process(target=receiver, args=(i,b, flag)).start()

    wait_till_complete(flag, 9) # max msg received

if __name__ == "__main__":
    main()
