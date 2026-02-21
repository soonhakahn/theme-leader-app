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
  font-size: clamp(1.1rem, 4.6vw, 1.65rem);
  margin: 0;
  letter-spacing: 0.2px;
  line-height: 1.2;
  word-break: keep-all;
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



@media (max-width: 768px) {
  .main .block-container {padding-top: 0.7rem; padding-left: 0.7rem; padding-right: 0.7rem;}
  .hero {padding: 0.85rem 0.9rem; border-radius: 16px;}
  .hero p {font-size: 0.86rem; line-height: 1.3;}
  .glass {padding: 0.75rem 0.75rem; border-radius: 14px;}
  .stTabs [data-baseweb="tab"] {padding: 0.34rem 0.62rem; height: 2.1rem; font-size: 0.88rem;}
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

THEME_KEYWORDS: Dict[str, List[str]] = {
    "반도체": ["반도체", "HBM", "메모리", "파운드리"],
    "2차전지": ["2차전지", "배터리", "양극재", "음극재", "전해질"],
    "로봇": ["로봇", "자동화", "협동로봇"],
    "방산": ["방산", "미사일", "국방", "K-방산"],
    "전력": ["전력", "변압기", "전선", "전력기기"],
    "원전": ["원전", "SMR", "원자력"],
    "조선": ["조선", "LNG선", "선박"],
    "AI": ["AI", "인공지능", "LLM", "데이터센터"],
    "양자": ["양자", "퀀텀", "양자컴퓨팅"],
    "바이오": ["바이오", "신약", "임상", "항체"],
}


@st.cache_data(ttl=60 * 30)
def get_krx_listing() -> pd.DataFrame:
    df = fdr.StockListing("KRX")
    keep = [c for c in ["Code", "Name", "Market", "Sector", "Industry", "Marcap"] if c in df.columns]
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


def infer_themes(name: str, listing_df: pd.DataFrame) -> List[str]:
    # 1) 직접 사전 매칭
    direct = [t for t, arr in THEME_MAP.items() if name in arr]
    if direct:
        return direct

    scored: Dict[str, int] = {}

    # 2) 뉴스 키워드 매칭(테마명 + 동의어)
    try:
        blob = " ".join(fetch_news_titles(name, 30))
        for theme, kws in THEME_KEYWORDS.items():
            cnt = 0
            for kw in [theme] + kws:
                cnt += len(re.findall(re.escape(kw), blob, flags=re.IGNORECASE))
            if cnt > 0:
                scored[theme] = scored.get(theme, 0) + cnt
    except Exception:
        pass

    # 3) 업종/섹터 힌트 매칭
    row = listing_df[listing_df["Name"] == name]
    if not row.empty:
        txt = " ".join(
            [
                str(row.iloc[0].get("Sector", "")),
                str(row.iloc[0].get("Industry", "")),
            ]
        )
        for theme, kws in THEME_KEYWORDS.items():
            cnt = 0
            for kw in [theme] + kws:
                cnt += len(re.findall(re.escape(kw), txt, flags=re.IGNORECASE))
            if cnt > 0:
                scored[theme] = scored.get(theme, 0) + cnt

    ranked = [k for k, _ in sorted(scored.items(), key=lambda x: x[1], reverse=True)]
    return ranked[:4]


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
    st.plotly_chart(fig, width="stretch")


def render_stock_analysis(code: str, name: str, listing_df: pd.DataFrame):
    h = fetch_hist(code)
    if h is None or h.empty or len(h) < 5:
        st.info("분석 데이터가 충분하지 않습니다.")
        return

    close = h["Close"].dropna()
    vol = h["Volume"].fillna(0)

    latest = float(close.iloc[-1])
    ret_1m = (latest / float(close.iloc[-21]) - 1) * 100 if len(close) >= 21 else np.nan
    ret_3m = (latest / float(close.iloc[-63]) - 1) * 100 if len(close) >= 63 else np.nan

    ma20 = close.rolling(20).mean().iloc[-1] if len(close) >= 20 else np.nan
    ma60 = close.rolling(60).mean().iloc[-1] if len(close) >= 60 else np.nan

    vol20 = vol.rolling(20).mean().iloc[-1] if len(vol) >= 20 else np.nan
    vol_ratio = float(vol.iloc[-1] / vol20) if vol20 and not np.isnan(vol20) else np.nan

    high_52w = float(close.tail(252).max()) if len(close) >= 2 else latest
    low_52w = float(close.tail(252).min()) if len(close) >= 2 else latest

    info = listing_df[listing_df["Code"] == code]
    market = info["Market"].iloc[0] if not info.empty and "Market" in info.columns else "-"
    sector = info["Sector"].iloc[0] if not info.empty and "Sector" in info.columns else "-"
    industry = info["Industry"].iloc[0] if not info.empty and "Industry" in info.columns else "-"

    st.markdown("#### 📊 종목 분석")
    c1, c2, c3 = st.columns(3)
    c1.metric("1개월 수익률", f"{ret_1m:.2f}%" if pd.notna(ret_1m) else "-")
    c2.metric("3개월 수익률", f"{ret_3m:.2f}%" if pd.notna(ret_3m) else "-")
    c3.metric("거래량(20일 대비)", f"{vol_ratio:.2f}x" if pd.notna(vol_ratio) else "-")

    trend = "상승" if pd.notna(ma20) and pd.notna(ma60) and latest > ma20 > ma60 else "중립/약세"
    st.write(f"- 추세: **{trend}**")
    st.write(f"- 현재가: **{latest:,.0f}원** / 52주 고가 **{high_52w:,.0f}원**, 52주 저가 **{low_52w:,.0f}원**")
    st.write(f"- 시장: **{market}**, 섹터: **{sector}**, 업종: **{industry}**")


# --------------------------
# Header
# --------------------------
try:
    st.image("assets/logo.svg", width="stretch")
except Exception:
    pass

st.markdown(
    """
<div class="hero">
  <h1>ShadowTrade Pro</h1>
  <p>테마 주도주 Top10 · 차트 · 종목분석 · 뉴스</p>
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
if "inferred_themes" not in st.session_state:
    st.session_state.inferred_themes = []
if "picked_stock" not in st.session_state:
    st.session_state.picked_stock = None
if "ultra_mobile" not in st.session_state:
    st.session_state.ultra_mobile = False

if st.session_state.ultra_mobile:
    st.markdown(
        """
<style>
@media (max-width: 900px) {
  .main .block-container {padding-left: 0.55rem; padding-right: 0.55rem;}
  .stButton > button {min-height: 46px; font-size: 1rem;}
  .stSelectbox label, .stTextInput label, .stNumberInput label {font-size: 0.95rem;}
  .stTabs [data-baseweb="tab"] {font-size: 0.92rem; min-width: 74px;}
  p, li, .small-note {font-size: 0.94rem !important;}
}
</style>
""",
        unsafe_allow_html=True,
    )

# --------------------------
# Tabs
# --------------------------
tab1, tab2, tab3, tab4 = st.tabs(["키워드", "TOP10", "사전(테마)", "설정"])

with tab1:
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.subheader("키워드/종목 입력")
    name_list = sorted(list(all_names))
    picked_name = st.selectbox("종목명 목록에서 선택", options=name_list, index=name_list.index("삼성전자") if "삼성전자" in name_list else 0)
    typed_name = st.text_input("또는 직접 입력", placeholder="예) 삼성전자")
    stock_name = typed_name.strip() if typed_name.strip() else picked_name

    col_a, col_b = st.columns([1, 1])
    with col_a:
        run = st.button("🔎 찾기", width="stretch")
    with col_b:
        refresh = st.button("↻ TOP10 갱신", width="stretch")

    if run or refresh:
        if not stock_name:
            st.warning("종목명을 입력해 주세요.")
        elif stock_name not in all_names:
            st.error("KRX 상장 종목명 기준으로 정확히 입력해 주세요.")
        else:
            themes = infer_themes(stock_name, listing)
            st.session_state.inferred_themes = themes
            if themes:
                st.session_state.selected_theme = themes[0]
                st.success(f"연관 테마 추정: {', '.join(themes)}")
                st.session_state.top_df = build_top(st.session_state.selected_theme, top_n=10)
            else:
                st.warning("이 종목의 테마를 자동으로 특정하지 못했습니다. 아래에서 테마를 직접 선택해 주세요.")

    theme_candidates = st.session_state.inferred_themes if st.session_state.inferred_themes else list(THEME_MAP.keys())[:6]
    st.markdown("#### 연관 테마 빠른 선택")
    cols = st.columns(min(4, len(theme_candidates)))
    for i, t in enumerate(theme_candidates):
        with cols[i % len(cols)]:
            if st.button(f"테마: {t}", key=f"theme_btn_{t}", width="stretch"):
                st.session_state.selected_theme = t
                st.session_state.top_df = build_top(t, top_n=10)

    st.markdown("#### 관련 테마주 버튼")
    stocks = THEME_MAP.get(st.session_state.selected_theme, [])
    if stocks:
        cols2 = st.columns(3)
        for i, s in enumerate(stocks[:12]):
            with cols2[i % 3]:
                if st.button(s, key=f"stock_btn_{s}", width="stretch"):
                    st.session_state.picked_stock = s

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
        st.dataframe(show, width="stretch", hide_index=True)

        st.caption("주도점수 = 거래대금(35) + 등락률(30) + 관심도(15) + 뉴스모멘텀(20)")

        st.markdown("#### Top10 빠른 선택")
        quick_cols = st.columns(2)
        for i, nm in enumerate(show["종목"].tolist()):
            with quick_cols[i % 2]:
                if st.button(f"{i+1}. {nm}", key=f"top_pick_{nm}", width="stretch"):
                    st.session_state.picked_stock = nm

        options = show["종목"].tolist()
        default_idx = 0
        if st.session_state.picked_stock in options:
            default_idx = options.index(st.session_state.picked_stock)
        picked = st.selectbox("상세 보기 종목", options, index=default_idx)
        r = df[df["Name"] == picked].iloc[0]

        dtab1, dtab2, dtab3 = st.tabs(["주가 흐름", "종목분석", "관련 뉴스"])
        with dtab1:
            render_candle(r["Code"], r["Name"])
        with dtab2:
            render_stock_analysis(r["Code"], r["Name"], listing)
        with dtab3:
            st.markdown("#### 📰 관련 뉴스")
            try:
                links = fetch_news_links(f"{picked} 특징주", 12)
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

    if st.button("이 테마로 TOP10 재계산", width="stretch"):
        st.session_state.top_df = build_top(theme, top_n=10)
        st.success("갱신 완료")
    st.markdown('</div>', unsafe_allow_html=True)

with tab4:
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.subheader("설정")
    top_n = st.slider("TOP N", 5, 20, 10)
    min_cap = st.number_input("최소 시가총액(원)", value=500_000_000_000, step=100_000_000_000)
    st.checkbox("초모바일(아이폰 미니) 모드", key="ultra_mobile")

    if st.button("현재 테마에 설정 적용", width="stretch"):
        st.session_state.top_df = build_top(st.session_state.selected_theme, min_marcap=int(min_cap), top_n=int(top_n))
        st.success("설정 반영 완료")

    st.markdown("<p class='small-note'>실시간 HTS(0186/0181/0198) 원천과 1:1 동일하지는 않으며, 공개 데이터 기반 근사 모델입니다.</p>", unsafe_allow_html=True)
    st.markdown("<p class='small-note'>초모바일 모드를 켜면 버튼/폰트/여백이 더 크게 조정됩니다.</p>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
