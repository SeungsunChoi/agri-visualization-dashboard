import streamlit as st
import pandas as pd
import altair as alt
import zipfile

st.title("📌 품종·등급 선택 페이지 (kg당 가격 기준)")

PRICE_COL = 'kg당가격'  # 이미 만들어 둔 kg당 가격 컬럼

# ==============================
# 0) ZIP에서 전체 데이터 로드
# ==============================
ZIP_PATH = "data/농수축산_분석가능품목_only_v2_with_kgprice.zip"
CSV_NAME = "농수축산_분석가능품목_only_v2_with_kgprice.csv"

@st.cache_data
def load_full_df():
    """ZIP 파일 안의 CSV를 읽어서 전체 DataFrame 반환"""
    with zipfile.ZipFile(ZIP_PATH) as z:
        with z.open(CSV_NAME) as f:
            df = pd.read_csv(f)

    # 날짜 파싱 + 깨진 날짜(NaT) 제거
    df['가격등록일자'] = pd.to_datetime(df['가격등록일자'], errors='coerce')
    df = df.dropna(subset=['가격등록일자'])
    return df

# 1) app.py에서 선택된 품목 받기
item = st.session_state.get('selected_item', None)
if item is None:
    st.error("⚠ 먼저 첫 페이지에서 품목을 선택해주세요.")
    st.stop()

# 2) 데이터 로드
df = load_full_df()

if df.empty:
    st.error("⚠ 유효한 날짜 데이터가 없습니다.")
    st.stop()

# 3) 전체 기간 기준으로 min/max 날짜 구해서 기간 선택 UI 만들기
st.subheader("📅 기간 선택")

global_min = df['가격등록일자'].min().date()
global_max = df['가격등록일자'].max().date()

start_date = st.date_input("시작 날짜", global_min)
end_date = st.date_input("종료 날짜", global_max)

if start_date > end_date:
    st.error("⚠ 시작 날짜가 종료 날짜보다 늦습니다.")
    st.stop()

start_ts = pd.to_datetime(start_date)
end_ts = pd.to_datetime(end_date)

# 선택한 기간 안의 데이터만 사용
df_period = df[(df['가격등록일자'] >= start_ts) & (df['가격등록일자'] <= end_ts)]

if df_period.empty:
    st.error("⚠ 이 기간에는 어떤 데이터도 없습니다.")
    st.stop()

# 4) 선택한 품목만 필터
df_item = df_period[df_period['품목명'] == item].copy()

if df_item.empty:
    st.error("⚠ 이 기간에는 선택한 품목의 데이터가 없습니다.")
    st.stop()

# 5) 품종 / 등급 선택 (원본 그대로)
var_list = sorted(df_item['품종명'].dropna().unique())
grade_list = sorted(df_item['산물등급명'].dropna().unique())

selected_var = st.selectbox("품종 선택", var_list)
selected_grade = st.selectbox("등급 선택", grade_list)

# 6) 선택한 품종 + 등급만 필터
sub = df_item[
    (df_item['품종명'] == selected_var) &
    (df_item['산물등급명'] == selected_grade)
].copy()

if sub.empty:
    st.error("⚠ 이 기간에는 해당 품종·등급 데이터가 없습니다.")
    st.stop()

# 7) kg당가격 숫자형으로 변환하고 NaN 제거
sub[PRICE_COL] = pd.to_numeric(sub[PRICE_COL], errors='coerce')
sub = sub.dropna(subset=[PRICE_COL])

if sub.empty:
    st.error("⚠ kg당가격 값이 없는 행만 남았습니다.")
    st.stop()

# 8) 날짜·조사구분별로 하루 평균 kg당가격 계산
sub_grouped = (
    sub.groupby(['가격등록일자', '조사구분명'], as_index=False)[PRICE_COL]
      .mean()
)

# 9) 차트 그리기
st.subheader(f"📈 kg당 가격 추이 · ({item} / {selected_var} / {selected_grade})")

chart = alt.Chart(sub_grouped).mark_line().encode(
    x=alt.X(
        '가격등록일자:T',
        axis=alt.Axis(format='%Y-%m', labelAngle=0),
        title='날짜'
    ),
    y=alt.Y(f'{PRICE_COL}:Q', title='kg당 가격(원/kg)'),
    color='조사구분명:N'
).properties(
    width=800,
    height=350
)

st.altair_chart(chart, use_container_width=False)

