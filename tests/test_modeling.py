from backend.app.services.modeling import train_baseline_model


def test_train_baseline_model_includes_holdout_metrics() -> None:
    samples = [
        {"team_win_loss_home_away": 0.6, "recent_form_last_n": 0.6, "head_to_head": 0.5, "rest_days_density": 0.1, "off_def_efficiency": 1.0, "home_court_advantage": 1.0},
        {"team_win_loss_home_away": 0.4, "recent_form_last_n": 0.4, "head_to_head": 0.4, "rest_days_density": -0.2, "off_def_efficiency": -1.0, "home_court_advantage": 1.0},
        {"team_win_loss_home_away": 0.55, "recent_form_last_n": 0.52, "head_to_head": 0.5, "rest_days_density": 0.2, "off_def_efficiency": 0.8, "home_court_advantage": 1.0},
        {"team_win_loss_home_away": 0.35, "recent_form_last_n": 0.45, "head_to_head": 0.45, "rest_days_density": -0.1, "off_def_efficiency": -0.6, "home_court_advantage": 1.0},
        {"team_win_loss_home_away": 0.7, "recent_form_last_n": 0.68, "head_to_head": 0.6, "rest_days_density": 0.3, "off_def_efficiency": 1.2, "home_court_advantage": 1.0},
        {"team_win_loss_home_away": 0.3, "recent_form_last_n": 0.35, "head_to_head": 0.4, "rest_days_density": -0.3, "off_def_efficiency": -1.2, "home_court_advantage": 1.0},
    ]
    labels = [1, 0, 1, 0, 1, 0]
    _, metrics = train_baseline_model(samples, labels, "test-model-metrics")

    assert "log_loss" in metrics
    assert "brier_score_loss" in metrics
    assert "calibration_bins" in metrics
    assert "holdout_size" in metrics
