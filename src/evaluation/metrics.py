"""Metrics calculation for evaluation tasks"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvaluationMetrics:
    """Container for evaluation metrics"""

    task_type: str
    test_case_id: str
    metrics: dict[str, Any] = field(default_factory=dict)
    passed: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary format"""
        return {
            "task_type": self.task_type,
            "test_case_id": self.test_case_id,
            "passed": self.passed,
            "metrics": self.metrics,
            "error": self.error,
        }


class MetricsCalculator:
    """Calculate metrics for different evaluation tasks"""

    @staticmethod
    def calculate_party_member_extraction_metrics(
        expected: dict[str, Any], actual: dict[str, Any]
    ) -> EvaluationMetrics:
        """Calculate metrics for party member extraction task

        Metrics:
        - extraction_rate: Percentage of successfully extracted members
        - name_accuracy: Accuracy of extracted names
        - attribute_accuracy: Accuracy of other attributes (position, district, etc.)
        """
        metrics = EvaluationMetrics(
            task_type="party_member_extraction",
            test_case_id=expected.get("id", "unknown"),
        )

        try:
            expected_members = expected.get("expected_output", {}).get("members", [])
            actual_members = actual.get("members", [])

            if expected_members:
                # Calculate extraction rate
                metrics.metrics["extraction_rate"] = len(actual_members) / len(
                    expected_members
                )

                # Calculate name accuracy
                name_matches = 0
                for exp_member in expected_members:
                    exp_name = exp_member["name"]
                    if any(m["name"] == exp_name for m in actual_members):
                        name_matches += 1

                metrics.metrics["name_accuracy"] = name_matches / len(expected_members)

                # Calculate attribute accuracy (check position, district, etc.)
                attribute_matches = 0
                total_attributes = 0

                for exp_member in expected_members:
                    act_member = next(
                        (m for m in actual_members if m["name"] == exp_member["name"]),
                        None,
                    )
                    if act_member:
                        # Check various attributes
                        for attr in ["position", "district", "email", "website"]:
                            if attr in exp_member:
                                total_attributes += 1
                                if exp_member.get(attr) == act_member.get(attr):
                                    attribute_matches += 1

                metrics.metrics["attribute_accuracy"] = (
                    attribute_matches / total_attributes
                    if total_attributes > 0
                    else 0.0
                )
            else:
                metrics.metrics["extraction_rate"] = 0.0
                metrics.metrics["name_accuracy"] = 0.0
                metrics.metrics["attribute_accuracy"] = 0.0

            # Count statistics
            metrics.metrics["expected_count"] = len(expected_members)
            metrics.metrics["actual_count"] = len(actual_members)

            # Determine if test passed (80% threshold for extraction and name accuracy)
            metrics.passed = (
                metrics.metrics["extraction_rate"] >= 0.8
                and metrics.metrics["name_accuracy"] >= 0.8
            )

        except Exception as e:
            metrics.error = str(e)
            metrics.passed = False

        return metrics

    @staticmethod
    def calculate_conference_member_matching_metrics(
        expected: dict[str, Any], actual: dict[str, Any]
    ) -> EvaluationMetrics:
        """Calculate metrics for conference member matching task

        Metrics:
        - match_precision: Precision of matching (correct matches / total matches)
        - match_recall: Recall of matching (correct matches / expected matches)
        - confidence_distribution: Distribution of confidence scores
        """
        metrics = EvaluationMetrics(
            task_type="conference_member_matching",
            test_case_id=expected.get("id", "unknown"),
        )

        try:
            expected_matches = expected.get("expected_output", {}).get(
                "matched_members", []
            )
            actual_matches = actual.get("matched_members", [])

            if expected_matches:
                # Calculate precision and recall
                correct_matches = 0
                confidence_scores = []

                for exp_match in expected_matches:
                    member_name = exp_match["member_name"]
                    exp_politician_id = exp_match.get("politician_id")

                    # Find corresponding actual match
                    act_match = next(
                        (m for m in actual_matches if m["member_name"] == member_name),
                        None,
                    )

                    if act_match:
                        if exp_politician_id == act_match.get("politician_id"):
                            correct_matches += 1
                        if "confidence_score" in act_match:
                            confidence_scores.append(act_match["confidence_score"])

                # Precision: correct matches / total actual matches
                metrics.metrics["match_precision"] = (
                    correct_matches / len(actual_matches) if actual_matches else 0.0
                )

                # Recall: correct matches / total expected matches
                metrics.metrics["match_recall"] = correct_matches / len(
                    expected_matches
                )

                # F1 Score
                precision = metrics.metrics["match_precision"]
                recall = metrics.metrics["match_recall"]
                metrics.metrics["f1_score"] = (
                    2 * (precision * recall) / (precision + recall)
                    if (precision + recall) > 0
                    else 0.0
                )

                # Confidence distribution
                if confidence_scores:
                    metrics.metrics["confidence_mean"] = sum(confidence_scores) / len(
                        confidence_scores
                    )
                    metrics.metrics["confidence_min"] = min(confidence_scores)
                    metrics.metrics["confidence_max"] = max(confidence_scores)
                else:
                    metrics.metrics["confidence_mean"] = 0.0
                    metrics.metrics["confidence_min"] = 0.0
                    metrics.metrics["confidence_max"] = 0.0

            else:
                metrics.metrics["match_precision"] = 0.0
                metrics.metrics["match_recall"] = 0.0
                metrics.metrics["f1_score"] = 0.0

            # Count statistics
            metrics.metrics["expected_count"] = len(expected_matches)
            metrics.metrics["actual_count"] = len(actual_matches)

            # Determine if test passed (85% threshold for F1 score)
            metrics.passed = metrics.metrics.get("f1_score", 0.0) >= 0.85

        except Exception as e:
            metrics.error = str(e)
            metrics.passed = False

        return metrics

    @classmethod
    def calculate_metrics(
        cls, task_type: str, expected: dict[str, Any], actual: dict[str, Any]
    ) -> EvaluationMetrics:
        """Calculate metrics based on task type

        Args:
            task_type: Type of evaluation task
            expected: Expected output from test case
            actual: Actual output from system

        Returns:
            Calculated metrics
        """
        calculators = {
            "party_member_extraction": cls.calculate_party_member_extraction_metrics,
            "conference_member_matching": (
                cls.calculate_conference_member_matching_metrics
            ),
        }

        calculator = calculators.get(task_type)
        if not calculator:
            metrics = EvaluationMetrics(
                task_type=task_type, test_case_id=expected.get("id", "unknown")
            )
            metrics.error = f"Unknown task type: {task_type}"
            return metrics

        return calculator(expected, actual)
