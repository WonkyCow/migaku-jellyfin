#!/usr/bin/env bash
# Launch an isolated Brave/Chromium dev profile with the patched Migaku loaded.
# Configuration comes from the repo's .env (see .env.example). Never touches your main profile.
#
#   jellyfin-patch/run-dev.sh            normal launch
#   jellyfin-patch/run-dev.sh --debug    also open a localhost-only DevTools port (127.0.0.1:9222)
#
# Note: reloading an unpacked extension in place (chrome://extensions "reload" or
# chrome.runtime.reload()) can leave it disabled; restart with this script instead.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ -f "$REPO/.env" ] && set -a && . "$REPO/.env" && set +a

expand() { eval echo "${1/#\~/$HOME}"; }
BRAVE_BIN="$(expand "${BRAVE_BIN:-brave-browser}")"
PROFILE="$(expand "${DEV_PROFILE_DIR:-$HOME/.config/brave-migaku-dev}")"
OUT="$(expand "${MIGAKU_OUT:-build/migaku-jellyfin}")"
case "$OUT" in /*) ;; *) OUT="$REPO/$OUT" ;; esac
URL="${JELLYFIN_URL:-}"

[ -f "$OUT/manifest.json" ] || { echo "No patched extension at $OUT. Run: python3 jellyfin-patch/patch.py" >&2; exit 1; }

# Safety: refuse to use a profile directory that looks like the main browser profile.
case "$PROFILE" in
  *BraveSoftware*|*google-chrome*|*chromium*) echo "Refusing to use a main-profile path: $PROFILE" >&2; exit 1 ;;
esac

ARGS=(--user-data-dir="$PROFILE" --no-first-run --no-default-browser-check
      --disable-features=DisableLoadExtensionCommandLineSwitch --load-extension="$OUT")
[ "${1:-}" = "--debug" ] && ARGS+=(--remote-debugging-port=9222 --remote-debugging-address=127.0.0.1)
[ -n "$URL" ] && ARGS+=("$URL")

mkdir -p "$PROFILE"
exec "$BRAVE_BIN" "${ARGS[@]}"
