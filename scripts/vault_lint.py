#!/usr/bin/env python3
"""Pemeriksa kesehatan vault AsistenObsidian: link mati, konvensi note, sampah.

Pakai:
  python vault_lint.py                      # ringkasan saja
  python vault_lint.py --report             # tulis ulang 04-Sistem/Vault Link Report.md
  python vault_lint.py --index              # generate 04-Sistem/INDEX - Vault.md
  python vault_lint.py --report --index     # keduanya
  python vault_lint.py --list konvensi      # cetak daftar lengkap satu kategori

Stdlib saja. Vault default dari OBSIDIAN_VAULT_PATH, fallback D:/obsidian/AsistenObsidian.
"""

import argparse
import fnmatch
import os
import re
import sys
import unicodedata
from datetime import datetime
from collections import defaultdict

DEFAULT_VAULT = "D:/obsidian/AsistenObsidian"
GENERATED = {"Vault Link Report.md", "INDEX - Vault.md"}
SKIP_DIRS = {".obsidian", ".git", ".trash", "cache", "apikeys"}
FENCE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE = re.compile(r"`[^`\n]*`")
WIKILINK = re.compile(r"\[\[([^\]\n]+)\]\]")
JUNK = re.compile(r"(_tmp.*|_d_.*\.txt|.*\.bak|.*\.orig|.*\.tmp|.*\.old)$")


ALLOW = set()


def load_allow(vault):
    """Baca 04-Sistem/vault_lint_allow.txt: pola note yang CJK-nya sengaja."""
    path = os.path.join(vault, "04-Sistem", "vault_lint_allow.txt")
    out = set()
    if os.path.exists(path):
        for ln in open(path, encoding="utf-8"):
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                out.add(ln)
    return out


def allowed(rel):
    return any(fnmatch.fnmatch(rel, pat) for pat in ALLOW)


def vault_path(cli):
    if cli:
        return cli
    env = os.environ.get("OBSIDIAN_VAULT_PATH")
    if env:
        return env
    return DEFAULT_VAULT


def strip_boxes(text):
    """Buang blok kode fenced dan inline code supaya contoh kode tidak dihitung link."""
    out, in_fence = [], False
    for ln in text.split("\n"):
        if FENCE.match(ln):
            in_fence = not in_fence
            out.append("")
            continue
        out.append("" if in_fence else INLINE_CODE.sub("", ln))
    return "\n".join(out)


def scan(vault):
    notes, assets, junk = [], set(), []
    for root, dirs, fs in os.walk(vault):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in fs:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, vault).replace("\\", "/")
            if f.endswith(".md"):
                notes.append((rel, full))
            else:
                assets.add(f.lower())
                if JUNK.search(f):
                    junk.append(rel)
    return notes, assets, junk


CJK_RANGES = (
    (0x2E80, 0xA4CF),   # radikal, kana, hangul jamo, CJK unified
    (0xAC00, 0xD7AF),   # hangul suku kata
    (0xF900, 0xFAFF),   # CJK compatibility ideographs
    (0xFE30, 0xFE4F),   # CJK compatibility forms
    (0xFF00, 0xFF60),   # fullwidth forms
    (0xFFE0, 0xFFE6),
)


def cjk_chars(text):
    """Aksara CJK/fullwidth saja. Emoji, panah, dan box-drawing tidak dihitung."""
    bad = []
    for ch in text:
        cp = ord(ch)
        if any(a <= cp <= b for a, b in CJK_RANGES):
            bad.append(ch)
    return bad


WAJIB_PREFIX = ("nama file", "aksara")


def check_note(rel, full):
    raw = open(full, encoding="utf-8", errors="replace").read()
    text = strip_boxes(raw)
    lines = text.split("\n")
    issues = []
    head = lines[:14]
    if not any(l.startswith("> ") for l in head):
        issues.append("anjuran: tanpa blockquote ringkasan")
    if not re.search(r"(?m)^## Terkait\s*$", text):
        issues.append("anjuran: tanpa ## Terkait")
    else:
        terkait = text.split("## Terkait", 1)[1]
        terkait = terkait.split("\n## ", 1)[0]
        n = len([l for l in terkait.split("\n") if l.strip().startswith(("- [[", "* [["))])
        if n < 3:
            issues.append(f"anjuran: ## Terkait hanya {n} link")
    if not re.search(r"(?m)^Tags:", text):
        issues.append("anjuran: tanpa baris Tags:")
    name = os.path.basename(rel)
    if "—" in name or any(ord(c) > 127 for c in name):
        issues.append("nama file memuat karakter non-ASCII")
    bad = [] if allowed(rel) else cjk_chars(raw)
    if bad:
        issues.append("aksara lebar/CJK: " + "".join(sorted(set(bad))[:5]))
    size = os.path.getsize(full)
    if size > 200 * 1024:
        issues.append(f"info: ukuran {size // 1024}KB (gudang mentah, pecah ke data/)")
    elif size > 60 * 1024:
        issues.append(f"info: ukuran {size // 1024}KB (catatan besar)")
    return issues, raw



def broken_links(notes):
    stems = {os.path.basename(rel)[:-3].lower(): rel for rel, _ in notes}
    broken = defaultdict(list)
    for rel, full in notes:
        if os.path.basename(rel) in GENERATED:
            continue
        text = strip_boxes(open(full, encoding="utf-8", errors="replace").read())
        for target in WIKILINK.findall(text):
            t = target.split("|")[0].split("#")[0].strip()
            if not t:
                continue
            stem = t.split("/")[-1]
            if stem.lower() in stems:
                continue
            if stem.lower() in ASSETS_SEEN:
                continue
            broken[stem].append(rel)
    return broken


def inbound_count(notes):
    stems = {}
    for rel, full in notes:
        stems[os.path.basename(rel)[:-3].lower()] = rel
    inbound = defaultdict(set)
    for rel, full in notes:
        text = strip_boxes(open(full, encoding="utf-8", errors="replace").read())
        for target in WIKILINK.findall(text):
            t = target.split("|")[0].split("#")[0].strip().split("/")[-1].lower()
            if t in stems and stems[t] != rel:
                inbound[t].add(rel)
    return inbound


def gen_index(vault, notes, report, inbound, big):
    by_folder = defaultdict(int)
    for rel, _ in notes:
        by_folder[rel.split("/")[0]] += 1
    def mtime(rel_full):
        return os.path.getmtime(rel_full[1])
    def fmt(p):
        return datetime.fromtimestamp(os.path.getmtime(p)).strftime("%d %b %Y")
    projects = [(rel, full) for rel, full in notes if rel.startswith("01-Proyek/")
                and not os.path.basename(rel).startswith("_Portal ")]
    projects.sort(key=mtime, reverse=True)
    recaps = [(rel, full) for rel, full in notes
              if re.search(r"(Session|Log Sesi|laporan \d{4}-\d{2}-\d{2})", os.path.basename(rel))]
    recaps.sort(key=mtime, reverse=True)
    decisions = [(rel, full) for rel, full in notes if os.path.basename(rel).startswith("Keputusan - ")]
    decisions.sort(key=mtime, reverse=True)
    portals = sorted(rel for rel, _ in notes if os.path.basename(rel).startswith("_Portal "))
    out = []
    out.append("# INDEX - Vault")
    out.append("")
    out.append(f"> Di-generate otomatis oleh `vault_lint.py --index` pada {datetime.now().strftime('%d %b %Y %H:%M')}. Jangan edit manual, perubahannya akan tertimpa.")
    out.append("")
    out.append("## Proyek aktif (12 terbaru)")
    for rel, full in projects[:12]:
        out.append(f"- [[{os.path.basename(rel)[:-3]}]] - {fmt(full)}")
    out.append("")
    out.append("## Rekap terakhir (8 terbaru)")
    if recaps:
        for rel, full in recaps[:8]:
            out.append(f"- [[{os.path.basename(rel)[:-3]}]] - {fmt(full)}")
    else:
        out.append("- belum ada")
    out.append("")
    out.append("## Keputusan tercatat")
    if decisions:
        for rel, full in decisions:
            out.append(f"- [[{os.path.basename(rel)[:-3]}]] - {fmt(full)}")
    else:
        out.append("- belum ada. Pola: `Keputusan - <Topik>.md` (lihat skill `vaultkeeper`).")
    out.append("")
    out.append("## Pintu masuk")
    for p in portals:
        out.append(f"- [[{os.path.basename(p)[:-3]}]] - `{os.path.dirname(p)}`")
    out.append("")
    out.append("## Jumlah")
    out.append(f"- {len(notes)} note markdown")
    for folder in sorted(by_folder):
        out.append(f"- `{folder}/`: {by_folder[folder]}")
    out.append("")
    out.append("## Cek kesehatan")
    out.append(f"- Link mati: {len(report['broken'])} target ({sum(len(v) for v in report['broken'].values())} rujukan)")
    wajib_n = sum(1 for iss in report["issues"].values() if any(i.startswith(WAJIB_PREFIX) for i in iss))
    out.append(f"- Pelanggaran konvensi wajib: {wajib_n} note")
    out.append(f"- File sampah: {len(report['junk'])}")
    out.append(f"- Catatan besar (>60KB): {len(big)}")
    out.append("- Perintah: `python \"D:/obsidian/AsistenObsidian/04-Sistem/scripts/vault_lint.py\" --vault \"D:/obsidian/AsistenObsidian\" --report --index`")
    out.append("")
    out.append("## Terkait")
    out.append("- [[MOC - Knowledge Base]] - index lengkap semua catatan")
    out.append("- [[Peta Vault dan Konvensi Penulisan]] - aturan penempatan dan format")
    out.append("- [[Vault Link Report]] - hasil pemeriksaan link dan konvensi")
    return "\n".join(out) + "\n"


def norm_core(t):
    return re.sub(r"[^a-z0-9]+", "", t.lower().replace("portal", ""))


def portal_hint(target, stems):
    """Tebak maksud link mati: portal tanpa underscore, beda huruf, beda tanda hubung."""
    hints = []
    if ("_" + target.lower()) in stems:
        hints.append("target ada sebagai `_Portal " + re.sub(r"^Portal\s+", "", target) + "` (butuh underscore)")
    core = norm_core(target)
    if core:
        cands = [st for st in stems if st.startswith("_portal ") and core and core in norm_core(st)]
        if cands and not hints:
            hints.append("mungkin maksud `" + os.path.basename(stems[cands[0]])[:-3] + "`")
        else:
            same = [st for st in stems if norm_core(st) == core and st != target.lower()]
            if same and not hints:
                hints.append("mungkin maksud `" + os.path.basename(stems[same[0]])[:-3] + "` (beda tanda hubung atau huruf besar/kecil)")
    return " (" + "; ".join(hints) + ")" if hints else ""


def emit(out, items, cap=40):
    for it in items[:cap]:
        out.append(it)
    if len(items) > cap:
        out.append(f"- ... dan {len(items) - cap} baris lain (jalankan `--list` untuk daftar penuh)")


def gen_report(report, big, notes):
    stems = {os.path.basename(rel)[:-3].lower(): rel for rel, _ in notes}
    wajib = {r: [i for i in iss if i.startswith(WAJIB_PREFIX)] for r, iss in report["issues"].items()}
    wajib = {r: v for r, v in wajib.items() if v}
    anjuran = {r: [i for i in iss if i.startswith(("anjuran", "info"))] for r, iss in report["issues"].items()}
    anjuran = {r: v for r, v in anjuran.items() if v}
    out = []
    out.append("# Vault Link Report")
    out.append("")
    out.append(f"> Di-generate otomatis oleh `vault_lint.py --report` pada {datetime.now().strftime('%d %b %Y %H:%M')}. Jangan edit manual. Daftar panjang dipotong, `--list konvensi` untuk penuh.")
    out.append("")
    out.append("## Ringkasan")
    out.append(f"- Link mati: {len(report['broken'])} target ({sum(len(v) for v in report['broken'].values())} rujukan)")
    out.append(f"- Pelanggaran wajib: {len(wajib)} note (nama file, aksara CJK) | anjuran belum dipenuhi: {len(anjuran)} note")
    out.append(f"- File sampah: {len(report['junk'])} | catatan besar (>60KB): {len(big)} | note yatim: {len(report['orphans'])}")
    out.append("")
    out.append("## Link mati")
    if report["broken"]:
        items = []
        for target in sorted(report["broken"], key=lambda k: -len(report["broken"][k])):
            refs = sorted(report["broken"][target])
            items.append(f"- `[[{target}]]`{portal_hint(target, stems)} - dirujuk {len(refs)} file: {', '.join('`' + r + '`' for r in refs[:4])}")
        emit(out, items)
    else:
        out.append("- tidak ada")
    out.append("")
    out.append("## Pelanggaran wajib (nama file, aksara CJK)")
    emit(out, [f"- `{rel}`: {', '.join(wajib[rel])}" for rel in sorted(wajib)]) if wajib else out.append("- tidak ada")
    out.append("")
    out.append("## Anjuran belum dipenuhi (blockquote, Terkait < 3, Tags, ukuran)")
    emit(out, [f"- `{rel}`: {', '.join(anjuran[rel])}" for rel in sorted(anjuran)]) if anjuran else out.append("- tidak ada")
    out.append("")
    out.append("## File sampah (pola sementara)")
    emit(out, [f"- `{j}`" for j in sorted(report["junk"])]) if report["junk"] else out.append("- tidak ada")
    out.append("")
    out.append("## Catatan besar (kandidat pecah ke data/)")
    emit(out, [f"- `{rel}` - {size // 1024}KB" for rel, size in sorted(big, key=lambda x: -x[1])]) if big else out.append("- tidak ada")
    out.append("")
    out.append("## Catatan tanpa link masuk (yatim)")
    emit(out, [f"- `{o}`" for o in sorted(report["orphans"])]) if report["orphans"] else out.append("- tidak ada")
    out.append("")
    out.append("## Terkait")
    out.append("- [[MOC - Knowledge Base]]")
    out.append("- [[Peta Vault dan Konvensi Penulisan]]")
    out.append("- [[INDEX - Vault]]")
    return "\n".join(out) + "\n"


ASSETS_SEEN = set()


def main():
    global ASSETS_SEEN
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=None)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--index", action="store_true")
    ap.add_argument("--list", nargs="?", const="all", default=None,
                    help="broken | konvensi | sampah | besar | yatim (kosong = semua)")
    args = ap.parse_args()

    vault = vault_path(args.vault)
    if not os.path.isdir(vault):
        print(f"vault tidak ditemukan: {vault}", file=sys.stderr)
        return 2
    global ALLOW
    ALLOW = load_allow(vault)
    notes, assets, junk = scan(vault)
    ASSETS_SEEN = assets
    issues = {}
    big = []
    for rel, full in notes:
        if os.path.basename(rel) in GENERATED:
            continue
        iss, raw = check_note(rel, full)
        if iss:
            issues[rel] = iss
        size = os.path.getsize(full)
        if size > 60 * 1024:
            big.append((rel, size))
    broken = broken_links(notes)
    inbound = inbound_count(notes)
    generated = GENERATED | {"MOC - Knowledge Base.md"}
    orphans = [rel for rel, _ in notes
               if os.path.basename(rel)[:-3].lower() not in inbound
               and os.path.basename(rel) not in generated]
    report = {"broken": dict(broken), "issues": issues, "junk": junk, "orphans": orphans}

    wajib = sum(1 for iss in issues.values()
                if any(i.startswith(WAJIB_PREFIX) for i in iss))
    print(f"vault: {vault}")
    print(f"note: {len(notes)} | link mati: {len(broken)} target | pelanggaran wajib: {wajib} note "
          f"| sampah: {len(junk)} | besar: {len(big)} | yatim: {len(orphans)}")
    for label, data in (("broken", sorted(broken, key=lambda k: -len(broken[k]))),
                        ("konvensi", sorted(issues)),
                        ("sampah", sorted(junk)),
                        ("besar", [r for r, _ in sorted(big, key=lambda x: -x[1])]),
                        ("yatim", sorted(orphans))):
        if args.list in (label, "all"):
            for d in data:
                print("-", d)

    if args.report:
        dest = os.path.join(vault, "04-Sistem", "Vault Link Report.md")
        open(dest, "w", encoding="utf-8").write(gen_report(report, big, notes))
        print("report ->", dest)
    if args.index:
        dest = os.path.join(vault, "04-Sistem", "INDEX - Vault.md")
        open(dest, "w", encoding="utf-8").write(gen_index(vault, notes, report, inbound, big))
        print("index ->", dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
