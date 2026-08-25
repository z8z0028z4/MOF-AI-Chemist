
import os
import sys
import asyncio
from typing import Dict, Any

try:
    import google.genai as genai
    from google.genai import types
    print("Successfully imported google.genai")
except ImportError:
    print("Failed to import google.genai")
    sys.exit(1)

async def test_complex_schema():
    print("\nTesting Complex Schema (referencing schema_manager.py)...")

    # Exact schema from schema_manager.py
    proposal_schema = {
        "type": "object",
        "title": "ResearchProposal",  # Potential suspect
        "additionalProperties": False, # Potential suspect
        "required": [
            "proposal_title",
            "materials_list"
        ],
        "properties": {
            "proposal_title": {
                "type": "string",
                "description": "Title"
            },
            "materials_list": {
                "type": "array",
                "properties": {}, # Empty properties? Gemini doesn't like this maybe?
                "items": {
                    "type": "string"
                }
            }
        }
    }

    try:
        print("Attempting to create config with complex schema...")
        # Note: We are just creating the config object, the validation might happen here or during API call?
        # The previous error "config.response_schema': Cannot find field" usually happens at API call time if it's a server error,
        # or construction time if it's a Pydantic error.
        # But scripts/debug/reproduce_issue.py failed at call_structured_llm -> generate_structured_content_sync -> generate_content.

        config = types.GenerateContentConfig(response_schema=proposal_schema, response_mime_type="application/json")
        print("Successfully created config with complex schema (Constructor).")

        # To be sure, we might need to actually convert it to the Proto look-alike if SDK does that lazily?
        # But mostly valid Pydantic models validate on init.

    except Exception as e:
        print(f"Failed to create config: {e}")

    # Test removing suspect fields
    clean_schema = {
        "type": "OBJECT", # UPPERCASE?
        "properties": {
            "proposal_title": {"type": "STRING"}
        },
        "required": ["proposal_title"]
        # No title, no additionalProperties
    }
    try:
        config = types.GenerateContentConfig(response_schema=clean_schema, response_mime_type="application/json")
        print("Successfully created config with CLEAN schema.")
    except Exception as e:
        print(f"Failed clean schema: {e}")

if __name__ == "__main__":
    asyncio.run(test_complex_schema())
