import streamlit as st
import pandas as pd

# --------------------------
#  페이지 기본 설정 (가장 윗줄에 있어야 함)
# --------------------------
st.set_page_config(
    page_title="농수축산물 가격 분석",
    layout="wide"
)

# ==========================================
#  [옵션 1] 고급 그라데이션 배경 적용 코드
# ==========================================
st.markdown("""
<style>
/* 전체 배경 (App View) */
.stApp {
    background: rgb(20,30,48);
    background: linear-gradient(90deg, rgba(20,30,48,1) 0%, rgba(36,59,85,1) 50%, rgba(28,69,50,1) 100%);
    background-attachment: fixed; /* 스크롤해도 배경 고정 */
}

/* 사이드바 배경 (약간 투명하게) */
[data-testid="stSidebar"] {
    background-color: rgba(20, 30, 40, 0.8);
}

/* 메트릭/글씨 잘 보이게 글자 그림자 */
[data-testid="stMetricValue"], h1, h2, h3 {
    text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
}
</style>
""", unsafe_allow_html=True)

DATA_PATH = "data/농수축산_분석가능품목_only_v2_with_kgprice.parquet"

# --------------------------
#  데이터 로드
# --------------------------
@st.cache_data
def load_items():
    df = pd.read_parquet(DATA_PATH)
    df = df[df["조사구분명"] != "친환경"].copy()  # 친환경 제외
    items = sorted(df['품목명'].dropna().unique())
    return df, items

try:
    df, items = load_items()
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()

# --------------------------
#  아이콘 매핑
# --------------------------
ICON_MAP = {
    "감자": "🥔", "고구마": "🍠", "깻잎": "🌿", "상추": "🥬",
    "시금치": "🌱", "양파": "🧅", "토마토": "🍅", "파 ": "🧅",
    "파프리카": "🫑", "피망": "🫑", "버섯": "🍄", "배추": "🥬",
    "무": "🥕", "오이": "🥒", "호박": "🎃"
}

def get_icon(name: str) -> str:
    for key, icon in ICON_MAP.items():
        if key in name:
            return icon
    return ""  # 기본 아이콘

# --------------------------
#  세션 초기화
# --------------------------
if "selected_item" not in st.session_state:
    st.session_state["selected_item"] = None

# --------------------------
#  UI 구성 (제목 + 버튼 스타일)
# --------------------------
st.markdown("""
    <style>
    /* ✅ 왕제목 색상을 흰색으로 변경 */
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #FFFFFF;              /* 여기! 원래 #004B85 → 흰색 */
        text-align: center;
    }

    .sub-header {
        font-size: 1.2rem;
        color: #CCCCCC;
        text-align: center;
        margin-bottom: 30px;
    }

    /* ✅ 모든 버튼 크기/글씨 크게 */
    .stButton > button {
        padding-top: 0.85rem;
        padding-bottom: 0.85rem;
        font-size: 1.05rem;          /* 글씨 살짝 키움 */
        font-weight: 600;
        border-radius: 999px;        /* 알약 모양(원형에 가깝게) – 원하면 지워도 됨 */
    }
    </style>
    <div class="main-header"> 농수축산물 가격 동향 대시보드</div>
    <div class="sub-header">분석할 품목을 선택하면 상세 분석 페이지로 이동합니다.</div>
""", unsafe_allow_html=True)

st.markdown("---")

# 품목 선택 버튼 그리드
cols = st.columns(4)  # 4열로 더 넓게 배치
for idx, name in enumerate(items):
    icon = get_icon(name)
    with cols[idx % 4]:
        # 선택된 항목은 강조 표시
        btn_type = "primary" if st.session_state["selected_item"] == name else "secondary"
        if st.button(f"{icon} {name}", key=f"btn_{name}", use_container_width=True, type=btn_type):
            st.session_state["selected_item"] = name
            st.rerun()

# 하단 이동 버튼
st.markdown("<br><br>", unsafe_allow_html=True)
if st.session_state["selected_item"]:
    st.success(f" **{st.session_state['selected_item']}** 품목이 선택되었습니다!")
    if st.button(" 상세 분석 보러가기 (Next)", type="primary", use_container_width=True):
        st.switch_page("pages/01_도·소매 가격 개요.py")
else:
    st.info(" 위에서 분석할 품목을 먼저 선택해주세요.")













