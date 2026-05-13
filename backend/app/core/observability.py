import os
from langfuse.langchain import CallbackHandler
from functools import lru_cache

@lru_cache()
def get_langfuse_callback():
    """
    Initializes and returns a Langfuse Callback Handler if environment variables are set.
    """
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    base_url = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")

    if public_key and secret_key:
        print(f"📡 Langfuse Tracing Initialized (Host: {base_url})")
        # In modern Langfuse, the handler picks up env vars automatically
        return CallbackHandler()
    
    return None
