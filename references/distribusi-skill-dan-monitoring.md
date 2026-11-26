# Distribusi skill antar bot + monitoring

## When to Use

- memasang atau menyalin skill ini ke profil bot lain, atau memeriksa apakah semua salinan masih sama versinya;
- bot lain kelihatan tidak memakai skill ini padahal sudah terpasang;
- menyiapkan atau mengubah laporan otomatis (skor pengaruh, cek kesehatan) yang dikirim ke channel Discord;
- membaca tren laporan untuk memutuskan perbaikan vault berikutnya.

Dipakai saat memasang atau memverifikasi skill ini (atau skill lain) di banyak profil bot Hermes, dan saat mengirim laporan otomatis ke Discord.

## 1. Empat salinan wajib sama

1. kanonik `~/AppData/Local/hermes/skills/<kategori>/<skill>/`.
2. `profiles/<nama>/skills/<kategori>/<skill>/` untuk tiap profil aktif. Salin ULANG seluruh folder (`shutil.rmtree` lalu `shutil.copytree`), jangan menambal satu berkas.
3. mirror di vault `05-Skills/<kategori>/<skill>.md` = satu baris versi + badan `SKILL.md` (bagian setelah frontmatter).
4. repo GitHub: clone ke scratch, salin `SKILL.md` + `references/` `templates/` `scripts/`, commit, push, buktikan lewat `gh api repos/<owner>/<repo>/git/trees/main?recursive=1`.

Profil yang berstatus pending-delete tetap ikut disalin kalau murah, tapi jangan dijadikan target verifikasi.

## 2. Auto-load tiap sesi

Hermes tidak punya opsi "always load skill"; skill selalu on-demand. Yang membuatnya termuat tiap sesi adalah blok pendek di `SOUL.md` tiap profil, misalnya:

```markdown
## Vault Obsidian (otomatis, tiap sesi)

Sesi yang menyentuh vault `D:/obsidian/AsistenObsidian` atau memory kerja agent: load skill `vaultkeeper` DULU (`skill_view(name='vaultkeeper')`), ikuti 6 fasenya sebelum menulis note apa pun. Sesudah sesi vault apa pun (termasuk yang cuma membaca), jalankan skor pengaruh: `python <skills>/note-taking/vaultkeeper/scripts/vault_impact.py --send`. Dilarang `git clean -f` di vault.
```

SOUL.md memang ikut masuk system prompt: `grep <string-khas> profiles/<nama>/sessions/request_dump_*.json` mengembalikan hit pada sesi yang dibuka setelah suntingan (sesi yang masih berjalan tetap pakai prompt lama, jadi perubahan baru terasa di sesi berikutnya).

Skill yang dimuat bot lain tidak selalu menyentuh vault: kerja plugin/research memang tidak memicu fase vault. Kalau user mengharapkan bot itu ikut mencatat ke vault, lebarkan pemicunya di `SOUL.md`, jangan menambah skill kedua.

## 3. Buktikan bot benar memakai skill

Jangan percaya klaim bot. Tiga bukti, dipakai berurutan:

1. `hermes --profile <nama> skills list` -> skill tampil `enabled`.
2. One-shot: `hermes --profile <nama> -z "<tugas ringan yang memicu skill>"` -> jawabannya mengikuti fase skill.
3. Efek samping terukur: cari nama skill di `profiles/<nama>/logs/agent.log`, dan pastikan mtime berkas state (`04-Sistem/vault_impact_state.json`) berubah sesudah sesi bot itu - itu bukti skrip benar dijalankan bot, bukan oleh sesi lain.

`skill_view completed (…, N chars)` di agent.log tidak mencetak nama skill; pakai panjang isi atau bukti (3), bukan log saja. Jalur `--deliver bot-chat:<profil>` tidak selalu bisa dipakai dari `hermes send`; memicu bot lain paling andal lewat one-shot `-z` atau dengan mengirim pesan ke channel chat bot itu.

## 4. Kirim laporan ke channel Discord

- Cari id channel: `hermes send --list discord` -> baris `<nama> [chat_id]`.
- Kirim dari skrip: `hermes send --to discord:<chat_id> --file -`, teks lewat stdin, cek baris balasan `sent`.
- Cron tanpa LLM: `hermes cron create "0 21 * * *" --name "<nama job>" --script <berkas>.py --no-agent --deliver discord:<chat_id> --timezone Asia/Jakarta`; stdout skrip langsung jadi isi pesan.
- `--script` menerima NAMA berkas saja (relatif ke `~/AppData/Local/hermes/scripts/`), tanpa argumen. Untuk opsi tambahan, buat wrapper kecil di folder scripts yang memanggil skrip asli via `subprocess` dengan flag (`--send-if-stale 24`).
- Jaring pengaman ganda: sesi melapor sendiri di fase LAPOR, cron `--send-if-stale` mengisi kalau tidak ada sesi. Keduanya membaca state yang sama supaya tidak dobel kirim.

## 5. Analisis tren

`04-Sistem/vault_impact_state.json` menyimpan `history` (10 laporan terakhir: ts, skor, note, broken, wajib, junk, big, orphan, anjuran). Bacanya `json.load`, lalu bandingkan antar laporan: butir yang dulu 0 sekarang terisi? `anjuran belum dipenuhi` turun? Skor naik tanpa perbaikan angka vault = laporan kosong, bukan perbaikan. Pesan dipagu ~1900 karakter; rincian yang dipotong selalu bisa diambil dari state JSON.
