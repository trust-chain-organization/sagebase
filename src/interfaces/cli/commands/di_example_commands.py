"""
Example CLI commands demonstrating Dependency Injection container usage.

This module shows how to integrate the DI container with CLI commands.
"""

import asyncio
import sys
from typing import Any

import click

from src.infrastructure.di.container import ApplicationContainer, init_container


@click.command()
@click.option(
    "--meeting-id",
    type=int,
    required=True,
    help="Meeting ID to process",
)
@click.option(
    "--environment",
    type=click.Choice(["development", "testing", "production"]),
    default="development",
    help="Environment to run in",
)
def process_minutes_with_di(meeting_id: int, environment: str) -> None:
    """Process meeting minutes using DI container.

    This is an example command showing how to use the DI container
    to get dependencies and execute use cases.
    """
    try:
        # Initialize the container for the specified environment
        container = init_container(environment=environment)

        # Get the use case from the container
        process_minutes_usecase = container.use_cases.process_minutes_usecase()

        # Execute the use case
        async def run_process():
            from src.application.dtos.minutes_dto import ProcessMinutesDTO

            input_dto = ProcessMinutesDTO(
                meeting_id=meeting_id,
                force_reprocess=False,
            )

            result = await process_minutes_usecase.execute(input_dto)

            if result.success:
                click.echo(f"✅ Successfully processed meeting {meeting_id}")
                click.echo(f"   Conversations created: {result.conversation_count}")
                click.echo(f"   Speakers extracted: {result.speaker_count}")
            else:
                click.echo(f"❌ Failed to process meeting {meeting_id}")
                if result.error_message:
                    click.echo(f"   Error: {result.error_message}")

        # Run the async function
        asyncio.run(run_process())

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@click.command()
@click.option(
    "--party-id",
    type=int,
    help="Specific party ID to scrape",
)
@click.option(
    "--all-parties",
    is_flag=True,
    help="Scrape all parties",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Perform a dry run without saving to database",
)
def scrape_politicians_with_di(
    party_id: int | None, all_parties: bool, dry_run: bool
) -> None:
    """Scrape politicians using DI container.

    This example shows how to use dependency injection for external service operations.
    """
    if not party_id and not all_parties:
        click.echo("Error: Specify either --party-id or --all-parties", err=True)
        sys.exit(1)

    try:
        # Initialize container
        container = ApplicationContainer.create_for_environment()

        # Get the use case
        scrape_politicians_usecase = container.use_cases.scrape_politicians_usecase()

        # Execute the use case
        async def run_scrape():
            from src.application.dtos.politician_dto import ScrapePoliticiansInputDTO

            if all_parties:
                # Get all parties from repository
                party_repo = container.repositories.political_party_repository()
                parties = await party_repo.find_all()
                party_ids = [party.id for party in parties if party.members_list_url]
            else:
                party_ids = [party_id] if party_id else []

            for pid in party_ids:
                input_dto = ScrapePoliticiansInputDTO(
                    party_id=pid,
                    dry_run=dry_run,
                )

                result = await scrape_politicians_usecase.execute(input_dto)

                # Result is a list of PoliticianDTO
                politician_count = len(result)
                click.echo(f"✅ Party {pid}: {politician_count} politicians processed")

        asyncio.run(run_scrape())

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@click.command()
def show_container_info() -> None:
    """Show information about the DI container configuration.

    This command demonstrates how to inspect the container configuration.
    """
    try:
        # Initialize container
        container = init_container()

        click.echo("DI Container Information")
        click.echo("=" * 40)

        # Show configuration
        config = container.config()
        click.echo("\n📋 Configuration:")
        click.echo(f"   Database URL: {config.get('database_url', 'Not set')[:50]}...")
        click.echo(f"   LLM Model: {config.get('llm_model', 'Not set')}")
        click.echo(f"   LLM Temperature: {config.get('llm_temperature', 'Not set')}")
        click.echo(f"   GCS Bucket: {config.get('gcs_bucket_name', 'Not set')}")

        # Show available providers
        click.echo("\n🔧 Available Providers:")

        # Repositories
        repo_providers = [
            name
            for name in dir(container.repositories)
            if not name.startswith("_") and name.endswith("_repository")
        ]
        click.echo(f"\n   Repositories ({len(repo_providers)}):")
        for repo in repo_providers[:5]:  # Show first 5
            click.echo(f"      - {repo}")
        if len(repo_providers) > 5:
            click.echo(f"      ... and {len(repo_providers) - 5} more")

        # Services
        service_providers = [
            name
            for name in dir(container.services)
            if not name.startswith("_") and name.endswith("_service")
        ]
        click.echo(f"\n   Services ({len(service_providers)}):")
        for service in service_providers:
            click.echo(f"      - {service}")

        # Use Cases
        usecase_providers = [
            name
            for name in dir(container.use_cases)
            if not name.startswith("_") and name.endswith("_usecase")
        ]
        click.echo(f"\n   Use Cases ({len(usecase_providers)}):")
        for usecase in usecase_providers:
            click.echo(f"      - {usecase}")

        click.echo("\n✅ Container initialized successfully")

    except Exception as e:
        click.echo(f"❌ Error initializing container: {e}", err=True)
        sys.exit(1)


@click.command()
@click.option(
    "--check-db",
    is_flag=True,
    help="Check database connection",
)
@click.option(
    "--check-llm",
    is_flag=True,
    help="Check LLM service",
)
@click.option(
    "--check-storage",
    is_flag=True,
    help="Check storage service",
)
def health_check_with_di(check_db: bool, check_llm: bool, check_storage: bool) -> None:
    """Perform health checks using DI container.

    This command demonstrates how to use the container for system health checks.
    """
    if not any([check_db, check_llm, check_storage]):
        check_db = check_llm = check_storage = True

    try:
        container = init_container()
        all_healthy = True

        click.echo("🏥 Health Check Results")
        click.echo("=" * 40)

        if check_db:
            try:
                # Get a database session and test connection
                with container.get_session_context() as session:
                    from sqlalchemy import text

                    result = session.execute(text("SELECT 1"))
                    result.scalar()
                click.echo("✅ Database: Healthy")
            except Exception as e:
                click.echo(f"❌ Database: Unhealthy - {e}")
                all_healthy = False

        if check_llm:
            try:
                # Get LLM service and test
                _ = container.services.llm_service()
                # Just check if service can be instantiated
                click.echo("✅ LLM Service: Configured")
            except Exception as e:
                click.echo(f"❌ LLM Service: Not configured - {e}")
                all_healthy = False

        if check_storage:
            try:
                # Get storage service and test
                _ = container.services.storage_service()
                click.echo("✅ Storage Service: Configured")
            except Exception as e:
                click.echo(f"❌ Storage Service: Not configured - {e}")
                all_healthy = False

        click.echo("\n" + "=" * 40)
        if all_healthy:
            click.echo("✅ All systems operational")
        else:
            click.echo("⚠️ Some systems need attention")
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Health check failed: {e}", err=True)
        sys.exit(1)


def get_di_example_commands() -> list[Any]:
    """Get all DI example commands.

    Returns:
        List of Click command functions.
    """
    return [
        process_minutes_with_di,
        scrape_politicians_with_di,
        show_container_info,
        health_check_with_di,
    ]
