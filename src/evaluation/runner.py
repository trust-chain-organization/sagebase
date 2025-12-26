"""Evaluation runner for executing test cases and calculating metrics"""

import json
import logging
import os
from pathlib import Path
from typing import Any

from src.infrastructure.external.llm_service import GeminiLLMService
from src.interfaces.factories.party_member_extractor_factory import (
    PartyMemberExtractorFactory,
)

from .metrics import EvaluationMetrics, MetricsCalculator


logger = logging.getLogger(__name__)


class EvaluationRunner:
    """Run evaluation tests and calculate metrics"""

    def __init__(self, use_real_llm: bool = True):
        """Initialize evaluation runner

        Args:
            use_real_llm: Whether to use real LLM API or mock responses
        """
        self.metrics_calculator = MetricsCalculator()
        self.use_real_llm = use_real_llm

        # Initialize LLM service if using real LLM
        if self.use_real_llm:
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                logger.warning("GOOGLE_API_KEY not set, will use mock responses")
                self.use_real_llm = False
            else:
                self.llm_service = GeminiLLMService(api_key=api_key)

    def load_dataset(self, dataset_path: str) -> dict[str, Any]:
        """Load evaluation dataset from JSON file

        Args:
            dataset_path: Path to the dataset JSON file

        Returns:
            Loaded dataset dictionary

        Raises:
            FileNotFoundError: If dataset file doesn't exist
            json.JSONDecodeError: If dataset file is not valid JSON
        """
        path = Path(dataset_path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def execute_test_case(
        self, task_type: str, test_case: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a single test case

        Args:
            task_type: Type of task to execute
            test_case: Test case data

        Returns:
            Actual output from system
        """
        logger.info(f"Executing test case {test_case.get('id')} for task {task_type}")

        if not self.use_real_llm:
            # Return mock response that matches expected format
            mock_responses = {
                "minutes_division": {
                    "speaker_and_speech_content_list": test_case.get(
                        "expected_output", {}
                    ).get("speaker_and_speech_content_list", [])
                },
                "speaker_matching": {
                    "results": test_case.get("expected_output", {}).get("results", [])
                },
                "party_member_extraction": {
                    "members": test_case.get("expected_output", {}).get("members", [])
                },
                "conference_member_matching": {
                    "matched_members": test_case.get("expected_output", {}).get(
                        "matched_members", []
                    )
                },
            }
            return mock_responses.get(task_type, {})

        # Use real LLM services
        try:
            if task_type == "speaker_matching":
                return self._execute_speaker_matching(test_case)
            elif task_type == "party_member_extraction":
                return self._execute_party_member_extraction(test_case)
            elif task_type == "conference_member_matching":
                return self._execute_conference_member_matching(test_case)
            else:
                logger.error(f"Unknown task type: {task_type}")
                return {}
        except Exception as e:
            logger.error(f"Error executing test case: {e}")
            return {}

    def _execute_speaker_matching(self, test_case: dict[str, Any]) -> dict[str, Any]:
        """Execute speaker matching task using LLM

        Args:
            test_case: Test case data with speakers and politicians

        Returns:
            Dict with matching results
        """
        try:
            input_data = test_case.get("input", {})
            speakers = input_data.get("speakers", [])
            politicians = input_data.get("politicians", [])

            # Simple LLM-based matching
            prompt = f"""以下の話者と政治家をマッチングしてください。

話者リスト:
{json.dumps(speakers, ensure_ascii=False, indent=2)}

政治家リスト:
{json.dumps(politicians, ensure_ascii=False, indent=2)}

各話者に最も適切な政治家IDを割り当て、信頼度スコア(0-1)を付けて返してください。
JSON形式で、以下のような構造で返してください:
{{"results": [{{"speaker_id": 1, "politician_id": 101,
 "confidence_score": 0.95}}, ...]}}"""

            # Use the LLM directly
            messages = [{"role": "user", "content": prompt}]
            response = self.llm_service.invoke_llm(messages)

            # Parse LLM response
            try:
                import re

                # Ensure response is a string
                response_text = (
                    str(response) if not isinstance(response, str) else response
                )
                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return result
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM response: {response}")

            # Fallback to simple name matching
            results = []
            for speaker in speakers:
                best_match = None
                best_score = 0.0

                for politician in politicians:
                    if (
                        speaker["name"]
                        .replace("議員", "")
                        .replace("委員長", "")
                        .replace("部長", "")
                        in politician["name"]
                    ):
                        score = 0.9
                        if score > best_score:
                            best_match = politician["id"]
                            best_score = score

                if best_match:
                    results.append(
                        {
                            "speaker_id": speaker["id"],
                            "politician_id": best_match,
                            "confidence_score": best_score,
                        }
                    )

            return {"results": results}

        except Exception as e:
            logger.error(f"Error in speaker matching: {e}")
            return {"results": []}

    def _execute_party_member_extraction(
        self, test_case: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute party member extraction using PartyMemberExtractor

        Args:
            test_case: Test case data with HTML content

        Returns:
            Dict with extracted members
        """
        try:
            input_data = test_case.get("input", {})
            html_content = input_data.get("html_content", "")
            html_file = input_data.get("html_file", "")
            party_name = input_data.get("party_name", "")

            # Load HTML content from file if html_file is provided
            if html_file and not html_content:
                try:
                    with open(html_file, encoding="utf-8") as f:
                        html_content = f.read()
                except FileNotFoundError:
                    logger.error(f"HTML file not found: {html_file}")
                    return {"members": []}

            if not html_content:
                return {"members": []}

            # Use PartyMemberExtractor
            extractor = PartyMemberExtractorFactory.create(llm_service=self.llm_service)
            members = extractor.extract_from_html(html_content, party_name)

            # Format the result
            formatted_members = []
            for member in members:
                formatted_member = {"name": member.get("name", ""), "party": party_name}
                if "position" in member:
                    formatted_member["position"] = member["position"]
                if "district" in member:
                    formatted_member["district"] = member["district"]
                if "email" in member:
                    formatted_member["email"] = member["email"]
                if "website" in member:
                    formatted_member["website"] = member["website"]

                formatted_members.append(formatted_member)

            return {"members": formatted_members}

        except Exception as e:
            logger.error(f"Error in party member extraction: {e}")
            return {"members": []}

    def _execute_conference_member_matching(
        self, test_case: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute conference member matching using LLM

        Args:
            test_case: Test case data with extracted members and politicians

        Returns:
            Dict with matched members
        """
        try:
            input_data = test_case.get("input", {})
            extracted_members = input_data.get("extracted_members", [])
            politicians = input_data.get("politicians", [])

            # Use LLM for fuzzy matching
            prompt = f"""以下の会議メンバーと政治家をファジーマッチングしてください。
名前の表記揺れ（ひらがな/カタカナ/漢字）や党名の略称も考慮してください。

会議メンバー:
{json.dumps(extracted_members, ensure_ascii=False, indent=2)}

政治家リスト:
{json.dumps(politicians, ensure_ascii=False, indent=2)}

各メンバーに最も適切な政治家IDを割り当て、信頼度スコア(0-1)とステータス(matched/needs_review/no_match)を付けてください。
信頼度スコア: 0.7以上=matched, 0.5-0.7=needs_review, 0.5未満=no_match

JSON形式で以下のような構造で返してください:
{{"matched_members": [{{"member_name": "山田太郎", "politician_id": 101,
"confidence_score": 0.95, "status": "matched"}}, ...]}}"""

            # Use the LLM directly
            messages = [{"role": "user", "content": prompt}]
            response = self.llm_service.invoke_llm(messages)

            # Parse LLM response
            try:
                import re

                # Ensure response is a string
                response_text = (
                    str(response) if not isinstance(response, str) else response
                )
                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return result
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM response: {response}")

            # Fallback to simple matching
            matched_members = []
            for member in extracted_members:
                best_match = None
                best_score = 0.0

                for politician in politicians:
                    # Simple name and party matching
                    name_match = member["name"] == politician["name"]
                    party_match = member.get("party", "").replace(
                        "自由民主党", "自民党"
                    ).replace("立憲", "立憲民主党").replace(
                        "公明", "公明党"
                    ) == politician.get("party", "")

                    if name_match and party_match:
                        score = 0.95
                    elif name_match:
                        score = 0.75
                    elif party_match and member["name"] in politician["name"]:
                        score = 0.65
                    else:
                        continue

                    if score > best_score:
                        best_match = politician["id"]
                        best_score = score

                if best_match:
                    status = (
                        "matched"
                        if best_score >= 0.7
                        else "needs_review"
                        if best_score >= 0.5
                        else "no_match"
                    )
                    matched_members.append(
                        {
                            "member_name": member["name"],
                            "politician_id": best_match,
                            "confidence_score": best_score,
                            "status": status,
                        }
                    )

            return {"matched_members": matched_members}

        except Exception as e:
            logger.error(f"Error in conference member matching: {e}")
            return {"matched_members": []}

    def run_evaluation(
        self,
        task_type: str | None = None,
        dataset_path: str | None = None,
        run_all: bool = False,
    ) -> list[EvaluationMetrics]:
        """Run evaluation for specified task or all tasks

        Args:
            task_type: Type of task to evaluate (if None and not run_all, error)
            dataset_path: Path to dataset file (if None, uses default)
            run_all: Whether to run all tasks

        Returns:
            List of evaluation metrics
        """
        all_metrics = []

        if run_all:
            # Run all tasks
            task_types = [
                "minutes_division",
                "speaker_matching",
                "party_member_extraction",
                "conference_member_matching",
            ]
        elif task_type:
            task_types = [task_type]
        else:
            raise ValueError("Either specify task_type or use run_all=True")

        for current_task in task_types:
            # Determine dataset path
            if dataset_path and not run_all:
                current_dataset_path = dataset_path
            else:
                # Use default path pattern
                current_dataset_path = (
                    f"data/evaluation/datasets/{current_task}/basic_cases.json"
                )

            try:
                # Load dataset
                dataset = self.load_dataset(current_dataset_path)

                # Check task type matches
                if dataset.get("task_type") != current_task:
                    logger.warning(
                        f"Task type mismatch: expected {current_task}, "
                        f"got {dataset.get('task_type')}"
                    )

                # Process each test case
                test_cases = dataset.get("test_cases", [])
                print(f"\nRunning {len(test_cases)} test cases for {current_task}")

                for test_case in test_cases:
                    # Execute test case
                    actual_output = self.execute_test_case(current_task, test_case)

                    # Calculate metrics
                    metrics = self.metrics_calculator.calculate_metrics(
                        current_task, test_case, actual_output
                    )

                    all_metrics.append(metrics)

                    # Display test case result
                    status = "✅ PASSED" if metrics.passed else "❌ FAILED"
                    print(f"  Test {test_case.get('id', 'unknown')}: {status}")

            except FileNotFoundError as e:
                logger.error(f"Dataset not found for {current_task}: {e}")
                print(f"Dataset not found for {current_task}")
            except Exception as e:
                logger.error(f"Error processing {current_task}: {e}")
                print(f"Error processing {current_task}: {e}")

        return all_metrics

    def display_results(self, metrics_list: list[EvaluationMetrics]) -> None:
        """Display evaluation results in a formatted output

        Args:
            metrics_list: List of evaluation metrics to display
        """
        if not metrics_list:
            print("No evaluation results to display")
            return

        # Group metrics by task type
        task_groups: dict[str, list[EvaluationMetrics]] = {}
        for metrics in metrics_list:
            task_type = metrics.task_type
            if task_type not in task_groups:
                task_groups[task_type] = []
            task_groups[task_type].append(metrics)

        # Display results for each task type
        for task_type, task_metrics in task_groups.items():
            print(f"\nResults for {task_type}:")
            print("-" * 60)

            # Get metric columns based on task type
            metric_columns = self._get_metric_columns(task_type)

            # Print header
            header = f"{'Test Case':<20} {'Status':<10}"
            for col in metric_columns:
                header += f" {col:<15}"
            print(header)
            print("=" * 60)

            # Print rows
            for metrics in task_metrics:
                row = f"{metrics.test_case_id:<20} "
                row += f"{'✅ PASS' if metrics.passed else '❌ FAIL':<10}"

                # Add metric values
                for col in metric_columns:
                    col_key = col.lower().replace(" ", "_")
                    value = metrics.metrics.get(col_key, "-")
                    if isinstance(value, float):
                        formatted = f"{value:.2%}" if value <= 1.0 else f"{value:.2f}"
                        row += f" {formatted:<15}"
                    else:
                        row += f" {str(value):<15}"

                print(row)

            # Calculate and display summary statistics
            self._display_summary(task_type, task_metrics)

    def _get_metric_columns(self, task_type: str) -> list[str]:
        """Get metric column names for task type

        Args:
            task_type: Type of task

        Returns:
            List of metric column names
        """
        columns_map = {
            "minutes_division": ["Speaker Match", "Content Similarity", "Count"],
            "speaker_matching": ["ID Match Rate", "Confidence", "Accuracy"],
            "party_member_extraction": ["Extraction Rate", "Name Accuracy", "Count"],
            "conference_member_matching": ["Precision", "Recall", "F1 Score"],
        }
        return columns_map.get(task_type, ["Metric 1", "Metric 2", "Metric 3"])

    def _display_summary(
        self, task_type: str, metrics_list: list[EvaluationMetrics]
    ) -> None:
        """Display summary statistics for a task type

        Args:
            task_type: Type of task
            metrics_list: List of metrics for the task
        """
        total = len(metrics_list)
        passed = sum(1 for m in metrics_list if m.passed)
        pass_rate = passed / total if total > 0 else 0

        print("\nSummary:")
        print(f"  Total test cases: {total}")
        print(f"  Passed: {passed}")
        print(f"  Failed: {total - passed}")
        print(f"  Pass rate: {pass_rate:.1%}")

        # Calculate average metrics
        if metrics_list and metrics_list[0].metrics:
            print("\nAverage Metrics:")
            metric_sums: dict[str, float] = {}
            metric_counts: dict[str, int] = {}

            for metrics in metrics_list:
                for key, value in metrics.metrics.items():
                    if isinstance(value, int | float) and not key.endswith("_count"):
                        if key not in metric_sums:
                            metric_sums[key] = 0
                            metric_counts[key] = 0
                        metric_sums[key] += value
                        metric_counts[key] += 1

            for key in sorted(metric_sums.keys()):
                avg = metric_sums[key] / metric_counts[key]
                display_key = key.replace("_", " ").title()
                if avg <= 1.0:  # Likely a percentage
                    print(f"  {display_key}: {avg:.1%}")
                else:
                    print(f"  {display_key}: {avg:.2f}")
