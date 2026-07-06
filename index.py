import streamlit as st
import pandas as pd
import requests

# Konfigurasi halaman agar tampilan lebar (Wide Mode)
st.set_page_config(page_title="Sistem Scan & Posting BMN Buku", layout="wide")

# ⚠️ PASTIKAN URL WEB APP GOOGLE APPS SCRIPT ANDA SUDAH BENAR DI SINI
WEB_APP_URL = "PASANG_URL_APPS_SCRIPT_ANDA_DI_SINI"

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
    if WEB_APP_URL == "PASANG_URL_APPS_SCRIPT_ANDA_DI_SINI":
        st.error("Masukkan URL Web App dari Google Apps Script terlebih dahulu di dalam kode!")
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
    st.title("📚 Sistem Pencarian & Posting Live BMN Buku")
    st.write("Pencarian fleksibel (bisa sebagian kode, abaikan spasi/titik). Centang kolom 'Kirim' untuk memposting.")
    
    # Input Scan / Cari
    search_query = st.text_input("Scan / Input Kode di sini:", key="search_input", autocomplete="off").strip()

    kolom_filter = ['Kode1', 'Kode2', 'Kode3', 'ISBN1', 'ISBN2', 'ISBN3', 'Barcode1', 'Barcode2', 'Barcode3']
    kolom_tersedia = [col for col in kolom_filter if col in df.columns]

    if search_query:
        # Bersihkan input user dari spasi dan titik untuk pencarian yang fleksibel
        query_clean = search_query.replace(" ", "").replace(".", "").lower()
        
        hasil_filter = pd.DataFrame()
        kolom_ditemukan = ""

        # Proses pencarian berjenjang (Waterfall) dengan pencocokan sebagian (Contains)
        for col in kolom_tersedia:
            # Bersihkan juga data di kolom database dari spasi dan titik untuk perbandingan
            kolom_clean = df[col].str.replace(" ", "", regex=False).str.replace(".", "", regex=False).str.lower()
            
            # Cari apakah query ada di dalam text kolom (Partial Match)
            match_rows = df[kolom_clean.str.contains(query_clean, na=False)]
            
            if not match_rows.empty:
                hasil_filter = match_rows.copy()
                kolom_ditemukan = col
                break

        # Tampilkan Hasil jika ditemukan
        if not hasil_filter.empty:
            st.success(f"Ditemukan {len(hasil_filter)} data berdasarkan pencarian di kolom **{kolom_ditemukan}**")
            
            # Pastikan kolom utama tersedia di CSV master
            required_cols = ['NUP', 'Merk', 'Kodefikasi']
            if all(col in hasil_filter.columns for col in required_cols):
                
                # 1. Ambil data yang dibutuhkan dan ganti nama 'Merk' menjadi 'Judul'
                df_tampil = hasil_filter[required_cols].copy()
                df_tampil = df_tampil.rename(columns={'Merk': 'Judul'})
                
                # 2. Kelompokkan berdasarkan NUP & Judul, lalu gabungkan kodefikasi jika ada yang berbeda
                # Menggunakan '/' sebagai penghubung jika kodenya unik dan lebih dari 1
                df_grouped = df_tampil.groupby(['NUP', 'Judul'])['Kodefikasi'].apply(
                    lambda x: ' / '.join(sorted(list(set(filter(None, x)))))
                ).reset_index()
                
                # 3. Tambahkan kolom checklist dengan nama 'Kirim' di posisi paling kanan
                df_grouped['Kirim'] = False
                
                # 4. Susun urutan tampilan kolom secara presisi: NUP, Kodefikasi, Judul, Kirim
                df_grouped = df_grouped[['NUP', 'Kodefikasi', 'Judul', 'Kirim']]
                
                # 5. Tampilkan tabel interaktif (Data Editor)
                edited_df = st.data_editor(
                    df_grouped,
                    use_container_width=True,
                    hide_index=True,
                    disabled=["NUP", "Kodefikasi", "Judul"], # Kunci data master agar aman
                    key="editor_buku"
                )
                
                # 6. Deteksi aksi klik pada kolom 'Kirim'
                for i in range(len(edited_df)):
                    if edited_df.iloc[i]["Kirim"] == True:
                        nup_terpilih = edited_df.iloc[i]["NUP"]
                        judul_terpilih = edited_df.iloc[i]["Judul"]
                        
                        # Jalankan fungsi kirim ke Google Sheets via Web App URL
                        sukses = simpan_ke_google_sheets(nup_terpilih, judul_terpilih)
                        
                        if sukses:
                            st.toast(f"🚀 Terposting ke Google Sheets! NUP: {nup_terpilih} | Judul: {judul_terpilih}")
            else:
                st.warning("Kolom 'NUP', 'Merk', atau 'Kodefikasi' tidak lengkap di file 'databmnbuku.csv'.")
        else:
            st.error(f"Data dengan kata kunci '{search_query}' tidak ditemukan di seluruh kolom filter.")
