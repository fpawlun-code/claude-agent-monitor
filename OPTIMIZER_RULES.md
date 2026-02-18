Here is the optimized workflow for Claude, minimizing token usage:

**claude_optimizer.py**
```python
import re
from rtx_api import RTX  # assume this is the API to delegate tasks

# Auto-responder templates
response_templates = {
    "done": "[DELEGATED] Task X â†’ RTX â†’ results.txt",
    "summary": "[DELEGATED] Summarize files A, B, C"
}

# Batch operation rules
batch_rules = [
    {"pattern": r"Read file (A|B|C)", "delegate_to_rtx": "Read files A, B, and C"}
]

# Documentation auto-generation rules
doc_generation_rules = [
    {"pattern": r"Create documentation for (.*)", "delegate_to_rtx": "Create documentation for {}"}
]

# Response compression rules
response_compression_rules = [
    {"pattern": r"Task (.*) complete", "response": "âś… Done. Results: [file]. Next?"}
]

# Smart delegation rules
smart_delegation_rules = [
    {"threshold": 200, "delegate_to_rtx": "Delegate task to RTX"}
]

def optimize_response(input_text):
    # Apply response compression rules
    for rule in response_compression_rules:
        if re.match(rule["pattern"], input_text):
            return rule["response"].format(input_text)

    # Apply auto-responder templates
    for template, response in response_templates.items():
        if re.match(template, input_text):
            return response

    # Delegate to RTX if task requires >200 tokens
    for rule in smart_delegation_rules:
        if int(rule["threshold"]) < len(input_text):
            return "âš… Delegated. Results: [file]. Next?"

    # Apply batch operation rules
    for rule in batch_rules:
        if re.match(rule["pattern"], input_text):
            return "[DELEGATED] {}".format(rule["delegate_to_rtx"])

    # Apply documentation auto-generation rules
    for rule in doc_generation_rules:
        if re.match(rule["pattern"], input_text):
            return "âš… Delegated. Results: [file]. Next?"

    # Default response if none of the above apply
    return "â˜€ Unknown task. Please clarify."

def pre_flight_check(input_text):
    # Check if task requires >200 tokens and delegate to RTX if so
    for rule in smart_delegation_rules:
        if int(rule["threshold"]) < len(input_text):
            return "âš… Delegated. Results: [file]. Next?"

    # Apply batch operation rules
    for rule in batch_rules:
        if re.match(rule["pattern"], input_text):
            return "[DELEGATED] {}".format(rule["delegate_to_rtx"])

    # Apply documentation auto-generation rules
    for rule in doc_generation_rules:
        if re.match(rule["pattern"], input_text):
            return "âš… Delegated. Results: [file]. Next?"

    # Default response if none of the above apply
    return "â˜€ Unknown task. Please clarify."
