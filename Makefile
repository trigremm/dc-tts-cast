.PHONY: build up run down logs clean format lint help

IMAGE_NAME := dc-tts-cast
SPEAKER    := xenia
DURATION   := 20
SAMPLE_RATE := 48000

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

build: ## Build the Docker image
	docker compose build

up: ## Build and run (process all .txt files)
	docker compose up --build

run: ## Run with custom options (e.g. make run SPEAKER=aidar DURATION=30)
	docker compose run --rm tts \
		--speaker $(SPEAKER) \
		--duration $(DURATION) \
		--sample-rate $(SAMPLE_RATE)

down: ## Stop and remove containers
	docker compose down

logs: ## Show container logs
	docker compose logs -f

clean: ## Remove generated output files
	rm -rf output/*/

format: ## Format Python code with ruff
	ruff format app/
	ruff check --fix app/

lint: ## Lint Python code with ruff
	ruff check app/
	ruff format --check app/
