import streamlit as st
import pandas as pd
from datetime import date
import itertools

st.set_page_config(page_title="競艇AI予想", layout="wide")

# =====================
# 定数
# =====================
PLACES = ["桐生", "戸田", "江戸川", "平和島", "多摩川", "浜名湖", "蒲郡", "常滑", "津", "三国"]
BOAT_COLORS = {
    1: "#ffffff",
    2: "#000000",
    3: "#ff0000",
    4: "#0000ff",
    5: "#ffff00",
    6: "#00aa00",
}

# =====================
# セッション初期化
# =====================
if "history" not in st.session_state:
    st.session_state.history = []

# =====================
# UI ヘッダ
# =====================
st.title("🚤 競艇AI予想（展示前・展示後対応）")

# =====================
# 基本情報
# =====================
col1, col2, col3 = st.columns(3)
with col1:
    race_date = st.date_input("日付", value=date.today())
with col2:
    place = st.selectbox("開催場所", PLACES)
with col3:
    race_no = st.selectbox("レース番号", list(range(1, 13)))

# =====================
# 展示前 / 展示後 切替
# =====================
mode = st.radio("予想モード", ["展示前予想", "展示後予想"], horizontal=True)

st.divider()

# =====================
# 入力UI（6艇）
# =====================
st.subheader("📥 数値入力（小数第2位まで）")

boats = []
for i in range(1, 7):
    with st.expander(f"{i}号艇 入力", expanded=True):
        c1, c2, c3, c4 = st.columns(4)

        course = c1.number_input(
            "侵入補正",
            min_value=-0.50, max_value=0.50,
            value=0.00, step=0.01, format="%.2f",
            key=f"course_{i}_{mode}"
        )

        motor = c2.number_input(
            "モーター2連率",
            min_value=0.00, max_value=100.00,
            value=50.00, step=0.01, format="%.2f",
            key=f"motor_{i}_{mode}"
        )

        time_diff = c3.number_input(
            "展示タイム平均との差",
            min_value=-1.00, max_value=1.00,
            value=0.00, step=0.01, format="%.2f",
            key=f"time_{i}_{mode}"
        )

        st_time = c4.number_input(
            "展示ST",
            min_value=0.00, max_value=0.30,
            value=0.15, step=0.01, format="%.2f",
            key=f"st_{i}_{mode}"
        )

        boats.append({
            "boat": i,
            "course": course,
            "motor": motor,
            "time": time_diff,
            "st": st_time
        })

# =====================
# スコア計算
# =====================
def calc_score(b):
    return (
        b["course"] * 1.2
        + b["motor"] * 0.02
        - b["time"] * 1.5
        - b["st"] * 2.0
    )

df = pd.DataFrame(boats)
df["score"] = df.apply(calc_score, axis=1)
df = df.sort_values("score", ascending=False)

# =====================
# 三連単生成（6点）
# =====================
top_boats = df["boat"].tolist()[:4]
combos = list(itertools.permutations(top_boats, 3))[:6]

st.divider()
st.subheader("🎯 三連単予想（6点）")

for idx, c in enumerate(combos, 1):
    html = f"<b>予想{idx}：</b> "
    for b in c:
        color = BOAT_COLORS[b]
        text_color = "#000000" if b != 2 else "#ffffff"
        html += f"""
        <span style="
            background:{color};
            color:{text_color};
            padding:6px;
            margin:2px;
            border-radius:6px;
            border:1px solid #333;
            font-weight:bold;">
            {b}
        </span>
        →
        """
    st.markdown(html[:-1], unsafe_allow_html=True)

# =====================
# 買った/買ってない
# =====================
st.divider()
bought = st.checkbox("💰 この予想を購入した")

hit = False
odds = st.number_input("オッズ（買った場合）", min_value=0.0, value=0.0, step=0.1)

if st.button("結果を保存"):
    st.session_state.history.append({
        "date": race_date,
        "place": place,
        "race": race_no,
        "mode": mode,
        "bought": bought,
        "hit": hit,
        "odds": odds
    })
    st.success("保存しました")

# =====================
# 成績表示
# =====================
st.divider()
st.subheader("📊 成績")

if st.session_state.history:
    hist = pd.DataFrame(st.session_state.history)

    total = len(hist)
    bought_df = hist[hist["bought"] == True]

    hit_rate = bought_df["hit"].mean() * 100 if len(bought_df) else 0
    recovery = bought_df["odds"].sum() / len(bought_df) if len(bought_df) else 0

    st.write(f"🎯 購入的中率：{hit_rate:.1f}%")
    st.write(f"💰 回収率：{recovery:.2f}")

    st.dataframe(hist)
else:
    st.info("まだデータがありません")
