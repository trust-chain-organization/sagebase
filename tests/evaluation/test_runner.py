"""Tests for evaluation runner"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.evaluation.metrics import EvaluationMetrics
from src.evaluation.runner import EvaluationRunner


class TestEvaluationRunner:
    """Test EvaluationRunner class"""

    @pytest.fixture
    def runner(self):
        """Create a runner instance with mock LLM"""
        # Use mock LLM to avoid needing real API keys in tests
        with patch.dict("os.environ", {"GOOGLE_API_KEY": ""}, clear=False):
            return EvaluationRunner(use_real_llm=False)

    @pytest.fixture
    def sample_dataset(self):
        """Create a sample dataset for testing"""
        return {
            "version": "1.0.0",
            "task_type": "minutes_division",
            "metadata": {
                "created_at": "2025-08-08T10:00:00Z",
                "created_by": "Test",
                "description": "Test dataset",
            },
            "test_cases": [
                {
                    "id": "test_001",
                    "description": "Test case 1",
                    "input": {"original_minutes": "Test minutes"},
                    "expected_output": {
                        "speaker_and_speech_content_list": [
                            {"speaker": "Speaker 1", "speech_content": "Content 1"}
                        ]
                    },
                }
            ],
        }

    def test_load_dataset_success(self, runner, sample_dataset):
        """Test loading dataset from file successfully"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            json.dump(sample_dataset, tmp)
            tmp_path = tmp.name

        try:
            dataset = runner.load_dataset(tmp_path)
            assert dataset["version"] == "1.0.0"
            assert dataset["task_type"] == "minutes_division"
            assert len(dataset["test_cases"]) == 1
        finally:
            Path(tmp_path).unlink()

    def test_load_dataset_file_not_found(self, runner):
        """Test loading dataset with non-existent file"""
        with pytest.raises(FileNotFoundError):
            runner.load_dataset("non_existent_file.json")

    def test_load_dataset_invalid_json(self, runner):
        """Test loading dataset with invalid JSON"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            tmp.write("{ invalid json }")
            tmp_path = tmp.name

        try:
            with pytest.raises(json.JSONDecodeError):
                runner.load_dataset(tmp_path)
        finally:
            Path(tmp_path).unlink()

    def test_execute_test_case_minutes_division(self):
        """Test executing minutes division test case"""
        # Create runner directly without fixture to ensure use_real_llm=False
        with patch.dict("os.environ", {"GOOGLE_API_KEY": ""}, clear=False):
            runner = EvaluationRunner(use_real_llm=False)

            test_case = {
                "id": "test_001",
                "expected_output": {
                    "speaker_and_speech_content_list": [
                        {"speaker": "Speaker 1", "speech_content": "Content 1"}
                    ]
                },
            }

            result = runner.execute_test_case("minutes_division", test_case)

            assert "speaker_and_speech_content_list" in result
            assert len(result["speaker_and_speech_content_list"]) == 1

    def test_execute_test_case_speaker_matching(self):
        """Test executing speaker matching test case"""
        # Create runner directly without fixture to ensure use_real_llm=False
        with patch.dict("os.environ", {"GOOGLE_API_KEY": ""}, clear=False):
            runner = EvaluationRunner(use_real_llm=False)

            test_case = {
                "id": "test_001",
                "expected_output": {
                    "results": [{"speaker_id": 1, "politician_id": 101}]
                },
            }

            result = runner.execute_test_case("speaker_matching", test_case)

            assert "results" in result
            assert len(result["results"]) == 1

    @patch("src.evaluation.runner.EvaluationRunner.load_dataset")
    @patch("src.evaluation.runner.EvaluationRunner.execute_test_case")
    def test_run_evaluation_single_task(
        self, mock_execute, mock_load, runner, sample_dataset
    ):
        """Test running evaluation for a single task"""
        mock_load.return_value = sample_dataset
        mock_execute.return_value = {
            "speaker_and_speech_content_list": [
                {"speaker": "Speaker 1", "speech_content": "Content 1"}
            ]
        }

        metrics = runner.run_evaluation(
            task_type="minutes_division", dataset_path="test.json"
        )

        assert len(metrics) == 1
        assert metrics[0].task_type == "minutes_division"
        mock_load.assert_called_once_with("test.json")
        mock_execute.assert_called_once()

    @patch("src.evaluation.runner.EvaluationRunner.load_dataset")
    @patch("src.evaluation.runner.EvaluationRunner.execute_test_case")
    def test_run_evaluation_all_tasks(self, mock_execute, mock_load, runner):
        """Test running evaluation for all tasks"""
        mock_load.return_value = {
            "task_type": "minutes_division",
            "test_cases": [{"id": "test_001", "expected_output": {}}],
        }
        mock_execute.return_value = {}

        metrics = runner.run_evaluation(run_all=True)

        # Should attempt to run all 4 task types
        assert mock_load.call_count == 4
        assert len(metrics) == 4

    def test_run_evaluation_no_task_specified(self, runner):
        """Test running evaluation without specifying task"""
        with pytest.raises(ValueError) as exc_info:
            runner.run_evaluation()

        assert "Either specify task_type or use run_all=True" in str(exc_info.value)

    @patch("src.evaluation.runner.EvaluationRunner.load_dataset")
    @patch("builtins.print")
    def test_run_evaluation_dataset_not_found(self, mock_print, mock_load, runner):
        """Test running evaluation with missing dataset"""
        mock_load.side_effect = FileNotFoundError("Dataset not found")

        metrics = runner.run_evaluation(task_type="minutes_division")

        assert len(metrics) == 0
        mock_print.assert_called()

    @patch("builtins.print")
    def test_display_results_empty(self, mock_print, runner):
        """Test displaying empty results"""
        runner.display_results([])
        mock_print.assert_called_with("No evaluation results to display")

    @patch("builtins.print")
    def test_display_results_with_metrics(self, mock_print, runner):
        """Test displaying results with metrics"""
        metrics = [
            EvaluationMetrics(
                task_type="minutes_division",
                test_case_id="test_001",
                metrics={
                    "speaker_match_rate": 0.95,
                    "content_similarity": 0.88,
                    "expected_count": 10,
                    "actual_count": 9,
                },
                passed=True,
            ),
            EvaluationMetrics(
                task_type="minutes_division",
                test_case_id="test_002",
                metrics={
                    "speaker_match_rate": 0.70,
                    "content_similarity": 0.65,
                    "expected_count": 5,
                    "actual_count": 4,
                },
                passed=False,
            ),
        ]

        runner.display_results(metrics)

        # Check that print was called
        assert mock_print.called
        # Should print header, table, and summary
        assert mock_print.call_count >= 3

    def test_get_metric_columns(self, runner):
        """Test getting metric columns for different task types"""
        assert runner._get_metric_columns("minutes_division") == [
            "Speaker Match",
            "Content Similarity",
            "Count",
        ]
        assert runner._get_metric_columns("speaker_matching") == [
            "ID Match Rate",
            "Confidence",
            "Accuracy",
        ]
        assert runner._get_metric_columns("party_member_extraction") == [
            "Extraction Rate",
            "Name Accuracy",
            "Count",
        ]
        assert runner._get_metric_columns("conference_member_matching") == [
            "Precision",
            "Recall",
            "F1 Score",
        ]
        assert runner._get_metric_columns("unknown") == [
            "Metric 1",
            "Metric 2",
            "Metric 3",
        ]

    @patch("builtins.print")
    def test_display_summary(self, mock_print, runner):
        """Test displaying summary statistics"""
        metrics = [
            EvaluationMetrics(
                task_type="test_task",
                test_case_id="test_001",
                metrics={"accuracy": 0.95, "count": 10},
                passed=True,
            ),
            EvaluationMetrics(
                task_type="test_task",
                test_case_id="test_002",
                metrics={"accuracy": 0.85, "count": 8},
                passed=False,
            ),
        ]

        runner._display_summary("test_task", metrics)

        # Check summary was printed
        assert mock_print.called
        # Should print summary header, stats, and average metrics
        assert mock_print.call_count >= 5
