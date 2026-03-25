import os
import requests
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime, date

load_dotenv()

try:
    API_KEY = st.secrets["API_KEY"]
except Exception:
    API_KEY = os.environ.get("API_KEY", "")
BASE_URL = "http://apis.data.go.kr/1543061/abandonmentPublicService_v2"

st.set_page_config(
    page_title="유기 기타축종 보호 현황",
    page_icon="🐹",
    layout="wide",
)

# ==========================================
# API 호출 함수
# ==========================================

@st.cache_data(ttl=3600)
def get_sido_list():
    url = f"{BASE_URL}/sido_v2"
    params = {"serviceKey": API_KEY, "numOfRows": 100, "_type": "json"}
    try:
        r = requests.get(url, params=params, timeout=10)
        items = r.json().get("response", {}).get("body", {}).get("items", {}).get("item", [])
        return items if isinstance(items, list) else [items]
    except Exception:
        return []

@st.cache_data(ttl=3600)
def get_sigungu_list(sido_code):
    url = f"{BASE_URL}/sigungu_v2"
    params = {"serviceKey": API_KEY, "upr_cd": sido_code, "numOfRows": 100, "_type": "json"}
    try:
        r = requests.get(url, params=params, timeout=10)
        items = r.json().get("response", {}).get("body", {}).get("items", {}).get("item", [])
        return items if isinstance(items, list) else [items]
    except Exception:
        return []

def get_all_animals(sido_code="", sigungu_code=""):
    url = f"{BASE_URL}/abandonmentPublic_v2"
    base_params = {
        "serviceKey": API_KEY,
        "upkind": "429900",
        "upr_cd": sido_code,
        "org_cd": sigungu_code,
        "numOfRows": 100,
        "_type": "json",
    }
    base_params = {k: v for k, v in base_params.items() if v}

    # 1페이지로 totalCount 먼저 확인
    try:
        r = requests.get(url, params={**base_params, "pageNo": 1}, timeout=15)
        body = r.json().get("response", {}).get("body", {})
        total_count = int(body.get("totalCount", 0))
        items = body.get("items", {}).get("item", [])
        if isinstance(items, dict):
            items = [items]
        if not isinstance(items, list):
            items = []
    except Exception:
        return [], datetime.now()

    all_items = list(items)
    total_pages = -(-total_count // 100)

    if total_pages > 1:
        progress = st.progress(1 / total_pages, text=f"데이터 로딩 중... (1/{total_pages})")
        for page in range(2, total_pages + 1):
            try:
                r = requests.get(url, params={**base_params, "pageNo": page}, timeout=15)
                body = r.json().get("response", {}).get("body", {})
                items = body.get("items", {}).get("item", [])
                if isinstance(items, dict):
                    items = [items]
                if isinstance(items, list):
                    all_items.extend(items)
                progress.progress(page / total_pages, text=f"데이터 로딩 중... ({page}/{total_pages})")
            except Exception:
                break
        progress.empty()

    return all_items, datetime.now()

def days_until(date_str):
    try:
        d = date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:]))
        return (d - date.today()).days
    except Exception:
        return None

# ==========================================
# CSS
# ==========================================
st.markdown("""
<style>
.card {
    background: #fff;
    padding: 4px 4px 8px 4px;
    height: 100%;
}
.card-placeholder {
    height: 240px;
    background: #F1F5F9;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2rem;
    margin-bottom: 8px;
}
[data-testid="stImage"] img,
[data-testid="stImage"] > img,
.stImage img {
    height: 240px !important;
    object-fit: cover !important;
    border-radius: 8px !important;
}
.card-name {
    font-size: 1rem;
    font-weight: 700;
    margin-top: 10px;
    margin-bottom: 6px;
    color: #0F172A;
}
.card-info {
    font-size: 0.83rem;
    color: #334155;
    margin-top: 0;
    line-height: 1.8;
}
.card-divider {
    border: none;
    border-top: 1px solid #F1F5F9;
    margin: 6px 0;
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
.deadline-urgent {
    color: #DC2626;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 헤더
# ==========================================
st.markdown("# 🐹 유기 기타축종 보호 현황")
st.caption("전국 보호소의 유기동물 공고를 한곳에서 확인하세요. 데이터 출처: 농림축산식품부 공공데이터포털")
st.divider()

# ==========================================
# 필터
# ==========================================
col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 0.4])

with col1:
    sido_list = get_sido_list()
    sido_options = {"전체": ""}
    for item in sido_list:
        name = item.get("orgdownNm") or item.get("orgNm") or item.get("sidonm") or item.get("name", "")
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
            name = item.get("orgdownNm") or item.get("orgNm") or item.get("sigungunm") or item.get("name", "")
            code = item.get("orgCd") or item.get("sigunguCd") or item.get("code", "")
            if name and code and code != selected_sido_code and name != selected_sido_name and name != "가정보호":
                sigungu_options[name] = code
        if len(selected_sido_code) >= 3:
            sigungu_options["가정보호"] = selected_sido_code[:3] + "9999"
    else:
        sigungu_options = {"전체": ""}
    selected_sigungu_name = st.selectbox("시군구", list(sigungu_options.keys()))
    selected_sigungu_code = sigungu_options[selected_sigungu_name]

with col3:
    state_options = {"보호중": "protect", "전체": "", "입양완료": "complete", "기타": "etc"}
    selected_state_name = st.selectbox("상태", list(state_options.keys()))
    selected_state = state_options[selected_state_name]

with col4:
    search_query = st.text_input("동물 검색", placeholder="예: 햄스터, 거북이")

with col5:
    st.markdown("<div style='margin-top:28px'>", unsafe_allow_html=True)
    if st.button("초기화", use_container_width=True):
        st.session_state.page = 1
        st.session_state.filter_key = ""
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# ==========================================
# 페이지 상태
# ==========================================
PER_PAGE = 20
if "page" not in st.session_state:
    st.session_state.page = 1

filter_key = f"{selected_sido_code}_{selected_sigungu_code}_{selected_state}_{search_query}"
if st.session_state.get("filter_key") != filter_key:
    st.session_state.page = 1
    st.session_state.filter_key = filter_key

# ==========================================
# 데이터 로드
# ==========================================
cache_key = f"{selected_sido_code}_{selected_sigungu_code}"
if st.session_state.get("cache_key") != cache_key or "all_animals_data" not in st.session_state:
    with st.spinner("🐹 공고를 불러오는 중..."):
        all_animals, fetched_at = get_all_animals(
            sido_code=selected_sido_code,
            sigungu_code=selected_sigungu_code,
        )
    st.session_state.all_animals_data = all_animals
    st.session_state.fetched_at = fetched_at
    st.session_state.cache_key = cache_key
else:
    all_animals = st.session_state.all_animals_data

# 상태 필터링 (로컬)
if selected_state == "protect":
    all_animals = [a for a in all_animals if "보호" in a.get("processState", "")]
elif selected_state == "complete":
    all_animals = [a for a in all_animals if "입양" in a.get("processState", "") or "종료" in a.get("processState", "")]
elif selected_state == "etc":
    all_animals = [a for a in all_animals if "보호" not in a.get("processState", "") and "입양" not in a.get("processState", "") and "종료" not in a.get("processState", "")]

# 검색어 필터링 (로컬)
if search_query:
    query = search_query.strip().lower()
    all_animals = [
        a for a in all_animals
        if query in (a.get("kindFullNm", "") + a.get("kindNm", "") + a.get("colorCd", "") + a.get("specialMark", "")).lower()
    ]

total = len(all_animals)
start = (st.session_state.page - 1) * PER_PAGE
animals = all_animals[start:start + PER_PAGE]

if not animals:
    st.markdown("""
<div style="text-align:center;padding:80px 20px;color:#94A3B8">
  <div style="font-size:60px">🐹</div>
  <div style="font-size:1.1rem;margin-top:16px;font-weight:600">조건에 맞는 동물이 없습니다</div>
  <div style="font-size:0.85rem;margin-top:8px">필터를 변경해보세요.</div>
</div>""", unsafe_allow_html=True)
    st.stop()

total_pages = max(1, -(-total // PER_PAGE))
fetched_at = st.session_state.get("fetched_at")
fetched_str = fetched_at.strftime("%Y-%m-%d %H:%M") if fetched_at else ""
st.markdown(f"**총 {total}건** | {st.session_state.page} / {total_pages} 페이지 &nbsp;&nbsp; <span style='color:#94A3B8;font-size:0.8rem'>🕐 {fetched_str} 기준</span>", unsafe_allow_html=True)

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
          with st.container(border=True):
            img_url = animal.get("popfile1", "") or animal.get("popfile2", "")
            kind_nm = animal.get("kindNm", "기타축종")
            notice_no = animal.get("noticeNo", "")
            sex = {"M": "수컷", "F": "암컷", "Q": "미상"}.get(animal.get("sexCd", "Q"), "미상")
            age = animal.get("age", "미상")
            shelter = animal.get("careNm", "")
            care_tel = animal.get("careTel", "")
            org = animal.get("orgNm", "")
            notice_edt = animal.get("noticeEdt", "")
            state = animal.get("processState", "")
            color = animal.get("colorCd", "")
            weight = animal.get("weight", "")
            feature = animal.get("specialMark", "")
            happen_place = animal.get("happenPlace", "")
            desertion_no = animal.get("desertionNo", "")
            detail_url = f"https://www.animal.go.kr/front/awtis/public/publicDtl.do?desertionNo={desertion_no}" if desertion_no else ""
            badge = STATE_BADGE.get(
                "protect" if "보호" in state else
                "complete" if "입양" in state or "종료" in state else "etc",
                '<span class="badge-etc">기타</span>'
            )
            notice_edt_fmt = f"{notice_edt[:4]}-{notice_edt[4:6]}-{notice_edt[6:]}" if len(notice_edt) == 8 else notice_edt
            happen_dt = animal.get("happenDt", "")
            happen_dt_fmt = f"{happen_dt[:4]}-{happen_dt[4:6]}-{happen_dt[6:]}" if len(happen_dt) == 8 else ""

            # 마감 임박 계산
            d_day = days_until(notice_edt) if len(notice_edt) == 8 else None
            if d_day is not None and d_day <= 3:
                deadline_html = f'📅 마감: <span class="deadline-urgent">{notice_edt_fmt} (D{d_day:+d})</span><br>'
            else:
                deadline_html = f'📅 마감: <b>{notice_edt_fmt}</b><br>'

            if img_url:
                st.image(img_url, use_container_width=True)
            else:
                st.markdown('<div class="card-placeholder">🐹</div>', unsafe_allow_html=True)

            card_link_open = f'<a href="{detail_url}" target="_blank" style="text-decoration:none;color:inherit;">' if detail_url else ""
            card_link_close = "</a>" if detail_url else ""

            st.markdown(f"""
{card_link_open}<div class="card">
  <div class="card-name">{kind_nm} {badge}</div>
  <div class="card-info">
    <span style="color:#94A3B8;font-size:0.75rem">📋 {notice_no}</span><br>
    <hr class="card-divider">
    ⚥ <b>{sex}</b> &nbsp;|&nbsp; 🎂 <b>{age}</b> &nbsp;|&nbsp; ⚖️ <b>{weight}</b><br>
    🎨 {color}<br>
    <hr class="card-divider">
    🏠 <b>{shelter}</b><br>
    {f"📞 {care_tel}<br>" if care_tel else ""}📍 {org}<br>
    {f"📌 발견: {happen_place}<br>" if happen_place else ""}
    <hr class="card-divider">
    {f"🚑 구조일: <b>{happen_dt_fmt}</b><br>" if happen_dt_fmt else ""}{deadline_html}💬 <span style="color:#475569">{feature}</span>
  </div>
</div>{card_link_close}""", unsafe_allow_html=True)

# ==========================================
# 페이지 버튼
# ==========================================
st.divider()
pcol1, pcol2, pcol3 = st.columns([1, 2, 1])
with pcol1:
    if st.session_state.page > 1:
        if st.button("◀ 이전"):
            st.session_state.page -= 1
            st.rerun()
with pcol2:
    st.markdown(f"<div style='text-align:center;padding-top:6px'>{st.session_state.page} / {total_pages}</div>", unsafe_allow_html=True)
with pcol3:
    if st.session_state.page < total_pages:
        if st.button("다음 ▶"):
            st.session_state.page += 1
            st.rerun()
