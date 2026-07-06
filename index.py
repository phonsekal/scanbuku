import streamlit as st
import pandas as pd
import requests

# Konfigurasi halaman
st.set_page_config(page_title="Sistem Scan & Posting BMN Buku", layout="wide")

# Fungsi untuk memuat data master lokal
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

# Membuat koneksi ke Google Sheets (Otomatis membaca URL dari secrets.toml)
conn = st.connection("gsheets", type=GSheetsConnection)

# Memuat database master
df = load_data()

if df is not None:
    st.title("📚 Sistem Pencarian & Posting Live BMN Buku (Tanpa Kunci)")
    st.write("Beri centang pada hasil pencarian untuk otomatis mengisi No Urut, NUP, dan Judul di Google Sheets Anda.")
    
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
                df_tampil.insert(0, "Pilih & Posting", False)
                
                # Tabel Interaktif
                edited_df = st.data_editor(
                    df_tampil,
                    use_container_width=True,
                    hide_index=True,
                    disabled=["NUP", "Merk"],
                    key="editor_buku"
                )
                
                # Deteksi Aksi Centang
                for i in range(len(edited_df)):
                    if edited_df.iloc[i]["Pilih & Posting"] == True:
                        nup_terpilih = edited_df.iloc[i]["NUP"]
                        merk_terpilih = edited_df.iloc[i]["Merk"]
                        
                        # --- PROSES POSTING VIA GSHEETS CONNECTION ---
                        try:
                            # 1. Ambil data yang sudah ada di cloud saat ini
                            df_existing = conn.read(ttl=0) # ttl=0 memastikan data paling update yang diambil
                            
                            # Cek nomor urut terakhir
                            if df_existing.empty or 'No' not in df_existing.columns:
                                next_no = 1
                            else:
                                # Bersihkan baris kosong jika ada
                                df_existing = df_existing.dropna(subset=['No'])
                                if len(df_existing) == 0:
                                    next_no = 1
                                else:
                                    next_no = int(pd.to_numeric(df_existing['No']).max()) + 1
                            
                            # 2. Buat baris baru
                            new_row = pd.DataFrame([{"No": next_no, "NUP": nup_terpilih, "Judul": merk_terpilih}])
                            
                            # 3. Gabungkan dan update ke Google Sheets
                            df_updated = pd.concat([df_existing, new_row], ignore_index=True)
                            conn.update(data=df_updated)
                            
                            st.toast(f"🚀 Sukses! No: {next_no} | NUP: {nup_terpilih} berhasil diposting!")
                            st.cache_data.clear() # Hapus cache agar tampilan live di bawah langsung berubah
                        except Exception as e:
                            st.error(f"Gagal posting data: {e}")
                            
            else:
                st.warning("Kolom 'NUP' atau 'Merk' tidak lengkap di file 'databmnbuku.csv'.")
        else:
            st.error(f"Data dengan kode '{search_query}' tidak ditemukan.")
            
    # --- PRATINJAU LIVE DATA DI GOOGLE SHEETS ---
    st.markdown("---")
    st.subheader("📋 Tampilan Live Data Terposting (Google Sheets)")
    
    try:
        df_live = conn.read(ttl=0)
        if not df_live.empty:
            st.dataframe(df_live, use_container_width=True, hide_index=True)
            st.caption(f"Total entri tercatat di Google Sheets: {len(df_live)} baris.")
        else:
            st.info("Spreadsheet Anda masih kosong.")
    except Exception as e:
        st.info("Sedang memuat atau spreadsheet belum terisi.")
