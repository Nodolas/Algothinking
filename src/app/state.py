"""Global app state: runner, clob, history_store. Set in lifespan, read in routes."""
_runner = None
_clob = None
_history_store = None


def get_runner():
    return _runner


def set_runner(r):
    global _runner
    _runner = r


def get_clob():
    return _clob


def set_clob(c):
    global _clob
    _clob = c


def get_history_store():
    return _history_store


def set_history_store(store):
    global _history_store
    _history_store = store
