.DEFAULT_GOAL := help

template := {{ cookiecutter._repository_url }}

.PHONY: help
help:
	@echo "Usage: make [target] [argument=value] ..."
	@echo
	@grep -E '^[a-z.A-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo

.PHONY: update-project
update-project: ## update current project with upstream template changes
	cookiecutter --replay-file=.cookiecutter.json --output-dir=.. --overwrite-if-exists ${template}

.PHONY: run
run: ## run the fastapi app
	fastapi run {{ cookiecutter.python_module_name }}/app/main.py 
