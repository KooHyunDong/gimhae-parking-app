import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, time
from streamlit_autorefresh import st_autorefresh

# 1. 자동 새로고침 (60초 주기)
st_autorefresh(interval=60000, key="datarefresh")

# 2. 데이터 수집 로직
def get_parking_data():
    DATA_API_KEY = 'a50c28a4672e470d594bae9af0dd980b37474e12b353b76e13fb1becba418ab1'
    url = f"http://openapi.airport.co.kr/service/rest/AirportParking/airportparkingRT?serviceKey={DATA_API_KEY}&schAirportCode=PUS"
    try:
        response = requests.get(url, timeout=10)
        root = ET.fromstring(response.text)
        items = root.findall('.//item')
        return items
    except: return []

# 3. 요금 계산 로직
def calculate_kims_fee_pro(start_dt, end_dt, car_size, discount_type, parking_lot):
    if start_dt >= end_dt: return 0
    total_fee, current_dt = 0, start_dt
    while current_dt < end_dt:
        next_dt = min(current_dt + timedelta(days=1), end_dt)
        duration_min = int((next_dt - current_dt).total_seconds() / 60)
        is_weekend = current_dt.weekday() >= 4 
        if car_size == "소형":
            base_fee, unit_fee = 900, 300
            if "P3" in parking_lot: daily_limit = 10000 if is_weekend else 7000
            else: daily_limit = 15000 if is_weekend else 10000
            fee = base_fee if duration_min <= 30 else base_fee + ((duration_min - 30) // 10) * unit_fee
            total_fee += min(fee, daily_limit)
        else:
            base_fee, unit_fee = 1200, 400
            fee = base_fee if duration_min <= 30 else base_fee + ((duration_min - 30) // 10) * unit_fee
            total_fee += fee 
        current_dt = next_dt
    if discount_type in ["국가유공자(상이)", "장애인차량", "저공해 1,2종", "경차", "다자녀"]:
        total_fee *= 0.5
    elif discount_type == "저공해 3종":
        total_fee *= 0.8
    return int(total_fee)

# 4. 스타일 설정
st.set_page_config(page_title="김해공항 주차안내", layout="centered")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
    font-family: 'Noto Sans KR', sans-serif;
    .stApp { background-color: #FFFFFF; }
    .header-line { border-top: 3px solid #005596; margin-top: 10px; margin-bottom: 20px; }
    .status-card { border: 1px solid #E5E7EB; padding: 18px 25px; border-radius: 10px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
    .status-name { font-weight: 700; font-size: 1.15rem; color: #111827; }
    .status-avail { font-weight: 700; font-size: 1.4rem; }
    .fee-result-red { background-color: #b00b2d; color: white; padding: 45px 20px; border-radius: 8px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# ----------------- UI -----------------
st.title("김해공항 실시간 주차 현황")
st.markdown("<div class='header-line'></div>", unsafe_allow_html=True)
st.caption(f"⏱️ 실시간 자동 갱신 중: {datetime.now().strftime('%H:%M:%S')}")

items = get_parking_data()
p12_avail = 0
p3_avail = 0

if items:
    for item in items:
        name = item.findtext('parkingAirportCodeName')
        display_name = name + " 주차장" if "P3" in name else name
        avail = max(0, int(item.findtext('parkingFullSpace', 0)) - int(item.findtext('parkingIstay', 0)))
        
        # 문구 수정: 0대이면 '만차', 아니면 'n대 가능'
        if avail == 0:
            avail_text = "만차"
            avail_color = "#FF4D4D"
        else:
            avail_text = f"{avail:,}대 가능"
            avail_color = "#005596"
        
        if "P1" in name or "P2" in name: p12_avail += avail
        if "P3" in name: p3_avail = avail
        
        st.markdown(f"""
            <div class="status-card">
                <span class="status-name">{display_name}</span>
                <span class="status-avail" style="color: {avail_color};">{avail_text}</span>
            </div>
        """, unsafe_allow_html=True)

st.write("")
st.subheader("예상 주차요금 계산")

c1, c2 = st.columns([1.3, 1], gap="medium")
with c1:
    st.markdown("**주차 설정**")
    p_lot = st.selectbox("주차장 선택", ["P1, P2 여객주차장", "P3 여객(화물)주차장"])
    car_size = st.radio("차량 크기", ["소형", "대형"], horizontal=True)
    discount = st.selectbox("할인 항목 선택", ["일반", "국가유공자(상이)", "장애인차량", "저공해 3종", "저공해 1,2종", "경차", "다자녀"])
    
    col_in_d, col_in_t = st.columns(2); in_d = col_in_d.date_input("입차 예정일"); in_t = col_in_t.time_input("입차 시간", time(11, 0), step=600)
    col_out_d, col_out_t = st.columns(2); out_d = col_out_d.date_input("출차 예정일", value=datetime.now()+timedelta(days=1)); out_t = col_out_t.time_input("출차 시간", time(11, 0), step=600)
    start = datetime.combine(in_d, in_t); end = datetime.combine(out_d, out_t)

with c2:
    st.markdown("**예상 요금**")
    if start < end:
        fee = calculate_kims_fee_pro(start, end, car_size, discount, p_lot)
        dur = end - start
        st.markdown(f"""<div class="fee-result-red"><div style='font-size:2.5rem; font-weight:bold; margin-bottom:15px;'>{fee:,}원</div><div style='font-size:0.85rem; opacity:0.9;'>주차시간: {dur.days}일 {dur.seconds // 3600}시간 {(dur.seconds % 3600) // 60}분</div></div>""", unsafe_allow_html=True)
        
        st.write("")
        # --- 가이드 로직 (담백하게 수정) ---
        if p12_avail == 0 and p3_avail == 0:
            st.warning("ℹ️ 공항 내 모든 주차장이 만차입니다. 가급적 사설 주차장이나 대중교통 이용을 권장합니다.")
        elif p12_avail == 0:
            st.info(f"💡 여객주차장 만차! 현재 P3 주차장({p3_avail}대 가능) 이용이 가장 빠릅니다.")
        else:
            st.success(f"✅ 현재 원활합니다. 터미널 앞 P1 주차장 이용이 편리합니다.")
    else:
        st.error("시간 확인")