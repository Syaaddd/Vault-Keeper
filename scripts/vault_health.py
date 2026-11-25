#!/usr/bin/env python3
"""Cek kesehatan vault AsistenObsidian: jalankan linter, cetak ringkasan pendek.

Dipakai cron `--no-agent` (stdout dikirim apa adanya ke Discord). Tidak ada LLM.
Kosong = tidak ada masalah baru, tapi ringkasan tetap dicetak tiap jalan.
"""
import os
import re
import subprocess
import sys

VAULT = os.environ.get("OBSIDIAN_VAULT_PATH", r"D:/obsidian/AsistenObsidian")
LINT = os.path.join(VAULT, "04-Sistem", "scripts", "vault_lint.py")
# ponytail: ambang "besar" disamakan dengan linter; kalau linter diubah, ubah di sini juga.
AMBANG_BESAR = 60 * 1024


def main() -> int:
    if not os.path.exists(LINT):
        print(f"linter tidak ada: {LINT}")
        return 1
    r = subprocess.run([sys.executable, LINT, "--vault", VAULT, "--report", "--index"],
                       capture_output=True, text=True, errors="replace")
    out = (r.stdout or "").strip()
    if r.returncode != 0:
        print("lint gagal:")
        print((r.stderr or out)[-800:])
        return 1
    ringkas = "\n".join(l for l in out.split("\n") if l.startswith(("note:", "report", "index")))
    print(f"**Cek kesehatan vault** ({os.path.basename(VAULT)})")
    print(ringkas)
    m = re.search(r"link mati: (\d+)", out)
    if m and int(m.group(1)):
        rep = os.path.join(VAULT, "04-Sistem", "Vault Link Report.md")
        if os.path.exists(rep):
            tg = re.findall(r"(?m)^- `\[\[([^\]]+)\]\]`", open(rep, encoding="utf-8", errors="replace").read())
            if tg:
                print("link mati teratas: " + ", ".join(f"`{t}`" for t in tg[:3]))
    return 0


if __name__ == "__main__":
    sys.exit(main())