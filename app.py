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

# 八卦三爻對應（從下爻到上爻：True=陽爻, False=陰爻）
GUA_LINES = {
    1: [True, True, True],     # 乾
    2: [True, True, False],    # 兌
    3: [True, False, True],    # 離
    4: [True, False, False],   # 震
    5: [False, True, True],    # 巽
    6: [False, True, False],   # 坎
    7: [False, False, True],   # 艮
    0: [False, False, False],  # 坤
}

# 根據三爻陣列還原八卦數
def lines_to_gua_val(lines):
    for val, l in GUA_LINES.items():
        if l == lines:
            return val
    return 0

# 季節月令五行旺衰判斷
SEASON_ELEMENT_MAP = {
    1: "水", 2: "木", 3: "木", 4: "土", 5: "火", 6: "火",
    7: "土", 8: "金", 9: "金", 10: "土", 11: "水", 12: "水",
}

# 五行生剋判定與係數
ELEMENT_RELATIONS = {
    ("金", "金"): ("比和", "多空拉鋸，平盤或小幅跳空", "⚠️ 平盤震盪", 0.0),
    ("金", "木"): ("體克用", "耗費精力但能獲勝，開高或震盪趨強", "📈 偏多開高", 0.4),
    ("金", "水"): ("體生用", "自身能量洩出，資金不足，易跳空開低", "📉 偏空開低", -0.4),
    ("金", "火"): ("用克體", "受外力壓制，空頭強勁，大機率跳空開低", "🔻 開低承壓", -1.0),
    ("金", "土"): ("用生體", "獲得外部大吉助力，買盤強勁，強勢跳空開高", "🚀 強勢開高", 1.2),

    ("木", "木"): ("比和", "動能相當，多方平盤附近開出", "⚠️ 平盤震盪", 0.0),
    ("木", "火"): ("體生用", "動能過度消耗，開高易走低或直接開低", "📉 偏空開低", -0.4),
    ("木", "土"): ("體克用", "克服賣壓前行，順勢小幅開高", "📈 偏多開高", 0.4),
    ("木", "金"): ("用克體", "遇到強大賣壓，多頭受挫，跳空開低", "🔻 開低承壓", -1.0),
    ("木", "水"): ("用生體", "資金源源不絕，買單湧入，跳空開高", "🚀 強勢開高", 1.2),

    ("水", "水"): ("比和", "量能平平，隨波逐流，平盤附近開出", "⚠️ 平盤震盪", 0.0),
    ("水", "木"): ("體生用", "資金外流，開盤乏力，偏空開低", "📉 偏空開低", -0.4),
    ("水", "火"): ("體克用", "多頭逆勢反攻，有機會偏多開高", "📈 偏多開高", 0.4),
    ("水", "土"): ("用克體", "遭利空擊中，觀望氣氛濃，跳空開低", "🔻 開低承壓", -1.0),
    ("水", "金"): ("用生體", "水到渠成，買單積極，強勢跳空開高", "🚀 強勢開高", 1.2),

    ("火", "火"): ("比和", "熱度高但多空分歧，高開低走震盪大", "⚠️ 高震盪開盤", 0.1),
    ("火", "土"): ("體生用", "追高力道不足，逢高賣壓沉重，易開低", "📉 偏空開低", -0.4),
    ("火", "金"): ("體克用", "衝破賣壓牆，力道強勁，偏多開高", "📈 偏多開高", 0.4),
    ("火", "水"): ("用克體", "冷水灌頂，空頭力道強，防大跌跳空開低", "🔻 開低承壓", -1.0),
    ("火", "木"): ("用生體", "利多頻傳，資金力挺，強勢漲停或跳空大開高", "🚀 強勢開高", 1.2),

    ("土", "土"): ("比和", "底部堅實，波幅極小，平盤開出", "⚠️ 平盤震盪", 0.0),
    ("土", "金"): ("體生用", "漲勁不足，逢高獲利了結賣壓，偏空開低", "📉 偏空開低", -0.4),
    ("土", "水"): ("體克用", "成功吸收籌碼，緩步墊高，小幅開高", "📈 偏多開高", 0.4),
    ("土", "木"): ("用克體", "主力洗盤拋售，支撐脆弱，跳空開低", "🔻 開低承壓", -1.0),
    ("土", "火"): ("用生體", "買盤支撐力道強，有利多頭，強勢開高", "🚀 強勢開高", 1.2),
}

def get_stock_data_and_atr(stock_code: str, target_date: datetime.date):
    """抓取股價與計算近 14 日 ATR"""
    digits = "".join(filter(str.isdigit, stock_code))
    if not digits:
        return None, None, "無效的股票代號"

    tickers = [f"{digits}.TW", f"{digits}.TWO"]
    start_date = target_date - datetime.timedelta(days=45)

    for ticker in tickers:
        df = yf.download(ticker, start=start_date, end=target_date, progress=False)
        if not df.empty and len(df) >= 5:
            if isinstance(df.columns, tuple) or hasattr(df.columns, "levels"):
                df.columns = [col[0] for col in df.columns]

            last_close = float(df["Close"].iloc[-1])
            actual_date = df.index[-1].strftime("%Y-%m-%d")

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

            if math.isnan(atr):
                atr = last_close * 0.02

            return last_close, atr, actual_date

    return None, None, "找不到該股票歷史價格與波動資料"

def calculate_season_factor(ti_element: str, month: int):
    """計算體卦月令旺衰加權"""
    season_element = SEASON_ELEMENT_MAP.get(month, "土")
    if ti_element == season_element:
        return 1.3, "當旺（氣勢最極盛）"

    element_generates = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
    if element_generates.get(season_element) == ti_element:
        return 1.15, "相（受月令相生，次吉）"
    elif element_generates.get(ti_element) == season_element:
        return 0.85, "休（洩氣，力道較弱）"
    else:
        return 0.7, "囚/死（受月令克制，動能不足）"

def get_changed_hexagram(upper_val, lower_val, moving_yao):
    """計算動爻改變後的『變卦』"""
    # 組合六爻 (下卦3爻 + 上卦3爻)
    full_lines = GUA_LINES[lower_val] + GUA_LINES[upper_val]
    
    # 翻轉動爻 (1-based index)
    idx = moving_yao - 1
    full_lines[idx] = not full_lines[idx]
    
    # 分拆回新下卦與新上卦
    new_lower_lines = full_lines[0:3]
    new_upper_lines = full_lines[3:6]
    
    new_lower_val = lines_to_gua_val(new_lower_lines)
    new_upper_val = lines_to_gua_val(new_upper_lines)
    
    return BAGUA[new_upper_val], BAGUA[new_lower_val]

def calculate_hexagram(stock_code: str, date_obj: datetime.date, prev_close: float, atr_val: float):
    """結合本卦（開盤）與變卦（收盤）預測價位"""
    digits = "".join(filter(str.isdigit, stock_code))
    stock_num = int(digits) if digits else 100

    year, month, day = date_obj.year, date_obj.month, date_obj.day

    # 1. 本卦起卦
    upper_val = (stock_num + year + month + day) % 8
    upper_卦 = BAGUA[upper_val]

    lower_val = (stock_num + day) % 8
    lower_卦 = BAGUA[lower_val]

    yao_val = (stock_num + year + month + day) % 6
    moving_yao = 6 if yao_val == 0 else yao_val

    # 體用判定
    if moving_yao <= 3:
        ti_卦, yong_卦, ti_pos = upper_卦, lower_卦, "上卦"
    else:
        ti_卦, yong_卦, ti_pos = lower_卦, upper_卦, "下卦"

    # 2. 開盤預測（看本卦）
    open_rel_key = (ti_卦["element"], yong_卦["element"])
    open_rel_name, open_desc, open_trend, open_base_factor = ELEMENT_RELATIONS.get(
        open_rel_key, ("平和", "多空平盤附近開出", "⚠️ 平盤震盪", 0.0)
    )

    season_weight, season_desc = calculate_season_factor(ti_卦["element"], month)
    
    # 計算開盤預估價（開盤跳空通常為 daily ATR 的 0.2~0.4 倍）
    open_price_change = open_base_factor * season_weight * (atr_val * 0.3)
    predicted_open_price = prev_close + open_price_change
    open_change_pct = (open_price_change / prev_close) * 100

    # 3. 收盤預測（看變卦）
    changed_upper, changed_lower = get_changed_hexagram(upper_val, lower_val, moving_yao)
    changed_ti = changed_upper if ti_pos == "上卦" else changed_lower
    changed_yong = changed_lower if ti_pos == "上卦" else changed_upper

    close_rel_key = (changed_ti["element"], changed_yong["element"])
    close_rel_name, close_desc, close_trend, close_base_factor = ELEMENT_RELATIONS.get(
        close_rel_key, ("平和", "多空交戰，謹慎看待。", "⚠️ 盤整", 0.0)
    )

    yao_factor = 0.8 + (moving_yao * 0.067)
    close_price_change = close_base_factor * season_weight * yao_factor * (atr_val * 0.8)
    predicted_close_price = prev_close + close_price_change
    close_change_pct = (close_price_change / prev_close) * 100

    return {
        "upper": upper_卦,
        "lower": lower_卦,
        "moving_yao": moving_yao,
        "ti": ti_卦,
        "yong": yong_卦,
        "ti_pos": ti_pos,
        "changed_upper": changed_upper,
        "changed_lower": changed_lower,
        "season_desc": season_desc,
        # 開盤結果
        "open_trend": open_trend,
        "open_rel_name": open_rel_name,
        "open_desc": open_desc,
        "open_change_pct": open_change_pct,
        "open_price_change": open_price_change,
        "predicted_open_price": predicted_open_price,
        # 收盤結果
        "close_trend": close_trend,
        "close_rel_name": close_rel_name,
        "close_desc": close_desc,
        "close_change_pct": close_change_pct,
        "close_price_change": close_price_change,
        "predicted_close_price": predicted_close_price,
    }

# --- Streamlit UI 介面 ---
st.set_page_config(page_title="台股易經卜卦（開盤與收盤預測）", page_icon="🔮", layout="centered")

st.title("🔮 台股易經卜卦（開盤與收盤預測）")
st.caption("利用「本卦」預測開盤跳空走勢，結合「變卦」預測終場收盤價")

st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    stock_input = st.text_input("請輸入台股代號", value="2330", help="例如：2330 或 2454")
with col2:
    base_date = st.date_input("選擇基準日期", datetime.date.today())

target_mode = st.radio(
    "選擇預測目標時間：",
    ["預測該日期「當天」盤勢", "預測該日期「次日（隔天）」盤勢"],
    horizontal=True,
)

if st.button("🔮 自動抓取數據並起卦預測", use_container_width=True):
    if not stock_input:
        st.warning("請輸入正確的股票代號！")
    else:
        calc_date = base_date + datetime.timedelta(days=1) if target_mode == "預測該日期「次日（隔天）」盤勢" else base_date

        with st.spinner("正在讀取股價與計算 ATR 波動度..."):
            prev_close, atr_val, price_info = get_stock_data_and_atr(stock_input, base_date)

        if prev_close is None:
            st.error(f"❌ 數據抓取失敗：{price_info}")
        else:
            st.success(
                f"📈 **基準資料**（{price_info}）｜ 昨日收盤價：**{prev_close:.2f} 元** ｜ 14日平均波幅 (ATR)：**{atr_val:.2f} 元**"
            )

            result = calculate_hexagram(stock_input, calc_date, prev_close, atr_val)

            st.subheader("📊 開盤與收盤雙維度預測")

            # 雙欄位：左邊看開盤、右邊看收盤
            m1, m2 = st.columns(2)
            with m1:
                st.metric(
                    label="🌅 預估「開盤」走勢 / 價格",
                    value=f"{result['predicted_open_price']:.2f} 元",
                    delta=f"{result['open_price_change']:+.2f} 元 ({result['open_trend']})"
                )
                st.caption(f"**開盤氣場**：{result['open_rel_name']}（{result['open_desc']}）")

            with m2:
                st.metric(
                    label="🌆 預估「收盤」走勢 / 價格",
                    value=f"{result['predicted_close_price']:.2f} 元",
                    delta=f"{result['close_price_change']:+.2f} 元 ({result['close_trend']})"
                )
                st.caption(f"**尾盤氣場**：{result['close_rel_name']}（{result['close_desc']}）")

            st.markdown("---")

            # 詳細卦象資訊 (本卦 vs 變卦)
            st.write("### ☯️ 本卦（開盤）與 變卦（收盤）對照")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**【本卦】開盤格局**\n- 上卦：{result['upper']['symbol']} {result['upper']['name']} ({result['upper']['element']})\n- 下卦：{result['lower']['symbol']} {result['lower']['name']} ({result['lower']['element']})\n- 動爻：第 **{result['moving_yao']}** 爻")
            with c2:
                st.markdown(f"**【變卦】尾盤定局**\n- 上卦：{result['changed_upper']['symbol']} {result['changed_upper']['name']} ({result['changed_upper']['element']})\n- 下卦：{result['changed_lower']['symbol']} {result['changed_lower']['name']} ({result['changed_lower']['element']})\n- 狀態：{result['season_desc']}")

st.caption("⚠️ **免責聲明**：本程式僅供玄學娛樂與程式邏輯參考，不構成任何金融投資建議。")
