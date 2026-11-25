# Panduan Desain & Implementasi UI — BPIC17 Event Log Analyzer

Dokumen ini menjadi acuan resmi bagi seluruh kontributor saat mengembangkan, memperbarui, atau menambah komponen antarmuka desktop **BPIC17 Event Log Analyzer** (Python, PM4Py, PySide6).

---

## 1. Filosofi & Prinsip Dasar

1. **Alat Kerja yang Tenang dan Tegas:** Antarmuka harus terasa seperti instrumen analisis data yang dirancang khusus untuk kejelasan jawaban dan keterlacakan bukti (*evidence*), bukan *landing page* pemasaran.
2. **Satu Fokus Utama per Layar:** Setiap tab memiliki hierarki visual yang jelas — angka jawaban besar di atas, aturan filter di tengah, dan tabel/jejak bukti di bawah.
3. **Hierarki Tanpa Dekorasi:** Gunakan **ukuran teks, ketebalan huruf (`font-weight`), ruang kosong (`16–24 px`), dan garis pemisah `1 px`**, bukan kotak berlapis, bayangan, atau gradien.
4. **Keterlacakan Penuh (Sesuai Penilaian Akademik):** Setiap angka wajib berasal dari hasil pemrosesan event log aktif (dilarang *hard-coded*), dan dapat ditelusuri hingga `Case ID` asli serta event pembuktinya.

---

## 2. Palet Warna Resmi (Light Mode)

Seluruh warna didefinisikan sebagai konstanta token di bagian atas `src/gui.py`.

| Token | Kode Hex | Penggunaan |
|---|---|---|
| `NAVY` | `#0B1F5C` | Warna aksen tunggal: header datar (`64 px`), chip soal aktif, bar progres aktivitas & corong, tombol unit aktif. |
| `YELLOW` | `#FFC700` | **Hanya untuk satu tombol aksi utama per layar:** tombol **Ekspor** (dengan teks `#0B1F5C`). |
| `BG_CANVAS` | `#F5F7FB` | Latar belakang utama jendela aplikasi (netral dingin). |
| `BG_CARD` | `#FFFFFF` | Latar kartu metrik (`KartuAngka`), dialog, input, dan tabel. |
| `BG_SURFACE_MUTED` | `#F8FAFC` | Latar header kolom tabel dan chip event non-sorot. |
| `BORDER` | `#E2E8F0` | Garis pemisah struktural `1 px` dan border kartu/tabel. |
| *Input/Button Border* | `#CBD5E1` | Border tipis tegas pada tombol sekunder, `QLineEdit`, dan `QComboBox`. |
| `TEXT_PRIMARY` | `#0F172A` | Teks utama, judul bagian, dan angka besar. |
| `TEXT_MUTED` | `#64748B` | Teks label kartu, keterangan sekunder, dan header kolom tabel. |
| `GREEN` / `GREEN_BG` | `#16A34A` / `#DCFCE7` | Hanya untuk status valid/lolos (`BadgeStatus`, `ChipStatus`, status `"Ya"`). |
| `RED` / `RED_BG` | `#DC2626` / `#FEE2E2` | Hanya untuk status gagal/error dan garis batas `45 hari` pada histogram. |
| `AMBER_BG` / `AMBER_TEXT` | `#FEF3C7` / `#92400E` | **Khusus** untuk menandai chip event bukti pada `StripAlur` (border `#FCD34D`). |
| `SELECTION_BG` / `SELECTION_TEXT` | `#EEF2FF` / `#1E3A8A` | Sorot baris terpilih di tabel dan kartu soal aktif. |
| `BLUE_LINK` | `#2563EB` | Tautan aksi teks (`Lihat semua aktivitas`, `Daftar case dan durasi`) dan garis bawah tab aktif. |

---

## 3. Tipografi, Satuan & Format Angka

* **Keluarga Font:** Satu keluarga font sans sistem: `system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif`. **Dilarang memakai font serif atau display dekoratif.**
* **Ukuran Minimum:** Tidak ada teks di bawah **`12 px`** di seluruh aplikasi.
  * Angka jawaban raksasa (`lbl_22_ans`): `38 px` tebal (`700`).
  * Angka kartu (`KartuAngka`): `28 px` tebal (`700`).
  * Judul header: `18 px` tebal (`700`).
  * Judul seksi & tab: `15 px`.
  * Label kartu & tabel: `13–14 px`.
  * Teks sekunder / sub-teks lifecycle: `12 px`.
* **Format Indonesia & Presisi Global:**
  * Gunakan helper `fmt_int()` (pemisah ribuan titik: `13.087`) dan `fmt_num(val, p)` (koma desimal: `6,90`, `30,00%`).
  * Pengaturan **Ketelitian** (`2 desimal` atau `4 desimal`) berlaku **global** pada tab **Data**, **Exercise 11.7**, **Exercise 11.15 & 11.18**, **Exercise 11.22**, dan grafik.
  * Satuan durasi ditulis lengkap **`hari`** (jangan disingkat `hr` agar tidak ambigu dengan *hour*).
* **Penulisan Case ID:** Tampilkan ID asli (`Application_1221917431`, `CASE_01_DOUBLE_ACCEPTED`). Gunakan `format_case_id_middle(..., max_len=40)` agar pemotongan tengah (`…`) hanya terjadi pada ID yang sangat panjang, dan selalu sediakan ID penuh di `Qt.ToolTipRole`.

---

## 4. Aturan 20 Larangan Desain (Anti-AI-Slop)

Setiap kontributor wajib memastikan 20 pola berikut **tidak muncul** di kode UI:

1. **Panah di tombol/teks biasa (`→`, `↗`, `›`, `»`):** Tombol hanya berisi teks kata kerja jelas. Pengecualian tunggal hanya `StripAlur` karena panah `→` menyandi urutan kejadian event.
2. **Titik kecil pemisah (`·`, `•`, `|`):** Jangan menggabung informasi dengan `·` (misal `"Min · Median · Maks"`). Gunakan baris label-nilai terpisah atau kalimat biasa dengan koma.
3. **Eyebrow di atas angka:** Kode soal (`11.7 C`) tidak diletakkan di atas angka besar; gabungkan dengan label di bawah angka dalam satu baris (`"11.7 C Berhasil"`).
4. **Latar krem/hangat (`#FAF7F2`, `#FFF8E7`):** Gunakan netral dingin `#F5F7FB` dan `#FFFFFF`. Kuning lembut `#FEF3C7` hanya untuk chip bukti event.
5. **Kata miring (*italic*) pada judul:** Tidak ada `font-style: italic` di judul, tab, atau keterangan UI.
6. **Ikon kilau/dekoratif & emoji (`✦`, `✨`, `★`, `⚡`, `📋`):** Gunakan teks polos (`"Checklist 8/10"`) atau ikon fungsional sederhana (`✓`, `✕`, `ⓘ`).
7. **Membungkus semua blok dengan kartu:** **Hanya `KartuAngka` dan `QDialog` yang berbentuk kartu.** Blok lain (`Aktivitas terbanyak`, `Durasi case`, `StripAlur`, panel `Case Explorer`) duduk langsung di canvas `#F5F7FB`, dipisah ruang kosong `24 px` dan garis `1 px` `#E2E8F0`.
8. **Kata pemasaran/buzzword:** Dilarang memakai kata `quiet`, `real`, `seamless`, `effortless`, `powerful`, `elevate`, `unlock`, `supercharge`, `magic`, `smart`, `insight` pada teks UI.
9. **Seksi bernomor & kode `F01–F07` di UI:** Nama tab polos (`Data`, `Exercise 11.7`, `Exercise 11.15 & 11.18`, `Exercise 11.22`, `Case Explorer`); daftar Checklist tanpa nomor urut `1.`–`10.`. Kode soal PDF (`11.7 A`, `11.15`, dst.) dipertahankan demi keterlacakan.
10. **Titik berdenyut / animasi status (`QTimer` untuk status):** Gunakan `BadgeStatus` statis (`✓ Valid`, `Memuat...`, `✕ Gagal`). Satu-satunya animasi adalah bar progres saat memuat file XES.
11. **Glow, blur, gradien, atau bayangan besar:** Dilarang memakai `QGraphicsBlurEffect`, `QGraphicsDropShadowEffect`, `qlineargradient`, atau `qradialgradient`.
12. **Font serif:** Dilarang memakai `Instrument Serif`, `Georgia`, atau `Times` pada judul/angka.
13. **Border kiri tebal berwarna pada kotak info:** Gunakan teks biasa atau badge penuh. (`border-left: 1px solid #E2E8F0` hanya diizinkan sebagai garis pemisah panel geser `ChecklistDrawer`).
14. **Tiga kartu ikon berjajar:** `KartuAngka` tidak memakai ikon.
15. **Pill teknologi di atas judul:** Info versi Python, PM4Py, Pandas, dan PySide6 diletakkan di dialog About (`ⓘ`).
16. **Placeholder statistik karangan:** Keadaan kosong memakai tanda `"—"` atau pesan jelas; jangan pernah mengisi angka contoh statis (`"3 case"`, `"30%"`) sebelum log dimuat.
17. **Kalimat fragmen bergaya slogan:** Pesan status ditulis sebagai kalimat utuh (`"Data dimuat dalam 0,06 detik."`), dan tombol memakai kata kerja (`"Ekspor"`, `"Ganti data"`, `"Jalankan ulang"`).
18. **Animasi fade/slide saat pindah tab atau scroll:** Perpindahan tab instan tanpa `QPropertyAnimation` / `QGraphicsOpacityEffect`.
19. **Tekstur / dithering / noise / pola piksel:** Semua isian datar satu warna.
20. **Duplikasi pesan status:** Informasi pemuatan cukup tampil satu kali di baris status tab `Data`.

---

## 5. Struktur Antarmuka (Header + 5 Tab + Drawer)

### Header (`64 px`, latar `#0B1F5C`)
* **Kiri:** Judul `BPIC17 Analyzer`, tombol `ⓘ` (membuka `AboutDialog`), dan nama berkas aktif.
* **Kanan:** Tombol `Checklist X/10` (membuka `ChecklistDrawer` Lampiran A), dropdown `Ganti data ▾` (`Impor Berkas XES...`, `Muat Dataset Utama BPIC17`, `Muat Log Sintetis`, `Jalankan Ulang Semua Analisis`), dan tombol kuning `Ekspor`.

### 5 Tab Utama
1. **`Data`** (F01 & F02)
   * Baris status (`BadgeStatus` + bar progres bertahap + pesan waktu muat).
   * 5 `KartuAngka`: `Case`, `Event`, `Aktivitas`, `Resource unik`, `Rata-rata durasi`.
   * 5 `ChipStatus` validasi atribut: `Case ID`, `concept:name`, `timestamp`, `lifecycle`, `resource`.
   * Kolom kiri: `Aktivitas terbanyak` (top 5 + tautan `Lihat semua ... aktivitas`) dan **`Distribusi lifecycle`** (`complete`, `schedule`, `start`, dll.).
   * Kolom kanan: `Durasi case` (toggle `Hari`/`Jam`/`Detik`, 5 baris label-nilai `Minimum`, `Median`, `Maksimum`, `Simpangan baku`, `Rentang waktu`, dropdown `Ketelitian`, **`HistogramDurasiWidget`** dengan garis batas merah di hari ke-45 + angka Fast/Slow, dan tautan `Daftar case dan durasi`).
2. **`Exercise 11.7`** (F03)
   * 5 `KartuAngka` sejajar (`11.7 A` s/d `11.7 E`) dengan rata-rata durasi pada kartu C, D, dan E.
   * Baris catatan irisan C & D (`"X case masuk C dan D (...)"`) dan perbedaan 11.7 E vs *contains* `O_Cancelled`.
   * Tabel daftar *case* + `StripAlur` bukti trace + tombol aksi (`Buka di Case Explorer`, `Ekspor CSV soal ini`, `Jalankan ulang`).
3. **`Exercise 11.15 & 11.18`** (F04 & F05)
   * 2 `KartuAngka` (`11.15 Fraud 2x` & `11.18 Resource sama`) berdampingan dengan **`Corong1115Widget`** (`Seluruh case` → `11.15` → `11.18`).
   * Checkbox **`Tampilkan case yang tidak lolos`** untuk membuktikan filter *complete-only* (11.15) dan *same-resource* (11.18).
   * Tabel bukti + `StripAlur` yang menampilkan **aktivitas, lifecycle, resource, dan tanggal** di setiap chip bukti.
4. **`Exercise 11.22`** (F06)
   * Angka jawaban besar, persentase, badge denominator, aturan filter *eventually follows* (`i < j`), tabel pasangan posisi, `StripAlur`, dan keterangan terpisah **Analisis tambahan (Level OfferID)**.
5. **`Case Explorer`** (F07)
   * Panel kiri (`430 px`): kotak `Cari Case ID...` (*debounce* `180 ms`), dropdown filter grup soal, tombol `Reset`, dan tabel 3 kolom (`Case ID`, `Event`, `Lolos di`).
   * Panel kanan: ringkasan *case*, tabel event (`Waktu`, `Aktivitas` dengan sub-teks `lifecycle: ...` via `ActivityLifecycleDelegate`, `Resource`, serta checkbox opsional `Offer ID, Event ID`).

---

## 6. Aturan Teknis PySide6 (Wajib Dipatuhi Kontributor)

1. **Isolasi Stylesheet Qt (Mencegah Artefak Garis/Kotak):**
   * Di Qt, `QLabel` adalah turunan `QFrame`. Selalu pertahankan reset global `QLabel { background: transparent; border: none; padding: 0px; margin: 0px; }` di `APP_STYLESHEET` dan sertakan `background: transparent; border: none;` pada setiap inline `QLabel.setStyleSheet(...)`.
   * Setiap wadah `QFrame` atau `QTabWidget` yang diberi stylesheet **wajib** memakai `#objectName` (contoh: `QFrame#KartuAngka`, `QFrame#MainHeader`, `QTabWidget#BodyStack`) agar `border` atau `background` tidak merembes ke tombol, input, atau label di dalamnya.
2. **Perataan Header & Isi Tabel:**
   * Semua header kolom dan sel di `Simple3ColTableModel` dan `QTableView` diratakan kiri (`Qt.AlignLeft | Qt.AlignVCenter`) agar header sejajar sempurna dengan datanya.
3. **Skala Data Besar (31.509+ Case / 1,2 Juta+ Event):**
   * Wajib menggunakan `QTableView` + `QAbstractTableModel` (dilarang `QTableWidget`).
   * Untuk tabel berjumlah puluhan ribu baris (`table_exp_cases`, `CaseDurationDialog`), gunakan `QHeaderView.Interactive` dengan lebar kolom tetap dan hindari `df.iterrows()` maupun `QHeaderView.ResizeToContents` agar UI tidak membeku saat rendering.
   * Wajib gunakan `QTimer` *debounce* (`180 ms`) pada kolom pencarian dan `AnalysisWorker` (`QThread`) untuk pemrosesan PM4Py.
