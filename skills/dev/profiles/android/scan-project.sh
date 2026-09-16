#!/usr/bin/env bash
set -euo pipefail

root="${1:-.}"
root="$(cd "$root" && pwd)"
base="$root/.agent-workflow/project-baseline"
mkdir -p "$base"

git_head=""
if git -C "$root" rev-parse HEAD >/dev/null 2>&1; then
  git_head="$(git -C "$root" rev-parse HEAD)"
fi

{
  echo "# Android architecture baseline"
  echo
  echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
  echo "## Modules"
  find "$root" -name build.gradle -o -name build.gradle.kts | sed "s|$root/||" | sort
  echo
  echo "## Detected technologies"
  rg -l 'androidx\.compose|setContent\(' "$root" -g '*.kt' 2>/dev/null | head -20 | sed 's/^/- Jetpack Compose: /' || true
  rg -l 'androidx\.room|RoomDatabase' "$root" -g '*.kt' 2>/dev/null | head -20 | sed 's/^/- Room: /' || true
  rg -l 'HiltAndroidApp|@HiltViewModel|dagger\.hilt' "$root" -g '*.kt' 2>/dev/null | head -20 | sed 's/^/- Hilt: /' || true
  rg -l 'Retrofit|OkHttp' "$root" -g '*.kt' 2>/dev/null | head -20 | sed 's/^/- Retrofit or OkHttp: /' || true
} > "$base/architecture.md"

{
  echo "# Conventions to inspect"
  echo
  echo "Review representative feature, ViewModel, repository, UI, and test files before coding."
  echo "Do not treat this generated file as a substitute for reading those examples."
} > "$base/conventions.md"

{
  echo "# Reuse candidates"
  echo
  rg -l 'class .*ViewModel|@Composable|interface .*Repository' "$root" -g '*.kt' 2>/dev/null | head -40 | sed "s|$root/|- |" || true
} > "$base/examples.md"

{
  printf '{\n  "generated_at": "%s",\n  "git_head": "%s",\n  "files": [\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$git_head"
  first=true
  while IFS= read -r file; do
    hash=$(shasum -a 256 "$file" | awk '{print $1}')
    rel="${file#$root/}"
    if [ "$first" = false ]; then printf ',\n'; fi
    first=false
    printf '    {"path":"%s","sha256":"%s"}' "$rel" "$hash"
  done < <(find "$root" -maxdepth 3 \( -name 'settings.gradle' -o -name 'settings.gradle.kts' -o -name 'build.gradle' -o -name 'build.gradle.kts' -o -name 'libs.versions.toml' \) | sort)
  printf '\n  ]\n}\n'
} > "$base/fingerprint.json"

echo "Project baseline written to $base"
