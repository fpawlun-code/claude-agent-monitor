import os
from typing import Any, Dict

def delegate_with_approval(task: str, context: Dict[str, Any], auto_approve: bool = False) -> Dict[str, Any]:
    """
    Delegate a task with an approval-only mode.

    Args:
        task (str): The task to be delegated.
        context (Dict[str, Any]): Context information for the task.
        auto_approve (bool): Whether to automatically approve if confidence is high.

    Returns:
        Dict[str, Any]: A dictionary containing result, confidence, and explanation.
    """
    # Simulate some logic that generates a confidence score
    confidence = 0.86 if "high_confidence" in context else 0.75

    if auto_approve and confidence > 0.85:
        return {"result": "approved", "confidence": confidence, "explanation": "Auto-approved due to high confidence."}

    # Simulate approval process
    approval = input(f"Do you approve the task '{task}'? (y/n): ")
    if approval.lower() == 'y':
        return {"result": "approved", "confidence": confidence, "explanation": "Manually approved by user."}
    else:
        return {"result": "rejected", "confidence": confidence, "explanation": "Rejected by user."}
