"""
Normalize Text Function
Cleans and normalizes text (removes extra spaces, special chars, etc).
"""
import re
import unicodedata
from typing import Dict, Any


def execute(content: str, lowercase: bool = False, remove_accents: bool = False, 
            remove_special: bool = False, remove_numbers: bool = False) -> Dict[str, Any]:
    """
    Normalize text content.
    
    Args:
        content: Text to normalize
        lowercase: Convert to lowercase
        remove_accents: Remove accent marks
        remove_special: Remove special characters
        remove_numbers: Remove numeric characters
    
    Returns:
        Dictionary with original and normalized text
    """
    original = content
    normalized = content
    
    # Remove extra whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    if lowercase:
        normalized = normalized.lower()
    
    if remove_accents:
        # Normalize unicode and remove accent marks
        normalized = unicodedata.normalize('NFD', normalized)
        normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    
    if remove_special:
        # Keep only alphanumeric and spaces
        normalized = re.sub(r'[^\w\s]', '', normalized)
    
    if remove_numbers:
        normalized = re.sub(r'\d', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return {
        "original": original,
        "normalized": normalized,
        "original_length": len(original),
        "normalized_length": len(normalized),
        "transformations": {
            "lowercase": lowercase,
            "remove_accents": remove_accents,
            "remove_special": remove_special,
            "remove_numbers": remove_numbers
        }
    }
