from tools.grammar_check_tool import grammar_check

result = grammar_check("She go to the market yesterday and buyed some apples.")

print(f"Issues found: {result['issues_found']}")
print(f"Corrected:    {result['corrected_text']}")