"""Production ASGI entrypoint with mandatory operator authorization."""
from main import app as application
from rhns_middleware import OperatorGuard

app = OperatorGuard(application)
