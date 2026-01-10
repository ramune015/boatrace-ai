import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import date

# =========================
# 基本設定
# =========================
st.set_page_config(
    page_title="競艇AI予想",
    layout="centered"
)

FRAME_BONUS = {1:1.00,2:0.92,3:0.85,4:0.78,5:0.70,6:0.60}
BOAT_COLORS = {
    1:"white",2:"black",3:"red",
    4:"blue",5:"yellow",6:"green"
}

PLACE_CODES = {
    "桐生":"01","戸田":"02","江戸川":"03","平和島":"04","蒲郡":"05",
    "多摩川":"06","浜名湖":"07","三国":"08","びわこ":"09","住之江":"12"
}

HEADERS = {"User-Agent":"Mozilla/5.0"}

# =========================
# セッション初期化
# =========================
if "history" not in st.session_state:
    st.session_state.history = []

if "preds" not in st.session_state:
    st.session_state.preds = []

if "odds_map" not in st.session_state:
    st.session_state.odds_map = {}

# =========================
# データ取得（展示前）
# =========================
def get_boat_data_pre_real(race_date, place, race_no):
    ymd = race_date.strftime("%Y%m%d")
    jcd = PLACE_CODES[place]

    url = f"https://www.boatrace.jp/owpc/pc/race/racelist?rno={race_no}&jcd={jcd}&hd={ymd}"
    res = requests.get(url, headers=HEADERS, timeout=10)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")
    rows = soup.select("table.is-w748 tbody tr")

    boats = []
    for i,row in enumerate(rows, start=1):
        tds = row.find_all("td")
        boats.append({
            "boat_no": i,
            "winrate": float(tds[4].text.strip() or 0),
            "st_avg": float(tds[6].text.strip() or 0.20),
            "motor_2rate": float(tds[9].text.strip().replace("%","") or 0)
        })

    if len(boats) != 6:
        raise ValueError("出走表取得失敗")

    return boats

# =========================
# オッズ取得（三連単）
# =========================
def get_trifecta_odds(race_date, place, race_no):
    ymd = race_date.strftime("%Y%m%d")
    jcd = PLACE_CODES[place]

    url = f"https://www.boatrace.jp/owpc/pc/race/odds3t?rno={race_no}&jcd={jcd}&hd={ymd}"
    res = requests.get(url, headers=HEADERS, timeout=10)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")
    odds_map = {}

    rows = soup.select("table.is-w748 tbody tr")
    for row in rows:
        tds = row.find_all("td")
        if len(tds) < 6:
            continue
        combo = tds[0].text.strip()
        try:
            odds_map[combo] = float(tds[-1].text.strip())
        except:
            continue

    return odds_map

# =========================
# スコア
# =========================
def st_score(st):
    return max(0, min(1, (0.25 - st) / 0.13))

def score_pre(b):
    return (
        (b["motor_2rate"]/100)*0.35 +
        min(1,b["winrate"]/7)*0.30 +
        FRAME_BONUS[b["boat_no"]]*0.20 +
        st_score(b["st_avg"])*0.15
    )

# =========================
# 三連単6点
# =========================
def generate_6(boats):
    scored = sorted([(b, score_pre(b)) for b in boats],
                    key=lambda x:x[1], reverse=True)
    res=[]
    for a,_ in scored[:2]:
        for b,_ in scored[1:4]:
            if a["boat_no"]==b["boat_no"]: continue
            for c,_ in scored:
                if c["boat_no"] in (a["boat_no"],b["boat_no"]): continue
                res.append(f"{a['boat_no']}-{b['boat_no']}-{c['boat_no']}")
                if len(res)==6:
                    return res
    return res

# =========================
# 表示用
# =========================
def color_text(tri):
    return "-".join(
        f"<span style='color:{BOAT_COLORS[int(x)]};font-weight:bold;font-size:20px'>{x}</span>"
        for x in tri.split("-")
    )

# =========================
# UI
# =========================
st.title("🚤 競艇AI予想（iPhone対応）")

c1,c2,c3 = st.columns(3)
with c1:
    race_date = st.date_input("日付", value=date.today())
with c2:
    place = st.selectbox("開催場", PLACE_CODES.keys())
with c3:
    race_no = st.selectbox("レース", [str(i) for i in range(1,13)])

# =========================
# 予想実行
# =========================
if st.button("展示前で予想する", use_container_width=True):
    boats = get_boat_data_pre_real(race_date, place, race_no)
    preds = generate_6(boats)
    st.session_state.preds = preds

    try:
        st.session_state.odds_map = get_trifecta_odds(race_date, place, race_no)
    except:
        st.session_state.odds_map = {}

# =========================
# 予想表示
# =========================
if st.session_state.preds:
    st.markdown("### 📌 予想6点")
    for i,p in enumerate(st.session_state.preds,1):
        st.markdown(f"**予想{i}：** {color_text(p)}", unsafe_allow_html=True)

# =========================
# 結果入力
# =========================
st.markdown("---")
st.subheader("📝 結果入力")

result = st.text_input("実際の三連単（例: 1-2-3）")
bought = st.radio("このレースは買いましたか？", ["買った","買ってない"], horizontal=True)

if st.button("結果を保存"):
    if result:
        hit = result in st.session_state.preds
        bet = 600 if bought=="買った" else 0

        ret = 0
        if hit and bought=="買った":
            if result in st.session_state.odds_map:
                ret = int(100 * st.session_state.odds_map[result])
            else:
                ret = 100 * 20

        st.session_state.history.append({
            "hit": hit,
            "bought": bought=="買った",
            "bet": bet,
            "ret": ret
        })
        st.success("保存しました")

# =========================
# 集計
# =========================
def calc(records):
    if not records:
        return 0,0
    hits = sum(1 for r in records if r["hit"])
    bet = sum(r["bet"] for r in records)
    ret = sum(r["ret"] for r in records)
    hit_rate = hits/len(records)*100
    rec = ret/bet*100 if bet>0 else 0
    return hit_rate, rec

st.markdown("---")
st.subheader("📊 成績")

all_hr, all_rec = calc(st.session_state.history)
buy_hr, buy_rec = calc([r for r in st.session_state.history if r["bought"]])

cA,cB = st.columns(2)
with cA:
    st.markdown("### 🟩 全予想")
    st.write(f"的中率：{all_hr:.1f}%")
    st.write(f"回収率：{all_rec:.1f}%")

with cB:
    st.markdown("### 🟦 購入レース")
    st.write(f"的中率：{buy_hr:.1f}%")
    st.write(f"回収率：{buy_rec:.1f}%")
