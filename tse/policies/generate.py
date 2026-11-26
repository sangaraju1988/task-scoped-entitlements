"""Seeded, documented role-policy (entitlement E(u)) generation.

No released role policies were found for the RBAC text-to-SQL benchmark (Fei et al., PACMMOD 2026), so we
generate synthetic policies with the procedure below. Every number derived from these policies is labelled
"synthetic-policy" in the paper.

Per database, three roles:
  full        all columns, all rows.
  restricted  all rows; drops every column tagged sensitive by a fixed lexical tagger (below) plus a seeded
              random fraction `frac` of the remaining non-key columns.
  partition   drops sensitive columns; adds a row predicate on one table: the largest table having a text
              column with 2..20 distinct values; a seeded random subset of those values covering 30-70% of
              that table's rows is permitted (col IN (...)).
Parameters (frac, seed) are varied in the sensitivity analysis (L8).
"""
from __future__ import annotations
import hashlib, json, random, re
from ..db import connect, qident, qlit
from ..scope import Scope, TableScope

SENSITIVE_TOKENS = [
    "email", "e_mail", "phone", "telephone", "fax", "address", "street", "zip", "postal", "postcode",
    "birth", "dob", "birthday", "ssn", "social security", "salary", "income", "wage", "payment", "password",
    "credit", "card number", "iban", "account number", "latitude", "longitude", "lat", "lng", "ip address",
    "gender", "sex", "first name", "last name", "forename", "surname", "firstname", "lastname",
    "middle name", "nationality", "religion", "ethnic", "race_", "medical", "diagnosis",
]


def is_sensitive(col_name: str, desc: str = "") -> bool:
    text = (" " + re.sub(r"[_\-]", " ", (col_name + " " + (desc or "")).lower()) + " ")
    for tok in SENSITIVE_TOKENS:
        t = tok.replace("_", " ")
        if re.search(r"(?<![a-z])" + re.escape(t) + r"(?![a-z])", text):
            return True
    return False


def _rng(seed, db, role):
    h = int(hashlib.sha256(f"{seed}|{db}|{role}".encode()).hexdigest()[:12], 16)
    return random.Random(h)


def generate(sl, seed: int = 1, frac: float = 0.25):
    """Return {role_name: Scope} for one database."""
    all_cols = {t: set(tb.columns) for t, tb in sl.tables.items()}
    sens = {t: {c for c in cols if is_sensitive(c, sl.tables[t].columns[c].description)} for t, cols in all_cols.items()}
    roles = {}
    roles["full"] = Scope({t: TableScope(frozenset(c), None) for t, c in all_cols.items()})
    # restricted
    r = _rng(seed, sl.pgdb, "restricted")
    sc = {}
    for t in sorted(all_cols):
        keys = sl.key_columns(t)
        cand = sorted(all_cols[t] - sens[t] - keys)
        drop = set(r.sample(cand, int(round(frac * len(cand))))) if cand else set()
        keep = all_cols[t] - sens[t] - drop
        if keep:
            sc[t] = TableScope(frozenset(keep), None)
    roles["restricted"] = Scope(sc)
    # partition
    r = _rng(seed, sl.pgdb, "partition")
    sc = {t: TableScope(frozenset(all_cols[t] - sens[t]), None) for t in all_cols if all_cols[t] - sens[t]}
    pred_table = None
    with connect(sl.pgdb) as c:
        for t in sorted(sl.tables, key=lambda t: -sl.tables[t].rowcount):
            if t not in sc or sl.tables[t].rowcount < 10:
                continue
            for col in sorted(sc[t].columns):
                if sl.tables[t].columns[col].type not in ("text", "character varying"):
                    continue
                vals = c.execute(f"select {qident(col)}, count(*) from public.{qident(t)} where {qident(col)} is not null "
                                 f"group by 1 order by 2 desc, 1 limit 21").fetchall()
                if 2 <= len(vals) <= 20:
                    total = sl.tables[t].rowcount
                    for _ in range(50):
                        k = r.randint(1, len(vals) - 1)
                        chosen = r.sample(vals, k)
                        share = sum(v[1] for v in chosen) / total
                        if 0.3 <= share <= 0.7:
                            pred = f"{qident(col)} IN ({', '.join(qlit(v[0]) for v in sorted(chosen))})"
                            sc[t] = TableScope(sc[t].columns, pred)
                            pred_table = t
                            break
                if pred_table:
                    break
            if pred_table:
                break
    roles["partition"] = Scope(sc)
    return roles


def policies_to_json(roles):
    return {r: s.to_json() for r, s in roles.items()}
