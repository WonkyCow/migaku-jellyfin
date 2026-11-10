#!/usr/bin/env python3
"""Build a Jellyfin-enabled, unpacked copy of Migaku (personal-use POC).

Usage: python3 jellyfin-patch/patch.py [--src DIR] [--out DIR] [--hosts h1,h2] [--force]

Configuration precedence: command-line flag > environment variable > .env file in the repo root.
  JELLYFIN_HOSTS  comma-separated hostnames/IPs (required, no defaults, no ports/scheme)
  MIGAKU_SRC      pristine copy of the extension version folder (default ~/migaku-src/<tested version>_0)
  MIGAKU_OUT      output folder (default build/migaku-jellyfin)

Reads the pristine extension copy (never the installed one) and writes a patched copy to --out.
Edits (every anchor is a pattern; the script aborts if one is missing or ambiguous):
  1. dispatches.background-*.js : add a JELLYFIN entry to the hostname table and the watch-URL
     table so the content script treats Jellyfin as a video site.
  2. *.umd.cjs (page-world adapter bundle): insert jellyfin-adapter.js and one branch in the
     adapter chain. Minified identifiers it needs are discovered by pattern, not hardcoded.
  3. manifest.json: rename (so it is distinguishable), drop update_url.
  4. delete _metadata/: Chrome rejects reserved '_' directories in unpacked extensions.
Tested against Migaku 1.32.0.0. Other versions are refused unless --force is given.
"""
import argparse, json, os, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
TESTED_VERSIONS = {"1.32.0.0"}


def load_dotenv(path: Path) -> dict:
    env = {}
    if path.exists():
        for line in path.read_text(encoding="utf8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def die(msg: str):
    sys.exit(f"ABORT: {msg}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        die(f"anchor for {label!r} found {n} times (expected 1). Migaku version changed?")
    return text.replace(old, new, 1)


def find_one(pattern: str, text: str, label: str, group: int = 1) -> str:
    ms = {m.group(group) for m in re.finditer(pattern, text)}
    if len(ms) != 1:
        die(f"could not uniquely locate {label!r} (matches: {sorted(ms)[:5]}). Migaku version changed?")
    return ms.pop()


def one_file(directory: Path, glob: str) -> Path:
    files = sorted(directory.glob(glob))
    if len(files) != 1:
        die(f"expected exactly one {glob} in {directory}, found {len(files)}")
    return files[0]


def main():
    dotenv = load_dotenv(REPO / ".env")
    cfg = lambda k, d=None: os.environ.get(k) or dotenv.get(k) or d

    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--hosts", default=None)
    ap.add_argument("--force", action="store_true", help="patch an untested Migaku version anyway")
    a = ap.parse_args()

    expand = lambda p: Path(os.path.expanduser(str(p)))
    src = expand(a.src or cfg("MIGAKU_SRC", f"~/migaku-src/{sorted(TESTED_VERSIONS)[-1]}_0"))
    out = a.out or Path(cfg("MIGAKU_OUT", "build/migaku-jellyfin"))
    out = expand(out)
    if not out.is_absolute():
        out = REPO / out

    hosts_raw = a.hosts or cfg("JELLYFIN_HOSTS")
    if not hosts_raw:
        die("no Jellyfin hosts configured. Set JELLYFIN_HOSTS in .env (see .env.example) or pass --hosts.")
    hosts = [h.strip() for h in hosts_raw.split(",") if h.strip()]
    bad = [h for h in hosts if re.search(r"[/:\s]", h)]
    if bad:
        die(f"hosts must be bare hostnames/IPs without scheme, port or slashes: {bad}")
    host_alt = "|".join(re.escape(h) for h in hosts).replace("/", r"\/")

    if not (src / "manifest.json").exists():
        die(f"source extension not found: {src}")
    version = json.loads((src / "manifest.json").read_text(encoding="utf8")).get("version")
    if version not in TESTED_VERSIONS and not a.force:
        die(f"Migaku {version} is untested (tested: {sorted(TESTED_VERSIONS)}). Re-run with --force to try anyway.")

    if out.exists():
        shutil.rmtree(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # reflink copy is near-instant on btrfs; falls back to a normal copy.
    subprocess.run(["cp", "-r", "--reflink=auto", str(src), str(out)], check=True)
    assets = out / "assets"

    # 1. isolated-world gating tables ------------------------------------------------------
    disp = one_file(assets, "dispatches.background-*.js")
    t = disp.read_text(encoding="utf8")
    dom_re = r"(?:^|:\/\/)(?:" + host_alt + r")(?::\d+)?(?:\/|$)"
    # optional path prefix so a Jellyfin served under e.g. /jellyfin/web/ is also recognised
    url_re = r"(?:^|:\/\/)(?:" + host_alt + r")(?::\d+)?(?:\/[^#?]*)?\/web\/(?:index\.html)?#\/video"
    dom_anchor = find_one(r"(\{NETFLIX:\w+\.VIDEO_DOMAIN_REGEX\.NETFLIX,)", t, "hostname table")
    url_anchor = find_one(r"(\{NETFLIX:\w+\.WATCH_URL_REGEX\.NETFLIX,)", t, "watch-URL table")
    t = replace_once(t, dom_anchor, "{JELLYFIN:/" + dom_re + "/i," + dom_anchor[1:], "hostname table")
    t = replace_once(t, url_anchor, "{JELLYFIN:/" + url_re + "/i," + url_anchor[1:], "watch-URL table")
    disp.write_text(t, encoding="utf8")

    # 2. page-world adapter bundle ---------------------------------------------------------
    umd = one_file(assets, "*.umd.cjs")
    t = umd.read_text(encoding="utf8")
    base = find_one(r"class (\w+)\{videoUrl=window\.location\.href;videoPlayer=null", t, "adapter base class")
    langnorm = find_one(r"language:(\w+)\(\w+\),languageDescription:", t, "language normaliser")
    init = 'const EH=()=>{v("video website API injectable init");'
    m = re.search(r'(const (\w+)=\(\)=>\{(\w+)\("video website API injectable init"\);)let (\w+)=(\w+)\(\)\?new (\w+):', t)
    if not m or t.count('video website API injectable init') != 1:
        die("could not locate the adapter chain. Migaku version changed?")
    head, fn_name, _log, var, first_pred, first_cls = m.groups()
    adapter = (HERE / "jellyfin-adapter.js").read_text(encoding="utf8")
    adapter = adapter.replace("__BASE__", base).replace("__LANGNORM__", langnorm).replace("__JF_HOST_RE__", host_alt)
    t = replace_once(t, head, adapter + "\n" + head, "adapter insertion point")
    t = replace_once(
        t,
        f"let {var}={first_pred}()?new {first_cls}:",
        f"let {var}=jfMatch()?new JellyfinAdapter:{first_pred}()?new {first_cls}:",
        "adapter chain",
    )
    umd.write_text(t, encoding="utf8")

    # 3. manifest --------------------------------------------------------------------------
    mf = out / "manifest.json"
    m = json.loads(mf.read_text(encoding="utf8"))
    m["name"] = "Migaku (Jellyfin POC)"
    m.pop("update_url", None)
    mf.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf8")

    # 4. reserved dir ----------------------------------------------------------------------
    shutil.rmtree(out / "_metadata", ignore_errors=True)

    print(f"OK: patched Migaku {version} at {out}")
    print(f"hosts: {hosts}")
    print(f"discovered: base={base} langnorm={langnorm} chain-first={first_pred}/{first_cls}")


if __name__ == "__main__":
    main()
