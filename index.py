import streamlit as st
import pandas as pd

# Konfigurasi halaman agar tampilan lebih luas (Wide Mode)
st.set_page_config(page_title="Pencarian Data BMN Buku", layout="wide")

# Fungsi untuk memuat data ke memori (RAM) agar pencarian instan
@st.cache_data
def load_data():
    try:
        # 1. Menggunakan sep=';' karena file menggunakan pembatas titik koma
        # 2. Menggunakan on_bad_lines='skip' untuk mengamankan jika ada baris yang korup/tidak konsisten
        df = pd.read_csv("databmnbuku.csv", sep=';', dtype=str, on_bad_lines='skip', encoding='utf-8')
        
        # Bersihkan spasi di awal/akhir pada nama kolom
        df.columns = df.columns.str.strip()
        
        # Hapus kolom tanpa nama (kolom kosong beruntun di sebelah kanan seperti sisa kolom AP)
        df = df.loc[:, ~df.columns.str.contains('^Unnamed:|^\s*$', case=False, na=True)]
        
        # Mengisi data kosong (NaN) dengan string kosong agar tidak error saat filter
        df = df.fillna("")
        return df
    except FileNotFoundError:
        st.error("File 'databmnbuku.csv' tidak ditemukan. Pastikan file berada di folder yang sama dengan skrip ini.")
        return None

# Memuat database buku
df = load_data()

if df is not None:
    st.title("📚 Sistem Pencarian & Scan BMN Buku")
    st.write("Masukkan kode atau scan barcode untuk menampilkan data NUP dan Merk secara instan.")
    
    # 1. Komponen Input (Otomatis Fokus untuk mempermudah scan barcode)
    # Fitur autofocus membuat petugas bisa langsung scan tanpa perlu klik kolom input terlebih dahulu
    search_query = st.text_input("Scan / Input Kode di sini:", key="search_input", autocomplete="off").strip()

    # Urutan kolom yang akan diperiksa secara berurutan (Waterfall Filter)
    kolom_filter = [
        'Kode1', 'Kode2', 'Kode3', 
        'ISBN1', 'ISBN2', 'ISBN3', 
        'Barcode1', 'Barcode2', 'Barcode3'
    ]

    # Cek apakah nama-nama kolom di atas benar-benar ada di file CSV Anda
    kolom_tersedia = [col for col in kolom_filter if col in df.columns]

    # 2. Proses Pencarian Berjenjang
    if search_query:
        hasil_filter = pd.DataFrame() # Tempat menampung hasil data yang cocok
        kolom_ditemukan = ""

        # Loop berurutan dari Kode1 sampai Barcode3
        for col in kolom_tersedia:
            # Cari baris yang cocok (case-insensitive / mengabaikan huruf besar-kecil)
            match_rows = df[df[col].str.lower() == search_query.lower()]
            
            if not match_rows.empty:
                hasil_filter = match_rows
                kolom_ditemukan = col
                break # BERHENTI mencari jika sudah ditemukan di kolom yang lebih prioritas

        # 3. Tampilkan Hasil
        if not hasil_filter.empty:
            st.success(f"Ditemukan {len(hasil_filter)} data pada kolom **{kolom_ditemukan}**")
            
            # Ambil hanya kolom NUP dan Merk sesuai permintaan Anda
            kolom_tampilan = []
            if 'NUP' in hasil_filter.columns: kolom_tampilan.append('NUP')
            if 'Merk' in hasil_filter.columns: kolom_tampilan.append('Merk')
            
            # Jika kolom NUP atau Merk ternyata tidak ada di CSV, tampilkan kolom pencarian sebagai cadangan
            if not kolom_tampilan:
                kolom_tampilan = [kolom_ditemukan]
                st.warning("Kolom 'NUP' atau 'Merk' tidak ditemukan di CSV. Menampilkan kolom referensi pencarian.")

            # Menampilkan hasil dalam bentuk tabel Streamlit yang bersih tanpa nomor indeks bawaan
            st.dataframe(
                hasil_filter[kolom_tampilan], 
                use_container_width=True,
                hide_index=True
            )
        else:
            st.error(f"Data dengan kode '{search_query}' tidak ditemukan di seluruh urutan kolom filter.")
            
    # Tampilkan info total kapasitas database di bagian bawah aplikasi
    st.markdown("---")
    st.caption(f"Total kapasitas database aktif: {len(df):,} baris.")
