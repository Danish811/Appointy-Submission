import os

MODE = os.getenv("MODE", "MONOLITH")  # or "MICROSERVICE"

LINKS_URL = os.getenv("LINKS_URL", "http://localhost:8001")
REDIRECTOR_URL = os.getenv("REDIRECTOR_URL", "http://localhost:8002")
ANALYTICS_URL = os.getenv("ANALYTICS_URL", "http://localhost:8003")
