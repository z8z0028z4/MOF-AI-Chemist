"""
Unit tests for backend.services.demo_service (TODO 13.0 card a).

Written FIRST per TDD: backend/services/demo_service.py and its fixture JSON files
do not exist yet, so all of these should fail (RED) before implementation.
"""


def test_get_proposal_response_has_required_keys():
    from backend.services import demo_service

    result = demo_service.get_proposal_response("some research goal")

    assert isinstance(result, dict)
    for key in ("proposal", "chemicals", "citations", "not_found", "chunks", "structured_proposal"):
        assert key in result
    assert isinstance(result["proposal"], str) and len(result["proposal"]) > 0
    assert isinstance(result["chemicals"], list) and len(result["chemicals"]) > 0


def test_get_proposal_response_is_deterministic_across_calls():
    from backend.services import demo_service

    first = demo_service.get_proposal_response("goal A")
    second = demo_service.get_proposal_response("goal B")

    # Fixture-backed: same canned proposal text/shape regardless of input.
    assert first["proposal"] == second["proposal"]
    assert first["structured_proposal"] == second["structured_proposal"]


def test_get_revision_response_has_required_keys():
    from backend.services import demo_service

    result = demo_service.get_revision_response("please use ethanol instead")

    assert isinstance(result, dict)
    for key in ("proposal", "chemicals", "structured_proposal"):
        assert key in result
    assert isinstance(result["proposal"], str) and len(result["proposal"]) > 0


def test_get_property_prediction_response_has_required_keys():
    from backend.services import demo_service

    result = demo_service.get_property_prediction_response()

    assert isinstance(result, dict)
    assert "results" in result
    assert isinstance(result["results"], list)
    assert len(result["results"]) > 0
    for item in result["results"]:
        assert "node_id" in item
        assert "linker_id" in item
        assert "uptake" in item


def test_get_experiment_detail_response_has_required_keys():
    from backend.services import demo_service

    result = demo_service.get_experiment_detail_response("proposal text mentioning methanol")

    assert isinstance(result, dict)
    for key in ("experiment_detail", "structured_experiment", "citations"):
        assert key in result
    assert isinstance(result["experiment_detail"], str) and len(result["experiment_detail"]) > 0


def test_get_experiment_detail_response_default_is_methanol_variant():
    from backend.services import demo_service

    # Per approved v1 scope simplification: always returns methanol variant regardless
    # of proposal_text content (ethanol-variant selection is a documented follow-up).
    result_no_text = demo_service.get_experiment_detail_response()
    result_ethanol_text = demo_service.get_experiment_detail_response("uses ethanol as solvent")

    assert "methanol" in result_no_text["experiment_detail"].lower()
    assert result_no_text == result_ethanol_text


def test_demo_service_functions_are_deterministic_and_side_effect_free():
    from backend.services import demo_service

    # Calling repeatedly must not mutate shared state (no I/O beyond the initial load).
    a = demo_service.get_property_prediction_response()
    b = demo_service.get_property_prediction_response()
    assert a == b
