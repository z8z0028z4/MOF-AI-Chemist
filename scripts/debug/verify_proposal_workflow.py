
import sys
import os
import asyncio
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from backend.core.settings_manager import settings_manager
from backend.services.knowledge_service import agent_answer
from backend.core.model_config import set_current_model

def verify_workflow():
    print("Starting End-to-End Verification for Gemini Proposal Workflow...")

    # 1. Set global model to Gemini
    target_model = "gemini-3-pro-preview"
    settings_manager.set_current_model(target_model)
    set_current_model(target_model)
    print(f"Set global model to: {target_model}")

    # 2. Define research goal
    research_goal = "Find a conductive MOF that can selectively adsorption ethylene with electro-swing process."
    print(f"Research Goal: {research_goal}")

    # 3. Call agent_answer (Simulating API)
    print("Calling agent_answer (mode='make proposal')...")
    try:
        # Reduced k for speed in verification
        result = agent_answer(research_goal, mode="make proposal", k=1)

        print("\n=== Result Received ===")
        # print(json.dumps(result, indent=2, default=str))

        # 4. Verification
        structured_proposal = result.get("structured_proposal")
        if not structured_proposal:
            print("❌ FAILED: 'structured_proposal' is missing in result.")
            sys.exit(1)

        print("✅ Structured Proposal found.")

        required_fields = ["proposal_title", "materials_list", "experimental_overview"]
        missing = [f for f in required_fields if f not in structured_proposal]

        if missing:
            print(f"❌ FAILED: Missing fields in structured output: {missing}")
            sys.exit(1)

        print("✅ All required fields present.")
        print(f"Title: {structured_proposal.get('proposal_title')}")
        print(f"Materials: {structured_proposal.get('materials_list')}")

        # Check if citations exist
        citations = result.get("citations")
        if citations:
            print(f"✅ Citations present: {len(citations)}")
        else:
            print("⚠️ Warning: No citations found (might be due to mocked retrieval or strict prompt).")

        print("\n🎉 VERIFICATION SUCCESSFUL! Gemini flow is working.")

    except Exception as e:
        print(f"❌ FAILED: Exception during execution: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    verify_workflow()
