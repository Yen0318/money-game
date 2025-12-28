import streamlit as st
import pandas as pd
import numpy as np
import os
import csv
import time
from datetime import datetime
import plotly.express as px
import streamlit.components.v1 as components
# --- 0. 輔助函數：獲取在線人數 ---
def get_active_user_count():
    try:
        from streamlit.runtime import get_instance
        runtime = get_instance()
        if runtime:
            session_manager = runtime._session_manager
            sessions = session_manager.list_active_sessions()
            return len(sessions)
    except Exception:
        return 1 # 如果無法讀取 (例如本地端開發或版本差異)，預設回傳 1
    return 1
# --- 1. 頁面設定 (必須放在所有 Streamlit 指令的第一行) ---
st.set_page_config(page_title="Flip Your Destiny - IFRC Edition", page_icon="🏦", layout="wide")

# ==========================================
# ⚙️ 後台設定區 (Host Control)
# ==========================================
BASE_RATES = {
    'Dividend': 0.06, 'USBond': 0.03, 'TWStock': 0.07, 'Cash': 0.0, 'Crypto': 0.1
}

EVENT_CARDS = {
    "101": {"name": "US FED降息3%",      "dividend": 7,  "bond": 2,  "stock": 20,   "cash": 0,  "crypto": 100,   "desc": "💸 資金大放水！市場流動性暴增，風險資產狂噴。"},
    "102": {"name": "AI晶片大戰",        "dividend": 6,  "bond": 5,  "stock": -30,  "cash": -1, "crypto": -80,   "desc": "🤖 科技霸權爭奪，供應鏈大亂，科技股與幣圈重挫。"},
    "103": {"name": "美債信心危機",      "dividend": 5,  "bond": -6, "stock": -20,  "cash": 1,  "crypto": -70,   "desc": "📉 公債遭拋售，避險資產失靈，市場信心動搖。"},
    "104": {"name": "關稅戰全面升級",    "dividend": 6,  "bond": 7,  "stock": -45,  "cash": -3, "crypto": -70,   "desc": "🚧 全球貿易壁壘升高，企業獲利受損，股市大跌。"},
    "105": {"name": "AI/半導體世代級突破","dividend": 6,  "bond": -2, "stock": 30,   "cash": -3, "crypto": 50,    "desc": "🚀 生產力大爆發！科技股領漲，帶動加密貨幣回升。"},
    "106": {"name": "能源通膨衝擊",      "dividend": 7,  "bond": -6, "stock": -60,  "cash": -8, "crypto": -85,   "desc": "🛢️ 油價飆升，萬物齊漲，停滯性通膨重創所有資產。"},
    "107": {"name": "科技股估值回歸",    "dividend": 6,  "bond": 9,  "stock": -40,  "cash": 1,  "crypto": -65,   "desc": "📉 泡沫破裂，資金回流防禦性資產與債券。"},
    "108": {"name": "關鍵航道被封鎖",    "dividend": 6,  "bond": 6,  "stock": -35,  "cash": -2, "crypto": -65,   "desc": "🚢 供應鏈斷鏈，運輸成本暴增，全球經濟受阻。"},
    "109": {"name": "加密貨幣監管核爆",  "dividend": 6,  "bond": 4,  "stock": -15,  "cash": 1,  "crypto": -88,   "desc": "👮‍♂️ 各國聯手監管，交易所倒閉，幣圈血流成河。"},
    "110": {"name": "資產估值錯配",      "dividend": 6,  "bond": -8, "stock": -55,  "cash": -2, "crypto": -80,   "desc": "⚠️ 市場定價機制失靈，引發全面性拋售潮。"},
    "111": {"name": "全球疫情快速升溫",  "dividend": 6,  "bond": 7,  "stock": -25,  "cash": 0,  "crypto": -55,   "desc": "😷 封城再現，經濟活動停擺，資金湧入債券避險。"},
    "112": {"name": "金融去槓桿崩盤",    "dividend": 6,  "bond": 7,  "stock": -35,  "cash": -4, "crypto": -70,   "desc": "💥 流動性枯竭，機構被迫平倉，多殺多局面出現。"},
}

CSV_FILE = 'game_data_records.csv'

# --- 存檔函數 ---
def save_data_to_csv(name, wealth, roi, cards, config_history, feedback):
    data = {
        '時間': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        '姓名': name,
        '最終資產': int(wealth),
        '報酬率(%)': round(roi, 1),
        '抽卡歷程': " | ".join(cards),
        '配置_Year0': str(config_history.get('Year 0', '')),
        '配置_Year10': str(config_history.get('Year 10', '')),
        '配置_Year20': str(config_history.get('Year 20', '')),
        '玩家反饋': feedback
    }
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=data.keys())
        if not file_exists: writer.writeheader()
        writer.writerow(data)

# ==========================================
# ⚡️ 核心初始化區 (State Initialization)
# ==========================================
# 1. 遊戲核心變數
ASSET_KEYS = ['Dividend', 'USBond', 'TWStock', 'Cash', 'Crypto']
if 'stage' not in st.session_state: st.session_state.stage = 'login'
if 'year' not in st.session_state: st.session_state.year = 0
if 'assets' not in st.session_state: st.session_state.assets = {k: 0 for k in ASSET_KEYS}
if 'history' not in st.session_state: st.session_state.history = []
if 'user_name' not in st.session_state: st.session_state.user_name = ""
if 'drawn_cards' not in st.session_state: st.session_state.drawn_cards = []
if 'config_history' not in st.session_state: st.session_state.config_history = {}
if 'data_saved' not in st.session_state: st.session_state.data_saved = False
# 🔥 新增：確保 waiting_for_rebalance 變數存在
if 'waiting_for_rebalance' not in st.session_state: st.session_state.waiting_for_rebalance = False

# 🔥 新增：動態利率初始化 (讓管理員可以調整)
if 'dynamic_rates' not in st.session_state: 
    st.session_state.dynamic_rates = BASE_RATES.copy()


# 2. 捲動偵測變數
if 'last_stage' not in st.session_state: st.session_state.last_stage = st.session_state.stage
if 'last_year' not in st.session_state: st.session_state.last_year = st.session_state.year
# 🔥 新增：偵測再平衡狀態的改變
if 'last_rebalance' not in st.session_state: st.session_state.last_rebalance = st.session_state.waiting_for_rebalance

# ==========================================
# 📜 捲動控制函數 (Smart & Strong Scroll)
# ==========================================
def scroll_to_top():
    # 1. 埋下錨點
    st.markdown('<div id="top-anchor"></div>', unsafe_allow_html=True)
    
    # 2. 檢查是否發生「換頁」、「年份變更」或「進入再平衡階段」
    should_scroll = False
    
    if st.session_state.stage != st.session_state.last_stage:
        should_scroll = True
    elif st.session_state.year != st.session_state.last_year:
        should_scroll = True
    elif st.session_state.waiting_for_rebalance != st.session_state.last_rebalance:
        # 🔥 新增：當從抽卡畫面(False)變成調整畫面(True)時，觸發捲動
        should_scroll = True
        
    # 如果只是單純調整滑桿(狀態未變)，同步紀錄後退出，不執行 JS
    if not should_scroll:
        st.session_state.last_stage = st.session_state.stage
        st.session_state.last_year = st.session_state.year
        st.session_state.last_rebalance = st.session_state.waiting_for_rebalance
        return

    # 3. 確實進入新階段了，更新狀態
    st.session_state.last_stage = st.session_state.stage
    st.session_state.last_year = st.session_state.year
    st.session_state.last_rebalance = st.session_state.waiting_for_rebalance

    # 4. 執行霸道捲動 JS (連續執行 1 秒)
    js = f"""
    <script>
        var timestamp = {time.time()};
        
        function forceScroll() {{
            var target = window.parent.document.getElementById('top-anchor');
            var viewContainer = window.parent.document.querySelector("[data-testid='stAppViewContainer']");
            
            if (target) {{
                target.scrollIntoView({{behavior: 'auto', block: 'start'}});
            }}
            if (viewContainer) {{
                viewContainer.scrollTop = 0;
            }}
        }}

        // 立即執行
        forceScroll();
        
        // 連續轟炸 1 秒 (對抗手機渲染延遲)
        var count = 0;
        var intervalId = setInterval(function(){{
            forceScroll();
            count++;
            if(count > 20) clearInterval(intervalId);
        }}, 50);
    </script>
    """
    components.html(js, height=0)

# 🔥 立即執行捲動檢查
scroll_to_top()

# ---------------- 下方接續 CSS 設定與主程式 ----------------

# --- 2. ✨ 現代 FinTech 風格 CSS (強力修正字體顏色版) ✨ ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Noto+Sans+TC:wght@400;700&display=swap');

    :root {
        --primary: #2563EB;
        --primary-dark: #1E40AF;
        --secondary: #F59E0B;
        --bg-main: #F3F4F6;
        --bg-card: #FFFFFF;
        --text-main: #1F2937;
        --text-sub: #6B7280;
        --radius: 12px;
    }

    .stApp {
        background-color: var(--bg-main);
        color: var(--text-main);
        font-family: 'Inter', 'Noto Sans TC', sans-serif;
    }
    
    h1 { color: var(--primary-dark) !important; font-weight: 800 !important; text-align: center; margin-bottom: 0.5rem !important; }
    h2, h3 { color: var(--text-main) !important; font-weight: 700; }
    p, span, div { color: var(--text-main); }
    .caption { color: var(--text-sub); font-size: 0.9rem; }

    div[data-testid="stExpander"], div[data-testid="stContainer"] {
        background: var(--bg-card);
        border-radius: var(--radius);
        border: 1px solid #E5E7EB;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        padding: 24px;
        margin-bottom: 24px;
    }
    
    /* --- 按鈕樣式強力修正區 Start --- */
    div.stButton > button {
        background-color: white;
        color: var(--text-main);
        border: 1px solid #D1D5DB;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.2s;
        width: 100%;
    }
    div.stButton > button:hover {
        background-color: #F9FAFB;
        border-color: var(--primary);
        color: var(--primary);
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--primary), var(--primary-dark)) !important;
        border: none !important;
        box-shadow: 0 4px 6px rgba(37, 99, 235, 0.2);
    }
    div.stButton > button[kind="primary"],
    div.stButton > button[kind="primary"] > div,
    div.stButton > button[kind="primary"] p {
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
    }
    div.stButton > button[kind="primary"]:hover {
        box-shadow: 0 6px 10px rgba(37, 99, 235, 0.3) !important;
    }
    div.stButton > button[kind="primary"]:hover,
    div.stButton > button[kind="primary"]:hover > div,
    div.stButton > button[kind="primary"]:hover p {
        color: #FFFFFF !important;
    }
    div.stButton > button[kind="primary"]:focus:not(:active) {
        border-color: transparent !important;
        color: #FFFFFF !important;
    }
    /* --- 按鈕樣式修正區 End --- */

    .stTextInput > div > div > input, .stNumberInput > div > div > input {
        background-color: #F9FAFB;
        color: var(--text-main);
        border: 1px solid #D1D5DB;
        border-radius: 8px;
    }
    div[data-testid="stMetricValue"] { font-family: 'Inter', sans-serif; font-weight: 700; color: var(--primary-dark) !important; }
    div[data-testid="stMetricLabel"] { color: var(--text-sub) !important; font-weight: 500; }
    .stProgress > div > div > div > div { background-color: var(--primary); }
    section[data-testid="stSidebar"] { background-color: white; border-right: 1px solid #E5E7EB; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 初始化 ---
ASSET_KEYS = ['Dividend', 'USBond', 'TWStock', 'Cash', 'Crypto']
ASSET_NAMES = {'Dividend': '分紅收益', 'USBond': '美債', 'TWStock': '台股', 'Cash': '現金', 'Crypto': '加密幣'}
FINANCE_COLORS = {'分紅收益': '#F59E0B', '美債': '#3B82F6', '台股': '#EF4444', '現金': '#9CA3AF', '加密幣': '#8B5CF6'}

if 'stage' not in st.session_state: st.session_state.stage = 'login'
if 'year' not in st.session_state: st.session_state.year = 0
if 'assets' not in st.session_state: st.session_state.assets = {k: 0 for k in ASSET_KEYS}
if 'history' not in st.session_state: st.session_state.history = []
if 'user_name' not in st.session_state: st.session_state.user_name = ""
if 'drawn_cards' not in st.session_state: st.session_state.drawn_cards = []
if 'config_history' not in st.session_state: st.session_state.config_history = {}
if 'data_saved' not in st.session_state: st.session_state.data_saved = False

# --- 輔助函數 ---
def render_asset_snapshot(current_assets, title="📊 當前資產快照"):
    """渲染資產快照區塊"""
    st.markdown(f"### {title}")
    snap_c1, snap_c2 = st.columns([1, 1])
    
    with snap_c1:
        df_snap = pd.DataFrame({
            'Asset_Name': [ASSET_NAMES[k] for k in ASSET_KEYS],
            'Value': [current_assets[k] for k in ASSET_KEYS]
        })
        fig_snap = px.pie(
            df_snap, values='Value', names='Asset_Name', 
            color='Asset_Name', color_discrete_map=FINANCE_COLORS,
            hole=0.5
        )
        fig_snap.update_layout(
            showlegend=False, margin=dict(l=0, r=0, t=0, b=0), height=200,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            annotations=[dict(text='資產分佈', x=0.5, y=0.5, font_size=14, showarrow=False, font=dict(color='#1F2937'))],
            font=dict(color='#1F2937')
        )
        fig_snap.update_traces(textinfo='percent+label', textposition='inside')
        st.plotly_chart(fig_snap, use_container_width=True)
        
    with snap_c2:
        total_val = sum(current_assets.values())
        table_data = []
        for k in ASSET_KEYS:
            val = current_assets[k]
            pct = (val / total_val) * 100 if total_val > 0 else 0
            table_data.append({"資產": ASSET_NAMES[k], "金額 ($)": f"${int(val):,}", "佔比": f"{pct:.1f}%"})
        st.dataframe(pd.DataFrame(table_data), hide_index=True, use_container_width=True)

# --- 側邊欄 ---
ADMIN_PASSWORD = "tsts"
if 'admin_unlocked' not in st.session_state: st.session_state.admin_unlocked = False
# ==========================================
# 👑 管理員超級控制台 (Admin Super Panel)
# ==========================================
with st.sidebar:
    st.markdown("### 🏦 IFRC 管理員後台")
    if not st.session_state.admin_unlocked:
        st.info("🔒 需要管理員權限")
        pwd_input = st.text_input("輸入密碼", type="password", key="admin_pwd_input")
        if pwd_input == ADMIN_PASSWORD:
            st.session_state.admin_unlocked = True
            st.rerun()
    else:
        st.success("✅ 系統管理權限已解鎖")
        
        # --- 1. 遊戲進程控制 (跳轉功能) ---
        with st.expander("🚀 頁面快速跳轉", expanded=False):
            target_stage = st.selectbox(
                "切換至階段",
                options=['login', 'setup', 'playing', 'finished'],
                index=['login', 'setup', 'playing', 'finished'].index(st.session_state.stage)
            )
            target_year = st.slider("調整當前年份", 0, 30, st.session_state.year)
            # 在管理員後台的「執行跳轉」按鈕中加入自動補數據邏輯
            if st.button("執行強制跳轉"):
                st.session_state.stage = target_stage
                st.session_state.year = target_year
                
                # 🔥 如果跳轉到結束頁且目前沒數據，塞入一筆假資料防止報錯
                if target_stage == 'finished' and not st.session_state.history:
                    st.session_state.history = [{'Year': 0, 'Total': 1000000}]
                    # 給予一些預設資產數值
                    for k in ASSET_KEYS:
                        st.session_state.assets[k] = 200000 
                        
                st.session_state.waiting_for_event = False
                st.session_state.waiting_for_rebalance = False
                st.rerun()

        # --- 2. 動態市場調控 (上帝模式) ---
        with st.expander("📈 市場動態環境調控", expanded=False):
            st.caption("調整後的基礎利率將影響下一個『10年跳轉』。")
            updated_rates = {}
            for k in ASSET_KEYS:
                updated_rates[k] = st.slider(f"{ASSET_NAMES[k]} 年化", -0.20, 0.20, st.session_state.dynamic_rates[k], step=0.01, format="%.2f")
            if st.button("儲存新市場設定"):
                st.session_state.dynamic_rates = updated_rates
                st.toast("市場參數已更新！", icon="🌍")

        # --- 3. 即時戰況與數據導出 ---
        with st.expander("📊 現場數據監控", expanded=True):
            active_users = get_active_user_count()
            st.metric("🟢 目前同時在線人數", f"{active_users} 人")
            st.markdown("---")            
            if os.path.exists(CSV_FILE):
                df_rec = pd.read_csv(CSV_FILE)
                st.write(f"目前累積完賽人數: `{len(df_rec)}`")
                if not df_rec.empty:
                    lb = df_rec[['姓名', '最終資產', '報酬率(%)']].sort_values(by='最終資產', ascending=False)
                    st.dataframe(lb.head(5), hide_index=True)
                
                with open(CSV_FILE, "rb") as f:
                    st.download_button("📥 下載完整 CSV", data=f, file_name="final_report.csv", mime="text/csv")
            else:
                st.info("尚無玩家數據")

        # --- 4. 系統維護 ---
        with st.expander("🧹 危險區域", expanded=False):
            if st.button("🔥 清空所有歷史記錄"):
                if os.path.exists(CSV_FILE):
                    os.remove(CSV_FILE)
                    st.success("數據已清空")
                    st.rerun()

        st.markdown("---")
        if st.button("🔒 重新鎖定系統"):
            st.session_state.admin_unlocked = False
            st.rerun()
# --- 標題 ---
st.markdown("""
    <div style="text-align: center; padding: 20px 0 40px 0;">
        <div style="
            font-size: 0.9rem; 
            font-weight: 800; 
            color: #9CA3AF; 
            letter-spacing: 3px; 
            margin-bottom: 8px;
            font-family: 'Inter', sans-serif;
            text-transform: uppercase;
        ">
            IFRC <span style="color: #F59E0B;">x</span> TS
        </div>
        <h1 style="
            font-size: 2.5rem; 
            color: #1E40AF; 
            font-weight: 800; 
            letter-spacing: -0.5px; 
            margin: 0;
            padding: 0;
        ">
            💰 扭轉命運 30 年
        </h1>
        <div style="
            color: #6B7280; 
            font-size: 1.2rem; 
            font-weight: 500; 
            margin-top: 8px;
        ">
            Wealth Management Simulation
        </div>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 階段 0: 登入
# ==========================================
if st.session_state.stage == 'login':
    with st.container():
        st.markdown("<div style='text-align: center; margin-bottom: 5px;'></div>", unsafe_allow_html=True)
        
        img_c1, img_c2, img_c3 = st.columns([1, 1, 1])
        with img_c2:
            image_path = "images/homepage.png"
            if os.path.exists(image_path):
                st.image(image_path, use_container_width=True) 
            else:
                st.info("📷 圖片讀取中...")

        st.markdown("<div style='text-align: center; color: #6B7280; font-size: 0.9rem; margin-bottom: 20px;'>扭轉命運的機會就在眼前，準備好了嗎？</div>", unsafe_allow_html=True)
        
        input_c1, input_c2, input_c3 = st.columns([1, 2, 1])
        with input_c2:
            name_input = st.text_input("請輸入玩家暱稱", placeholder="例如: 小明", key="login_name")
            st.write("")
            if st.button("▶ 開始挑戰", type="primary"):
                if name_input.strip():
                    st.session_state.user_name = name_input
                    st.session_state.stage = 'setup'
                    st.session_state.data_saved = False
                    st.rerun()
                else:
                    st.warning("⚠️ 請輸入暱稱以開始遊戲")

        # 👇 在登入按鈕下方加入這段
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #9CA3AF; font-size: 13px; margin-top: 20px;">
            <div style="display: inline-block; text-align: left; background: white; padding: 15px 30px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                <div style="font-weight: 700; color: #4B5563; margin-bottom: 8px; text-align: center;">製作團隊IFRCxTS</div>
                🔹 <b>總策劃：</b>Yen/全家/Color/EN/Liya/小天/Yuna/Renee<br>
                🔹 <b>技術支援：</b> Yen <br> 
                🔹 <b>美術支援：</b> Liya <br>    
                🔹 <b>遊戲設計：</b> 天行 & IFRC<br>
            </div>
        </div>
        """, unsafe_allow_html=True)
# ==========================================
# 階段 1: Setup
# ==========================================
elif st.session_state.stage == 'setup':
    with st.container():
        st.markdown(f"### 🚀 初始資產配置 (玩家: {st.session_state.user_name})")
        
        # --- 🔥 新增：基礎利率參考表 ---
        st.markdown("#### ℹ️ 市場基礎利率表 (無事件影響下)")
        st.caption("這是各類資產在「風平浪靜」時的理論年化報酬率，請作為配置參考。")
        
        # 準備表格數據
        rate_data = []
        risk_map = {
            'Dividend': '低 (穩定現金流)',
            'USBond': '極低 (避險首選)',
            'TWStock': '中高 (隨景氣波動)',
            'Cash': '無 (會被通膨侵蝕)',
            'Crypto': '極高 (心跳漏一拍)'
        }
        
        for key in ASSET_KEYS:
            rate_data.append({
                "資產項目": ASSET_NAMES[key],
                "基礎年化報酬": f"{int(BASE_RATES[key]*100)}%",
                "風險屬性": risk_map.get(key, "未知")
            })
            
        df_rates = pd.DataFrame(rate_data)
        
        # 顯示表格 (use_container_width讓表格撐滿寬度，看起來比較大器)
        st.dataframe(
            df_rates, 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "資產項目": st.column_config.TextColumn("資產項目", help="資產的種類"),
                "基礎年化報酬": st.column_config.TextColumn("基礎年化報酬", help="每年預期會自動增長的比例"),
            }
        )
        st.markdown("---")
        # ----------------------------------

        col_cap, col_space = st.columns([1, 2])
        with col_cap:
            initial_wealth = 1000000
            st.metric("💰 起始資金 (固定)", f"${initial_wealth:,}", help="所有玩家起跑點皆相同")
        
        st.markdown("#### 📊 第 0 年資產比例配置 (%)")
        c1, c2, c3, c4, c5 = st.columns(5)
        p1 = c1.number_input(f"{ASSET_NAMES['Dividend']}", 0, 100, 20)
        p2 = c2.number_input(f"{ASSET_NAMES['USBond']}", 0, 100, 20)
        p3 = c3.number_input(f"{ASSET_NAMES['TWStock']}", 0, 100, 20)
        p4 = c4.number_input(f"{ASSET_NAMES['Cash']}", 0, 100, 20)
        p5 = c5.number_input(f"{ASSET_NAMES['Crypto']}", 0, 100, 20)
        
        current_sum = p1+p2+p3+p4+p5
        if current_sum != 100:
            st.markdown(f"""
                <div style="background-color: #FEF2F2; color: #991B1B; padding: 12px; border-radius: 8px; border: 1px solid #FCA5A5; text-align: center; font-weight: 600;">
                    ⚠️ 目前總和為 {current_sum}% (目標: 100%)
                </div>
            """, unsafe_allow_html=True)
        else:
            st.write("")
            if st.button("確定配置 ✅", type="primary"):
                props = [p1, p2, p3, p4, p5]
                st.session_state.config_history['Year 0'] = {k: v for k, v in zip(ASSET_KEYS, props)}
                for i, key in enumerate(ASSET_KEYS):
                    st.session_state.assets[key] = initial_wealth * (props[i] / 100)
                
                record = {'Year': 0, 'Total': initial_wealth}
                record.update(st.session_state.assets)
                st.session_state.history.append(record)
                st.session_state.stage = 'playing'
                st.rerun()

# ==========================================
# 階段 2: 遊戲進行中 (Playing)
# ==========================================
elif st.session_state.stage == 'playing':
    total = sum(st.session_state.assets.values())
    roi = (total - st.session_state.history[0]['Total']) / st.session_state.history[0]['Total'] * 100
    
    with st.container():
        c_year, c_wealth, c_roi = st.columns(3)
        c_year.metric("目前年份", f"第 {st.session_state.year} 年", delta=f"剩餘 {30-st.session_state.year} 年", delta_color="off")
        c_wealth.metric("總資產", f"${int(total):,}")
        c_roi.metric("累積報酬率", f"{roi:.1f}%", delta_color="normal")
        st.write("")
        st.progress(st.session_state.year / 30)

    current_year = st.session_state.year
    
    st.markdown(f"""<div style="text-align: center; margin-bottom: 20px;"><h2 style="color: #EF4444 !important;">⚡ 重大財經事件發生 (Year {current_year})</h2></div>""", unsafe_allow_html=True)
    
# --- 1. 抽卡事件 ---
    if st.session_state.get('waiting_for_event', False):
        with st.container():
            
            render_asset_snapshot(st.session_state.assets, title="📊 當前資產快照")
            st.markdown("---")
            st.markdown(f"""<div style="text-align: center; margin-bottom: 20px;"><h2 style="color: #EF4444 !important;">⚡ 命運扭蛋 (Year {current_year})</h2></div>""", unsafe_allow_html=True)
            
            # 卡片封面與輸入邏輯
            current_input = st.session_state.get("event_card_input", "")
            temp_code = str(current_input).strip()
            
            if temp_code not in EVENT_CARDS:
                cover_img = "images/homepage.png"
                cover_c1, cover_c2, cover_c3 = st.columns([1, 1, 1])
                with cover_c2:
                    if os.path.exists(cover_img):
                        st.image(cover_img, use_container_width=True, caption="請輸入卡片代碼翻開命運...")
                    else:
                        st.markdown("<div style='text-align: center; font-size: 80px;'>🎴</div>", unsafe_allow_html=True)
            
            col_input, col_status = st.columns([2, 1])
            input_code = col_input.text_input(
                "請在此輸入卡片代碼 (3碼)",
                placeholder="例如: 101", 
                help="請查看您抽到的實體卡片，輸入上面的3位數編號",
                key="event_card_input"
            )
            clean_code = str(input_code).strip()
            
            if clean_code in EVENT_CARDS:
                card_data = EVENT_CARDS[clean_code]
                image_path = f"images/{clean_code}.png"
                
                col_img, col_desc = st.columns([1, 2])
                with col_img:
                    if os.path.exists(image_path): st.image(image_path, use_container_width=True)
                    else: st.info("📷 No Image")
                with col_desc:
                    st.markdown(f"""<div style="background: #F0F9FF; border-left: 4px solid #3B82F6; padding: 16px; border-radius: 4px; height: 100%;"><h3 style="margin-top: 0; color: #1E40AF !important;">{card_data['name']}</h3><p style="font-size: 1.1rem; color: #374151;">{card_data['desc']}</p></div>""", unsafe_allow_html=True)
                
                st.write("")
                st.write("#### 📊 市場衝擊預覽 (預估損益)")
                cols = st.columns(5)
                key_map = {'dividend': 'Dividend', 'bond': 'USBond', 'stock': 'TWStock', 'cash': 'Cash', 'crypto': 'Crypto'}
                metrics = [('分紅收益', 'dividend'), ('美債', 'bond'), ('台股', 'stock'), ('現金', 'cash'), ('加密幣', 'crypto')]
                
                for i, (name, card_key) in enumerate(metrics):
                    asset_key = key_map[card_key]
                    pct_change = card_data[card_key]
                    current_val = st.session_state.assets[asset_key] # 取得當前資產
                    impact_val = current_val * (pct_change / 100)
                    
                    color = '#EF4444' if pct_change < 0 else ('#10B981' if pct_change > 0 else '#6B7280')
                    arrow = '▼' if pct_change < 0 else ('▲' if pct_change > 0 else '-')
                    sign = '' if pct_change < 0 else ('+' if pct_change > 0 else '')
                    bg_color = '#FEF2F2' if pct_change < 0 else '#ECFDF5'
                    
                    # 🔥 修改處：增加顯示「當前」資產數值
                    cols[i].markdown(f"""
                    <div style="text-align: center; background: #fff; padding: 12px 5px; border-radius: 8px; border: 1px solid #E5E7EB; height: 100%;">
                        <div style="color: #6B7280; font-size: 13px; margin-bottom: 2px;">{name}</div>
                        <div style="color: #1F2937; font-size: 14px; font-weight: 600; border-bottom: 1px dashed #E5E7EB; padding-bottom: 4px; margin-bottom: 4px;">現: ${int(current_val):,}</div>
                        <div style="color: {color}; font-size: 18px; font-weight: bold; line-height: 1.2;">{arrow} {abs(pct_change)}%</div>
                        <div style="color: {color}; font-size: 13px; font-weight: 600; margin-top: 4px; background-color: {bg_color}; padding: 2px 4px; border-radius: 4px;">{sign}${int(impact_val):,}</div>
                    </div>
                    """, unsafe_allow_html=True)

                st.write("")
                if st.button("迎接命運衝擊 📉", type="primary"):
                    st.session_state.assets['Dividend'] *= (1 + card_data['dividend']/100)
                    st.session_state.assets['USBond']   *= (1 + card_data['bond']/100)
                    st.session_state.assets['TWStock']  *= (1 + card_data['stock']/100)
                    st.session_state.assets['Cash']     *= (1 + card_data['cash']/100)
                    st.session_state.assets['Crypto']   *= (1 + card_data['crypto']/100)
                    st.session_state.drawn_cards.append(f"第 {current_year} 年: [{clean_code}] {card_data['name']}")
                    last_rec = st.session_state.history[-1]
                    last_rec.update(st.session_state.assets)
                    last_rec['Total'] = sum(st.session_state.assets.values())
                    st.session_state.waiting_for_event = False
                    if current_year >= 30: st.session_state.stage = 'finished'
                    else: st.session_state.waiting_for_rebalance = True
                    st.rerun()

    # --- 2. 再平衡階段 ---
    elif st.session_state.get('waiting_for_rebalance', False):
        with st.container():
            current_total = sum(st.session_state.assets.values())
            
            render_asset_snapshot(st.session_state.assets, title="📊 衝擊後資產現況 (請進行再平衡)")
            st.markdown("---")

            st.markdown(f"### ⚖️ 資產再平衡配置 (Year {current_year})")
            st.markdown(f"""<div style="display: flex; align-items: center; background: #ECFDF5; padding: 15px; border-radius: 8px; color: #065F46; border: 1px solid #6EE7B7;"><span style="font-size: 1.2rem; font-weight: bold; margin-right: 10px;">目前總資產:</span><span style="font-size: 1.5rem; font-weight: 800;">${int(current_total):,}</span></div>""", unsafe_allow_html=True)
            
            # 🔥 修改處：計算浮點數預設值，完整複製當前比例
            current_pcts = {}
            for k in ASSET_KEYS:
                if current_total > 0:
                    # 使用小數點計算，不強制轉 int
                    current_pcts[k] = (st.session_state.assets[k] / current_total) * 100
                else:
                    current_pcts[k] = 20.0
            
            st.write("請調整下方比例 (預設為當前資產比例)：")
            
            c1, c2, c3, c4, c5 = st.columns(5)
            # 這裡的 input 改為 float 模式 (0.0 - 100.0)
            rb1 = c1.number_input(f"{ASSET_NAMES['Dividend']}", 0.0, 100.0, current_pcts['Dividend'], step=1.0, format="%.1f", key=f"rb1_{current_year}")
            rb2 = c2.number_input(f"{ASSET_NAMES['USBond']}", 0.0, 100.0, current_pcts['USBond'], step=1.0, format="%.1f", key=f"rb2_{current_year}")
            rb3 = c3.number_input(f"{ASSET_NAMES['TWStock']}", 0.0, 100.0, current_pcts['TWStock'], step=1.0, format="%.1f", key=f"rb3_{current_year}")
            rb4 = c4.number_input(f"{ASSET_NAMES['Cash']}", 0.0, 100.0, current_pcts['Cash'], step=1.0, format="%.1f", key=f"rb4_{current_year}")
            rb5 = c5.number_input(f"{ASSET_NAMES['Crypto']}", 0.0, 100.0, current_pcts['Crypto'], step=1.0, format="%.1f", key=f"rb5_{current_year}")
            
            total_rb = rb1 + rb2 + rb3 + rb4 + rb5
            # 浮點數比對，允許 0.01 的誤差
            if abs(total_rb - 100.0) > 0.01: 
                st.warning(f"⚠️ 比例總和錯誤: {total_rb:.1f}% (請手動調整至100%)")
            else:
                st.write("")
                if st.button("執行配置 ✅", type="primary"):
                    props = [rb1, rb2, rb3, rb4, rb5]
                    st.session_state.config_history[f'Year {current_year}'] = {k: v for k, v in zip(ASSET_KEYS, props)}
                    for i, key in enumerate(ASSET_KEYS):
                        st.session_state.assets[key] = current_total * (props[i] / 100)
                    last_rec = st.session_state.history[-1]
                    last_rec.update(st.session_state.assets)
                    st.session_state.waiting_for_rebalance = False
                    st.rerun()

# --- 3. 推進時間軸 ---
    elif current_year < 30:
        with st.container():
            st.markdown(f"### ⏩ 推進時間軸: 第 {current_year+1} - {current_year+10} 年")
            
            # 🔥 修改處：如果是第0年，把「資產配置快照」搬到這裡顯示
            if current_year == 0:
                render_asset_snapshot(st.session_state.assets, title="📊 第 0 年初始配置確認")
                st.write("") # 加一點留白

            run_simulation = False
            
            # 🔥 修改處：建立一個 Placeholder 來包住按鈕，按下後可以把它清空
            action_placeholder = st.empty()
            
            with action_placeholder.container():
                # 按鈕區域佈局
                if current_year == 0:
                    c_back, c_run = st.columns([1, 4])
                    with c_back:
                        if st.button("⬅️ 返回重設"):
                            st.session_state.stage = 'setup'
                            st.session_state.history = [] 
                            st.rerun()
                    with c_run:
                        if st.button(f"🚀 啟動時光機 (前往第 {current_year+10} 年)", type="primary"):
                            run_simulation = True
                else:
                    if st.button(f"🚀 前往下一個十年 (Year {current_year+10})", type="primary"):
                        run_simulation = True
            
            # --- ⏳ 轉場動畫與計算邏輯 ---
            if run_simulation:
                # 🔥 修改處：立刻把上面的按鈕區塊清空，讓按鈕消失
                action_placeholder.empty()

                # 1. 建立一個佔位區塊，用來顯示全螢幕過場動畫
                transition_placeholder = st.empty()
                
                # 2. 決定過場圖片
                if current_year == 0:
                    jump_img = "images/wait1.png"
                    jump_text = "🚀 3, 2, 1... 投資旅程正式展開！"
                elif current_year == 10:
                    jump_img = "images/wait2.png"
                    jump_text = "📈 十年過去了，市場風雲變色..."
                else:
                    jump_img = "images/wait3.png"
                    jump_text = "🏁 最後衝刺！迎向財富自由的終點！"
                
                # 3. 顯示過場畫面
                with transition_placeholder.container():
                    st.markdown("---")
                    t_c1, t_c2, t_c3 = st.columns([1, 2, 1])
                    with t_c2:
                        st.markdown(f"<h2 style='text-align: center; color: #2563EB;'>{jump_text}</h2>", unsafe_allow_html=True)
                        
                        # 🔥 修改處：進度條 (Progress Bar) 移到 圖片 (Image) 上面
                        progress_text = "正在計算複利效應..."
                        my_bar = st.progress(0, text=progress_text)
                        
                        if os.path.exists(jump_img):
                            st.image(jump_img, use_container_width=True)
                        else:
                            st.markdown("""<div style='text-align: center; font-size: 80px; margin: 40px 0; animation: bounce 1s infinite;'>⏳ ➡️ 💰</div>""", unsafe_allow_html=True)
                        
                        # 跑進度條動畫
                        for percent_complete in range(100):
                            time.sleep(0.015) 
                            my_bar.progress(percent_complete + 1, text=progress_text)
                    
                    time.sleep(0.5) 

                # 4. 執行數學計算 (後台)
                for y in range(1, 11):
                    st.session_state.assets['Dividend'] *= (1 + st.session_state.dynamic_rates['Dividend']) 
                    st.session_state.assets['USBond']   *= (1 + st.session_state.dynamic_rates['USBond']) 
                    st.session_state.assets['TWStock']  *= (1 + st.session_state.dynamic_rates['TWStock']) 
                    st.session_state.assets['Cash']     *= (1 + st.session_state.dynamic_rates['Cash'])
                    st.session_state.assets['Crypto']   *= (1 + st.session_state.dynamic_rates['Crypto']) 
                    
                    record = {'Year': current_year + y, 'Total': sum(st.session_state.assets.values())}
                    record.update(st.session_state.assets)
                    st.session_state.history.append(record)
                
                st.session_state.year += 10
                st.session_state.waiting_for_event = True
                
                transition_placeholder.empty()
                st.rerun()

    # 🔥 記得移除原本放在最下面的 render_asset_snapshot 呼叫（因為已經搬到上面了）
    # if len(st.session_state.history) > 0 and current_year == 0: ... (這段請刪除或確保不會重複出現)


# ==========================================
# 階段 3: Finished
# ==========================================
elif st.session_state.stage == 'finished':
    st.balloons()
    final_wealth = sum(st.session_state.assets.values())
    roi = (final_wealth - st.session_state.history[0]['Total']) / st.session_state.history[0]['Total'] * 100
    
 # --- 🏆 30年最終分級 (修正版) ---
    # 邏輯：
    # 1. 虧損 (ROI < 0): 遇到黑天鵝，直接破產。
    # 2. 跑輸通膨 (0 < ROI < 150): 30年只賺不到1.5倍，其實購買力是下降的 (定存族)。
    # 3. 普通人 (150 < ROI < 500): 合理的股市回報。
    # 4. 高手 (500 < ROI < 1000): 有避開大跌，並吃到複利。
    # 5. 傳奇 (> 1000): 運氣與實力兼具。

    if roi < 0:
        rank_title = "💸 破產俱樂部"
        rank_desc = "黑天鵝來襲！波動性吃掉了你的本金..."
        bg_gradient = "linear-gradient(135deg, #7f1d1d, #ef4444)" # 深紅警戒
    elif roi < 200:
        rank_title = "🐢 佛系定存族"
        rank_desc = "這30年你只贏了帳面，卻輸給了真實通膨。"
        bg_gradient = "linear-gradient(135deg, #4b5563, #9ca3af)" # 水泥灰
    elif roi < 300:
        rank_title = "🐢 佛系理財族"
        rank_desc = "這30年只贏了通貨膨脹，接下來能追求財富倍增。"
        bg_gradient = "linear-gradient(135deg, #4b5563, #9ca3af)" # 水泥灰
    elif roi < 400:
        rank_title = "💼 理財小白"
        rank_desc = "表現穩健！開始有資產配置觀念。"
        bg_gradient = "linear-gradient(135deg, #059669, #34d399)" # 穩健綠    
    elif roi < 600:
        rank_title = "💼 理財老手"
        rank_desc = "表現穩健！這是大多數普通人退休目標。"
        bg_gradient = "linear-gradient(135deg, #059669, #34d399)" # 穩健綠
    elif roi < 800:
        rank_title = "🚀 投資理財老鳥"
        rank_desc = "眼光精準！你的資產成長速度驚人。"
        bg_gradient = "linear-gradient(135deg, #7c3aed, #a78bfa)" # 尊爵紫    
    elif roi < 1200:
        rank_title = "🚀 自由財富號"
        rank_desc = "眼光精準！你的資產成長速度驚人。"
        bg_gradient = "linear-gradient(135deg, #7c3aed, #a78bfa)" # 尊爵紫
    else:
        rank_title = "👑 投資界的神"
        rank_desc = "30年資產翻了10倍以上，巴菲特都要叫你老師！"
        bg_gradient = "linear-gradient(135deg, #b45309, #fbbf24)" # 傳說金
    

 # --- 📱 IG 限動截圖區 (置中顯示) ---
    with st.container():
        st.markdown("### 📸 IG 限動截圖區")
        st.caption("👇 請直接對下方卡片進行螢幕截圖 (Screenshot)，即可分享至 IG 限時動態！")
        
        ig_c1, ig_c2, ig_c3 = st.columns([1, 2, 1])
        
        with ig_c2:
            # ⚠️ 注意：這裡的 HTML 字串盡量靠左，不要有太多縮排，以免被誤判為程式碼區塊
            st.markdown(f"""
<div style="width: 100%; max-width: 380px; margin: 0 auto; background: {bg_gradient}; border-radius: 20px; padding: 30px 20px; color: white; box-shadow: 0 10px 25px rgba(0,0,0,0.3); text-align: center; border: 4px solid rgba(255,255,255,0.2); font-family: 'Inter', sans-serif;">
    <div style="font-size: 14px; opacity: 0.4; letter-spacing: 2px; margin-bottom: 10px;">IFRC WEALTH SIMULATION</div>
    <div style="background: rgba(255,255,255,0.15); border-radius: 50%; width: 80px; height: 80px; margin: 0 auto 15px auto; display: flex; align-items: center; justify-content: center; font-size: 40px; backdrop-filter: blur(5px);">
        {rank_title.split(' ')[0]}
    </div>
    <div style="font-size: 28px; font-weight: 800; margin-bottom: 5px; text-shadow: none;">
        {rank_title.split(' ')[1]}
    </div>
    <div style="font-size: 14px; opacity: 0.9; margin-bottom: 25px; font-style: italic;">
        “{rank_desc}”
    </div>
    <div style="background: rgba(255,255,255,0.95); border-radius: 12px; padding: 15px; color: #1F2937; margin-bottom: 15px;">
        <div style="font-size: 12px; color: #6B7280; font-weight: 600;">最終資產 (30年)</div>
        <div style="font-size: 32px; font-weight: 800; color: #111827; line-height: 1.2;">
            ${int(final_wealth):,}
        </div>
    </div>
    <div style="display: flex; justify-content: space-between; gap: 10px;">
        <div style="flex: 1; background: rgba(0,0,0,0.2); border-radius: 12px; padding: 10px;">
            <div style="font-size: 11px; opacity: 0.8;">總報酬率</div>
            <div style="font-size: 18px; font-weight: 700;">{roi:+.1f}%</div>
        </div>
        <div style="flex: 1; background: rgba(0,0,0,0.2); border-radius: 12px; padding: 10px;">
            <div style="font-size: 11px; opacity: 0.8;">玩家</div>
            <div style="font-size: 18px; font-weight: 700;">{st.session_state.user_name}</div>
        </div>
    </div>
    <div style="margin-top: 25px; font-size: 12px; opacity: 0.6; border-top: 1px solid rgba(255,255,255,0.2); padding-top: 15px;">
        扭轉命運 30 年 • IFRC Edition
        <br>#InvestmentChallenge #IFRC
    </div>
</div>
            """, unsafe_allow_html=True)
    
    # ... (以下接續原本的詳細數據分析代碼: c1, c2 = st.columns(2) ...)
    # 記得要把原本 title 的部分 ("🏆 挑戰完成" 那塊) 稍微往下移或保留皆可，
    # 但這個 IG 卡片最好放在最上面，因為玩家一結束最想看結果。

    with st.container():
        st.markdown(f"""<div style="text-align: center;"><h1 style="color: #F59E0B !important;">🏆 挑戰完成</h1><p style="font-size: 1.2rem;">恭喜玩家 <b>{st.session_state.user_name}</b> 完成 30 年投資模擬！</p></div>""", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        c1.markdown(f"""<div style="text-align: center; border: 1px solid #F59E0B; padding: 24px; background: #FFFBEB; border-radius: 12px;"><div style="color: #92400E; font-size: 14px; font-weight: 600;">最終資產總額</div><div style="color: #D97706; font-size: 36px; font-weight: 800; font-family: 'Inter';">${int(final_wealth):,}</div></div>""", unsafe_allow_html=True)
        roi_color = '#EF4444' if roi < 0 else '#10B981'
        bg_color = '#FEF2F2' if roi < 0 else '#ECFDF5'
        border_color = '#FCA5A5' if roi < 0 else '#6EE7B7'
        c2.markdown(f"""<div style="text-align: center; border: 1px solid {border_color}; padding: 24px; background: {bg_color}; border-radius: 12px;"><div style="color: #374151; font-size: 14px; font-weight: 600;">總累積報酬率</div><div style="color: {roi_color}; font-size: 36px; font-weight: 800; font-family: 'Inter';">{roi:.1f}%</div></div>""", unsafe_allow_html=True)
        
        # 🔥 新增：歷史配置策略回顧
        if st.session_state.config_history:
            st.markdown("---")
            st.subheader("🎛️ 歷史配置策略回顧")
            
            # 將配置紀錄轉換為 DataFrame
            df_config = pd.DataFrame(st.session_state.config_history).T # 轉置: 列是年份, 欄是資產
            df_config = df_config.rename(columns=ASSET_NAMES) # 換成中文名稱
            
            # 準備畫圖用的數據 (Melt)
            df_config_melt = df_config.reset_index().melt(id_vars='index', var_name='Asset', value_name='Percentage')
            
            c_chart, c_table = st.columns([2, 1])
            
            with c_chart:
                fig_alloc = px.bar(
                    df_config_melt, 
                    x='index', 
                    y='Percentage', 
                    color='Asset', 
                    color_discrete_map=FINANCE_COLORS,
                    title="配置比例變化圖",
                    labels={'index': '年份', 'Percentage': '配置比例 (%)'}
                )
                fig_alloc.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#000000"),
                    margin=dict(t=30, b=0, l=0, r=0)
                )
                st.plotly_chart(fig_alloc, use_container_width=True, theme=None)
                
            with c_table:
                st.write("詳細配置數據 (%)")
                st.dataframe(df_config.style.format("{:.1f}%"), use_container_width=True) # 修改為顯示小數點

        # 🔥 修改處：結算頁面顯示最終資產快照 (Pie + Table)
        st.markdown("---")
        render_asset_snapshot(st.session_state.assets, title="📊 最終資產分佈")

        # 🔥 修改處：結算頁面顯示資產成長趨勢圖 (Area Chart)
        st.markdown("---")
        st.subheader("📈 30年資產成長回顧")
        df = pd.DataFrame(st.session_state.history)
        df_melted = df.melt(id_vars=['Year', 'Total'], value_vars=list(ASSET_KEYS), var_name='Asset_Type', value_name='Value')
        df_melted['Asset_Name'] = df_melted['Asset_Type'].map(ASSET_NAMES)
        
        fig = px.area(df_melted, x="Year", y="Value", color="Asset_Name", color_discrete_map=FINANCE_COLORS, template="plotly_white")
        fig.update_layout(
            hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None),
            margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(title="年份", showgrid=False, tickmode='linear'), yaxis=dict(title="資產價值 ($)", showgrid=True, gridcolor='#F3F4F6', tickformat=".2s"),
            font=dict(color="#060606")
        )
        st.plotly_chart(fig, use_container_width=True, theme=None)

        st.markdown("---")
        st.subheader("🎴 命運歷程回顧")
        
        if len(st.session_state.drawn_cards) > 0:
            for card_info in st.session_state.drawn_cards:
                st.markdown(f"""
                <div style="background: white; border-left: 4px solid #F59E0B; padding: 16px; margin-bottom: 12px; border-radius: 0 8px 8px 0; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                    {card_info}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("本次模擬無重大事件發生。")

        st.markdown("---")
        st.subheader("📝 心得與反饋")
        feedback = st.text_area("請留下您的遊戲心得")
        if st.button("💾 儲存並結束", type="primary"):
            if not st.session_state.data_saved:
                save_data_to_csv(st.session_state.user_name, final_wealth, roi, st.session_state.drawn_cards, st.session_state.config_history, feedback)
                st.session_state.data_saved = True
                st.success("✅ 數據已成功上傳。")
                import time
                time.sleep(1) 
                st.rerun()    

    if st.button("🔄 開啟新挑戰"):
        for key in st.session_state.keys(): del st.session_state[key]
        st.rerun()
# ------------------------------------------------
# 🦶 頁尾 Footer (放在程式碼最後面，縮排最外層)
# ------------------------------------------------
st.markdown("""
    <div style="
        text-align: center; 
        margin-top: 60px; 
        padding-bottom: 30px; 
        color: #D1D5DB; /* 淺灰色 */
        font-size: 13px; 
        font-weight: 600;
        font-family: 'Inter', sans-serif;
        letter-spacing: 2px;
        opacity: 0.8;
    ">
        IFRC <span style="color: #F59E0B;">x</span> TS
    </div>
""", unsafe_allow_html=True)       
