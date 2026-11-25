# Konvensi Vault AsistenObsidian

> Ringkasan aturan kerja vault. Sumber resmi di dalam vault: `04-Sistem/Peta Vault dan Konvensi Penulisan.md`; kalau berbeda, yang di vault menang.

## Peta folder

| Folder | Isi |
|--------|-----|
| `01-Proyek/` | Catatan proyek aktif, `Log Sesi.md`, `_Portal Proyek.md` |
| `02-Workflow/` | SOP, konvensi git, setup environment, keputusan lintas proyek |
| `03-Referensi/<Kategori>/` | Referensi teknis per kategori (Minecraft, Slimefun5-Wiki, Slimefun5-Engineering, Web-Development, Architecture, Database, DevOps, Security, Design, Public APIs, Jobs) |
| `04-Sistem/` | Meta vault: `INDEX - Vault.md`, `MOC - Knowledge Base.md`, `Peta Vault dan Konvensi Penulisan.md`, `Anti-Slop Writing Rules.md`, `Vault Link Report.md`, `scripts/` |
| `05-Skills/` | Mirror skill Hermes per kategori |
| `06-Memory/<Agent>/` | Memory persisten per agent (Minju, Bagas, Agus) |
| `_Agent-Memory/` | Gudang memory agent + `apikeys/`, `arsip/`, `logs/`, `scripts/`. Dipakai cron jobs-hunter dan research - jangan hapus isinya tanpa cek cron |

Note baru masuk **leaf folder**, bukan root kategori. Setiap folder punya `_Portal <Nama>.md` sebagai pintu masuk.

## Peran tiga index

| File | Peran | Kapan dibuka |
|------|-------|--------------|
| `INDEX - Vault.md` | Orientasi satu layar: proyek aktif, rekap terakhir, keputusan terbuka | Setiap awal sesi, auto-generate |
| `MOC - Knowledge Base.md` | Index of indexes: link + satu baris label | Kalau butuh daftar penuh |
| `_Portal <Kategori>.md` | Detail satu kategori: daftar catatan + deskripsi | Begitu topik sudah jelas |

Deskripsi panjang hidup di portal (heading `## Arsip Ringkasan MOC` untuk teks yang dulu menempel di MOC). MOC dijaga ringan: kalau satu baris MOC lewat ~120 karakter, pindahkan teksnya ke portal.

## Format note

```
# Judul

> Satu baris ringkasan di blockquote.

## Seksi
Tabel / code block / daftar - hindari paragraf panjang.

## Terkait
- [[Note terkait]] - alasan singkat kenapa terkait

---
Tags: #tag1 #tag2
```

Tanpa YAML frontmatter. Bahasa Indonesia informal-teknis. Minimal 3 wikilink di `## Terkait` dan satu blockquote ringkasan adalah **anjuran kuat**, bukan syarat mutlak.

## Aturan nama file

- Tanpa em dash (`—`); pakai `-`. Alasan: aturan anti-slop + path non-ASCII pernah bikin tool `patch`/`read_file` gagal.
- Prefix `Slimefun5 - ` untuk dump wiki resmi, `_Portal ` untuk note hub.
- `Keputusan - <Topik>.md` untuk note keputusan.

## Tabel rekap (jangan bikin gaya keempat)

| Jenis | Rumah |
|-------|-------|
| Sesi kerja biasa | append `<Proyek>/Log Sesi.md` |
| Sesi yang ubah arsitektur | note sendiri di folder proyek |
| Keputusan | `Keputusan - <Topik>.md` |
| Hasil cron agent | `06-Memory/<Agent>/laporan YYYY-MM-DD - <topik>.md` |
| Rekap mingguan lintas proyek | `04-Sistem/Rekap Mingguan - YYYY-Www.md` |

## Note keputusan

Seksi: Konteks, Opsi, Keputusan, Alasan, Konsekuensi, Pembalik, Terkait. Bagian **Pembalik** wajib: kapan keputusan ini harus ditinjau ulang atau dibatalkan.

## Linter

```bash
python "D:/obsidian/AsistenObsidian/04-Sistem/scripts/vault_lint.py" --vault "D:/obsidian/AsistenObsidian" [--report] [--index] [--list]
```

- Keluaran default: ringkasan hitungan (note, link mati, pelanggaran wajib, sampah, note besar, yatim).
- `--report`: tulis ulang `04-Sistem/Vault Link Report.md`.
- `--index`: tulis ulang `04-Sistem/INDEX - Vault.md`.
- `--list`: cetak daftar temuan untuk dibaca.

Pelanggaran wajib = nama file (em dash/non-ASCII), aksara CJK di isi, link portal tanpa underscore. Tags/Terkait/ukuran hanya anjuran.

## Note besar dan arsip `data/`

Ambang sekitar 60 KB. Pola: note depan simpan ringkasan/status/aturan + bagian `## Arsip`; isi lama ke `<folder>/data/<nama> - arsip NN.md` (potongan maksimal sekitar 45 KB). Tiap arsip: blockquote asal-usul, `## Terkait` minimal 3 wikilink (note depan + arsip tetangga), `Tags:`.

Note yang ditulis cron pakai `data/<nama> - YYYY-MM.md` untuk dump baru; note depan hanya baris status. Dedup cron pakai `rg` di seluruh folder (note depan + `data/`).

`04-Sistem/vault_lint_allow.txt` = pola note yang aksara CJK-nya sengaja (nama layanan asing, kutipan bukti, `data/*.md`).

## Sweep link mati

Urutan resolusi: nama persis (case-insensitive) -> `_Portal <stem>` -> nama ternormalisasi (buang non-alfanumerik) -> satu-satunya kandidat berawalan sama (kunci minimal 6 karakter). Hindari pencocokan `contains` bebas: menghasilkan target ngawur seperti `[[Security]]`.

Sesudah sapu: jalankan `--report` lagi, link mati harus turun dan tidak ada link baru rusak. Target yang tidak ada di vault = note belum ditulis: biarkan, itu memang penanda TODO di index.

## Portal dan note yatim

Folder kategori `NN-Nama` punya portal `_Portal Nama.md` (angka dibuang). Note tanpa backlink ditautkan dari portal folder lewat heading `## Catatan Belum Tertaut` (satu bullet per note); jangan menambah heading itu ke note yang ditulis cron, arsip `data/`, atau mirror skill.

## Git vault

Vault repo git lokal. Commit sebelum operasi besar (pecah note, sapu link, rename massal); pulihkan file salah dengan `git checkout HEAD -- <path>`. `.gitignore` menutup `.obsidian/workspace*.json`, `.obsidian/cache/`, `.trash/`, `_Agent-Memory/apikeys/`, `*.bak`.

Bahaya pecah ulang: skrip pemecah pernah menghapus arsip lama karena menghapus pola `<stem> - arsip *.md` sebelum menulis ulang. Cek isi arsip yang ada dulu, hapus hanya kalau itu memang hasil pecahan note yang sama.
