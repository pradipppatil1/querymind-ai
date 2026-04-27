from app.agents.sql_agent import SQLAgent
import pandas as pd

def main():
    agent = SQLAgent()
    print("Welcome to Wealth Banking Analytics")
    print("Type 'exit' to quit.")
    
    while True:
        query = input("\nAsk about your banking data: ")
        if query.lower() in ['exit', 'quit']:
            break
            
        result = agent.run(query)
        
        if result['error']:
            print(f"\n[ERROR]: {result['error']}")
            print(f"SQL attempted: {result['sql']}")
        else:
            print(f"\n[SQL]: {result['sql']}")
            if result['results']:
                print("\n[RESULTS]:")
                print(pd.DataFrame(result['results']))
            else:
                print("\nNo records found.")

if __name__ == "__main__":
    main()
