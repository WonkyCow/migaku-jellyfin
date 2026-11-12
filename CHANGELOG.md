# Changelog

All notable changes to this project. Versions track this project, not Migaku.

## [0.9.1]

### Added
- Support for Migaku extension **1.32.1.0** (tested alongside 1.32.0.0).
- The patched extension is now named "Migaku (patched for Jellyfin)" and its version string includes the
  patch version (for example `1.32.1 + Jellyfin patch 0.9.1`).

### Fixed
- **Subtitle order swap (Alt+Shift+S):** it previously had no visible effect, because Migaku renders its UI
  inside a shadow DOM that page-level CSS cannot reach. The rule is now injected into the shadow root, and
  the secondary line is placed directly above the target line instead of on top of it.
- `run-dev.sh` now lets environment variables override `.env`, matching `patch.py`.

## [0.9.0]

First public pre-release (beta): functional and in regular use, but not yet a full stable release
because some scenarios are still untested (see the README). Targets Migaku extension 1.32.0.0 and
Jellyfin web 10.11.x.

### Added
- Jellyfin adapter: Migaku's overlay, lookups, sidebar and card creation (sentence audio and
  screenshot) on the Jellyfin web player.
- `patch.py`: builds a patched, unpacked copy of your own Migaku install. Configurable hosts via
  `.env`, version gate (`--force` to override), identifiers located by pattern, loud failure when an
  anchor is missing.
- `run-dev.sh`: launches an isolated browser profile with the patched extension.
- `Alt+Shift+S` hotkey to show the secondary subtitle line above the target line.
- Documentation of Migaku's built-in display controls (hide/show, size, shade opacity, position).

### Fixed
- Sidebar layout: player stays full height and Jellyfin's OSD sizes to the space beside the sidebar.
- ASS subtitle tracks: override codes (`{\i1}`, `\N`) are stripped from cue text.
- Jellyfin served under a path prefix (e.g. `/jellyfin/web/`) is recognised.
