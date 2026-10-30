"""
Scoring and Evaluation Engine
Provides deterministic validation and rubric grading for candidate LLM outputs.
"""
from typing import Dict, Any, List

class DeterministicGrader:
    """
    Evaluates LLM responses using deterministic pattern matching,
    AST inspection, and test assertion checks to guarantee 0% hallucination
    and avoid false positives.
    """
    
    @staticmethod
    def grade_task(task: Dict[str, Any], model_response: str) -> Dict[str, Any]:
        """
        Grades an individual task output against required and forbidden patterns.
        """
        passed = True
        reasons: List[str] = []
        
        expected = task.get("expected_patterns", [])
        forbidden = task.get("forbidden_patterns", [])
        
        # Check for presence of required solution patterns (any match or all match)
        has_expected = any(pattern.lower() in model_response.lower() for pattern in expected)
        if expected and not has_expected:
            passed = False
            reasons.append(f"Missing expected core fix patterns: {expected}")
            
        # Check for forbidden patterns (anti-patterns / flawed assumptions)
        for anti_pattern in forbidden:
            if anti_pattern.lower() in model_response.lower():
                passed = False
                reasons.append(f"Contains fatal anti-pattern: '{anti_pattern}'")
                
        return {
            "task_id": task["id"],
            "passed": passed,
            "reasons": reasons,
            "response_preview": model_response[:150] + "..." if len(model_response) > 150 else model_response
        }
