# Run `make help` to see every command.

# Jekyll runs inside Docker, so no local Ruby is needed. Gems are cached in a
# named Docker volume. To use a local Ruby instead, run e.g. `make build DOCKER=`.
RUBY_VERSION := $(shell cat .ruby-version)
DOCKER ?= docker run --rm --init -v "$(CURDIR)":/site -w /site \
	-v s4s-gems-ruby-$(RUBY_VERSION):/usr/local/bundle
RUN = $(if $(DOCKER),$(DOCKER) ruby:$(RUBY_VERSION))
SERVE = $(if $(DOCKER),$(DOCKER) -p 4000:4000 -p 35729:35729 ruby:$(RUBY_VERSION))

# Where `make deploy` copies the site. --delete removes files on the server
# that are no longer in _site; `make deploy_dry_run` shows what would change.
DEPLOY_TARGET ?= aq.byu.edu:aq.byu.edu/
RSYNC := rsync -avz --checksum --delete

# These sites are up but block automated checkers with a Cloudflare challenge.
IGNORE_URLS := /blacksheepcafe\.com/,/communalrestaurant\.com/

# The Python helpers run on the host's python3. schedule_to_csv.py needs
# PyYAML, so it runs from a local virtual environment that `make schedule_csv`
# creates the first time. Pass CSV=path to write the file somewhere else.
VENV := .venv
CSV ?= schedule.csv

.PHONY: default help install update develop build check_links check_internal_links \
	deploy deploy_dry_run archive schedule_csv

default: develop

help: ## List these commands
	@echo "Usage: make <command>"
	@echo
	@awk 'BEGIN {FS = ":.*## "} /^[a-z_]+:.*## / {printf "  make %-22s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install the Ruby gems (runs automatically when needed)
	$(RUN) bundle install

update: ## Update the Ruby gems to the newest allowed versions
	$(RUN) bundle update

# File-change events don't always reach containers (e.g. colima's default
# settings), so poll for changes when running in Docker.
develop: install ## Preview the site at http://localhost:4000 (also plain `make`)
	$(SERVE) bundle exec jekyll serve --livereload --host 0.0.0.0 $(if $(DOCKER),--force_polling)

build: install ## Build the site into _site/
	$(RUN) bundle exec jekyll build

check_links: build ## Check all links, including ones to other sites
	$(RUN) bundle exec htmlproofer --ignore-empty-alt --ignore-urls "$(IGNORE_URLS)" _site

check_internal_links: build ## Check links within the site only (faster)
	$(RUN) bundle exec htmlproofer --ignore-empty-alt --disable-external _site

deploy: build ## Build the site and copy it to aq.byu.edu
	$(RSYNC) _site/ $(DEPLOY_TARGET)

deploy_dry_run: build ## Show what deploy would change, without changing anything
	$(RSYNC) --dry-run _site/ $(DEPLOY_TARGET)

# Run this after a conference, before changing anything for next year. The
# year comes from _data/dates.yaml.
archive: build ## Freeze this year's site into past/<year>/ (options: YEAR=2026 FORCE=1)
	python3 archive_year.py $(if $(YEAR),--year $(YEAR)) $(if $(FORCE),--force)

schedule_csv: $(VENV)/.installed ## Write the program in _data/schedule.yaml to schedule.csv (option: CSV=path)
	$(VENV)/bin/python schedule_to_csv.py _data/schedule.yaml "$(CSV)"
	@echo "Wrote $(CSV)"

$(VENV)/.installed:
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install --quiet --disable-pip-version-check pyyaml
	touch $@
