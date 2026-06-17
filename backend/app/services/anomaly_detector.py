"""
ML Anomaly Detection Engine
----------------------------
Uses scikit-learn's Isolation Forest to detect anomalous
authentication behavior based on per-user behavioral baselines.

How it works:
1. Build a feature vector from a user's historical events
2. Train an Isolation Forest on "normal" behavior
3. Score new events against the baseline
4. Flag statistical outliers as anomalies

Why Isolation Forest?
- Designed specifically for anomaly detection (not classification)
- Works well with small datasets (no need for thousands of samples)
- Unsupervised — no labeled "attack" data needed
- Fast and interpretable
"""

import numpy as np
import logging
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AnomalyResult:
    """Result of anomaly detection for a single event"""
    is_anomaly: bool
    anomaly_score: float          # 0.0 (normal) to 1.0 (highly anomalous)
    confidence: float             # How confident we are in this assessment
    anomalous_features: list[str] # Which features triggered the anomaly
    baseline_comparison: dict     # How this event compares to the user's baseline


class UserBaseline:
    """
    Behavioral baseline for a single user, built from their event history.
    Tracks: login hours, IP addresses, failure rates, login frequency,
            event type distribution, and geolocation patterns.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.login_hours: list[int] = []          # Hours of day (0-23)
        self.ip_addresses: set[str] = set()
        self.countries: set[str] = set()
        self.event_types: list[str] = []
        self.outcomes: list[str] = []
        self.daily_event_counts: list[int] = []
        self.total_events: int = 0
        self.failure_count: int = 0
        self.is_trained: bool = False

    def add_event(self, event) -> None:
        """Add a historical event to build the baseline."""
        if hasattr(event, 'published') and event.published:
            self.login_hours.append(event.published.hour)

        if hasattr(event, 'ip_address') and event.ip_address:
            self.ip_addresses.add(event.ip_address)

        if hasattr(event, 'geolocation') and event.geolocation:
            if event.geolocation.country:
                self.countries.add(event.geolocation.country)

        if hasattr(event, 'event_type') and event.event_type:
            self.event_types.append(event.event_type)

        if hasattr(event, 'outcome') and event.outcome:
            self.outcomes.append(event.outcome)
            if event.outcome == "FAILURE":
                self.failure_count += 1

        self.total_events += 1

    def add_event_from_dict(self, event: dict) -> None:
        """Add event from DynamoDB dict format."""
        published_str = event.get("published", "")
        if published_str:
            try:
                dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                self.login_hours.append(dt.hour)
            except Exception:
                pass

        ip = event.get("ip_address", "")
        if ip:
            self.ip_addresses.add(ip)

        country = event.get("geo_country", "")
        if country:
            self.countries.add(country)

        event_type = event.get("event_type", "")
        if event_type:
            self.event_types.append(event_type)

        outcome = event.get("outcome", "")
        if outcome:
            self.outcomes.append(outcome)
            if outcome == "FAILURE":
                self.failure_count += 1

        self.total_events += 1

    @property
    def typical_hours(self) -> tuple[float, float]:
        """Mean and std deviation of login hours."""
        if not self.login_hours:
            return 12.0, 6.0  # Default: midday, wide window
        arr = np.array(self.login_hours, dtype=float)
        return float(np.mean(arr)), float(np.std(arr)) + 0.1

    @property
    def failure_rate(self) -> float:
        """Historical failure rate (0.0 - 1.0)."""
        if not self.outcomes:
            return 0.0
        return self.failure_count / len(self.outcomes)

    @property
    def known_ip_count(self) -> int:
        return len(self.ip_addresses)

    @property
    def known_country_count(self) -> int:
        return len(self.countries)

    def has_enough_data(self) -> bool:
        """Need at least 3 events to build a meaningful baseline."""
        return self.total_events >= 3


class AnomalyDetector:
    """
    Isolation Forest-based anomaly detector.
    Builds per-user behavioral baselines and scores new events.
    """

    def __init__(self):
        # Store baselines per user
        self._baselines: dict[str, UserBaseline] = {}
        # Store trained models per user
        self._models: dict[str, object] = {}

    def build_baseline(self, user_id: str, events: list) -> UserBaseline:
        """
        Build a behavioral baseline from a user's event history.
        Events can be AuthEvent objects or DynamoDB dicts.
        """
        baseline = UserBaseline(user_id)

        for event in events:
            if isinstance(event, dict):
                baseline.add_event_from_dict(event)
            else:
                baseline.add_event(event)

        self._baselines[user_id] = baseline
        logger.info(
            f"Built baseline for {user_id}: "
            f"{baseline.total_events} events, "
            f"{baseline.known_ip_count} IPs, "
            f"{baseline.known_country_count} countries, "
            f"typical hours: {baseline.typical_hours[0]:.1f}±{baseline.typical_hours[1]:.1f}"
        )
        return baseline

    def _extract_features(self, event, baseline: UserBaseline) -> np.ndarray:
        """
        Convert an event + baseline into a numeric feature vector.

        Features:
        0: Hour deviation from baseline mean (z-score)
        1: Is this a known IP? (0/1)
        2: Is this a known country? (0/1)
        3: Is outcome a failure? (0/1)
        4: Is hour outside business hours? (0/1)
        5: Deviation from typical failure rate
        """
        features = np.zeros(6)

        # Feature 0: Login hour deviation (z-score)
        if isinstance(event, dict):
            published_str = event.get("published", "")
            hour = 12  # Default
            if published_str:
                try:
                    dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                    hour = dt.hour
                except Exception:
                    pass
            ip = event.get("ip_address", "")
            country = event.get("geo_country", "")
            outcome = event.get("outcome", "")
        else:
            hour = event.published.hour if event.published else 12
            ip = event.ip_address or ""
            country = (event.geolocation.country if event.geolocation and event.geolocation.country else "")
            outcome = event.outcome or ""

        mean_hour, std_hour = baseline.typical_hours
        features[0] = abs(hour - mean_hour) / std_hour

        # Feature 1: Known IP (inverted — unknown IPs are anomalous)
        features[1] = 0.0 if (ip and ip in baseline.ip_addresses) else 1.0

        # Feature 2: Known country (inverted)
        features[2] = 0.0 if (country and country in baseline.countries) else 1.0

        # Feature 3: Failure outcome
        features[3] = 1.0 if outcome == "FAILURE" else 0.0

        # Feature 4: Outside business hours (before 7am or after 10pm)
        features[4] = 1.0 if (hour < 7 or hour > 22) else 0.0

        # Feature 5: Failure rate deviation
        current_failure = 1.0 if outcome == "FAILURE" else 0.0
        features[5] = abs(current_failure - baseline.failure_rate)

        return features

    def train_model(self, user_id: str, historical_events: list) -> bool:
        """
        Train an Isolation Forest on a user's historical events.
        Returns True if training succeeded.
        """
        try:
            from sklearn.ensemble import IsolationForest

            baseline = self._baselines.get(user_id)
            if not baseline or not baseline.has_enough_data():
                logger.warning(f"Not enough data to train model for {user_id}")
                return False

            # Build feature matrix from historical events
            feature_matrix = []
            for event in historical_events:
                features = self._extract_features(event, baseline)
                feature_matrix.append(features)

            if len(feature_matrix) < 3:
                return False

            X = np.array(feature_matrix)

            # Train Isolation Forest
            # contamination=0.1 means we expect ~10% of events to be anomalous
            model = IsolationForest(
                contamination=0.1,
                random_state=42,
                n_estimators=100,
            )
            model.fit(X)
            self._models[user_id] = model

            logger.info(f"Trained Isolation Forest for {user_id} on {len(X)} events")
            return True

        except Exception as e:
            logger.error(f"Failed to train model for {user_id}: {e}")
            return False

    def score_event(self, event, user_id: str) -> AnomalyResult:
        """
        Score a single event against the user's trained model.
        Returns an AnomalyResult with anomaly score and explanation.
        """
        baseline = self._baselines.get(user_id)
        model = self._models.get(user_id)

        # Fall back to rule-based if no ML model available
        if not baseline or not model:
            return self._rule_based_score(event, baseline)

        try:
            features = self._extract_features(event, baseline)
            X = features.reshape(1, -1)

            # Isolation Forest: -1 = anomaly, 1 = normal
            prediction = model.predict(X)[0]
            # Raw anomaly score (more negative = more anomalous)
            raw_score = model.score_samples(X)[0]

            # Normalize to 0-1 range (1 = most anomalous)
            # Typical range is roughly -0.5 to 0.5
            anomaly_score = max(0.0, min(1.0, (-raw_score + 0.5) / 1.0))
            is_anomaly = prediction == -1

            # Identify which features triggered the anomaly
            anomalous_features = self._explain_anomaly(features, baseline, event)

            # Build baseline comparison
            mean_hour, std_hour = baseline.typical_hours
            if isinstance(event, dict):
                published_str = event.get("published", "")
                hour = 12
                if published_str:
                    try:
                        dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                        hour = dt.hour
                    except Exception:
                        pass
                ip = event.get("ip_address", "")
                country = event.get("geo_country", "")
            else:
                hour = event.published.hour if event.published else 12
                ip = event.ip_address or ""
                country = (event.geolocation.country if event.geolocation and event.geolocation.country else "")

            baseline_comparison = {
                "typical_login_hours": f"{mean_hour:.0f}:00 ± {std_hour:.0f}h",
                "this_event_hour": f"{hour}:00",
                "hour_deviation_sigma": round(features[0], 2),
                "known_ip": ip in baseline.ip_addresses,
                "known_country": country in baseline.countries,
                "historical_failure_rate": f"{baseline.failure_rate:.0%}",
                "baseline_events": baseline.total_events,
            }

            return AnomalyResult(
                is_anomaly=is_anomaly,
                anomaly_score=round(anomaly_score, 3),
                confidence=0.85 if baseline.total_events >= 10 else 0.60,
                anomalous_features=anomalous_features,
                baseline_comparison=baseline_comparison,
            )

        except Exception as e:
            logger.error(f"Error scoring event for {user_id}: {e}")
            return self._rule_based_score(event, baseline)

    def _explain_anomaly(self, features: np.ndarray, baseline: UserBaseline, event) -> list[str]:
        """Generate human-readable explanations for anomalous features."""
        explanations = []
        mean_hour, std_hour = baseline.typical_hours

        if features[0] > 2.0:
            explanations.append(
                f"Login hour is {features[0]:.1f}σ outside normal pattern "
                f"(typical: {mean_hour:.0f}:00)"
            )
        if features[1] > 0:
            explanations.append("Unrecognized IP address — not seen in historical logins")
        if features[2] > 0:
            explanations.append(f"Unrecognized country — not in user's known locations")
        if features[3] > 0:
            explanations.append("Authentication failure")
        if features[4] > 0:
            explanations.append("Login outside normal business hours (before 7am or after 10pm)")
        if features[5] > 0.5:
            explanations.append(
                f"Failure rate anomaly — historical rate: {baseline.failure_rate:.0%}"
            )

        return explanations if explanations else ["No specific anomalous features identified"]

    def _rule_based_score(self, event, baseline: Optional[UserBaseline]) -> AnomalyResult:
        """Fallback rule-based scoring when ML model isn't available."""
        score = 0.0
        factors = []

        if isinstance(event, dict):
            outcome = event.get("outcome", "")
            hour = 12
            published_str = event.get("published", "")
            if published_str:
                try:
                    dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                    hour = dt.hour
                except Exception:
                    pass
        else:
            outcome = event.outcome or ""
            hour = event.published.hour if event.published else 12

        if outcome == "FAILURE":
            score += 0.3
            factors.append("Authentication failure")
        if hour < 7 or hour > 22:
            score += 0.2
            factors.append(f"Unusual hour: {hour}:00")
        if not baseline:
            score += 0.1
            factors.append("No baseline available")

        return AnomalyResult(
            is_anomaly=score > 0.4,
            anomaly_score=round(min(score, 1.0), 3),
            confidence=0.5,
            anomalous_features=factors or ["No anomalies detected"],
            baseline_comparison={"note": "Rule-based fallback — ML model not trained yet"},
        )


# Module-level singleton — reused across requests
_detector = AnomalyDetector()


def get_detector() -> AnomalyDetector:
    return _detector
