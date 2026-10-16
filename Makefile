SUPABASE := npx -y supabase@2.121.0
SB_EXCLUDE := studio,edge-runtime,imgproxy,vector,logflare,supavisor,mailpit,realtime

.PHONY: help install db-start db-stop db-reset db-test brain web invite chat lint test check

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

install: ## Install brain + web dependencies
	cd apps/brain && uv sync
	cd apps/web && npm ci

db-start: ## Start local Supabase (Docker/Colima)
	$(SUPABASE) start -x $(SB_EXCLUDE)

db-stop: ## Stop local Supabase
	$(SUPABASE) stop

db-reset: ## Re-apply migrations + seed
	$(SUPABASE) db reset

db-test: ## Run pgTAP database tests
	$(SUPABASE) test db

brain: ## Run FastAPI brain on :8000
	cd apps/brain && uv run uvicorn app.main:app --reload --port 8000

web: ## Run Next.js web on :3000
	cd apps/web && npm run dev

invite: ## Invite a number: make invite PHONE=+91... NAME=Kunal [ROLE=admin] [HOUSEHOLD=Home]
	cd apps/brain && uv run python -m app.cli invite "$(PHONE)" "$(NAME)" --role $(or $(ROLE),member) $(if $(HOUSEHOLD),--household "$(HOUSEHOLD)")

chat: ## Chat through the real gate as a number: make chat PHONE=+91...
	cd apps/brain && uv run python -m app.cli chat "$(PHONE)"

lint: ## Lint + typecheck both apps
	cd apps/brain && uv run ruff check . && uv run ruff format --check . && uv run mypy
	cd apps/web && npm run lint && npm run typecheck

test: ## Unit tests for both apps
	cd apps/brain && uv run pytest -q
	cd apps/web && npm test

check: lint test db-test ## Everything CI runs
