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

# CSS untuk tampilan Modern & Mobile Friendly
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; font-weight: bold; }
    .stExpander { background-color: white; border-radius: 10px; margin-bottom: 10px; }
    .metric-container { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
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
        img.thumbnail((500, 500)) # Kompresi agar hemat space
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
    
    # Mingguan
    if week_num == 1: tasks["Mingguan"] = ["Lap Kaca/Pintu: TU, Perpus, PPDB, Security"]
    elif week_num == 2: tasks["Mingguan"] = ["Lap Kaca: Lab Komputer, Lab Biologi"]
    elif week_num == 3: tasks["Mingguan"] = ["Lap Kaca/Pintu: Kelas XI, XII"]
    else: tasks["Mingguan"] = ["Lap Kaca/Pintu: Kelas X, UKS, IPM"]
    
    # Bulanan (Rotasi 5 Bulan)
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
    # Perbaikan Logo: Menggunakan URL yang lebih reliabel
    st.image("https://upload.wikimedia.org/wikipedia/commons/a/af/Muhammadiyah_Logo.svg", width=100)
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
    st.title("👷 Dashboard Pak Hanto")
    tasks = get_current_tasks()
    logs = load_data("cleaning_logs")
    reps = load_data("cleaning_reports")
    
    # Perhitungan Progress untuk Pak Hanto
    total_tugas = sum(len(v) for v in tasks.items())
    tgl_hari_ini = datetime.now(jakarta_tz).strftime("%Y-%m-%d")
    done = len(logs[logs['tanggal'] == tgl_hari_ini]) if not logs.empty else 0
    persen = (done / total_tugas) if total_tugas > 0 else 0
    
    # UI Progress di Dashboard Hanto [Request User]
    col_h1, col_h2 = st.columns(2)
    col_h1.metric("Tugas Selesai", f"{done} / {total_tugas}")
    col_h2.metric("Progress", f"{int(persen*100)}%")
    st.progress(min(persen, 1.0))
    st.divider()
    
    tab1, tab2, tab3 = st.tabs(["📝 Checklist Kerja", "📣 Komplain Pengawas", "🚨 Lapor Kerusakan"])
    
    with tab1:
        st.info(f"Jadwal: {datetime.now(jakarta_tz).strftime('%d %B %Y')}")
        for cat, items in tasks.items():
            with st.expander(f"📌 {cat}"):
                for item in items:
                    if st.button(f"Update: {item}", key=f"btn_{item}"):
                        st.session_state.active_task = item
        
        if 'active_task' in st.session_state:
            st.markdown(f"### Upload Bukti: {st.session_state.active_task}")
            f1 = st.camera_input("Foto SEBELUM", key="cam1")
            f2 = st.camera_input("Foto SESUDAH", key="cam2")
            ket = st.text_input("Keterangan/Kendala")
            if st.button("Simpan Laporan", type="primary"):
                if f1 and f2:
                    save_data("cleaning_logs", pd.DataFrame([{
                        "tanggal": datetime.now(jakarta_tz).strftime("%Y-%m-%d"),
                        "tugas": st.session_state.active_task,
                        "sebelum": img_to_bytes(f1),
                        "sesudah": img_to_bytes(f2),
                        "keterangan": ket, "status": "Selesai"
                    }]))
                    st.success("Tugas Berhasil Disimpan!")
                    del st.session_state.active_task
                    st.rerun()
                else:
                    st.error("Foto Sebelum & Sesudah Wajib Diambil")

    with tab2:
        st.subheader("Instruksi Khusus dari Pengawas")
        if not reps.empty:
            komplain = reps[reps['tipe'] == "Komplain Pengawas"].sort_index(ascending=False)
            if not komplain.empty:
                for _, k in komplain.head(5).iterrows():
                    st.warning(f"📍 **{k['area']}**: {k['masalah']} ({k['tanggal']})")
            else:
                st.write("Belum ada komplain masuk.")
        else:
            st.write("Belum ada data.")

    with tab3:
        with st.form("f_rusak"):
            area = st.text_input("Lokasi Temuan")
            masalah = st.text_area("Detail Masalah / Barang Rusak")
            foto = st.camera_input("Foto Bukti")
            if st.form_submit_button("Kirim Laporan Kerusakan"):
                save_data("cleaning_reports", pd.DataFrame([{
                    "tanggal": datetime.now(jakarta_tz).strftime("%Y-%m-%d"),
                    "area": area, "masalah": masalah, "foto": img_to_bytes(foto), "tipe": "Temuan Pelaksana"
                }]))
                st.success("Laporan terkirim!")

# --- DASHBOARD PENGAWAS ---
elif st.session_state.auth == "Pengawas":
    st.title("🔍 Menu Pengawas")
    logs = load_data("cleaning_logs")
    reps = load_data("cleaning_reports")
    
    t_today = get_current_tasks()
    total_tugas = sum(len(v) for v in t_today.values())
    tgl_hari_ini = datetime.now(jakarta_tz).strftime("%Y-%m-%d")
    
    done = len(logs[logs['tanggal'] == tgl_hari_ini]) if not logs.empty else 0
    persen = (done / total_tugas) if total_tugas > 0 else 0
    
    # UI Progress Pengawas [Request User]
    col_p1, col_p2 = st.columns(2)
    col_p1.metric("Progress Hari Ini", f"{done} / {total_tugas}")
    col_p2.metric("Persentase Selesai", f"{int(persen*100)}%")
    st.progress(min(persen, 1.0))

    t1, t2, t3 = st.tabs(["📊 Histori Foto", "🛠️ Laporan Perbaikan", "📣 Komplain"])
    
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
            else: st.info("Tidak ada data pada tanggal ini.")
        else: st.write("Database kosong")

    with t2:
        if not reps.empty:
            st.table(reps[reps['tipe'] == "Temuan Pelaksana"][['tanggal', 'area', 'masalah']])
        else: st.info("Tidak ada laporan kerusakan")

    with t3:
        with st.form("f_komplain"):
            loc = st.text_input("Lokasi yang Kotor")
            det = st.text_area("Instruksi ke Pak Hanto")
            if st.form_submit_button("Kirim Komplain"):
                save_data("cleaning_reports", pd.DataFrame([{
                    "tanggal": datetime.now(jakarta_tz).strftime("%Y-%m-%d"),
                    "area": loc, "masalah": det, "foto": "", "tipe": "Komplain Pengawas"
                }]))
                st.error("Instruksi telah dikirim ke dashboard Pak Hanto")

if st.sidebar.button("Logout"):
    st.session_state.auth = None
    st.rerun()
