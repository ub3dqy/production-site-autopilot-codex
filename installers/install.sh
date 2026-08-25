#!/usr/bin/env sh
set -eu

PROJECT_PATH="${1:-.}"
ACTION="${2:-install}"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
SOURCE="$ROOT/plugin/skills/production-site-autopilot"
PROJECT=$(CDPATH= cd -- "$PROJECT_PATH" && pwd -P)
TARGET="$PROJECT/.codex/skills/production-site-autopilot"
MARKER="$TARGET/.production-site-autopilot-install.json"

case "$TARGET" in "$PROJECT"/*) ;; *) echo "Target escapes project" >&2; exit 2 ;; esac
if [ -L "$PROJECT/.codex" ] || [ -L "$PROJECT/.codex/skills" ]; then
  echo "Refusing symlinked installation path" >&2
  exit 2
fi
if [ "$ACTION" = "doctor" ]; then
  printf '{"project":"%s","source_exists":%s,"installed":%s,"target":"%s"}\n' \
    "$PROJECT" "$(test -d "$SOURCE" && echo true || echo false)" "$(test -f "$MARKER" && echo true || echo false)" "$TARGET"
  exit 0
fi
if [ "$ACTION" = "uninstall" ]; then
  test -f "$MARKER" || { echo "Managed installation marker not found; refusing removal" >&2; exit 2; }
  rm -rf -- "$TARGET"
  echo "Removed: $TARGET"
  exit 0
fi
mkdir -p -- "$(dirname -- "$TARGET")"
if [ -e "$TARGET" ]; then
  STAMP=$(date -u +%Y%m%dT%H%M%SZ)
  mv -- "$TARGET" "$TARGET.backup-$STAMP"
fi
cp -R -- "$SOURCE" "$TARGET"
VERSION=$(tr -d '\r\n' < "$ROOT/VERSION")
cat > "$MARKER" <<EOF
{"schema_version":"1.0","version":"$VERSION","source":"$SOURCE"}
EOF
echo "Installed: $TARGET"
