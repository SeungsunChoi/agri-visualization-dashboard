import streamlit as st
import pandas as pd
import altair as alt

PRICE_COL = "kg당가격"

st.markdown("""
<style>

 /* ================================================
      🔥 Streamlit 기본 장식 제거
  ================================================= */
div[data-testid="stDecoration"] { display: none !important; }
hr { display: none !important; }

 /* ================================================
      📌 페이지 메인 제목 (h1)
  ================================================= */
.main-title {
    font-size: 2.1rem !important;
    font-weight: 750 !important;
    margin-top: 0.3rem !important;
    margin-bottom: 0.7rem !important;
}

 /* ================================================
      📌 섹션 제목 (h2, h3)
  ================================================= */
h2 {
    font-size: 1.45rem !important;
    font-weight: 650 !important;
    margin-top: 0.6rem !important;
    margin-bottom: 0.4rem !important;
}

h3 {
    font-size: 1.25rem !important;
    font-weight: 600 !important;
    margin-top: 0.4rem !important;
    margin-bottom: 0.3rem !important;
}

h4 {
    font-size: 1.05rem !important;
    font-weight: 500 !important;
    margin-top: 0.2rem !important;
    margin-bottom: 0.2rem !important;
}

 /* ================================================
      📌 Streamlit 기본 라벨(font-size) 크게 만들기
      (slider / selectbox / radio)
  ================================================= */
div[data-testid="stSliderLabel"] label,
div[data-testid="stSelectboxLabel"] label,
div[data-testid="stRadioLabel"] label {
    font-size: 1.22rem !important;
    font-weight: 600 !important;
    color: #333 !important;
}

 /* ================================================
      📌 위젯 간 기본 마진 축소
  ================================================= */
div[data-testid="stSelectbox"], 
div[data-testid="stRadio"],
div[data-testid="stSlider"] {
    margin-top: -0.2rem !important;
    margin-bottom: 0.5rem !important;
}

 /* ================================================
      📌 버튼 스타일 통일
  ================================================= */
.stButton>button {
    font-size: 0.95rem !important;
    padding: 0.35rem 0.6rem !important;
    border-radius: 8px !important;
}

</style>
""", unsafe_allow_html=True)




# ======================================================
# 0. 제목 (항상 표시되도록 container로 보호)
# ======================================================
st.markdown('<h1 class="main-title">📍 지역·시장별 가격 비교</h1>', unsafe_allow_html=True)

# ======================================================
# 0. 데이터 로드
# ======================================================
DATA_PATH = "data/농수축산_분석가능품목_only_v2_with_kgprice.parquet"
df = pd.read_parquet(DATA_PATH)

df["가격등록일자"] = pd.to_datetime(df["가격등록일자"], errors="coerce")
df = df.dropna(subset=["가격등록일자"])
df = df[df["조사구분명"].isin(["도매", "소매"])]

# ------------------------------
# 🔹 품목 선택 여부 체크
# ------------------------------
item = st.session_state.get("selected_item", None)

if item is None:
    st.warning("⚠ 먼저 첫 화면(app.py)에서 품목을 선택해주세요.")
    st.info("현재 페이지는 품목이 선택되면 자동으로 업데이트됩니다.")
    st.stop()


# ------------------------------
# 🔹 품목 필터링
# ------------------------------
df_item = df[df["품목명"] == item].copy()

if df_item.empty:
    st.warning(f"⚠ 선택된 품목 **{item}** 에 대한 데이터가 존재하지 않습니다.")
    st.info("다른 품목을 선택해 주세요.")
    st.stop()


# ======================================================
# 1. 분석 조건
# ======================================================
st.markdown("#### 🔧 분석 조건 설정")

col_date, col_var, col_grade = st.columns([2, 1, 1])

with col_date:
    min_date = df_item["가격등록일자"].min().to_pydatetime()
    max_date = df_item["가격등록일자"].max().to_pydatetime()

    start_ts, end_ts = st.slider(
        "📅 분석 기간",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM-DD",
    )

df_period = df_item[
    (df_item["가격등록일자"] >= start_ts) &
    (df_item["가격등록일자"] <= end_ts)
]

with col_var:
    품종_list = sorted(df_period["품종명"].dropna().unique())
    선택_품종 = st.selectbox("📌 품종", 품종_list)

df_var = df_period[df_period["품종명"] == 선택_품종]

with col_grade:
    등급_list = sorted(df_var["산물등급명"].dropna().unique())
    선택_등급 = st.selectbox("📌 등급", 등급_list)

sub = df_var[df_var["산물등급명"] == 선택_등급].copy()
if sub.empty:
    st.warning("⚠ 선택된 조건 데이터 없음")
    st.stop()


# ======================================================
# 2. 지역 비교
# ======================================================
st.markdown("---")
st.markdown("#### 🌍 지역별 가격 비교")

sub_region_base = sub.copy()
sub_region_base["연월"] = sub_region_base["가격등록일자"].dt.to_period("M").astype(str)

if "selected_regions" not in st.session_state:
    st.session_state["selected_regions"] = []

# 🔝 상단 한 줄
top1, top2, top3, top4 = st.columns([1.1, 2.5, 0.6, 0.9])

with top1:
    price_type = st.radio(
        "지역 비교 기준 선택",
        ["도매", "소매"],
        horizontal=True,
        key="region_price_type"
    )

sub_region = sub_region_base[sub_region_base["조사구분명"] == price_type].copy()

with top2:
    all_regions = sorted(sub_region["시도명"].unique())
    remaining_regions = [r for r in all_regions if r not in st.session_state["selected_regions"]]
    region_to_add = st.selectbox("지역 선택", remaining_regions if remaining_regions else ["추가할 지역 없음"],
                                 label_visibility="collapsed")

with top3:
    if st.button("➕", help="지역 추가"):
        if region_to_add != "추가할 지역 없음":
            st.session_state["selected_regions"].append(region_to_add)

with top4:
    if st.button("🗑 전체 초기화", key="region_reset_small"):
        st.session_state["selected_regions"] = []
        st.rerun()

# 선택된 지역 삭제 버튼
if st.session_state["selected_regions"]:
    btn_cols = st.columns(len(st.session_state["selected_regions"]))
    for i, region in enumerate(st.session_state["selected_regions"]):
        with btn_cols[i]:
            if st.button(f"❌ {region}", key=f"del_region_{i}"):
                st.session_state["selected_regions"].remove(region)
                st.rerun()


# 📈 / 📊 그래프
colL, colR = st.columns([1.15, 1], gap="small")

# --- 좌측: 시계열 ---
with colL:
    st.markdown("##### 📈 시계열")
    ts = sub_region.groupby(["시도명", "가격등록일자"], as_index=False)[PRICE_COL].mean()
    ts_sel = ts[ts["시도명"].isin(st.session_state["selected_regions"])]

    if not ts_sel.empty:
        chart_region = (
            alt.Chart(ts_sel)
            .mark_line()
            .encode(
                x=alt.X("가격등록일자:T", axis=alt.Axis(format="%Y-%m"), title=""),
                y=alt.Y(f"{PRICE_COL}:Q", title="가격(원/kg)"),
                color="시도명:N",
            )
            .properties(height=230)
        )
        st.altair_chart(chart_region, use_container_width=True)
    else:
        st.info("왼쪽에서 지역을 하나 이상 선택해 주세요.")

# --- 우측: 히트맵 ---
with colR:
    st.markdown(f"##### 📊 연·월 패턴 ({price_type})")

    heat = sub_region.groupby(["시도명", "연월"], as_index=False)[PRICE_COL].mean()

    heatmap = (
        alt.Chart(heat)
        .mark_rect()
        .encode(
            x=alt.X("연월:N", sort=sorted(heat["연월"].unique()), axis=alt.Axis(labelAngle=-45), title=""),
            y=alt.Y("시도명:N", title=""),
            color=alt.Color(f"{PRICE_COL}:Q", scale=alt.Scale(scheme="blues")),
        )
        .properties(height=230)
    )
    st.altair_chart(heatmap, use_container_width=True)


# ======================================================
# 3. 시장 비교
# ======================================================
st.markdown("---")
st.markdown("#### 🏬 시장별 가격 비교")

sub_market_base = sub.copy()
sub_market_base["시장_라벨"] = sub_market_base.apply(
    lambda x: f"{x['시장명']} ({x['시도명']})", axis=1
)

if "selected_markets" not in st.session_state:
    st.session_state["selected_markets"] = []

m1, m2, m3, m4 = st.columns([1.1, 2.5, 0.6, 0.9])

with m1:
    market_price_type = st.radio(
        "시장 비교 기준 선택", ["도매", "소매"],
        horizontal=True, key="market_price_type"
    )

sub_market = sub_market_base[sub_market_base["조사구분명"] == market_price_type].copy()

with m2:
    remaining_mk = [
        m for m in sorted(sub_market["시장_라벨"].unique())
        if m not in st.session_state["selected_markets"]
    ]
    market_to_add = st.selectbox("시장 선택",
                                 remaining_mk if remaining_mk else ["추가할 시장 없음"],
                                 label_visibility="collapsed")

with m3:
    if st.button("➕ 시장"):
        if market_to_add != "추가할 시장 없음":
            st.session_state["selected_markets"].append(market_to_add)

with m4:
    if st.button("🗑 전체 초기화", key="market_reset_small"):
        st.session_state["selected_markets"] = []
        st.rerun()

# 선택된 시장 삭제 버튼
if st.session_state["selected_markets"]:
    mk_cols = st.columns(len(st.session_state["selected_markets"]))
    for i, mk in enumerate(st.session_state["selected_markets"]):
        with mk_cols[i]:
            if st.button(f"❌ {mk}", key=f"del_mk_{i}"):
                st.session_state["selected_markets"].remove(mk)
                st.rerun()

# 📈 / 📦 그래프
colL2, colR2 = st.columns([1.15, 1], gap="small")

with colL2:
    st.markdown("##### 📈 시장 시계열")

    if st.session_state["selected_markets"]:
        ts_market = sub_market.groupby(["시장_라벨", "가격등록일자"], as_index=False)[PRICE_COL].mean()

        ts_sel = ts_market[
            ts_market["시장_라벨"].isin(st.session_state["selected_markets"])
        ]

        line_market = (
            alt.Chart(ts_sel)
            .mark_line()
            .encode(
                x=alt.X("가격등록일자:T", axis=alt.Axis(format="%Y-%m"), title=""),
                y=alt.Y(f"{PRICE_COL}:Q", title="가격(원/kg)"),
                color="시장_라벨:N",
            )
            .properties(height=230)
        )
        st.altair_chart(line_market, use_container_width=True)
    else:
        st.info("위에서 시장을 하나 이상 선택해 주세요.")

with colR2:
    st.markdown("##### 📦 시장별 가격 분포")

    if st.session_state["selected_markets"]:
        sub_box = sub_market[sub_market["시장_라벨"].isin(st.session_state["selected_markets"])]

        box_chart = (
            alt.Chart(sub_box)
            .mark_boxplot(size=28)
            .encode(
                x=alt.X("시장_라벨:N", title=""),
                y=alt.Y(f"{PRICE_COL}:Q", title="가격(원/kg)"),
                color="시장_라벨:N",
            )
            .properties(height=230)
        )
        st.altair_chart(box_chart, use_container_width=True)
    else:
        st.info("시장 선택 후 박스플롯을 확인할 수 있습니다.")
