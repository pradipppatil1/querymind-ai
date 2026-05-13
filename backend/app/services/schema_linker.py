from pydantic import BaseModel, Field
from .llm_factory import get_llm

class ResolvedSchema(BaseModel):
    resolved_tables: list[str]
    resolved_columns: list[str]
    ambiguities: list[str] = Field(default_factory=list, description="List of any ambiguous terms requiring user clarification.")

class SchemaLinker:
    def __init__(self):
        self.llm = get_llm(temperature=0.0).with_structured_output(ResolvedSchema)

    def link(self, query: str, tables_mentioned: list[str], columns_mentioned: list[str], schema_context: str) -> ResolvedSchema:
        prompt = f"""
        Given the user query, and the database schema context, map the natural language entities 
        to the exact table and column names in the database.
        
        If a term could refer to multiple columns and it's impossible to tell which one is meant 
        (e.g., "cost" could be procedures.cost OR billing_records.total_amount), flag it in 'ambiguities'.
        
        User Query: "{query}"
        Potential Tables: {tables_mentioned}
        Potential Columns: {columns_mentioned}
        
        Database Schema Context:
        {schema_context}
        """
        return self.llm.invoke(prompt)
