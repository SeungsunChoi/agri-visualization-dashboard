import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="도·소매 가격 개요", layout="wide")
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

#  CSS: 메트릭 카드 스타일링
st.markdown("""
<style>
[data-testid="stMetricValue"] {
    font-size: 1.8rem !important;
    color: #004B85;
}
</style>
""", unsafe_allow_html=True)

PRICE_COL = "kg당가격"

# --------------------------
# 1. 데이터 로드 & 전처리
# --------------------------
if "selected_item" not in st.session_state or not st.session_state["selected_item"]:
    st.warning(" 메인 페이지에서 품목을 먼저 선택해주세요.")
    st.stop()

item = st.session_state["selected_item"]
st.title(f" {item} 도·소매 가격 개요")

DATA_PATH = "data/농수축산_분석가능품목_only_v2_with_kgprice.parquet"
try:
    df = pd.read_parquet(DATA_PATH)
except:
    st.error("데이터 파일을 찾을 수 없습니다.")
    st.stop()

df = df[df["조사구분명"] != "친환경"].copy()
df["가격등록일자"] = pd.to_datetime(df["가격등록일자"], errors="coerce")
df = df.dropna(subset=["가격등록일자", PRICE_COL])
df[PRICE_COL] = pd.to_numeric(df[PRICE_COL], errors="coerce")

# --------------------------
# 2. 사이드바(Sidebar) 필터 
# --------------------------
with st.sidebar:
    st.header("분석 옵션 설정")
    
    # 기간 선택
    min_date = df["가격등록일자"].min().date()
    max_date = df["가격등록일자"].max().date()
    
    selected_range = st.slider(
        " 조회 기간",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM-DD"
    )
    
    # 품목 데이터 필터링
    df_period = df[
        (df["가격등록일자"] >= pd.to_datetime(selected_range[0])) & 
        (df["가격등록일자"] <= pd.to_datetime(selected_range[1])) &
        (df["품목명"] == item)
    ]
    
    # 품종/등급 선택
    var_list = sorted(df_period["품종명"].dropna().unique())
    selected_var = st.selectbox(" 품종 선택", var_list)
    
    grade_list = sorted(df_period[df_period["품종명"] == selected_var]["산물등급명"].dropna().unique())
    selected_grade = st.selectbox(" 등급 선택", grade_list)

# 최종 필터링
sub = df_period[(df_period["품종명"] == selected_var) & (df_period["산물등급명"] == selected_grade)].copy()

if sub.empty:
    st.error("선택하신 조건에 해당하는 데이터가 없습니다.")
    st.stop()

# 집계 데이터 생성
sub_grouped = sub.groupby(["가격등록일자", "조사구분명"], as_index=False)[PRICE_COL].mean()

#  공통 색상 정의 (도매=파랑, 소매=주황)
color_scale = alt.Scale(domain=['도매', '소매'], range=['#004B85', '#FF5E00'])

# --------------------------
# 3. 핵심 지표 (Metrics)
# --------------------------
st.markdown("###  핵심 가격 지표")
pivot = sub_grouped.pivot(index="가격등록일자", columns="조사구분명", values=PRICE_COL)
has_wholesale = "도매" in pivot.columns
has_retail = "소매" in pivot.columns

m1, m2, m3 = st.columns(3)

with m1:
    if has_wholesale:
        avg_w = pivot["도매"].mean()
        last_w = pivot["도매"].iloc[-1]
        delta_w = last_w - avg_w 
        st.metric("평균 도매가격", f"{avg_w:,.0f}원", delta=f"{delta_w:,.0f}원 (평균대비)", delta_color="inverse")

with m2:
    if has_retail:
        avg_r = pivot["소매"].mean()
        last_r = pivot["소매"].iloc[-1]
        delta_r = last_r - avg_r
        st.metric("평균 소매가격", f"{avg_r:,.0f}원", delta=f"{delta_r:,.0f}원 (평균대비)", delta_color="inverse")

with m3:
    if has_wholesale and has_retail:
        margin = pivot["소매"] - pivot["도매"]
        avg_margin = margin.mean()
        st.metric("평균 유통 마진", f"{avg_margin:,.0f}원/kg", "도매와 소매의 가격 차이")

st.markdown("---")

# --------------------------
# 4. 메인 시각화 (시계열 + 박스플롯)
# --------------------------
col1, col2 = st.columns([1.2, 0.8])

with col1:
    st.subheader(" 일자별 가격 추이")
    line_chart = alt.Chart(sub_grouped).mark_line(point=True).encode(
        x=alt.X("가격등록일자:T", title="날짜", axis=alt.Axis(format="%y-%m-%d")),
        y=alt.Y(f"{PRICE_COL}:Q", title="가격(원/kg)"),
        color=alt.Color("조사구분명:N", scale=color_scale, title="구분"),
        tooltip=["가격등록일자", "조사구분명", alt.Tooltip(PRICE_COL, format=",")]
    ).properties(height=350).interactive()
    st.altair_chart(line_chart, use_container_width=True)

with col2:
    st.subheader(" 가격 분포 (Boxplot)")
    box_chart = alt.Chart(sub).mark_boxplot(size=50).encode(
        x=alt.X("조사구분명:N", title=None),
        y=alt.Y(f"{PRICE_COL}:Q", title=None),
        color=alt.Color("조사구분명:N", scale=color_scale, legend=None)
    ).properties(height=350)
    st.altair_chart(box_chart, use_container_width=True)

# --------------------------
# 5. [복구됨] 도·소매 월별 평균 마진 그래프
# --------------------------
if has_wholesale and has_retail:
    st.markdown("---")
    st.subheader(" 도·소매 월별 평균 마진 추이")
    
    # 마진 데이터 계산
    margin_df = pivot.copy()
    margin_df["마진"] = margin_df["소매"] - margin_df["도매"]
    margin_df = margin_df.dropna(subset=["마진"]).reset_index()
    margin_df["연월"] = margin_df["가격등록일자"].dt.to_period("M").dt.to_timestamp()
    
    month_margin = margin_df.groupby("연월", as_index=False)["마진"].mean()

    # 막대 그래프 그리기
    margin_bar = alt.Chart(month_margin).mark_bar(color="#004B85").encode(
        x=alt.X("연월:T", axis=alt.Axis(format="%Y-%m"), title="연월"),
        y=alt.Y("마진:Q", title="평균 마진(원/kg)"),
        tooltip=[
            alt.Tooltip("연월:T", title="연월", format="%Y-%m"),
            alt.Tooltip("마진:Q", title="평균 마진", format=",.0f")
        ]
    ).properties(height=300)
    
    st.altair_chart(margin_bar, use_container_width=True)











