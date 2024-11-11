.DEFAULT_GOAL := help

template := git@github.com:claco/claco.python.git

.PHONY: help
help:
	@echo "Usage: make [target] [argument=value] ..."
	@echo
	@grep -E '^[a-z.A-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo

.PHONY: default-project
default-project: ## create a new project using default settings
	cookiecutter --no-input --output-dir=${output-dir} .

.PHONY: new-project
new-project: ## create a new project
	cookiecutter --output-dir=${output-dir} .
