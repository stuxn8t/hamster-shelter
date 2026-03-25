import os
import requests
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

try:
    API_KEY = st.secrets["API_KEY"]
except Exception:
    API_KEY = os.environ.get("API_KEY", "")
BASE_URL = "http://apis.data.go.kr/1543061/abandonmentPublicService_v2"

st.set_page_config(
    page_title="유기 햄스터 보호 현황",
    page_icon="🐹",
    layout="wide",
)

# ==========================================
# API 호출 함수
# ==========================================

def get_sido_list():
    url = f"{BASE_URL}/sido_v2"
    params = {"serviceKey": API_KEY, "numOfRows": 100, "_type": "json"}
    try:
        r = requests.get(url, params=params, timeout=10)
        items = r.json().get("response", {}).get("body", {}).get("items", {}).get("item", [])
        return items if isinstance(items, list) else [items]
    except Exception:
        return []

def get_sigungu_list(sido_code):
    url = f"{BASE_URL}/sigungu_v2"
    params = {"serviceKey": API_KEY, "upr_cd": sido_code, "numOfRows": 100, "_type": "json"}
    try:
        r = requests.get(url, params=params, timeout=10)
        items = r.json().get("response", {}).get("body", {}).get("items", {}).get("item", [])
        return items if isinstance(items, list) else [items]
    except Exception:
        return []

def get_abandoned_hamsters(sido_code="", sigungu_code="", state="", page=1, num_of_rows=20):
    url = f"{BASE_URL}/abandonmentPublic_v2"
    params = {
        "serviceKey": API_KEY,
        "upkind": "429900",
        "upr_cd": sido_code,
        "org_cd": sigungu_code,
        "state": state,
        "pageNo": page,
        "numOfRows": num_of_rows,
        "_type": "json",
    }
    params = {k: v for k, v in params.items() if v}
    try:
        r = requests.get(url, params=params, timeout=10)
        body = r.json().get("response", {}).get("body", {})
        total_count = int(body.get("totalCount", 0))
        items = body.get("items", {}).get("item", [])
        if isinstance(items, dict):
            items = [items]
        if not isinstance(items, list):
            items = []
        return items, total_count
    except Exception:
        return [], 0


# ==========================================
# CSS
# ==========================================
st.markdown("""
<style>
.card {
    background: #fff;
    border-radius: 12px;
    padding: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    margin-bottom: 16px;
    height: 100%;
}
.card img {
    width: 100%;
    border-radius: 8px;
    object-fit: cover;
    height: 180px;
}
.card-name {
    font-size: 1rem;
    font-weight: 700;
    margin-top: 8px;
    color: #1E293B;
}
.card-info {
    font-size: 0.82rem;
    color: #64748B;
    margin-top: 4px;
    line-height: 1.5;
}
.badge-protect {
    background: #DBEAFE;
    color: #1D4ED8;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 700;
}
.badge-done {
    background: #D1FAE5;
    color: #065F46;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 700;
}
.badge-etc {
    background: #F1F5F9;
    color: #475569;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 헤더
# ==========================================
st.markdown("# 🐹 유기 햄스터 보호 현황")
st.caption("전국 보호소의 유기 햄스터 공고를 한곳에서 확인하세요. 데이터 출처: 농림축산식품부 공공데이터포털")
st.divider()

# ==========================================
# 필터
# ==========================================
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    sido_list = get_sido_list()
    sido_options = {"전체": ""}
    for item in sido_list:
        name = item.get("orgNm") or item.get("sidonm") or item.get("name", "")
        code = item.get("orgCd") or item.get("sidoCd") or item.get("code", "")
        if name and code:
            sido_options[name] = code
    selected_sido_name = st.selectbox("시도", list(sido_options.keys()))
    selected_sido_code = sido_options[selected_sido_name]

with col2:
    if selected_sido_code:
        sigungu_list = get_sigungu_list(selected_sido_code)
        sigungu_options = {"전체": ""}
        for item in sigungu_list:
            name = item.get("orgNm") or item.get("sigungunm") or item.get("name", "")
            code = item.get("orgCd") or item.get("sigunguCd") or item.get("code", "")
            if name and code:
                sigungu_options[name] = code
    else:
        sigungu_options = {"전체": ""}
    selected_sigungu_name = st.selectbox("시군구", list(sigungu_options.keys()))
    selected_sigungu_code = sigungu_options[selected_sigungu_name]

with col3:
    state_options = {"전체": "", "보호중": "protect", "입양완료": "complete", "기타": "etc"}
    selected_state_name = st.selectbox("상태", list(state_options.keys()))
    selected_state = state_options[selected_state_name]

st.divider()

# ==========================================
# 데이터 로드
# ==========================================
with st.spinner("🐹 유기 햄스터 공고를 불러오는 중..."):
    animals, total = get_abandoned_hamsters(
        sido_code=selected_sido_code,
        sigungu_code=selected_sigungu_code,
        state=selected_state,
    )

if not animals:
    st.markdown("""
<div style="text-align:center;padding:80px 20px;color:#94A3B8">
  <div style="font-size:60px">🐹</div>
  <div style="font-size:1.1rem;margin-top:16px;font-weight:600">조건에 맞는 유기 햄스터가 없습니다</div>
  <div style="font-size:0.85rem;margin-top:8px">필터를 변경해보세요.</div>
</div>""", unsafe_allow_html=True)
    st.stop()

st.markdown(f"**총 {total}건** 중 {len(animals)}건 표시")

# ==========================================
# 카드 목록
# ==========================================
COLS = 4
rows = [animals[i:i+COLS] for i in range(0, len(animals), COLS)]

STATE_BADGE = {
    "protect": '<span class="badge-protect">보호중</span>',
    "complete": '<span class="badge-done">입양완료</span>',
    "etc": '<span class="badge-etc">기타</span>',
}

for row in rows:
    cols = st.columns(COLS)
    for col, animal in zip(cols, row):
        with col:
            img_url = animal.get("popfile", "").replace("http://", "https://")
            kind_nm = animal.get("kindNm", "햄스터")
            notice_no = animal.get("noticeNo", "")
            sex = {"M": "수컷", "F": "암컷", "Q": "미상"}.get(animal.get("sexCd", "Q"), "미상")
            age = animal.get("age", "미상")
            shelter = animal.get("careNm", "")
            org = animal.get("orgNm", "")
            notice_edt = animal.get("noticeEdt", "")
            state = animal.get("processState", "")
            color = animal.get("colorCd", "")
            weight = animal.get("weight", "")
            feature = animal.get("specialMark", "")
            badge = STATE_BADGE.get(
                "protect" if "보호" in state else
                "complete" if "입양" in state or "종료" in state else "etc",
                '<span class="badge-etc">기타</span>'
            )
            notice_edt_fmt = f"{notice_edt[:4]}-{notice_edt[4:6]}-{notice_edt[6:]}" if len(notice_edt) == 8 else notice_edt

            if img_url:
                try:
                    st.image(img_url, use_container_width=True)
                except Exception:
                    st.markdown('<div style="height:180px;background:#F1F5F9;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:2rem">🐹</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="height:180px;background:#F1F5F9;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:2rem">🐹</div>', unsafe_allow_html=True)

            st.markdown(f"""
<div class="card">
  <div class="card-name">{kind_nm} {badge}</div>
  <div class="card-info">
    📋 {notice_no}<br>
    ⚥ {sex} | 🎂 {age} | ⚖️ {weight}<br>
    🎨 {color}<br>
    🏠 {shelter}<br>
    📍 {org}<br>
    📅 공고 마감: {notice_edt_fmt}<br>
    💬 {feature}<br>
    🖼️ {img_url}
  </div>
</div>""", unsafe_allow_html=True)
