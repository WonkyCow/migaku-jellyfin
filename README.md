# Migaku x Jellyfin (personal proof of concept)

Makes the [Migaku](https://migaku.com) browser extension treat the **Jellyfin web player** like a
supported video site (Netflix, YouTube, ...), without a separate "dual subtitles" extension.

With it working you get Migaku's own subtitle overlay, hover lookups, furigana, known-word
underlining, the subtitle sidebar, and card creation with **sentence audio and a screenshot**
captured from the video.

> **Status: working proof of concept, personal use.** Tested on Jellyfin 10.11.5 with
> Migaku extension **1.32.0.0** in Brave. Not affiliated with or endorsed by Migaku or Jellyfin.

## How it works

Migaku injects a page-side "adapter" for each supported site and talks to it over DOM events. This
project adds a Jellyfin adapter in that same slot:

- `jellyfin-patch/jellyfin-adapter.js` is original code. It finds the playing item through
  Jellyfin's own web client API, lists the text subtitle tracks, fetches the VTT (cleaning ASS override
  codes), and gives Migaku the cues, plus seek/play/pause and the video geometry used to crop
  screenshots. It also keeps Jellyfin's OSD and player sized correctly beside Migaku's sidebar.
- `jellyfin-patch/patch.py` builds a patched, **unpacked** copy of your own installed Migaku. It adds
  your Jellyfin hosts to Migaku's site tables, inserts the adapter, renames the extension, and
  removes the `_metadata` folder Chrome rejects for unpacked extensions. It finds Migaku's minified
  identifiers by pattern, refuses untested Migaku versions (override with `--force`), and aborts if
  any anchor is missing or ambiguous, so it fails loudly after a Migaku update.
- `jellyfin-patch/run-dev.sh` launches an isolated browser profile with the patched copy loaded.

Migaku's code is **not** in this repo. You patch your own copy locally. Analysis notes (message
protocol, capture pipeline, where the gates are) are in [`FINDINGS.md`](FINDINGS.md).

## Requirements

- Chromium browser (developed on Brave) and an active Migaku subscription
- Migaku extension **1.32.0.0** installed (other versions need `--force` and may need patch updates)
- Jellyfin web client, with a **text** subtitle track (SRT/VTT/ASS). Image subs (PGS) can't be used.
- Python 3 (and Node.js only if you want to syntax-check the output)

## Setup

1. Copy the installed extension somewhere safe. Never edit the installed one. On Linux with Brave it
   lives under `~/.config/BraveSoftware/Brave-Browser/Default/Extensions/lkhiljgmbeecmljiogckofcalncmfnfo/`:

   ```bash
   mkdir -p ~/migaku-src
   cp -r ~/.config/BraveSoftware/Brave-Browser/Default/Extensions/lkhiljgmbeecmljiogckofcalncmfnfo/1.32.0.0_0 ~/migaku-src/
   ```

2. Configure your hosts. Copy the template and edit it (`.env` is git-ignored):

   ```bash
   cp .env.example .env
   # edit JELLYFIN_HOSTS=your.host.example,192.168.1.10   (bare hostnames/IPs: no scheme, no port)
   ```

3. Build the patched copy (output: `build/migaku-jellyfin/`, git-ignored):

   ```bash
   python3 jellyfin-patch/patch.py
   ```

   Options: `--src`, `--out`, `--hosts`, `--force`. Flags override environment variables, which
   override `.env`.

4. Launch the isolated dev profile (uses `.env` for browser path, profile dir and start URL):

   ```bash
   jellyfin-patch/run-dev.sh            # add --debug for a localhost-only DevTools port (127.0.0.1:9222)
   ```

   Or load `build/migaku-jellyfin` yourself via `brave://extensions` -> Developer mode -> Load unpacked.
   **Use a separate profile**: the manifest pins Migaku's extension ID, so the patched copy has the
   same ID as the Web Store version and the two cannot coexist in one profile.

5. In that profile: sign in to Migaku, open Jellyfin, play something, pick a text subtitle track,
   and press **Alt+R** once per tab to arm tab recording (a Chrome `tabCapture` requirement).
   Then create cards as usual.

## Tips and known quirks

- **First launch:** if Migaku shows no overlay on a tab that was open at browser start, reload the tab
  once. Migaku's language core may not have been ready when the page first loaded.
- **Don't reload the unpacked extension in place** (`chrome.runtime.reload()` or the reload button can
  leave it disabled). Restart with `run-dev.sh` instead.
- **Host not recognised?** Hosts must match exactly what's in the address bar's hostname, without the
  port. A Jellyfin served under a path prefix (e.g. `/jellyfin/web/`) is supported.

## Known limitations

- **Real-time capture:** card audio is recorded live (the cue's duration), like other Migaku sites.
- **Version pinned:** Migaku's minified code changes between releases. After an update, re-copy the new
  version and re-run the patch (with `--force` once, then fix anchors if it aborts). There are no Web
  Store auto-updates for the unpacked copy.
- **Hosts required:** the adapter is injected only on the hosts you list, because the patch can't
  safely inject into arbitrary sites.
- Burned-in or image subtitles can't be read; Jellyfin's own subtitle display is hidden while active.
- Not yet tested: playlist next-episode transitions, mid-playback audio/subtitle switching, and
  HTTPS/WAN hosts.

## Legal / ethics

Personal interoperability with your own Migaku subscription. This does not bypass licensing or any
paywall check, and does not redistribute Migaku's code. I have **not** reviewed Migaku's Terms of
Service; check them before using this beyond personal experimentation or sharing it.
Licensed under the MIT License (see `LICENSE`), which covers this project's own code only, not Migaku.
