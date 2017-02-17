# errors.py
## custom error classes

class ThreadError(Exception):
    """
    raise whenever a thread is missing or invalid
    """
    pass

class OrderError(Exception):
    """
    raise for invalid or flawed orders
    """
    pass