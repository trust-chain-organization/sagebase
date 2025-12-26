"""Command for analyzing speaker matching history."""

from datetime import datetime, timedelta

import click

from src.interfaces.cli.base import BaseCommand, with_error_handling


class AnalyzeMatchingHistoryCommand:
    """Commands for analyzing speaker matching history."""

    @staticmethod
    @click.command()
    @click.option(
        "--days",
        type=int,
        default=30,
        help="Number of days to analyze (default: 30)",
    )
    @click.option(
        "--conference-id",
        type=int,
        help="Filter by conference ID",
    )
    @click.option(
        "--status",
        type=click.Choice(["all", "completed", "failed"]),
        default="all",
        help="Filter by processing status",
    )
    @click.option(
        "--export-csv",
        type=str,
        help="Export results to CSV file",
    )
    @with_error_handling
    @BaseCommand.async_command
    async def analyze_matching_history(
        days: int, conference_id: int | None, status: str, export_csv: str | None
    ):
        """Analyze speaker matching history (発言者マッチング履歴の分析)

        This command analyzes LLM processing history for speaker matching,
        providing insights on success rates, confidence scores, and failure patterns.

        Examples:
            # Analyze last 30 days
            sagebase analyze-matching-history

            # Analyze specific conference
            sagebase analyze-matching-history --conference-id 123

            # Export to CSV
            sagebase analyze-matching-history --export-csv results.csv
        """

        from src.domain.entities.llm_processing_history import (
            LLMProcessingHistory,
            ProcessingStatus,
            ProcessingType,
        )
        from src.infrastructure.config.async_database import get_async_session
        from src.infrastructure.persistence import LLMProcessingHistoryRepositoryImpl

        BaseCommand.show_progress("Fetching speaker matching history...")

        async with get_async_session() as session:
            repo = LLMProcessingHistoryRepositoryImpl(session)

            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # Get histories by type
            histories = await repo.get_by_processing_type(
                ProcessingType.SPEAKER_MATCHING,
                limit=10000,  # Large limit to get all records
            )

            # Filter by date and status
            filtered_histories: list[LLMProcessingHistory] = []
            for h in histories:
                # Check date range
                if h.created_at and h.created_at < start_date:
                    continue

                # Check status filter
                if status == "completed" and h.status != ProcessingStatus.COMPLETED:
                    continue
                elif status == "failed" and h.status != ProcessingStatus.FAILED:
                    continue

                # Check conference filter
                if conference_id and h.processing_metadata:
                    meta = h.processing_metadata
                    if meta.get("conference_id") != conference_id:
                        continue

                filtered_histories.append(h)

            if not filtered_histories:
                click.echo("⚠ No matching history found for the specified criteria")
                return

            # Analyze results
            total_count = len(filtered_histories)
            completed_count = sum(
                1 for h in filtered_histories if h.status == ProcessingStatus.COMPLETED
            )
            failed_count = sum(
                1 for h in filtered_histories if h.status == ProcessingStatus.FAILED
            )

            # Extract confidence scores and matching results
            matched_count = 0
            unmatched_count = 0
            confidence_scores: list[float] = []
            high_confidence_count = 0
            medium_confidence_count = 0
            low_confidence_count = 0
            failure_reasons: dict[str, int] = {}
            matching_methods: dict[str, int] = {}

            for history in filtered_histories:
                if history.result and history.status == ProcessingStatus.COMPLETED:
                    result = history.result

                    # Check if matched
                    if result.get("matched_id"):
                        matched_count += 1

                        # Get confidence score
                        confidence = result.get("confidence", 0.0)
                        confidence_scores.append(confidence)

                        # Categorize confidence
                        if confidence >= 0.9:
                            high_confidence_count += 1
                        elif confidence >= 0.7:
                            medium_confidence_count += 1
                        else:
                            low_confidence_count += 1

                        # Track matching method
                        method = result.get("method", "unknown")
                        matching_methods[method] = matching_methods.get(method, 0) + 1
                    else:
                        unmatched_count += 1

                        # Track failure reason
                        reason = result.get("reason", "no_match")
                        failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

                elif history.status == ProcessingStatus.FAILED:
                    # Track error message
                    error = history.error_message or "unknown_error"
                    failure_reasons[error] = failure_reasons.get(error, 0) + 1

            # Calculate statistics
            avg_confidence = (
                sum(confidence_scores) / len(confidence_scores)
                if confidence_scores
                else 0
            )
            success_rate = (
                (completed_count / total_count * 100) if total_count > 0 else 0
            )
            match_rate = (
                (matched_count / completed_count * 100) if completed_count > 0 else 0
            )

            # Display results
            click.echo(f"\n{'=' * 60}")
            click.echo("Speaker Matching History Analysis")
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            click.echo(f"Period: {start_str} to {end_str}")
            if conference_id:
                click.echo(f"Conference ID: {conference_id}")
            click.echo(f"{'=' * 60}\n")

            click.echo("📊 Overall Statistics:")
            click.echo(f"  Total Processings: {total_count}")
            click.echo(f"  Completed: {completed_count} ({success_rate:.1f}%)")
            click.echo(
                f"  Failed: {failed_count} ({failed_count / total_count * 100:.1f}%)"
            )
            click.echo()

            if completed_count > 0:
                click.echo("🎯 Matching Results:")
                click.echo(f"  Matched: {matched_count} ({match_rate:.1f}%)")
                unmatched_pct = unmatched_count / completed_count * 100
                click.echo(f"  Unmatched: {unmatched_count} ({unmatched_pct:.1f}%)")
                click.echo()

                if confidence_scores:
                    click.echo("📈 Confidence Distribution:")
                    click.echo(f"  Average Confidence: {avg_confidence:.2f}")
                    high_pct = high_confidence_count / matched_count * 100
                    click.echo(
                        f"  High (≥0.9): {high_confidence_count} ({high_pct:.1f}%)"
                    )
                    med_pct = medium_confidence_count / matched_count * 100
                    click.echo(
                        f"  Medium (0.7-0.9): {medium_confidence_count} "
                        f"({med_pct:.1f}%)"
                    )
                    low_pct = low_confidence_count / matched_count * 100
                    click.echo(f"  Low (<0.7): {low_confidence_count} ({low_pct:.1f}%)")
                    click.echo()

                if matching_methods:
                    click.echo("🔧 Matching Methods:")
                    for method, count in sorted(
                        matching_methods.items(), key=lambda x: x[1], reverse=True
                    ):
                        click.echo(
                            f"  {method}: {count} ({count / matched_count * 100:.1f}%)"
                        )
                    click.echo()

            if failure_reasons:
                click.echo("❌ Failure Patterns:")
                for reason, count in sorted(
                    failure_reasons.items(), key=lambda x: x[1], reverse=True
                )[:5]:
                    # Truncate long reasons
                    display_reason = reason[:50] + "..." if len(reason) > 50 else reason
                    click.echo(f"  {display_reason}: {count}")
                click.echo()

            # Export to CSV if requested
            if export_csv:
                BaseCommand.show_progress(f"Exporting results to {export_csv}...")

                import csv
                import os

                # Ensure directory exists
                os.makedirs(
                    os.path.dirname(export_csv) if os.path.dirname(export_csv) else ".",
                    exist_ok=True,
                )

                with open(export_csv, "w", newline="", encoding="utf-8") as csvfile:
                    fieldnames = [
                        "id",
                        "created_at",
                        "status",
                        "speaker_name",
                        "matched_id",
                        "confidence",
                        "method",
                        "reason",
                        "processing_time_ms",
                    ]
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()

                    for history in filtered_histories:
                        row: dict[str, str] = {
                            "id": str(history.id),
                            "created_at": history.created_at.isoformat()
                            if history.created_at
                            else "",
                            "status": history.status.value if history.status else "",
                            "speaker_name": "",
                            "matched_id": "",
                            "confidence": "",
                            "method": "",
                            "reason": "",
                            "processing_time_ms": "",
                        }

                        # Extract speaker name from prompt variables
                        if history.prompt_variables:
                            row["speaker_name"] = history.prompt_variables.get(
                                "speaker_name", ""
                            )

                        # Extract results
                        if history.result:
                            result = history.result
                            row["matched_id"] = str(result.get("matched_id", ""))
                            row["confidence"] = str(result.get("confidence", ""))
                            row["method"] = result.get("method", "")
                            row["reason"] = result.get("reason", "")

                        # Calculate processing time
                        if history.started_at and history.completed_at:
                            delta = history.completed_at - history.started_at
                            row["processing_time_ms"] = str(
                                int(delta.total_seconds() * 1000)
                            )

                        writer.writerow(row)

                BaseCommand.success(f"Results exported to {export_csv}")

            # Provide recommendations
            click.echo("💡 Recommendations:")
            if avg_confidence < 0.8:
                click.echo(
                    "  - Low average confidence. "
                    "Consider improving prompts or candidate filtering."
                )
            if match_rate < 70:
                click.echo(
                    "  - Low match rate. "
                    "Review unmatched speakers for data quality issues."
                )
            if failed_count > total_count * 0.1:
                click.echo(
                    "  - High failure rate. Check API limits and error patterns."
                )
            if low_confidence_count > matched_count * 0.2:
                click.echo(
                    "  - Many low-confidence matches. Manual review recommended."
                )

        BaseCommand.success("Analysis completed successfully")


def get_analyze_matching_history_command():
    """Get the analyze matching history command."""
    return AnalyzeMatchingHistoryCommand.analyze_matching_history
