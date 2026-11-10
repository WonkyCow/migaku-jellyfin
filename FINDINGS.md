# Migaku 1.32.0.0 – Jellyfin integration findings

Source: read-only analysis of the copy at `~/migaku-src/1.32.0.0_0/` (nothing executed, installed folder untouched).
All JS is minified onto a few very long lines, so "line references" below are **character offsets** into the file
(`python3 -c "print(open(F).read()[OFF:OFF+600])"`). Code is paraphrased, not reproduced.

Abbreviations: `DB` = `assets/dispatches.background-3ad09d19.js`, `PS` = `assets/player-store-3bbf7ee8.js`,
`MAIN` = `assets/main-9193eaf9.js`, `CH` = `assets/core-host-c759479a.js`, `BG` = `assets/background-script.ts-9b7fc05a.js`,
`UMD` = `assets/jFNkW8z65JGnFf4B1nUyDtUkUFW.umd.cjs` (page-world "video website API" bundle).

## Architecture in one paragraph
Migaku has three cooperating worlds: (1) an **isolated-world content script** (start + idle scripts, injected on `<all_urls>`)
that owns the UI/overlay/state, (2) a **page-world adapter bundle** (`UMD`) that knows how to talk to each supported site's
player, and (3) a **core-host page + service worker** that records tab audio and takes screenshots. (1) and (2) talk over DOM
CustomEvents on `document`; (1) and (3) talk over `chrome.runtime` messages.

## Q1. How is a page recognised as a supported video player?
Four independent gates, all hostname/URL-regex based and all hard-coded:

| Gate | Where | What it does |
|---|---|---|
| Content scripts | `manifest.json` `content_scripts` | start/idle run on `<all_urls>` (Jellyfin already gets them). A third, `capture`, only on `*.youtube.com`. |
| Adapter injection | `DB` @141530 (`zin` = any `VIDEO_DOMAIN_REGEX` matches hostname), injector `bin` @139661, start script `content-script.start.ts-f2310a8a.js` | Only injects `UMD` into the page if the hostname matches a supported site. **Not injected on Jellyfin.** |
| Domain / watch-URL tables | `DB` @126199–127400 (`VIDEO_DOMAIN_REGEX`, `WATCH_URL_REGEX`, `SUPPORTED_VIDEO_DOMAINS`), @129000–130900 (`Z5`, `vy`, `GL`) | Netflix, YouTube, Disney+, Viki, Bettermelon, iQiyi, Bilibili, Crunchyroll, Prime. Regexes are anchored on public domain names. |
| Store gating | `PS` @766452 (`fS`), exposes `isVideoDomain`, `isVideoPage`, `isRecordingEnabled` @771075 | `isVideoDomain` = (URL-matches-supported-site) OR (domain-name predicate). `isVideoPage` = watch-URL predicate. Controls overlay, sidebar, recording. |
| Adapter selection (page world) | tail of `UMD` (`EH`, last ~3 KB) | A chain `siteA()? new A : siteB()? new B : ... : localPlayer()? new LocalPlayer : null`. Each class extends the base `uo`. |

### Adapter interface (what a site adapter must provide)
Base class `uo` @ `UMD` 413821. Child classes **must** implement: `getVideoData`, `getVideoInfo`, `getSubtitle(meta, isTarget)`,
`getMovieIdFromUrl`, `awaitVideoToFinishLoading`, `hideVideoUI`, `displayVideoUI`.
Inherited/overridable: `videoElementSelector` (default `"video"`), `standInSiblingSelector` / `standInContainerSelector`
(where Migaku mounts its subtitle-browser sidebar), `loadPlayer`, `play`, `pause`, `seek`, `seekAwaitLoadAndPlay`,
`getPlaybackTime`, `getPlaybackState`, `getReadyState`, `getIsVideoAdShowing`, `getCurrentAudioTrack`, `getPlaybackRate`/`setPlaybackRate`.

`getVideoPlayerData()` (`UMD` ~422500) must return
`{videoHeight, videoWidth, playerBoundingRect, sidebar, sidebarWidth, pixelRatio, playbackRate}` – this is what the screenshot crop uses.

### Transport (the seam)
`DB` @130787 and @135300–136200 and `UMD` @26900: request = `CustomEvent("MigakuVideoInterfaceSend", {detail:{msgId,msgKey,payload}})`
dispatched on `document`; reply = `CustomEvent("MigakuVideoInterfaceResponse", {detail:{msgId,msgKey,payload|error}})`.
Message keys are `mgk--GetVideoData`, `mgk--GetSubtitles`, `mgk--GetVideoPlayerData`, `mgk--SeekThenPlay`, `mgk--CueChanged`,
`mgk--SendReadyState`, etc. (full list `DB` @130900–132600). Default timeout 20 s, subtitle fetch 180 s.
The adapter registers handlers for ~45 keys at the very end of `UMD` (the `EH` function).

## Q2. How are screenshot and audio captured?
Non-YouTube sites use a **real-time tab recorder**, not ffmpeg cutting and not per-element capture:

1. Card creation (`PS` ~149900–152800, funcs `LJ` / `jD`) checks the tab is armed, builds `playerData` from the adapter
   (`GET_VIDEO_PLAYER_DATA`), then calls core-host `RECORD_SEGMENT {startTime, endTime, screenshot:true, playerData}`.
   Audio padding (start/end) comes from video options.
2. Arming = `START_TAB_RECORDING` → `BG` @18677 → `chrome.tabCapture.getMediaStreamId` (`language.config-5699f270.js` @59834)
   → core-host `ENABLE_RECORDING` → `getUserMedia({chromeMediaSource:"tab"})` → `MediaRecorder` (`CH` @119520–120120, class `va`).
   Needs the user to trigger the extension command once per tab (**Alt+R toggle-recording**; Migaku shows a toast telling you so,
   `PS` @~149000). This is Chrome's tabCapture/activeTab rule, not Migaku-specific.
3. `recordSegment` (`CH` ~120200): sends `PLAY_VIDEO_FROM_TIME` to the tab (`MAIN` @1032323 → adapter `SEEK_THEN_PLAY`),
   records **in real time for (end-start)/playbackRate**, takes a screenshot at the midpoint.
4. Screenshot = `chrome.tabs.captureVisibleTab` via background relay (`BG` @18418, `CH` @117747), cropped to the video rectangle
   using `playerBoundingRect`, `videoWidth/Height`, `pixelRatio` (`CH` @118165–119341), returned as a `blob:` URL.
5. Returns `{imageUrl, audioUrl}` → wrapped as `AudioAsset` / `ImageAsset` → card payload
   `{sentence, sentenceAudio:[…], images:[…]}` (`PS` ~151700) → card creator page.
6. ffmpeg (`ffmpeg/`, `CH`, sandbox page) is used inside the extension for media post-processing/conversion; I have **not** traced
   exactly where. The audio blob is made seekable with a metadata-fix helper (`CH` ~117400).

YouTube is special: separate SABR audio download (`mgk-capture-worker.js`, `mgk-hijack.js`, `mgk-stitch.js`, capture content script).
Not relevant for Jellyfin.

So the capture path only needs, from a site: the `<video>` rect/size, seek+play, playback rate, and a tab that has been armed.
It is **site-agnostic** once the adapter exists. Audio will include whatever the tab plays (so card creation takes as long as the cue).

## Q3. Seam for Jellyfin
**(b) outside script only – not sufficient on its own.** The page-world half *could* be implemented by an external MAIN-world script
that answers the CustomEvents (the DOM is shared), but Migaku's isolated half never enters video mode because the hostname gate
(`zin`, `fS`, domain tables) rejects a self-hosted Jellyfin host, and the adapter bundle is never injected. Those checks are inside the
extension; there is no hook or setting to extend them. (Spoofing a supported hostname via DNS/proxy would be a fragile hack and would
load the wrong adapter; not recommended.)

**(a) Add Jellyfin as a supported site – feasible, small patch surface.** Needed edits to an *unpacked copy*:
1. `DB`: add a Jellyfin entry to the domain/watch-URL tables so `zin`, `Z5`/`VIDEO_DOMAIN_REGEX` and `WATCH_URL_REGEX` accept it.
   Jellyfin has arbitrary hostnames, so the matcher should be user-configurable (e.g. path `/web/` + `#/video` hash, or a stored host list),
   not a public-domain regex.
2. `PS` `fS` and its URL predicates: make `isVideoDomain` / `isVideoPage` true for Jellyfin.
3. `UMD` `EH` chain: add one branch `jellyfinPage() ? new JellyfinAdapter : …` and define `JellyfinAdapter extends uo`.
   To avoid copying Migaku code, `JellyfinAdapter` can live in **my own separate file** loaded by a one-line hook, extending the
   exposed base class.
4. `manifest.json`: nothing needed for matching (`<all_urls>` already). `web_accessible_resources` already exposes `UMD` to all URLs via `"*"`.

`JellyfinAdapter` responsibilities (this is what replaces the dual-subs extension):
- `videoElementSelector`: Jellyfin's `video.htmlvideoplayer` (to verify in DevTools).
- `getVideoData` / `getVideoInfo`: item id + title + list of **text** subtitle tracks from `ApiClient` / `/Items/{id}` MediaStreams.
- `getSubtitle`: fetch `/Videos/{id}/{mediaSourceId}/Subtitles/{index}/0/Stream.vtt` (or `.srt`) and return cues in Migaku's format.
- seek/play/pause/rate: drive the `<video>` element directly (same-origin).
- `getVideoPlayerData`: from the element + `getBoundingClientRect` + `devicePixelRatio`.
- stand-in selectors: pick a Jellyfin container (`.videoPlayerContainer` style) so the sidebar mounts.
- hide/show UI: toggle Jellyfin OSD CSS.

## Q4. Local Player and URLs
`UMD` class `us` (Local Player adapter, selected last in the chain). `handleVideoMode` (`UMD`, near `loadVideo` @~ after 413821) sets
`videoElement.src = e.videoURL`, i.e. it consumes a **URL string on a descriptor object** (`{name, type, videoURL, audioTracks, …}`),
not a `File` directly; `videoURL` is normally a `blob:` URL created by the player page. So a remote/Jellyfin stream URL is *plausible*
(not tested) but there is no UI for it, subtitle loading expects local srt/vtt/ass, and it would live on the extension's own page, not
in the Jellyfin tab. Interesting as a fallback, worse than a real adapter for "one tool".

## Constraints / risks discovered
- **Extension ID**: `manifest.json` has a `key`, so an unpacked copy gets the **same ID** as the Web Store version.
  Two installs with the same ID cannot coexist in one profile; removing the Store copy deletes its storage (settings, maybe login).
  → Test the patched copy in a **separate Brave profile** first.
- Brave overwrites/restores the Store copy on update and verifies it (`_metadata/verified_contents.json`); never edit in place.
- Patch must be re-applied after every Migaku update. Plan: a patch script that finds small anchor strings and inserts
  hooks (no Migaku code stored in my repo beyond tiny anchors), plus my own `jellyfin-adapter.js`.
- Subtitle tracks must be text (srt/vtt/ass); image/burned-in subs cannot be read.
- Card creation is real-time (duration of cue) and needs the Alt+R arming once per tab.
- Migaku ToS not yet checked – needed before any public sharing.
