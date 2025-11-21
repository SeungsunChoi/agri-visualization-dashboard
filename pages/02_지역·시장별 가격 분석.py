import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="지역·시장 분석", layout="wide")
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

# 데이터 및 세션 체크
if "selected_item" not in st.session_state or not st.session_state["selected_item"]:
    st.warning(" 메인 페이지에서 품목을 먼저 선택해주세요.")
    st.stop()

item = st.session_state["selected_item"]
st.title(f" {item} 지역 및 시장별 심층 분석")

DATA_PATH = "data/농수축산_분석가능품목_only_v2_with_kgprice.parquet"
df = pd.read_parquet(DATA_PATH)
df = df[(df["품목명"] == item) & (df["조사구분명"].isin(["도매", "소매"]))].copy()
df["가격등록일자"] = pd.to_datetime(df["가격등록일자"])

# --------------------------
# 🛠 사이드바: 통합 필터
# --------------------------
with st.sidebar:
    st.header(" 분석 옵션 설정")
    
    # 기간
    min_d, max_d = df["가격등록일자"].min(), df["가격등록일자"].max()
    dates = st.slider(" 기간 선택", min_value=min_d.date(), max_value=max_d.date(), value=(min_d.date(), max_d.date()))
    
    # 품종/등급
    filtered_date = df[(df["가격등록일자"] >= pd.to_datetime(dates[0])) & (df["가격등록일자"] <= pd.to_datetime(dates[1]))]
    p_list = sorted(filtered_date["품종명"].dropna().unique())
    sel_p = st.selectbox("품종", p_list)
    
    g_list = sorted(filtered_date[filtered_date["품종명"] == sel_p]["산물등급명"].dropna().unique())
    sel_g = st.selectbox("등급", g_list)
    
    # 최종 데이터
    sub = filtered_date[(filtered_date["품종명"] == sel_p) & (filtered_date["산물등급명"] == sel_g)].copy()

if sub.empty:
    st.error("조건에 맞는 데이터가 없습니다.")
    st.stop()

# --------------------------
#  탭(Tabs) 구성 - Option C 적용
# --------------------------
tab1, tab2 = st.tabs([" 지역별 분석 (시도 단위)", " 시장별 분석 (세부 시장)"])

# [Tab 1] 지역 분석
with tab1:
    st.markdown("####  지역별 가격 비교 및 히트맵")
    
    col_con1, col_con2 = st.columns([1, 3])
    with col_con1:
        target_type = st.radio("조사 기준", ["도매", "소매"], horizontal=True, key="t1_radio")
        regions = sorted(sub[sub["조사구분명"] == target_type]["시도명"].unique())
        sel_regions = st.multiselect("비교할 지역 선택", regions, default=regions[:2] if len(regions)>1 else regions)
    
    sub_r = sub[(sub["조사구분명"] == target_type) & (sub["시도명"].isin(sel_regions))]
    
    if not sub_r.empty:
        # 시계열
        chart_r = alt.Chart(sub_r.groupby(["가격등록일자", "시도명"], as_index=False)[PRICE_COL].mean()).mark_line().encode(
            x="가격등록일자:T", y=f"{PRICE_COL}:Q", color="시도명:N"
        ).properties(height=300, title="지역별 가격 추이")
        st.altair_chart(chart_r, use_container_width=True)
        
        # 히트맵 (월별 패턴)
        sub_r["연월"] = sub_r["가격등록일자"].dt.to_period("M").astype(str)
        heat_data = sub_r.groupby(["시도명", "연월"], as_index=False)[PRICE_COL].mean()
        
        heatmap = alt.Chart(heat_data).mark_rect().encode(
            x=alt.X("연월:O", title=""),
            y=alt.Y("시도명:N", title=""),
            color=alt.Color(f"{PRICE_COL}:Q", scale=alt.Scale(scheme="blues"), title="가격"),
            tooltip=["시도명", "연월", alt.Tooltip(PRICE_COL, format=",")]
        ).properties(height=300, title="지역별 가격 히트맵")
        st.altair_chart(heatmap, use_container_width=True)
    else:
        st.info("좌측 상단에서 지역을 선택해주세요.")

# [Tab 2] 시장 분석
with tab2:
    st.markdown("####  개별 시장 가격 분포")
    
    # 시장 필터
    m_type = st.radio("조사 기준", ["도매", "소매"], horizontal=True, key="t2_radio")
    sub_m_base = sub[sub["조사구분명"] == m_type]
    
    markets = sorted(sub_m_base["시장명"].unique())
    sel_markets = st.multiselect("비교할 시장 선택 (최대 5개 권장)", markets, default=markets[:3] if len(markets)>2 else markets)
    
    sub_m = sub_m_base[sub_m_base["시장명"].isin(sel_markets)]
    
    if not sub_m.empty:
        c1, c2 = st.columns(2)
        with c1:
            # 시장별 시계열
            m_line = alt.Chart(sub_m.groupby(["가격등록일자", "시장명"], as_index=False)[PRICE_COL].mean()).mark_line().encode(
                x="가격등록일자:T", y=f"{PRICE_COL}:Q", color="시장명:N"
            ).properties(height=350, title="시장별 가격 흐름")
            st.altair_chart(m_line, use_container_width=True)
            
        with c2:
            # 시장별 박스플롯
            m_box = alt.Chart(sub_m).mark_boxplot().encode(
                x=alt.X("시장명:N", title=None),
                y=alt.Y(f"{PRICE_COL}:Q", title="가격"),
                color="시장명:N"
            ).properties(height=350, title="시장별 가격 분포")
            st.altair_chart(m_box, use_container_width=True)
    else:
        st.info("비교할 시장을 선택해주세요.")
