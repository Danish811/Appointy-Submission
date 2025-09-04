import time
from collections import defaultdict

REQUEST_COUNTERS = defaultdict(list)
LIFE_TIME = 60  # seconds window

def record_request(module: str):
    now = time.time()
    REQUEST_COUNTERS[module].append(now)
    _cleanup(module)

def get_rpm(module: str) -> int:
    _cleanup(module)
    return len(REQUEST_COUNTERS[module])

def _cleanup(module: str):
    now = time.time()
    cutoff = now - LIFE_TIME
    REQUEST_COUNTERS[module] = [t for t in REQUEST_COUNTERS[module] if t >= cutoff]
