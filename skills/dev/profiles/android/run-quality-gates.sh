#!/usr/bin/env bash
set -euo pipefail

root="${1:-.}"
root="$(cd "$root" && pwd)"
wrapper="$root/gradlew"

if [ ! -x "$wrapper" ]; then
  echo "QUALITY_GATE_UNAVAILABLE: no executable Gradle wrapper at $wrapper" >&2
  exit 2
fi

cd "$root"
./gradlew check
