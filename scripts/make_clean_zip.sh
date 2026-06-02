#!/usr/bin/env bash
# Create a clean ZIP archive excluding secrets, dependencies, build artifacts, caches, and OS junk.
# Usage: ./scripts/make_clean_zip.sh [output_name]
set -euo pipefail

OUTPUT="${1:-kesha-finance-clean.zip}"

# Always run from the project root, no matter where the script was called from.
cd "$(dirname "$0")/.."

# Do not overwrite the archive while zipping the project into itself.
rm -f "$OUTPUT"

# zip -x patterns are matched against archive paths like:
#   ./web/node_modules/...
#   ./bot/venv/...
# So we need both top-level and recursive patterns.
EXCLUDE=(
  # Secrets and local env files. Keep examples.
  "./.env"
  "./.env.*"
  "./*/.env"
  "./*/.env.*"
  "./**/.env"
  "./**/.env.*"
  "!./.env.example"
  "!./*/.env.example"

  # Dependencies / virtual environments.
  "./node_modules/*"
  "./*/node_modules/*"
  "./**/node_modules/*"
  "./venv/*"
  "./*/venv/*"
  "./**/venv/*"
  "./.venv/*"
  "./*/.venv/*"
  "./**/.venv/*"

  # Build artifacts.
  "./.next/*"
  "./*/.next/*"
  "./**/.next/*"
  "./dist/*"
  "./*/dist/*"
  "./**/dist/*"
  "./build/*"
  "./*/build/*"
  "./**/build/*"
  "./.vercel/*"
  "./*/.vercel/*"
  "./**/.vercel/*"

  # Python / JS caches.
  "./__pycache__/*"
  "./*/__pycache__/*"
  "./**/__pycache__/*"
  "./*.pyc"
  "./*/*.pyc"
  "./**/*.pyc"
  "./*.tsbuildinfo"
  "./*/*.tsbuildinfo"
  "./**/*.tsbuildinfo"

  # Git and local metadata.
  "./.git/*"
  "./*/.git/*"
  "./.gitignore"
  "./__MACOSX/*"
  "./*/__MACOSX/*"
  "./.DS_Store"
  "./*/.DS_Store"
  "./**/.DS_Store"
  "./Thumbs.db"
  "./*/Thumbs.db"
  "./**/Thumbs.db"

  # Local deploy config with app/account-specific data.
  "./fly.toml"
)

ZIP_ARGS=()
for pattern in "${EXCLUDE[@]}"; do
  ZIP_ARGS+=(-x "$pattern")
done

zip -r "$OUTPUT" . "${ZIP_ARGS[@]}"

echo "✅ Clean archive: $OUTPUT"
ls -lh "$OUTPUT"

echo "\n🔎 Archive safety check:"
if unzip -l "$OUTPUT" | grep -E '(^|/)(node_modules|venv|\.venv|\.next|\.vercel|__pycache__)(/|$)|(^|/)\.env(\.|$)|\.env\.local|\.pyc$|\.DS_Store|fly\.toml' >/tmp/kesha_zip_leaks.txt; then
  echo "⚠️ Found files that should probably be excluded:"
  cat /tmp/kesha_zip_leaks.txt
  exit 1
else
  echo "✅ No obvious secrets/dependencies/build artifacts found."
fi
