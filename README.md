# Aplikasi Desktop Analisis Event Log BPIC17 (Python & PM4Py)

Aplikasi desktop berbasis **Python**, **PM4Py**, dan **PySide6 (Qt)** untuk mengeksplorasi, memvalidasi, memfilter, dan menjawab soal-soal Latihan Bab 11 *Fundamentals of Business Process Management (FBPM)* (**Exercise 11.7 A–E, 11.15, 11.18, dan 11.22**) secara dinamis dari berkas event log XES **BPI Challenge 2017 (`BPI Challenge 2017.xes.gz`)** maupun log sintetis pengujian *edge cases*.

---

## 1. Fitur Utama Aplikasi (F01–F07)

Antarmuka mengadopsi tata letak **5-Tab Light Mode** sesuai [`DESIGN.md`](DESIGN.md), dilengkapi panel geser **Checklist Demo (Lampiran A)**, dropdown **Ganti data**, dan modal **Ekspor**:

1. **F01 & F02 — Tab `Data` (Impor, Validasi XES, Overview & Statistika Dasar)**
   - Memilih berkas `.xes` atau `.xes.gz` melalui menu **Ganti data** (`Impor Berkas XES...`, `Muat Dataset Utama BPIC17 (.xes.gz)`, `Muat Log Sintetis Edge Cases`, `Jalankan Ulang Semua Analisis`).
   - Mengimpor event log secara *asynchronous* menggunakan `pm4py.read_xes` di *worker thread* (`QThread`) dengan bar progres bertahap agar antarmuka tetap responsif (*non-blocking UI*).
   - Memvalidasi atribut wajib (`case:concept:name`, `concept:name`, `time:timestamp`) dan mendeteksi atribut opsional (`lifecycle:transition`, `org:resource`, `OfferID`) dengan indikator *chip* status serta banner peringatan apabila ada timestamp tidak kronologis atau atribut kosong.
   - Menampilkan 5 kartu ringkasan (`Case`, `Event`, `Aktivitas`, `Resource unik`, `Rata-rata durasi`), grafik top 5 aktivitas, distribusi *lifecycle*, statistik durasi (`Minimum`, `Median`, `Maksimum`, `Simpangan baku`, `Rentang waktu`) dengan tombol satuan `Hari` / `Jam` / `Detik` dan pengatur ketelitian global (`2 desimal` / `4 desimal`), histogram sebaran durasi berbatas 45 hari (*Fast vs Slow Cases*, *Example 11.10*), serta dialog **Daftar case dan durasi** dan **Lihat semua aktivitas**.
2. **F03 — Tab `Exercise 11.7` (A–E)**
   - Menghitung ke-5 subsoal (11.7 A, B, C, D, E) dari log aktif tanpa nilai *hard-coded*.
   - Memisahkan secara tegas aturan **Contains** (`O_Accepted` pada 11.7 C dan `O_Refused` pada 11.7 D, tanpa memaksakan eksklusivitas) dari aturan **Endpoint / Event Terakhir** (`O_Cancelled` pada 11.7 E).
   - Mempertahankan konteks trace utuh saat menghitung *cycle time* masing-masing kelompok dan menyajikan bukti trace di `StripAlur`.
3. **F04 & F05 — Tab `Exercise 11.15 & 11.18` (Pengulangan Complete & Resource Sama)**
   - **11.15**: Memilih case di mana `W_Assess potential fraud` diselesaikan (`lifecycle:transition == 'complete'`) minimal 2 kali.
   - **11.18**: Melanjutkan F04 dengan syarat $\ge 2$ kejadian `complete` pada satu case dilakukan oleh `org:resource` yang identik dan valid (nilai kosong/`NaN`/`UNKNOWN` tidak pernah dianggap sebagai satu resource yang sama).
   - Menyediakan **Corong penyaringan pengulangan dan resource** serta kotak centang **`Tampilkan case yang tidak lolos`** untuk membuktikan efek filter *complete-only* (290 case tereliminasi pada BPIC17) dan filter *same-resource* (10 case tereliminasi pada BPIC17).
4. **F06 — Tab `Exercise 11.22` (Urutan Event `O_Cancelled` $\rightarrow$ `O_Accepted`)**
   - Memilih case yang memiliki pasangan posisi $i < j$ dalam trace di mana event ke-$i$ adalah `O_Cancelled` dan event ke-$j$ adalah `O_Accepted` (*eventually follows*, tidak harus bersebelahan).
   - Menampilkan jumlah case, persentase terhadap denominator total case aktif, posisi indeks event pembukti, `StripAlur` bukti urutan, serta analisis tambahan terpisah pada level `OfferID` (Bagian 7.3).
5. **F07 — Tab `Case Explorer`, Checklist Demo, & Modal `Ekspor`**
   - **Case Explorer**: Pencarian Case ID dengan *debounce* (`180 ms`), dropdown filter per kelompok soal (dengan tampilan jumlah dan persentase terhadap total case), penyorotan baris kejadian bukti di trace lengkap, tampilan sub-teks *lifecycle*, serta opsi kolom detail `Offer ID` & `Event ID`.
   - **Checklist Demo (Lampiran A)**: Panel geser kanan yang memantau progres 10 butir demonstrasi secara otomatis maupun manual.
   - **Ekspor (CSV & HTML)**: Modal **Ekspor** di header (serta tombol `Ekspor CSV soal ini` di tiap tab soal) mengekspor data lengkap tanpa pemotongan: ringkasan ke-8 jawaban wajib (CSV), seluruh daftar case terpilih & bukti event per soal (CSV), dan laporan ringkas analitis mandiri (HTML).

---

## 2. Struktur Folder Proyek

```text
Proyek Datmin/
├── main.py                                    # Entrypoint utama aplikasi desktop PySide6
├── requirements.txt                           # Daftar dependency Python beserta versinya
├── pytest.ini                                 # Konfigurasi pengujian unit pytest
├── DESIGN.md                                  # Panduan desain & token antarmuka PySide6 (Light Mode)
├── README.md                                  # Dokumentasi instalasi, arsitektur, dan petunjuk penggunaan
├── LAPORAN_PROYEK_TAHAP_1.md                  # Laporan lengkap pemetaan soal, hasil BPIC17, bukti case, & pengujian
├── BPI Challenge 2017.xes.gz                  # Dataset utama BPIC17 (31.509 traces, 1.202.267 events)
├── DATA.xml                                   # Metadata resmi dataset BPI Challenge 2017
├── src/
│   ├── __init__.py                            # Metadata paket aplikasi
│   ├── core.py                                # Impor XES PM4Py, validasi atribut (F01), & pre-komputasi trace O(N)
│   ├── analyzer.py                            # Mesin analisis F02 (Overview) dan F03-F06 (11.7, 11.15, 11.18, 11.22)
│   ├── exporter.py                            # Modul ekspor CSV dan generator laporan HTML (F07)
│   ├── synthetic.py                           # Generator log XES sintetis untuk 8 skenario edge cases (Bagian 8)
│   └── gui.py                                 # Antarmuka pengguna desktop PySide6 (5 tab + virtual model + QThread)
├── tests/
│   ├── test_edge_cases.py                     # 9 pengujian unit pytest untuk 8 skenario edge cases (Bagian 8)
│   ├── test_f01_f02_data_processing.py        # 10 pengujian unit hardening F01 & konsistensi metrik F02
│   └── test_gui_and_perf.py                   # 4 pengujian unit & integrasi PySide6 GUI + fallback interleaved trace
├── data/
│   └── synthetic_edge_cases.xes               # File XES log sintetis (10 case, 32 event) hasil generator
├── outputs/
│   ├── bpic17/                                # Hasil ekspor lengkap CSV (01-10) dan laporan HTML (11) pada BPIC17
│   └── synthetic/                             # Hasil ekspor CSV dan laporan HTML pada log sintetis
└── screenshots/                               # Tangkapan layar antarmuka dan bukti jejak kasus
```

---

## 3. Langkah Instalasi dan Menjalankan Aplikasi

### Prasyarat Lingkungan
- **OS**: Windows / macOS / Linux
- **Python**: Python 3.10+ (diverifikasi dengan **Python 3.11.9**)

### Langkah 1 — Buat dan Aktifkan Virtual Environment (Disarankan)
Buka terminal (PowerShell / Command Prompt) pada folder proyek ini:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Langkah 2 — Instal Dependency
```powershell
pip install -r requirements.txt
```

### Langkah 3 — Jalankan Aplikasi Desktop GUI
```powershell
python main.py
```
Atau langsung memuat dataset `BPI Challenge 2017.xes.gz` saat aplikasi dibuka:
```powershell
python main.py --file "BPI Challenge 2017.xes.gz"
```
Atau langsung memuat log sintetis pengujian *edge cases*:
```powershell
python main.py --synthetic
```

### Langkah 4 — Menjalankan Unit & Integration Tests
```powershell
python -m pytest -v
```

---

## 4. Petunjuk Penggunaan Singkat (Alur Demonstrasi)

1. **Buka Aplikasi**: Jalankan `python main.py`.
2. **Muat Dataset BPIC17**: Klik tombol **Ganti data ▾** pada bilah header lalu pilih **Muat Dataset Utama BPIC17 (.xes.gz)** (atau **Impor Berkas XES...** untuk memilih file `.xes` / `.xes.gz` lain). Tunggu sekitar 8–12 detik hingga pembacaan 1,2 juta event selesai.
3. **Periksa Validasi & Overview (Tab `Data`)**:
   - Periksa status `✓ Valid`, *chip* atribut (`Case ID`, `concept:name`, `timestamp`, `lifecycle`, `resource`), distribusi aktivitas dan *lifecycle*, serta statistik durasi case dan histogram batas 45 hari.
   - Klik tautan **Daftar case dan durasi** untuk mencari dan menelusuri durasi seluruh 31.509 case secara instan.
4. **Lihat Jawaban Latihan**:
   - Tab **`Exercise 11.7`**: Klik masing-masing kartu `11.7 A` s/d `11.7 E` untuk melihat aturan filter, jumlah case, rata-rata *cycle time*, tabel daftar case lengkap, dan `StripAlur` bukti.
   - Tab **`Exercise 11.15 & 11.18`**: Lihat 13 case yang lolos 11.15 dan 3 case yang lolos 11.18 beserta **Corong penyaringan**. Centang **`Tampilkan case yang tidak lolos`** untuk membuktikan eliminasi oleh filter `complete-only` dan filter `same-resource`.
   - Tab **`Exercise 11.22`**: Lihat jawaban **Ya, 902 case (2,86%)** beserta posisi indeks `(i, j)`, `StripAlur` urutan `O_Cancelled → O_Accepted`, dan catatan analisis level `OfferID`.
5. **Telusuri Bukti Trace di `Case Explorer`**:
   - Klik tombol **Buka di Case Explorer** pada tab soal mana pun atau buka tab **`Case Explorer`** secara langsung untuk mencari Case ID dan memeriksa alur event lengkap beserta sorotan bukti kejadian.
6. **Ekspor Hasil & Pantau Checklist Demo**:
   - Klik tombol kuning **Ekspor** di pojok kanan atas untuk menyimpan ringkasan jawaban (CSV), seluruh daftar case bukti per soal (CSV), atau laporan analitis (HTML).
   - Klik **Checklist X/10** di header untuk membuka panel checklist demonstrasi Lampiran A.
