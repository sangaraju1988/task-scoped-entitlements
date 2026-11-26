"""Connection helpers."""
import psycopg
from . import config

def _superuser_password():
    import json, os
    p = os.path.join(config.DATA, ".secrets.json")
    return os.environ.get("TSE_PG_PASSWORD") or (json.load(open(p)).get("postgres") if os.path.exists(p) else None)

def connect(dbname, user=None, password=None, autocommit=True, **kw):
    if user is None or user == config.PG_SUPERUSER:
        password = password or _superuser_password()
    return psycopg.connect(host=config.PG_HOST, port=config.PG_PORT, dbname=dbname,
                           user=user or config.PG_SUPERUSER, password=password,
                           autocommit=autocommit, **kw)

def qident(name: str) -> str:
    """Quote an SQL identifier."""
    return '"' + name.replace('"', '""') + '"'

def qlit(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"
