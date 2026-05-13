import re
from typing import Any

class ComplianceShield:
    def __init__(self, sensitive_columns: list[str] = None):
        # Default sensitive columns based on the Hospital Billing domain
        self.sensitive_columns = sensitive_columns or [
            "first_name", "last_name", "dob", "phone", "email", 
            "address", "ssn", "patient_name", "provider_name"
        ]
        
        # Mapping of column patterns to masking functions
        self.masking_rules = {
            r".*name.*": self._mask_name,
            r".*dob.*|.*date_of_birth.*": self._mask_date,
            r".*phone.*": self._mask_phone,
            r".*email.*": self._mask_email,
            r".*ssn.*": self._mask_sensitive_id,
            r".*address.*|.*city.*": self._mask_location
        }

    def mask_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Applies masking to sensitive columns in a list of result rows."""
        if not rows:
            return rows
            
        masked_rows = []
        for row in rows:
            new_row = {}
            for col, val in row.items():
                masked_val = self._apply_masking(col, val)
                new_row[col] = masked_val
            masked_rows.append(new_row)
            
        return masked_rows

    def _apply_masking(self, column_name: str, value: Any) -> Any:
        if value is None:
            return None
            
        col_lower = column_name.lower()
        
        # Check if the column is explicitly marked as sensitive or matches a pattern
        for pattern, mask_func in self.masking_rules.items():
            if re.match(pattern, col_lower):
                return mask_func(str(value))
                
        return value

    def _mask_name(self, val: str) -> str:
        if not val or len(val) < 2:
            return "***"
        return f"{val[0]}***{val[-1]}" if len(val) > 2 else f"{val[0]}***"

    def _mask_date(self, val: str) -> str:
        # Mask day and month, keep year for analytical utility (common in HIPAA De-identification)
        # Assumes YYYY-MM-DD
        if len(val) >= 4:
            return f"{val[:4]}-XX-XX"
        return "XXXX-XX-XX"

    def _mask_phone(self, val: str) -> str:
        if len(val) >= 4:
            return f"XXX-XXX-{val[-4:]}"
        return "XXX-XXX-XXXX"

    def _mask_email(self, val: str) -> str:
        if "@" in val:
            parts = val.split("@")
            return f"{parts[0][0]}***@{parts[1]}"
        return "***@***.***"

    def _mask_sensitive_id(self, val: str) -> str:
        return "[REDACTED]"

    def _mask_location(self, val: str) -> str:
        # Keep it very generic
        return "[MASKED LOCATION]"
