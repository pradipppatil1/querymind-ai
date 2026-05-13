"""
Dialect Transpiler Service
--------------------------
Wraps sqlglot to provide multi-dialect SQL transpilation.

Extensibility: Available dialects are auto-discovered from the installed
sqlglot version at runtime. Upgrading sqlglot automatically exposes new
dialects in the Admin UI with zero code changes.
"""
import sqlglot
import sqlglot.dialects

# Dialects to hide from the Admin UI (too experimental or non-standard)
DIALECT_BLOCKLIST = {
    "",         # empty key
    "dialect",  # base class
}

# Friendly display names override (sqlglot class names can be verbose)
DIALECT_LABELS: dict[str, str] = {
    "mysql":     "MySQL",
    "postgres":  "PostgreSQL",
    "snowflake": "Snowflake",
    "bigquery":  "BigQuery",
    "duckdb":    "DuckDB",
    "spark":     "Apache Spark SQL",
    "tsql":      "T-SQL (SQL Server)",
    "sqlite":    "SQLite",
    "trino":     "Trino",
    "athena":    "Amazon Athena",
    "clickhouse":"ClickHouse",
    "hive":      "Apache Hive",
    "presto":    "PrestoDB",
    "redshift":  "Amazon Redshift",
    "databricks":"Databricks",
}


def get_supported_dialects() -> dict[str, str]:
    """
    Auto-discovers all SQL dialects supported by the installed sqlglot version.
    MySQL is excluded (it's the base default, always ON).
    Returns: dict of {dialect_key: display_label}
    """
    dialects: dict[str, str] = {}

    for name, cls in sqlglot.dialects.Dialect.classes.items():
        if not name or name in DIALECT_BLOCKLIST or name == "mysql":
            continue
        # Use our friendly label if available, otherwise derive from class name
        label = DIALECT_LABELS.get(name)
        if not label:
            label = cls.__name__.replace("Dialect", "").strip() or name.title()
        dialects[name] = label

    return dict(sorted(dialects.items(), key=lambda x: x[1]))


def _expand_group_by(expression: sqlglot.exp.Expression) -> sqlglot.exp.Expression:
    """
    Ensures all non-aggregated columns in SELECT are present in GROUP BY.
    Required for strict ANSI-compliant dialects like PostgreSQL.
    """
    from sqlglot import exp
    
    # Only act if there is already a GROUP BY clause
    if not expression.args.get("group"):
        return expression
        
    group_expressions = expression.args["group"].expressions
    # Use canonical SQL strings to track what's already grouped
    group_texts = {g.sql() for g in group_expressions}
    
    for select in expression.selects:
        # Get the underlying expression (strip alias)
        inner = select.this if isinstance(select, exp.Alias) else select
        
        # If the expression contains no aggregate functions, it must be in GROUP BY
        if not inner.find(exp.AggFunc):
            if inner.sql() not in group_texts:
                expression.group_by(inner, append=True, copy=False)
                group_texts.add(inner.sql())
                
    return expression


def transpile_sql(sql: str, target_dialect: str, schema: dict = None) -> str:
    """
    Transpile MySQL SQL to a target dialect using sqlglot.
    Uses optimization passes to ensure aliases in HAVING/GROUP BY are expanded
    and missing columns are added to GROUP BY for ANSI compliance.
    """
    if not sql or target_dialect == "mysql":
        return sql
        
    try:
        # Parse the MySQL SQL into an expression tree
        expression = sqlglot.parse_one(sql, read="mysql")
        
        # 1. Apply qualification and unaliasing
        # This expands SELECT aliases used in HAVING/GROUP BY/ORDER BY
        from sqlglot.optimizer.qualify import qualify
        try:
            expression = qualify(expression, schema=schema, expand_alias_refs=True)
        except Exception:
            pass

        # 2. Expand GROUP BY for strict dialects (Postgres, Snowflake, etc.)
        # We do this for all non-mysql dialects to be safe
        try:
            expression = _expand_group_by(expression)
        except Exception:
            pass

        # Transpile to the target dialect
        return expression.sql(dialect=target_dialect, pretty=True)
    except Exception:
        # Final fallback: just try basic transpilation if parsing failed
        try:
            result = sqlglot.transpile(sql, read="mysql", write=target_dialect, pretty=True)
            return result[0] if result else sql
        except Exception:
            return sql


def transpile_all(sql: str, dialects: list[str], schema: dict = None) -> dict[str, str]:
    """
    Transpile a MySQL SQL query into all requested dialects at once.
    """
    versions: dict[str, str] = {}
    for dialect in dialects:
        versions[dialect] = transpile_sql(sql, dialect, schema=schema)
    return versions
