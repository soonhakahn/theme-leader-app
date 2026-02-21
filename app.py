import re
import datetime as dt
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup
import plotly.graph_objects as go

import FinanceDataReader as fdr
from pykrx import stock

st.set_page_config(page_title="테마 주도주 탐색기", layout="wide")

# --- 간단 테마 DB (확장 가능) ---
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


@dataclass
class LeaderRow:
    code: str
    name: str
    theme: str
    chg_pct: float
    value: float
    marcap: float
    popularity: float
    news_hits: int
    score: float


@st.cache_data(ttl=60 * 30)
def get_krx_listing() -> pd.DataFrame:
    df = fdr.StockListing("KRX")
    df = df[["Code", "Name", "Market", "Sector", "Industry", "Marcap"]].copy()
    df["Code"] = df["Code"].astype(str).str.zfill(6)
    return df


@st.cache_data(ttl=60 * 10)
def get_latest_ohlcv_and_value(date_str: str) -> pd.DataFrame:
    ohlcv = stock.get_market_ohlcv_by_ticker(date_str, market="ALL")
    ohlcv = ohlcv.rename(columns={"종가": "close", "등락률": "chg_pct", "거래대금": "value"})
    ohlcv.index.name = "Code"
    ohlcv = ohlcv.reset_index()
    ohlcv["Code"] = ohlcv["Code"].astype(str).str.zfill(6)
    return ohlcv[["Code", "close", "chg_pct", "value"]]


@st.cache_data(ttl=60 * 10)
def get_latest_marcap(date_str: str) -> pd.DataFrame:
    mc = stock.get_market_cap_by_ticker(date_str, market="ALL").reset_index()
    mc = mc.rename(columns={"티커": "Code", "시가총액": "marcap"})
    mc["Code"] = mc["Code"].astype(str).str.zfill(6)
    return mc[["Code", "marcap"]]


def latest_bday_str() -> str:
    d = dt.date.today()
    for i in range(7):
        day = d - dt.timedelta(days=i)
        s = day.strftime("%Y%m%d")
        try:
            test = stock.get_market_ticker_list(s)
            if test:
                return s
        except Exception:
            pass
    return d.strftime("%Y%m%d")


@st.cache_data(ttl=60 * 10)
def fetch_naver_news_titles(query: str, limit: int = 30) -> List[str]:
    url = f"https://search.naver.com/search.naver?where=news&query={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    titles = []
    for tag in soup.select("a.news_tit")[:limit]:
        t = tag.get("title") or tag.get_text(" ", strip=True)
        if t:
            titles.append(t)
    return titles


@st.cache_data(ttl=60 * 30)
def build_name_to_code() -> Dict[str, str]:
    ls = get_krx_listing()
    return {row.Name: row.Code for row in ls.itertuples()}


def infer_themes(stock_name: str) -> List[str]:
    found = [theme for theme, names in THEME_MAP.items() if stock_name in names]
    if found:
        return found

    # 뉴스 키워드 기반 가벼운 추정
    guessed = []
    try:
        titles = " ".join(fetch_naver_news_titles(stock_name, 20))
        for theme in THEME_MAP.keys():
            if re.search(theme, titles, re.IGNORECASE):
                guessed.append(theme)
    except Exception:
        pass

    return guessed[:3]


def popularity_proxy(names: List[str]) -> Dict[str, float]:
    # 네이버 뉴스 검색결과 수를 인기 대리값으로 사용
    result = {}
    for n in names:
        try:
            titles = fetch_naver_news_titles(n, limit=20)
            result[n] = float(len(titles))
        except Exception:
            result[n] = 0.0
    return result


def news_hits_for_name(name: str) -> int:
    try:
        return len(fetch_naver_news_titles(f"{name} 특징주", limit=20))
    except Exception:
        return 0


def minmax(series: pd.Series) -> pd.Series:
    if series.max() == series.min():
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - series.min()) / (series.max() - series.min())


def calc_leaders(theme: str, top_n: int = 10, min_marcap_krw: int = 500_000_000_000) -> pd.DataFrame:
    name_code = build_name_to_code()
    candidates = [n for n in THEME_MAP.get(theme, []) if n in name_code]
    if not candidates:
        return pd.DataFrame()

    date_str = latest_bday_str()
    listing = get_krx_listing()
    px = get_latest_ohlcv_and_value(date_str)
    mc = get_latest_marcap(date_str)

    cand = pd.DataFrame({"Name": candidates})
    cand["Code"] = cand["Name"].map(name_code)
    df = cand.merge(px, on="Code", how="left").merge(mc, on="Code", how="left")
    df = df.merge(listing[["Code", "Market"]], on="Code", how="left")

    # 인기/뉴스
    pop_map = popularity_proxy(candidates)
    df["popularity"] = df["Name"].map(pop_map).fillna(0)
    df["news_hits"] = df["Name"].map(news_hits_for_name)

    # 필터: 시총 5천억 이상
    df = df[df["marcap"] >= min_marcap_krw].copy()
    if df.empty:
        return df

    # 주도주 점수(요청 기준 반영)
    # 거래대금(35) + 상승률(30) + 인기검색(15) + 뉴스모멘텀(20)
    df["s_value"] = minmax(df["value"]) * 35
    df["s_chg"] = minmax(df["chg_pct"]) * 30
    df["s_pop"] = minmax(df["popularity"]) * 15
    df["s_news"] = minmax(df["news_hits"]) * 20
    df["leader_score"] = df[["s_value", "s_chg", "s_pop", "s_news"]].sum(axis=1)

    df = df.sort_values("leader_score", ascending=False).head(top_n)
    return df


@st.cache_data(ttl=60 * 10)
def fetch_price_history(code: str, days: int = 120) -> pd.DataFrame:
    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    df = fdr.DataReader(code, start, end)
    return df


def render_chart(code: str, name: str):
    hist = fetch_price_history(code)
    if hist.empty:
        st.warning("차트 데이터가 없습니다.")
        return

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=hist.index,
                open=hist["Open"],
                high=hist["High"],
                low=hist["Low"],
                close=hist["Close"],
                name=name,
            )
        ]
    )
    fig.update_layout(height=460, xaxis_rangeslider_visible=False, title=f"{name} ({code})")
    st.plotly_chart(fig, use_container_width=True)


def render_news(name: str):
    st.markdown(f"### 📰 {name} 관련 뉴스")
    try:
        titles = fetch_naver_news_titles(f"{name} 특징주", limit=12)
        if not titles:
            st.info("관련 뉴스가 충분히 수집되지 않았습니다.")
            return
        for t in titles:
            st.write(f"- {t}")
    except Exception as e:
        st.warning(f"뉴스 수집 실패: {e}")


st.title("📈 테마 주도주 Top 10 탐색기 (MVP)")
st.caption("입력 종목 기반으로 관련 테마를 찾고, 거래대금/상승률/인기/뉴스를 결합해 주도주를 점수화합니다.")

listing = get_krx_listing()
stock_input = st.text_input("종목명 입력", placeholder="예: 삼성전자")

if stock_input:
    if stock_input not in set(listing["Name"]):
        st.error("종목명을 정확히 입력해 주세요 (KRX 상장 종목명 기준).")
        st.stop()

    themes = infer_themes(stock_input)
    if not themes:
        st.warning("테마를 자동 추정하지 못했습니다. 아래에서 직접 선택해 주세요.")
        themes = list(THEME_MAP.keys())

    selected_theme = st.selectbox("관련 테마", themes)
    top_n = st.slider("Top N", 5, 20, 10)

    leaders = calc_leaders(selected_theme, top_n=top_n)
    if leaders.empty:
        st.warning("조건(시총 5천억+)을 만족하는 종목이 없습니다.")
        st.stop()

    show = leaders[["Name", "Code", "Market", "chg_pct", "value", "marcap", "popularity", "news_hits", "leader_score"]].copy()
    show.columns = ["종목", "코드", "시장", "등락률(%)", "거래대금", "시총", "인기점수", "뉴스건수", "주도점수"]

    st.markdown("## ✅ 주도주 Top 리스트")
    st.dataframe(show, use_container_width=True)

    st.info("주도점수 산식: 거래대금(35) + 등락률(30) + 인기검색대리(15) + 뉴스모멘텀(20) / 시총 5천억 이상 필터")

    pick = st.selectbox("차트/뉴스 볼 종목", show["종목"].tolist())
    row = leaders[leaders["Name"] == pick].iloc[0]

    col1, col2 = st.columns([1.35, 1])
    with col1:
        render_chart(row["Code"], row["Name"])
    with col2:
        render_news(row["Name"])

st.markdown("---")
st.caption("주의: 본 앱은 투자판단 보조 도구이며, 실시간 HTS 데이터(0186/0181/0198)와 1:1 동일하지 않을 수 있습니다.")
