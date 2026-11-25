#!/usr/bin/env python3
"""Skor pengaruh skill vaultkeeper.

Hitung skor 0-100 dari keadaan vault (linter) plus jejak kerja sejak laporan
terakhir, lalu (opsional) kirim ke Discord lewat `hermes send`.

    python vault_impact.py            # hitung + cetak
    python vault_impact.py --send     # hitung + kirim ke channel monitoring
    python vault_impact.py --selftest # cek rumus

Catatan jujur: skor ini PROKSI terukur (kesehatan vault + jejak perubahan),
bukan uji kausal "skill bikin hasil lebih baik". Angka naik kalau vault makin
sehat dan sesi meninggalkan jejak kerja yang disepakati konvensi.
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
STATE = os.path.join(VAULT, "04-Sistem", "vault_impact_state.json")
CHANNEL = "discord:1575174326922248344"  # #monitoring-vault-keeper
INDEX = os.path.join(VAULT, "04-Sistem", "INDEX - Vault.md")
REPORT = os.path.join(VAULT, "04-Sistem", "Vault Link Report.md")


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


def load_state():
    if os.path.exists(STATE):
        try:
            return json.load(open(STATE, encoding="utf-8"))
        except Exception:
            pass
    return {"ts": now().isoformat(), **{k: 0 for k in ("note", "broken", "wajib", "junk", "big", "orphan")}}


def save_state(m, head=None):
    json.dump({"ts": now().isoformat(), "head": head, **m}, open(STATE, "w", encoding="utf-8"))


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
    age = (now() - dt.datetime.fromtimestamp(os.path.getmtime(path))).total_seconds() / 60
    return age <= minutes


def score(m, prev, notes, touched_decision, index_fresh):
    """Kembalikan (total, rincian dict). Semua komponen deterministik."""
    health = 0
    health += 15 if m["wajib"] == 0 else 0
    health += 10 if m["junk"] == 0 else 0
    health += 10 if m["broken"] <= prev.get("broken", m["broken"]) else 0
    health += 5 if m["orphan"] <= prev.get("orphan", m["orphan"]) else 0

    effect = 0
    n = len(notes)
    effect += 20 if n >= 1 else 0
    effect += 10 if n >= 10 else 0
    effect += 10 if any("/data/" in f for f in notes) else 0

    flow = 0
    flow += 10 if touched_decision else 0
    flow += 10 if index_fresh else 0
    return min(100, health + effect + flow), {"kesehatan": health, "efek": effect, "alur": flow, "note_berubah": n}


def report(m, prev, sc, detail, head):
    d = lambda k: f'{prev.get(k, m[k])}->{m[k]}'
    lines = [
        f"**Skor pengaruh skill `vaultkeeper`: {sc}%**",
        f"- rincian: kesehatan vault {detail['kesehatan']}/40, efek kerja {detail['efek']}/40, alur {detail['alur']}/20",
        f"- delta: link mati {d('broken')}, yatim {d('orphan')}, wajib {d('wajib')}, sampah {d('junk')}, note {d('note')}",
        f"- jejak sesi: {detail['note_berubah']} note berubah sejak laporan terakhir (HEAD {head[:7] if head else '-'})",
        "- catatan: proksi terukur (kesehatan vault + jejak kerja), bukan uji kausal.",
    ]
    return "\n".join(lines)


def selftest():
    m = {"note": 663, "broken": 85, "wajib": 0, "junk": 0, "big": 4, "orphan": 17}
    s, det = score(m, m, ["a.md", "b.md"], True, True)
    assert 0 <= s <= 100 and det["kesehatan"] == 40, det
    bad = {"note": 1, "broken": 200, "wajib": 3, "junk": 5, "big": 9, "orphan": 40}
    s2, det2 = score(bad, m, [], False, False)
    assert s2 == 0 and det2["note_berubah"] == 0, det2
    s3, _ = score(m, {"broken": 99, "orphan": 99}, ["x"] * 12 + ["a/data/y.md"], True, True)
    assert s3 == 100, s3
    print("selftest lulus")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true", help=f"kirim ke {CHANNEL}")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--send-if-stale", type=float, default=0,
                    help="kirim hanya kalau laporan terakhir lebih lama dari N jam")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    if a.send_if_stale and os.path.exists(STATE):
        age = (now() - dt.datetime.fromisoformat(load_state()["ts"])).total_seconds() / 3600
        if age < a.send_if_stale:
            print(f"laporan terakhir {age:.1f} jam lalu, dilewati")
            return 0
        a.send = True

    m = run_lint()
    if not m:
        print("lint gagal, skor tidak dihitung")
        return 1
    prev = load_state()
    notes = changed_notes(prev.get("ts"))
    touched_decision = any(re.match(r"Keputusan |Rekap ", os.path.basename(f)) for f in notes)
    sc, detail = score(m, prev, notes, touched_decision, fresh(INDEX, 10) and fresh(REPORT, 10))
    head = git("rev-parse", "HEAD")
    msg = report(m, prev, sc, detail, head)
    save_state(m, head)
    print(json.dumps({"skor": sc, **detail, **m}, ensure_ascii=False) if a.json else msg)
    if a.send:
        r = subprocess.run(["hermes", "send", "--to", CHANNEL, "--file", "-"],
                           input=msg, capture_output=True, text=True, errors="replace")
        print(f"kirim: {'ok' if r.returncode == 0 else 'GAGAL'} {r.stdout.strip()} {r.stderr.strip()[:200]}")
        return 0 if r.returncode == 0 else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
