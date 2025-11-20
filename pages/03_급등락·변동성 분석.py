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
df = pd.read_parquet(DATA_PATH)

df["가격등록일자"] = pd.to_datetime(df["가격등록일자"], errors="coerce")
df = df.dropna(subset=["가격등록일자"])
df = df[df["조사구분명"].isin(["도매", "소매"])]

# ====================================================
# 1. 기간, 품종, 등급 선택
# ====================================================
st.markdown("## 📅 기간 · 품종 · 등급 설정")

col1, col2, col3 = st.columns([1.2, 0.9, 0.8])

# ① 기간 선택
with col1:
    st.markdown("#### 📅 분석 기간")

    min_date = df["가격등록일자"].min().date()
    max_date = df["가격등록일자"].max().date()

    start_d, end_d = st.slider(
        "분석 기간",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM-DD",
    )

    start_ts = pd.to_datetime(start_d)
    end_ts = pd.to_datetime(end_d)

    df_period = df[(df["가격등록일자"] >= start_ts) & (df["가격등록일자"] <= end_ts)]

# ② 품종 선택
with col2:
    st.markdown("#### 📌 품종")

    item = st.session_state.get("selected_item", None)
    if item is None:
        st.error("⚠ 먼저 페이지 1에서 품목을 선택해주세요.")
        st.stop()

    df_item = df_period[df_period["품목명"] == item]
    if df_item.empty:
        st.warning("⚠ 선택된 기간에 해당 품목 데이터가 없습니다.")
        st.stop()

    품종_list = sorted(df_item["품종명"].dropna().unique().tolist())
    선택_품종 = st.selectbox("품종 선택", 품종_list)

    df_var = df_item[df_item["품종명"] == 선택_품종]

# ③ 등급 선택
with col3:
    st.markdown("#### 📌 등급")

    등급_list = sorted(df_var["산물등급명"].dropna().unique().tolist())
    선택_등급 = st.selectbox("등급 선택", 등급_list)

    sub = df_var[df_var["산물등급명"] == 선택_등급]

# ====================================================
# 🚨 4. 급등·급락 탐지
# ====================================================
st.markdown("## 🚨 4. 급등·급락 탐지 (도매 기준)")

sub_wholesale = sub[sub["조사구분명"] == "도매"].copy()
if sub_wholesale.empty:
    st.warning("⚠ 선택된 조건에서 '도매' 데이터가 없습니다.")
    st.stop()

sub_wholesale[PRICE_COL] = pd.to_numeric(sub_wholesale[PRICE_COL], errors="coerce")
sub_wholesale = sub_wholesale.dropna(subset=[PRICE_COL]).sort_values("가격등록일자")

# 이동평균 선택
col_w1, col_w2 = st.columns([1, 1])
with col_w1:
    window = st.radio("이동평균 기간", [7, 14, 30], horizontal=True)

# 급등락 계산
sub_wholesale["MA"] = sub_wholesale[PRICE_COL].rolling(window).mean()
sub_wholesale["STD"] = sub_wholesale[PRICE_COL].rolling(window).std()

sub_wholesale["급등"] = sub_wholesale[PRICE_COL] > (sub_wholesale["MA"] + 2 * sub_wholesale["STD"])
sub_wholesale["급락"] = sub_wholesale[PRICE_COL] < (sub_wholesale["MA"] - 2 * sub_wholesale["STD"])

spike_up = sub_wholesale[sub_wholesale["급등"]]
spike_down = sub_wholesale[sub_wholesale["급락"]]

sub_wholesale["연월"] = sub_wholesale["가격등록일자"].dt.to_period("M").astype(str)

# ====================================================
# 📈 급등·급락 시계열 (왼쪽)
# ====================================================
base_line = (
    alt.Chart(sub_wholesale)
    .mark_line(
        color="rgba(0,0,0,0.3)",
        strokeWidth=1.2
    )
    .encode(
        x="가격등록일자:T",
        y=alt.Y(f"{PRICE_COL}:Q", title="가격(원/kg)")
    )
)

spike_up_chart = (
    alt.Chart(spike_up)
    .mark_circle(size=30, color="rgba(255,0,0,1)")
    .encode(x="가격등록일자:T", y=f"{PRICE_COL}:Q")
)

spike_down_chart = (
    alt.Chart(spike_down)
    .mark_circle(size=30, color="rgba(30,80,255,1)")
    .encode(x="가격등록일자:T", y=f"{PRICE_COL}:Q")
)

final_chart = (
    base_line + spike_up_chart + spike_down_chart
).properties(
    width="container",
    height=360,
    title="📉 급등·급락 시계열"
)

# ====================================================
# 📈 + 📊 2열 배치 (붙여놓기)
# ====================================================
st.markdown("## 🚨 4. 급등·급락 시각화 & 월별 통계")

colA, colB = st.columns([1.3, 0.7])

with colA:
    st.markdown("### 📈 급등·급락 시계열")
    st.altair_chart(final_chart, use_container_width=True)

# 월별 급등·급락
with colB:
    st.markdown("### 📊 월별 급등·급락 횟수")

    count_df = (
        sub_wholesale.groupby("연월")
        .agg(급등횟수=("급등", "sum"), 급락횟수=("급락", "sum"))
        .reset_index()
    )

    df_div = count_df.copy()
    df_div["급등_signed"] = df_div["급등횟수"]
    df_div["급락_signed"] = -df_div["급락횟수"]

    df_melt = df_div.melt(
        id_vars="연월",
        value_vars=["급등_signed", "급락_signed"],
        var_name="구분",
        value_name="값"
    )

    df_melt["구분"] = df_melt["구분"].map({"급등_signed": "급등", "급락_signed": "급락"})
    color_scale = alt.Scale(domain=["급등", "급락"], range=["red", "blue"])

    chart_div = (
        alt.Chart(df_melt)
        .mark_bar()
        .encode(
            x=alt.X("연월:N", sort=count_df["연월"].tolist()),
            y="값:Q",
            color=alt.Color("구분:N", scale=color_scale),
        )
        .properties(height=340)
    )

    st.altair_chart(chart_div, use_container_width=True)

# ====================================================
# 📉 5·6 변동성 & 박스플롯
# ====================================================
st.markdown("## 📉 5·6. 월별 변동성 & 박스플롯")

colC, colD = st.columns(2)

# 변동성
with colC:
    st.markdown("### 📉 월별 가격 변동성")

    vol_df = (
        sub_wholesale.groupby("연월")
        .agg(
            평균가격=(PRICE_COL, "mean"),
            표준편차=(PRICE_COL, "std"),
        )
        .reset_index()
    )

    vol_df["변동계수"] = vol_df["표준편차"] / vol_df["평균가격"]

    vol_chart = (
        alt.Chart(vol_df)
        .mark_bar()
        .encode(
            x=alt.X("연월:N", sort=vol_df["연월"].tolist()),
            y=alt.Y("표준편차:Q", title="표준편차"),
            tooltip=[
                "연월:N",
                alt.Tooltip("평균가격:Q", title="평균가격", format=","),
                alt.Tooltip("표준편차:Q", title="표준편차", format=","),
                alt.Tooltip("변동계수:Q", title="CV", format=".3f"),
            ]
        )
        .properties(height=260)
    )

    st.altair_chart(vol_chart, use_container_width=True)

# 박스플롯
with colD:
    st.markdown("### 📦 월별 가격 박스플롯")

    box_df = sub_wholesale.copy()

    box_chart = (
        alt.Chart(box_df)
        .mark_boxplot(color="#4154B3")
        .encode(
            x=alt.X("연월:N", sort=box_df["연월"].unique().tolist()),
            y=alt.Y(f"{PRICE_COL}:Q", title="가격(원/kg)")
        )
        .properties(height=260)
    )

    st.altair_chart(box_chart, use_container_width=True)


