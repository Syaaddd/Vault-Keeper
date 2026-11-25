# Vault-Keeper

Skill Hermes untuk menggarap vault Obsidian `AsistenObsidian` (dan vault Obsidian lain yang ikut konvensi ini): mekanik baca/tulis note, disiplin kerja 5 fase, linter kesehatan vault, plus aturan pecah note besar.

Versi: **2.4.0** (dulu bernama `obsidian`).

## Isi

| Berkas | Fungsi |
|---|---|
| `SKILL.md` | Induk skill: 5 fase ORIENT / THINK / WRITE / RECAP / TIDY, mekanik file, pitfalls |
| `references/konvensi-vault.md` | Peta folder, format note, aturan nama file, tempat rekap, pola arsip, sapu link |
| `templates/note-keputusan.md` | Template note keputusan (Konteks, Opsi, Keputusan, Alasan, Konsekuensi, Pembalik) |
| `templates/rekap-mingguan.md` | Template rekap lintas proyek mingguan |
| `scripts/vault_lint.py` | Linter vault (stdlib Python, tanpa dependensi): link mati, pelanggaran konvensi wajib, sampah, note besar, note yatim, aksara CJK nyasar |
| `scripts/vault_health.py` | Pembungkus tipis untuk cron: jalankan linter, cetak ringkasan 4-5 baris |

## Pasang sebagai skill Hermes

Salin folder ini (tanpa README) ke direktori skill profil:

```bash
git clone https://github.com/Syaaddd/Vault-Keeper-.git
cp -r Vault-Keeper ~/.hermes/skills/note-taking/vaultkeeper
```

Di Windows, direktori profilnya misalnya `C:\Users\<user>\AppData\Local\hermes\skills\note-taking\vaultkeeper`.

Setelah itu skill bisa dimuat dengan `skill_view(name='vaultkeeper')`.

## Jalankan linter

```bash
python scripts/vault_lint.py --vault "D:/obsidian/AsistenObsidian" --report --index
```

Opsi lain: `--list broken`, `--list konvensi`, `--list sampah`, `--list besar`, `--list yatim` (tanpa nilai = semua).

Linter menulis dua berkas di vault: `04-Sistem/Vault Link Report.md` dan `04-Sistem/INDEX - Vault.md` (keduanya auto-generate, jangan diedit manual).

## Cek kesehatan berkala

`scripts/vault_health.py` dipanggil cron mingguan: jalankan linter, kirim ringkasan pendek. Di Hermes bisa dipasang mode tanpa LLM:

```bash
hermes cron create "0 8 * * 1" --name "Vault health mingguan" --script vault_health.py --no-agent --deliver discord:<channel_id> --timezone Asia/Jakarta
```

## Konvensi inti yang ditegakkan

- Nama file tanpa em dash dan tanpa aksara non-ASCII; portal bernama `_Portal <Kategori>.md` dan dirujuk `[[_Portal <Kategori>]]`.
- Note tanpa YAML frontmatter; blockquote ringkasan + `## Terkait` minimal 3 wikilink + baris `Tags:` di akhir.
- Note di atas sekitar 60 KB dipecah: note depan ringkas plus arsip `data/<nama> - arsip NN.md` (potongan maksimal sekitar 45 KB); arsip yang masih kelebihan dipecah lagi jadi `<arsip> - bagian NN.md`.
- Note yang ditulis agent/cron: dump mentah ke `data/<nama> - YYYY-MM.md`, note depan hanya baris status.
- Note tanpa backlink ditautkan dari portal folder lewat heading `## Catatan Belum Tertaut`.
- Vault disimpan sebagai repo git lokal; jangan pakai `git clean -f` di dalam vault karena bisa menghapus keluaran cron yang belum terlacak.

## Lisensi

MIT (lihat header `SKILL.md`).
