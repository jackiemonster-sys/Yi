import datetime
import math
import streamlit as st
import yfinance as yf

# 1. 基礎資料定義：八卦名稱、五行、對應先天數與卦數
BAGUA = {
    1: {"name": "乾", "symbol": "☰", "element": "金", "num": 1},
    2: {"name": "兌", "symbol": "☱", "element": "金", "num": 2},
    3: {"name": "離", "symbol": "☲", "element": "火", "num": 3},
    4: {"name": "震", "symbol": "☳", "element": "木", "num": 4},
    5: {"name": "巽", "symbol": "☴", "element": "木", "num": 5},
    6: {"name": "坎", "symbol": "☵", "element": "水", "num": 6},
    7: {"name": "艮", "symbol": "☶", "element": "土", "num": 7},
    0: {"name": "坤", "symbol": "☷", "element": "土", "num": 8},
}

# 季節月令五行旺衰判斷 (月分簡化為四季: 春木、夏火、秋金、冬水、四季末土)
SEASON_ELEMENT_MAP = {
    1: "水",
    2: "木",
    3: "木",
    4: "土",
    5: "火",
    6: "火",
    7: "土",
    8: "金",
    9: "金",
    10: "土",
    11: "水",
    12: "水",
}

# 五行生剋判定與漲跌趨勢係數 (base_factor)
ELEMENT_RELATIONS = {
    ("金", "金"): (
        "比和",
        "雙方勢均力敵，市場多空交戰，預計高位盤整或平盤出局。",
        "⚠️ 盤整",
        0.0,
    ),
    ("金", "木"): (
        "體克用",
        "耗費精力但能獲勝，過程可能震盪，但終能收紅。",
        "📈 偏多",
        0.5,
    ),
    ("金", "水"): (
        "體生用",
        "自身能量洩出，資金或動能不足，易開高走低。",
        "📉 偏空",
        -0.5,
    ),
    ("金", "火"): (
        "用克體",
        "受外力強烈壓制，主力拋售或利空襲來，收陰機率高。",
        "🔻 看跌",
        -1.2,
    ),
    ("金", "土"): (
        "用生體",
        "獲得外部大吉助力，買盤強勁，強勢看漲。",
        "🚀 大漲",
        1.5,
    ),
    ("木", "木"): (
        "比和",
        "動能相當，多方持續整理，波動不大。",
        "⚠️ 盤整",
        0.0,
    ),
    ("木", "火"): (
        "體生用",
        "動能過度消耗，追高風險大，易逢高拉回。",
        "📉 偏空",
        -0.5,
    ),
    ("木", "土"): (
        "體克用",
        "克服賣壓前行，小幅獲利，小漲作收。",
        "📈 偏多",
        0.5,
    ),
    ("木", "金"): (
        "用克體",
        "遇到強大拋售賣壓，空方佔優，跌勢較明顯。",
        "🔻 看跌",
        -1.2,
    ),
    ("木", "水"): (
        "用生體",
        "資金源源不絕挹注，多頭格局強勢。",
        "🚀 大漲",
        1.5,
    ),
    ("水", "水"): (
        "比和",
        "量能平平，隨波逐流，呈現窄幅震盪。",
        "⚠️ 盤整",
        0.0,
    ),
    ("水", "木"): (
        "體生用",
        "資金外流或動能潰散，獲利吐回。",
        "📉 偏空",
        -0.5,
    ),
    ("水", "火"): (
        "體克用",
        "多頭逆勢反攻，順利克服阻力，收紅可期。",
        "📈 偏多",
        0.5,
    ),
    ("水", "土"): (
        "用克體",
        "遭強烈利空擊中，觀望氣氛濃，股價承壓。",
        "🔻 看跌",
        -1.2,
    ),
    ("水", "金"): (
        "用生體",
        "水到渠成，市場買單積極，強勢衝高。",
        "🚀 大漲",
        1.5,
    ),
    ("火", "火"): (
        "比和",
        "熱度極高但多空分歧，震盪劇烈。",
        "⚠️ 高震盪",
        0.1,
    ),
    ("火", "土"): (
        "體生用",
        "追高力道不足，漲勢受阻，易拉回走低。",
        "📉 偏空",
        -0.5,
    ),
    ("火", "金"): (
        "體克用",
        "強力衝破賣壓牆，雖有震盪但終能獲勝。",
        "📈 偏多",
        0.5,
    ),
    ("火", "水"): (
        "用克體",
        "冷水灌頂，空頭力道強勁，慎防大跌。",
        "🔻 看跌",
        -1.2,
    ),
    ("火", "木"): (
        "用生體",
        "利多頻傳，資金力挺，強勢漲停或大漲。",
        "🚀 大漲",
        1.5,
    ),
    ("土", "土"): (
        "比和",
        "底部堅實，盤整蓄勢，變幅極小。",
        "⚠️ 盤整",
        0.0,
    ),
    ("土", "金"): (
        "體生用",
        "漲勁不足，逢高獲利了結賣壓沉重。",
        "📉 偏空",
        -0.5,
    ),
    ("土", "水"): (
        "體克用",
        "成功吸收籌碼，緩步墊高，小漲作收。",
        "📈 偏多",
        0.5,
    ),
    ("土", "木"): (
        "用克體",
        "主力洗盤拋售，支撐脆弱，偏空看待。",
        "🔻 看跌",
        -1.2,
    ),
    ("土", "火"): (
        "用生體",
        "買盤支撐力道強，震盪走高，利於多頭。",
        "🚀 大漲",
        1.5,
    ),
}


def get_stock_data_and_atr(stock_code: str, target_date: datetime.date):
    """抓取股價與計算近 20 日 ATR (平均真實波幅)"""
    digits = "".join(filter(str.isdigit, stock_code))
    if not digits:
        return None, None, "無效的股票代號"

    tickers = [f"{digits}.TW", f"{digits}.TWO"]
    # 抓取往前 45 天數據確保足夠計算 20 日 ATR
    start_date = target_date - datetime.timedelta(days=45)

    for ticker in tickers:
        df = yf.download(
            ticker, start=start_date, end=target_date, progress=False
        )
        if not df.empty and len(df) >= 5:
            # 展平多重欄位索引 (若有)
            if isinstance(df.columns, tuple) or hasattr(
                df.columns, "levels"
            ):
                df.columns = [col[0] for col in df.columns]

            # 取最近一筆交易日數據
            last_close = float(df["Close"].iloc[-1])
            actual_date = df.index[-1].strftime("%Y-%m-%d")

            # 計算 14 日 ATR
            high_low = df["High"] - df["Low"]
            high_cp = (df["High"] - df["Close"].shift(1)).abs()
            low_cp = (df["Low"] - df["Close"].shift(1)).abs()

            tr = (
                high_low.to_frame("hl")
                .join(high_cp.to_frame("hcp"))
                .join(low_cp.to_frame("lcp"))
                .max(axis=1)
            )
            atr = float(tr.rolling(14).mean().iloc[-1])

            # 防呆：若數據不夠計算 ATR，預設取股價的 2%
            if math.isnan(atr):
                atr = last_close * 0.02

            return last_close, atr, actual_date

    return None, None, "找不到該股票歷史價格與波動資料"


def calculate_season_factor(ti_element: str, month: int):
    """根據當月月令五行計算體卦旺衰權重"""
    season_element = SEASON_ELEMENT_MAP.get(month, "土")
    if ti_element == season_element:
        return 1.3, "當旺（氣勢最極盛）"

    # 五行相生對照
    element_generates = {
        "木": "火",
        "火": "土",
        "土": "金",
        "金": "水",
        "水": "木",
    }
    if element_generates.get(season_element) == ti_element:
        return 1.15, "相（受月令相生，次吉）"
    elif element_generates.get(ti_element) == season_element:
        return 0.85, "休（洩氣，力道較弱）"
    else:
        return 0.7, "囚/死（受月令克制，動能不足）"


def calculate_hexagram(
    stock_code: str,
    date_obj: datetime.date,
    prev_close: float,
    atr_val: float,
):
    """結合卦象、月令與 ATR 進行綜合價格推算"""
    digits = "".join(filter(str.isdigit, stock_code))
    stock_num = int(digits) if digits else 100

    year, month, day = date_obj.year, date_obj.month, date_obj.day

    # 1. 起卦
    upper_val = (stock_num + year + month + day) % 8
    upper_卦 = BAGUA[upper_val]

    lower_val = (stock_num + day) % 8
    lower_卦 = BAGUA[lower_val]

    yao_val = (stock_num + year + month + day) % 6
    moving_yao = 6 if yao_val == 0 else yao_val

    if moving_yao <= 3:
        ti_卦, yong_卦, ti_pos = upper_卦, lower_卦, "上卦"
    else:
        ti_卦, yong_卦, ti_pos = lower_卦, upper_卦, "下卦"

    # 2. 體用生剋判定
    relation_key = (ti_卦["element"], yong_卦["element"])
    relation_name, desc, trend, base_factor = ELEMENT_RELATIONS.get(
        relation_key, ("平和", "多空交戰，謹慎看待。", "⚠️ 盤整", 0.0)
    )

    # 3. 月令旺衰權重
    season_weight, season_desc = calculate_season_factor(
        ti_卦["element"], month
    )

    # 4. 價格推算：幅度 = 卦象方向 × 月令加權 × ATR 歷史波幅
    # 動爻數微調 (0.8 ~ 1.2 之間)
    yao_factor = 0.8 + (moving_yao * 0.067)

    # 最終預估金額變動 = 基礎係數 × 月令加權 × 動爻加權 × (ATR 波動值 × 0.8)
    price_change = base_factor * season_weight * yao_factor * (atr_val * 0.8)
    predicted_price = prev_close + price_change
    predicted_change_pct = (price_change / prev_close) * 100

    return {
        "upper": upper_卦,
        "lower": lower_卦,
        "moving_yao": moving_yao,
        "ti": ti_卦,
        "yong": yong_卦,
        "ti_pos": ti_pos,
        "relation_name": relation_name,
        "desc": desc,
        "trend": trend,
        "season_desc": season_desc,
        "change_pct": predicted_change_pct,
        "price_change": price_change,
        "predicted_price": predicted_price,
    }


# --- Streamlit UI 介面 ---
st.set_page_config(
    page_title="進階台股易經卜卦預測系統", page_icon="🔮", layout="centered"
)

st.title("🔮 進階台股易經卜卦預測系統")
st.caption(
    "結合「梅花易數」、「月令五行旺衰」與「yfinance 歷史波幅 (ATR)」量化模型"
)

st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    stock_input = st.text_input(
        "請輸入台股代號", value="2330", help="例如：2330 或 2454"
    )
with col2:
    base_date = st.date_input("選擇基準日期", datetime.date.today())

target_mode = st.radio(
    "選擇預測目標時間：",
    ["預測該日期「當天」盤勢", "預測該日期「次日（隔天）」盤勢"],
    horizontal=True,
)

if st.button("🔮 自動抓取市場數據並起卦", use_container_width=True):
    if not stock_input:
        st.warning("請輸入正確的股票代號！")
    else:
        if target_mode == "預測該日期「次日（隔天）」盤勢":
            calc_date = base_date + datetime.timedelta(days=1)
            date_label = f"{base_date} 之「隔日（{calc_date}）」"
        else:
            calc_date = base_date
            date_label = f"{calc_date}「當日」"

        with st.spinner("正在計算 14 日 ATR 歷史波動度與股價..."):
            prev_close, atr_val, price_info = get_stock_data_and_atr(
                stock_input, base_date
            )

        if prev_close is None:
            st.error(f"❌ 數據抓取失敗：{price_info}")
        else:
            st.success(
                f"📈 **數據載入成功**（最新交易日：{price_info}）｜ 收盤價：**{prev_close:.2f} 元** ｜ 近期平均波幅 (ATR)：**{atr_val:.2f} 元**"
            )

            result = calculate_hexagram(
                stock_input, calc_date, prev_close, atr_val
            )

            st.subheader("📊 卦象分析與價位預測")

            m1, m2 = st.columns(2)
            with m1:
                st.metric(
                    label="🔮 走勢卦象預測",
                    value=result["trend"],
                    delta=result["relation_name"],
                )
            with m2:
                st.metric(
                    label="💰 預估收盤價",
                    value=f"{result['predicted_price']:.2f} 元",
                    delta=f"{result['price_change']:+.2f} 元 ({result['change_pct']:+.2f}%)",
                )

            st.info(f"💡 **易理解析**：{result['desc']}")

            st.markdown("---")

            # 詳細卦象資訊
            st.write("### ☯️ 本卦與能量詳細資訊")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(
                    f"**上卦（天）**\n### {result['upper']['symbol']} {result['upper']['name']}\n五行：{result['upper']['element']}"
                )
            with c2:
                st.markdown(
                    f"**下卦（地）**\n### {result['lower']['symbol']} {result['lower']['name']}\n五行：{result['lower']['element']}"
                )
            with c3:
                st.markdown(
                    f"**動爻**\n### 第 {result['moving_yao']} 爻\n體卦所在：{result['ti_pos']}"
                )

            with st.expander("🔍 檢視「月令旺衰與 ATR 量化」詳細邏輯"):
                st.write(f"- **體卦五行**：{result['ti']['element']}")
                st.write(
                    f"- **月令旺衰狀態**：{result['season_desc']}"
                )
                st.write(
                    f"- **波動校正 (ATR)**：以該股近期 {atr_val:.2f} 元的平均日內波動幅度進行價格折算"
                )

st.caption("⚠️ **免責聲明**：本程式僅供玄學娛樂與程式邏輯參考，不構成任何金融投資建議。")
