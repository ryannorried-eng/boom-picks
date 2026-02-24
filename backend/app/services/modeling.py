from __future__ import annotations

from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression

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


def train_baseline_model(rows: list[dict], labels: list[int], model_version: str) -> tuple[str, dict]:
    X = np.array([[r[c] for c in FEATURE_COLUMNS] for r in rows])
    y = np.array(labels)
    clf = LogisticRegression(max_iter=400)
    clf.fit(X, y)
    artifact_path = ARTIFACT_DIR / f"{model_version}.joblib"
    joblib.dump(clf, artifact_path)
    metrics = {"n_samples": len(labels), "trained_at": datetime.utcnow().isoformat()}
    return str(artifact_path), metrics


def predict_home_win_probability(feature_row: dict, artifact_path: str) -> float:
    clf = joblib.load(artifact_path)
    X = np.array([[feature_row[c] for c in FEATURE_COLUMNS]])
    return float(clf.predict_proba(X)[0][1])
