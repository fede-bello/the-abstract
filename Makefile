# the-abstract — common dev tasks. Run `make` (or `make help`) to list targets.

.DEFAULT_GOAL := help
.PHONY: help install dev ingest verify

help: ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

install: ## Install backend (uv) and frontend (npm) dependencies
	uv sync
	npm --prefix frontend install

dev: ## Run the Vite dev server (the SPA reads Supabase directly; no backend server to run)
	npm --prefix frontend run dev

ingest: ## Run the ingestion pipeline once to populate the database
	uv run arxiv-digest ingest

verify: ## Run all checks: backend ruff+mypy+tests and frontend typecheck+lint+test
	uv run ruff check backend && uv run mypy backend
	uv run pytest backend -m "not integration"
	npm --prefix frontend run typecheck
	npm --prefix frontend run lint
	npm --prefix frontend run test
