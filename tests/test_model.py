from Scripts.ML_model.predict_bikes import train_and_evaluate

def test_model_r2_above_threshold():
    _, score = train_and_evaluate()
    assert score >= 0.75, f"❌ Score R2 trop faible : {score:.4f}"



