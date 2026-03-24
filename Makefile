.PHONY: build up run run-resume down logs clean format lint help

IMAGE_NAME  := dc-tts-cast-tts
SPEAKER     := xenia
DURATION    := 20
SAMPLE_RATE := 48000
SPEED       := 1.0
COUNT       := 0
INPUT       := /data/input
OUTPUT      := /data/output
INPUT_HOST  := $(PWD)/input
OUTPUT_HOST := $(PWD)/output

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

build: ## Build the Docker image
	docker compose build

up: ## Build and run (process all .txt files)
	docker compose up --build

run: ## Run with options (e.g. make run SPEAKER=baya SPEED=1.5 INPUT_HOST=./input/chapters OUTPUT_HOST=./output/baya)
	docker run --rm --gpus all \
		-v $(abspath $(INPUT_HOST)):$(INPUT) \
		-v $(abspath $(OUTPUT_HOST)):$(OUTPUT) \
		$(IMAGE_NAME) \
		--speaker $(SPEAKER) \
		--duration $(DURATION) \
		--sample-rate $(SAMPLE_RATE) \
		--speed $(SPEED) \
		--input-host $(abspath $(INPUT_HOST)) \
		--output-host $(abspath $(OUTPUT_HOST)) \
		$(if $(filter-out 0,$(COUNT)),--count $(COUNT))

run-resume: ## Resume from saved config (e.g. make run-resume OUTPUT_HOST=./output/o_e_v_baya)
	$(eval CFG := $(OUTPUT_HOST)/tts_config.json)
	$(eval _INPUT_HOST := $(shell python3 -c "import json; print(json.load(open('$(CFG)'))['input-host'])"))
	docker run --rm --gpus all \
		-v $(_INPUT_HOST):$(INPUT) \
		-v $(abspath $(OUTPUT_HOST)):$(OUTPUT) \
		$(IMAGE_NAME) \
		--skip-existing

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
