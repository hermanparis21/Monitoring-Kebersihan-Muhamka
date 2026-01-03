import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import io
import base64
from streamlit_gsheets import GSheetsConnection
from PIL import Image

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Monitoring Kebersihan Muhamka", layout="centered")
jakarta_tz = pytz.timezone('Asia/Jakarta')

# Fungsi konversi waktu ke Bahasa Indonesia
def get_waktu_indo():
    now = datetime.now(jakarta_tz)
    hari = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", 
             "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    
    nama_hari = hari[now.weekday()]
    nama_bulan = bulan[now.month - 1]
    return f"{nama_hari}, {now.day} {nama_bulan} {now.year} | {now.strftime('%H:%M')} WIB"

# CSS untuk tampilan Modern
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; font-weight: bold; }
    .stExpander { background-color: white; border-radius: 10px; margin-bottom: 10px; }
    .time-box { font-size: 1.1em; font-weight: bold; color: #2e7d32; text-align: right; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- KONEKSI GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    try:
        return conn.read(worksheet=sheet_name, ttl="0s")
    except:
        return pd.DataFrame()

def save_data(sheet_name, data):
    existing_df = load_data(sheet_name)
    updated_df = pd.concat([existing_df, data], ignore_index=True)
    conn.update(worksheet=sheet_name, data=updated_df)

def img_to_bytes(uploaded_file):
    if uploaded_file:
        img = Image.open(uploaded_file).convert("RGB")
        img.thumbnail((500, 500))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=50)
        return base64.b64encode(buf.getvalue()).decode()
    return ""

# --- LOGIKA JADWAL OTOMATIS ---
def get_current_tasks():
    now = datetime.now(jakarta_tz)
    day = now.day
    month = now.month
    week_num = (day - 1) // 7 + 1
    
    tasks = {
        "Harian": ["Sapu/Pel Kantor TU & Guru", "Cuci Gelas & Alat Minum", "Sapu Halaman Sekolah", "Buang Sampah Kelas", "Kamar Mandi Siswa & Guru"],
        "Mingguan": [],
        "Bulanan": [],
        "Tahunan": ["Kuras Toren / Tandon Air"]
    }
    
    if week_num == 1: tasks["Mingguan"] = ["Lap Kaca/Pintu: TU, Perpus, PPDB, Security"]
    elif week_num == 2: tasks["Mingguan"] = ["Lap Kaca: Lab Komputer, Lab Biologi"]
    elif week_num == 3: tasks["Mingguan"] = ["Lap Kaca/Pintu: Kelas XI, XII"]
    else: tasks["Mingguan"] = ["Lap Kaca/Pintu: Kelas X, UKS, IPM"]
    
    cycle = (month - 1) % 5 + 1
    if cycle == 1: tasks["Bulanan"] = ["Plafon/Laba-laba: TU, Perpus, PPDB, Gerbang, Security"]
    elif cycle == 2: tasks["Bulanan"] = ["Plafon: Lab Komp & Bio", "Cabut Rumput Liar", "Rapikan Taman"]
    elif cycle == 3: tasks["Bulanan"] = ["Plafon: Kelas XI & XII"]
    elif cycle == 4: tasks["Bulanan"] = ["Plafon: Kelas X, UKS, IPM"]
    else: tasks["Bulanan"] = ["Kuras Kolam Ikan Depan & Belakang"]
    
    return tasks

# --- LOGIN ---
if 'auth' not in st.session_state:
    st.session_state.auth = None

if st.session_state.auth is None:
    st.markdown("<h1 style='text-align: center; font-size: 80px;'>🧹</h1>", unsafe_allow_html=True)
    st.title("Monitoring Kebersihan SMA Muhamka")
    user = st.text_input("Username")
    pw = st.text_input("Password", type="password")
    if st.button("Login"):
        if user == "hanto" and pw == "sayapastibisa":
            st.session_state.auth = "Pelaksana"
            st.rerun()
        elif user == "pengawas" and pw == "ayokitabantu":
            st.session_state.auth = "Pengawas"
            st.rerun()
        else:
            st.error("User atau Password salah!")

# --- DASHBOARD PELAKSANA (HANTO) ---
elif st.session_state.auth == "Pelaksana":
    st.markdown(f"<div class='time-box'>🕒 {get_waktu_indo()}</div>", unsafe_allow_html=True)
    st.title("👷 Dashboard Pak Hanto")
    
    tasks = get_current_tasks()
    logs = load_data("cleaning_logs")
    reps = load_data("cleaning_reports")
    tgl_hari_ini = datetime.now(jakarta_tz).strftime("%Y-%m-%d")
    
    # Hitung Progress
    total_tugas_list = [item for sublist in tasks.values() for item in sublist]
    total_tugas = len(total_tugas_list)
    done_tasks_df = logs[logs['tanggal'] == tgl_hari_ini] if not logs.empty else pd.DataFrame()
    done_count = len(done_tasks_df)
    persen = (done_count / total_tugas) if total_tugas > 0 else 0
    
    col_h1, col_h2 = st.columns(2)
    col_h1.metric("Tugas Selesai", f"{done_count} / {total_tugas}")
    col_h2.metric("Progress", f"{int(persen*100)}%")
    st.progress(min(persen, 1.0))
    st.divider()
    
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Checklist Kerja", "✅ Laporan Saya", "📣 Komplain Pengawas", "🚨 Lapor Kerusakan"])
    
    with tab1:
        st.subheader("Daftar Tugas Hari Ini")
        for cat, items in tasks.items():
            if items:
                with st.expander(f"📌 {cat}"):
                    for item in items:
                        # Cek status tugas untuk Hanto
                        is_done = item in done_tasks_df['tugas'].values if not done_tasks_df.empty else False
                        status_icon = "✅" if is_done else "⌛"
                        
                        col_text, col_btn = st.columns([3, 1])
                        col_text.write(f"{status_icon} {item}")
                        if not is_done:
                            if col_btn.button("Update", key=f"upd_{item}"):
                                st.session_state.active_task = item
                                st.rerun()

        if 'active_task' in st.session_state:
            st.markdown(f"--- \n ### 📸 Upload Bukti: {st.session_state.active_task}")
            f1 = st.camera_input("Foto SEBELUM", key="cam1")
            f2 = st.camera_input("Foto SESUDAH", key="cam2")
            ket = st.text_input("Keterangan/Kendala")
            if st.button("Simpan Laporan Sekarang", type="primary"):
                if f1 and f2:
                    save_data("cleaning_logs", pd.DataFrame([{
                        "tanggal": tgl_hari_ini,
                        "tugas": st.session_state.active_task,
                        "sebelum": img_to_bytes(f1),
                        "sesudah": img_to_bytes(f2),
                        "keterangan": ket, "status": "Selesai"
                    }]))
                    st.success("Berhasil disimpan!")
                    del st.session_state.active_task
                    st.rerun()
                else:
                    st.error("Wajib ambil foto Sebelum & Sesudah!")

    with tab2:
        st.subheader("Riwayat Pekerjaan Hari Ini")
        if not done_tasks_df.empty:
            for _, r in done_tasks_df.iterrows():
                st.success(f"✔️ {r['tugas']} (Selesai)")
        else:
            st.info("Belum ada tugas yang dilaporkan hari ini.")

    with tab3:
        st.subheader("Instruksi Pengawas")
        if not reps.empty:
            komplain = reps[reps['tipe'] == "Komplain Pengawas"].sort_index(ascending=False)
            if not komplain.empty:
                for _, k in komplain.head(5).iterrows():
                    st.warning(f"📍 **{k['area']}**: {k['masalah']} ({k['tanggal']})")
            else: st.write("Belum ada komplain.")
        else: st.write("Data kosong.")

    with tab4:
        st.subheader("Laporan Kerusakan/Temuan")
        if 'show_form_rusak' not in st.session_state:
            st.session_state.show_form_rusak = False
            
        if st.button("➕ Buat Laporan Kerusakan Baru"):
            st.session_state.show_form_rusak = True
            
        if st.session_state.show_form_rusak:
            with st.form("f_rusak"):
                area = st.text_input("Lokasi Temuan")
                masalah = st.text_area("Detail Masalah")
                foto = st.camera_input("Foto Bukti")
                if st.form_submit_button("Kirim Laporan"):
                    save_data("cleaning_reports", pd.DataFrame([{
                        "tanggal": tgl_hari_ini,
                        "area": area, "masalah": masalah, "foto": img_to_bytes(foto), "tipe": "Temuan Pelaksana"
                    }]))
                    st.success("Laporan terkirim!")
                    st.session_state.show_form_rusak = False
                    st.rerun()

# --- DASHBOARD PENGAWAS ---
elif st.session_state.auth == "Pengawas":
    st.markdown(f"<div class='time-box'>🕒 {get_waktu_indo()}</div>", unsafe_allow_html=True)
    st.title("🔍 Menu Pengawas")
    logs = load_data("cleaning_logs")
    reps = load_data("cleaning_reports")
    
    t_today = get_current_tasks()
    total_tugas = sum(len(v) for v in t_today.values())
    tgl_hari_ini = datetime.now(jakarta_tz).strftime("%Y-%m-%d")
    done = len(logs[logs['tanggal'] == tgl_hari_ini]) if not logs.empty else 0
    persen = (done / total_tugas) if total_tugas > 0 else 0
    
    col_p1, col_p2 = st.columns(2)
    col_p1.metric("Progress Hari Ini", f"{done} / {total_tugas}")
    col_p2.metric("Persentase", f"{int(persen*100)}%")
    st.progress(min(persen, 1.0))

    t1, t2, t3, t4, t5 = st.tabs(["📊 Histori Foto", "📋 Daftar Tugas", "📥 Export Data", "🛠️ Laporan Perbaikan", "📣 Komplain"])
    
    # ... (Isi tab pengawas tetap stabil seperti sebelumnya)
    with t1:
        f_tgl = st.date_input("Pilih Tanggal", value=datetime.now(jakarta_tz))
        target_date = f_tgl.strftime("%Y-%m-%d")
        if not logs.empty:
            view = logs[logs['tanggal'] == target_date]
            if not view.empty:
                for _, r in view.iterrows():
                    with st.expander(f"✅ {r['tugas']}"):
                        c1, c2 = st.columns(2)
                        if r['sebelum']: c1.image(f"data:image/jpeg;base64,{r['sebelum']}", caption="Sebelum")
                        if r['sesudah']: c2.image(f"data:image/jpeg;base64,{r['sesudah']}", caption="Sesudah")
                        st.write(f"Ket: {r['keterangan']}")
            else: st.info("Tidak ada data.")

    with t2:
        st.subheader("Tugas yang Harus Dikerjakan Hanto")
        for cat, items in t_today.items():
            if items:
                with st.expander(f"📅 {cat}"):
                    for i, item in enumerate(items, 1):
                        is_done = not logs[(logs['tanggal'] == tgl_hari_ini) & (logs['tugas'] == item)].empty if not logs.empty else False
                        st.write(f"{'✅' if is_done else '⌛'} {i}. {item}")

    with t3:
        st.subheader("📥 Export Laporan")
        if not logs.empty:
            df_export = logs.copy().drop(columns=['sebelum', 'sesudah'], errors='ignore')
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_export.to_excel(writer, index=False, sheet_name='Laporan')
            st.download_button(label="Download Excel", data=output.getvalue(), file_name="Laporan_Kebersihan.xlsx")
            st.dataframe(df_export)

    with t4:
        if not reps.empty:
            st.table(reps[reps['tipe'] == "Temuan Pelaksana"][['tanggal', 'area', 'masalah']])

    with t5:
        with st.form("f_komplain"):
            loc = st.text_input("Lokasi Kotor")
            det = st.text_area("Instruksi")
            if st.form_submit_button("Kirim ke Hanto"):
                save_data("cleaning_reports", pd.DataFrame([{"tanggal": tgl_hari_ini, "area": loc, "masalah": det, "foto": "", "tipe": "Komplain Pengawas"}]))
                st.error("Terkirim!")

if st.sidebar.button("Logout"):
    st.session_state.auth = None
    st.rerun()
