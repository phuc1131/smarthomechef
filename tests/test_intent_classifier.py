from app.services.intent_classifier import classify_intent


def test_classify_recommendation_vietnamese():
    label, conf, matches = classify_intent('Gợi ý món ăn giảm cân')
    assert label == 'recommendation'
    assert conf > 0


def test_classify_recipe_vietnamese():
    label, conf, matches = classify_intent('Cho tôi công thức món phở bò')
    assert label == 'recipe'
    assert conf > 0
