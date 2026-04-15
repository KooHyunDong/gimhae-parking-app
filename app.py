import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, time
from streamlit_autorefresh import st_autorefresh

# 1. 자동 새로고침 (60초 주기)
st_autorefresh(interval=60000, key="datarefresh")

# 2. 데이터 수집 로직 (User-Agent 포함)
def get_parking_data():
    DATA_API_KEY = 'a50c28a4672e470d594bae9af0dd980b37474e12b353b76e13fb1becba418ab1'
    url = f"http://openapi.airport.co.kr/service/rest/AirportParking/airportparkingRT?serviceKey={DATA_API_KEY}&schAirportCode=PUS"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        root = ET.fromstring(response.text)
        return root.findall('.//item')
    except: return []

# 3. 요금 계산 로직 (생략 없이 유지)
def calculate_kims_fee_pro(start_dt, end_dt, car_size, discount_type, parking_lot):
    if start_dt >= end_dt: return 0
    total_fee, current_dt = 0, start_dt
    while current_dt < end_dt:
        next_dt = min(current_dt + timedelta(days=1), end_dt)
        duration_min = int((next_dt - current_dt).total_seconds() / 60)
        is_weekend = current_dt.weekday() >= 4 
        if car_size == "소형":
            base_fee = 900
            if "P3" in parking_lot: daily_limit = 10000 if is_weekend else 7000
            else: daily_limit = 15000 if is_weekend else 10000
            fee = base_fee if duration_min <= 30 else base_fee + ((duration_min - 30) // 10) * 300
            total_fee += min(fee, daily_limit)
        else:
            base_fee = 1200
            fee = base_fee if duration_min <= 30 else base_fee + ((duration_min - 30) // 10) * 400
            total_fee += fee 
        current_dt = next_dt
    if discount_type in ["국가유공자(상이)", "장애인차량", "저공해 1,2종", "경차", "다자녀"]:
        total_fee *= 0.5
    elif discount_type == "저공해 3종":
        total_fee *= 0.8
    return int(total_fee)

# 4. 스타일 설정 (모바일 초밀착 레이아웃)
st.set_page_config(page_title="김해공항 주차", layout="centered")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
    * { font-family: 'Noto Sans KR', sans-serif; }
    
    /* 상단 여백 제거 */
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
    [data-testid="stHeader"] { display: none; }
    
    .stApp { background-color: #F9FAFB; }
    
    /* 제목 크기 최적화 */
    .main-title { font-size: 1.6rem; font-weight: 800; color: #111827; margin-bottom: 5px; }
    .header-line { border-top: 3px solid #005596; margin-bottom: 10px; }
    
    /* 카드 높이 축소 및 폰트 조정 */
    .status-card { 
        background: white; border: 1px solid #E5E7EB; 
        padding: 12px 18px; border-radius: 10px; 
        margin-bottom: 6px; display: flex; 
        justify-content: space-between; align-items: center;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .status-name { font-weight: 700; font-size: 0.95rem; color: #374151; }
    .status-avail { font-weight: 700; font-size: 1.1rem; }
    
    /* 요금 결과창 */
    .fee-container { background: #b00b2d; color: white; padding: 20px 10px; border-radius: 12px; text-align: center; margin-top: 10px; }
    .fee-value { font-size: 2.4rem; font-weight: 800; }
    .fee-label { font-size: 0.85rem; opacity: 0.8; }
    
    /* 입력 위젯 간격 축소 */
    .stSelectbox, .stRadio { margin-bottom: -10px; }
    </style>
    """, unsafe_allow_html=True)

# ----------------- UI -----------------
st.markdown('<div class="main-title">🛫 김해공항 주차 현황</div>', unsafe_allow_html=True)
st.markdown('<div class="header-line"></div>', unsafe_allow_html=True)
st.caption(f"🔄 갱신: {datetime.now().strftime('%H:%M:%S')}")

items = get_parking_data()
p12_avail = 0
p3_avail = 0

if items:
    for item in items:
        name = item.findtext('parkingAirportCodeName')
        display_name = name + " 주차장" if "P3" in name else name
        avail = max(0, int(item.findtext('parkingFullSpace', 0)) - int(item.findtext('parkingIstay', 0)))
        
        if avail == 0:
            avail_text, avail_color = "만차", "#EF4444"
        else:
            avail_text, avail_color = f"{avail:,}대 여유", "#005596"
        
        if "P1" in name or "P2" in name: p12_avail += avail
        if "P3" in name: p3_avail = avail
        
        st.markdown(f'<div class="status-card"><span class="status-name">{display_name}</span><span class="status-avail" style="color: {avail_color};">{avail_text}</span></div>', unsafe_allow_html=True)

st.markdown("<div style='margin: 15px 0;'></div>", unsafe_allow_html=True)
st.markdown("### 💰 요금 계산기")

p_lot = st.selectbox("주차장", ["P1, P2 여객주차장", "P3 여객(화물)주차장"])
car_size = st.radio("차량 크기", ["소형", "대형"], horizontal=True)
discount = st.selectbox("할인 항목", ["일반", "국가유공자(상이)", "장애인차량", "저공해 3종", "저공해 1,2종", "경차", "다자녀"])

# 날짜/시간 선택을 더 콤팩트하게
c1, c2 = st.columns(2)
in_d = c1.date_input("입차 날짜")
in_t = c2.time_input("입차 시간", time(11, 0))

c3, c4 = st.columns(2)
out_d = c3.date_input("출차 날짜", value=datetime.now()+timedelta(days=1))
out_t = c4.time_input("출차 시간", time(11, 0))

start = datetime.combine(in_d, in_t)
end = datetime.combine(out_d, out_t)

if start < end:
    fee = calculate_kims_fee_pro(start, end, car_size, discount, p_lot)
    dur = end - start
    st.markdown(f"""
        <div class="fee-container">
            <div class="fee-value">{fee:,}원</div>
            <div class="fee-label">시간: {dur.days}일 {dur.seconds // 3600}시간 {(dur.seconds % 3600) // 60}분</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.write("")
    if p12_avail == 0 and p3_avail == 0:
        st.warning("⚠️ 모든 주차장 만차! 대중교통 권장")
    elif p12_avail == 0:
        st.info(f"💡 P3 주차장({p3_avail}대 가능) 이용 추천")
    else:
        st.success("✅ P1 주차장 이용이 편리합니다.")
