This is Lockless, the STM library for Python.

STM is an easy consistency abstraction. It won't be the best solution to all problems, but
when share-nothing designs (message passing, mapreduce) come up short, try using
STM before rolling your own pessimistic locking solution.

By the way, be really, really sure that you want to use shared memory. Some people will tell you that you should exclusively use message-passing, but we all know that that is often unrealistic. When you DO need to share state, share it sparingly; transactions are not free.

What's the point?

To promote Python. The GIL is a pain point for most people and it's not going away anytime soon. Having STM baked into Python using multiprocessing along with the new
futures package should solidify it as a great tool for concurrency even with the GIL.

Things to keep in mind

1. This is my personal project right now and is not documented or thoroughly tested yet.
2. STM is optimistic. That means that transactions will often fail and need to be retried.
    That means you shouldn't modify external state (i.e. do I/O) in a transaction unless
    it is idempotent or repeats are okay.
3. STM is not a silver bullet. If there is a lot of contention transactions will conflict and
    perform badly. If this is the case, switch to pessimistic locking (roll-your-own),
    preferably using this recipe (which should be included in the stdlib): http://dabeaz.blogspot.com/2009/11/python-thread-deadlock-avoidance_20.html and this one: http://code.activestate.com/recipes/413393-multiple-reader-one-writer-mrow-resource-locking/

Outstanding issues:

1. When handling Retry, we poll multiple Events with a very low timeout. This stinks!
2. Naming conventions
3. Docs
4. Refactoring
5. See if starvation will ever occur and how to fix it
6. Microthreads
7. MROW and deadlock avoidance library
