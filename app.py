import datetime
import streamlit as st

# 1. 基礎資料定義：八卦名稱、五行與對應數值
BAGUA = {
    1: {"name": "乾", "symbol": "☰", "element": "金"},
    2: {"name": "兌", "symbol": "☱", "element": "金"},
    3: {"name": "離", "symbol": "☲", "element": "火"},
    4: {"name": "震", "symbol": "☳", "element": "木"},
    5: {"name": "巽", "symbol": "☴", "element": "木"},
    6: {"name": "坎", "symbol": "☵", "element": "水"},
    7: {"name": "艮", "symbol": "☶", "element": "土"},
    0: {"name": "坤", "symbol": "☷", "element": "土"},  # 餘數 0 為坤
}

# 五行生剋判定 (體卦為 A，用卦為 B)
ELEMENT_RELATIONS = {
    ("金", "金"): ("比和", "雙方勢均力敵，市場多空交戰，預計高位盤整或平盤出局。", "⚠️ 盤整"),
    ("金", "木"): ("體克用", "耗費精力但能獲勝，過程可能震盪，但終能收紅。", "📈 偏多"),
    ("金", "水"): ("體生用", "自身能量洩出，資金或動能不足，易開高走低。", "📉 偏空"),
    ("金", "火"): ("用克體", "受外力強烈壓制，主力拋售或利空襲來，收陰機率高。", "🔻 看跌"),
    ("金", "土"): ("用生體", "獲得外部大吉助力，買盤強勁，強勢看漲。", "🚀 大漲"),
    ("木", "木"): ("比和", "動能相當，多方持續整理，波動不大。", "⚠️ 盤整"),
    ("木", "火"): ("體生用", "動能過度消耗，追高風險大，易逢高拉回。", "📉 偏空"),
    ("木", "土"): ("體克用", "克服賣壓前行，小幅獲利，小漲作收。", "📈 偏多"),
    ("木", "金"): ("用克體", "遇到強大拋售賣壓，空方佔優，跌勢較明顯。", "🔻 看跌"),
    ("木", "水"): ("用生體", "資金源源不絕挹注，多頭格局強勢。", "🚀 大漲"),
    ("水", "水"): ("比和", "量能平平，隨波逐流，呈現窄幅震盪。", "⚠️ 盤整"),
    ("水", "木"): ("體生用", "資金外流或動能潰散，獲利吐回。", "📉 偏空"),
    ("水", "火"): ("體克用", "多頭逆勢反攻，順利克服阻力，收紅可期。", "📈 偏多"),
    ("水", "土"): ("用克體", "遭強烈利空擊中，觀望氣氛濃，股價承壓。", "🔻 看跌"),
    ("水", "金"): ("用生體", "水到渠成，市場買單積極，強勢衝高。", "🚀 大漲"),
    ("火", "火"): ("比和", "熱度極高但多空分歧，震盪劇烈。", "⚠️ 高震盪"),
    ("火", "土"): ("體生用", "追高力道不足，漲勢受阻，易拉回走低。", "📉 偏空"),
    ("火", "金"): ("體克用", "強力衝破賣壓牆，雖有震盪但終能獲勝。", "📈 偏多"),
    ("火", "水"): ("用克體", "冷水灌頂，空頭力道強勁，慎防大跌。", "🔻 看跌"),
    ("火", "木"): ("用生體", "利多頻傳，資金力挺，強勢漲停或大漲。", "🚀 大漲"),
    ("土", "土"): ("比和", "底部堅實，盤整蓄勢，變幅極小。", "⚠️ 盤整"),
    ("土", "金"): ("體生用", "漲勁不足，逢高獲利了結賣壓沉重。", "📉 偏空"),
    ("土", "水"): ("體克用", "成功吸收籌碼，緩步墊高，小漲作收。", "📈 偏多"),
    ("土", "木"): ("用克體", "主力洗盤拋售，支撐脆弱，偏空看待。", "🔻 看跌"),
    ("土", "火"): ("用生體", "買盤支撐力道強，震盪走高，利於多頭。", "🚀 大漲"),
}


def calculate_hexagram(stock_code: str, date_obj: datetime.date):
    """根據個股代號與日期起卦"""
    # 提取個股代號中的數字
    digits = "".join(filter(str.isdigit, stock_code))
    stock_num = int(digits) if digits else 100

    # 提取年月日時 (以當日 09:00 開盤時間為準)
    year = date_obj.year
    month = date_obj.month
    day = date_obj.day

    # 1. 求上卦：(股票代號 + 年 + 月 + 日) % 8
    upper_val = (stock_num + year + month + day) % 8
    upper_卦 = BAGUA[upper_val]

    # 2. 求下卦：(股票代號 + 日) % 8
    lower_val = (stock_num + day) % 8
    lower_卦 = BAGUA[lower_val]

    # 3. 求動爻：(股票代號 + 年 + 月 + 日) % 6 (餘數0算作6爻)
    yao_val = (stock_num + year + month + day) % 6
    moving_yao = 6 if yao_val == 0 else yao_val

    # 4. 判斷體用：1~3爻動，上卦為體、下卦為用；4~6爻動，下卦為體、上卦為用
    if moving_yao <= 3:
        ti_卦 = upper_卦
        yong_卦 = lower_卦
        ti_pos = "上卦"
    else:
        ti_卦 = lower_卦
        yong_卦 = upper_卦
        ti_pos = "下卦"

    # 5. 分析體用生剋
    relation_key = (ti_卦["element"], yong_卦["element"])
    relation_name, desc, trend = ELEMENT_RELATIONS.get(
        relation_key, ("平和", "多空交戰，謹慎看待。", "⚠️ 盤整")
    )

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
    }


# --- Streamlit UI 介面設計 ---
st.set_page_config(
    page_title="台股個股易經卜卦預測", page_icon="🔮", layout="centered"
)

st.title("🔮 台股個股易經卜卦預測 App")
st.caption("結合梅花易數與個股資訊，預測明日股價走勢與多空能量")

st.markdown("---")

# 輸入區
col1, col2 = st.columns(2)
with col1:
    stock_input = st.text_input(
        "請輸入台股代號", value="2330", help="例如：2330 或 2330.TW"
    )
with col2:
    predict_date = st.date_input("選擇預測日期", datetime.date.today())

if st.button("🔮 開始起卦預測", use_container_width=True):
    if not stock_input:
        st.warning("請輸入正確的股票代號！")
    else:
        result = calculate_hexagram(stock_input, predict_date)

        st.subheader("📊 卦象分析結果")

        # 顯示趨勢卡片
        st.metric(
            label=f"股票 [{stock_input}] 於 {predict_date} 的隔日走勢預測",
            value=result["trend"],
            delta=result["relation_name"],
        )

        st.info(f"💡 **易理解析**：{result['desc']}")

        st.markdown("---")

        # 顯示詳細卦象細節
        st.write("### ☯️ 本卦詳細資訊")
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

        # 體用關係說明
        with st.expander("🔍 檢視「體用生剋」詳細邏輯"):
            st.write(
                f"- **體卦（主體/個股自身）**：{result['ti']['name']}卦（五行屬{result['ti']['element']}）"
            )
            st.write(
                f"- **用卦（環境/資金/市場）**：{result['yong']['name']}卦（五行屬{result['yong']['element']}）"
            )
            st.write(
                f"- **生剋結果**：{result['relation_name']}（{result['ti']['element']}與{result['yong']['element']}）"
            )

st.caption("⚠️ **免責聲明**：本程式僅供玄學娛樂與程式邏輯參考，不構成任何金融投資建議。")
