import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Add project root
sys.path.append(os.getcwd())

from ragas import evaluate
from datasets import Dataset
from openai import OpenAI
from ragas.llms import llm_factory

client = OpenAI()
llm = llm_factory("gpt-4o-mini", client=client)

# Dummy data
data = {
    "question": ["Test?"],
    "answer": ["Yes."],
    "contexts": [["Context."]],
    "ground_truth": ["SELECT 1;"]
}
dataset = Dataset.from_dict(data)

print("--- Testing Strategy 1: ragas.metrics (lowercase instances) ---")
try:
    from ragas.metrics import context_precision, faithfulness
    res = evaluate(dataset, metrics=[context_precision, faithfulness], llm=llm)
    print("Strategy 1 SUCCESS!")
except Exception as e:
    print(f"Strategy 1 FAILED: {e}")

print("\n--- Testing Strategy 2: ragas.metrics.collections (Capitalized classes) ---")
try:
    from ragas.metrics.collections import ContextPrecision, Faithfulness
    # Try initializing with LLM
    cp = ContextPrecision(llm=llm)
    f = Faithfulness(llm=llm)
    res = evaluate(dataset, metrics=[cp, f], llm=llm)
    print("Strategy 2 SUCCESS!")
except Exception as e:
    print(f"Strategy 2 FAILED: {e}")

print("\n--- Testing Strategy 3: ragas.metrics (Capitalized classes) ---")
try:
    from ragas.metrics import ContextPrecision, Faithfulness
    cp = ContextPrecision(llm=llm)
    f = Faithfulness(llm=llm)
    res = evaluate(dataset, metrics=[cp, f], llm=llm)
    print("Strategy 3 SUCCESS!")
except Exception as e:
    print(f"Strategy 3 FAILED: {e}")
