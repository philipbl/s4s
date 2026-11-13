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

.PHONY: default install update develop build check_links check_internal_links deploy deploy_dry_run

default: develop

install:
	$(RUN) bundle install

update:
	$(RUN) bundle update

# File-change events don't always reach containers (e.g. colima's default
# settings), so poll for changes when running in Docker.
develop: install
	$(SERVE) bundle exec jekyll serve --livereload --host 0.0.0.0 $(if $(DOCKER),--force_polling)

build: install
	$(RUN) bundle exec jekyll build

check_links: build
	$(RUN) bundle exec htmlproofer --ignore-empty-alt --ignore-urls "$(IGNORE_URLS)" _site

check_internal_links: build
	$(RUN) bundle exec htmlproofer --ignore-empty-alt --disable-external _site

deploy: build
	$(RSYNC) _site/ $(DEPLOY_TARGET)

deploy_dry_run: build
	$(RSYNC) --dry-run _site/ $(DEPLOY_TARGET)
