#!/usr/bin/env python3
"""Skor pengaruh skill vaultkeeper - laporan rinci + tren.

Hitung skor 0-100 dari keadaan vault (linter) plus jejak kerja sejak laporan
terakhir, lalu (opsional) kirim laporan rinci ke Discord lewat `hermes send`.

    python vault_impact.py                 # hitung + cetak laporan rinci
    python vault_impact.py --send          # + kirim ke #monitoring-vault-keeper
    python vault_impact.py --note "sesi pecah note X"   # konteks sesi
    python vault_impact.py --send-if-stale 24           # kirim kalau laporan > 24 jam
    python vault_impact.py --json
    python vault_impact.py --selftest

Catatan jujur: skor ini PROKSI terukur (kesehatan vault + jejak perubahan),
bukan uji kausal "skill bikin hasil lebih baik". Butir bernilai 0 menunjuk apa
yang belum dikerjakan sesi ini, bukan penilaian kualitas tulisan.
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys

VAULT = os.environ.get("OBSIDIAN_VAULT_PATH", r"D:/obsidian/AsistenObsidian")
LINT = os.path.join(VAULT, "04-Sistem", "scripts", "vault_lint.py")
REPORT = os.path.join(VAULT, "04-Sistem", "Vault Link Report.md")
INDEX = os.path.join(VAULT, "04-Sistem", "INDEX - Vault.md")
STATE = os.path.join(VAULT, "04-Sistem", "vault_impact_state.json")
CHANNEL = "discord:1575174326922248344"  # #monitoring-vault-keeper
HIST = 10      # laporan yang disimpan untuk tren
LIMIT = 1900   # pagu karakter pesan Discord


def now():
    return dt.datetime.now()


def run_lint():
    r = subprocess.run([sys.executable, LINT, "--vault", VAULT, "--report", "--index"],
                       capture_output=True, text=True, errors="replace")
    out = r.stdout or ""
    m = re.search(r"note: (\d+) \| link mati: (\d+) target.*?pelanggaran wajib: (\d+) note.*?"
                  r"sampah: (\d+) \| besar: (\d+) \| yatim: (\d+)", out)
    if not m:
        return None
    keys = ("note", "broken", "wajib", "junk", "big", "orphan")
    return dict(zip(keys, (int(x) for x in m.groups())))


def parse_report():
    """Ambil butir rinci dari laporan linter: link mati teratas, note besar, yatim, anjuran."""
    out = {"top": [], "big_notes": [], "orphans": [], "anjuran": 0, "refs": 0}
    if not os.path.exists(REPORT):
        return out
    txt = open(REPORT, encoding="utf-8", errors="replace").read()
    m = re.search(r"anjuran belum dipenuhi: (\d+) note", txt)
    out["anjuran"] = int(m.group(1)) if m else 0
    m = re.search(r"Link mati: (\d+) target \((\d+) rujukan\)", txt)
    out["refs"] = int(m.group(2)) if m else 0

    def section(pattern):
        m = re.search(rf"^## {pattern}[^\n]*\n(.*?)(?=^## |\Z)", txt, re.S | re.M)
        return m.group(1) if m else ""

    for line in section("Link mati").splitlines():
        m = re.match(r"- `\[\[(.+?)\]\]` - dirujuk (\d+) file", line)
        if m:
            out["top"].append((m.group(1), int(m.group(2))))
    for line in section("Catatan besar").splitlines():
        m = re.match(r"- `(.+?)` - (\d+)KB", line)
        if m:
            out["big_notes"].append((m.group(1), int(m.group(2))))
    for line in section("Catatan tanpa link masuk").splitlines():
        m = re.match(r"- `(.+?)`", line)
        if m:
            out["orphans"].append(m.group(1))
    return out


def load_state():
    if os.path.exists(STATE):
        try:
            return json.load(open(STATE, encoding="utf-8"))
        except Exception:
            pass
    base = {k: 0 for k in ("note", "broken", "broken_ref", "wajib", "junk", "big", "orphan", "anjuran")}
    return {"ts": now().isoformat(), "history": [], **base}


def save_state(m, rp, head, skor, note=""):
    st = load_state()
    hist = st.get("history", [])[-HIST:]
    hist.append({"ts": now().isoformat(), "skor": skor, "note": note, "anjuran": rp["anjuran"],
                 **{k: m[k] for k in ("note", "broken", "wajib", "junk", "big", "orphan")}})
    json.dump({"ts": hist[-1]["ts"], "head": head, "skor": skor,
               **{k: m[k] for k in ("note", "broken", "broken_ref", "wajib", "junk", "big", "orphan")},
               "anjuran": rp["anjuran"], "history": hist[-HIST:]},
              open(STATE, "w", encoding="utf-8"), ensure_ascii=False)


def git(*args):
    r = subprocess.run(["git", "-C", VAULT, *args], capture_output=True, text=True, errors="replace")
    return (r.stdout or "").strip()


def changed_notes(since_iso):
    if not since_iso:
        return []
    files = git("log", f"--since={since_iso}", "--name-only", "--pretty=format:")
    return sorted({f.strip() for f in files.split("\n") if f.strip().endswith(".md")})


def fresh(path, minutes):
    if not os.path.exists(path):
        return False
    return (now() - dt.datetime.fromtimestamp(os.path.getmtime(path))).total_seconds() / 60 <= minutes


def score(m, prev, notes, touched_decision, index_fresh):
    """Komponen (total 100) plus rincian per butir supaya bisa dianalisis."""
    pts = {
        "wajib_nol": 15 if m["wajib"] == 0 else 0,
        "sampah_nol": 10 if m["junk"] == 0 else 0,
        "link_mati_tidak_naik": 10 if m["broken"] <= prev.get("broken", m["broken"]) else 0,
        "yatim_tidak_naik": 5 if m["orphan"] <= prev.get("orphan", m["orphan"]) else 0,
        "note_berubah": 20 if len(notes) >= 1 else 0,
        "note_berubah_banyak": 10 if len(notes) >= 10 else 0,
        "jejak_data": 10 if any("/data/" in f for f in notes) else 0,
        "keputusan_atau_rekap": 10 if touched_decision else 0,
        "index_report_segar": 10 if index_fresh else 0,
    }
    health = pts["wajib_nol"] + pts["sampah_nol"] + pts["link_mati_tidak_naik"] + pts["yatim_tidak_naik"]
    effect = pts["note_berubah"] + pts["note_berubah_banyak"] + pts["jejak_data"]
    flow = pts["keputusan_atau_rekap"] + pts["index_report_segar"]
    return min(100, health + effect + flow), {"kesehatan": health, "efek": effect, "alur": flow,
                                              "note_berubah": len(notes), "butir": pts}


def render(m, rp, prev, sc, det, head, notes, note=""):
    p = det["butir"]
    prev_skor = prev.get("skor")
    if prev_skor is None:
        arah = " (laporan pertama, belum ada pembanding)"
    elif sc >= prev_skor:
        arah = f" (naik {sc - prev_skor} dari {prev_skor}%)"
    else:
        arah = f" (turun {prev_skor - sc} dari {prev_skor}%)"
    prev_of = lambda k: prev.get(k, m[k])
    tanda = lambda k: "" if m[k] == prev_of(k) else (" ❌" if m[k] > prev_of(k) else " ✅")

    L = [f"**Skor pengaruh skill `vaultkeeper`: {sc}%**{arah}"]
    ctx = f"{now():%d %b %Y %H:%M} WIB · HEAD {(head or '-')[:7]} · {m['note']} note"
    prof = os.environ.get("HERMES_PROFILE") or ""
    act = os.environ.get("HERMES_SESSION_ACTOR_NAME") or ""
    if prof:
        ctx += f" · profil {prof}"
    if act:
        ctx += f" · pemicu {act}"
    L.append(ctx)
    if note:
        L.append(f"Konteks sesi: {note}")

    L.append("")
    L.append("**Penilaian**")
    L.append(f"• Kesehatan vault **{det['kesehatan']}/40** — pelanggaran wajib 0 ({p['wajib_nol']}/15) · "
             f"sampah 0 ({p['sampah_nol']}/10) · link mati tidak naik ({p['link_mati_tidak_naik']}/10) · "
             f"yatim tidak naik ({p['yatim_tidak_naik']}/5)")
    bonus = f" + {p['note_berubah_banyak']} karena ≥10 note" if p["note_berubah_banyak"] else ""
    L.append(f"• Efek kerja **{det['efek']}/40** — {det['note_berubah']} note berubah sejak laporan terakhir "
             f"({p['note_berubah'] + p['note_berubah_banyak']}/30{bonus}) · jejak `data/` ({p['jejak_data']}/10)")
    L.append(f"• Alur **{det['alur']}/20** — note Keputusan/Rekap disentuh ({p['keputusan_atau_rekap']}/10) · "
             f"index + report segar ({p['index_report_segar']}/10)")

    L.append("")
    L.append("**Angka vault** (laporan lalu → sekarang)")
    L.append(f"• link mati {prev_of('broken')}→{m['broken']} target ({m['broken_ref']} rujukan){tanda('broken')} · "
             f"pelanggaran wajib {prev_of('wajib')}→{m['wajib']} · sampah {prev_of('junk')}→{m['junk']}")
    L.append(f"• yatim {prev_of('orphan')}→{m['orphan']}{tanda('orphan')} · note besar (>60KB) {prev_of('big')}→{m['big']} · "
             f"anjuran belum dipenuhi {prev.get('anjuran', rp['anjuran'])}→{rp['anjuran']} · total note {prev_of('note')}→{m['note']}")

    opsional = []
    if rp["top"]:
        opsional.append(["", "**Link mati paling sering dirujuk** (kandidat note baru)"] +
                        [f"• [[{nama}]] — {n} rujukan" for nama, n in rp["top"][:5]])
    if rp["big_notes"]:
        opsional.append(["", "**Note besar** (kandidat pecah ke `data/`)"] +
                        [f"• `{path}` — {kb}KB" for path, kb in rp["big_notes"][:5]])
    if notes:
        blok = ["", f"**Note yang berubah sesi ini** ({len(notes)})"] + [f"• {f}" for f in notes[:8]]
        if len(notes) > 8:
            blok.append(f"• … dan {len(notes) - 8} lain")
        opsional.append(blok)
    if rp["orphans"]:
        opsional.append(["", f"**Yatim teratas** ({m['orphan']} total)"] +
                        [f"• `{path}`" for path in rp["orphans"][:4]])

    catatan_len = len(L)  # penanda: semua setelah indeks ini = buntut (tren + catatan)
    hist = (prev.get("history") or [])[-4:] + [{"ts": now().isoformat(), "skor": sc}]
    L.append("")
    L.append("**Tren laporan terakhir**")
    for h in hist[-5:]:
        t_ = dt.datetime.fromisoformat(h["ts"])
        L.append(f"• {t_:%d %b %H:%M} — {h['skor']}%")
    s = [h["skor"] for h in hist[-5:]]
    if len(s) > 1:
        sk = "naik" if s[-1] > s[0] else ("turun" if s[-1] < s[0] else "datar")
        L.append(f"• arah {len(s)} laporan: {sk} ({s[0]}% → {s[-1]}%)")

    L.append("")
    L.append("Catatan: skor = proksi terukur (kesehatan vault + jejak kerja), bukan uji kausal. "
             f"Butir 0 menunjuk yang belum dikerjakan sesi ini. Riwayat {HIST} laporan: `04-Sistem/vault_impact_state.json`.")

    # core = L + tren + catatan; blok opsional mengisi sisa pagu (paling penting dulu)
    buntut_len = len(L) - catatan_len
    core = len("\n".join(L))
    budget = LIMIT - core
    dipakai = []
    for blok in opsional:
        for batas in (len(blok), 3, 2):
            potong = blok[:batas]
            if batas < len(blok):
                potong = potong + [f"• … ({len(blok) - batas} baris lain di state JSON)"]
            if len("\n".join(potong)) <= budget:
                dipakai += potong
                budget -= len("\n".join(potong))
                break
    buntut = L[catatan_len:]
    return "\n".join(L[:catatan_len] + dipakai + buntut)


    return "\n".join(L)


def selftest():
    m = {"note": 669, "broken": 85, "broken_ref": 109, "wajib": 0, "junk": 0, "big": 4, "orphan": 17}
    s, det = score(m, m, ["a.md", "b.md"], True, True)
    assert 0 <= s <= 100 and det["kesehatan"] == 40 and det["butir"]["note_berubah"] == 20, det
    bad = {"note": 1, "broken": 200, "broken_ref": 9, "wajib": 3, "junk": 5, "big": 9, "orphan": 40}
    s2, det2 = score(bad, m, [], False, False)
    assert s2 == 0 and det2["note_berubah"] == 0, det2
    s3, det3 = score(m, {"broken": 99, "orphan": 99}, ["x"] * 12 + ["a/data/y.md"], True, True)
    assert s3 == 100 and all(det3["butir"].values()), det3
    rp = {"top": [("Custom Items untuk MC", 15)], "big_notes": [("a.md", 81)], "orphans": ["y.md"], "anjuran": 613, "refs": 109}
    prev = {"broken": 99, "orphan": 99, "anjuran": 610, "skor": 50,
            "history": [{"ts": "2026-11-25T23:00:00", "skor": 50}]}
    msg = render(m, rp, prev, 100, det3, "abc1234", ["a.md"] * 12, "uji render")
    assert "Tren laporan terakhir" in msg and "Kesehatan vault" in msg and len(msg) <= LIMIT, len(msg)
    print("selftest lulus")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true", help=f"kirim ke {CHANNEL}")
    ap.add_argument("--send-if-stale", type=float, default=0,
                    help="kirim hanya kalau laporan terakhir lebih lama dari N jam")
    ap.add_argument("--note", default="", help="konteks sesi ikut dilaporkan")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    if a.send_if_stale:
        st = load_state()
        age = (now() - dt.datetime.fromisoformat(st["ts"])).total_seconds() / 3600 if st.get("ts") else 1e9
        if age < a.send_if_stale:
            print(f"laporan terakhir {age:.1f} jam lalu, dilewati")
            return 0
        a.send = True

    m = run_lint()
    if not m:
        print("lint gagal, skor tidak dihitung")
        return 1
    rp = parse_report()
    m["broken_ref"] = rp["refs"] or m["broken"]
    prev = load_state()
    notes = changed_notes(prev.get("ts"))
    touched = any(re.match(r"Keputusan |Rekap ", os.path.basename(f)) for f in notes)
    sc, det = score(m, prev, notes, touched, fresh(INDEX, 10) and fresh(REPORT, 10))
    head = git("rev-parse", "HEAD")
    msg = render(m, rp, prev, sc, det, head, notes, a.note)
    save_state(m, rp, head, sc, a.note)
    print(json.dumps({"skor": sc, "anjuran": rp["anjuran"], **det, **m}, ensure_ascii=False) if a.json else msg)
    if a.send:
        r = subprocess.run(["hermes", "send", "--to", CHANNEL, "--file", "-"],
                           input=msg, capture_output=True, text=True, errors="replace")
        print(f"kirim: {'ok' if r.returncode == 0 else 'GAGAL'} {r.stdout.strip()} {r.stderr.strip()[:200]}")
        return 0 if r.returncode == 0 else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
