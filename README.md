# Migaku for Jellyfin: subtitle lookups and sentence mining in the Jellyfin web player

**Use [Migaku](https://migaku.com) in the Jellyfin web player.** Watch your own library with Migaku's
subtitle overlay, hover dictionary lookups, furigana, known-word highlighting and the subtitle sidebar,
and create flashcards with **sentence audio and a screenshot** from the video, with no separate
"dual subtitles" extension needed.

> **Unofficial third-party project. Use at your own risk** (see [Legal / disclaimer](#legal--disclaimer)).
> Not affiliated with or endorsed by Migaku or Jellyfin.
>
> **Warning:** Migaku's Terms of Service restrict using unofficial extensions with its service and
> modifying its application. Using this project very likely violates them, and Migaku may restrict or
> terminate your account without notice and without support. Don't use it on an account you can't
> afford to lose.

## Status and compatibility

**Version 0.9.1, a public pre-release (beta), not yet a full stable release.** The core features work
and are in regular use by the author, but several scenarios are still untested (listed below), so
expect rough edges. It is tied to a specific Migaku version because Migaku's code is minified and
changes between releases.

| Component | Tested with |
|---|---|
| Migaku extension | **1.32.0.0** and **1.32.1.0** (other versions are refused unless you pass `--force`) |
| Jellyfin | 10.11.5 (web client) |
| Browser / OS | Brave (Chromium 153) on Linux |

Not yet tested: other browsers and operating systems, playlist next-episode transitions,
mid-playback audio/subtitle switching, and HTTPS/WAN hosts. Reports are welcome.

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

**Privacy:** the adapter only talks to the Jellyfin server of the page you are on, through Jellyfin's
own web client. This project adds no telemetry and no other network requests. Migaku's own extension
behaves as it does elsewhere, and that includes its own analytics: the recording-related events it
builds appear to include the page's hostname and full URL, which on Jellyfin means **your server
address and the page you're watching**. See [`FINDINGS.md`](FINDINGS.md) for details. If that matters
to you, don't use a host or URL you consider private.

## Requirements

- A Chromium-based browser and an active Migaku subscription
- Migaku extension **1.32.1.0** (or 1.32.0.0) installed from the Web Store, to copy from
- Jellyfin web client, with a **text** subtitle track (SRT/VTT/ASS). Image subs (PGS) can't be used.
- Python 3 (Node.js only if you want to syntax-check the output)

## Setup

1. Copy the installed extension somewhere safe. Never edit the installed one. On Linux with Brave it
   lives under `~/.config/BraveSoftware/Brave-Browser/Default/Extensions/lkhiljgmbeecmljiogckofcalncmfnfo/`:

   ```bash
   mkdir -p ~/migaku-src
   cp -r ~/.config/BraveSoftware/Brave-Browser/Default/Extensions/lkhiljgmbeecmljiogckofcalncmfnfo/1.32.1.0_0 ~/migaku-src/
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

4. Launch the isolated profile (uses `.env` for browser path, profile dir and start URL):

   ```bash
   jellyfin-patch/run-dev.sh            # add --debug for a localhost-only DevTools port (127.0.0.1:9222)
   ```

   Or load `build/migaku-jellyfin` yourself via `brave://extensions` -> Developer mode -> Load unpacked.
   **Use a separate profile**: the manifest pins Migaku's extension ID, so the patched copy has the
   same ID as the Web Store version and the two cannot coexist in one profile.

5. In that profile: sign in to Migaku, open Jellyfin, play something, pick a text subtitle track,
   and press **Alt+R** once per tab to arm tab recording (a Chrome `tabCapture` requirement).
   Then create cards as usual.

## FAQ

**Does Migaku work with Jellyfin?**
Not out of the box: Migaku only treats a fixed list of sites (Netflix, YouTube and similar) as video
players. This project adds the Jellyfin web player to that list.

**Can I make flashcards with audio and screenshots from Jellyfin?**
Yes. Cards created from the Jellyfin player include the sentence, its audio and a screenshot of the
video, captured the same way as on Migaku's supported sites (press Alt+R once per tab to arm recording).

**Do I still need a Jellyfin "dual subtitles" extension?**
No. This reads the subtitle tracks through Jellyfin's own web client and hands them to Migaku, which
draws its own overlay.

**Does it work in the Jellyfin desktop or mobile apps?**
No. It needs the Jellyfin **web** client in a Chromium-based browser. The desktop app plays video
outside the browser, where extensions can't reach it.

**Which languages does it support?**
It was tested with Japanese. The adapter itself is language-agnostic, so other Migaku languages should
work, but they are untested.

**Can I hide the English subtitles while mining?**
Yes, with Migaku's own controls (Shift+W). See [Subtitle display controls](#subtitle-display-controls).

## Subtitle display controls

Most display options are Migaku's own and work on Jellyfin unchanged (hotkeys are Migaku's defaults
and can be rebound in its settings):

| Want to... | How |
|---|---|
| Hide / show the secondary (e.g. English) line | **Shift+W**, or the toolbar's video options ("always hide secondary subtitles") |
| Hide / show the target (e.g. Japanese) line | **W**; **R** hides the whole overlay |
| Resize subtitles | **Alt+=** / **Alt+-** (target), **Alt+Shift+=** / **Alt+Shift+-** (secondary) |
| Background transparency | Toolbar video options: "Subtitle overlay background shade" + "Shade opacity" |
| Move subtitles up/down | Drag them; the position is remembered |
| Put the secondary line **above** the target line | **Alt+Shift+S** (added by this project; remembered per browser profile) |

The swap keeps the target line where it is and places the secondary line directly above it. After
swapping, drag the subtitles if you want them higher or lower.

## Updating

- **Migaku updates:** the Web Store copy in your normal profile updates itself, but the patched copy
  stays on the version you built. To move to a new Migaku version, copy the new version folder from the
  installed extension (step 1), then run `python3 jellyfin-patch/patch.py --force --src <new folder>`.
  If it aborts with an anchor error, Migaku changed something this project depends on; please open an
  issue with the version number.
- **This project:** pull the latest, re-run `patch.py`, then restart the browser with `run-dev.sh`.

## Uninstalling

Remove the extension from the separate profile (or delete the profile directory), and delete
`build/`. Nothing is installed anywhere else and your normal profile and the Store copy are untouched.

## Troubleshooting

- **No overlay on a tab that was open at browser start:** reload the tab once. Migaku's language core
  may not have been ready when the page first loaded.
- **Extension shows as disabled after reloading it:** don't reload the unpacked extension in place
  (`chrome.runtime.reload()` or the reload button can leave it disabled). Restart with `run-dev.sh`.
- **Popup shows "Your file couldn't be accessed" (`ERR_FILE_NOT_FOUND`):** the build folder was deleted or
  rebuilt while the browser was running, so the extension's files vanished from disk. Close the profile's
  window and start it again with `run-dev.sh`. Close the window before re-running `patch.py`, which
  recreates the output folder.
- **Host not recognised:** hosts must match the hostname in the address bar, without the port. A
  Jellyfin served under a path prefix (e.g. `/jellyfin/web/`) is supported.
- **Build aborts with "untested" or "anchor" errors:** your Migaku version differs from the tested one
  (see Updating).
- **No subtitles offered:** the item needs a *text* subtitle track; image-based tracks (PGS) can't be read.
- **Cards have no audio/image:** press **Alt+R** once in the tab to arm recording.

## Known limitations

- **Real-time capture:** card audio is recorded live (the cue's duration), like other Migaku sites.
- **Version pinned:** there are no Web Store auto-updates for the unpacked copy.
- **Extension name:** the patched copy shows up as "Migaku (patched for Jellyfin)", with the patch version
  added to its version string, so you can tell it apart from the Store copy.
- **Hosts required:** the adapter is injected only on the hosts you list, because the patch can't
  safely inject into arbitrary sites.
- Burned-in or image subtitles can't be read; Jellyfin's own subtitle display is hidden while active.

## Contributing

Issues and pull requests are welcome, especially compatibility reports for other Migaku, Jellyfin and
browser versions. Please never include Migaku's code, your `.env`, or any keys or credentials.

## Legal / disclaimer

This is an unofficial, independent project. It does not bypass licensing or any paywall check, and it
does not include or redistribute Migaku's code: you patch your own locally installed copy. It is not
affiliated with or endorsed by Migaku Inc. or the Jellyfin project.

**Migaku's Terms of Service.** As of the version dated September 21, 2023, Migaku's Terms of Service
prohibit using its service through third-party, community-made or unofficial extensions, tools or
clients, and prohibit modifying or reverse engineering its application or creating derivative works
of it. Migaku states it does not support such tools, that they are used entirely at the user's own
risk, that it provides no support, data recovery or account remediation for problems they cause, and
that it may terminate or restrict accounts at any time without notice. Using this project very likely
falls within those restrictions. Read the current Terms yourself; you are solely responsible for
complying with them and with the terms of any other party (Jellyfin, your browser vendor, and so on),
and for any consequences of using this software, including any action taken on your accounts.

The software is provided "as is", with no warranty of any kind, and the author accepts no liability
for how it is used. This is not legal advice.

Licensed under the MIT License (see `LICENSE`), which covers this project's own code only, not
Migaku or any other third-party software.
