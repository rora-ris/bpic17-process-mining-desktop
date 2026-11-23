# Aplikasi Desktop Analisis Event Log BPIC17 (Python & PM4Py)

Aplikasi desktop berbasis **Python**, **PM4Py**, dan **PySide6 (Qt)** untuk mengeksplorasi, memvalidasi, memfilter, dan menjawab soal-soal Latihan Bab 11 *Fundamentals of Business Process Management (FBPM)* (**Exercise 11.7 A–E, 11.15, 11.18, dan 11.22**) secara dinamis dari berkas event log XES **BPI Challenge 2017 (`BPI Challenge 2017.xes.gz`)** maupun log sintetis pengujian *edge cases*.

---

## 1. Fitur Utama Aplikasi (F01–F07)

1. **F01 — Impor dan Validasi Event Log XES (`1. Dataset & Validasi (F01)`)**
   - Memilih berkas `.xes` atau `.xes.gz` melalui dialog file atau tombol cepat **Muat BPIC17 (.xes.gz)** / **Muat Log Sintetis (Edge Cases)**.
   - Mengimpor event log secara *asynchronous* menggunakan `pm4py.read_xes` di *worker thread* (`QThread`) dengan indikator progres sehingga antarmuka tidak pernah membeku (*non-blocking UI*).
   - Memvalidasi atribut wajib (`case:concept:name`, `concept:name`, `time:timestamp`), mendeteksi atribut opsional penting (`lifecycle:transition`, `org:resource`, `OfferID`), dan menampilkan pesan kesalahan yang jelas bila berkas rusak atau atribut wajib tidak tersedia.
2. **F02 — Event Log Overview dan Statistika Dasar (`2. Overview & Statistika (F02)`)**
   - Menampilkan total *unique case* (31.509), total *event* (1.202.267), jumlah aktivitas unik (26), jumlah *resource* (149), rentang waktu log, serta rata-rata, median, simpangan baku, minimum, dan maksimum *cycle time* dalam satuan hari, jam, dan detik.
   - Menampilkan perbandingan pengayaan **Fast Cases (< 45 hari)** dan **Slow Cases ($\ge$ 45 hari)** sesuai *Example 11.10*.
   - Menyediakan tabel frekuensi aktivitas (level event, level `complete`, dan level case) serta tabel durasi per case dengan fitur pencarian/filter.
3. **F03 — Analisis Exercise 11.7 A–E (`3. Exercise 11.7 A–E (F03)`)**
   - Menghitung ke-5 subsoal (11.7 A, B, C, D, E) dari log aktif tanpa nilai *hard-coded*.
   - Memisahkan secara tegas aturan **Contains** (`O_Accepted` pada 11.7 C dan `O_Refused` pada 11.7 D) dari aturan **Endpoint / Event Terakhir** (`O_Cancelled` pada 11.7 E).
   - Mempertahankan konteks trace utuh saat menghitung *cycle time* masing-masing kelompok.
4. **F04 — Analisis Pengulangan Aktivitas / Exercise 11.15 (`4. Exercise 11.15 & 11.18 (F04–F05)`)**
   - Memilih case di mana `W_Assess potential fraud` diselesaikan (`lifecycle:transition == 'complete'`) minimal 2 kali.
   - Menyertakan bukti perbandingan dengan seluruh *lifecycle* (`schedule`, `start`, `suspend`, `resume`, `ate_abort`, `withdraw`) serta tombol untuk menampilkan contoh case yang tereliminasi oleh filter *complete-only*.
5. **F05 — Analisis Pengulangan oleh Resource Sama / Exercise 11.18 (`4. Exercise 11.15 & 11.18 (F04–F05)`)**
   - Melanjutkan F04 dengan syarat $\ge 2$ kejadian `complete` pada satu case dilakukan oleh `org:resource` yang identik dan valid.
   - Menangani nilai *resource* kosong/`NaN`/`UNKNOWN` secara eksplisit (tidak pernah dianggap sebagai satu *resource* yang sama).
6. **F06 — Analisis Urutan Event / Exercise 11.22 (`5. Exercise 11.22 (F06)`)**
   - Memilih case yang memiliki pasangan posisi $i < j$ dalam trace di mana event ke-$i$ adalah `O_Cancelled` dan event ke-$j$ adalah `O_Accepted` (*eventually follows*, tidak harus bersebelahan).
   - Menampilkan jumlah case, denominator total case aktif, persentase, jumlah event perantara, serta analisis tambahan terpisah pada level `OfferID` (Bagian 7.3).
7. **F07 — Case Explorer, Jejak Analisis, dan Ekspor (`6. Case Explorer & Bukti (F07)` & `7. Ringkasan & Ekspor (F07)`)**
   - **Case Explorer**: Memungkinkan pencarian dan pemeriksaan jejak trace lengkap (`_trace_pos`, `time:timestamp`, `concept:name`, `lifecycle:transition`, `org:resource`, `OfferID`, `EventID`) dengan penyorotan warna kuning otomatis pada event bukti.
   - **Ekspor CSV & HTML**: Mengekspor tabel ringkasan ke-8 jawaban wajib, seluruh daftar case terpilih (11.7 C/D/E, 11.15, 11.18, 11.22), bukti event, serta laporan ringkas HTML mandiri.

---

## 2. Struktur Folder Proyek

```text
Proyek Datmin/
├── main.py                                    # Entrypoint utama aplikasi desktop PySide6
├── requirements.txt                           # Daftar dependency Python beserta versinya
├── pytest.ini                                 # Konfigurasi pengujian unit pytest
├── README.md                                  # Dokumentasi instalasi, arsitektur, dan petunjuk penggunaan
├── LAPORAN_PROYEK_TAHAP_1.md                  # Laporan lengkap pemetaan soal, hasil BPIC17, bukti case, & pengujian
├── BPI Challenge 2017.xes.gz                  # Dataset utama BPIC17 (31.509 traces, 1.202.267 events)
├── DATA.xml                                   # Metadata resmi dataset BPI Challenge 2017
├── src/
│   ├── __init__.py                            # Metadata paket aplikasi
│   ├── core.py                                # Impor XES PM4Py, validasi atribut (F01), & pre-komputasi trace
│   ├── analyzer.py                            # Mesin analisis F02 (Overview) dan F03-F06 (11.7, 11.15, 11.18, 11.22)
│   ├── exporter.py                            # Modul ekspor CSV dan generator laporan HTML (F07)
│   ├── synthetic.py                           # Generator log XES sintetis untuk 8 skenario edge cases (Bagian 8)
│   └── gui.py                                 # Antarmuka pengguna desktop PySide6 (7 tab utama + worker thread)
├── tests/
│   └── test_edge_cases.py                     # 9 pengujian unit pytest yang memverifikasi seluruh edge cases
├── data/
│   └── synthetic_edge_cases.xes               # File XES log sintetis (10 case, 32 event) hasil generator
├── outputs/
│   ├── bpic17/                                # Hasil ekspor lengkap CSV (01-10) dan laporan HTML (11) pada BPIC17
│   └── synthetic/                             # Hasil ekspor CSV dan laporan HTML pada log sintetis
└── screenshots/                               # Tangkapan layar setiap menu utama dan bukti jejak kasus (01-10)
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

### Langkah 4 — Menjalankan Unit Tests (Skenario Edge Cases Bagian 8)
```powershell
python -m pytest -v
```

---

## 4. Petunjuk Penggunaan Singkat (Alur Demonstrasi)

1. **Buka Aplikasi**: Jalankan `python main.py`.
2. **Muat Dataset BPIC17**: Klik tombol hijau **Muat BPIC17 (.xes.gz)** pada bilah atas (atau klik **Impor XES...** untuk memilih file `.xes` / `.xes.gz` secara manual). Tunggu sekitar 8–12 detik hingga pembacaan 1,2 juta event selesai.
3. **Periksa Validasi & Overview**:
   - Buka tab **1. Dataset & Validasi (F01)** untuk melihat status validasi atribut XES (`case:concept:name`, `concept:name`, `time:timestamp`, `lifecycle:transition`, `org:resource`, `OfferID`).
   - Buka tab **2. Overview & Statistika (F02)** untuk melihat frekuensi 26 aktivitas dan tabel durasi 31.509 case.
4. **Lihat Jawaban Latihan**:
   - Tab **3. Exercise 11.7 A–E (F03)**: Menampilkan ke-5 kartu jawaban 11.7 A–E beserta daftar case yang lolos masing-masing filter.
   - Tab **4. Exercise 11.15 & 11.18 (F04–F05)**: Menampilkan 13 case yang lolos 11.15 dan 3 case yang lolos 11.18 beserta tabel bukti event di bagian bawah. Klik tombol **Tampilkan Contoh Case Tereliminasi Filter Complete-Only** untuk membuktikan peran filter `lifecycle:transition == 'complete'`.
   - Tab **5. Exercise 11.22 (F06)**: Menampilkan 902 case (2,86%) yang memiliki urutan `O_Cancelled` diikuti `O_Accepted` beserta posisi indeks event dalam trace dan `OfferID`-nya.
5. **Telusuri Bukti Trace di Case Explorer**:
   - Klik ganda (*double-click*) pada baris case mana pun atau buka tab **6. Case Explorer & Bukti (F07)** untuk melihat urutan seluruh event pada case tersebut. Baris kejadian yang menjadi bukti kelolosan filter akan otomatis disorot dengan warna kuning.
6. **Ekspor Hasil**:
   - Buka tab **7. Ringkasan & Ekspor (F07)** lalu klik **Ekspor Semua Hasil Analisis ke Folder (CSV + Laporan HTML)...** untuk menyimpan seluruh tabel ringkasan dan daftar case bukti.
