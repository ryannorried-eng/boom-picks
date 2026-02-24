from __future__ import annotations

from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss

ARTIFACT_DIR = Path("artifacts")
ARTIFACT_DIR.mkdir(exist_ok=True)


FEATURE_COLUMNS = [
    "team_win_loss_home_away",
    "recent_form_last_n",
    "head_to_head",
    "rest_days_density",
    "off_def_efficiency",
    "home_court_advantage",
]


def _calibration_bins(y_true: np.ndarray, y_prob: np.ndarray, bins: int = 10) -> list[dict]:
    edges = np.linspace(0, 1, bins + 1)
    out: list[dict] = []
    for idx in range(bins):
        left, right = edges[idx], edges[idx + 1]
        mask = (y_prob >= left) & (y_prob < right if idx < bins - 1 else y_prob <= right)
        if mask.sum() == 0:
            continue
        out.append({
            "bin": idx,
            "avg_pred": float(y_prob[mask].mean()),
            "empirical": float(y_true[mask].mean()),
            "count": int(mask.sum()),
        })
    return out


def train_baseline_model(rows: list[dict], labels: list[int], model_version: str) -> tuple[str, dict]:
    X = np.array([[r[c] for c in FEATURE_COLUMNS] for r in rows])
    y = np.array(labels)
    split_idx = max(1, int(len(y) * 0.8))
    if split_idx >= len(y):
        split_idx = len(y) - 1

    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    clf = LogisticRegression(max_iter=400)
    clf.fit(X_train, y_train)
    artifact_path = ARTIFACT_DIR / f"{model_version}.joblib"
    joblib.dump(clf, artifact_path)

    probs = clf.predict_proba(X_test)[:, 1]
    preds = (probs >= 0.5).astype(int)
    metrics = {
        "n_samples": len(labels),
        "trained_at": datetime.utcnow().isoformat(),
        "holdout_size": int(len(y_test)),
        "log_loss": float(log_loss(y_test, probs, labels=[0, 1])),
        "brier_score_loss": float(brier_score_loss(y_test, probs)),
        "accuracy": float(accuracy_score(y_test, preds)),
        "calibration_bins": _calibration_bins(y_test, probs),
    }
    return str(artifact_path), metrics


def predict_home_win_probability(feature_row: dict, artifact_path: str) -> float:
    clf = joblib.load(artifact_path)
    X = np.array([[feature_row[c] for c in FEATURE_COLUMNS]])
    return float(clf.predict_proba(X)[0][1])
