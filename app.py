import datetime
import math
import pandas as pd
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

GUA_LINES = {
    1: [True, True, True],
    2: [True, True, False],
    3: [True, False, True],
    4: [True, False, False],
    5: [False, True, True],
    6: [False, True, False],
    7: [False, False, True],
    0: [False, False, False],
}

def lines_to_gua_val(lines):
    for val, l in GUA_LINES.items():
        if l == lines:
            return val
    return 0

SEASON_ELEMENT_MAP = {
    1: "水", 2: "木", 3: "木", 4: "土", 5: "火", 6: "火",
    7: "土", 8: "金", 9: "金", 10: "土", 11: "水", 12: "水",
}

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

def calculate_season_factor(ti_element: str, month: int):
    season_element = SEASON_ELEMENT_MAP.get(month, "土")
    if ti_element == season_element:
        return 1.3, "當旺"
    element_generates = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
    if element_generates.get(season_element) == ti_element:
        return 1.15, "相"
    elif element_generates.get(ti_element) == season_element:
        return 0.85, "休"
    else:
        return 0.7, "囚/死"

def get_changed_hexagram(upper_val, lower_val, moving_yao):
    full_lines = GUA_LINES[lower_val] + GUA_LINES[upper_val]
    idx = moving_yao - 1
    full_lines[idx] = not full_lines[idx]
    new_lower_val = lines_to_gua_val(full_lines[0:3])
    new_upper_val = lines_to_gua_val(full_lines[3:6])
    return BAGUA[new_upper_val], BAGUA[new_lower_val]

def calculate_raw_hexagram(stock_code: str, date_obj: datetime.date, prev_close: float, atr_val: float):
    digits = "".join(filter(str.isdigit, stock_code))
    stock_num = int(digits) if digits else 100
    year, month, day = date_obj.year, date_obj.month, date_obj.day

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

    # 開盤預測
    open_rel_key = (ti_卦["element"], yong_卦["element"])
    _, _, open_trend, open_base_factor = ELEMENT_RELATIONS.get(
        open_rel_key, ("平和", "多空平盤附近開出", "⚠️ 平盤震盪", 0.0)
    )
    season_weight, season_desc = calculate_season_factor(ti_卦["element"], month)
    raw_open_change = open_base_factor * season_weight * (atr_val * 0.3)

    # 收盤預測
    changed_upper, changed_lower = get_changed_hexagram(upper_val, lower_val, moving_yao)
    changed_ti = changed_upper if ti_pos == "上卦" else changed_lower
    changed_yong = changed_lower if ti_pos == "上卦" else changed_upper

    close_rel_key = (changed_ti["element"], changed_yong["element"])
    _, _, close_trend, close_base_factor = ELEMENT_RELATIONS.get(
        close_rel_key, ("平和", "多空交戰，謹慎看待。", "⚠️ 盤整", 0.0)
    )
    yao_factor = 0.8 + (moving_yao * 0.067)
    raw_close_change = close_base_factor * season_weight * yao_factor * (atr_val * 0.8)

    return {
        "raw_open_change": raw_open_change,
        "raw_close_change": raw_close_change,
        "upper": upper_卦, "lower": lower_卦, "moving_yao": moving_yao,
        "changed_upper": changed_upper, "changed_lower": changed_lower,
        "season_desc": season_desc, "open_trend": open_trend, "close_trend": close_trend
    }

# 滾動遞推自我校正算法 (Iterative Rolling Adjustment)
def get_stock_data_and_recursive_backtest(stock_code: str, target_date: datetime.date, backtest_days: int = 10, lr: float = 0.3):
    """
    lr (Learning Rate): 學習率 (0.1 ~ 0.5)，決定當天誤差要以多大比例更新到下一天的修正變數中
    """
    digits = "".join(filter(str.isdigit, stock_code))
    if not digits:
        return None, "無效的股票代號"

    tickers = [f"{digits}.TW", f"{digits}.TWO"]
    start_date = target_date - datetime.timedelta(days=70)

    for ticker in tickers:
        df = yf.download(ticker, start=start_date, end=target_date + datetime.timedelta(days=1), progress=False)
        if not df.empty and len(df) >= backtest_days + 15:
            if isinstance(df.columns, tuple) or hasattr(df.columns, "levels"):
                df.columns = [col[0] for col in df.columns]

            high_low = df["High"] - df["Low"]
            high_cp = (df["High"] - df["Close"].shift(1)).abs()
            low_cp = (df["Low"] - df["Close"].shift(1)).abs()
            tr = high_low.to_frame("hl").join(high_cp.to_frame("hcp")).join(low_cp.to_frame("lcp")).max(axis=1)
            df["ATR"] = tr.rolling(14).mean().fillna(df["Close"] * 0.02)

            history_df = df.iloc[-(backtest_days + 1):-1].copy()
            
            # 初始修正變數為 0
            open_bias_adj = 0.0
            close_bias_adj = 0.0
            
            rolling_logs = []

            # 從第 -10 天開始逐日滾動計算並自我更新
            for i in range(len(history_df)):
                curr_date = history_df.index[i].date()
                prev_close = df["Close"].iloc[df.index.get_loc(history_df.index[i]) - 1]
                actual_open = history_df["Open"].iloc[i]
                actual_close = history_df["Close"].iloc[i]
                atr = history_df["ATR"].iloc[i]

                # 當日原始卦象
                raw = calculate_raw_hexagram(stock_code, curr_date, prev_close, atr)
                
                # 套用「昨日累積」的修正變數，得到當天校正後的預測
                pred_open_adj = prev_close + raw["raw_open_change"] + open_bias_adj
                pred_close_adj = prev_close + raw["raw_close_change"] + close_bias_adj

                # 計算當日校正後與真實情況的殘差 (Residuals)
                open_err = actual_open - pred_open_adj
                close_err = actual_close - pred_close_adj

                # 記錄當前步進狀態
                rolling_logs.append({
                    "步數": f"第 {i+1} 天",
                    "日期": curr_date.strftime("%Y-%m-%d"),
                    "套用開盤修正量": open_bias_adj,
                    "當日實際開盤": actual_open,
                    "校正後預測開盤": pred_open_adj,
                    "開盤剩餘誤差": open_err,
                    "套用收盤修正量": close_bias_adj,
                    "當日實際收盤": actual_close,
                    "校正後預測收盤": pred_close_adj,
                    "收盤剩餘誤差": close_err,
                })

                # 關鍵：遞推更新修正變數，產生給「隔天」使用的修正量！
                # 滾動公式：新修正量 = 舊修正量 + (當日誤差 * 學習率)
                open_bias_adj += open_err * lr
                close_bias_adj += close_err * lr

            bt_df = pd.DataFrame(rolling_logs)

            last_close = float(df["Close"].iloc[-1])
            last_atr = float(df["ATR"].iloc[-1])
            actual_date = df.index[-1].strftime("%Y-%m-%d")

            return {
                "last_close": last_close,
                "last_atr": last_atr,
                "actual_date": actual_date,
                "final_open_bias_adj": open_bias_adj,   # 經過 10 輪滾動遞推後，最終提煉出的修正變數
                "final_close_bias_adj": close_bias_adj, # 經過 10 輪滾動遞推後，最終提煉出的修正變數
                "bt_df": bt_df
            }, None

    return None, "找不到該股票歷史價格數據"

# --- Streamlit UI 介面 ---
st.set_page_config(page_title="台股易經卜卦（滾動遞推自我校正版）", page_icon="🔮", layout="centered")

st.title("🔮 台股易經卜卦（滾動遞推自學習版）")
st.caption("模擬連鎖效應：以 T-10 天校正 T-9 天，層層遞推疊加，提煉出最新目標日的自適應修正變數")

st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    stock_input = st.text_input("請輸入台股代號", value="2330")
with col2:
    base_date = st.date_input("選擇基準日期", datetime.date.today())

learning_rate = st.slider("選擇自適應學習率 (Learning Rate)", min_value=0.1, max_value=0.8, value=0.3, step=0.05, help="學習率越高，近期的誤差對當前預測影響越大")

target_mode = st.radio(
    "選擇預測目標時間：",
    ["預測該日期「當天」盤勢", "預測該日期「次日（隔天）」盤勢"],
    horizontal=True,
)

if st.button("🔄 開始 10 輪遞推學習並導出最終預測", use_container_width=True):
    if not stock_input:
        st.warning("請輸入正確的股票代號！")
    else:
        calc_date = base_date + datetime.timedelta(days=1) if target_mode == "預測該日期「次日（隔天）」盤勢" else base_date

        with st.spinner("正在執行遞推滾動學習 (Recursive Learning)..."):
            data, err = get_stock_data_and_recursive_backtest(stock_input, base_date, backtest_days=10, lr=learning_rate)

        if err:
            st.error(f"❌ 數據抓取失敗：{err}")
        else:
            prev_close = data["last_close"]
            atr_val = data["last_atr"]
            final_open_adj = data["final_open_bias_adj"]
            final_close_adj = data["final_close_bias_adj"]

            st.success(
                f"📈 **基準行情**（{data['actual_date']}）｜ 收盤：**{prev_close:.2f} 元** ｜ ATR：**{atr_val:.2f} 元**"
            )

            # 1. 計算目標日原始卦象
            raw_res = calculate_raw_hexagram(stock_input, calc_date, prev_close, atr_val)

            # 2. 將 10 輪遞推進化後最終產生的修正變數，套用到目標預測日
            final_open_price = prev_close + raw_res["raw_open_change"] + final_open_adj
            final_close_price = prev_close + raw_res["raw_close_change"] + final_close_adj

            final_open_change = final_open_price - prev_close
            final_close_change = final_close_price - prev_close

            st.subheader("📊 10 輪遞推進化後 — 最終目標日預測結果")

            m1, m2 = st.columns(2)
            with m1:
                st.metric(
                    label="🌅 遞推校正「開盤」預估價",
                    value=f"{final_open_price:.2f} 元",
                    delta=f"{final_open_change:+.2f} 元 (累計修正 {final_open_adj:+.2f}元)"
                )
            with m2:
                st.metric(
                    label="🌆 遞推校正「收盤」預估價",
                    value=f"{final_close_price:.2f} 元",
                    delta=f"{final_close_change:+.2f} 元 (累計修正 {final_close_adj:+.2f}元)"
                )

            # 3. 展開 10 步逐日遞推過程
            with st.expander("🔄 點擊檢視 10 個交易日「逐日遞推校正」演進日誌"):
                st.markdown(f"**遞推公式**：$W_{{t+1}} = W_t + (Actual_t - Pred_t) \\times {learning_rate}$")
                st.dataframe(
                    data["bt_df"]
                    .style.format("{:.2f}", subset=[
                        "套用開盤修正量", "當日實際開盤", "校正後預測開盤", "開盤剩餘誤差",
                        "套用收盤修正量", "當日實際收盤", "校正後預測收盤", "收盤剩餘誤差"
                    ])
                )

            st.markdown("---")
            st.write("### ☯️ 當日卦象格局")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**【本卦】開盤**\n- 卦象：{raw_res['upper']['symbol']}{raw_res['upper']['name']}卦上 / {raw_res['lower']['symbol']}{raw_res['lower']['name']}卦下\n- 趨勢：{raw_res['open_trend']}")
            with c2:
                st.markdown(f"**【變卦】收盤**\n- 卦象：{raw_res['changed_upper']['symbol']}{raw_res['changed_upper']['name']}卦上 / {raw_res['changed_lower']['symbol']}{raw_res['changed_lower']['name']}卦下\n- 趨勢：{raw_res['close_trend']}")

st.caption("⚠️ **免責聲明**：本程式結合遞推自適應學習與易經卦象計算，僅供玄學程式開發研究，不構成投資建議。")
