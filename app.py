import streamlit as st
import json
import os
from datetime import date

# =====================
# 基本設定
# =====================
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

WEIGHT_FILE = f"{DATA_DIR}/weights.json"
HISTORY_FILE = f"{DATA_DIR}/history.json"

PLACES = ["大村", "住之江", "戸田", "桐生", "若松"]

BOAT_COLORS = {
    1: "white",
    2: "black",
    3: "red",
    4: "blue",
    5: "yellow",
    6: "green"
}

DEFAULT_WEIGHTS = {
    "展示前": {
        "course": 0.35,
        "motor": 0.35,
        "ex_time": 0.0,
        "ex_st": 0.0,
        "entry_change": 0.30
    },
    "展示後": {
        "course": 0.20,
        "motor": 0.20,
        "ex_time": 0.30,
        "ex_st": 0.20,
        "entry_change": 0.10
    }
}

# =====================
# データ操作
# =====================
def load_json(path, default):
    if os.path.exists(path):
        return json.load(open(path))
    return default

def save_json(path, data):
    json.dump(data, open(path, "w"), indent=2, ensure_ascii=False)

def load_weights(place, mode):
    data = load_json(WEIGHT_FILE, {})
    if place in data and mode in data[place]:
        return data[place][mode]
    return DEFAULT_WEIGHTS[mode].copy()

def save_weights(place, mode, w):
    data = load_json(WEIGHT_FILE, {})
    if place not in data:
        data[place] = {}
    data[place][mode] = w
    save_json(WEIGHT_FILE, data)

# =====================
# AIスコア
# =====================
def calc_score(b, w):
    return (
        b["course"] * w["course"]
        + b["motor"] * w["motor"]
        - abs(b["ex_diff"]) * w["ex_time"]
        - b["st"] * w["ex_st"]
        - b["entry_change"] * w["entry_change"]
    )

# =====================
# UI
# =====================
st.set_page_config(page_title="競艇AI 完全版", layout="wide")
st.title("🚤 学習する競艇AI（完全統合版）")

place = st.selectbox("開催場所", PLACES)
mode = st.radio("予想モード", ["展示前", "展示後"])
race_date = st.date_input("日付", date.today())
race_no = st.selectbox("レース番号", list(range(1, 13)))

weights = load_weights(place, mode)

st.markdown("---")
st.subheader("出走データ入力")

boats = []
cols = st.columns(6)

for i in range(6):
    with cols[i]:
        st.markdown(
            f"<span style='color:{BOAT_COLORS[i+1]};font-weight:bold'>"
            f"{i+1}号艇</span>", unsafe_allow_html=True
        )
        course = st.slider("侵入補正", 0.0, 1.0, 0.5, key=f"c{i}")
        motor = st.slider("モーター2連率", 0.0, 1.0, 0.5, key=f"m{i}")

        ex_diff = 0.0
        st_time = 0.0
        entry_change = 0.0

        if mode == "展示後":
            ex_diff = st.slider("展示タイム差", -1.0, 1.0, 0.0, key=f"e{i}")
            st_time = st.slider("展示ST", 0.05, 0.30, 0.15, key=f"s{i}")
            entry_change = st.checkbox("進入変更", key=f"x{i}") * 1.0

        boats.append({
            "no": i+1,
            "course": course,
            "motor": motor,
            "ex_diff": ex_diff,
            "st": st_time,
            "entry_change": entry_change
        })

# =====================
# 予想生成
# =====================
st.markdown("---")
if st.button("🔮 予想する"):
    for b in boats:
        b["score"] = calc_score(b, weights)

    ranked = sorted(boats, key=lambda x: x["score"], reverse=True)

    preds = []
    for i in range(6):
        a = ranked[0]["no"]
        b = ranked[i % 5 + 1]["no"]
        c = ranked[(i + 1) % 5 + 1]["no"]
        preds.append([a, b, c])

    st.subheader("📊 三連単予想（6点）")
    for idx, p in enumerate(preds, 1):
        txt = ""
        for n in p:
            txt += f"<span style='color:{BOAT_COLORS[n]};font-weight:bold'>{n}</span>-"
        st.markdown(f"**予想{idx}**：{txt[:-1]}", unsafe_allow_html=True)

    # =====================
    # 購入 & 学習
    # =====================
    st.markdown("---")
    bought = st.checkbox("このレースを買った")
    hit = st.radio("結果", ["未確定", "的中", "不的中"])
    odds = st.number_input("的中オッズ", min_value=1.0, step=0.1)

    if st.button("📚 結果を保存・学習") and bought and hit != "未確定":
        factor = 1.02 if hit == "的中" else 0.98
        for k in weights:
            weights[k] *= factor

        save_weights(place, mode, weights)

        history = load_json(HISTORY_FILE, [])
        history.append({
            "place": place,
            "mode": mode,
            "hit": hit,
            "odds": odds
        })
        save_json(HISTORY_FILE, history)

        st.success("学習完了！次の予想に反映されます")

# =====================
# 成績表示
# =====================
st.markdown("---")
history = load_json(HISTORY_FILE, [])

if history:
    total = len(history)
    hits = sum(1 for h in history if h["hit"] == "的中")
    rate = hits / total * 100

    recovery = sum(
        h["odds"] if h["hit"] == "的中" else 0 for h in history
    ) / total * 100

    st.subheader("📈 通算成績")
    st.metric("的中率", f"{rate:.1f}%")
    st.metric("回収率", f"{recovery:.1f}%")

st.markdown("---")
st.subheader("🧠 学習済み重み")
st.json(weights)
