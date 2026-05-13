from pydantic import BaseModel
from typing import Any
import time
from app.database.mysql_client import MySQLClient

class ExecutionResult(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    latency_ms: float
    error: str | None = None

class SQLExecutor:
    def __init__(self):
        self.db = MySQLClient()

    def execute(self, sql: str, mask_data: bool = True) -> ExecutionResult:
        start_time = time.time()
        try:
            results, error = self.db.execute_query(sql)
            latency_ms = (time.time() - start_time) * 1000
            
            if error:
                return ExecutionResult(columns=[], rows=[], row_count=0, latency_ms=latency_ms, error=error)
            
            # Apply HIPAA masking if requested
            if mask_data and results:
                from app.services.compliance_shield import ComplianceShield
                shield = ComplianceShield()
                results = shield.mask_rows(results)
            
            columns = list(results[0].keys()) if results else []
            return ExecutionResult(
                columns=columns,
                rows=results,
                row_count=len(results),
                latency_ms=latency_ms,
                error=None
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return ExecutionResult(columns=[], rows=[], row_count=0, latency_ms=latency_ms, error=str(e))

    def get_schema(self) -> dict:
        """Returns the schema in a format useful for SQL transpilers."""
        metadata = self.db.get_schema_metadata()
        # sqlglot format: {"table": {"column": "type"}, ...}
        return {
            table: {col: "TEXT" for col in details["columns"]} 
            for table, details in metadata.items()
        }
