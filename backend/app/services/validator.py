import sqlglot
from pydantic import BaseModel

class ValidationResult(BaseModel):
    valid: bool
    sanitized_sql: str
    errors: list[str]

class SQLValidator:
    def __init__(self):
        self.destructive_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE", "ALTER"]
        
    def validate(self, sql: str, allow_destructive: bool = False, max_limit: int = 100, allowed_table_prefixes: list[str] = None) -> ValidationResult:
        errors = []
        sanitized_sql = sql
        
        # 1. Guardrails
        if not allow_destructive:
            upper_sql = sql.upper()
            for kw in self.destructive_keywords:
                if kw in upper_sql:
                    errors.append(f"Destructive operation '{kw}' is blocked by guardrails.")
                    
        # 2. Syntax Check & Formatting
        try:
            parsed = sqlglot.parse_one(sql)
            
            # Scope Restriction Check
            if allowed_table_prefixes:
                for table in parsed.find_all(sqlglot.exp.Table):
                    table_name = table.name.lower()
                    if not any(table_name.startswith(p.lower()) for p in allowed_table_prefixes):
                        errors.append(f"Table access denied: '{table_name}'. Allowed prefixes: {allowed_table_prefixes}")
            
            # 3. Append LIMIT if missing and no syntax errors
            if not parsed.args.get("limit"):
                sanitized_sql = f"{sql.strip().rstrip(';')} LIMIT {max_limit};"
            else:
                sanitized_sql = sqlglot.transpile(sql, write="mysql")[0]
                
        except Exception as e:
            errors.append(f"SQL Syntax Error: {str(e)}")
            
        return ValidationResult(
            valid=len(errors) == 0,
            sanitized_sql=sanitized_sql,
            errors=errors
        )
