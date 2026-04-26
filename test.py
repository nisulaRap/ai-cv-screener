from agents.parser_agent import run_parser_agent

results = run_parser_agent()

print("Parser Agent completed successfully!")
print(f"Total CVs parsed: {len(results)}")
print("Output saved to outputs/parsed.json")