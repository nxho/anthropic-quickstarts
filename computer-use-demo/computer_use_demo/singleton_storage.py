import threading

class SingletonStorage:
    _instance = None
    _lock = threading.Lock()  # Lock object for thread safety

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.data = {}
        return cls._instance

