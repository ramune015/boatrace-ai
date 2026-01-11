import streamlit as st
import itertools
import requests
from bs4 import BeautifulSoup
from datetime import date

st.set_page_config(page_title="競艇AI予想", layout="wide")

# ===== 定数 =====
PLACES = [
    "桐生","戸田","江戸川","平和島","多摩川","浜名湖","蒲郡","常滑",
    "津","三国","びわこ","住之江","尼崎","鳴門","丸亀","児島",
    "宮島","徳山","下関","若松","芦屋","福岡","唐津","大村"
]

PLACE_CODE = {
    "桐生":"01","戸田":"02","江戸川":"03","平和島":"04","多摩川":"05",
    "浜名湖":"06","蒲郡":"07","常滑":"08","津":"09","三国":"10",
    "びわこ":"11","住之江":"12","尼崎":"13","鳴門":"14","丸亀":"15",
    "児島":"16","宮島":"17","徳山":"18","下関":"19","若松":"20",
    "芦屋":"21","福岡":"22","唐津":"23","大村":"24"
}

LANE_COLORS = {
    1:"#FFFFFF",2:"#000000",3:"#FF0000",
    4:"#0000FF",5:"#FFFF00",6:"#00AA00"
}

BET_UNIT = 100  # 1点100円

# ===== セッション =====
if "boats" not in st.session_state:
    st.session_state.boats = []
if "predictions" not in st.session_state:
    st.session_state.predictions = []

# ===== 実データ取得 =====
def fetch_boatrace_data(race_date, place, race_no):
    ymd = race_date.strftime("%Y%m%d")
    jcd = PLACE_CODE[place]
    rno = f"{race_no:02d}"

    url = f"https://www.boatrace.jp/owpc/pc/race/racelist?rno={rno}&jcd={jcd}&hd={ymd}"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers, timeout=10)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")
    rows = soup.select("tbody tr")

    boats = []
    for i, row in enumerate(rows, start=1):
        tds = row.find_all("td")
        motor2 = float(tds[6].text.replace("%",""))
        motor3 = float(tds[7].text.replace("%",""))
        boats.append({
            "lane": i,
            "motor2": motor2,
            "motor3": motor3,
            "time": 6.80,
            "st": 0.15,
            "course": i
        })
    return boats

# ===== UI 上部 =====
st.title("🚤 競艇AI予想（実データ自動取得）")

c1,c2,c3 = st.columns(3)
with c1:
    race_date = st.date_input("日付", value=date.today())
with c2:
    place = st.selectbox("開催場所", PLACES)
with c3:
    race_no = st.selectbox("レース番号", list(range(1,13)))

if st.button("📥 実データ取得"):
    try:
        st.session_state.boats = fetch_boatrace_data(race_date, place, race_no)
        st.success("実データ取得完了")
    except:
        st.error("取得失敗（未開催 or 時間外）")

# ===== 出走表 =====
if st.session_state.boats:
    st.subheader("出走表（展示は手入力）")
    for b in st.session_state.boats:
        cols = st.columns(6)
        cols[0].markdown(f"**{b['lane']}号艇**")
        b["motor2"] = cols[1].number_input("2連率", value=b["motor2"], step=0.1, key=f"m2{b['lane']}")
        b["motor3"] = cols[2].number_input("3連率", value=b["motor3"], step=0.1, key=f"m3{b['lane']}")
        b["time"]   = cols[3].number_input("展示T", value=b["time"], step=0.01, key=f"t{b['lane']}")
        b["st"]     = cols[4].number_input("ST", value=b["st"], step=0.01, key=f"st{b['lane']}")
        b["course"] = cols[5].selectbox("進入", list(range(1,7)), index=b["lane"]-1, key=f"c{b['lane']}")

# ===== スコア =====
def score(b, avg):
    return (
        b["motor2"]/100*0.4 +
        b["motor3"]/100*0.2 +
        max(0, avg-b["time"])*0.25 +
        max(0, 0.2-b["st"])*1.5 +
        max(0, 7-b["course"])*0.05
    )

# ===== 予想 =====
if st.button("🎯 予想する"):
    boats = st.session_state.boats
    avg = sum(b["time"] for b in boats)/6
    for b in boats:
        b["score"] = score(b, avg)

    s = sorted(boats, key=lambda x:x["score"], reverse=True)
    honmei = s[:3]
    ana = sorted([b for b in s if b not in honmei], key=lambda x:x["motor2"], reverse=True)[0]

    preds = []
    for c in itertools.permutations([b["lane"] for b in honmei],3):
        preds.append({"type":"本線","combo":c,"odds":12.0,"bought":False})
    preds = preds[:6]

    preds += [
        {"type":"穴","combo":(ana["lane"],honmei[0]["lane"],honmei[1]["lane"]),"odds":45.0,"bought":False},
        {"type":"穴","combo":(ana["lane"],honmei[1]["lane"],honmei[0]["lane"]),"odds":60.0,"bought":False},
        {"type":"穴","combo":(honmei[0]["lane"],ana["lane"],honmei[1]["lane"]),"odds":38.0,"bought":False},
    ]
    st.session_state.predictions = preds

# ===== 表示 =====
if st.session_state.predictions:
    st.subheader("予想結果")
    for i,p in enumerate(st.session_state.predictions):
        cols = st.columns([1,4,2,1])
        cols[0].write(p["type"])
        combo=""
        for n in p["combo"]:
            combo+=f"<span style='background:{LANE_COLORS[n]};padding:6px;margin:2px'>{n}</span>"
        cols[1].markdown(combo, unsafe_allow_html=True)
        cols[2].write(p["odds"])
        p["bought"] = cols[3].checkbox("買う", key=f"buy{i}")

    # ===== 結果入力 =====
    st.subheader("📥 レース結果入力")
    r1,r2,r3 = st.columns(3)
    res = (
        r1.selectbox("1着", [1,2,3,4,5,6]),
        r2.selectbox("2着", [1,2,3,4,5,6]),
        r3.selectbox("3着", [1,2,3,4,5,6]),
    )
    payout = st.number_input("三連単 配当金（円）", value=0, step=10)

    # ===== 成績 =====
    def calc(preds, bought_only):
        tgt=[p for p in preds if (p["bought"] or not bought_only)]
        if not tgt:
            return 0,0
        hit=0
        spent=len(tgt)*BET_UNIT
        ret=0
        for p in tgt:
            if p["combo"]==res:
                hit+=1
                ret+=payout
        return round(hit/len(tgt)*100,1), round(ret/spent*100,1)

    st.subheader("📊 成績")
    h1,r1 = calc(st.session_state.predictions, True)
    h2,r2 = calc(st.session_state.predictions, False)

    st.write(f"🟢 買った分：的中率 {h1}% / 回収率 {r1}%")
    st.write(f"🔵 全予想　：的中率 {h2}% / 回収率 {r2}%")
