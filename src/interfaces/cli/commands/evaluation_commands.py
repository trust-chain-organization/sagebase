"""CLI commands for LLM evaluation"""

import asyncio

import click

from ..base import BaseCommand, with_error_handling


class EvaluationCommands(BaseCommand):
    """Commands for running LLM evaluation tests"""

    @staticmethod
    @click.command()
    @click.option(
        "--task",
        type=click.Choice(
            [
                "party_member_extraction",
                "conference_member_matching",
            ]
        ),
        help="Type of task to evaluate",
    )
    @click.option(
        "--dataset",
        type=click.Path(exists=True),
        help="Path to evaluation dataset JSON file",
    )
    @click.option(
        "--all",
        "run_all",
        is_flag=True,
        help="Run evaluation for all tasks",
    )
    @click.option(
        "--use-real-llm/--use-mock",
        default=True,
        help="Use real LLM API instead of mock responses (default: use real)",
    )
    @with_error_handling
    def evaluate(
        task: str | None, dataset: str | None, run_all: bool, use_real_llm: bool
    ):
        """Run LLM evaluation tests (LLM評価テストの実行)

        This command runs evaluation tests to measure LLM performance
        on various tasks such as party member extraction and
        conference member matching.

        Examples:
            # Evaluate specific task
            sagebase evaluate --task party_member_extraction

            # Evaluate with custom dataset
            sagebase evaluate --task conference_member_matching --dataset custom.json

            # Evaluate all tasks
            sagebase evaluate --all
        """
        from src.evaluation import EvaluationRunner

        runner = EvaluationRunner(use_real_llm=use_real_llm)

        if use_real_llm:
            click.echo(click.style("🤖 Using real LLM API for evaluation", fg="cyan"))
        else:
            click.echo(
                click.style("📝 Using mock responses for evaluation", fg="yellow")
            )

        # Validate arguments
        if not run_all and not task:
            raise click.UsageError(
                "Either specify --task or use --all to run all tasks"
            )

        if run_all and dataset:
            click.echo(
                click.style(
                    "⚠️  Dataset path is ignored when running all tasks. "
                    "Default datasets will be used.",
                    fg="yellow",
                )
            )

        # Run evaluation
        EvaluationCommands.show_progress("Starting evaluation...")

        try:
            # Run async evaluation
            metrics = asyncio.run(
                runner.run_evaluation(
                    task_type=task,
                    dataset_path=dataset,
                    run_all=run_all,
                )
            )

            # Display results
            runner.display_results(metrics)

            # Check overall success
            if metrics:
                passed = sum(1 for m in metrics if m.passed)
                total = len(metrics)
                pass_rate = passed / total if total > 0 else 0

                if pass_rate >= 0.8:  # 80% pass threshold
                    EvaluationCommands.success(
                        f"Evaluation completed successfully! "
                        f"Pass rate: {pass_rate:.1%} ({passed}/{total})"
                    )
                else:
                    click.echo(
                        click.style(
                            f"⚠️  Evaluation completed with low pass rate: "
                            f"{pass_rate:.1%} ({passed}/{total})",
                            fg="yellow",
                        )
                    )
            else:
                click.echo(click.style("⚠️  No test cases were executed", fg="yellow"))

        except Exception as e:
            EvaluationCommands.error(f"Evaluation failed: {e}")
            raise


def get_evaluation_commands():
    """Get all evaluation-related commands"""
    return [EvaluationCommands.evaluate]
