import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="급등락 분석", layout="wide")

# ==========================================
# 🎨 CSS: 전역 레이아웃 & Tabs 패딩 제거
# ==========================================
st.markdown("""
<style>

.stApp {
    background: rgb(20,30,48);
    background: linear-gradient(90deg, rgba(20,30,48,1) 0%, rgba(36,59,85,1) 50%, rgba(28,69,50,1) 100%);
    background-attachment: fixed;
}

/* 사이드바 */
[data-testid="stSidebar"] {
    background-color: rgba(20, 30, 40, 0.8);
}

/* 텍스트 그림자 */
[data-testid="stMetricValue"], h1, h2, h3 {
    text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
}

/* ====== 핵심: columns 내부 패딩 제거 ====== */
div[data-testid="column"] > div:first-child {
    padding-top: 0 !important;
    margin-top: 0 !important;
}

/* ====== tabs 기본 padding 제거 ====== */
div[data-testid="stTabs"] {
    margin-top: -10px !important;
    padding-top: 0 !important;
}

/* tabs 버튼 패딩 조정 */
div[data-testid="stTabs"] button {
    padding-top: 3px !important;
    padding-bottom: 3px !important;
}

/* Streamlit 기본 구분선 제거 */
div[data-testid="stDecoration"]{
    display:none !important;
}

</style>
""", unsafe_allow_html=True)

PRICE_COL = "kg당가격"

# ============================
# 0. 품목 체크
# ============================
if "selected_item" not in st.session_state or not st.session_state["selected_item"]:
    st.warning(" 메인 페이지에서 품목을 먼저 선택해주세요.")
    st.stop()

item = st.session_state["selected_item"]
st.title(f" {item} 가격 급등락(이상탐지) 분석")

# ============================
# 1. 데이터 로드
# ============================
DATA_PATH = "data/농수축산_분석가능품목_only_v2_with_kgprice.parquet"
df = pd.read_parquet(DATA_PATH)

df["가격등록일자"] = pd.to_datetime(df["가격등록일자"])
df[PRICE_COL] = pd.to_numeric(df[PRICE_COL], errors="coerce")

# ============================
# 🔥 (A) Sidebar
# ============================
with st.sidebar:
    st.header("분석 옵션 설정")

    min_date = df["가격등록일자"].min().date()
    max_date = df["가격등록일자"].max().date()

    selected_range = st.slider(
        "조회 기간",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM-DD"
    )

    df = df[
        (df["가격등록일자"] >= pd.to_datetime(selected_range[0])) &
        (df["가격등록일자"] <= pd.to_datetime(selected_range[1])) &
        (df["품목명"] == item)
    ]

    st.markdown("### 탐지 민감도(Window)")
    window = st.radio("이동평균 기간", [7, 14, 30], index=0)

    st.markdown("### 데이터 필터")

    df_w = df[df["조사구분명"] == "도매"]
    p_list = sorted(df_w["품종명"].dropna().unique())
    sel_p = st.selectbox("품종", p_list)

    g_list = sorted(df_w[df_w["품종명"] == sel_p]["산물등급명"].dropna().unique())
    sel_g = st.selectbox("등급", g_list)

# ============================
# 2. 분석 데이터 준비
# ============================
sub = df_w[(df_w["품종명"] == sel_p) & (df_w["산물등급명"] == sel_g)].copy()
sub = sub.sort_values("가격등록일자")

if len(sub) < window:
    st.error(f"데이터가 너무 적어 이동평균({window}일) 계산 불가.")
    st.stop()

# ============================
# 3. 볼린저 밴드 탐지
# ============================
sub["MA"] = sub[PRICE_COL].rolling(window).mean()
sub["STD"] = sub[PRICE_COL].rolling(window).std()
sub["Upper"] = sub["MA"] + 2 * sub["STD"]
sub["Lower"] = sub["MA"] - 2 * sub["STD"]

sub["급등"] = sub[PRICE_COL] > sub["Upper"]
sub["급락"] = sub[PRICE_COL] < sub["Lower"]
sub["연월"] = sub["가격등록일자"].dt.to_period("M").astype(str)

# ============================
# 4. 핵심 지표
# ============================
st.markdown("### 핵심 요약 지표")

m1, m2, m3, m4 = st.columns(4)
m1.metric("분석 기간", f"{window}일")
m2.metric("🔴 총 급등 횟수", f"{sub['급등'].sum()}회")
m3.metric("🔵 총 급락 횟수", f"{sub['급락'].sum()}회")

latest_vol = (sub["STD"].iloc[-1] / sub["MA"].iloc[-1] * 100) if sub["MA"].iloc[-1] != 0 else 0
m4.metric("변동성(CV)", f"{latest_vol:.1f}%")

st.markdown("---")

# ============================
# 5. 이상치 탐지 시계열
# ============================
st.subheader("이상치 탐지 시계열")

base = alt.Chart(sub).encode(x="가격등록일자:T")
line = base.mark_line(color="gray", opacity=0.5).encode(y=PRICE_COL)
ma_line = base.mark_line(color="#004B85", strokeDash=[5,5]).encode(y="MA")
up_p = base.mark_circle(size=60, color="red").encode(y=PRICE_COL).transform_filter("datum.급등 == true")
down_p = base.mark_circle(size=60, color="blue").encode(y=PRICE_COL).transform_filter("datum.급락 == true")

st.altair_chart((line + ma_line + up_p + down_p).properties(height=400), use_container_width=True)

# ============================
# 6. 월별 분석
# ============================
st.subheader("월별 상세 분석")

# 🔥 탭을 먼저 정의 (colB 바깥)
tab1, tab2 = st.tabs(["변동성", "가격 분포"])

# ---- colA + colB 구성 ----
colA, colB = st.columns(2)

# (A) 월별 급등·급락 빈도
with colA:
    count_df = sub.groupby("연월").agg(급등횟수=("급등","sum"), 급락횟수=("급락","sum")).reset_index()
    df_melt = count_df.melt(id_vars="연월", value_vars=["급등횟수","급락횟수"], 
                            var_name="구분", value_name="횟수")
    df_melt["표시"] = df_melt.apply(
        lambda x: x["횟수"] if x["구분"]=="급등횟수" else -x["횟수"], axis=1
    )

    chart = alt.Chart(df_melt).mark_bar().encode(
        x="연월:O",
        y="표시:Q",
        color=alt.Color("구분:N",
                        scale=alt.Scale(domain=["급등횟수","급락횟수"],
                                        range=["red","blue"])),
        tooltip=["연월","구분","횟수"]
    ).properties(height=300)

    st.altair_chart(chart, use_container_width=True)

# (B) 선택된 탭에 따라 그래프 표시
with colB:
    with tab1:
        vol_df = sub.groupby("연월")[PRICE_COL].std().reset_index(name="표준편차")
        vol_chart = alt.Chart(vol_df).mark_bar(color="#004B85").encode(
            x="연월:O",
            y="표준편차:Q"
        ).properties(height=300)
        st.altair_chart(vol_chart, use_container_width=True)

    with tab2:
        box_chart = alt.Chart(sub).mark_boxplot(color="#004B85").encode(
            x="연월:O",
            y=f"{PRICE_COL}:Q"
        ).properties(height=300)
        st.altair_chart(box_chart, use_container_width=True)





