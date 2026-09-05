"""
Centralized Tool Executor (Choke Point)
Enforces tool-contract discipline, structured inputs/outputs, centralized logging,
status reporting (success/failure), and immediate error surfacing per Lab 2 specifications.
"""

from typing import Dict, Any, List, Callable, Optional
from app.tools.calendar_tool import read_calendar
from app.tools.invitee_tool import read_invitee_preferences
from app.tools.calculator_tool import calculate_meeting_slots, validate_slot

TOOLS: Dict[str, Callable[..., Dict[str, Any]]] = {
    "read_calendar": read_calendar,
    "read_invitee_preferences": read_invitee_preferences,
    "calculate_meeting_slots": calculate_meeting_slots,
    "validate_slot": validate_slot,
}


class ToolExecutor:
    """
    Centralized choke point through which every tool call passes.
    Logs tool name, reason, inputs, outputs, success status, and error messages.
    """

    def __init__(self):
        self.trace: List[Dict[str, Any]] = []

    def execute(self, tool_name: str, reason: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a tool by name with explicit reason and keyword arguments.
        
        Args:
            tool_name: Registered tool identifier
            reason: Justification/rationale explaining why the planner chose this tool
            **kwargs: Structured parameters passed to the tool
            
        Returns:
            Structured dictionary output from the tool
            
        Raises:
            ValueError: If tool_name is not registered
            RuntimeError: If the tool output contains an 'error' key
        """
        if tool_name not in TOOLS:
            err_msg = f"Unknown tool: '{tool_name}'. Available tools: {list(TOOLS.keys())}"
            self.trace.append({
                "tool": tool_name,
                "reason": reason,
                "input": kwargs,
                "output": {"error": err_msg},
                "success": False,
                "error": err_msg,
            })
            raise ValueError(err_msg)
        
        tool_fn = TOOLS[tool_name]
        try:
            result = tool_fn(**kwargs)
        except Exception as exc:
            err_msg = f"Exception in {tool_name}: {str(exc)}"
            self.trace.append({
                "tool": tool_name,
                "reason": reason,
                "input": kwargs,
                "output": {"error": err_msg},
                "success": False,
                "error": err_msg,
            })
            raise RuntimeError(err_msg)
        
        has_error = isinstance(result, dict) and "error" in result
        entry = {
            "tool": tool_name,
            "reason": reason,
            "input": kwargs,
            "output": result,
            "success": not has_error,
            "error": result.get("error") if has_error else None,
        }
        self.trace.append(entry)
        
        if has_error:
            raise RuntimeError(f"{tool_name} failed: {result['error']}")
            
        return result

    def get_trace(self) -> List[Dict[str, Any]]:
        """Return the current tool execution trace."""
        return list(self.trace)

    def clear_trace(self) -> None:
        """Clear recorded tool trace."""
        self.trace.clear()
