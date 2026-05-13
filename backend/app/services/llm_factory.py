import os
from langchain_openai import ChatOpenAI

def get_llm(temperature=0.0):
    # Use OpenAI for local testing as requested.
    # AWS Bedrock can be enabled via environment variables for production.
    use_bedrock = os.getenv("USE_AWS_BEDROCK", "false").lower() == "true"
    
    if use_bedrock:
        from langchain_aws import ChatBedrock
        return ChatBedrock(
            model_id="openai.gpt-oss-120b-1:0",
            region_name=os.getenv("DEFAULT_AWS_REGION", "us-east-1"),
            model_kwargs={"temperature": temperature}
        )
        
    return ChatOpenAI(model="gpt-4o", temperature=temperature)
