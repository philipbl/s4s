source "https://rubygems.org"

gem "jekyll", "~> 4.4"
gem "jekyll-sitemap", "~> 1.4"
gem "html-proofer", "~> 5.2"

# Jekyll uses logger, which is no longer a default gem in Ruby 4.0.
gem "logger"

# Windows and JRuby do not include zoneinfo files.
platforms :windows, :jruby do
  gem "tzinfo", ">= 1", "< 3"
  gem "tzinfo-data"
end

# Performance booster for watching directories on Windows.
gem "wdm", "~> 0.2", platforms: :windows
