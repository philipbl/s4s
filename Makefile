# Jekyll runs inside Docker, so no local Ruby is needed. Gems are cached in a
# named Docker volume. To use a local Ruby instead, run e.g. `make build DOCKER=`.
RUBY_IMAGE := ruby:4.0
DOCKER ?= docker run --rm --init -v "$(CURDIR)":/site -w /site \
	-v s4s-gems-$(subst :,-,$(RUBY_IMAGE)):/usr/local/bundle
RUN = $(if $(DOCKER),$(DOCKER) $(RUBY_IMAGE))
SERVE = $(if $(DOCKER),$(DOCKER) -p 4000:4000 -p 35729:35729 $(RUBY_IMAGE))

.PHONY: default install update develop build check_links check_internal_links deploy

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

# These sites are up but block automated checkers with a Cloudflare challenge.
IGNORE_URLS := /blacksheepcafe\.com/,/communalrestaurant\.com/

check_links: build
	$(RUN) bundle exec htmlproofer --ignore-empty-alt --ignore-urls "$(IGNORE_URLS)" _site

check_internal_links: build
	$(RUN) bundle exec htmlproofer --ignore-empty-alt --disable-external _site

deploy: build
	rsync -av _site/* aq.byu.edu:aq.byu.edu/
