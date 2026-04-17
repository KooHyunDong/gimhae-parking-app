import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, time
from streamlit_autorefresh import st_autorefresh

# 1. 자동 새로고침 (60초 주기)
st_autorefresh(interval=60000, key="datarefresh")

# --- 한국 시간 설정 함수 ---
def get_kst_now():
    # 서버 시간(UTC)에 9시간을 더해 한국 시간으로 변환
    return datetime.utcnow() + timedelta(hours=9)

# 2. 데이터 수집 로직
def get_parking_data():
    try:
        DATA_API_KEY = st.secrets["data_api_key"]
    except KeyError:
        st.error("Streamlit Secrets에 API 키를 등록해주세요.")
        return[]
    url = "http://openapi.airport.co.kr/servi
    ce/rest/AirportParking/airportparkingRT"
    params = {'serviceKey': requests.utils.unquote(DATA_API_KEY), 'schAirportCode': 'PUS'}
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        root = ET.fromstring(response.text)
        return root.findall('.//item')
    except: return []

# 3. 요금 계산 로직 (기존 유지)
def calculate_kims_fee_pro(start_dt, end_dt, car_size, discount_type, parking_lot):
    if start_dt >= end_dt: return 0
    total_fee, current_dt = 0, start_dt
    while current_dt < end_dt:
        next_dt = min(current_dt + timedelta(days=1), end_dt)
        duration_min = int((next_dt - current_dt).total_seconds() / 60)
        is_weekend = current_dt.weekday() >= 4 
        if car_size == "소형":
            base, unit = 900, 300
            limit = (15000 if is_weekend else 10000) if "P3" not in parking_lot else (10000 if is_weekend else 7000)
            fee = base if duration_min <= 30 else base + ((duration_min - 30) // 10) * unit
            total_fee += min(fee, limit)
        else:
            base, unit = 1200, 400
            fee = base if duration_min <= 30 else base + ((duration_min - 30) // 10) * unit
            total_fee += fee 
        current_dt = next_dt
    if discount_type in ["국가유공자(상이)", "장애인차량", "저공해 1,2종", "경차", "다자녀"]: total_fee *= 0.5
    elif discount_type == "저공해 3종": total_fee *= 0.8
    return int(total_fee)

# 4. 스타일 설정 (모바일 최적화 레이아웃 유지)
st.set_page_config(page_title="김해공항 주차", layout="centered")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
    * { font-family: 'Noto Sans KR', sans-serif; }
    .block-container { padding: 0.5rem 1rem !important; }
    [data-testid="stHeader"] { display: none; }
    .main-title { font-size: 1.4rem; font-weight: 800; color: #111827; margin-bottom: 2px; }
    .header-line { border-top: 3px solid #005596; margin-bottom: 8px; }
    .status-card { background: white; border: 1px solid #E5E7EB; padding: 10px 15px; border-radius: 8px; margin-bottom: 5px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
    .status-name { font-weight: 700; font-size: 0.9rem; color: #374151; }
    .status-avail { font-weight: 700; font-size: 1rem; color: #005596; }
    .fee-container { background: #b00b2d; color: white; padding: 15px; border-radius: 12px; text-align: center; margin-top: 10px; }
    .fee-value { font-size: 2.2rem; font-weight: 800; }
    .fee-label { font-size: 0.8rem; opacity: 0.8; }
    .stSelectbox, .stRadio { margin-bottom: -15px; }
    label { font-size: 0.8rem !important; font-weight: 700 !important; }
    </style>
    """, unsafe_allow_html=True)

# ----------------- UI -----------------
st.markdown('<div class="main-title">🛫 김해공항 주차</div>', unsafe_allow_html=True)
st.markdown('<div class="header-line"></div>', unsafe_allow_html=True)

# --- 한국 시간으로 갱신 시간 표시 ---
kst_now = get_kst_now()
st.caption(f"🔄 마지막 갱신: {kst_now.strftime('%H:%M:%S')} (KST)")

items = get_parking_data()
if items:
    for item in items:
        name = item.findtext('parkingAirportCodeName')
        display_name = name + " 주차장" if "P3" in name else name
        avail = max(0, int(item.findtext('parkingFullSpace', 0)) - int(item.findtext('parkingIstay', 0)))
        avail_text = "만차" if avail == 0 else f"{avail:,}대 여유"
        color = "#EF4444" if avail == 0 else "#005596"
        st.markdown(f'<div class="status-card"><span class="status-name">{display_name}</span><span class="status-avail" style="color: {color};">{avail_text}</span></div>', unsafe_allow_html=True)

st.write("")
p_lot = st.selectbox("주차장", ["P1, P2 여객주차장", "P3 여객(화물)주차장"])
car_size = st.radio("크기", ["소형", "대형"], horizontal=True)
discount = st.selectbox("할인", ["일반", "국가유공자(상이)", "장애인차량", "저공해 3종", "저공해 1,2종", "경차", "다자녀"])

c1, c2 = st.columns(2)
# 입차 날짜도 한국 시간 기준으로 기본값 설정
in_d = c1.date_input("입차", kst_now.date())
in_t = c2.time_input("시간", time(11, 0))

c3, c4 = st.columns(2)
out_d = c3.date_input("출차", kst_now.date() + timedelta(days=1))
out_t = c4.time_input(" 시간 ", time(11, 0))

start = datetime.combine(in_d, in_t); end = datetime.combine(out_d, out_t)

if start < end:
    fee = calculate_kims_fee_pro(start, end, car_size, discount, p_lot)
    dur = end - start
    st.markdown(f'<div class="fee-container"><div class="fee-value">{fee:,}원</div><div class="fee-label">{dur.days}일 {dur.seconds // 3600}시간 {(dur.seconds % 3600) // 60}분 주차</div></div>', unsafe_allow_html=True)
else:
    st.error("시간 확인 요망")
