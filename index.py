import streamlit as st
import pandas as pd
import requests

# Konfigurasi halaman
st.set_page_config(page_title="Sistem Scan & Posting BMN Buku", layout="wide")

# ⚠️ GANTI DENGAN URL APLIKASI WEB YANG ANDA COPY DARI APPS SCRIPT!
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwbKuC3gS5Z3HxctjwlLreXdErZJhU59ND59l7y-Sj79a-86VL1CTtR8McTEIxG5n2g/exec"

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

# Fungsi posting data langsung via Web App URL tanpa credentials.json
def simpan_ke_google_sheets(nup, merk):
    if WEB_APP_URL == "PASANG_URL_APPS_SCRIPT_ANDA_DI_SINI":
        st.error("Masukkan URL Web App dari Google Apps Script terlebih dahulu di dalam kode!")
        return False
    try:
        # Kirim data dalam format JSON ke Google Sheets
        payload = {"nup": nup, "merk": merk}
        response = requests.post(WEB_APP_URL, json=payload)
        
        if response.status_code == 200:
            return True
        else:
            st.error(f"Gagal mengirim data. Status: {response.status_code}")
            return False
    except Exception as e:
        st.error(f"Terjadi kesalahan koneksi: {e}")
        return False

# Memuat database master
df = load_data()

if df is not None:
    st.title("📚 Sistem Pencarian & Posting Live BMN Buku")
    st.write("Tanpa Credentials! Beri centang pada hasil pencarian untuk langsung mengisi Google Sheets.")
    
    # Input Scan / Cari
    search_query = st.text_input("Scan / Input Kode di sini:", key="search_input", autocomplete="off").strip()

    kolom_filter = ['Kode1', 'Kode2', 'Kode3', 'ISBN1', 'ISBN2', 'ISBN3', 'Barcode1', 'Barcode2', 'Barcode3']
    kolom_tersedia = [col for col in kolom_filter if col in df.columns]

    if search_query:
        hasil_filter = pd.DataFrame()
        kolom_ditemukan = ""

        for col in kolom_tersedia:
            match_rows = df[df[col].str.lower() == search_query.lower()]
            if not match_rows.empty:
                hasil_filter = match_rows.copy()
                kolom_ditemukan = col
                break

        # Tampilkan Hasil jika ditemukan
        if not hasil_filter.empty:
            st.success(f"Ditemukan {len(hasil_filter)} data pada kolom **{kolom_ditemukan}**")
            
            if 'NUP' in hasil_filter.columns and 'Merk' in hasil_filter.columns:
                df_tampil = hasil_filter[['NUP', 'Merk']].copy()
                
                # Kolom checklist interaktif
                df_tampil.insert(0, "Pilih & Posting", False)
                
                # Tampilkan tabel interaktif
                edited_df = st.data_editor(
                    df_tampil,
                    use_container_width=True,
                    hide_index=True,
                    disabled=["NUP", "Merk"],
                    key="editor_buku"
                )
                
                # Deteksi aksi klik checklist
                for i in range(len(edited_df)):
                    if edited_df.iloc[i]["Pilih & Posting"] == True:
                        nup_terpilih = edited_df.iloc[i]["NUP"]
                        merk_terpilih = edited_df.iloc[i]["Merk"]
                        
                        # Jalankan fungsi kirim tanpa ribet
                        sukses = simpan_ke_google_sheets(nup_terpilih, merk_terpilih)
                        
                        if sukses:
                            st.toast(f"🚀 Terposting! NUP: {nup_terpilih} | Judul: {merk_terpilih}")
            else:
                st.warning("Kolom 'NUP' atau 'Merk' tidak lengkap di file 'databmnbuku.csv'.")
        else:
            st.error(f"Data dengan kode '{search_query}' tidak ditemukan.")
