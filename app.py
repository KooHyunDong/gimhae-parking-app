import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, time
from streamlit_autorefresh import st_autorefresh

# 1. 자동 새로고침 (60초 주기)
st_autorefresh(interval=60000, key="datarefresh")

def get_kst_now():
    return datetime.utcnow() + timedelta(hours=9)

def get_parking_data():
    # 실제 배포시 st.secrets["API_KEY"] 사용 권장
    DATA_API_KEY = 'a50c28a4672e470d594bae9af0dd980b37474e12b353b76e13fb1becba418ab1'
    url = "http://openapi.airport.co.kr/service/rest/AirportParking/airportparkingRT"
    params = {'serviceKey': requests.utils.unquote(DATA_API_KEY), 'schAirportCode': 'PUS'}
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        root = ET.fromstring(response.text)
        return root.findall('.//item')
    except: return None

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
    
    # 할인 적용
    if discount_type in ["국가유공자(상이)", "장애인차량", "저공해 1,2종", "경차", "다자녀"]: total_fee *= 0.5
    elif discount_type == "저공해 3종": total_fee *= 0.8
    return int(total_fee)

# --- UI 설정 ---
st.set_page_config(page_title="김해공항 주차 가이드", layout="centered")
st.markdown("""
    <style>
    .main-title { font-size: 1.5rem; font-weight: 800; color: #111827; }
    .status-card { background: white; border: 1px solid #E5E7EB; padding: 12px; border-radius: 10px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center; }
    .status-name { font-weight: 700; color: #374151; }
    .fee-container { background: #b00b2d; color: white; padding: 15px; border-radius: 12px; text-align: center; margin-top: 10px; }
    .alert-box { background-color: #FEF2F2; border-left: 5px solid #EF4444; padding: 10px; margin-bottom: 15px; font-size: 0.85rem; color: #B91C1C; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-title">🛫 김해공항 실시간 주차</div>', unsafe_allow_html=True)

# 한국 시간 기준 갱신 표시
kst_now = get_kst_now()
st.caption(f"🔄 마지막 업데이트: {kst_now.strftime('%H:%M:%S')}")

# 혼잡 안내 메시지 (사용자 요청 반영)
st.markdown("""
    <div class="alert-box">
        <strong>⚠️ 주차장 혼잡 안내</strong><br>
        현재 P1, P2 여객주차장은 매우 혼잡하거나 만차인 경우가 많습니다. 
        비교적 여유로운 <strong>P3 여객(화물) 주차장</strong> 이용을 적극 권장합니다.
    </div>
    """, unsafe_allow_html=True)

items = get_parking_data()
if items:
    for item in items:
        name = item.findtext('parkingAirportCodeName')
        # P3 명칭 보정
        display_name = "P3 여객(화물) 주차장" if "P3" in name else name
        stay = int(item.findtext('parkingIstay', 0))
        total = int(item.findtext('parkingFullSpace', 0))
        avail = max(0, total - stay)
        
        color = "#EF4444" if avail <= 5 else "#005596" # 5대 이하일 때 빨간색 표시
        avail_text = "만차" if avail == 0 else f"{avail:,}대 여유"
        
        st.markdown(f'''
            <div class="status-card">
                <span class="status-name">{display_name}</span>
                <span style="color: {color}; font-weight: bold;">{avail_text}</span>
            </div>
        ''', unsafe_allow_html=True)
else:
    st.warning("데이터를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.")

# --- 요금 계산기 UI ---
st.divider()
st.subheader("💰 요금 계산기")
p_lot = st.selectbox("주차장 선택", ["P1, P2 여객주차장", "P3 여객(화물)주차장"])
c_size = st.radio("차종", ["소형", "대형"], horizontal=True)
disc = st.selectbox("할인 대상", ["일반", "국가유공자(상이)", "장애인차량", "저공해 3종", "저공해 1,2종", "경차", "다자녀"])

col1, col2 = st.columns(2)
in_d = col1.date_input("입차일", kst_now.date())
in_t = col2.time_input("입차시간", time(11, 0))
out_d = col1.date_input("출차일", kst_now.date() + timedelta(days=1))
out_t = col2.time_input("출차시간", time(11, 0))

start = datetime.combine(in_d, in_t)
end = datetime.combine(out_d, out_t)

if start < end:
    total_fee = calculate_kims_fee_pro(start, end, c_size, disc, p_lot)
    duration = end - start
    st.markdown(f'''
        <div class="fee-container">
            <div style="font-size: 0.9rem; opacity: 0.9;">예상 주차 요금</div>
            <div style="font-size: 2.2rem; font-weight: 800;">{total_fee:,}원</div>
            <div style="font-size: 0.8rem; opacity: 0.8;">{duration.days}일 {duration.seconds // 3600}시간 {(duration.seconds % 3600) // 60}분 주차</div>
        </div>
    ''', unsafe_allow_html=True)
else:
    st.error("출차 시간이 입차 시간보다 빨라야 합니다.")
