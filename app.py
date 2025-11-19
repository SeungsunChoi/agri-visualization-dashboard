import streamlit as st
import pandas as pd

st.set_page_config(page_title="품목 선택", layout="wide")

DATA_PATH = "data/농수축산_분석가능품목_only_v2_with_kgprice.parquet"

# --------------------------
# 📌 데이터 로드 함수 (Parquet)
# --------------------------
@st.cache_data
def load_items():
    df = pd.read_parquet(DATA_PATH)

    # ⚠ 친환경 조사구분 제외
    df = df[df["조사구분명"] != "친환경"].copy()

    # 품목 리스트 정렬
    items = sorted(df['품목명'].dropna().unique())
    return df, items

df, items = load_items()

# --------------------------
# 📌 품목별 아이콘 매핑
# --------------------------
ICON_MAP = {
    "감자": "🥔",
    "고구마": "🍠",
    "깻잎": "🌿",
    "상추": "🥬",
    "시금치": "🌱",
    "양파": "🧅",
    "토마토": "🍅",
    "파 ": "🧅",         # 공백 버전
    "파프리카": "🫑",
    "피망": "🫑",
    "버섯": "🍄",
}

def get_icon(name: str) -> str:
    for key, icon in ICON_MAP.items():
        if key in name:
            return icon
    return "🥕"  # 기본 아이콘


# --------------------------
# 📌 선택 상태 초기화
# --------------------------
if "selected_item" not in st.session_state:
    st.session_state["selected_item"] = None


# --------------------------
# 📌 헤더
# --------------------------
st.markdown(
    """
    <h1 style='text-align:center; margin-bottom:10px;'>📌 품목 선택 페이지</h1>
    <p style='text-align:center; font-size:18px; color:#555;'>
        분석할 품목을 아래에서 선택한 후, 다음 단계로 이동하세요.
    </p>
    """,
    unsafe_allow_html=True
)

st.markdown("---")


# --------------------------
# 📌 카드형 버튼 UI
# --------------------------
st.subheader("🥕 분석할 품목을 선택하세요")

cols = st.columns(3)
for idx, name in enumerate(items):
    icon = get_icon(name)
    with cols[idx % 3]:
        if st.button(
            f"{icon}  {name}",
            key=f"item_{name}",
            use_container_width=True
        ):
            st.session_state["selected_item"] = name


# --------------------------
# 📌 선택된 품목 표시
# --------------------------
if st.session_state["selected_item"]:
    st.success(f"✔ 선택된 품목: **{st.session_state['selected_item']}**")
else:
    st.info("아직 선택된 품목이 없습니다.")

st.markdown("<br>", unsafe_allow_html=True)

# --------------------------
# 📌 다음 단계 버튼
# --------------------------
if st.session_state["selected_item"]:
    if st.button("👉 다음 단계로 이동", type="primary"):
        st.switch_page("pages/01_세부선택.py")




