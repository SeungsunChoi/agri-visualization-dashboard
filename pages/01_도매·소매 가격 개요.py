import streamlit as st
import pandas as pd
import altair as alt

# =========================================================
# 🎨 1) 전체 제목 사이즈 축소 (CSS)
# =========================================================
st.markdown("""
<style>
.big-title { font-size: 26px !important; font-weight: 700; margin-bottom: 10px !important; }
.section-title { font-size: 20px !important; font-weight: 700; margin-top: 20px; }
.subheader { font-size: 17px !important; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 📌 2) 페이지 제목
# =========================================================
st.markdown('<div class="big-title">📌 품종·등급 선택 페이지 (kg당 가격 기준)</div>', unsafe_allow_html=True)

PRICE_COL = "kg당가격"

# =========================================================
# 3) 앱 첫 페이지에서 넘어온 선택 품목
# =========================================================
item = st.session_state.get("selected_item", None)
if item is None:
    st.error("⚠ 먼저 첫 페이지에서 품목을 선택해주세요.")
    st.stop()

# =========================================================
# 4) 데이터 불러오기
# =========================================================
DATA_PATH = "data/농수축산_분석가능품목_only_v2_with_kgprice.parquet"
df = pd.read_parquet(DATA_PATH)

# 친환경 제거
df = df[df["조사구분명"] != "친환경"].copy()

# 날짜/수치 정리
df["가격등록일자"] = pd.to_datetime(df["가격등록일자"], errors="coerce")
df = df.dropna(subset=["가격등록일자"])
df[PRICE_COL] = pd.to_numeric(df[PRICE_COL], errors="coerce")

# =========================================================
# 5) 슬라이더 + 품종 + 등급 — 하나의 ROW(3열)
# =========================================================
col1, col2, col3 = st.columns([2.0, 1.2, 1.2])

# ----------------------------
# 📅 기간 슬라이더
# ----------------------------
with col1:
    st.markdown("#### 조회 기간 선택")

    min_date = df["가격등록일자"].min().date()
    max_date = df["가격등록일자"].max().date()

    selected_range = st.slider(
        " ",  # 라벨 숨기기
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM-DD",
        label_visibility="collapsed"
    )

    start_ts, end_ts = map(pd.to_datetime, selected_range)

    df_period = df[
        (df["가격등록일자"] >= start_ts) &
        (df["가격등록일자"] <= end_ts)
    ].copy()

# ----------------------------
# 📌 품종 선택
# ----------------------------
with col2:
    st.markdown("#### 품종 선택")

    df_item = df_period[df_period["품목명"] == item]
    var_list = sorted(df_item["품종명"].dropna().unique())

    selected_var = st.selectbox(
        "품종",
        var_list,
        label_visibility="collapsed"
    )

# ----------------------------
# 📌 등급 선택
# ----------------------------
with col3:
    st.markdown("#### 등급 선택")

    grade_list = sorted(
        df_item[df_item["품종명"] == selected_var]["산물등급명"].dropna().unique()
    )

    selected_grade = st.selectbox(
        "등급",
        grade_list,
        label_visibility="collapsed"
    )

# =========================================================
# 6) 품종 & 등급 필터 결과
# =========================================================
sub = df_item[
    (df_item["품종명"] == selected_var) &
    (df_item["산물등급명"] == selected_grade)
].copy()

sub = sub.dropna(subset=[PRICE_COL])
if sub.empty:
    st.error("⚠ 해당 품종·등급 조합의 데이터가 없습니다.")
    st.stop()

# 도매/소매 비교용 집계
sub_grouped = (
    sub.groupby(["가격등록일자", "조사구분명"], as_index=False)[PRICE_COL]
    .mean()
)

# =========================================================
# 7) 📈 + 📊 시각화 1행 (시계열 + 박스플롯)
# =========================================================
colA, colB = st.columns(2)

# ----------------------------
# 📈 일자별 가격 추이
# ----------------------------
with colA:
    st.markdown('<div class="section-title">📈 일자별 가격 추이 (도매·소매)</div>', unsafe_allow_html=True)

    line_chart = (
        alt.Chart(sub_grouped)
        .mark_line()
        .encode(
            x=alt.X("가격등록일자:T", axis=alt.Axis(format="%Y-%m")),
            y=alt.Y(f"{PRICE_COL}:Q", title="가격(원/kg)"),
            color=alt.Color("조사구분명:N", title="조사구분"),
            tooltip=["가격등록일자:T", "조사구분명:N", alt.Tooltip(f"{PRICE_COL}:Q", title="가격(원/kg)")]
        )
        .properties(height=260)
    )
    st.altair_chart(line_chart, use_container_width=True)

# ----------------------------
# 📊 도매·소매 가격 분포 (Boxplot)
# ----------------------------
with colB:
    st.markdown('<div class="section-title">📊 도매·소매 가격 분포 (Boxplot)</div>', unsafe_allow_html=True)

    box_chart = (
        alt.Chart(sub)
        .mark_boxplot()
        .encode(
            x=alt.X("조사구분명:N", title="조사구분"),
            y=alt.Y(f"{PRICE_COL}:Q", title="가격(원/kg)"),
            color="조사구분명:N",
        )
        .properties(height=260)
    )
    st.altair_chart(box_chart, use_container_width=True)

# =========================================================
# 8) 💰 월별 평균 마진 그래프
# =========================================================
st.markdown('<div class="section-title">💰 월별 평균 마진 (소매 - 도매)</div>', unsafe_allow_html=True)

# 피벗
pivot = sub_grouped.pivot(
    index="가격등록일자",
    columns="조사구분명",
    values=PRICE_COL,
)

if {"도매", "소매"}.issubset(pivot.columns):

    margin_df = pivot.copy()
    margin_df["마진"] = margin_df["소매"] - margin_df["도매"]
    margin_df = margin_df.dropna(subset=["마진"]).reset_index()

    # 연월화
    margin_df["연월"] = margin_df["가격등록일자"].dt.to_period("M").dt.to_timestamp()

    month_margin = (
        margin_df.groupby("연월", as_index=False)["마진"].mean()
    )

    margin_bar = (
        alt.Chart(month_margin)
        .mark_bar()
        .encode(
            x=alt.X("연월:T", axis=alt.Axis(format="%Y-%m"), title="연월"),
            y=alt.Y("마진:Q", title="평균 마진(원/kg)"),
            tooltip=[
                alt.Tooltip("연월:T", title="연월"),
                alt.Tooltip("마진:Q", title="평균 마진(원/kg)", format=",.0f")
            ],
        )
        .properties(height=280)
    )
    st.altair_chart(margin_bar, use_container_width=True)

    avg_margin = month_margin["마진"].mean()
    st.markdown(f"✔ 선택 기간 평균 마진: **{avg_margin:,.0f}원/kg**")

else:
    st.info("현재 조건에서는 도매·소매가 모두 존재하지 않아 마진 계산이 불가능합니다.")




