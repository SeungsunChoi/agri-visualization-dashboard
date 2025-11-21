import streamlit as st
import pandas as pd
import altair as alt

# ====================================================
# 🎨 CSS — 제목 크기만 살짝 조정
# ====================================================
st.markdown("""
<style>
h1 {font-size: 1.55rem !important;}
h2 {font-size: 1.28rem !important;}
h3 {font-size: 1.15rem !important;}
</style>
""", unsafe_allow_html=True)

# ====================================================
# 🏷 페이지 제목
# ====================================================
st.title("📉 가격 이상탐지 및 안정성 분석 (도매 기준)")

PRICE_COL = "kg당가격"

# ====================================================
# 0. 데이터 불러오기
# ====================================================
DATA_PATH = "data/농수축산_분석가능품목_only_v2_with_kgprice.parquet"
df = pd.read_parquet(DATA_PATH)import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="급등락 분석", layout="wide")
# ==========================================
# 🎨 [옵션 1] 고급 그라데이션 배경 적용 코드
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

/* 메트릭/글씨 잘 보이게 배경 박스 추가 (선택사항) */
[data-testid="stMetricValue"], h1, h2, h3 {
    text-shadow: 2px 2px 4px rgba(0,0,0,0.5); /* 글자 그림자 */
}
</style>
""", unsafe_allow_html=True)

PRICE_COL = "kg당가격"

if "selected_item" not in st.session_state or not st.session_state["selected_item"]:
    st.warning(" 메인 페이지에서 품목을 먼저 선택해주세요.")
    st.stop()

item = st.session_state["selected_item"]
st.title(f" {item} 가격 급등락(이상탐지) 분석")

# 데이터 로드 (도매만 분석)
DATA_PATH = "data/농수축산_분석가능품목_only_v2_with_kgprice.parquet"
try:
    df = pd.read_parquet(DATA_PATH)
except:
    st.error("데이터 로드 실패")
    st.stop()

df["가격등록일자"] = pd.to_datetime(df["가격등록일자"])
df[PRICE_COL] = pd.to_numeric(df[PRICE_COL], errors="coerce")

# --------------------------
# 사이드바 설정
# --------------------------
with st.sidebar:
    st.header(" 탐지 민감도 설정")
    window = st.radio("이동평균 기간 (Window)", [7, 14, 30], index=0, help="기간이 짧을수록 최근 변화에 민감합니다.")
    
    st.markdown("---")
    st.markdown("**데이터 필터**")
    # 도매 데이터만 사용
    df_w = df[(df["품목명"] == item) & (df["조사구분명"] == "도매")].copy()
    
    if df_w.empty:
        st.error("도매 데이터가 없습니다.")
        st.stop()

    p_list = sorted(df_w["품종명"].dropna().unique())
    sel_p = st.selectbox("품종", p_list)
    g_list = sorted(df_w[df_w["품종명"] == sel_p]["산물등급명"].dropna().unique())
    sel_g = st.selectbox("등급", g_list)

# 분석 데이터 준비
sub = df_w[(df_w["품종명"] == sel_p) & (df_w["산물등급명"] == sel_g)].sort_values("가격등록일자").copy()

if len(sub) < window:
    st.error(f"데이터가 너무 적어 ({len(sub)}개) 이동평균({window}일)을 계산할 수 없습니다.")
    st.stop()

# --------------------------
#  급등락 알고리즘 (볼린저 밴드)
# --------------------------
sub["MA"] = sub[PRICE_COL].rolling(window).mean()
sub["STD"] = sub[PRICE_COL].rolling(window).std()
sub["Upper"] = sub["MA"] + (2 * sub["STD"])
sub["Lower"] = sub["MA"] - (2 * sub["STD"])

sub["급등"] = sub[PRICE_COL] > sub["Upper"]
sub["급락"] = sub[PRICE_COL] < sub["Lower"]
sub["연월"] = sub["가격등록일자"].dt.to_period("M").astype(str)

spike_up_cnt = sub["급등"].sum()
spike_down_cnt = sub["급락"].sum()
latest_volatility = (sub["STD"].iloc[-1] / sub["MA"].iloc[-1]) * 100 if sub["MA"].iloc[-1] > 0 else 0

# --------------------------
#  핵심 요약 Metrics
# --------------------------
m1, m2, m3, m4 = st.columns(4)
m1.metric("분석 기간", f"{window}일 이동평균")
m2.metric("🔴 총 급등 횟수", f"{spike_up_cnt}회")
m3.metric("🔵 총 급락 횟수", f"{spike_down_cnt}회")
m4.metric(" 현재 변동성(CV)", f"{latest_volatility:.1f}%")

st.markdown("---")

# --------------------------
# 1. [유지] 급등락 시계열
# --------------------------
st.subheader(" 이상치 탐지 시계열")

base = alt.Chart(sub).encode(x=alt.X("가격등록일자:T", title="날짜"))
line = base.mark_line(color="gray", opacity=0.5).encode(y=alt.Y(PRICE_COL, title="가격"))
ma_line = base.mark_line(color="#004B85", strokeDash=[5, 5]).encode(y="MA", tooltip="MA")
up_points = base.mark_circle(size=60, color="red").encode(y=PRICE_COL, tooltip=[PRICE_COL]).transform_filter(alt.datum.급등 == True)
down_points = base.mark_circle(size=60, color="blue").encode(y=PRICE_COL, tooltip=[PRICE_COL]).transform_filter(alt.datum.급락 == True)

st.altair_chart((line + ma_line + up_points + down_points).properties(height=400).interactive(), use_container_width=True)

# --------------------------
# 2. [복구됨] 하단 분석 그래프들
# --------------------------
st.markdown("---")
st.subheader(" 월별 상세 분석")

colA, colB = st.columns(2)

# (1) 월별 급등/급락 횟수 막대 그래프
with colA:
    st.markdown("** 월별 급등·급락 빈도**")
    
    count_df = sub.groupby("연월").agg(급등횟수=("급등", "sum"), 급락횟수=("급락", "sum")).reset_index()
    count_melt = count_df.melt(id_vars="연월", value_vars=["급등횟수", "급락횟수"], var_name="구분", value_name="횟수")
    
    # 급락은 음수로 표현하여 위아래로 보이게 처리
    count_melt["표시값"] = count_melt.apply(lambda x: x["횟수"] if x["구분"] == "급등횟수" else -x["횟수"], axis=1)
    
    bar_chart = alt.Chart(count_melt).mark_bar().encode(
        x=alt.X("연월:O", title=""),
        y=alt.Y("표시값:Q", title="횟수 (상:급등 / 하:급락)"),
        color=alt.Color("구분:N", scale=alt.Scale(domain=["급등횟수", "급락횟수"], range=["red", "blue"]), legend=None),
        tooltip=["연월", "구분", "횟수"]
    ).properties(height=300)
    st.altair_chart(bar_chart, use_container_width=True)

# (2) 월별 변동성 및 박스플롯 (탭으로 구분하여 공간 활용)
with colB:
    tab1, tab2 = st.tabs([" 월별 변동성", " 월별 가격 분포"])
    
    with tab1:
        vol_df = sub.groupby("연월")[PRICE_COL].std().reset_index(name="표준편차")
        vol_chart = alt.Chart(vol_df).mark_bar(color="#004B85").encode(
            x=alt.X("연월:O", title=""),
            y=alt.Y("표준편차:Q", title="가격 표준편차"),
            tooltip=["연월", alt.Tooltip("표준편차", format=",.0f")]
        ).properties(height=250)
        st.altair_chart(vol_chart, use_container_width=True)
        
    with tab2:
        box_chart = alt.Chart(sub).mark_boxplot(color="#004B85").encode(
            x=alt.X("연월:O", title=""),
            y=alt.Y(f"{PRICE_COL}:Q", title="가격"),
        ).properties(height=250)
        st.altair_chart(box_chart, use_container_width=True)


