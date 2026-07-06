import streamlit as st
import pandas as pd
import requests

# Konfigurasi halaman agar tampilan lebar (Wide Mode)
st.set_page_config(page_title="Inventarisasi BMN Sekretariat Badan Pengembangan dan Pembinaan Bahasa", layout="wide")

# URL WEB APP GOOGLE APPS SCRIPT yang sudah Anda sesuaikan
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyVCt37xvsX_oiNsw-AX99RW2SC4gU0K0qOMJvcY0909zqGMC1J1eaUbZOMrRI1oOXh/exec"

# Fungsi memuat data master lokal (instan dari RAM)
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("databmnbuku.csv", sep=';', dtype=str, on_bad_lines='skip', encoding='utf-8')
        df.columns = df.columns.str.strip()
        df = df.loc[:, ~df.columns.str.contains('^Unnamed:|^\s*$', case=False, na=True)]
        df = df.fillna("")
        return df
    except FileNotFoundError:
        st.error("File 'databmnbuku.csv' tidak ditemukan.")
        return None

# Fungsi posting data langsung via Web App URL
def simpan_ke_google_sheets(nup, merk):
    if "PASANG_URL" in WEB_APP_URL:
        st.error("Masukkan URL Web App dari Google Apps Script terlebih dadaulu di dalam kode!")
        return False
    try:
        payload = {"nup": nup, "merk": merk}
        response = requests.post(WEB_APP_URL, json=payload)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Terjadi kesalahan koneksi ke Google Sheets: {e}")
        return False

# Memuat database master
df = load_data()

if df is not None:
    st.title("Sistem Inventarisasi Buku Perpustakaan Badan Bahasa 2026")
    st.write("Sistem pencarian buku berdasarkan kodefikasi SLIMS")
    
    # Inisialisasi session state untuk menyimpan hasil pencarian agar tidak hilang saat klik centang
    if "hasil_pencarian" not in st.session_state:
        st.session_state.hasil_pencarian = None
    if "kolom_ditemukan" not in st.session_state:
        st.session_state.kolom_ditemukan = ""

    # 1. Menggunakan st.form untuk menampung Input Teks dan Tombol Fisik Cari
    with st.form(key="search_form", clear_on_submit=False):
        # Input Scan / Cari
        search_query = st.text_input("Scan / Input Kode di sini:", autocomplete="off").strip()
        
        # Tombol Fisik untuk memicu pencarian (Menghilangkan paksaan press enter bawaan)
        submit_button = st.form_submit_button(label="🔍 Cari Data", type="primary")

    kolom_filter = ['Kode1', 'Kode2', 'Kode3', 'ISBN1', 'ISBN2', 'ISBN3', 'Barcode1', 'Barcode2', 'Barcode3']
    kolom_tersedia = [col for col in kolom_filter if col in df.columns]

    # 2. Proses Pencarian (Hanya berjalan jika tombol Cari diklik / Enter ditekan di dalam form)
    if submit_button:
        if search_query:
            # Bersihkan input user dari spasi dan titik untuk pencarian yang fleksibel
            query_clean = search_query.replace(" ", "").replace(".", "").lower()
            hasil_filter = pd.DataFrame()
            kolom_ditemukan = ""

            # Proses pencarian berjenjang (Waterfall) dengan pencocokan sebagian (Contains)
            for col in kolom_tersedia:
                # Bersihkan juga data di kolom database dari spasi dan titik untuk perbandingan
                kolom_clean = df[col].str.replace(" ", "", regex=False).str.replace(".", "", regex=False).str.lower()
                match_rows = df[kolom_clean.str.contains(query_clean, na=False)]
                
                if not match_rows.empty:
                    hasil_filter = match_rows.copy()
                    kolom_ditemukan = col
                    break

            # Simpan hasil atau status ke dalam session state agar awet
            if not hasil_filter.empty:
                st.session_state.hasil_pencarian = hasil_filter
                st.session_state.kolom_ditemukan = kolom_ditemukan
            else:
                st.session_state.hasil_pencarian = "KOSONG"
                st.session_state.kolom_ditemukan = ""
        else:
            st.warning("Silakan masukkan kata kunci kode atau scan barcode terlebih dahulu!")
            st.session_state.hasil_pencarian = None

    # 3. Tampilkan dan Proses Hasil dari Session State (Aman dari Rerun akibat klik checkbox)
    if st.session_state.hasil_pencarian is not None:
        if isinstance(st.session_state.hasil_pencarian, str) and st.session_state.hasil_pencarian == "KOSONG":
            st.error("Data tidak ditemukan di seluruh kolom filter.")
        elif isinstance(st.session_state.hasil_pencarian, pd.DataFrame):
            hasil_filter = st.session_state.hasil_pencarian
            kolom_ditemukan = st.session_state.kolom_ditemukan
            
            st.success(f"Ditemukan {len(hasil_filter)} data berdasarkan pencarian di kolom **{kolom_ditemukan}**")
            
            # Daftarkan kolom wajib dari CSV master
            cols_wajib = ['NUP', 'Merk', 'Kode1', 'Kode2', 'Kode3']
            if all(col in hasil_filter.columns for col in cols_wajib):
                
                # Ambil data yang dibutuhkan dan ganti nama 'Merk' menjadi 'Judul'
                df_tampil = hasil_filter[cols_wajib].copy()
                df_tampil = df_tampil.rename(columns={'Merk': 'Judul'})
                
                # Fungsi lokal untuk menggabungkan Kode1, Kode2, Kode3 per baris data
                def gabung_kode_baris(row):
                    list_kode = [row['Kode1'], row['Kode2'], row['Kode3']]
                    kode_bersih = [k.strip() for k in list_kode if k.strip() not in ["", "-", "#N/A"]]
                    kode_unik = list(dict.fromkeys(kode_bersih))
                    return " / ".join(kode_unik) if kode_unik else "-"

                df_tampil['Kodefikasi'] = df_tampil.apply(gabung_kode_baris, axis=1)
                
                # Kelompokkan berdasarkan NUP & Judul (jika hasil pencarian menghasilkan baris kembar)
                def gabung_grup_kode(series):
                    gabungan = []
                    for teks in series:
                        pecahan = [p.strip() for p in teks.split('/') if p.strip() not in ["", "-", "#N/A"]]
                        gabungan.extend(pecahan)
                    unik_grup = list(dict.fromkeys(gabungan))
                    return " / ".join(unik_grup) if unik_grup else "-"

                df_grouped = df_tampil.groupby(['NUP', 'Judul'])['Kodefikasi'].apply(gabung_grup_kode).reset_index()
                
                # Tambahkan kolom checklist dengan nama 'Kirim' di posisi paling kanan
                df_grouped['Kirim'] = False
                
                # Susun urutan kolom secara presisi: NUP, Kodefikasi, Judul, Kirim
                df_grouped = df_grouped[['NUP', 'Kodefikasi', 'Judul', 'Kirim']]
                
                # Tampilkan tabel interaktif (Data Editor)
                edited_df = st.data_editor(
                    df_grouped,
                    use_container_width=True,
                    hide_index=True,
                    disabled=["NUP", "Kodefikasi", "Judul"], # Kunci data agar aman dari salah ketik
                    key="editor_buku"
                )
                
                # Deteksi aksi klik pada kolom 'Kirim'
                for i in range(len(edited_df)):
                    if edited_df.iloc[i]["Kirim"] == True:
                        nup_terpilih = edited_df.iloc[i]["NUP"]
                        judul_terpilih = edited_df.iloc[i]["Judul"]
                        
                        # Jalankan fungsi kirim ke Google Sheets via Web App URL
                        sukses = simpan_ke_google_sheets(nup_terpilih, judul_terpilih)
                        
                        if sukses:
                            st.toast(f"🚀 Terposting ke Google Sheets! NUP: {nup_terpilih} | Judul: {judul_terpilih}")
            else:
                st.warning("Struktur kolom 'NUP', 'Merk', 'Kode1', 'Kode2', atau 'Kode3' tidak ditemukan di CSV master.")
