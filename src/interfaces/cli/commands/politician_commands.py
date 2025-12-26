"""CLI commands for politician data processing"""

import asyncio
import time
from typing import Any

import click
from sqlalchemy import text

from ..base import BaseCommand, with_error_handling
from ..progress import ProgressTracker, spinner


class PoliticianCommands(BaseCommand):
    """Commands for processing politician data"""

    @staticmethod
    @click.command()
    @click.option("--party-id", type=int, help="Specific party ID to scrape")
    @click.option(
        "--all-parties", is_flag=True, help="Scrape all parties with member list URLs"
    )
    @click.option(
        "--dry-run", is_flag=True, help="Show what would be scraped without saving"
    )
    @click.option("--max-pages", default=10, help="Maximum pages to fetch per party")
    @click.option(
        "--hierarchical",
        is_flag=True,
        help="Enable hierarchical page exploration (experimental)",
    )
    @click.option(
        "--max-depth",
        type=int,
        default=3,
        help="Maximum depth for hierarchical exploration",
    )
    @with_error_handling
    def scrape_politicians(
        party_id: int | None,
        all_parties: bool,
        dry_run: bool,
        max_pages: int,
        hierarchical: bool,
        max_depth: int,
    ):
        """Scrape politician data from party member list pages (政党議員一覧取得)

        This command fetches politician information from political party websites
        using LLM to extract structured data and saves them to the database.

        Examples:
            sagebase scrape-politicians --party-id 1
            sagebase scrape-politicians --all-parties
            sagebase scrape-politicians --all-parties --dry-run
            sagebase scrape-politicians --party-id 1 --hierarchical --max-depth 3
        """
        # Run the async scraping operation
        asyncio.run(
            PoliticianCommands._async_scrape_politicians(
                party_id, all_parties, dry_run, max_pages, hierarchical, max_depth
            )
        )

    @staticmethod
    async def _async_scrape_politicians(
        party_id: int | None,
        all_parties: bool,
        dry_run: bool,
        max_pages: int,
        hierarchical: bool,
        max_depth: int,
    ):
        """Async implementation of scrape_politicians"""
        # If hierarchical mode is enabled, use the new Agent-based approach
        if hierarchical:
            await PoliticianCommands._async_scrape_politicians_hierarchical(
                party_id, all_parties, dry_run, max_depth
            )
            return
        from src.infrastructure.config.database import get_db_engine
        from src.infrastructure.persistence.politician_repository_sync_impl import (
            PoliticianRepositorySyncImpl,
        )
        from src.interfaces.factories.party_member_extractor_factory import (
            PartyMemberExtractorFactory,
        )
        from src.party_member_extractor.html_fetcher import PartyMemberPageFetcher

        engine = get_db_engine()

        try:
            # 対象の政党を取得
            with engine.connect() as conn:
                if party_id:
                    query = text("""
                        SELECT id, name, members_list_url
                        FROM political_parties
                        WHERE id = :party_id AND members_list_url IS NOT NULL
                    """)
                    result = conn.execute(query, {"party_id": party_id})
                else:
                    query = text("""
                        SELECT id, name, members_list_url
                        FROM political_parties
                        WHERE members_list_url IS NOT NULL
                        ORDER BY name
                    """)
                    result = conn.execute(query)

                parties = result.fetchall()

            if not parties:
                PoliticianCommands.error(
                    "No parties found with member list URLs", exit_code=0
                )
                return

            PoliticianCommands.show_progress(f"Found {len(parties)} parties to scrape:")
            for party in parties:
                PoliticianCommands.show_progress(
                    f"  - {party.name}: {party.members_list_url}"
                )

            # Streamlitから実行される場合は確認をスキップ
            import os

            if os.environ.get("STREAMLIT_RUNNING") != "true":
                if not PoliticianCommands.confirm("\nDo you want to continue?"):
                    return

            # スクレイピング実行
            total_scraped = 0

            # HTMLフェッチャーを初期化
            with spinner("Initializing extractors"):
                pass  # extractor will be initialized per party

            async with PartyMemberPageFetcher() as fetcher:
                with ProgressTracker(len(parties), "Processing parties") as tracker:
                    for _i, party in enumerate(parties):
                        PoliticianCommands.show_progress(
                            f"\nProcessing {party.name}..."
                        )
                        PoliticianCommands.show_progress(
                            f"  URL: {party.members_list_url}"
                        )

                        # Initialize extractor
                        extractor = PartyMemberExtractorFactory.create()

                        # HTMLページを取得（ページネーション対応）
                        with spinner(
                            f"Fetching pages from {party.name} (max: {max_pages})..."
                        ):
                            pages = await fetcher.fetch_all_pages(
                                party.members_list_url, max_pages=max_pages
                            )

                        if not pages:
                            PoliticianCommands.show_progress(
                                f"  Failed to fetch pages for {party.name}"
                            )
                            continue

                        PoliticianCommands.show_progress(
                            f"  Fetched {len(pages)} pages"
                        )

                        # LLMで議員情報を抽出
                        with spinner(
                            f"Extracting member information using LLM for "
                            f"{party.name}..."
                        ):
                            result = await extractor.extract_from_pages(
                                pages, party.name
                            )

                        if not result or not result.members:
                            PoliticianCommands.show_progress(
                                f"  No members found for {party.name}"
                            )
                            continue

                        PoliticianCommands.show_progress(
                            f"  Extracted {len(result.members)} members"
                        )

                        if dry_run:
                            # ドライランモード：データを表示するだけ
                            for member in result.members[:5]:  # 最初の5件を表示
                                PoliticianCommands.show_progress(f"    - {member.name}")
                                if member.position:
                                    PoliticianCommands.show_progress(
                                        f"      Position: {member.position}"
                                    )
                                if member.electoral_district:
                                    PoliticianCommands.show_progress(
                                        f"      District: {member.electoral_district}"
                                    )
                                if member.prefecture:
                                    PoliticianCommands.show_progress(
                                        f"      Prefecture: {member.prefecture}"
                                    )
                                if member.party_position:
                                    PoliticianCommands.show_progress(
                                        f"      Party Role: {member.party_position}"
                                    )
                            if len(result.members) > 5:
                                PoliticianCommands.show_progress(
                                    f"    ... and {len(result.members) - 5} more"
                                )
                        else:
                            # データベースに保存
                            with spinner(
                                f"Saving {len(result.members)} members to database..."
                            ):
                                from src.infrastructure.config.database import (
                                    get_db_session,
                                )

                                session = get_db_session()
                                repo = PoliticianRepositorySyncImpl(session)

                                # Pydanticモデルを辞書に変換して
                                # political_party_idを追加
                                members_data: list[dict[str, Any]] = []
                                for member in result.members:
                                    member_dict = member.model_dump()
                                    member_dict["political_party_id"] = party.id
                                    members_data.append(member_dict)

                                stats = repo.bulk_create_politicians_sync(members_data)
                                session.close()

                            # 統計情報を表示
                            PoliticianCommands.show_progress(
                                "  Database operation results:"
                            )
                            PoliticianCommands.show_progress(
                                f"    - Created: {len(stats['created'])} "
                                "new politicians"
                            )
                            PoliticianCommands.show_progress(
                                f"    - Updated: {len(stats['updated'])} "
                                "existing politicians"
                            )
                            PoliticianCommands.show_progress(
                                f"    - Errors: {len(stats['errors'])}"
                            )

                            total_scraped += len(stats["created"]) + len(
                                stats["updated"]
                            )

                        tracker.update(1, f"Completed {party.name}")

            if not dry_run:
                PoliticianCommands.success(f"Total politicians saved: {total_scraped}")

        finally:
            engine.dispose()
            # 少し待機してから終了
            time.sleep(0.5)

    @staticmethod
    async def _async_scrape_politicians_hierarchical(
        party_id: int | None, all_parties: bool, dry_run: bool, max_depth: int
    ):
        """Async implementation using hierarchical Agent-based scraping"""
        from src.domain.entities.party_scraping_state import PartyScrapingState
        from src.infrastructure.config.database import get_db_engine
        from src.infrastructure.di.container import get_container, init_container
        from src.infrastructure.persistence.politician_repository_sync_impl import (
            PoliticianRepositorySyncImpl,
        )

        # Initialize DI container
        try:
            container = get_container()
        except RuntimeError:
            container = init_container()

        # Get Agent and dependencies from container
        agent = container.use_cases.party_scraping_agent()
        engine = get_db_engine()

        try:
            # Get target parties
            with engine.connect() as conn:
                if party_id:
                    query = text("""
                        SELECT id, name, members_list_url
                        FROM political_parties
                        WHERE id = :party_id AND members_list_url IS NOT NULL
                    """)
                    result = conn.execute(query, {"party_id": party_id})
                else:
                    query = text("""
                        SELECT id, name, members_list_url
                        FROM political_parties
                        WHERE members_list_url IS NOT NULL
                        ORDER BY name
                    """)
                    result = conn.execute(query)

                parties = result.fetchall()

            if not parties:
                PoliticianCommands.error(
                    "No parties found with member list URLs", exit_code=0
                )
                return

            PoliticianCommands.show_progress(
                f"Found {len(parties)} parties to scrape (hierarchical mode):"
            )
            for party in parties:
                PoliticianCommands.show_progress(
                    f"  - {party.name}: {party.members_list_url}"
                )

            # Skip confirmation if running from Streamlit
            import os

            if os.environ.get("STREAMLIT_RUNNING") != "true":
                if not PoliticianCommands.confirm("\nDo you want to continue?"):
                    return

            # Execute hierarchical scraping
            total_scraped = 0

            with ProgressTracker(len(parties), "Processing parties") as tracker:
                for _i, party in enumerate(parties):
                    PoliticianCommands.show_progress(f"\nProcessing {party.name}...")
                    PoliticianCommands.show_progress(f"  URL: {party.members_list_url}")

                    # Create initial scraping state
                    initial_state = PartyScrapingState(
                        current_url=party.members_list_url,
                        party_name=party.name,
                        party_id=party.id,
                        max_depth=max_depth,
                    )

                    # Run Agent
                    with spinner(
                        f"Running hierarchical scraping for {party.name} "
                        f"(max depth: {max_depth})..."
                    ):
                        final_state = await agent.scrape(initial_state)

                    if final_state.error_message:
                        PoliticianCommands.show_progress(
                            f"  Error: {final_state.error_message}"
                        )
                        continue

                    extracted_members = list(final_state.extracted_members)
                    PoliticianCommands.show_progress(
                        f"  Extracted {len(extracted_members)} members from "
                        f"{len(final_state.visited_urls)} pages"
                    )

                    if dry_run:
                        # Dry run mode: display data only
                        for member in extracted_members[:5]:
                            PoliticianCommands.show_progress(f"    - {member['name']}")
                            if member.get("position"):
                                PoliticianCommands.show_progress(
                                    f"      Position: {member['position']}"
                                )
                            if member.get("electoral_district"):
                                PoliticianCommands.show_progress(
                                    f"      District: {member['electoral_district']}"
                                )
                        if len(extracted_members) > 5:
                            PoliticianCommands.show_progress(
                                f"    ... and {len(extracted_members) - 5} more"
                            )
                    else:
                        # Save to database
                        with spinner(
                            f"Saving {len(extracted_members)} members to database..."
                        ):
                            from src.infrastructure.config.database import (
                                get_db_session,
                            )

                            session = get_db_session()
                            repo = PoliticianRepositorySyncImpl(session)

                            # Convert to dict and add political_party_id
                            members_data: list[dict[str, Any]] = []
                            for member in extracted_members:
                                member_dict = dict(member)
                                member_dict["political_party_id"] = party.id
                                members_data.append(member_dict)

                            stats = repo.bulk_create_politicians_sync(members_data)
                            session.close()

                        # Display statistics
                        PoliticianCommands.show_progress(
                            "  Database operation results:"
                        )
                        PoliticianCommands.show_progress(
                            f"    - Created: {len(stats['created'])} new politicians"
                        )
                        PoliticianCommands.show_progress(
                            f"    - Updated: {len(stats['updated'])} "
                            "existing politicians"
                        )
                        PoliticianCommands.show_progress(
                            f"    - Errors: {len(stats['errors'])}"
                        )

                        total_scraped += len(stats["created"]) + len(stats["updated"])

                    tracker.update(1, f"Completed {party.name}")

            if not dry_run:
                PoliticianCommands.success(f"Total politicians saved: {total_scraped}")

        finally:
            engine.dispose()
            # Wait a bit before exiting
            time.sleep(0.5)

    @staticmethod
    @click.command()
    @click.option("--party-id", type=int, help="Specific party ID to convert")
    @click.option(
        "--batch-size",
        type=int,
        default=100,
        help="Number of records to process at once",
    )
    @click.option(
        "--dry-run", is_flag=True, help="Preview what would be converted without saving"
    )
    @with_error_handling
    def convert_politicians(party_id: int | None, batch_size: int, dry_run: bool):
        """Convert approved extracted politicians to main politicians table

        This command processes extracted_politicians records with status='approved'
        and converts them to the main politicians/speakers tables.

        Examples:
            sagebase convert-politicians
            sagebase convert-politicians --party-id 1
            sagebase convert-politicians --batch-size 50 --dry-run
        """
        asyncio.run(
            PoliticianCommands._async_convert_politicians(party_id, batch_size, dry_run)
        )

    @staticmethod
    async def _async_convert_politicians(
        party_id: int | None, batch_size: int, dry_run: bool
    ):
        """Async implementation of convert_politicians"""
        from src.application.dtos.convert_extracted_politician_dto import (
            ConvertExtractedPoliticianInputDTO,
        )
        from src.infrastructure.di.container import get_container, init_container

        # Initialize and get dependencies from DI container
        try:
            container = get_container()
        except RuntimeError:
            container = init_container()

        use_case = container.use_cases.convert_extracted_politician_usecase()

        # Create input DTO
        input_dto = ConvertExtractedPoliticianInputDTO(
            party_id=party_id, batch_size=batch_size, dry_run=dry_run
        )

        # Show what will be processed
        if dry_run:
            PoliticianCommands.show_progress(
                "Running in DRY-RUN mode - no changes will be saved"
            )

        with spinner("Processing approved extracted politicians..."):
            result = await use_case.execute(input_dto)

        # Display results
        PoliticianCommands.show_progress("\n=== Conversion Results ===")
        PoliticianCommands.show_progress(f"Total processed: {result.total_processed}")
        PoliticianCommands.show_progress(
            f"Successfully converted: {result.converted_count}"
        )

        if result.converted_count > 0:
            PoliticianCommands.show_progress("\nConverted politicians:")
            for politician in result.converted_politicians[:10]:
                PoliticianCommands.show_progress(
                    f"  ✓ {politician.name} (ID: {politician.politician_id})"
                )
            if len(result.converted_politicians) > 10:
                PoliticianCommands.show_progress(
                    f"  ... and {len(result.converted_politicians) - 10} more"
                )

        if result.skipped_count > 0:
            PoliticianCommands.show_progress(f"\nSkipped: {result.skipped_count}")
            for name in result.skipped_names[:5]:
                PoliticianCommands.show_progress(f"  - {name}")
            if len(result.skipped_names) > 5:
                PoliticianCommands.show_progress(
                    f"  ... and {len(result.skipped_names) - 5} more"
                )

        if result.error_count > 0:
            PoliticianCommands.show_progress(f"\nErrors: {result.error_count}")
            for msg in result.error_messages[:5]:
                PoliticianCommands.show_progress(f"  ✗ {msg}")
            if len(result.error_messages) > 5:
                PoliticianCommands.show_progress(
                    f"  ... and {len(result.error_messages) - 5} more"
                )

        if not dry_run and result.converted_count > 0:
            PoliticianCommands.success(
                f"Successfully converted {result.converted_count} politicians"
            )
        elif dry_run:
            PoliticianCommands.show_progress(
                f"\nDRY-RUN completed: {result.converted_count} politicians "
                f"would be converted"
            )
        else:
            PoliticianCommands.show_progress("No politicians were converted")

        # 少し待機してから終了
        time.sleep(0.5)


def get_politician_commands():
    """Get all politician-related commands"""
    return [
        PoliticianCommands.scrape_politicians,
        PoliticianCommands.convert_politicians,
    ]
