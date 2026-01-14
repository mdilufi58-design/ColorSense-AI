import streamlit as st
from PIL import Image, ImageDraw
import numpy as np
import colorsys
import time
from gtts import gTTS
import io

# --- 1. ตั้งค่าหน้าเว็บ & Intro ---
st.set_page_config(page_title="ColorSense AI", page_icon="🧠", layout="centered")

# Intro Animation
if 'first_load' not in st.session_state:
    st.session_state['first_load'] = True

if st.session_state['first_load']:
    placeholder = st.empty()
    with placeholder.container():
        st.markdown("<h1 style='text-align: center;'>🚀 กำลังเปิดระบบ AI...</h1>", unsafe_allow_html=True)
        bar = st.progress(0)
        for i in range(100):
            time.sleep(0.01)
            bar.progress(i + 1)
        st.success("System Online!")
        time.sleep(0.5)
    placeholder.empty()
    st.toast('ยินดีต้อนรับสู่ ColorSense AI!', icon="🎉")
    st.session_state['first_load'] = False


# --- 2. ส่วนฟังก์ชันหลัก (Logic) ---

def speak(text):
    try:
        tts = gTTS(text=text, lang='th')
        audio_bytes = io.BytesIO()
        tts.write_to_fp(audio_bytes)
        st.audio(audio_bytes, format='audio/mp3', start_time=0)
    except Exception as e:
        st.error("ไม่สามารถเล่นเสียงได้ (ตรวจสอบอินเทอร์เน็ต)")


def simulate_color_blindness(image, type='protanopia'):
    img_array = np.array(image)
    if type == 'protanopia':
        matrix = [[0.567, 0.433, 0], [0.558, 0.442, 0], [0, 0.242, 0.758]]
    elif type == 'deuteranopia':
        matrix = [[0.625, 0.375, 0], [0.7, 0.3, 0], [0, 0.3, 0.7]]
    elif type == 'tritanopia':
        matrix = [[0.95, 0.05, 0], [0, 0.433, 0.567], [0, 0.475, 0.525]]
    else:
        return image
    simulated = np.dot(img_array[..., :3], np.array(matrix).T)
    simulated = np.clip(simulated, 0, 255).astype(np.uint8)
    return Image.fromarray(simulated)


# ฟังก์ชันจำแนกสี 12 สีพื้นฐาน
def classify_pixel_hsv(r, g, b):
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    h_deg = h * 360

    # 1. กลุ่มสี ขาว-ดำ (Achromatic)
    if s < 0.15:  # สีจางมาก
        if v > 0.65:
            return "สีขาว (White)", "#FFFFFF", "black"
        else:
            return "สีดำ (Black)", "#000000", "white"

    if v < 0.20:  # มืดมาก
        return "สีดำ (Black)", "#000000", "white"

    # 2. กลุ่มสีสัน (Chromatic) - แยกละเอียด 12 สี
    if (h_deg >= 0 and h_deg < 15) or (h_deg >= 345 and h_deg <= 360):
        return "สีแดง (Red)", "#FF0000", "white"

    elif 15 <= h_deg < 45:
        if v < 0.50: return "สีน้ำตาล (Brown)", "#8B4513", "white"
        return "สีส้ม (Orange)", "#FFA500", "black"

    elif 45 <= h_deg < 75:
        if v < 0.40: return "สีน้ำตาล (Brown)", "#8B4513", "white"
        return "สีเหลือง (Yellow)", "#FFFF00", "black"

    elif 75 <= h_deg < 160:
        # แยกเขียวอ่อน / เขียวเข้ม
        if v > 0.6 and s < 0.8:
            return "สีเขียวอ่อน (Light Green)", "#90EE90", "black"
        else:
            return "สีเขียวเข้ม (Dark Green)", "#006400", "white"

    elif 160 <= h_deg < 260:
        # แยกฟ้า / น้ำเงิน
        if h_deg < 200 or (v > 0.7 and s < 0.6):
            return "สีฟ้า (Light Blue)", "#00BFFF", "black"
        else:
            return "สีน้ำเงิน (Blue)", "#0000FF", "white"

    elif 260 <= h_deg < 330:
        return "สีม่วง (Purple)", "#800080", "white"

    elif 330 <= h_deg < 345:
        return "สีชมพู (Pink)", "#FFC0CB", "black"

    return "ไม่แน่ชัด", "#CCCCCC", "black"


def analyze_dominant_color(image):
    img_small = image.resize((100, 100))
    img_array = np.array(img_small)
    h, w, _ = img_array.shape
    box_s = int(min(h, w) * 0.4)
    c_y, c_x = h // 2, w // 2
    roi = img_array[c_y - box_s // 2: c_y + box_s // 2, c_x - box_s // 2: c_x + box_s // 2]

    vote_counts = {}
    color_meta = {}
    for row in range(0, roi.shape[0], 2):
        for col in range(0, roi.shape[1], 2):
            r, g, b = roi[row, col]
            color_name, hex_code, text_color = classify_pixel_hsv(r, g, b)
            if color_name in vote_counts:
                vote_counts[color_name] += 1
            else:
                vote_counts[color_name] = 1
                color_meta[color_name] = (hex_code, text_color)

    if not vote_counts: return "ไม่ทราบสี", "#000000", "white", image
    winner_name = max(vote_counts, key=vote_counts.get)
    winner_hex, winner_text = color_meta[winner_name]

    draw = ImageDraw.Draw(image)
    draw.rectangle([c_x - box_s // 2, c_y - box_s // 2, c_x + box_s // 2, c_y + box_s // 2], outline=winner_hex,
                   width=8)
    return winner_name, winner_hex, winner_text, image


# ฟังก์ชันดึงคำแนะนำตามบริบท 12 สี
def get_color_advice(color_name):
    advice = ""
    status_type = "info"  # success, warning, error, info

    if "แดง" in color_name:
        advice = "หยุด (Stop) / อันตราย (Danger) / ร้อน (Hot)"
        status_type = "error"
    elif "ส้ม" in color_name:
        advice = "ระวัง (Warning) / เขตก่อสร้าง / พลังงาน"
        status_type = "warning"
    elif "เหลือง" in color_name:
        advice = "เตรียมหยุด / ระวัง (Caution) / ผลไม้สุก"
        status_type = "warning"
    elif "เขียวอ่อน" in color_name:
        advice = "ธรรมชาติ / ผ่อนคลาย / ผลไม้อาจยังไม่สุก"
        status_type = "success"
    elif "เขียวเข้ม" in color_name or ("เขียว" in color_name and "อ่อน" not in color_name):
        advice = "ไปได้ (Go) / ปลอดภัย (Safe) / ธรรมชาติสมบูรณ์"
        status_type = "success"
    elif "ฟ้า" in color_name:
        advice = "สดใส / ท้องฟ้า / น้ำ / ความเย็น"
        status_type = "info"
    elif "น้ำเงิน" in color_name:
        advice = "ป้ายคำสั่งบังคับ / ข้อมูล / ทางการ / หนาวเย็น"
        status_type = "info"
    elif "ม่วง" in color_name:
        advice = "มีพิษ (ในธรรมชาติ) / ลึกลับ / หรูหรา"
        status_type = "error"
    elif "ชมพู" in color_name:
        advice = "อ่อนโยน / ความรัก / ขนมหวาน"
        status_type = "success"
    elif "น้ำตาล" in color_name:
        advice = "ดิน / แห้งแล้ง / เก่าแก่ / เน่าเสีย"
        status_type = "warning"
    elif "ดำ" in color_name:
        advice = "ปิดเครื่อง (Off) / มืด / สิ้นสุด"
        status_type = "error"
    elif "ขาว" in color_name:
        advice = "สว่าง / สะอาด / เริ่มต้น / เปิดไฟ"
        status_type = "info"
    else:
        advice = "โปรดพิจารณาบริบทเพิ่มเติม"

    return advice, status_type


# --- 3. ส่วนหน้าจอแสดงผล (UI) ---

st.title("ระบบ AI ช่วยแปลความหมายสีตามสถานการณ์")
st.caption("Contextual Color Translation System for Color Vision Deficiency")

# สร้าง Tabs
tab1, tab2, tab3 = st.tabs(["📸 สแกนสี & เสียง", "👓 จำลองตาบอดสี", "📚 ความรู้ (Edu Hub)"])

# === TAB 1: สแกนสี & เสียง ===
with tab1:
    st.info("💡 เลือกวิธีนำเข้าภาพ (ถ่ายรูป หรือ อัปโหลด)")

    # เลือก Input
    input_method = st.radio("แหล่งที่มาของภาพ:", ["📸 กล้องถ่ายรูป", "📂 อัปโหลดไฟล์ภาพ"], horizontal=True)

    image_to_process = None

    if input_method == "📸 กล้องถ่ายรูป":
        # CSS เป้าเล็ง
        st.markdown(
            """<style>div[data-testid="stCameraInput"]::after {content: "+"; font-size: 100px; color: rgba(0, 255, 0, 0.8); position: absolute; top: 50%; left: 50%; transform: translate(-50%, -55%); pointer-events: none;}</style>""",
            unsafe_allow_html=True)
        camera_file = st.camera_input("กดถ่ายภาพ")
        if camera_file: image_to_process = Image.open(camera_file)
    else:
        upload_file = st.file_uploader("เลือกไฟล์ภาพ (JPG, PNG)", type=["jpg", "png", "jpeg"])
        if upload_file: image_to_process = Image.open(upload_file)

    # ประมวลผลเมื่อมีภาพ
    if image_to_process:
        c_name, c_hex, c_text, result_img = analyze_dominant_color(image_to_process.copy())

        st.markdown("---")
        st.image(result_img, caption="พื้นที่วิเคราะห์ (ROI)", use_column_width=True)

        st.markdown(f"""
        <div style="background-color: {c_hex}; padding: 20px; border-radius: 15px; text-align: center; border: 5px solid #333;">
            <h1 style="color: {c_text}; margin:0;">{c_name}</h1>
        </div>
        """, unsafe_allow_html=True)

        # ดึงคำแนะนำ 12 สี
        advice_text, status = get_color_advice(c_name)

        st.subheader("📢 คำแนะนำเบื้องต้น:")
        if status == "error":
            st.error(f"**{c_name}:** {advice_text}")
        elif status == "warning":
            st.warning(f"**{c_name}:** {advice_text}")
        elif status == "success":
            st.success(f"**{c_name}:** {advice_text}")
        else:
            st.info(f"**{c_name}:** {advice_text}")

        # เตรียมเสียงพูด
        speech_text = f"ตรวจพบ {c_name} ครับ ความหมายคือ {advice_text}"
        st.write("🔊 กำลังเล่นเสียง...")
        speak(speech_text)

# === TAB 2: จำลองมุมมอง (Simulator) ===
with tab2:
    st.header("👓 โลกในมุมมองผู้มีภาวะตาบอดสี")
    st.write("อัปโหลดภาพเพื่อดูว่าผู้มีภาวะตาบอดสีแต่ละประเภทมองเห็นอย่างไร")
    sim_upload = st.file_uploader("เลือกรูปภาพทดสอบ", type=["jpg", "png", "jpeg"], key="sim_uploader")
    sim_type = st.selectbox("เลือกประเภทภาวะตาบอดสี",
                            ["ตาบอดสีแดง (Protanopia)", "ตาบอดสีเขียว (Deuteranopia)", "ตาบอดสีน้ำเงิน (Tritanopia)"])

    if sim_upload:
        raw_img = Image.open(sim_upload)
        type_code = 'protanopia'
        if "เขียว" in sim_type:
            type_code = 'deuteranopia'
        elif "น้ำเงิน" in sim_type:
            type_code = 'tritanopia'
        sim_img = simulate_color_blindness(raw_img, type_code)
        col_a, col_b = st.columns(2)
        with col_a:
            st.image(raw_img, caption="สายตาปกติ", use_column_width=True)
        with col_b:
            st.image(sim_img, caption=f"มุมมอง {sim_type}", use_column_width=True)

# === TAB 3: Education Hub ===
with tab3:
    st.header("📚 คลังความรู้เรื่องตาบอดสี")
    st.markdown(
        """<div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin-bottom: 20px;"><h3>🧬 ตาบอดสีเกิดจากอะไร?</h3><p>เกิดจากความผิดปกติของ <b>เซลล์รูปกรวย (Cone Cells)</b> ในจอประสาทตา</p></div>""",
        unsafe_allow_html=True)
    st.subheader("📊 สถิติที่น่าสนใจ")
    c1, c2 = st.columns(2)
    with c1: st.metric("ผู้ชายที่มีโอกาสเป็น", "8%", "เสี่ยงสูง")
    with c2: st.metric("ผู้หญิงที่มีโอกาสเป็น", "0.5%", "- ต่ำกว่ามาก", delta_color="inverse")
    st.subheader("🚦 ปัญหาที่พบบ่อย")
    st.info("1. การแยกสีไฟจราจร (แดง vs เหลือง)")
    st.info("2. การดูความสุกของผลไม้")
    st.info("3. การอ่านกราฟหรือแผนภูมิสี")