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
  Jellyfin's own web client API, lists the text subtitle tracks, fetches the VTT, and gives Migaku
  the cues, plus seek/play/pause and the video geometry used to crop screenshots.
- `jellyfin-patch/patch.py` builds a patched, **unpacked** copy of your own installed Migaku. It adds
  your Jellyfin hosts to Migaku's site tables, inserts the adapter, renames the extension, and
  removes the `_metadata` folder Chrome rejects for unpacked extensions. It aborts if any anchor in
  Migaku's code is missing or ambiguous, so it fails loudly after a Migaku update.

Migaku's code is **not** in this repo. You patch your own copy locally. Analysis notes (message
protocol, capture pipeline, where the gates are) are in [`FINDINGS.md`](FINDINGS.md).

## Requirements

- Chromium browser (developed on Brave) and an active Migaku subscription
- Migaku extension **1.32.0.0** installed (the patch is tied to that version's minified code)
- Jellyfin web client, with a **text** subtitle track (SRT/VTT/ASS). Image subs (PGS) can't be used.
- Python 3

## Usage

1. Copy the installed extension somewhere read-only-ish and never edit the installed one. On Linux
   with Brave the installed copy lives under
   `~/.config/BraveSoftware/Brave-Browser/Default/Extensions/lkhiljgmbeecmljiogckofcalncmfnfo/`:

   ```bash
   mkdir -p ~/migaku-src
   cp -r ~/.config/BraveSoftware/Brave-Browser/Default/Extensions/lkhiljgmbeecmljiogckofcalncmfnfo/1.32.0.0_0 ~/migaku-src/
   ```

2. Build the patched copy, **passing your own Jellyfin hostnames or IPs** (comma-separated, no ports):

   ```bash
   python3 jellyfin-patch/patch.py --hosts jellyfin.example.com,192.168.1.10
   ```

   Output goes to `build/migaku-jellyfin/` (git-ignored). Options: `--src`, `--out`, `--hosts`.

3. Load it **in a separate browser profile**. The manifest pins Migaku's extension ID, so the patched
   copy gets the same ID as the Web Store version and the two cannot coexist in one profile.
   `brave://extensions` -> Developer mode -> Load unpacked -> `build/migaku-jellyfin`.
   (Alternative: launch with `--user-data-dir=<dir> --load-extension=<path>`.)

4. In that profile: sign in to Migaku, open Jellyfin, play something, pick a text subtitle track,
   and press **Alt+R** once per tab to arm tab recording (a Chrome `tabCapture` requirement).
   Then create cards as usual.

## Known limitations

- **Sidebar layout:** Jellyfin's OSD and layout don't resize cleanly when Migaku's sidebar opens.
- **Real-time capture:** card audio is recorded live (the cue's duration), like other Migaku sites.
- **Version pinned:** minified identifiers change between Migaku releases. After an update you must
  re-copy the new version and adapt the patch. There are no Web Store auto-updates for the unpacked copy.
- **Same-ID caveat:** don't load it into the profile that has the Store copy.
- Burned-in or image subtitles can't be read; Jellyfin's own subtitle display is hidden while active.

## Legal / ethics

Personal interoperability with your own Migaku subscription. This does not bypass licensing or any
paywall check, and does not redistribute Migaku's code. I have **not** reviewed Migaku's Terms of
Service; check them before using this beyond personal experimentation or sharing it.
No license is set yet.
