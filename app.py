import re
import datetime as dt
from typing import Dict, List

import numpy as np
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup
import plotly.graph_objects as go

import FinanceDataReader as fdr
from pykrx import stock

st.set_page_config(page_title="ShadowTrade Pro", page_icon="📈", layout="wide")

# --------------------------
# Premium UI (dark + glass + 3D)
# --------------------------
st.markdown(
    """
<style>
:root {
  --bg1:#050914;
  --bg2:#0a1330;
  --card:#0d1b3ad9;
  --text:#e8eeff;
  --sub:#a8b5d9;
  --accent:#5bc0ff;
  --accent2:#8a6bff;
  --ok:#35d39a;
}

.stApp {
  background:
    radial-gradient(1200px 500px at 10% -10%, #18306b55, transparent 60%),
    radial-gradient(1000px 500px at 90% -20%, #542f8a55, transparent 60%),
    linear-gradient(145deg, var(--bg1), var(--bg2));
  color: var(--text);
}

.main .block-container {
  max-width: 1200px;
  padding-top: 1.3rem;
  padding-bottom: 2.2rem;
}

.hero {
  border-radius: 22px;
  padding: 1.2rem 1.4rem;
  margin-bottom: 0.9rem;
  background: linear-gradient(160deg, #10224df0, #101c38f0);
  border: 1px solid #3f63a455;
  box-shadow:
    0 18px 35px #00000066,
    inset 0 1px 0 #a7c5ff33,
    inset 0 -1px 0 #00000055;
}

.hero h1 {
  font-size: 1.65rem;
  margin: 0;
  letter-spacing: 0.2px;
}

.hero p {
  margin: 0.35rem 0 0;
  color: var(--sub);
}

.glass {
  border-radius: 20px;
  padding: 1rem 1.05rem;
  background: linear-gradient(165deg, #132a58d9, #0d1f45d9);
  border: 1px solid #4264a85a;
  box-shadow:
    0 10px 26px #00000066,
    inset 0 1px 0 #c2d4ff29,
    inset 0 -1px 0 #00000055;
  margin-bottom: 1rem;
}

.metric-chip {
  display: inline-block;
  margin: 0.1rem 0.35rem 0.4rem 0;
  padding: 0.42rem 0.72rem;
  border-radius: 999px;
  border: 1px solid #5a81c84b;
  background: linear-gradient(145deg, #132b5a, #0c1b3d);
  color: #d8e5ff;
  font-size: 0.82rem;
}

.stTabs [data-baseweb="tab-list"] {
  gap: 0.35rem;
}

.stTabs [data-baseweb="tab"] {
  background: linear-gradient(145deg,#102247,#0b1734);
  border: 1px solid #3d63ac59;
  border-radius: 13px;
  color: #c7d6ff;
  padding: 0.4rem 0.85rem;
  height: 2.4rem;
}

.stTabs [aria-selected="true"] {
  background: linear-gradient(145deg,#1a3a78,#142957);
  color: #fff;
  box-shadow: 0 8px 16px #00000055, inset 0 1px 0 #cde0ff2f;
}

div[data-testid="stDataFrame"] {
  border: 1px solid #4a69a452;
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 10px 20px #00000045;
}

.stButton > button {
  border-radius: 12px;
  border: 1px solid #5b89cc66;
  color: #e7efff;
  background: linear-gradient(145deg, #1a3e80, #123065);
  box-shadow: 0 8px 14px #00000050, inset 0 1px 0 #d7e6ff2a;
  font-weight: 600;
}

.stSelectbox > div > div,
.stTextInput > div > div > input,
.stTextArea textarea {
  background: #0d1c3f !important;
  color: #eaf0ff !important;
  border: 1px solid #4a67a05c !important;
  border-radius: 11px !important;
}

.small-note {
  color:#9db0df;
  font-size:0.82rem;
}

</style>
""",
    unsafe_allow_html=True,
)


# --------------------------
# Theme universe (editable)
# --------------------------
THEME_MAP: Dict[str, List[str]] = {
    "반도체": ["삼성전자", "SK하이닉스", "한미반도체", "리노공업", "DB하이텍", "원익IPS", "ISC"],
    "2차전지": ["에코프로", "에코프로비엠", "엘앤에프", "포스코퓨처엠", "LG에너지솔루션", "삼성SDI"],
    "로봇": ["레인보우로보틱스", "두산로보틱스", "로보스타", "유일로보틱스", "에스피지"],
    "방산": ["한화에어로스페이스", "LIG넥스원", "현대로템", "한국항공우주", "풍산"],
    "전력": ["LS ELECTRIC", "효성중공업", "HD현대일렉트릭", "일진전기", "가온전선"],
    "원전": ["두산에너빌리티", "한전기술", "한전KPS", "우리기술", "비에이치아이"],
    "조선": ["HD한국조선해양", "HD현대중공업", "한화오션", "삼성중공업", "HSD엔진"],
    "AI": ["NAVER", "카카오", "삼성전자", "SK하이닉스", "폴라리스오피스", "이스트소프트"],
    "양자": ["우리로", "엑스게이트", "드림시큐리티", "텔레필드", "케이씨에스"],
    "바이오": ["삼성바이오로직스", "셀트리온", "HLB", "알테오젠", "유한양행"],
}


@st.cache_data(ttl=60 * 30)
def get_krx_listing() -> pd.DataFrame:
    df = fdr.StockListing("KRX")
    keep = [c for c in ["Code", "Name", "Market", "Marcap"] if c in df.columns]
    df = df[keep].copy()
    df["Code"] = df["Code"].astype(str).str.zfill(6)
    return df


def latest_bday_str() -> str:
    d = dt.date.today()
    for i in range(7):
        day = d - dt.timedelta(days=i)
        s = day.strftime("%Y%m%d")
        try:
            if stock.get_market_ticker_list(s):
                return s
        except Exception:
            pass
    return d.strftime("%Y%m%d")


@st.cache_data(ttl=60 * 10)
def get_latest_ohlcv(date_str: str) -> pd.DataFrame:
    """pykrx 우선, 실패 시 빈 DF 반환(상위에서 FDR 폴백 처리)."""
    try:
        o = stock.get_market_ohlcv_by_ticker(date_str, market="ALL").reset_index()
        o = o.rename(columns={"티커": "Code", "종가": "close", "등락률": "chg_pct", "거래대금": "value"})
        o["Code"] = o["Code"].astype(str).str.zfill(6)
        return o[["Code", "close", "chg_pct", "value"]]
    except Exception:
        return pd.DataFrame(columns=["Code", "close", "chg_pct", "value"])


@st.cache_data(ttl=60 * 10)
def get_latest_marcap(date_str: str) -> pd.DataFrame:
    try:
        m = stock.get_market_cap_by_ticker(date_str, market="ALL").reset_index()
        m = m.rename(columns={"티커": "Code", "시가총액": "marcap"})
        m["Code"] = m["Code"].astype(str).str.zfill(6)
        return m[["Code", "marcap"]]
    except Exception:
        return pd.DataFrame(columns=["Code", "marcap"])


def fallback_price_snapshot(codes: List[str]) -> pd.DataFrame:
    """FDR 기반 폴백: 최근 10일에서 마지막 2개 거래일로 등락률/거래대금 근사치 생성."""
    rows = []
    end = dt.date.today()
    start = end - dt.timedelta(days=14)
    for code in codes:
        try:
            h = fdr.DataReader(code, start, end)
            if h is None or len(h) < 2:
                continue
            h = h.dropna()
            if len(h) < 2:
                continue
            last = h.iloc[-1]
            prev = h.iloc[-2]
            close = float(last["Close"])
            prev_close = float(prev["Close"])
            chg_pct = ((close / prev_close) - 1.0) * 100 if prev_close else 0.0
            value = float(last.get("Volume", 0)) * close
            rows.append({"Code": str(code).zfill(6), "close": close, "chg_pct": chg_pct, "value": value})
        except Exception:
            continue
    return pd.DataFrame(rows, columns=["Code", "close", "chg_pct", "value"])


@st.cache_data(ttl=60 * 8)
def fetch_news_titles(query: str, limit: int = 20) -> List[str]:
    url = f"https://search.naver.com/search.naver?where=news&query={query}"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    out = []
    for a in soup.select("a.news_tit")[:limit]:
        t = a.get("title") or a.get_text(" ", strip=True)
        if t:
            out.append(t)
    return out


@st.cache_data(ttl=60 * 10)
def fetch_news_links(query: str, limit: int = 10) -> List[tuple]:
    url = f"https://search.naver.com/search.naver?where=news&query={query}"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    out = []
    for a in soup.select("a.news_tit")[:limit]:
        title = a.get("title") or a.get_text(" ", strip=True)
        link = a.get("href")
        if title and link:
            out.append((title, link))
    return out


def minmax(s: pd.Series) -> pd.Series:
    if len(s) == 0 or s.max() == s.min():
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - s.min()) / (s.max() - s.min())


def infer_themes(name: str) -> List[str]:
    direct = [t for t, arr in THEME_MAP.items() if name in arr]
    if direct:
        return direct
    guessed = []
    try:
        blob = " ".join(fetch_news_titles(name, 25))
        for t in THEME_MAP.keys():
            if re.search(t, blob, re.IGNORECASE):
                guessed.append(t)
    except Exception:
        pass
    return guessed[:3]


def build_top(theme: str, min_marcap=500_000_000_000, top_n=10) -> pd.DataFrame:
    listing = get_krx_listing()
    if theme not in THEME_MAP:
        return pd.DataFrame()

    universe = pd.DataFrame({"Name": THEME_MAP[theme]})
    universe = universe.merge(listing[["Name", "Code", "Market"]], on="Name", how="left").dropna(subset=["Code"])

    ds = latest_bday_str()
    px = get_latest_ohlcv(ds)
    if px.empty:
        px = fallback_price_snapshot(universe["Code"].tolist())

    mc = get_latest_marcap(ds)
    # pykrx 실패 시 listing의 Marcap 사용
    if mc.empty and "Marcap" in listing.columns:
        mc = listing[["Code", "Marcap"]].rename(columns={"Marcap": "marcap"}).copy()

    df = universe.merge(px, on="Code", how="left").merge(mc, on="Code", how="left")
    # 가격정보가 없는 행 제거
    df = df.dropna(subset=["close", "chg_pct", "value"], how="any")
    # 시총 결측이면 0 처리 후 필터
    df["marcap"] = pd.to_numeric(df["marcap"], errors="coerce").fillna(0)
    df = df[df["marcap"] >= min_marcap].copy()
    if df.empty:
        return df

    # proxies for "실시간 조회순위" and 뉴스 모멘텀
    pop = {}
    hit = {}
    for n in df["Name"].tolist():
        try:
            t = fetch_news_titles(n, 20)
            pop[n] = float(len(t))
            hit[n] = len(fetch_news_titles(f"{n} 특징주", 20))
        except Exception:
            pop[n], hit[n] = 0.0, 0

    df["popularity"] = df["Name"].map(pop)
    df["news_hits"] = df["Name"].map(hit)

    # leader model from your rules
    # 거래대금 + 등락률 + 조회(관심) + 뉴스(재료)
    df["s_value"] = minmax(df["value"]) * 35
    df["s_chg"] = minmax(df["chg_pct"]) * 30
    df["s_pop"] = minmax(df["popularity"]) * 15
    df["s_news"] = minmax(df["news_hits"]) * 20
    df["leader_score"] = (df["s_value"] + df["s_chg"] + df["s_pop"] + df["s_news"]).round(2)

    return df.sort_values("leader_score", ascending=False).head(top_n)


@st.cache_data(ttl=60 * 10)
def fetch_hist(code: str, days: int = 240) -> pd.DataFrame:
    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    return fdr.DataReader(code, start, end)


def render_candle(code: str, name: str):
    df = fetch_hist(code)
    if df.empty:
        st.warning("차트 데이터가 없습니다.")
        return
    fig = go.Figure(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            increasing_line_color="#43d69f",
            decreasing_line_color="#ff6b87",
            name=name,
        )
    )
    fig.update_layout(
        height=450,
        margin=dict(l=8, r=8, t=36, b=8),
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        title=f"{name} ({code})",
    )
    st.plotly_chart(fig, use_container_width=True)


# --------------------------
# Header
# --------------------------
try:
    st.image("assets/logo.svg", use_container_width=True)
except Exception:
    pass

st.markdown(
    """
<div class="hero">
  <h1>ShadowTrade Pro · Theme Leaderboard</h1>
  <p>종목명 기반 테마 탐색 → 주도주 점수화(거래대금/등락률/관심도/뉴스 모멘텀) → 뉴스 + 3D 감성 차트</p>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<span class="metric-chip">거래대금 중심</span>
<span class="metric-chip">등락률 상위 반영</span>
<span class="metric-chip">실시간 관심 대리지표</span>
<span class="metric-chip">특징주 뉴스 모멘텀</span>
""",
    unsafe_allow_html=True,
)

listing = get_krx_listing()
all_names = set(listing["Name"].tolist())

if "top_df" not in st.session_state:
    st.session_state.top_df = pd.DataFrame()
if "selected_theme" not in st.session_state:
    st.session_state.selected_theme = "반도체"


# --------------------------
# Tabs
# --------------------------
tab1, tab2, tab3, tab4 = st.tabs(["키워드", "TOP10", "사전(테마)", "설정"])

with tab1:
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.subheader("키워드/종목 입력")
    stock_name = st.text_input("종목명", placeholder="예) 삼성전자")

    col_a, col_b = st.columns([1, 1])
    with col_a:
        run = st.button("🔎 찾기", use_container_width=True)
    with col_b:
        refresh = st.button("↻ TOP10 갱신", use_container_width=True)

    if run or refresh:
        if not stock_name:
            st.warning("종목명을 입력해 주세요.")
        elif stock_name not in all_names:
            st.error("KRX 상장 종목명 기준으로 정확히 입력해 주세요.")
        else:
            themes = infer_themes(stock_name)
            if not themes:
                themes = ["반도체", "AI", "2차전지", "로봇"]
            st.session_state.selected_theme = themes[0]
            st.success(f"연관 테마 추정: {', '.join(themes)}")
            st.session_state.top_df = build_top(st.session_state.selected_theme, top_n=10)

    st.markdown("<p class='small-note'>* 시총 5천억 미만 종목은 자동 제외됩니다.</p>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.subheader(f"주도주 Top10 · {st.session_state.selected_theme}")

    if st.session_state.top_df.empty:
        st.info("키워드 탭에서 종목명을 입력하고 찾기를 눌러 주세요.")
    else:
        df = st.session_state.top_df.copy()
        show = df[["Name", "Code", "Market", "chg_pct", "value", "marcap", "popularity", "news_hits", "leader_score"]]
        show.columns = ["종목", "코드", "시장", "등락률(%)", "거래대금", "시총", "관심도", "뉴스건수", "주도점수"]
        st.dataframe(show, use_container_width=True, hide_index=True)

        st.caption("주도점수 = 거래대금(35) + 등락률(30) + 관심도(15) + 뉴스모멘텀(20)")

        picked = st.selectbox("상세 보기 종목", show["종목"].tolist())
        r = df[df["Name"] == picked].iloc[0]

        c1, c2 = st.columns([1.4, 1])
        with c1:
            render_candle(r["Code"], r["Name"])
        with c2:
            st.markdown("#### 📰 관련 뉴스")
            try:
                links = fetch_news_links(f"{picked} 특징주", 10)
                if not links:
                    st.write("- 뉴스가 충분히 없습니다.")
                for title, link in links:
                    st.markdown(f"- [{title}]({link})")
            except Exception as e:
                st.warning(f"뉴스 로딩 실패: {e}")

    st.markdown('</div>', unsafe_allow_html=True)

with tab3:
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.subheader("테마 사전")
    theme = st.selectbox("테마 선택", list(THEME_MAP.keys()), index=list(THEME_MAP.keys()).index(st.session_state.selected_theme) if st.session_state.selected_theme in THEME_MAP else 0)
    st.session_state.selected_theme = theme

    stocks = THEME_MAP.get(theme, [])
    st.markdown("  ".join([f"`{s}`" for s in stocks]))

    if st.button("이 테마로 TOP10 재계산", use_container_width=True):
        st.session_state.top_df = build_top(theme, top_n=10)
        st.success("갱신 완료")
    st.markdown('</div>', unsafe_allow_html=True)

with tab4:
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.subheader("설정")
    top_n = st.slider("TOP N", 5, 20, 10)
    min_cap = st.number_input("최소 시가총액(원)", value=500_000_000_000, step=100_000_000_000)

    if st.button("현재 테마에 설정 적용", use_container_width=True):
        st.session_state.top_df = build_top(st.session_state.selected_theme, min_marcap=int(min_cap), top_n=int(top_n))
        st.success("설정 반영 완료")

    st.markdown("<p class='small-note'>실시간 HTS(0186/0181/0198) 원천과 1:1 동일하지는 않으며, 공개 데이터 기반 근사 모델입니다.</p>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
