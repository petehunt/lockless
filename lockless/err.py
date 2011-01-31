class RetryTransaction(Exception):
    """ There was some sort of conflict """

class NoTransactionError(Exception):
    """ You did a transactional operation outside of a transaction """
