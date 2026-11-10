#!/usr/bin/env python3
"""Build a Jellyfin-enabled, unpacked copy of Migaku (personal-use POC).

Usage: python3 patch.py [--src DIR] [--out DIR] [--hosts h1,h2,...]

Reads the pristine extension copy (never the installed one), writes a patched copy to --out.
Edits (all anchored; the script aborts if an anchor is missing or ambiguous):
  1. dispatches.background-*.js : add JELLYFIN entry to the hostname table (Z5) and the
     watch-URL table (vy) so the content script treats Jellyfin as a video site.
  2. jFNk...umd.cjs             : insert jellyfin-adapter.js and a branch in the adapter chain.
  3. manifest.json              : rename (so it is distinguishable), drop update_url.
  4. delete _metadata/          : Chrome rejects reserved '_' dirs in unpacked extensions.
Targets Migaku 1.32.0.0 (minified identifiers are version-specific).
"""
import argparse, json, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_SRC = Path.home() / "migaku-src" / "1.32.0.0_0"
DEFAULT_OUT = HERE.parent / "build" / "migaku-jellyfin"
DEFAULT_HOSTS = "192.168.0.60,arcanum.alysium.cc"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        sys.exit(f"ABORT: anchor for {label!r} found {n} times (expected 1). Migaku version changed?")
    return text.replace(old, new, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--hosts", default=DEFAULT_HOSTS)
    a = ap.parse_args()

    hosts = [h.strip() for h in a.hosts.split(",") if h.strip()]
    host_alt = "|".join(re.escape(h) for h in hosts)  # python escaping is valid JS regex source
    host_alt_js = host_alt.replace("/", r"\/")

    if not (a.src / "manifest.json").exists():
        sys.exit(f"source not found: {a.src}")
    if a.out.exists():
        shutil.rmtree(a.out)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    # reflink copy is near-instant on btrfs; falls back to a normal copy.
    subprocess.run(["cp", "-r", "--reflink=auto", str(a.src), str(a.out)], check=True)

    assets = a.out / "assets"

    # 1. isolated-world gating tables --------------------------------------------------
    disp = next(assets.glob("dispatches.background-*.js"))
    t = disp.read_text(encoding="utf8")
    dom_re = r"(?:^|:\/\/)(?:" + host_alt_js + r")(?::\d+)?(?:\/|$)"
    url_re = r"(?:^|:\/\/)(?:" + host_alt_js + r")(?::\d+)?\/web\/(?:index\.html)?#\/video"
    t = replace_once(t, "Z5={NETFLIX:", "Z5={JELLYFIN:/" + dom_re + "/i,NETFLIX:", "Z5 hostname table")
    t = replace_once(t, "vy={NETFLIX:", "vy={JELLYFIN:/" + url_re + "/i,NETFLIX:", "vy watch-url table")
    disp.write_text(t, encoding="utf8")

    # 2. page-world adapter bundle ----------------------------------------------------
    umd = assets / "jFNkW8z65JGnFf4B1nUyDtUkUFW.umd.cjs"
    t = umd.read_text(encoding="utf8")
    adapter = (HERE / "jellyfin-adapter.js").read_text(encoding="utf8").replace("__JF_HOST_RE__", host_alt_js)
    t = replace_once(
        t,
        'const EH=()=>{v("video website API injectable init");',
        adapter + '\nconst EH=()=>{v("video website API injectable init");',
        "adapter insertion point",
    )
    t = replace_once(t, "let t=K0()?new p8:", "let t=jfMatch()?new JellyfinAdapter:K0()?new p8:", "adapter chain")
    umd.write_text(t, encoding="utf8")

    # 3. manifest ---------------------------------------------------------------------
    mf = a.out / "manifest.json"
    m = json.loads(mf.read_text(encoding="utf8"))
    m["name"] = "Migaku (Jellyfin POC)"
    m.pop("update_url", None)
    mf.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf8")

    # 4. reserved dir -----------------------------------------------------------------
    shutil.rmtree(a.out / "_metadata", ignore_errors=True)

    print(f"OK: patched extension at {a.out}\nhosts: {hosts}")


if __name__ == "__main__":
    main()
