"""
Test for the shared `demo_stage` pytest fixture (tests/conftest.py), built once in
TODO 13.0 card (a) foundational so cards (b)/(c)/(e) can reuse it instead of
duplicating env-var setup.
"""


def test_demo_stage_turns_on_only_the_named_stage(demo_stage):
    from backend.core import demo_config

    demo_stage("proposal")

    assert demo_config.is_stage_demo("proposal") is True
    assert demo_config.is_stage_demo("generate_new_idea") is False
    assert demo_config.is_stage_demo("property_prediction") is False
    assert demo_config.is_stage_demo("experiment_detail") is False


def test_demo_stage_can_turn_on_multiple_stages(demo_stage):
    from backend.core import demo_config

    demo_stage("proposal", "experiment_detail")

    assert demo_config.is_stage_demo("proposal") is True
    assert demo_config.is_stage_demo("experiment_detail") is True
    assert demo_config.is_stage_demo("generate_new_idea") is False


def test_demo_stage_with_no_args_turns_everything_off(demo_stage):
    from backend.core import demo_config

    demo_stage("proposal")
    assert demo_config.is_stage_demo("proposal") is True

    demo_stage()
    assert demo_config.is_stage_demo("proposal") is False
    assert demo_config.is_demo_mode() is False


def test_demo_stage_does_not_leak_across_tests_case_a(demo_stage):
    from backend.core import demo_config

    demo_stage("proposal")
    assert demo_config.is_stage_demo("proposal") is True


def test_demo_stage_does_not_leak_across_tests_case_b(demo_stage):
    """Runs after case_a; must not see a stale 'proposal' flag from the previous
    test if this test never called demo_stage("proposal") itself."""
    from backend.core import demo_config

    assert demo_config.is_stage_demo("proposal") is False
