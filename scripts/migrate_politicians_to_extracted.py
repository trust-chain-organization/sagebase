#!/usr/bin/env python3
"""Migrate existing politicians data to extracted_politicians table.

This script provides additional validation and rollback capabilities
beyond the SQL migration script.
"""

import asyncio
import logging
import sys

from datetime import datetime
from pathlib import Path


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.domain.entities.politician_party_extracted_politician import (
    PoliticianPartyExtractedPolitician,
)
from src.infrastructure.config.async_database import get_async_session
from src.infrastructure.persistence.extracted_politician_repository_impl import (
    ExtractedPoliticianRepositoryImpl,
)
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class PoliticianMigrator:
    """Handle migration of politicians to extracted_politicians table."""

    async def migrate(self, dry_run: bool = False) -> None:
        """Migrate politicians to extracted_politicians table.

        Args:
            dry_run: If True, simulate migration without committing changes
        """
        async with get_async_session() as session:
            try:
                politician_repo = PoliticianRepositoryImpl(session)
                extracted_repo = ExtractedPoliticianRepositoryImpl(session)

                # Get all existing politicians
                politicians = await politician_repo.get_all()
                logger.info(f"Found {len(politicians)} politicians to migrate")

                migrated_count = 0
                skipped_count = 0
                error_count = 0

                for politician in politicians:
                    try:
                        # Check if already migrated
                        existing = await extracted_repo.get_duplicates(
                            politician.name, politician.political_party_id
                        )

                        if existing:
                            logger.debug(
                                f"Skipping {politician.name} - already migrated"
                            )
                            skipped_count += 1
                            continue

                        # Create ExtractedPolitician entity
                        extracted = PoliticianPartyExtractedPolitician(
                            name=politician.name,
                            party_id=politician.political_party_id,
                            district=getattr(politician, "electoral_district", None),
                            position=getattr(politician, "position", None),
                            profile_url=getattr(politician, "profile_url", None),
                            image_url=None,  # No image_url in current politicians table
                            status="approved",  # Approved since already in production
                            extracted_at=politician.created_at or datetime.now(),
                            reviewed_at=politician.created_at or datetime.now(),
                            reviewer_id=None,  # No reviewer for historical data
                        )

                        if not dry_run:
                            await extracted_repo.create(extracted)

                        migrated_count += 1
                        logger.info(
                            f"Migrated politician: {politician.name} "
                            f"(party_id: {politician.political_party_id})"
                        )

                    except Exception as e:
                        error_count += 1
                        logger.error(f"Error migrating politician {politician.id}: {e}")
                        if not dry_run:
                            await session.rollback()

                # Summary
                logger.info(
                    f"Migration {'simulation' if dry_run else 'completed'}:"
                    f"\n  - Migrated: {migrated_count}"
                    f"\n  - Skipped (already exists): {skipped_count}"
                    f"\n  - Errors: {error_count}"
                )

            except Exception as e:
                logger.error(f"Migration failed: {e}")
                if not dry_run:
                    await session.rollback()
                raise

    async def verify_migration(self) -> bool:
        """Verify that migration was successful.

        Returns:
            True if migration appears successful, False otherwise
        """
        async with get_async_session() as session:
            try:
                politician_repo = PoliticianRepositoryImpl(session)
                extracted_repo = ExtractedPoliticianRepositoryImpl(session)

                # Count politicians
                politicians = await politician_repo.get_all()
                politician_count = len(politicians)

                # Count extracted politicians with approved status
                extracted = await extracted_repo.get_all()
                approved_count = sum(1 for ep in extracted if ep.status == "approved")

                logger.info(
                    f"Verification:"
                    f"\n  - Politicians table: {politician_count} records"
                    f"\n  - Extracted politicians (approved): {approved_count} records"
                )

                if politician_count != approved_count:
                    missing = politician_count - approved_count
                    logger.warning(f"Counts don't match! Missing {missing} records")
                    return False

                logger.info("Migration verified successfully!")
                return True

            except Exception as e:
                logger.error(f"Verification failed: {e}")
                return False

    async def rollback(self) -> None:
        """Rollback migration by removing migrated records.

        WARNING: This will remove ALL records with 'approved' status
        that have no reviewer_id (indicating they were migrated).
        """
        async with get_async_session() as session:
            try:
                extracted_repo = ExtractedPoliticianRepositoryImpl(session)

                # Find all migrated records (approved with no reviewer)
                extracted = await extracted_repo.get_all()
                migrated = [
                    ep
                    for ep in extracted
                    if ep.status == "approved" and ep.reviewer_id is None
                ]

                logger.info(f"Found {len(migrated)} migrated records to rollback")

                if not migrated:
                    logger.info("No migrated records to rollback")
                    return

                # Confirm before proceeding
                response = input(
                    f"This will delete {len(migrated)} records. Continue? (yes/no): "
                )
                if response.lower() != "yes":
                    logger.info("Rollback cancelled")
                    return

                # Delete migrated records
                deleted_count = 0
                for ep in migrated:
                    if ep.id is not None:
                        await extracted_repo.delete(ep.id)
                        deleted_count += 1
                logger.info(f"Rollback completed: {deleted_count} records deleted")

            except Exception as e:
                logger.error(f"Rollback failed: {e}")
                await session.rollback()
                raise


async def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate politicians to extracted_politicians table"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate migration without making changes",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify migration was successful",
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback migration (removes migrated records)",
    )

    args = parser.parse_args()

    migrator = PoliticianMigrator()

    if args.verify:
        success = await migrator.verify_migration()
        sys.exit(0 if success else 1)
    elif args.rollback:
        await migrator.rollback()
    else:
        await migrator.migrate(dry_run=args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())
