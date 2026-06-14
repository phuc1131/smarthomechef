from app.services.ai_request_guard_service import (
    analyze_user_request,
    build_response_contract,
    validate_response_against_request,
)


def test_analyze_user_request_marks_dynamic_price_queries_to_skip_cache():
    analysis = analyze_user_request("Gia ca chua hom nay bao nhieu?")

    assert analysis.primary_goal == "price"
    assert analysis.skip_cache is True
    assert analysis.is_time_sensitive is True


def test_validate_response_rejects_recipe_answer_for_price_question():
    analysis = analyze_user_request("Gia thit heo bao nhieu?")
    result = validate_response_against_request(
        "Gia thit heo bao nhieu?",
        "Cong thuc nay can thit heo, hanh va 3 buoc che bien.",
        analysis=analysis,
        intent_name="ingredient",
    )

    assert result["ok"] is False
    assert "price_answer_missing" in result["issues"]


def test_build_response_contract_mentions_current_goal():
    analysis = analyze_user_request("Cho toi thuc don giam can 3 ngay")
    contract = build_response_contract(analysis)

    assert "thuc don" in contract.lower()
