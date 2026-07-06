import streamlit as st
import pandas as pd

# Konfigurasi halaman agar tampilan lebih luas (Wide Mode)
st.set_page_config(page_title="Pencarian Data BMN Buku", layout="wide")

# Fungsi untuk memuat data ke memori (RAM) agar pencarian instan
@st.cache_data
def load_data():
    try:
        # Membaca file CSV (sesuaikan encoding jika ada error karakter khusus)
        df = pd.read_csv("databmnbuku.csv", dtype=str)
        
        # Membersihkan spasi di awal/akhir pada nama kolom
        df.columns = df.columns.str.strip()
        
        # Mengisi data kosong (NaN) dengan string kosong agar tidak error saat filter
        df = df.fillna("")
        return df
    except FileNotFoundError:
        st.error("File 'databmnbuku.csv' tidak ditemukan. Pastikan file berada di folder yang sama dengan skrip ini.")
        return None

df = load_data()

if df is not None:
    st.title("📚 Sistem Pencarian & Scan BMN Buku")
    st.write("Masukkan kode atau scan barcode untuk menampilkan data NUP dan Merk secara instan.")
    
    # 1. Komponen Input (Otomatis Fokus untuk mempermudah scan barcode)
    # Gunakan fitur autofocus agar petugas bisa langsung scan tanpa klik kolom input terlebih dahulu
    search_query = st.text_input("Scan / Input Kode di sini:", key="search_input", autocomplete="off").strip()

    # Urutan kolom yang akan diperiksa secara berurutan
    kolom_filter = [
        'Kode1', 'Kode2', 'Kode3', 
        'ISBN1', 'ISBN2', 'ISBN3', 
        'Barcode1', 'Barcode2', 'Barcode3'
    ]

    # Cek apakah nama-nama kolom di atas benar-benar ada di file CSV
    kolom_tersedia = [col for col in kolom_filter if col in df.columns]
    
    if len(kolom_tersedia) < len(kolom_filter):
        st.warning(f"Catatan: Beberapa kolom filter tidak ditemukan di CSV Anda. Kolom aktif: {kolom_tersedia}")

    # 2. Proses Pencarian Berjenjang (Waterfall Filter)
    if search_query:
        hasil_filter = pd.DataFrame() # Tempat menampung hasil
        kolom_ditemukan = ""

        # Loop berurutan dari Kode1 sampai Barcode3
        for col in kolom_tersedia:
            # Cari baris yang cocok (case-insensitive / mengabaikan huruf besar-kecil)
            match_rows = df[df[col].str.lower() == search_query.lower()]
            
            if not match_rows.empty:
                hasil_filter = match_rows
                kolom_ditemukan = col
                break # Berhenti mencari jika sudah ditemukan di kolom yang lebih prioritas

        # 3. Tampilkan Hasil
        if not hasil_filter.empty:
            st.success(f"Ditemukan {len(hasil_filter)} data pada kolom **{kolom_ditemukan}**")
            
            # Ambil hanya kolom NUP dan Merk (pastikan nama kolom di CSV Anda persis seperti ini)
            kolom_tampilan = []
            if 'NUP' in hasil_filter.columns: kolom_tampilan.append('NUP')
            if 'Merk' in hasil_filter.columns: kolom_tampilan.append('Merk')
            
            # Jika kolom NUP/Merk tidak ketemu, tampilkan kolom pencarian sebagai cadangan
            if not kolom_tampilan:
                kolom_tampilan = [kolom_ditemukan]
                st.warning("Kolom 'NUP' atau 'Merk' tidak ditemukan di CSV. Menampilkan kolom pencarian.")

            # Menampilkan hasil dalam bentuk tabel yang bersih
            st.dataframe(
                hasil_filter[kolom_tampilan], 
                use_container_width=True,
                hide_index=True
            )
        else:
            st.error(f"Data dengan kode '{search_query}' tidak ditemukan di seluruh kolom filter.")
            
    # Tampilkan info total database di bagian bawah (opsional)
    st.markdown("---")
    st.caption(f"Total kapasitas database saat ini: {len(df):,} baris.")
