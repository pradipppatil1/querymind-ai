from pydantic import BaseModel, Field
from .llm_factory import get_llm
from app.core.observability import get_langfuse_callback

class SQLGenerationResult(BaseModel):
    sql: str = Field(description="The generated SQL query.")
    explanation: str = Field(description="A brief explanation of the SQL logic.")

class SQLGenerator:
    def __init__(self):
        self.llm = get_llm(temperature=0.0).with_structured_output(SQLGenerationResult)

    def generate(self, query: str, schema_context: str, resolved_schema: dict, examples: list[dict], error_message: str = None, history: list[dict] = None) -> SQLGenerationResult:
        examples_text = "\n".join([f"Q: {ex['question']}\nSQL: {ex['sql']}" for ex in examples])
        
        error_context = f"\n\nPREVIOUS ERROR (Fix this): {error_message}" if error_message else ""
        
        history_text = ""
        if history:
            history_text = "### Recent Conversation History:\n"
            for msg in history[-3:]:
                role = "User" if msg["role"] == "user" else "AI"
                history_text += f"{role}: {msg.get('content', '')}\n"
            history_text += "\n"

        prompt = f"""
        You are a world-class SQL Expert for a Hospital Billing system. 
        Your task is to generate a precise, read-only MySQL SELECT statement that answers the user's question.

        ### Database Schema Context:
        {schema_context}

        ### Guidance:
        1. **Joins**: Use the Primary Key (PK) and Foreign Key (FK) relationships defined in the schema. Always join on IDs.
        2. **Enums & Values**: Use the exact values mentioned in the schema descriptions (e.g., status must be 'Paid', 'Pending', or 'Overdue'). Do not guess.
        3. **Precision**: Use the specific tables/columns provided in the 'Resolved Schema' below.
        4. **Aliases**: Do not use column aliases (AS) unless specifically required for clarity in calculations (like SUM/AVG).
        5. **Dialect**: Generate standard MySQL syntax.
        6. **Examples**: Use the provided few-shot examples as structural guidance for how to join and filter.

        ### Resolved Schema (Use these!):
        Tables: {resolved_schema.get('resolved_tables', [])}
        Columns: {resolved_schema.get('resolved_columns', [])}

        ### Few-Shot Examples:
        {examples_text}

        {history_text}
        ### Current User Question:
        "{query}"
        {error_context}

        Output the SQL query and a brief explanation.
        """
        cb = get_langfuse_callback()
        return self.llm.invoke(prompt, config={"callbacks": [cb]} if cb else {})
