FROM       ruby:3.2-slim

ENV        LANG=C.UTF-8 \
           REDIS_URL="redis://localhost:6379" \
           CACHE="on"

WORKDIR    /app
RUN        apt-get update && apt-get install -y --no-install-recommends build-essential \
           && rm -rf /var/lib/apt/lists/*
COPY       Gemfile /app/
RUN        bundle install

COPY       linkextractor.rb /app/
EXPOSE     4567

CMD        ["ruby", "linkextractor.rb"]
