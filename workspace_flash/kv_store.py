import time
import json

class KVStore:
    def __init__(self):
        self.store = {}
        self.transactions = []

    def set(self, key, value, ttl=None):
        """Set the value for a given key with an optional TTL (in seconds)."""
        expiry_time = time.time() + ttl if ttl is not None else None
        entry = (value, expiry_time)
        if self.transactions:
            self.transactions[-1][key] = entry
        else:
            self.store[key] = entry

    def get(self, key):
        """Retrieve the value for a given key, considering transactions and TTL."""
        for tx in reversed(self.transactions):
            if key in tx:
                entry = tx[key]
                if entry is None:  # Marked as deleted
                    return None
                val, expiry = entry
                if expiry is None or expiry > time.time():
                    return val
                return None

        if key in self.store:
            val, expiry = self.store[key]
            if expiry is None or expiry > time.time():
                return val
            del self.store[key]
        return None

    def delete(self, key):
        """Delete a key from the store or the current transaction."""
        if self.transactions:
            self.transactions[-1][key] = None  # Use None to mark deletion
        else:
            if key in self.store:
                del self.store[key]

    def begin(self):
        """Start a new transaction."""
        self.transactions.append({})

    def commit(self):
        """Commit the current transaction."""
        if not self.transactions:
            return
        changes = self.transactions.pop()
        if self.transactions:
            self.transactions[-1].update(changes)
        else:
            for k, v in changes.items():
                if v is None:
                    if k in self.store:
                        del self.store[k]
                else:
                    self.store[k] = v

    def rollback(self):
        """Roll back the current transaction."""
        if self.transactions:
            self.transactions.pop()

    def save_to_file(self, filename):
        """Persist the store data to a JSON file."""
        with open(filename, 'w') as f:
            json.dump(self.store, f)

    def load_from_file(self, filename):
        """Load store data from a JSON file."""
        with open(filename, 'r') as f:
            self.store = json.load(f)
