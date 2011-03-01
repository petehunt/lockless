class TransactionError(Exception):
    pass

class RetryTransaction(TransactionError):
    """ The transaction needs to be retried for some reason.
    Wait for value to change. """
    def __init__(self):
        from . import core
        TransactionError.__init__(self)
        core.Transaction.current().wait_for_update()

class ConflictError(TransactionError):
    """ There was a conflict between two transactions """

class NoTransactionError(TransactionError):
    """ You did a transactional operation outside of a transaction """

