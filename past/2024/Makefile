default: develop

install:
	bundle install

develop: install
	bundle exec jekyll serve --livereload

build: install
	bundle exec jekyll build

check_links: build
	bundle exec htmlproofer --ignore_empty_alt --allow-hash-href ./_site

deploy: build
	rsync -av _site/* aq.byu.edu:/usr/share/nginx/html
