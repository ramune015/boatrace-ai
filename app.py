import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import date
import itertools

# =====================
# 基本設定
# =====================
st.set_page_config(page_title="競艇AI予想", layout="centered")

BOAT_COLORS = {
    1: "#ffffff",
    2: "#000000",
    3: "#ff0000",
    4: "#0066ff",
    5: "#ffd400",
    6: "#00aa44",
}

PLACE_CODES = {
    "桐生": "01",
    "戸田": "02",
    "江戸川": "03",
    "平和島": "04",
    "多摩川": "05",
    "浜名湖": "06",
    "蒲郡": "07",
    "常滑": "08",
    "津": "09",
    "三国": "10",
    "びわこ": "11",
    "住之江": "12",
    "尼崎": "13",
    "鳴門": "14",
    "丸亀": "15",
    "児島": "16",
    "宮島": "17",
    "徳山": "18",
    "下関": "19",
    "若松": "20",
    "芦屋": "21",
    "福岡": "22",
    "唐津": "23",
    "大村": "24",
}

# =====================
# データ取得
# =====================
def fetch_entry(date_str, place_code, race_no):
    url = f"https://www.boatrace.jp/owpc/pc/race/racelist?rno={race_no}&jcd={place_code}&hd={date_str}"
    soup = BeautifulSoup(requests.get(url).text, "html.parser")
    boats = []

    rows = soup.select("tbody.is-fs12 tr")
    for i, r in enumerate(rows, 1):
        try:
            win = float(r.select_one("td.is-lineH2").text.strip())
        except:
            win = 0.0
        boats.append({
            "boat": i,
            "win": win,
            "motor": 0.5
        })
    return boats

def fetch_exhibition(date_str, place_code, race_no):
    url = f"https://www.boatrace.jp/owpc/pc/race/exhibition?rno={race_no}&jcd={place_code}&hd={date_str}"
    soup = BeautifulSoup(requests.get(url).text, "html.parser")
    ex = {}
    rows = soup.select("tbody.is-fs12 tr")
    for i, r in enumerate(rows, 1):
        try:
            t = float(r.select("td")[4].text.strip())
        except:
            t = 7.0
        ex[i] = t
    return ex

def fetch_odds(date_str, place_code, race_no):
    url = f"https://www.boatrace.jp/owpc/pc/race/odds3t?rno={race_no}&jcd={place_code}&hd={date_str}"
    soup = BeautifulSoup(requests.get(url).text, "html.parser")
    odds = {}
    for row in soup.select("tbody tr"):
        tds = row.select("td")
        if len(tds) >= 2:
            key = tds[0].text.replace(" ", "")
            try:
                odds[key] = float(tds[1].text)
            except:
                pass
    return odds

# =====================
# スコアリング
# =====================
def score_boat(b, ex=None):
    base = b["win"]
    if ex:
        base += max(0, (7 - ex[b["boat"]])) * 0.3
    return base

def generate_predictions(boats, ex=None):
    scores = {b["boat"]: score_boat(b, ex) for b in boats}
    combos = []
    for a, b, c in itertools.permutations(range(1, 7), 3):
        s = scores[a]*0.5 + scores[b]*0.3 + scores[c]*0.2
        combos.append((s, (a, b, c)))
    combos.sort(reverse=True)
    return [c for _, c in combos[:6]]

# =====================
# 表示
# =====================
def show_predictions(preds, odds):
    for i, (a, b, c) in enumerate(preds, 1):
        key = f"{a}-{b}-{c}"
        o = odds.get(key, "-")
        st.markdown(
            f"""
            **予想{i}（オッズ {o}）**  
            <span style="background:{BOAT_COLORS[a]};padding:6px;border-radius:6px">{a}</span>
            →
            <span style="background:{BOAT_COLORS[b]};padding:6px;border-radius:6px">{b}</span>
            →
            <span style="background:{BOAT_COLORS[c]};padding:6px;border-radius:6px">{c}</span>
            """,
            unsafe_allow_html=True
        )

# =====================
# UI
# =====================
st.title("🚤 競艇AI予想（iPhone対応）")

d = st.date_input("日付", date.today())
place = st.selectbox("開催場", PLACE_CODES.keys())
race = st.selectbox("レース番号", list(range(1, 13)))

mode = st.radio("予想モード", ["展示前予想", "展示後予想"], horizontal=True)

if "history" not in st.session_state:
    st.session_state.history = []

if st.button("予想する"):
    date_str = d.strftime("%Y%m%d")
    code = PLACE_CODES[place]

    boats = fetch_entry(date_str, code, race)
    ex = fetch_exhibition(date_str, code, race) if mode == "展示後予想" else None
    odds = fetch_odds(date_str, code, race)

    preds = generate_predictions(boats, ex)
    show_predictions(preds, odds)

    st.session_state.current = {
        "preds": preds,
        "odds": odds
    }

# =====================
# 結果入力 & 成績
# =====================
st.divider()
st.subheader("📊 結果記録")

result = st.text_input("結果（三連単 例: 1-2-3）")
bought = st.checkbox("この予想を買った")

if st.button("保存"):
    hit = any(result == f"{a}-{b}-{c}" for a, b, c in st.session_state.current["preds"])
    payout = st.session_state.current["odds"].get(result, 0) if hit and bought else 0
    st.session_state.history.append({
        "bought": bought,
        "hit": hit,
        "payout": payout
    })
    st.success("保存しました")

if st.session_state.history:
    total = len(st.session_state.history)
    bought = [h for h in st.session_state.history if h["bought"]]
    hits = [h for h in bought if h["hit"]]
    roi = sum(h["payout"] for h in hits) / max(1, len(bought)) * 100

    st.write(f"🎯 的中率：{len(hits)/max(1,len(bought))*100:.1f}%")
    st.write(f"💰 回収率：{roi:.1f}%")

