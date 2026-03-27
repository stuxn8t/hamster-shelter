import os
import html as html_lib
import requests
import streamlit as st
from dotenv import load_dotenv
from datetime import datetime, date
import xml.etree.ElementTree as ET
import streamlit.components.v1 as components

load_dotenv()

try:
    API_KEY = st.secrets["API_KEY"]
except Exception:
    API_KEY = os.environ.get("API_KEY", "")

try:
    DAEJEON_KEY = st.secrets["DAEJEON_KEY"]
except Exception:
    DAEJEON_KEY = os.environ.get("DAEJEON_KEY", "")

BASE_URL = "http://apis.data.go.kr/1543061/abandonmentPublicService_v2"
DAEJEON_BASE = "http://apis.data.go.kr/6300000/animalDaejeonService"

DAEJEON_GU = {"1": "동구", "2": "중구", "3": "서구", "4": "유성구", "5": "대덕구"}
DAEJEON_STATUS = {
    "1": "보호중(공고중)", "2": "보호중(입양가능)", "3": "보호중(입양예정)",
    "4": "입양완료", "5": "자연사", "6": "안락사", "7": "주인반환",
    "8": "보호중(임시보호)", "9": "입양불가", "10": "방사",
    "11": "주민참여", "12": "보호중(입원중)",
}

UPKIND_DOG = "417000"
UPKIND_CAT = "422400"
UPKIND_ETC = "429900"

SPECIES_OPTIONS = ["전체", "🐹 햄스터", "🐰 토끼", "🐱 고양이", "🐶 강아지", "🐢 거북이", "🦔 고슴도치", "🐦 새", "기타"]
SPECIES_KEYWORDS = {
    "🐹 햄스터": ["햄스터"],
    "🐰 토끼": ["토끼"],
    "🐢 거북이": ["거북"],
    "🦔 고슴도치": ["고슴도치"],
    "🐦 새": ["앵무", "잉꼬", "금조", "사랑새", "카나리아"],
}
KNOWN_KEYWORDS = [kw for kws in SPECIES_KEYWORDS.values() for kw in kws]


def get_animal_emoji(kind_nm, upkind=""):
    if upkind == UPKIND_DOG: return "🐶"
    if upkind == UPKIND_CAT: return "🐱"
    if "햄스터" in kind_nm: return "🐹"
    if "토끼" in kind_nm: return "🐰"
    if "거북" in kind_nm: return "🐢"
    if "고슴도치" in kind_nm: return "🦔"
    if any(k in kind_nm for k in ["앵무", "잉꼬", "사랑새", "금조"]): return "🦜"
    if "페렛" in kind_nm: return "🦡"
    if "뱀" in kind_nm: return "🐍"
    if "도마뱀" in kind_nm or "이구아나" in kind_nm: return "🦎"
    if "기니" in kind_nm: return "🐭"
    if "다람쥐" in kind_nm: return "🐿️"
    return "🐾"


def matches_species(kind_nm, selected, upkind=""):
    if selected == "전체":
        return True
    if selected == "🐶 강아지":
        return upkind == UPKIND_DOG
    if selected == "🐱 고양이":
        return upkind == UPKIND_CAT
    if upkind in (UPKIND_DOG, UPKIND_CAT):
        return False
    if selected == "기타":
        return not any(kw in kind_nm for kw in KNOWN_KEYWORDS)
    keywords = SPECIES_KEYWORDS.get(selected, [])
    return any(kw in kind_nm for kw in keywords)


st.set_page_config(
    page_title="유기 동물 입양 공고",
    page_icon="🐹",
    layout="wide",
)

# ==========================================
# API 호출 함수
# ==========================================

@st.cache_data(ttl=86400)
def get_sido_list():
    url = f"{BASE_URL}/sido_v2"
    params = {"serviceKey": API_KEY, "numOfRows": 100, "_type": "json"}
    try:
        r = requests.get(url, params=params, timeout=10)
        items = r.json().get("response", {}).get("body", {}).get("items", {}).get("item", [])
        return items if isinstance(items, list) else [items]
    except Exception:
        return []

@st.cache_data(ttl=86400)
def get_sigungu_list(sido_code):
    url = f"{BASE_URL}/sigungu_v2"
    params = {"serviceKey": API_KEY, "upr_cd": sido_code, "numOfRows": 100, "_type": "json"}
    try:
        r = requests.get(url, params=params, timeout=10)
        items = r.json().get("response", {}).get("body", {}).get("items", {}).get("item", [])
        return items if isinstance(items, list) else [items]
    except Exception:
        return []

@st.cache_data(ttl=7200, show_spinner=False)
def _fetch_animal_page(sido_code, sigungu_code, upkind, page):
    """단일 페이지 fetch — 캐시됨 (2시간)"""
    url = f"{BASE_URL}/abandonmentPublic_v2"
    params = {k: v for k, v in {
        "serviceKey": API_KEY,
        "upkind": upkind,
        "upr_cd": sido_code,
        "org_cd": sigungu_code,
        "numOfRows": 100,
        "_type": "json",
        "pageNo": page,
    }.items() if v}
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json(), False
    except Exception:
        return {}, True

def get_all_animals(sido_code="", sigungu_code="", upkind="429900", label="데이터"):
    data, err = _fetch_animal_page(sido_code, sigungu_code, upkind, 1)
    if err:
        return [], datetime.now(), True

    body = data.get("response", {}).get("body", {})
    total_count = int(body.get("totalCount", 0))
    items = body.get("items", {}).get("item", [])
    if isinstance(items, dict): items = [items]
    if not isinstance(items, list): items = []

    all_items = list(items)
    total_pages = -(-total_count // 100)

    if total_pages > 1:
        progress = st.progress(1 / total_pages, text=f"{label} 로딩 중... (1/{total_pages})")
        for page in range(2, total_pages + 1):
            data, err = _fetch_animal_page(sido_code, sigungu_code, upkind, page)
            if not err:
                body = data.get("response", {}).get("body", {})
                items = body.get("items", {}).get("item", [])
                if isinstance(items, dict): items = [items]
                if isinstance(items, list): all_items.extend(items)
            progress.progress(page / total_pages, text=f"{label} 로딩 중... ({page}/{total_pages})")
        progress.empty()

    return all_items, datetime.now(), False

@st.cache_data(ttl=7200, show_spinner=False)
def get_daejeon_animals():
    all_items = []
    page = 1
    while True:
        try:
            r = requests.get(
                f"{DAEJEON_BASE}/animalDaejeonList",
                params={"serviceKey": DAEJEON_KEY, "searchCondition": "3", "numOfRows": 100, "pageNo": page},
                timeout=15,
            )
            root = ET.fromstring(r.text)
            if root.findtext(".//returnCode") != "00":
                break
            total_page = int(root.findtext(".//totalPage", "1") or 1)
            for item in root.findall(".//items"):
                def t(tag, el=item): return el.findtext(tag, "") or ""
                gu_cd = t("gu")
                file_path = t("filePath")
                animal_seq = t("animalSeq")
                all_items.append({
                    "kindNm": t("species"),
                    "noticeNo": t("regId"),
                    "desertionNo": "",
                    "processState": DAEJEON_STATUS.get(t("adoptionStatusCd"), ""),
                    "sexCd": {"1": "F", "2": "M"}.get(t("gender"), "Q"),
                    "age": t("age"),
                    "colorCd": t("hairColor"),
                    "weight": t("weight"),
                    "specialMark": t("memo"),
                    "happenPlace": t("foundPlace"),
                    "happenDt": t("rescueDate").replace("-", ""),
                    "noticeEdt": "",
                    "popfile1": f"http://www.daejeon.go.kr/{file_path}" if file_path else "",
                    "popfile2": "",
                    "careNm": f"대전 {DAEJEON_GU.get(gu_cd, '')} 동물보호센터",
                    "careTel": "042-270-7239",
                    "orgNm": "대전광역시",
                    "_source": "daejeon",
                    "_animalSeq": animal_seq,
                })
            if page >= total_page:
                break
            page += 1
        except Exception:
            break
    return all_items

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
/* ── 전체 배경 ── */
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {
    background: #FFF8F2 !important;
}
[data-testid="block-container"] {
    padding-top: 2rem !important;
}

/* ── 히어로 헤더 ── */
.hero {
    background: linear-gradient(135deg, #FFF3E0 0%, #FFF8F4 40%, #EEF4FF 100%);
    border: 1px solid #FFE0B2;
    border-radius: 20px;
    padding: 28px 36px 24px;
    margin-bottom: 8px;
}
.hero-title {
    font-size: 1.9rem;
    font-weight: 900;
    color: #1C1C2E;
    margin: 0 0 6px 0;
    letter-spacing: -0.5px;
}
.hero-sub {
    font-size: 0.88rem;
    color: #78716C;
    margin: 0;
    line-height: 1.5;
}
.hero-sources {
    display: inline-flex;
    gap: 6px;
    margin-top: 12px;
}
.source-tag-label {
    font-size: 0.7rem;
    color: #A8A29E;
    font-weight: 600;
    display: flex;
    align-items: center;
    margin-right: 2px;
}
.source-tag {
    font-size: 0.72rem;
    background: rgba(255,255,255,0.7);
    border: 1px solid #E5E0D8;
    color: #78716C;
    padding: 2px 10px;
    border-radius: 20px;
    font-weight: 600;
}

/* ── 통계 바 ── */
.stats-bar {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 16px;
    background: #FFFFFF;
    border: 1px solid #F0EDE8;
    border-radius: 12px;
    margin-bottom: 16px;
}
.stats-count {
    font-size: 0.92rem;
    font-weight: 700;
    color: #1C1C2E;
}
.stats-page {
    font-size: 0.82rem;
    color: #A8A29E;
}
.stats-dot {
    width: 4px; height: 4px;
    background: #D6D3D1;
    border-radius: 50%;
}
.stats-time {
    font-size: 0.76rem;
    color: #A8A29E;
    margin-left: auto;
}

/* ── 카드 컨테이너 override ── */
[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid #F0ECE7 !important;
    border-radius: 16px !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06) !important;
    overflow: hidden !important;
    transition: transform 0.18s ease, box-shadow 0.18s ease !important;
    background: #FFFFFF !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    transform: translateY(-4px) !important;
    box-shadow: 0 10px 28px rgba(0,0,0,0.12) !important;
    border-color: #FFD9B8 !important;
}

/* ── 카드 이미지 ── */
[data-testid="stImage"] img,
[data-testid="stImage"] > img,
.stImage img {
    height: 210px !important;
    object-fit: cover !important;
    border-radius: 0 !important;
    display: block !important;
}

/* ── 이미지 placeholder ── */
.card-placeholder {
    height: 210px;
    background: linear-gradient(135deg, #FFF3E0, #FFE8D6);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 3.8rem;
}

/* ── 카드 내부 ── */
.card-body {
    padding: 12px 14px 10px;
}
.card-top-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 4px;
}
.card-notice-no {
    font-size: 0.7rem;
    color: #B8B4AF;
    letter-spacing: 0.2px;
}
.card-title {
    font-size: 1.0rem;
    font-weight: 800;
    color: #1C1C2E;
    margin: 4px 0 8px;
    line-height: 1.3;
}
.card-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-bottom: 8px;
    min-height: 52px;
}
.chip {
    font-size: 0.72rem;
    font-weight: 600;
    background: #F5F4F2;
    color: #57534E;
    padding: 2px 9px;
    border-radius: 20px;
    white-space: nowrap;
}
.chip-color {
    background: #FFF7ED;
    color: #9A3412;
}
.card-divider {
    border: none;
    border-top: 1px solid #F5F0EB;
    margin: 7px 0;
}
.card-location {
    font-size: 0.78rem;
    color: #57534E;
    line-height: 1.6;
    min-height: 5.6em;
}
.card-location b { color: #1C1C2E; }
.card-date-row {
    font-size: 0.75rem;
    color: #78716C;
    line-height: 1.6;
    min-height: 3.2em;
}
.card-feature {
    font-size: 0.75rem;
    color: #78716C;
    background: #FAFAF8;
    border-radius: 8px;
    padding: 6px 10px;
    margin-top: 6px;
    line-height: 1.5;
    min-height: 3.0em;
}

/* ── 상태 배지 ── */
.badge-protect {
    background: #FFF1F2;
    color: #BE123C;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 700;
    border: 1px solid #FECDD3;
}
.badge-done {
    background: #F0FDF4;
    color: #166534;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 700;
    border: 1px solid #BBF7D0;
}
.badge-etc {
    background: #F5F4F2;
    color: #78716C;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 700;
    border: 1px solid #E7E5E4;
}
.badge-daejeon {
    background: #FFFBEB;
    color: #B45309;
    padding: 2px 8px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 700;
    border: 1px solid #FDE68A;
}

/* ── 빈 결과 ── */
.empty-state {
    text-align: center;
    padding: 80px 20px;
    color: #A8A29E;
}
.empty-state .icon { font-size: 56px; }
.empty-state .title { font-size: 1.05rem; font-weight: 700; margin-top: 14px; color: #78716C; }
.empty-state .sub { font-size: 0.83rem; margin-top: 6px; }

/* ── 특이사항 말줄임 ── */
.card-feature {
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

/* ── 모바일 반응형 ── */
@media (max-width: 768px) {
    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }
    [data-testid="stHorizontalBlock"] > [data-testid="column"] {
        flex: 0 0 calc(50% - 8px) !important;
        min-width: calc(50% - 8px) !important;
    }
    .hero { padding: 20px 20px 16px; }
    .hero-title { font-size: 1.5rem; }
}
@media (max-width: 480px) {
    [data-testid="stHorizontalBlock"] > [data-testid="column"] {
        flex: 0 0 100% !important;
        min-width: 100% !important;
    }
}
</style>
""", unsafe_allow_html=True)

# 초기화 플래그 처리 (위젯 생성 전에 적용)
if st.session_state.get("_do_reset"):
    st.session_state["f_sido"] = "전체"
    st.session_state["f_sigungu"] = "전체"
    st.session_state["f_state"] = "보호중"
    st.session_state["f_species"] = "전체"
    st.session_state.page = 1
    st.session_state.filter_key = ""
    st.session_state.page_history = {}
    del st.session_state["_do_reset"]

# ==========================================
# 헤더
# ==========================================
st.markdown("""
<div class="hero">
  <div class="hero-title">🐾 유기 동물 입양 공고</div>
  <div class="hero-sub">보호소의 작은 동물들이에요.<br>공고 기간이 지나면 입양 절차가 시작돼요. (공고 및 보호소마다 상이할 수 있어요)<br>새 가족이 필요해요.</div>
  <div class="hero-sources">
    <span class="source-tag-label">데이터 출처</span>
    <span class="source-tag">🏛️ 국가동물보호정보시스템</span>
    <span class="source-tag">🌆 대전광역시 유기동물공고현황</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 종류 필터 (pills)
# ==========================================
if "f_species" not in st.session_state:
    st.session_state["f_species"] = "전체"

try:
    selected_species = st.pills("동물 종류", SPECIES_OPTIONS, key="f_species")
except AttributeError:
    selected_species = st.radio("동물 종류", SPECIES_OPTIONS, horizontal=True, label_visibility="collapsed", key="f_species")

if selected_species is None:
    selected_species = "전체"

# ==========================================
# 필터
# ==========================================
col1, col2, col3, col4 = st.columns([1, 1, 0.8, 0.4])

with col1:
    sido_list = get_sido_list()
    sido_options = {"전체": ""}
    for item in sido_list:
        name = item.get("orgdownNm") or item.get("orgNm") or item.get("sidonm") or item.get("name", "")
        code = item.get("orgCd") or item.get("sidoCd") or item.get("code", "")
        if name and code:
            sido_options[name] = code
    selected_sido_name = st.selectbox("시도", list(sido_options.keys()), key="f_sido")
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
    selected_sigungu_name = st.selectbox("시군구", list(sigungu_options.keys()), key="f_sigungu")
    selected_sigungu_code = sigungu_options[selected_sigungu_name]

with col3:
    state_options = {"보호중": "protect", "전체": "", "입양완료": "complete", "기타": "etc"}
    selected_state_name = st.selectbox("상태", list(state_options.keys()), key="f_state")
    selected_state = state_options[selected_state_name]

with col4:
    st.markdown("<div style='margin-top:28px'>", unsafe_allow_html=True)
    if st.button("초기화", use_container_width=True):
        st.session_state["_do_reset"] = True
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

search_query = ""

st.divider()

# ==========================================
# 페이지 상태
# ==========================================
PER_PAGE = 12
if "page" not in st.session_state:
    st.session_state.page = 1

filter_key = f"{selected_sido_code}_{selected_sigungu_code}_{selected_state}_{selected_species}"
if st.session_state.get("filter_key") != filter_key:
    # 현재 페이지를 이전 필터 키에 저장
    prev_key = st.session_state.get("filter_key")
    if prev_key:
        if "page_history" not in st.session_state:
            st.session_state.page_history = {}
        st.session_state.page_history[prev_key] = st.session_state.get("page", 1)
    # 새 필터 키에 저장된 페이지가 있으면 복원, 없으면 1
    st.session_state.page = st.session_state.get("page_history", {}).get(filter_key, 1)
    st.session_state.filter_key = filter_key

# ==========================================
# 데이터 로드
# ==========================================
cache_key = f"{selected_sido_code}_{selected_sigungu_code}"
_do_scroll = st.session_state.get("_scroll_to_top", False)
if _do_scroll:
    st.session_state._scroll_to_top = False

if st.session_state.get("cache_key") != cache_key or "all_animals_data" not in st.session_state:
    all_animals = []
    fetched_at = datetime.now()
    fetch_errors = []

    for upkind_cd, label, emoji in [
        (UPKIND_ETC, "소동물", "🐹"),
        (UPKIND_CAT, "고양이", "🐱"),
        (UPKIND_DOG, "강아지", "🐶"),
    ]:
        with st.spinner(f"{emoji} {label} 공고를 불러오는 중..."):
            items, fetched_at, had_error = get_all_animals(
                sido_code=selected_sido_code,
                sigungu_code=selected_sigungu_code,
                upkind=upkind_cd,
                label=label,
            )
        if had_error:
            fetch_errors.append(f"{emoji} {label}")
        for a in items:
            a["_upkind"] = upkind_cd
        all_animals.extend(items)

    include_daejeon = selected_sido_name in ("전체", "대전광역시")
    if include_daejeon:
        try:
            daejeon_animals = get_daejeon_animals()
            national_notice_nos = {a.get("noticeNo", "") for a in all_animals}
            new_from_daejeon = [a for a in daejeon_animals if a["noticeNo"] not in national_notice_nos]
            for a in new_from_daejeon:
                a["_upkind"] = UPKIND_ETC
            all_animals = all_animals + new_from_daejeon
        except Exception:
            fetch_errors.append("🏠 대전 유기동물보호소")

    if fetch_errors:
        st.warning(f"⚠️ 일부 데이터를 불러오지 못했습니다: {', '.join(fetch_errors)}\n잠시 후 페이지를 새로고침해 주세요.")

    st.session_state.all_animals_data = all_animals
    st.session_state.fetched_at = fetched_at
    st.session_state.cache_key = cache_key
else:
    all_animals = st.session_state.all_animals_data

# 상태 필터링
if selected_state == "protect":
    all_animals = [a for a in all_animals if "보호" in a.get("processState", "")]
elif selected_state == "complete":
    all_animals = [a for a in all_animals if "입양" in a.get("processState", "") or "종료" in a.get("processState", "")]
elif selected_state == "etc":
    all_animals = [a for a in all_animals if "보호" not in a.get("processState", "") and "입양" not in a.get("processState", "") and "종료" not in a.get("processState", "")]

# 종류 필터링
if selected_species != "전체":
    all_animals = [a for a in all_animals if matches_species(
        a.get("kindNm", "") + a.get("kindFullNm", ""), selected_species, a.get("_upkind", "")
    )]

# 소동물 우선, 그 중 햄스터 최우선 정렬
def _sort_key(a):
    upkind = a.get("_upkind", "")
    kind = a.get("kindNm", "") + a.get("kindFullNm", "")
    if upkind == UPKIND_ETC and "햄스터" in kind: return 0
    if upkind == UPKIND_ETC: return 1
    if upkind == UPKIND_CAT: return 2
    return 3  # 개
all_animals = sorted(all_animals, key=_sort_key)

total = len(all_animals)
start = (st.session_state.page - 1) * PER_PAGE
animals = all_animals[start:start + PER_PAGE]

if not animals:
    st.markdown("""
<div class="empty-state">
  <div class="icon">🐾</div>
  <div class="title">조건에 맞는 동물이 없습니다</div>
  <div class="sub">필터를 변경하거나 초기화해보세요.</div>
</div>""", unsafe_allow_html=True)
    st.stop()

total_pages = max(1, -(-total // PER_PAGE))
fetched_at = st.session_state.get("fetched_at")
fetched_str = fetched_at.strftime("%Y-%m-%d %H:%M") if fetched_at else ""
data_age_min = int((datetime.now() - fetched_at).total_seconds() // 60) if fetched_at else 0

stats_col, refresh_col = st.columns([1, 0.001]) if data_age_min < 10 else st.columns([1, 0.18])

with stats_col:
    age_label = f"{data_age_min}분 전" if data_age_min < 60 else f"{data_age_min // 60}시간 전"
    st.markdown(f"""
<div class="stats-bar">
  <span class="stats-count">총 {total}건</span>
  <span class="stats-dot"></span>
  <span class="stats-page">{st.session_state.page} / {total_pages} 페이지</span>
  <span class="stats-time">🕐 {fetched_str} 기준 ({age_label})</span>
</div>
""", unsafe_allow_html=True)

if data_age_min >= 10:
    with refresh_col:
        st.markdown("<div style='margin-top:4px'>", unsafe_allow_html=True)
        if st.button("🔄 갱신", use_container_width=True):
            _fetch_animal_page.clear()
            get_daejeon_animals.clear()
            del st.session_state["all_animals_data"]
            del st.session_state["cache_key"]
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 카드 목록 (CSS grid — 행 단위 HTML 렌더링)
# ==========================================
COLS = 4
rows = [animals[i:i+COLS] for i in range(0, len(animals), COLS)]

CARD_CSS = """
<style>
*{box-sizing:border-box;margin:0;padding:0;}
html,body{height:auto!important;overflow:visible!important;}
body{background:transparent;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans KR',sans-serif;}
.all-rows{display:flex;flex-direction:column;gap:14px;}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;align-items:stretch;}
.card{background:#fff;border:1px solid #F0ECE7;border-radius:16px;overflow:hidden;
  box-shadow:0 2px 10px rgba(0,0,0,0.06);display:flex;flex-direction:column;
  transition:transform .18s,box-shadow .18s,border-color .18s;}
.card:hover{transform:translateY(-4px);box-shadow:0 10px 28px rgba(0,0,0,0.12);border-color:#FFD9B8;}
.card-img{width:100%;height:400px;object-fit:cover;display:block;}
.card-ph{height:400px;background:linear-gradient(135deg,#FFF3E0,#FFE8D6);
  display:flex;align-items:center;justify-content:center;font-size:3.5rem;}
.card-body{padding:12px 14px 8px;flex:1;display:flex;flex-direction:column;}
.notice-no{font-size:0.68rem;color:#B8B4AF;}
.card-title{font-size:0.97rem;font-weight:800;color:#1C1C2E;margin:4px 0 8px;
  line-height:1.3;display:flex;align-items:center;gap:5px;flex-wrap:wrap;}
.chips{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:8px;}
.chip{font-size:0.7rem;font-weight:600;background:#F5F4F2;color:#57534E;padding:2px 8px;border-radius:20px;}
.chip-c{background:#FFF7ED;color:#9A3412;}
.div{border:none;border-top:1px solid #F5F0EB;margin:6px 0;}
.loc{font-size:0.76rem;color:#57534E;line-height:1.7;}
.loc b{color:#1C1C2E;}
.dates{font-size:0.73rem;color:#78716C;line-height:1.7;margin-top:2px;}
.feat{font-size:0.73rem;color:#78716C;background:#FAFAF8;border-radius:8px;
  padding:5px 9px;margin-top:6px;line-height:1.5;}
.actions{display:flex;gap:6px;padding:8px 14px 12px;margin-top:auto;}
.btn-d{background:#FFF1E6;color:#C2410C;padding:5px 14px;border-radius:20px;font-size:0.73rem;
  font-weight:700;text-decoration:none;border:1px solid #FDDCB5;cursor:pointer;font-family:inherit;}
.btn-c{background:#F5F4F2;color:#57534E;border:1px solid #E7E5E4;padding:5px 14px;border-radius:20px;
  font-size:0.73rem;font-weight:700;cursor:pointer;font-family:inherit;}
.b{padding:2px 9px;border-radius:20px;font-size:0.7rem;font-weight:700;}
.b-p{background:#FFF1F2;color:#BE123C;border:1px solid #FECDD3;}
.b-d{background:#F0FDF4;color:#166534;border:1px solid #BBF7D0;}
.b-e{background:#F5F4F2;color:#78716C;border:1px solid #E7E5E4;}
.b-dj{background:#FFFBEB;color:#B45309;border:1px solid #FDE68A;}
</style>
"""

def _h(s):
    return html_lib.escape(str(s))

def build_card(animal):
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
    feature_raw = animal.get("specialMark", "")
    feature = feature_raw[:60] + "…" if len(feature_raw) > 60 else feature_raw
    happen_place_raw = animal.get("happenPlace", "")
    happen_place = happen_place_raw[:30] + "…" if len(happen_place_raw) > 30 else happen_place_raw
    desertion_no = animal.get("desertionNo", "")
    happen_dt = animal.get("happenDt", "")
    happen_dt_fmt = f"{happen_dt[:4]}-{happen_dt[4:6]}-{happen_dt[6:]}" if len(happen_dt) == 8 else ""
    notice_edt_fmt = f"{notice_edt[:4]}-{notice_edt[4:6]}-{notice_edt[6:]}" if len(notice_edt) == 8 else notice_edt

    if animal.get("_source") == "daejeon" and animal.get("_animalSeq"):
        detail_url = f"https://www.daejeon.go.kr/ani/AniStrayAnimalView.do?animalSeq={animal['_animalSeq']}"
    elif desertion_no:
        detail_url = f"https://www.animal.go.kr/front/awtis/public/publicDtl.do?desertionNo={desertion_no}"
    else:
        detail_url = ""

    badge_cls = "b-p" if "보호" in state else "b-d" if ("입양" in state or "종료" in state) else "b-e"
    badge_txt = "보호중" if "보호" in state else "입양완료" if ("입양" in state or "종료" in state) else "기타"
    src_badge = '<span class="b b-dj">대전시</span> ' if animal.get("_source") == "daejeon" else ""

    upkind = animal.get("_upkind", "")
    img_html = f'<img class="card-img" src="{_h(img_url)}" loading="lazy">' if img_url else f'<div class="card-ph">{get_animal_emoji(kind_nm, upkind)}</div>'

    chips = f'<span class="chip">⚥ {_h(sex)}</span><span class="chip">🎂 {_h(age)}</span>'
    if weight: chips += f'<span class="chip">⚖️ {_h(weight)}</span>'
    if color:  chips += f'<span class="chip chip-c">🎨 {_h(color)}</span>'

    loc = f'🏠 <b>{_h(shelter)}</b>'
    if care_tel: loc += f'<br>📞 {_h(care_tel)}'
    loc += f'<br>📍 {_h(org)}'
    if happen_place: loc += f'<br>📌 발견: {_h(happen_place)}'

    dates = ""
    if happen_dt_fmt: dates += f'🚑 구조일: <b>{happen_dt_fmt}</b><br>'
    if notice_edt_fmt: dates += f'📅 공고 기간: <b>{notice_edt_fmt}</b>'

    feat_html = f'<div class="feat">💬 {_h(feature)}</div>' if feature else ""
    date_html = f'<hr class="div"><div class="dates">{dates}</div>' if dates else ""

    safe_url = detail_url.replace("'", "\\'")
    actions = f'''<div class="actions">
      <a class="btn-d" href="{_h(detail_url)}" target="_blank">🔍 상세보기</a>
      <button class="btn-c" onclick="var u='{safe_url}';navigator.clipboard.writeText(u).then(function(){{this.textContent='✅ 복사됨';var b=this;setTimeout(function(){{b.textContent='🔗 링크 복사'}},2000)}}.bind(this))">🔗 링크 복사</button>
    </div>''' if detail_url else ""

    return f'''<div class="card">
  {img_html}
  <div class="card-body">
    <div class="notice-no">📋 {_h(notice_no)}</div>
    <div class="card-title">{src_badge}{_h(kind_nm)} <span class="b {badge_cls}">{badge_txt}</span></div>
    <div class="chips">{chips}</div>
    <hr class="div">
    <div class="loc">{loc}</div>
    {date_html}
    {feat_html}
  </div>
  {actions}
</div>'''

RESIZE_JS = """
<script>
function resizeIframe() {
  var el = document.querySelector('.all-rows');
  if (!el) return;
  var h = el.scrollHeight;
  if (h < 100) return;
  var newH = (h + 24) + 'px';
  try {
    var fe = window.frameElement;
    if (!fe) return;
    fe.style.height = newH;
    fe.height = h + 24;
    // Streamlit 래퍼 div도 함께 업데이트 (height 스타일 가진 첫 번째 부모)
    var p = fe.parentElement;
    while (p) {
      if (p.style && p.style.height && p.style.height !== '0px') {
        p.style.height = newH;
        p.style.minHeight = newH;
        break;
      }
      p = p.parentElement;
    }
  } catch(e) {}
}
[0, 80, 300, 800, 1800].forEach(function(d){ setTimeout(resizeIframe, d); });
document.querySelectorAll('img').forEach(function(img){
  img.addEventListener('load', function(){ setTimeout(resizeIframe, 60); });
  img.addEventListener('error', function(){ setTimeout(resizeIframe, 60); });
});
</script>
"""

def _animal_height(a):
    """카드 한 장의 예상 높이(px) — 실제 CSS 수치 기준"""
    h = 400   # 이미지/플레이스홀더
    h += 20   # card-body 패딩 (12top + 8bottom)
    h += 13   # notice-no
    h += 32   # card-title (폰트 + margin 4+8)
    h += 23   # chips 1줄 + margin-bottom
    h += 13   # divider
    loc_lines = 2  # 보호소명 + 지자체명
    if a.get("careTel"):      loc_lines += 1
    if a.get("happenPlace"):  loc_lines += 1
    h += loc_lines * 21
    if a.get("happenDt") or a.get("noticeEdt"):
        h += 13 + 2 + (bool(a.get("happenDt")) + bool(a.get("noticeEdt"))) * 20
    if a.get("specialMark"):
        h += 73  # margin + padding + 3줄
    desertion_no = a.get("desertionNo", "")
    if bool(desertion_no) or (a.get("_source") == "daejeon" and bool(a.get("_animalSeq"))):
        h += 42
    return h

# 이 페이지의 모든 카드 중 최대 높이 → CSS min-height와 Python 계산을 일치시킴
_max_card_h = max(_animal_height(a) for a in animals)
card_iframe_height = _max_card_h * len(rows) + 14 * max(0, len(rows) - 1) + 16

card_min_h_css = f"<style>.card{{min-height:{_max_card_h}px;}}</style>"
all_cards_html = CARD_CSS + card_min_h_css + '<div class="all-rows">'
for row in rows:
    all_cards_html += '<div class="grid">'
    for animal in row:
        all_cards_html += build_card(animal)
    for _ in range(COLS - len(row)):
        all_cards_html += '<div></div>'
    all_cards_html += '</div>'
all_cards_html += '</div>' + RESIZE_JS
components.html(all_cards_html, height=card_iframe_height)

# 모든 카드 렌더링 후 스크롤 상단 이동 (페이지 번호 포함 → 매번 다른 HTML로 캐시 우회)
if _do_scroll:
    components.html(f"""<script>
/* scroll-to-top page={st.session_state.page} ts={int(datetime.now().timestamp())} */
function doScroll() {{
  [
    window.parent.document.querySelector('section[data-testid="stMain"]'),
    window.parent.document.querySelector('[data-testid="stAppViewContainer"]'),
    window.parent.document.documentElement,
    window.parent.document.body,
  ].forEach(function(el){{ if(el) el.scrollTop = 0; }});
  try {{ window.parent.scrollTo(0, 0); }} catch(e) {{}}
}}
[0, 150, 400, 800].forEach(function(d){{ setTimeout(doScroll, d); }});
</script>""", height=1)

# ==========================================
# 페이지 버튼
# ==========================================
def get_visible_pages(current, total, span=10):
    if total <= span + 2:
        return list(range(1, total + 1))
    half = span // 2
    start = max(2, current - half)
    end = min(total - 1, start + span - 1)
    if end == total - 1:
        start = max(2, end - span + 1)
    pages = sorted({1, total} | set(range(start, end + 1)))
    result = []
    for i, p in enumerate(pages):
        if i > 0 and p - pages[i - 1] > 1:
            result.append(None)
        result.append(p)
    return result

cur = st.session_state.page
visible = get_visible_pages(cur, total_pages)

items = []
items.append(("prev", "←"))
for p in visible:
    items.append(("ellipsis", "…") if p is None else ("page", p))
items.append(("next", "→"))

# 아이템 타입별 컬럼 비율
def _col_w(typ):
    return {"prev": 0.9, "next": 0.9, "ellipsis": 0.3, "page": 0.45}[typ]

col_weights = [0.5] + [_col_w(t) for t, _ in items] + [0.5]
all_cols = st.columns(col_weights)

for i, (typ, val) in enumerate(items):
    col = all_cols[i + 1]
    with col:
        if typ == "prev":
            if st.button("←", use_container_width=True, disabled=(cur <= 1), key="pg_prev"):
                st.session_state.page = cur - 1
                st.session_state._scroll_to_top = True
                st.rerun()
        elif typ == "next":
            if st.button("→", use_container_width=True, disabled=(cur >= total_pages), key="pg_next"):
                st.session_state.page = cur + 1
                st.session_state._scroll_to_top = True
                st.rerun()
        elif typ == "ellipsis":
            st.markdown("<div style='text-align:center;padding-top:6px;color:#A8A29E;font-weight:600'>…</div>",
                        unsafe_allow_html=True)
        elif typ == "page":
            if val == cur:
                st.markdown(
                    f"<div style='text-align:center;padding:4px 0;font-size:0.8rem;"
                    f"font-weight:800;color:#C2410C;background:#FFF1E6;"
                    f"border-radius:8px;border:1px solid #FDDCB5'>{val}</div>",
                    unsafe_allow_html=True)
            else:
                if st.button(str(val), use_container_width=True, key=f"pg_{val}"):
                    st.session_state.page = val
                    st.session_state._scroll_to_top = True
                    st.rerun()
st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
