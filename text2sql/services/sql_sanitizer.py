"""
Sanitize and validate SQL before execution.

Rules enforced:
 - Only a single statement allowed (no multiple semicolons).
 - Must begin with SELECT (after whitespace / parentheses).
 - Blocked keywords like INSERT/UPDATE/DELETE/CREATE/DROP/ALTER/GRANT.
 - Block access to system catalogs (pg_catalog, information_schema).
 - Enforce max rows by injecting LIMIT if none present.
"""
import re
from django.db import connection

BLOCKED_TOKENS = [
    r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b", r"\bDROP\b",
    r"\bCREATE\b", r"\bALTER\b", r"\bTRUNCATE\b", r"\bREVOKE\b",
    r"\bGRANT\b", r"\bVACUUM\b", r"\bANALYZE\b", r"\bLOCK\b",
    r"\bSET\b", r"\bSHOW\b", r"\bCOMMENT\b"
]
SYSTEM_TABLES = [r"pg_catalog", r"information_schema"]

SELECT_RE = re.compile(r"^\s*(\(*\s*SELECT\b)", re.IGNORECASE)
SEMICOLON_RE = re.compile(r";")
LIMIT_RE = re.compile(r"\bLIMIT\s+\d+\b", re.IGNORECASE)


class SQLSanitizerError(Exception):
    pass


def basic_sanitize_and_enforce(sql: str, max_rows: int = 1000) -> str:
    if not sql or not sql.strip():
        raise SQLSanitizerError("Empty SQL returned from model.")

    cleaned = sql.strip()

    # Reject multiple statements or any semicolon usage
    if SEMICOLON_RE.search(cleaned):
        # allow a trailing semicolon only (but prefer to reject)
        # Safer to reject if there's any semicolon
        raise SQLSanitizerError("Multiple statements or semicolons not allowed.")

    # Block system tables access
    for p in SYSTEM_TABLES:
        if re.search(rf"\b{p}\b", cleaned, re.IGNORECASE):
            raise SQLSanitizerError(
                "Access to system catalogs is not allowed."
            )

    # Block disallowed tokens
    for token in BLOCKED_TOKENS:
        if re.search(token, cleaned, re.IGNORECASE):
            raise SQLSanitizerError(
                f"Disallowed SQL operation detected: {token}"
            )

    # Must start with SELECT (allow leading parentheses for CTE or subquery)
    if not SELECT_RE.match(cleaned):
        # It might be a CTE "WITH ... SELECT" — allow WITH as well
        if not re.match(r"^\s*WITH\b", cleaned, re.IGNORECASE):
            raise SQLSanitizerError("Only SELECT queries are allowed.")

    # Enforce LIMIT
    if not LIMIT_RE.search(cleaned):
        cleaned = f"{cleaned.rstrip()} LIMIT {max_rows}"

    return cleaned


def execute_sql(sql: str, row_limit=1000):
    sql = basic_sanitize_and_enforce(sql)
    with connection.cursor() as cursor:
        cursor.execute(sql)
        result = cursor.fetchmany(row_limit)
    return result