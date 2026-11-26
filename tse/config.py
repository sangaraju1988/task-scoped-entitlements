"""Central configuration. All values can be overridden by environment variables."""
import os
PG_HOST = os.environ.get("TSE_PG_HOST", "localhost")
PG_PORT = int(os.environ.get("TSE_PG_PORT", "5433"))
PG_SUPERUSER = os.environ.get("TSE_PG_SUPERUSER", "postgres")   # used ONLY for setup (loading data, creating owner/broker roles)
BROKER_ROLE = "tse_broker"      # trusted broker: CREATEROLE, owns task schemas; NOT superuser
OWNER_ROLE = "tse_owner"        # owns all base tables
OLLAMA_URL = os.environ.get("TSE_OLLAMA_URL", "http://localhost:11500")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
RESULTS = os.path.join(ROOT, "eval", "results")
