"""
Action Parser for Orchestrator.
Parses [ACTION:name params] syntax from prompts.
"""
import re
from typing import Optional, Dict, Any, Tuple


def parse_action(prompt: str) -> Tuple[Optional[str], Dict[str, Any], str]:
    """
    Parse [ACTION:function_name param1=value1 param2=value2] syntax.
    
    Returns:
        (action_name, params, content)
        - action_name: The function name to execute (None if no action found)
        - params: Dictionary of parameters
        - content: The content between triple backticks
    """
    # Pattern to match [ACTION:name key=value ...]
    action_pattern = r'\[ACTION:(\w+)([^\]]*)\]'
    action_match = re.search(action_pattern, prompt)
    
    action_name = None
    params = {}
    
    if action_match:
        action_name = action_match.group(1)
        params_str = action_match.group(2).strip()
        
        # Parse parameters (key=value pairs)
        if params_str:
            # Match key=value pairs (handles strings, booleans, numbers)
            param_pattern = r'(\w+)=(["\']?)([^"\'\s]+)\2'
            for match in re.finditer(param_pattern, params_str):
                key = match.group(1)
                value = match.group(3)
                
                # Convert value types
                if value.lower() == 'true':
                    params[key] = True
                elif value.lower() == 'false':
                    params[key] = False
                elif value.isdigit():
                    params[key] = int(value)
                elif re.match(r'^\d+\.\d+$', value):
                    params[key] = float(value)
                else:
                    params[key] = value
    
    # Extract content between triple backticks
    content_pattern = r'```(?:\w*\n)?(.*?)```'
    content_match = re.search(content_pattern, prompt, re.DOTALL)
    content = content_match.group(1).strip() if content_match else prompt
    
    return action_name, params, content


def validate_action_syntax(prompt: str) -> Dict[str, Any]:
    """
    Validate action syntax and return detailed info.
    """
    action_name, params, content = parse_action(prompt)
    
    return {
        "has_explicit_action": action_name is not None,
        "action_name": action_name,
        "params": params,
        "content": content,
        "content_length": len(content)
    }
