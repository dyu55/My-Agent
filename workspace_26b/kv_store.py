import time

class KVStore:
    def __init__(self):
        """Initialize the Key-Value store with an empty dictionary and a transaction stack."""
        self.store = {}
        self.transactions = []
        self._deleted = object()  # Sentinel for deleted keys in transactions

    def _get_current_scope(self):
        """Return the current active transaction scope or the main store."""
        return self.transactions[-1] if self.transactions else self.store

    def set(self, key, value, ttl=None):
        """
        Set the value for the given key.
        :param key: The key to set.
        :param value: The value to store.
        :param ttl: Time-to-Live in seconds. If None, the key does not expire.
        """
        expiry = time.time() + ttl if ttl is not None else None
        scope = self._get_current_scope()
        scope[key] = (value, expiry)

    def get(self, key):
        """
        Retrieve the value associated with the given key. Returns None if key does not exist or is expired.
        """
        # Search transactions from the most recent to the oldest
        for i in range(len(self.transactions) - 1, -1, -1):
            scope = self.transactions[i]
            if key in scope:
                val, expiry = scope[key]
                if val is self._deleted:
                    return None
                if expiry and time.time() > expiry:
                    del scope[key]  # Clean up expired key in transaction
                    return None
                return val

        # Search the main store
        if key in self.store:
            val, expiry = self.store[key]
            if expiry and time.time() > expiry:
                del self.store[key]
                return None
            return val
        return None

    def delete(self, key):
        """Delete the given key from the store or mark it as deleted in the current transaction."""
        if self.transactions:
            self.transactions[-1][key] = (self._deleted, None)
        else:
            self.store.pop(key, None)

    def begin(self):
        """Start a new transaction by pushing a new scope onto the stack."""
        self.transactions.append({})

    def commit(self):
        """Commit the current transaction by merging its changes into the previous scope or main store."""
        if not self.transactions:
            return

        changes = self.transactions.pop()
        if not self.transactions:
            # Merge into main store
            for key, (val, expiry) in changes.items():
                if val is self._deleted:
                    self.store.pop(key, None)
                else:
                    self.store[key] = (val, expiry)
        else:
            # Merge into the previous transaction level
            target = self.transactions[-1]
            for key, (val, expiry) in changes.items():
                target[key] = (val, expiry)

    def rollback(self):
        """Roll back the current transaction by popping the top scope from the stack."""
        if self.transactions:
            self.transactions.pop()