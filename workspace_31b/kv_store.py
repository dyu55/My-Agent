import time

class KVStore:
    def __init__(self):
        self.store = {}
        self.buffer = None
        self._tombstone = object()

    def begin(self):
        """Starts a new transaction."""
        self.buffer = {}

    def commit(self):
        """Commits the current transaction, applying changes to the main store."""
        if self.buffer is None:
            raise Exception("No active transaction to commit.")
        
        for key, value in self.buffer.items():
            if value is self._tombstone:
                self.store.pop(key, None)
            else:
                self.store[key] = value
        self.buffer = None

    def rollback(self):
        """Rolls back the current transaction, discarding all changes."""
        if self.buffer is None:
            raise Exception("No active transaction to rollback.")
        self.buffer = None

    def set(self, key, value, ttl=None):
        """Sets the value for the given key with an optional TTL in seconds."""
        expire_at = time.time() + ttl if ttl is not None else None
        entry = (value, expire_at)
        if self.buffer is not None:
            self.buffer[key] = entry
        else:
            self.store[key] = entry

    def get(self, key):
        """Retrieves the value for the given key. Returns None if key does not exist or has expired."""
        if self.buffer is not None and key in self.buffer:
            entry = self.buffer[key]
            if entry is self._tombstone:
                return None
            return self._get_value_if_not_expired(entry)

        if key in self.store:
            return self._get_value_if_not_expired(self.store[key])
        
        return None

    def delete(self, key):
        """Deletes the given key from the store."""
        if self.buffer is not None:
            self.buffer[key] = self._tombstone
        else:
            self.store.pop(key, None)

    def _get_value_if_not_expired(self, entry):
        """Helper to return value if not expired, else None."""
        value, expire_at = entry
        if expire_at is not None and time.time() > expire_at:
            return None
        return value
