import streamlit as st
import pandas as pd
import zipfile

st.set_page_config(page_title="품목 선택", layout="wide")

# ==============================
# 📌 ZIP 파일에서 데이터 불러오기
# ==============================
ZIP_PATH = "data/농수축산_분석가능품목_only_v2_with_kgprice.zip"
CSV_NAME = "농수축산_분석가능품목_only_v2_with_kgprice.csv"

@st.cache_data
def load_items():
    try:
        # ZIP 내부 CSV 읽기
        with zipfile.ZipFile(ZIP_PATH) as z:
            with z.open(CSV_NAME) as f:
                df = pd.read_csv(f)

        # 실제 CSV에 들어있는 품목명 기준으로 정렬
        items = sorted(df['품목명'].dropna().unique())
        return items

    except Exception as e:
        st.error(f"⚠ 데이터 로드 실패: {e}")
        return []


# ==============================
# 📌 품목 리스트 로드
# ==============================
items = load_items()

# ==============================
# 🥕 품목 → 이모지 매핑
# ==============================
ICON_MAP = {
    "감자": "🥔",
    "고구마": "🍠",
    "깻잎": "🌿",
    "상추": "🥬",
    "시금치": "🌱",
    "양파": "🧅",
    "토마토": "🍅",
    "파 ": "🧅",
    "파프리카": "🫑",
    "피망": "🫑",
    "버섯": "🍄"
}

def get_icon(name: str) -> str:
    for key, icon in ICON_MAP.items():
        if key in name:
            return icon
    return "🥕"   # 기본 아이콘


# ==============================
# 🔘 선택 상태 초기화
# ==============================
if "selected_item" not in st.session_state:
    st.session_state["selected_item"] = None


# ==============================
# 🎨 UI 헤더
# ==============================
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


# ==============================
# 🃏 카드형 버튼 UI
# ==============================
st.subheader("🥕 분석할 품목을 선택하세요")

if items:
    cols = st.columns(3)

    for idx, name in enumerate(items):
        icon = get_icon(name)
        with cols[idx % 3]:
            if st.button(f"{icon}  {name}", key=f"item_{name}", use_container_width=True):
                st.session_state["selected_item"] = name
else:
    st.error("⚠ ZIP 파일에서 품목을 불러오지 못했습니다. ZIP 경로/파일명을 확인하세요.")


# ==============================
# 📌 현재 선택 상태 표시
# ==============================
if st.session_state["selected_item"]:
    st.success(f"✔ 선택된 품목: **{st.session_state['selected_item']}**")
else:
    st.info("아직 선택된 품목이 없습니다.")


st.markdown("<br>", unsafe_allow_html=True)


# ==============================
# 👉 다음 페이지로 이동 버튼
# ==============================
if st.session_state["selected_item"]:
    if st.button("👉 다음 단계로 이동", type="primary"):
        st.switch_page("pages/02_세부선택.py")


