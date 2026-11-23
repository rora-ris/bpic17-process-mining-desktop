# Laporan Proyek Tahap 1 — Aplikasi Desktop untuk Analisis Event Log BPIC17
**Menjawab Latihan Bab 11 FBPM Menggunakan Python, PM4Py, dan PySide6**

---

## 1. Informasi Dataset dan Lingkungan Reproduktibilitas

### 1.1 Sumber dan Versi Dataset
- **Nama Dataset**: BPI Challenge 2017 (`BPI Challenge 2017.xes.gz`)
- **DOI Resmi (4TU.ResearchData)**: `doi:10.4121/uuid:5f3067df-f10b-45da-b98b-86ae4c7a310b`
- **Institusi & Pembuat**: Eindhoven University of Technology (B.F. van Dongen, 2 Februari 2017)
- **Ukuran Berkas Terkompresi**: 28,28 MB (`29.658.747` byte)
- **Jumlah Unique Case / Trace**: **31.509** aplikasi pinjaman (`Application_...`)
- **Jumlah Total Event**: **1.202.267** kejadian (rata-rata 38,16 event/trace, minimum 10, maksimum 180)
- **Rentang Waktu Log**: `2016-01-01 09:51:15.304+00:00` s/d `2017-02-01 14:11:03.499+00:00` (`2016-01-01T10:51:15.304+01:00` s/d `2017-02-01T15:11:03.499+01:00` CET)

### 1.2 Versi Lingkungan Eksekusi (Bagian 7.1)
- **Python**: `3.11.9` (64-bit Windows)
- **PM4Py**: `2.7.23.14`
- **Pandas**: `3.1.1`
- **PySide6 (Qt Desktop GUI)**: `6.12.0`
- **r4pm / rustxes (Akselerator Parser XES PM4Py)**: `0.7.1` / `0.2.11` (mempercepat pembacaan 1,2 juta event dari ~87 detik menjadi ~8–11 detik)
- **Pytest**: `9.2.0`

---

## 2. Pemetaan Soal $\rightarrow$ Fitur & Fungsi Aplikasi

| Kode Fitur / Soal | Deskripsi Kebutuhan | Modul & Fungsi Python | Tab / Panel Antarmuka GUI |
| :--- | :--- | :--- | :--- |
| **F01** | Impor file `.xes` / `.xes.gz` dengan PM4Py dan validasi atribut wajib (`case:concept:name`, `concept:name`, `time:timestamp`, `lifecycle:transition`, `org:resource`) | `src/core.py` $\rightarrow$ `load_and_validate_xes()`, `EventLogContext` | Tab 1: **1. Dataset & Validasi (F01)** |
| **F02** | Overview event log, frekuensi aktivitas, durasi tiap case, serta perbandingan *Fast (< 45 hari)* vs *Slow ($\ge$ 45 hari)* | `src/analyzer.py` $\rightarrow$ `analyze_overview()` | Tab 2: **2. Overview & Statistika (F02)** |
| **F03 (11.7 A–E)** | Jumlah keseluruhan case (A), rata-rata cycle time (B), *successful cases* `Contains('O_Accepted')` (C), *unsuccessful cases* `Contains('O_Refused')` (D), dan *canceled cases* `EndsWith('O_Cancelled')` (E) | `src/analyzer.py` $\rightarrow$ `analyze_exercise_11_7()` (`pm4py.filter_trace_attribute_values` & `pm4py.filter_end_activities`) | Tab 3: **3. Exercise 11.7 A–E (F03)** |
| **F04 (11.15)** | Jumlah & daftar case di mana `W_Assess potential fraud` selesai (`lifecycle:transition == 'complete'`) minimal 2 kali | `src/analyzer.py` $\rightarrow$ `analyze_exercise_11_15()` | Tab 4: **4. Exercise 11.15 & 11.18 (F04–F05)** (Panel Kiri & Panel Bukti Bawah) |
| **F05 (11.18)** | Jumlah & daftar case di mana `W_Assess potential fraud` selesai (`complete`) minimal 2 kali oleh `org:resource` yang sama dan valid | `src/analyzer.py` $\rightarrow$ `analyze_exercise_11_18()`, `is_valid_resource()` | Tab 4: **4. Exercise 11.15 & 11.18 (F04–F05)** (Panel Kanan & Panel Bukti Bawah) |
| **F06 (11.22)** | Analisis urutan event (*eventually follows*): case dengan `O_Cancelled` pada posisi $i$ diikuti `O_Accepted` pada posisi $j$ ($i < j$) beserta persentasenya | `src/analyzer.py` $\rightarrow$ `analyze_exercise_11_22()` | Tab 5: **5. Exercise 11.22 (F06)** |
| **F07** | Case Explorer (pencarian ID, trace lengkap dengan penyorotan bukti), re-run/reset filter, serta ekspor CSV & HTML | `src/gui.py` & `src/exporter.py` $\rightarrow$ `export_all_to_directory()`, `generate_html_report()` | Tab 6: **6. Case Explorer & Bukti (F07)** & Tab 7: **7. Ringkasan & Ekspor (F07)** |

---

## 3. Definisi Operasional Filter & Aturan Analisis (Bagian 4 & 7)

1. **Urutan Event dalam Trace (`_trace_pos`)**:
   - Setiap event di dalam satu case mempertahankan nomor urut kemunculan aktualnya di dalam elemen `<trace>` XES (`_trace_pos = 1, 2, ..., N`).
   - Pada BPIC17, seluruh trace sudah terurut secara monotonik non-turun terhadap `time:timestamp` (`first_timestamp == min_timestamp` dan `last_timestamp == max_timestamp` pada 100% dari 31.509 case). Apabila terdapat dua event dalam satu case yang memiliki *timestamp* identik hingga milidetik yang sama, `_trace_pos` menjamin urutan kejadian tetap deterministik sesuai representasi XES asli.
2. **Perhitungan Cycle Time Case**:
   - Dihitung pada level trace utuh sebelum pemfilteran event apa pun:
     $$\text{Cycle Time}(\text{case}) = \frac{t_{\text{last}} - t_{\text{first}}}{86.400 \text{ detik/hari}}$$
   - Aplikasi tidak pernah menghapus event dari trace sebelum menghitung durasi case, sehingga pemilihan subset case pada 11.7 C, D, dan E tetap menggunakan durasi penuh dari awal hingga akhir trace masing-masing case.
3. **Perbedaan Aturan `Contains` vs `Endpoint` (Exercise 11.7 C, D, E)**:
   - **Contains (`11.7 C` & `11.7 D`)**: Suatu case dipilih tepat satu kali apabila memuat $\ge 1$ event dengan `concept:name == 'O_Accepted'` (11.7 C) atau `concept:name == 'O_Refused'` (11.7 D). Kedua kelompok ini tidak dipaksa saling eksklusif oleh kode filter.
   - **Endpoint (`11.7 E`)**: Suatu case dipilih hanya apabila **event paling akhir** (`_trace_pos == N`) pada urutan trace adalah `O_Cancelled`.
4. **Identifikasi `Complete Occurrence` & Penanganan Nama Aktivitas (Exercise 11.15)**:
   - Di dalam dokumen soal tertulis `W_Assess Potential Fraud` (dengan huruf kapital `P` dan `F`), sedangkan di dalam atribut `concept:name` file XES BPIC17 tertulis `W_Assess potential fraud` (huruf kecil `p` dan `f`). Aplikasi mencocokkan nama aktivitas secara *case-insensitive* (`str.strip().str.lower() == 'w_assess potential fraud'`) sehingga akurat terhadap kedua penulisan.
   - File XES BPIC17 memiliki 7 nilai `lifecycle:transition`: `complete` (475.306), `suspend` (215.402), `schedule` (149.104), `start` (128.227), `resume` (127.160), `ate_abort` (85.224), dan `withdraw` (21.844).
   - Untuk `W_Assess potential fraud` (total 3.282 event), rincian *lifecycle*-nya adalah: `suspend` (1.277), `resume` (996), `start` (355), `schedule` (327), **`complete` (282)**, `ate_abort` (42), dan `withdraw` (3).
   - Hanya kejadian dengan `lifecycle:transition == 'complete'` (282 event yang tersebar di 268 case) yang dihitung sebagai *complete occurrence*.
5. **Aturan `Same Resource` & Penanganan Resource Kosong (Exercise 11.18)**:
   - Sebelum mengelompokkan berdasarkan `(case:concept:name, org:resource)`, aplikasi menyaring keluar nilai `org:resource` yang kosong (`""`), `NaN`/`None`, atau *placeholder* (`UNKNOWN`, `null`, `-`) melalui fungsi `is_valid_resource()`.
   - Suatu case lolos 11.18 hanya jika terdapat minimal satu `org:resource` valid $r$ yang menyelesaikan (`complete`) aktivitas `W_Assess potential fraud` sebanyak $\ge 2$ kali di dalam case tersebut.
6. **Aturan `Eventually Follows` & Level Trace vs Level OfferID (Exercise 11.22)**:
   - Suatu case lolos 11.22 apabila terdapat pasangan indeks event $i < j$ di dalam trace tersebut sehingga event ke-$i$ adalah `O_Cancelled` dan event ke-$j$ adalah `O_Accepted` (ekuivalen dengan $\min(\text{pos}(\text{O\_Cancelled})) < \max(\text{pos}(\text{O\_Accepted}))$).
   - Kedua event tidak dibatasi harus bersebelahan. Persentase dihitung terhadap seluruh case pada log aktif (`31.509` case).

---

## 4. Hasil Analisis Lengkap pada Dataset BPIC17 & Perbandingan dengan Materi

### 4.1 Tabel Ringkasan Kedelapan Butir Jawaban Wajib (BPIC17)

| Kode Soal | Pertanyaan Wajib | Aturan / Filter | Jumlah Case Terpilih | Denominator | Persentase Case | Rata-rata Cycle Time (Hari) | Rata-rata Cycle Time (Jam) | Median Cycle Time (Hari) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **11.7 A** | Berapa jumlah keseluruhan case? | Unique `case:concept:name` pada log aktif | **31.509** | 31.509 | **100,00%** | 21,90 hari (`21,8996`) | 525,59 jam | 19,09 hari |
| **11.7 B** | Berapa rata-rata cycle time seluruh case? | Selisih timestamp event terakhir $-$ event pertama tiap trace | **31.509** | 31.509 | **100,00%** | **21,90 hari** (`21,8996`) | **525,59 jam** | 19,09 hari |
| **11.7 C** | Berapa *successful cases* dan rata-rata cycle time-nya? | `Contains('O_Accepted')` ($\ge 1$ event `O_Accepted` dalam trace) | **17.228** | 31.509 | **54,68%** (`54,6764%`) | **18,13 hari** (`18,1343`) | 435,22 jam | 15,07 hari |
| **11.7 D** | Berapa *unsuccessful cases* dan rata-rata cycle time-nya? | `Contains('O_Refused')` ($\ge 1$ event `O_Refused` dalam trace) | **3.720** | 31.509 | **11,81%** (`11,8062%`) | **16,88 hari** (`16,8775`) | 405,06 jam | 13,20 hari |
| **11.7 E** | Berapa *canceled cases* dan rata-rata cycle time-nya? | `Endpoint == 'O_Cancelled'` (Event **TERAKHIR** trace adalah `O_Cancelled`) | **4.436** | 31.509 | **14,08%** (`14,0785%`) | **23,51 hari** (`23,5104`) | 564,25 jam | 29,43 hari |
| **11.15** | Berapa case dengan `W_Assess Potential Fraud` selesai minimal $2\times$? | `concept:name == 'W_Assess potential fraud'` DAN `lifecycle:transition == 'complete'` $\ge 2\times$ | **13** | 31.509 | **0,0413%** | 26,64 hari (`26,6371`) | 639,29 jam | 18,91 hari |
| **11.18** | Berapa case dengan aktivitas tersebut selesai minimal $2\times$ oleh resource yang sama? | Lanjutan 11.15 + dilakukan oleh `org:resource` valid yang identik $\ge 2\times$ dalam satu case | **3** | 31.509 | **0,0095%** | 24,52 hari (`24,5221`) | 588,53 jam | 23,58 hari |
| **11.22** | Adakah `O_Cancelled` yang kemudian diikuti `O_Accepted`? Berapa persentase case-nya? | `EventuallyFollows('O_Cancelled', 'O_Accepted')` ($\exists i < j$ dalam trace) | **Ya, ada 902 case** | 31.509 | **2,86%** (`2,8627%`) | 25,21 hari (`25,2053`) | 604,93 jam | 21,96 hari |

> **Catatan Pengayaan (Bagian 12 — Example 11.10 Fast vs Slow Cases)**:
> - **Fast Cases (< 45 hari)**: **29.932 case** (**94,99%**), rata-rata cycle time = **19,93 hari** (`19,9302` hari).
> - **Slow Cases ($\ge$ 45 hari)**: **1.577 case** (**5,01%**), rata-rata cycle time = **59,28 hari** (`59,2813` hari).

### 4.2 Analisis Perbandingan dengan Materi Latihan & Penjelasan Selisih Interpretasi Filter (Kriteria Penerimaan #5)

1. **Perbandingan Exercise 11.7 E (`Endpoint == O_Cancelled` vs `Contains O_Cancelled`)**:
   - Sesuai definisi operasional Bagian 3 & 4, `11.7 E` menggunakan filter **Endpoint** (event paling akhir pada trace adalah `O_Cancelled`), yang menghasilkan **4.436 case (14,08%)** dengan rata-rata cycle time **23,51 hari**.
   - Apabila seseorang menggunakan filter `Contains('O_Cancelled')` (memuat `O_Cancelled` di posisi mana pun), jumlahnya adalah **15.682 case (49,77%)** dengan rata-rata cycle time **27,52 hari**.
   - **Mengapa terdapat selisih 11.246 case?** Pada BPIC17, ketika sebuah penawaran dibatalkan (`O_Cancelled`), workflow aplikasi sering kali belum langsung berhenti pada event tersebut, melainkan masih mencatat event penutupan/telepon seperti `W_Call after offers` (terjadi sebagai event terakhir pada 9.323 case yang memuat `O_Cancelled`), `W_Call incomplete files` (1.125 case), atau `W_Validate application` (666 case). Selain itu, ada case yang membatalkan penawaran pertama lalu menerbitkan penawaran kedua yang diterima (`O_Accepted`, seperti pada Exercise 11.22).
   - **Proporsi Kategori 11.7 C, D, dan E**: Pada BPIC17, irisan antara `Contains('O_Accepted')` (17.228 case) dan `Contains('O_Refused')` (3.720 case) adalah **0 case** (tidak ada aplikasi di BPIC17 yang sekaligus memiliki `O_Accepted` dan `O_Refused`). Namun aplikasi kami tetap menerapkan kedua filter `Contains` secara independen tanpa memaksakan eksklusivitas, sebagaimana dibuktikan pada pengujian unit Skenario 3.
2. **Perbandingan Exercise 11.15 (`Complete-Only` vs `Semua Lifecycle Transition`)**:
   - Apabila filter `lifecycle:transition == 'complete'` diterapkan sesuai definisi soal, terdapat tepat **13 case** (12 case dengan 2$\times$ `complete`, dan 1 case dengan 3$\times$ `complete`).
   - Apabila seseorang tidak memfilter `lifecycle:transition` (menghitung semua event `W_Assess potential fraud` termasuk `schedule`, `start`, `suspend`, `resume`, `ate_abort`, `withdraw`), maka akan muncul **303 case** (selisih **290 case**!). Hal ini terjadi karena setiap satu pengerjaan pemeriksaan potensi fraud di BPIC17 biasanya menghasilkan banyak event transisi (`schedule` $\rightarrow$ `start` $\rightarrow$ `suspend` $\rightarrow$ `resume` $\rightarrow$ `complete`).
3. **Perbandingan Exercise 11.22 (Level Trace/Case vs Level `OfferID` — Bagian 7.3)**:
   - Pada level **Trace / Case** (sesuai pertanyaan soal latihan), terdapat **902 dari 31.509 case (2,8627%)** di mana suatu event `O_Cancelled` diikuti oleh event `O_Accepted` pada posisi lebih akhir. (Sebagai kontras, terdapat 5.050 case yang memuat kedua event tersebut dalam urutan apa pun, tetapi **4.148 case** di antaranya hanya memiliki urutan terbalik `O_Accepted` $\rightarrow$ `O_Cancelled` tanpa `O_Accepted` lagi sesudahnya — misalnya nasabah menyetujui penawaran awal lalu penawaran alternatif/pengajuan dibatalkan).
   - Pada analisis tambahan level **`OfferID`** (Bagian 7.3), terdapat **0 case** di mana `O_Cancelled` dan `O_Accepted` terjadi pada `OfferID` yang sama persis. Ini membuktikan fakta bisnis yang sangat penting pada BPIC17: di sistem bank tersebut, satu objek penawaran (`OfferID`) yang sudah berstatus `O_Cancelled` tidak dapat diubah lagi menjadi `O_Accepted`; ke-902 case pada Exercise 11.22 terjadi karena **penawaran pertama (`OfferID` ke-1) dibatalkan (`O_Cancelled`), kemudian bank membuat penawaran baru (`OfferID` ke-2) dalam aplikasi/case yang sama yang selanjutnya disetujui (`O_Accepted`) oleh nasabah**.

---

## 5. Bukti Case (Case Evidence) dari Dataset BPIC17

### 5.1 Bukti Exercise 11.15 — Seluruh 13 Case dengan `W_Assess potential fraud` Complete $\ge 2\times$

| No | Case ID | Jumlah `complete` | Total Event Semua Lifecycle (`Fraud`) | Resource yang Menyelesaikan (`complete`) | Jumlah Resource Unik | Waktu `complete` Pertama | Waktu `complete` Terakhir | Cycle Time Case (Hari) |
| :-: | :--- | :-: | :-: | :--- | :-: | :--- | :--- | :-: |
| 1 | `Application_612471425` | **2** | 19 | `User_99, User_144` | 2 | `2016-03-07 15:19:56.219+00:00` | `2016-03-09 08:37:17.801+00:00` | 9,8590 |
| 2 | `Application_900460993` | **2** | 22 | `User_144, User_138` | 2 | `2016-03-22 08:45:48.669+00:00` | `2016-03-22 09:32:01.256+00:00` | 30,5201 |
| 3 | `Application_534041276` | **2** | 8 | `User_75, User_138` | 2 | `2016-05-12 12:55:29.912+00:00` | `2016-05-13 07:07:52.977+00:00` | 0,8350 |
| 4 | `Application_412627378` | **2** | 9 | `User_83, User_144` | 2 | `2016-05-19 10:43:23.843+00:00` | `2016-05-19 12:42:00.234+00:00` | 18,9067 |
| 5 | `Application_1221917431` | **2** | 14 | `User_144, User_144` | **1** | `2016-07-05 11:36:11.613+00:00` | `2016-07-06 09:35:58.622+00:00` | 49,3007 |
| 6 | `Application_1021748617` | **2** | 10 | `User_99, User_138` | 2 | `2016-06-20 13:31:57.643+00:00` | `2016-06-21 08:54:00.134+00:00` | 1,0043 |
| 7 | `Application_1292983087` | **3** | 15 | `User_144, User_143, User_134` | 3 | `2016-08-11 08:05:51.911+00:00` | `2016-10-07 07:04:40.985+00:00` | 127,9320 |
| 8 | `Application_473455481` | **2** | 15 | `User_143, User_143` | **1** | `2016-08-18 11:19:40.665+00:00` | `2016-08-25 12:46:40.822+00:00` | 23,5794 |
| 9 | `Application_438711887` | **2** | 15 | `User_68, User_143` | 2 | `2016-10-18 15:45:28.901+00:00` | `2016-10-20 06:50:21.052+00:00` | 36,9285 |
| 10 | `Application_1405826636` | **2** | 16 | `User_143, User_143` | **1** | `2016-11-21 15:10:02.078+00:00` | `2016-11-22 10:15:11.617+00:00` | 0,6864 |
| 11 | `Application_287618269` | **2** | 16 | `User_143, User_68` | 2 | `2016-12-01 10:12:01.423+00:00` | `2016-12-12 14:29:46.122+00:00` | 11,4888 |
| 12 | `Application_1114361455` | **2** | 18 | `User_143, User_134` | 2 | `2016-12-02 09:15:56.833+00:00` | `2016-12-15 07:58:01.236+00:00` | 30,2787 |
| 13 | `Application_1568546217` | **2** | 15 | `User_134, User_99` | 2 | `2017-01-10 11:24:20.770+00:00` | `2017-01-12 09:43:29.735+00:00` | 4,9631 |

#### Contoh Pembuktian Filter `Complete-Only` (Bagian 7.2): Case `Application_1003257895`
Case `Application_1003257895` memiliki **14 event** `W_Assess potential fraud`, yaitu:
- `2016-06-15 06:26:21.686` (`schedule`, `User_83`), `06:26:21.690` (`start`, `User_83`), `06:26:39.252` (`suspend`, `User_83`)
- `2016-06-15 09:31:55.673` (`resume`, `User_144`), `09:31:55.684` (`suspend`, `User_144`), `09:31:55.688` (`resume`, `User_144`), `09:38:47.633` (`suspend`, `User_144`), `11:00:23.192` (`ate_abort`, `User_144`)
- `2016-06-16 02:06:26.399` (`schedule`, `User_1`), `02:06:26.509` (`start`, `User_1`), `02:06:26.526` (`suspend`, `User_1`), `02:06:26.560` (`resume`, `User_1`)
- `2016-06-17 12:31:34.937` (`suspend`, `User_138`), dan **`2016-06-17 12:32:11.386` (`complete`, `User_138`)**.

Karena hanya **1 event** yang berstatus `complete`, aplikasi dengan benar **tidak meloloskan** `Application_1003257895` pada Exercise 11.15.

---

### 5.2 Bukti Exercise 11.18 — Seluruh 3 Case dengan `W_Assess potential fraud` Complete $\ge 2\times$ oleh Resource Sama

Dari 13 case yang lolos Exercise 11.15, tepat **3 case** memiliki $\ge 2$ penyelesaian (`complete`) oleh `org:resource` yang identik (sedangkan 10 case lainnya diselesaikan oleh 2 atau 3 petugas berbeda, termasuk `Application_1292983087` yang walaupun memiliki 3$\times$ `complete`, ketiganya dilakukan oleh petugas berbeda: `User_144`, `User_143`, dan `User_134`):

| No | Case ID | Resource ID Identik | Jumlah `complete` oleh Resource Tersebut | Waktu `complete` Pertama | Waktu `complete` Kedua | Bukti `EventID` |
| :-: | :--- | :---: | :-: | :--- | :--- | :--- |
| 1 | `Application_1221917431` | **`User_144`** | **2** (`_trace_pos` 60 & 74) | `2016-07-05 11:36:11.613+00:00` | `2016-07-06 09:35:58.622+00:00` | `Workitem_735584915`, `Workitem_1308810967` |
| 2 | `Application_473455481` | **`User_143`** | **2** (`_trace_pos` 11 & 23) | `2016-08-18 11:19:40.665+00:00` | `2016-08-25 12:46:40.822+00:00` | `Workitem_518835990`, `Workitem_1085966826` |
| 3 | `Application_1405826636` | **`User_143`** | **2** (`_trace_pos` 11 & 21) | `2016-11-21 15:10:02.078+00:00` | `2016-11-22 10:15:11.617+00:00` | `Workitem_1623082800`, `Workitem_791844835` |

---

### 5.3 Bukti Exercise 11.22 — Contoh Case dengan `O_Cancelled` Diikuti `O_Accepted` (902 Case / 2,86%)

Lima contoh case pertama dari 902 case yang lolos Exercise 11.22 (daftar lengkap 902 case tersimpan di [`outputs/bpic17/10_cases_11_22_cancelled_followed_by_accepted.csv`](outputs/bpic17/10_cases_11_22_cancelled_followed_by_accepted.csv)):

| Case ID | Posisi Trace `O_Cancelled` ($i$) | Timestamp `O_Cancelled` | OfferID yang Dibatalkan | Posisi Trace `O_Accepted` ($j$) | Timestamp `O_Accepted` | OfferID yang Diterima | Jumlah Event Perantara ($j - i - 1$) | Selisih Waktu (Hari) |
| :--- | :-: | :--- | :--- | :-: | :--- | :--- | :-: | :-: |
| `Application_1000671285` | **13** | `2016-04-14 07:51:04.196+00:00` | `Offer_620142850` | **42** | `2016-04-22 06:06:16.582+00:00` | `Offer_888834469` | 28 event | 7,9272 |
| `Application_1004303396` | **29** | `2016-09-15 11:39:52.275+00:00` | `Offer_1290484385` | **75** | `2016-10-04 09:50:49.007+00:00` | `Offer_1451841225` | 45 event | 18,9243 |
| `Application_1006433086` | **22** | `2016-03-17 09:10:49.944+00:00` | `Offer_1569364095` | **36** | `2016-03-23 09:49:18.393+00:00` | `Offer_978487414` | 13 event | 6,0267 |
| `Application_1008568270` | **21** | `2016-10-20 07:45:17.283+00:00` | `Offer_1662926912` | **38** | `2016-10-24 14:43:29.520+00:00` | `Offer_1223251226` | 16 event | 4,2904 |
| `Application_1012642852` | **19** | `2016-08-05 13:02:13.917+00:00` | `Offer_35327260` | **47** | `2016-08-18 11:39:11.674+00:00` | `Offer_1861910153` | 27 event | 12,9423 |

---

## 6. Pengujian Unit & Verifikasi Skenario Kasus Tepi (Bagian 8)

Pengujian unit diimplementasikan di [`tests/test_edge_cases.py`](tests/test_edge_cases.py) menggunakan log XES sintetis [`data/synthetic_edge_cases.xes`](data/synthetic_edge_cases.xes) (dibangkitkan oleh [`src/synthetic.py`](src/synthetic.py)). Seluruh **9 fungsi uji pytest LULUS 100% (`9 passed`)**:

| No | Skenario Uji Wajib (Bagian 8) | Case Sintetis Penguji | Hasil yang Semestinya | Hasil Aktual Pengujian (`pytest`) | Status |
| :-: | :--- | :--- | :--- | :--- | :-: |
| 1 | Satu case memiliki `O_Accepted` dua kali | `CASE_01_DOUBLE_ACCEPTED` | 11.7 C menghitung case satu kali, bukan dua; durasi dihitung dari trace utuh (10,0 hari) | Dihitung tepat 1 kali pada 11.7 C dengan durasi 10,0 hari | **PASS** |
| 2 | Case memiliki `O_Cancelled` di tengah dan event lain sesudahnya | `CASE_02_CANCELLED_MIDDLE_THEN_OTHER` | 11.7 E tidak menganggapnya canceled hanya karena pernah muncul `O_Cancelled` | Tidak masuk hasil 11.7 E (`last_activity == 'W_Call after offers'`) | **PASS** |
| 3 | Case memiliki `O_Refused` dan `O_Accepted` | `CASE_03_BOTH_REFUSED_AND_ACCEPTED` | Case dapat lolos kedua filter contains (11.7 C & 11.7 D); tidak dipaksa eksklusif | Masuk di 11.7 C sekaligus 11.7 D (`overlap_c_and_d_count == 1`) | **PASS** |
| 4 | `W_Assess Potential Fraud` dijadwalkan dua kali tetapi `complete` hanya sekali | `CASE_04_FRAUD_SCHEDULED_TWICE_COMPLETE_ONCE` | 11.15 tidak meloloskan case tersebut | Tidak masuk hasil 11.15; terdeteksi sebagai case yang tereliminasi filter lifecycle | **PASS** |
| 5 | Dua `complete`, tetapi resource berbeda | `CASE_05_FRAUD_TWO_COMPLETE_DIFF_RESOURCE` | Lolos 11.15, tidak lolos 11.18 | Masuk hasil 11.15 (`User_A`, `User_B`), tidak masuk hasil 11.18 | **PASS** |
| 6 | Dua `complete` oleh resource sama (& penanganan resource kosong) | `CASE_06_FRAUD_TWO_COMPLETE_SAME_RESOURCE` & `CASE_07_..._EMPTY_RESOURCE` | `CASE_06` (`User_X` 2$\times$) lolos 11.15 & 11.18; `CASE_07` (`""` 2$\times$) lolos 11.15 tapi ditolak 11.18 | `CASE_06` lolos 11.15 & 11.18; `CASE_07` ditolak 11.18 karena resource kosong | **PASS** |
| 7 | `O_Cancelled` diikuti aktivitas lain lalu `O_Accepted` | `CASE_08_CANCELLED_THEN_OTHER_THEN_ACCEPTED` | Lolos 11.22 meskipun kedua event tidak bertetangga | Masuk hasil 11.22 (`pos(O_Cancelled)=2 < pos(O_Accepted)=4`, 1 event perantara) | **PASS** |
| 8 | `O_Accepted` mendahului `O_Cancelled` tanpa accepted sesudahnya | `CASE_09_ACCEPTED_BEFORE_CANCELLED_NO_ACCEPTED_AFTER` | Tidak lolos 11.22 | Ditolak oleh 11.22; tercatat di metrik `reverse_only_count` | **PASS** |
| 9 | Penanganan file XES hilang atau rusak (F01) | `test_invalid_or_missing_file_handling` | Aplikasi menolak file dengan pesan kesalahan jelas tanpa crash | `report.is_valid == False` disertai pesan `error_message` informatif | **PASS** |

---

## 7. Dokumentasi Tangkapan Layar Antarmuka & Jejak Kasus (Bagian 10.4)

Seluruh tangkapan layar resolusi penuh tersimpan di folder [`screenshots/`](screenshots/):

1. **Menu 1 — Impor & Validasi Dataset XES (F01)**:
   [`screenshots/01_menu_dataset_dan_validasi_F01.png`](screenshots/01_menu_dataset_dan_validasi_F01.png)
2. **Menu 2 — Event Log Overview & Statistika Dasar (F02)**:
   [`screenshots/02_menu_overview_dan_statistika_F02.png`](screenshots/02_menu_overview_dan_statistika_F02.png)
3. **Menu 3 — Analisis Exercise 11.7 A–E (F03)**:
   [`screenshots/03_menu_exercise_11_7_F03.png`](screenshots/03_menu_exercise_11_7_F03.png)
4. **Menu 4 — Analisis Exercise 11.15 & 11.18 beserta Bukti Event 11.15 (F04–F05)**:
   [`screenshots/04_menu_exercise_11_15_dan_11_18_bukti_11_15.png`](screenshots/04_menu_exercise_11_15_dan_11_18_bukti_11_15.png)
5. **Menu 4 — Analisis Exercise 11.15 & 11.18 beserta Bukti Event Same-Resource 11.18 (F04–F05)**:
   [`screenshots/05_menu_exercise_11_15_dan_11_18_bukti_11_18.png`](screenshots/05_menu_exercise_11_15_dan_11_18_bukti_11_18.png)
6. **Menu 5 — Analisis Exercise 11.22 Urutan `O_Cancelled` $\rightarrow$ `O_Accepted` (F06)**:
   [`screenshots/06_menu_exercise_11_22_F06.png`](screenshots/06_menu_exercise_11_22_F06.png)
7. **Menu 6 (Case Explorer) — Jejak Kasus Soal 11.15 (`Application_1292983087`)**:
   [`screenshots/07_case_explorer_jejak_kasus_11_15.png`](screenshots/07_case_explorer_jejak_kasus_11_15.png)
8. **Menu 6 (Case Explorer) — Jejak Kasus Soal 11.18 (`Application_1221917431` oleh `User_144`)**:
   [`screenshots/08_case_explorer_jejak_kasus_11_18.png`](screenshots/08_case_explorer_jejak_kasus_11_18.png)
9. **Menu 6 (Case Explorer) — Jejak Kasus Soal 11.22 (`Application_1000671285`)**:
   [`screenshots/09_case_explorer_jejak_kasus_11_22.png`](screenshots/09_case_explorer_jejak_kasus_11_22.png)
10. **Menu 7 — Ringkasan Jawaban & Ekspor CSV/HTML (F07)**:
    [`screenshots/10_menu_ringkasan_dan_ekspor_F07.png`](screenshots/10_menu_ringkasan_dan_ekspor_F07.png)

---

## 8. Temuan, Kendala Teknis, dan Solusi

1. **Performa Pembacaan Berkas XES Berukuran Besar (1,2 Juta Event)**:
   - *Kendala*: Parser XML Python standar pada `pm4py` membutuhkan waktu sekitar 85–90 detik untuk membaca `BPI Challenge 2017.xes.gz`.
   - *Solusi*: Mengintegrasikan akselerator berbasis Rust resmi untuk PM4Py (`r4pm` dan `rustxes`) sehingga waktu impor turun drastis menjadi **~8–11 detik**, serta menjalankan proses pembacaan dan perhitungan di dalam *worker thread* (`QThread`) agar antarmuka GUI tetap responsif dan menampilkan indikator progres secara *real-time*.
2. **Perbedaan Penulisan Kapitalisasi Nama Aktivitas (`W_Assess Potential Fraud` vs `W_Assess potential fraud`)**:
   - *Kendala*: Pada naskah soal tertulis `W_Assess Potential Fraud`, sedangkan nilai atribut `concept:name` di dalam XES BPIC17 adalah `W_Assess potential fraud`.
   - *Solusi*: Menerapkan pencocokan nama aktivitas secara *case-insensitive* (`str.strip().str.lower()`) pada fungsi filter F04 dan F05.
3. **Render Tabel Berukuran 31.509 Baris di GUI Desktop**:
   - *Kendala*: Penggunaan `QTableWidget` berbasis *item* biasa akan membekukan memori ketika memuat 31.509 baris case.
   - *Solusi*: Mengimplementasikan arsitektur *Model-View* menggunakan `QAbstractTableModel` (`DataFrameTableModel`) dan `QSortFilterProxyModel` yang membaca langsung dari memori `pandas.DataFrame` secara *lazy/virtual*, sehingga pencarian dan pengurutan 31.509 case berlangsung instan (< 50 ms).

---

## 9. Pembagian Peran & Kontribusi Anggota Kelompok (4 Mahasiswa)

Sesuai pedoman Bagian 9 Instruksi Proyek Tahap 1, berikut adalah pembagian tanggung jawab ke-4 anggota kelompok (silakan sesuaikan NIM/Nama anggota kelompok Anda sebelum pengumpulan final):

| Peran / Anggota | Modul yang Dikerjakan | Rincian Kontribusi & Tanggung Jawab |
| :--- | :--- | :--- |
| **Anggota 1** *(Parsing, Validasi & Overview)* | `src/core.py`, `src/analyzer.py` (`analyze_overview`) | Mengimplementasikan impor XES dengan `pm4py.read_xes`, validasi atribut wajib/opsional (F01), pre-komputasi indeks urutan trace (`_trace_pos`), perhitungan *cycle time* per case, serta statistik overview & frekuensi aktivitas (F02). |
| **Anggota 2** *(Exercise 11.7 & Cycle Time)* | `src/analyzer.py` (`analyze_exercise_11_7`) | Merancang dan menguji aturan filter `Contains` (`O_Accepted` pada 11.7 C, `O_Refused` pada 11.7 D) dan aturan `Endpoint` (`O_Cancelled` pada 11.7 E) menggunakan PM4Py tanpa mengubah konteks durasi trace utuh (F03). |
| **Anggota 3** *(Exercise 11.15, 11.18 & 11.22)* | `src/analyzer.py` (`analyze_exercise_11_15`, `11_18`, `11_22`), `src/synthetic.py` | Mengimplementasikan filter *repeated complete* `W_Assess potential fraud` ($\ge 2\times$ `complete`, F04), filter *same resource* dengan validasi resource kosong (F05), filter *eventually follows* `O_Cancelled` $\rightarrow$ `O_Accepted` beserta analisis level `OfferID` (F06), dan log sintetis. |
| **Anggota 4** *(Integrasi GUI, Case Explorer & Ekspor)* | `src/gui.py`, `src/exporter.py`, `main.py`, `tests/test_edge_cases.py` | Membangun antarmuka desktop PySide6 7-tab dengan *worker thread* (`QThread`), fitur pencarian & penyorotan bukti di *Case Explorer*, ekspor otomatis CSV/HTML (F07), serta pengujian unit *edge cases* dan penyusunan dokumentasi laporan. |
