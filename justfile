# justfile with git worktree support

# Setup worktree ports if needed (only runs in worktree)
_setup_worktree:
	#!/bin/bash
	if [ ! -f docker/docker-compose.override.yml ]; then
		if [ "$(git rev-parse --git-common-dir 2>/dev/null)" != ".git" ]; then
			echo "Git worktree detected. Setting up port configuration..."
			./scripts/setup-worktree-ports.sh
			# Also setup Streamlit secrets with the correct port
			./scripts/setup-streamlit-secrets.sh
			# Initialize git submodules (for Hugo theme)
			echo "Initializing git submodules..."
			git submodule update --init --recursive
		elif [ -d website/themes/PaperMod ] && [ -z "$(ls -A website/themes/PaperMod)" ]; then
			# Main branch (non-worktree): Initialize submodules if PaperMod is empty
			echo "Initializing git submodules..."
			git submodule update --init --recursive
		fi
	elif [ -f docker/docker-compose.override.yml ]; then
		# Update config.toml if it doesn't exist or if secrets.toml exists
		if [ ! -f .streamlit/config.toml ] || [ -f .streamlit/secrets.toml ]; then
			./scripts/setup-streamlit-secrets.sh
		fi
		# Check if submodules are initialized
		if [ -d website/themes/PaperMod ] && [ -z "$(ls -A website/themes/PaperMod)" ]; then
			echo "Initializing git submodules..."
			git submodule update --init --recursive
		fi
	fi

# Get compose command based on override file existence
compose_cmd := `if [ -f docker/docker-compose.override.yml ]; then echo "-f docker/docker-compose.yml -f docker/docker-compose.override.yml"; else echo "-f docker/docker-compose.yml"; fi`

default: format

# Stop and remove containers
down: _setup_worktree
	docker compose {{compose_cmd}} down --remove-orphans

# Start containers in background (for CI/testing)
up-detached: _setup_worktree
	#!/bin/bash
	docker compose {{compose_cmd}} up -d
	echo "Waiting for containers to be ready..."
	sleep 3
	# Run database migrations with Alembic (idempotent - safe to run every time)
	echo "Running database migrations with Alembic..."
	docker compose {{compose_cmd}} exec sagebase uv run alembic upgrade head 2>&1 || true
	echo "✅ Migrations complete!"
	# Load seed data (only on first run)
	./scripts/load-seeds.sh "{{compose_cmd}}"
	echo "Containers started in detached mode"
	echo "Run 'just logs' to view logs"

# Fast start without rebuild (use when no Dockerfile/dependency changes)
up-fast: _setup_worktree
	#!/bin/bash
	# Start containers without rebuilding (fast startup)
	docker compose {{compose_cmd}} up -d
	# Wait for containers to be healthy
	echo "Waiting for containers to be ready..."
	sleep 3
	# Run database migrations with Alembic (idempotent - safe to run every time)
	echo "Running database migrations with Alembic..."
	docker compose {{compose_cmd}} exec sagebase uv run alembic upgrade head 2>&1 || true
	echo "✅ Migrations complete!"
	# Load seed data (only on first run)
	./scripts/load-seeds.sh "{{compose_cmd}}"
	# Run test-setup.sh if it exists (for initial database setup)
	if [ -f scripts/test-setup.sh ] && docker compose {{compose_cmd}} exec postgres psql -U sagebase_user -d sagebase_db -c "SELECT COUNT(*) FROM meetings;" 2>/dev/null | grep -q "0"; then
		echo "Setting up test data..."
		./scripts/test-setup.sh
	fi
	# Detect actual host port from docker-compose.override.yml if it exists
	if [ -f docker/docker-compose.override.yml ]; then
		HOST_PORT=$(grep ":8501" docker/docker-compose.override.yml | awk -F'"' '{print $2}' | cut -d: -f1)
	else
		HOST_PORT=8501
	fi
	# Check if Streamlit is already running in the container
	if docker compose {{compose_cmd}} exec sagebase pgrep -f "streamlit run" > /dev/null 2>&1; then
		echo "🔄 Streamlit is already running, restarting to apply changes..."
		docker compose {{compose_cmd}} exec sagebase pkill -f "streamlit run" || true
		sleep 2
	fi
	if [ -n "$HOST_PORT" ] && [ "$HOST_PORT" != "8501" ]; then
		echo "Starting Streamlit on port $HOST_PORT..."
		echo "Press Ctrl+C to stop the server"
		echo ""
		docker compose {{compose_cmd}} exec -e STREAMLIT_HOST_PORT=$HOST_PORT sagebase uv run sagebase streamlit
	else
		echo "Starting Streamlit..."
		echo "Press Ctrl+C to stop the server"
		echo ""
		docker compose {{compose_cmd}} exec sagebase uv run sagebase streamlit
	fi

# Start containers and launch Streamlit (foreground mode with logs)
up: _setup_worktree
	#!/bin/bash
	# Start containers in background first (with automatic rebuild if needed)
	docker compose {{compose_cmd}} up -d --build
	# Wait for containers to be healthy
	echo "Waiting for containers to be ready..."
	sleep 3
	# Run database migrations with Alembic (idempotent - safe to run every time)
	echo "Running database migrations with Alembic..."
	docker compose {{compose_cmd}} exec sagebase uv run alembic upgrade head 2>&1 || true
	echo "✅ Migrations complete!"
	# Load seed data (only on first run)
	./scripts/load-seeds.sh "{{compose_cmd}}"
	# Note: Playwright is pre-installed in Dockerfile, no need to install here
	# Run test-setup.sh if it exists (for initial database setup)
	if [ -f scripts/test-setup.sh ] && docker compose {{compose_cmd}} exec postgres psql -U sagebase_user -d sagebase_db -c "SELECT COUNT(*) FROM meetings;" 2>/dev/null | grep -q "0"; then
		echo "Setting up test data..."
		./scripts/test-setup.sh
	fi
	# Detect actual host port from docker-compose.override.yml if it exists
	if [ -f docker/docker-compose.override.yml ]; then
		HOST_PORT=$(grep ":8501" docker/docker-compose.override.yml | awk -F'"' '{print $2}' | cut -d: -f1)
	else
		HOST_PORT=8501
	fi
	# Check if Streamlit is already running in the container
	if docker compose {{compose_cmd}} exec sagebase pgrep -f "streamlit run" > /dev/null 2>&1; then
		echo "🔄 Streamlit is already running, restarting to apply changes..."
		docker compose {{compose_cmd}} exec sagebase pkill -f "streamlit run" || true
		sleep 2
	fi
	if [ -n "$HOST_PORT" ] && [ "$HOST_PORT" != "8501" ]; then
		echo "Starting Streamlit on port $HOST_PORT..."
		echo "Press Ctrl+C to stop the server"
		echo ""
		# Use exec without -d flag to keep logs flowing
		docker compose {{compose_cmd}} exec -e STREAMLIT_HOST_PORT=$HOST_PORT sagebase uv run sagebase streamlit
	else
		echo "Starting Streamlit..."
		echo "Press Ctrl+C to stop the server"
		echo ""
		docker compose {{compose_cmd}} exec sagebase uv run sagebase streamlit
	fi

# Connect to database
db: _setup_worktree
	docker compose {{compose_cmd}} exec postgres psql -U sagebase_user -d sagebase_db

# Run database migrations with Alembic (safe to run multiple times, won't lose data)
migrate: _setup_worktree
	#!/bin/bash
	echo "Running database migrations with Alembic..."
	docker compose {{compose_cmd}} exec sagebase uv run alembic upgrade head
	echo "✅ Migrations complete!"

# Rollback the last migration
migrate-rollback: _setup_worktree
	#!/bin/bash
	echo "Rolling back last migration..."
	docker compose {{compose_cmd}} exec sagebase uv run alembic downgrade -1
	echo "✅ Rollback complete!"

# Show current migration version
migrate-current: _setup_worktree
	docker compose {{compose_cmd}} exec sagebase uv run alembic current

# Show migration history
migrate-history: _setup_worktree
	docker compose {{compose_cmd}} exec sagebase uv run alembic history

# Create a new migration file
migrate-new message: _setup_worktree
	docker compose {{compose_cmd}} exec sagebase uv run alembic revision -m "{{message}}"

# Run tests with type checking
test: _setup_worktree
	uv run --frozen pyright
	docker compose {{compose_cmd}} up -d
	docker compose {{compose_cmd}} exec sagebase uv run pytest

# Format code
format:
	uv run --frozen ruff format .

# Lint code
lint:
	uv run --frozen ruff check . --fix

# Run pytest only
pytest: _setup_worktree
	docker compose {{compose_cmd}} exec sagebase uv run pytest

# Run monitoring dashboard
monitoring: _setup_worktree
	#!/bin/bash
	# Detect actual host port from docker-compose.override.yml if it exists
	if [ -f docker/docker-compose.override.yml ]; then
		HOST_PORT=$(grep ":8502" docker/docker-compose.override.yml | awk -F'"' '{print $2}' | cut -d: -f1)
		if [ -n "$HOST_PORT" ]; then
			docker compose {{compose_cmd}} exec -e MONITORING_HOST_PORT=$HOST_PORT sagebase uv run sagebase monitoring
		else
			docker compose {{compose_cmd}} exec sagebase uv run sagebase monitoring
		fi
	else
		docker compose {{compose_cmd}} exec sagebase uv run sagebase monitoring
	fi

# Launch BI Dashboard (Plotly Dash) on port 8050
bi-dashboard: _setup_worktree
	#!/bin/bash
	echo "Starting BI Dashboard (Plotly Dash)..."
	docker compose {{compose_cmd}} up bi-dashboard --build
	echo "Access at: http://localhost:8050"

# Launch BI Dashboard in background
bi-dashboard-up: _setup_worktree
	#!/bin/bash
	docker compose {{compose_cmd}} up -d bi-dashboard --build
	echo "BI Dashboard started in background"
	echo "Access at: http://localhost:8050"

# Stop BI Dashboard
bi-dashboard-down: _setup_worktree
	docker compose {{compose_cmd}} stop bi-dashboard

# Launch Website (Hugo) on port 1313
website: _setup_worktree
	#!/bin/bash
	echo "Starting Website (Hugo)..."
	docker compose {{compose_cmd}} up website --build
	echo "Access at: http://localhost:1313"

# Launch Website in background
website-up: _setup_worktree
	#!/bin/bash
	docker compose {{compose_cmd}} up -d website --build
	echo "Website started in background"
	echo "Access at: http://localhost:1313"

# Stop Website
website-down: _setup_worktree
	docker compose {{compose_cmd}} stop website

# Process meeting minutes
process-minutes: _setup_worktree
	docker compose {{compose_cmd}} exec sagebase uv run sagebase process-minutes

# Show all available CLI commands
help: _setup_worktree
	docker compose {{compose_cmd}} exec sagebase uv run sagebase --help

# Build containers (with cache)
build: _setup_worktree
	docker compose {{compose_cmd}} build

# Rebuild containers (no cache)
rebuild: _setup_worktree
	docker compose {{compose_cmd}} build --no-cache

# View logs
logs: _setup_worktree
	docker compose {{compose_cmd}} logs -f

# Execute arbitrary command in container
exec *args: _setup_worktree
	docker compose {{compose_cmd}} exec sagebase {{args}}

# Clean up all containers and volumes (dangerous!)
clean: down
	docker compose -f docker/docker-compose.yml down -v
	docker compose -f docker/docker-compose.yml rm -f

# Show current port configuration
ports:
	#!/bin/bash
	if [ -f docker/docker-compose.override.yml ]; then
		echo "Current port configuration (from override):"
		grep -A1 "ports:" docker/docker-compose.override.yml | grep -E "[0-9]+:" | sed 's/.*- "/  /' | sed 's/"//'
	else
		echo "Using default port configuration"
	fi

# === GCP Cloud Management ===

# Start GCP development environment (restore from GCS backup)
cloud-up:
	@echo "🚀 Starting GCP development environment..."
	./scripts/cloud/setup-dev-env.sh

# Stop GCP development environment (backup to GCS and delete instance)
cloud-down:
	@echo "🛑 Stopping GCP development environment..."
	./scripts/cloud/teardown-dev-env.sh

# List GCS backups
cloud-backups:
	@echo "📋 Listing GCS backups..."
	./scripts/cloud/list-backups.sh

# Show GCP cloud environment status
cloud-status:
	@echo "📊 GCP Cloud Environment Status"
	@echo ""
	@echo "Cloud SQL Instances:"
	@gcloud sql instances list --format="table(name,state,settings.activationPolicy,region,databaseVersion)" 2>/dev/null || echo "  No instances found or gcloud not configured"
	@echo ""
	@echo "Cloud Run Services:"
	@gcloud run services list --format="table(name,region,status.url,status.conditions[0].status)" 2>/dev/null || echo "  No services found or gcloud not configured"
	@echo ""
	@echo "GCS Buckets:"
	@gsutil ls 2>/dev/null || echo "  No buckets found or gsutil not configured"
