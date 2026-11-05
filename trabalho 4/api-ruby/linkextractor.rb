#!/usr/bin/env ruby
# encoding: utf-8
#
# Serviço de extração de links (versão Ruby, passo 6 do tutorial).
# Mudanças em relação ao tutorial: URI.open (Ruby 3 removeu o open(url) do
# Kernel), servidor Puma explícito e a variável CACHE=off, que desliga o Redis.

require "sinatra"
require "open-uri"
require "uri"
require "nokogiri"
require "json"

set :protection, :except => :path_traversal
set :server, "puma"
set :bind, "0.0.0.0"
set :port, (ENV["PORT"] || 4567).to_i
set :logging, false

CACHE_ENABLED = (ENV["CACHE"] || "on").downcase != "off"
if CACHE_ENABLED
  require "redis"
  REDIS = Redis.new(url: ENV["REDIS_URL"] || "redis://localhost:6379")
end

get "/" do
  "Usage: http://<hostname>[:<prt>]/api/<url>"
end

get "/api/*" do
  url = [params["splat"].first, request.query_string].reject(&:empty?).join("?")
  jsonlinks = CACHE_ENABLED ? REDIS.get(url) : nil
  cache_status = jsonlinks.nil? ? "MISS" : "HIT"
  if jsonlinks.nil?
    jsonlinks = JSON.pretty_generate(extract_links(url))
    REDIS.set(url, jsonlinks) if CACHE_ENABLED
  end

  status 200
  headers "content-type" => "application/json",
          "x-cache" => (CACHE_ENABLED ? cache_status : "OFF")
  body jsonlinks
end

def extract_links(url)
  links = []
  doc = Nokogiri::HTML(URI.open(url, read_timeout: 30))
  doc.css("a").each do |link|
    text = link.text.strip.split.join(" ")
    begin
      links.push({
        text: text.empty? ? "[IMG]" : text,
        href: URI.join(url, link["href"])
      })
    rescue
    end
  end
  links
end
