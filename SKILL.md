---
name: vaultkeeper
description: Use when working in the Obsidian vault (notes, recap, lint).
version: 2.5.0
author: Teknium (teknium1), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Obsidian, Notes, Markdown, Vault]
    related_skills: [question-files]
---

# Obsidian Vault - mekanik + disiplin kerja

Vault kerja: `D:/obsidian/AsistenObsidian` (`OBSIDIAN_VAULT_PATH` di `~/.hermes/.env`). Skill ini dua lapis:

- **Mekanik** - baca, tulis, patch, wikilink, pitfall tool.
- **Disiplin** - 6 fase ORIENT / THINK / WRITE / RECAP / TIDY / LAPOR, supaya vault dipakai untuk berpikir dan berkarya, bukan cuma menimbun catatan.

Konvensi lengkap (peta folder, format note, aturan nama, tempat rekap): `references/konvensi-vault.md`. Template: `templates/note-keputusan.md`, `templates/rekap-mingguan.md`. Linter kanonik: `04-Sistem/scripts/vault_lint.py` di dalam vault (jalan di profil mana pun). Skor pengaruh sesi: `scripts/vault_impact.py`.

Skill ini dipasang di semua profil agent dan dimuat otomatis di awal sesi yang menyentuh vault (aturan di `SOUL.md` tiap profil).

## 1. ORIENT - awal sesi, 1 file saja

Baca `04-Sistem/INDEX - Vault.md` (satu layar: proyek aktif, rekap terakhir, keputusan terbuka). MOC dan 660-an note hanya dibuka kalau butuh daftar penuh; kalau topik sudah jelas, langsung `_Portal <Kategori>.md`.

Refresh index + laporan link satu perintah:

```bash
python "D:/obsidian/AsistenObsidian/04-Sistem/scripts/vault_lint.py" --vault "D:/obsidian/AsistenObsidian" --report --index
```

## 2. THINK - keputusan punya rumah

Keputusan yang mengubah arah (arsitektur, alur kerja, tool, gaya penulisan) ditulis jadi `Keputusan - <Topik>.md` di folder proyek, atau `02-Workflow/` kalau lintas proyek, pakai `templates/note-keputusan.md`. Seksi wajib: Konteks, Opsi, Keputusan, Alasan, Konsekuensi, **Pembalik** (kondisi kapan keputusan ini dibatalkan).

Alasan: keputusan yang cuma hidup di chat hilang dalam sepekan; note keputusan bisa dicari, di-link, dan dibatalkan dengan sadar.

Saat butuh keputusan atau approval user: pakai skill `question-files` (file `.md` yang di-tick lalu dikirim balik), jangan `clarify`.

## 3. WRITE - nulis ikut konvensi

Format: `# Judul` lalu blockquote satu baris, `##` seksi berisi tabel/code block (hindari prosa panjang), `## Terkait` minimal 3 wikilink plus alasan singkat, baris `Tags:` di akhir. Tanpa YAML frontmatter. Nama file tanpa em dash. Bahasa Indonesia informal-teknis, istilah teknis tetap Inggris; aturan bahasa lengkap di [[Anti-Slop Writing Rules]].

Note baru masuk leaf folder, lalu `_Portal <Kategori>.md` diperbarui di sesi yang sama. MOC hanya ditambah kalau note-nya penting.

## 4. RECAP - satu tempat per jenis

| Jenis rekap | Rumahnya |
|-------------|----------|
| Sesi kerja biasa | append ke `<Proyek>/Log Sesi.md` |
| Sesi yang mengubah arsitektur/keputusan | note sendiri di folder proyek + `Keputusan - <Topik>.md` |
| Hasil cron agent | `06-Memory/<Agent>/laporan YYYY-MM-DD - <topik>.md` |
| Rekap lintas proyek mingguan | `04-Sistem/Rekap Mingguan - YYYY-Www.md` pakai `templates/rekap-mingguan.md` |

Jangan bikin gaya keempat. Rekap kelompokkan sebagai: selesai, gagal/tertunda, keputusan, next step.

## 5. TIDY - perawatan berkala

`vault_lint.py --report` menulis ulang `04-Sistem/Vault Link Report.md` (link mati, pelanggaran konvensi wajib, sampah, note besar, note yatim) dan `--index` menyusun `INDEX - Vault.md`. Rapikan hanya yang muncul di laporan, jangan sapu ulang ratusan note sekaligus.

Cara pangkas index yang membengkak: pindahkan deskripsi panjang dari MOC ke `_Portal <Kategori>.md` di bawah heading `## Arsip Ringkasan MOC`, sisakan satu baris label di MOC. Verifikasi wajib setelah pangkas: jumlah wikilink di MOC sebelum == sesudah (di luar blok kode), dan setiap teks yang dipindah benar-benar ada di file tujuan.

Note besar (di atas sekitar 60 KB): pecah jadi note depan ringkas plus arsip `data/<nama> - arsip NN.md` (potongan maksimal sekitar 45 KB). Note depan simpan status/ringkasan/aturan + bagian `## Arsip`. Cara aman: pecah per blok heading, tulis tiap blok dari data yang sudah dipegang di memori ke file arsip, lalu VERIFIKASI tiap heading dan tiap badan blok masih ada di gabungan note depan + arsip (hitungan blok hilang wajib 0) sebelum menimpa note depan. Note yang ditulis cron: dump baru ke `data/<nama> - YYYY-MM.md`, note depan hanya baris status, dan prompt job-nya ikut diubah.

Sweep link mati: resolusi berurutan - nama persis (case-insensitive) -> `_Portal <stem>` -> bentuk ternormalisasi -> satu-satunya kandidat berawalan sama (panjang kunci minimal 6). Jangan pakai pencocokan `contains` tanpa syarat tunggal: hasilnya sampah seperti `[[Security]]`. Sesudah sapu, jalankan linter lagi dan pastikan jumlah link mati turun dan tidak ada link baru rusak. Target yang benar-benar tidak ada = note belum ditulis: biarkan, cukup tercatat di `Vault Link Report.md`.

Note yatim (tanpa backlink): tautkan dari portal folder lewat heading `## Catatan Belum Tertaut`, satu bullet per note. Jangan menambahkan heading itu ke note yang ditulis cron, portal, mirror skill, atau arsip `data/` - agent cron bisa menulis ulang file itu dan tautannya hilang.

Nama portal folder kategori: folder `NN-Nama` punya portal `_Portal Nama.md` di dalamnya (angka dibuang). `_Portal 01-Proyek` tidak ada; itu kesalahan yang paling sering muncul saat menyapu link.

Kalau vault sudah repo git, commit sebelum operasi besar dan pulihkan file salah pakai `git checkout HEAD -- <path>`. JANGAN pakai `git clean -f` di vault: cron agent menulis file baru yang belum terlacak (misalnya `data/<nama> - YYYY-MM.md`), dan `clean` menghapusnya tanpa riwayat. Cara aman membuang file sisa: hapus per path, bukan per folder. Skrip pemecah note pernah menghapus arsip lama karena menghapus `<stem> - arsip *.md` sebelum menulis ulang: cek dulu apakah arsip yang ada memang hasil pecahan note yang sama sebelum menghapus.

`04-Sistem/vault_lint_allow.txt` menampung pola note yang aksara CJK-nya sengaja (nama layanan asing, kutipan bukti, data mentah `data/*.md`); linter melewati cek aksara untuk pola itu, jadi jangan buang waktu menghapus CJK di dalam data mentah.

Cek kesehatan rutin: skrip `~/AppData/Local/hermes/scripts/vault_health.py` menjalankan linter lalu mencetak ringkasan pendek. Cron `Vault health mingguan` (id `6d9cb2cfe407`, Senin 08.00 WIB, mode `--no-agent`, kirim ke #minju-chat) memanggilnya; stdout skrip langsung jadi pesan, tanpa LLM. Kalau linter dipindah, ubah `LINT`/`VAULT` di skrip itu.

## 6. LAPOR - skor pengaruh (tiap sesi vault)

Sesudah kerja vault selesai (ujung fase TIDY), jalankan:

```bash
python "<skill>/scripts/vault_impact.py" --send
```

Skrip menghitung skor 0-100 lalu mengirimnya ke #monitoring-vault-keeper (`discord:1575174326922248344`) lewat `hermes send`. Komponen: kesehatan vault 40 (pelanggaran wajib 0, sampah 0, link mati & yatim tidak naik), efek kerja 40 (jumlah note berubah sejak laporan terakhir + jejak `data/`), alur 20 (note Keputusan/Rekap disentuh, index + report segar). Pembanding disimpan di `04-Sistem/vault_impact_state.json`.

Skor itu proksi terukur (kesehatan vault + jejak kerja), bukan uji kausal. Laporkan apa adanya; jangan naikkan angka dengan mengarang kerja. Kalau pengiriman gagal, sebut kegagalannya di balasan akhir sesi, jangan diam.

## Vault path

Use a known or resolved vault path before calling file tools.

The documented vault-path convention is the `OBSIDIAN_VAULT_PATH` environment variable, for example from `${HERMES_HOME:-~/.hermes}/.env`. If it is unset, use `~/Documents/Obsidian Vault`.

File tools do not expand shell variables. Do not pass paths containing `$OBSIDIAN_VAULT_PATH` to `read_file`, `write_file`, `patch`, or `search_files`; resolve the vault path first and pass a concrete absolute path. Vault paths may contain spaces, which is another reason to prefer file tools over shell commands.

If the vault path is unknown, `terminal` is acceptable for resolving `OBSIDIAN_VAULT_PATH` or checking whether the fallback path exists. Once the path is known, switch back to file tools.

## Mekanik file

- **Baca**: `read_file` dengan path absolut (numbering + pagination), bukan `cat`.
- **Daftar**: `search_files` `target: "files"`, `pattern: "*.md"`, bukan `ls`/`find`.
- **Cari**: `search_files` `target: "content"` + `file_glob: "*.md"`.
- **Buat note**: `write_file` dengan markdown penuh, bukan heredoc.
- **Append**: `read_file` dulu, lalu `patch` dengan anchor stabil (heading / blok penutup); `write_file` kalau menulis ulang lebih jelas.
- **Edit terarah**: `patch` selama konteksnya unik. Path non-ASCII: lihat Pitfall.

## Pitfalls (semua pernah kena)

- **Path non-ASCII**: `patch`/`read_file` bisa gagal "Failed to read file" pada path berisi em dash walau filenya ada. Panggil `patch()` dari `execute_code` untuk path seperti itu. `search_files(target="files")` glob `*Case Study*` mengembalikan 0, sementara `*Case*` jalan.
- **Rename note**: sapu semua `[[nama lama]]` di seluruh note DULU, baru `os.rename`. Wikilink berbasis nama file, jadi rename tanpa sapu link = note yatim.
- **Link mati**: cek target ada di daftar nama file aktual, termasuk underscore portal (`[[_Portal X]]`, bukan `[[Portal X]]`). Lewati blok kode saat memindai, kalau tidak contoh di dalam code block jadi false positive.
- **`.obsidian/*.json`**: edit pakai `execute_code` + `json.dump()`, jangan `write_file`/`patch` (JSON satu baris bikin anchor patch tidak andal). Baca dulu supaya key lain tidak hilang.
- **Teks panjang hasil generate**: assert tidak ada codepoint CJK/fullwidth dan assert sentinel yang mau disisipkan benar-benar masuk, sebelum `write_file`. Cek visual tidak cukup.
- **`$TMPDIR`** tidak diteruskan ke kernel `execute_code`, dan di `terminal` artinya direktori temp Windows. Panggil skrip dengan path absolut, jangan `cd "$TMPDIR" && python x.py`.
- **Sumber 403/blokir**: ambil markdown mentah via `curl` ke raw URL, batch beberapa URL dalam satu `execute_code`.

## Stray / duplicate vault cleanup

Kalau ada beberapa folder vault berdampingan (kopian typo dari sesi lama), konsolidasi ke vault kanonik, jangan dibiarkan:

1. Daftar tiap kandidat + jumlah file & `.md`. Jangan menebak yang kanonik kalau lebih dari satu berisi konten nyata - konfirmasi ke user.
2. Bandingkan file senama: jumlah karakter, baris, md5, daftar heading. Klasifikasi identik / tersuperseded / unik.
3. Gabung hanya konten unik. Kalau stray punya tabel lebih baru, ganti tabel lama, jangan tempel dua tabel yang saling bertentangan.
4. Sisipkan seksi baru di anchor heading nyata, bukan ujung file.
5. Verifikasi sentinel: assert 8-15 string khas dari konten stray muncul di note gabungan.
6. Baru hapus folder stray, lalu list ulang folder induk untuk memastikan tinggal satu vault.

**Urutan wajib: gabung -> verifikasi -> hapus.** Menghapus sebelum verifikasi = kehilangan data permanen.

## Wikilinks

Obsidian me-resolve `[[Note Name]]` berbasis nama file. Tulis bare `[[Note Name]]` tanpa prefix folder; pakai `[[Folder/Note]]` hanya kalau ada dua note bernama sama.

## Aksen folder

`.obsidian/snippets/folder-colors.css` memberi warna per folder (`[data-path^]`), portal dapat aksen emas + prefix `◆`. Sub-folder baru di `03-Referensi/` harus dapat blok CSS sendiri, dan `"folder-colors"` harus ada di `enabledCssSnippets` (`appearance.json`). Warna node graph ada di `graph.json` -> `colorGroups` (rgb desimal).
