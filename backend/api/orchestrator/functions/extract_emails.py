"""
Extract Emails Function
Extracts all email addresses from text.
"""
import re
from typing import Dict, Any, List


def execute(content: str, unique: bool = True) -> Dict[str, Any]:
    """
    Extract email addresses from text content.
    
    Args:
        content: Text to search for emails
        unique: If True, return only unique emails
    
    Returns:
        Dictionary with found emails
    """
    # Email pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    matches = re.findall(email_pattern, content)
    
    if unique:
        matches = list(dict.fromkeys(matches))  # Preserve order while removing duplicates
    
    return {
        "found": len(matches) > 0,
        "count": len(matches),
        "emails": matches
    }
