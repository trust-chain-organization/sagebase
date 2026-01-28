#!/bin/bash
# Load seed data into the database
# This script is run after Alembic migrations to populate initial data
#
# Usage: ./scripts/load-seeds.sh [compose_cmd]
# Example: ./scripts/load-seeds.sh "-f docker/docker-compose.yml"

set -e

COMPOSE_CMD="${1:--f docker/docker-compose.yml}"

# Check if governing_bodies table is empty (indicates first run)
GOVERNING_BODIES_COUNT=$(docker compose $COMPOSE_CMD exec -T postgres psql -U sagebase_user -d sagebase_db -t -c "SELECT COUNT(*) FROM governing_bodies;" 2>/dev/null | tr -d ' ' || echo "0")

if [ "$GOVERNING_BODIES_COUNT" = "0" ]; then
    echo "📦 Loading seed data (first run detected)..."

    # Load seeds in order (dependencies matter)
    SEED_FILES=(
        "database/seed_governing_bodies_generated.sql"
        "database/seed_political_parties_generated.sql"
        "database/seed_conferences_generated.sql"
        "database/seed_parliamentary_groups_generated.sql"
        "database/seed_meetings_generated.sql"
        "database/seed_politicians_generated.sql"
    )

    for seed_file in "${SEED_FILES[@]}"; do
        if [ -f "$seed_file" ]; then
            echo "  Loading $seed_file..."
            docker compose $COMPOSE_CMD exec -T postgres psql -U sagebase_user -d sagebase_db < "$seed_file" > /dev/null 2>&1
        else
            echo "  ⚠️ Seed file not found: $seed_file"
        fi
    done

    echo "✅ Seed data loaded!"
else
    echo "📦 Seed data already exists (skipping)"
fi
