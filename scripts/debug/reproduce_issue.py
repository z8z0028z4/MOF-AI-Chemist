
import sys
import os
import asyncio

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from backend.core.generation import call_llm_structured_proposal
from backend.utils.exceptions import LLMError

def reproduce():
    print("Running reproduction script for Gemini Structured Proposal...")

    system_prompt = "You are a helper."
    user_prompt = "Generate a proposal."

    # Test with a Gemini model
    test_model = "gemini-3-pro-preview"

    try:
        print(f"Attempting to call call_llm_structured_proposal with model: {test_model}")
        call_llm_structured_proposal(system_prompt, user_prompt, model=test_model)
        # Note: If this actually calls the API, it might fail with unrelated errors (like key or safety),
        # but as long as it doesn't fail with LLMError "Unsupported model" or "Cannot find field", we are good.
        print("Success! (Or at least passed validation and schema construction)")
    except LLMError as e:
        print(f"Caught expected LLMError: {e}")
    except Exception as e:
        print(f"Caught unexpected exception: {type(e).__name__}: {e}")

if __name__ == "__main__":
    reproduce()
