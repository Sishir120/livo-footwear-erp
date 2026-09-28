"""
In-process concurrency mutex for stock movements.
Works in tandem with PostgreSQL with_for_update() row-level locking to guarantee
thread-safe serialized balance checks and commit boundaries across both
local SQLite test runners and multi-worker production environments.
"""
import threading
from collections import defaultdict

_product_locks = defaultdict(threading.Lock)
_meta_lock = threading.Lock()

def get_stock_mutex(company_id: int, product_id: int) -> threading.Lock:
    """Returns a mutex dedicated to a specific product variant within a company tenant."""
    with _meta_lock:
        return _product_locks[(company_id, product_id)]
