class RetryTransaction(Exception):
    """ The transaction needs to be retried """

class ConflictError(RetryTransaction):
    """ There was a conflict between two transactions """

class NoTransactionError(Exception):
    """ You did a transactional operation outside of a transaction """
