#!/bin/sh
set -e

# Ensure data directories exist and are writable by the plateblank user
mkdir -p /app/data/originals /app/data/processed
chown -R plateblank:plateblank /app/data

exec gosu plateblank "$@"
