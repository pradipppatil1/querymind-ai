from pydantic import BaseModel, Field
from typing import Any
from .llm_factory import get_llm
from app.core.observability import get_langfuse_callback

class NLSummaryResult(BaseModel):
    """Only ask the LLM for the nl_summary. The table is injected separately."""
    nl_summary: str = Field(description="A 1-2 sentence natural language summary of the results.")

class FormattedResult(BaseModel):
    table: list[dict[str, Any]]
    nl_summary: str

class ResultFormatter:
    def __init__(self):
        # Use method="function_calling" to avoid strict JSON schema issues with dict[str, Any]
        self.llm = get_llm(temperature=0.0).with_structured_output(NLSummaryResult, method="function_calling")

    def format(self, user_query: str, execution_result) -> FormattedResult:
        if execution_result.error:
            return FormattedResult(
                table=[],
                nl_summary=f"I couldn't retrieve the data due to an error: {execution_result.error}"
            )
            
        if execution_result.row_count == 0:
            return FormattedResult(
                table=[],
                nl_summary="The query executed successfully, but no records were found."
            )
            
        # We only pass a sample of the data to the LLM to avoid token limits
        data_sample = execution_result.rows[:10]
        
        prompt = f"""
        USER QUESTION: "{user_query}"
        
        DATABASE RESULTS ({execution_result.row_count} total rows):
        {data_sample}
        
        TASK:
        Provide a 1-2 sentence natural language summary of these results to answer the user's question.
        
        STRICT GROUNDING RULES:
        1. ONLY use the information provided in the DATABASE RESULTS above.
        2. Do NOT mention any data points or counts that are not explicitly present in the results.
        3. If the results are empty or do not contain enough information, say so.
        4. Focus on the core answer requested by the user.
        """
        
        cb = get_langfuse_callback()
        response = self.llm.invoke(prompt, config={"callbacks": [cb]} if cb else {})
        
        # Return the full dataset to the UI (not just the LLM sample)
        return FormattedResult(
            table=execution_result.rows,
            nl_summary=response.nl_summary
        )
