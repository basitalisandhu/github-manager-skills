# syntax=docker/dockerfile:1
#
# The github-manager skill scripts as one command-line image. Build and run with:
#   docker build -t github-manager-skills .
#   docker run --rm -v "$PWD:/work" github-manager-skills pr-queue /work/export
#
# Standard library only: no pip install, no network use at run time. The base image is pinned by digest
# (python:3.12-slim, multi-arch index).
ARG PYTHON_IMAGE=python:3.12-slim@sha256:dddfd7e07f9d15aeeca61529320492139d21cac7f0070c00609243e51e4e0016

# Assemble the tree in a throwaway stage: only the dispatcher and the skill scripts, byte-compiled, and smoke-tested.
FROM ${PYTHON_IMAGE} AS build
WORKDIR /app
COPY LICENSE README.md pyproject.toml ./
COPY scripts/cli.py scripts/cli.py
COPY plugins/github-manager/skills/ /tmp/skills/
RUN set -e; for d in /tmp/skills/*/scripts; do \
      skill=$(basename "$(dirname "$d")"); \
      mkdir -p "plugins/github-manager/skills/$skill/scripts"; \
      cp "$d"/*.py "plugins/github-manager/skills/$skill/scripts/"; \
    done \
 && chmod 0755 scripts/cli.py plugins/github-manager/skills/*/scripts/[a-z]*.py \
 && python -m compileall -q scripts plugins \
 && python scripts/cli.py --help > /dev/null

FROM ${PYTHON_IMAGE}
ARG VERSION=0.0.0-dev
LABEL org.opencontainers.image.title="github-manager-skills" \
      org.opencontainers.image.description="Engineering manager reports from exported GitHub data (PR queue digest, iteration report, incident postmortem timeline) behind one command" \
      org.opencontainers.image.source="https://github.com/basitalisandhu/github-manager-skills" \
      org.opencontainers.image.url="https://github.com/basitalisandhu/github-manager-skills" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="${VERSION}"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY --from=build /app/ /app/
RUN ln -s /app/scripts/cli.py /usr/local/bin/github-manager \
 && useradd --uid 1000 --user-group --no-create-home --shell /usr/sbin/nologin app
# Mount the export folder at /work.
WORKDIR /work
USER 1000:1000
ENTRYPOINT ["github-manager"]
CMD ["--help"]
