import streamlit as st
import pandas as pd
import numpy as np
import os
import csv
import time
from datetime import datetime
import plotly.express as px
import streamlit.components.v1 as components
import random # <--- 新增這行
import base64 # 記得確認有沒有 import 這個
import json
from filelock import FileLock # 記得加這行

# 定義鎖文件 (會在同目錄下產生 .lock 檔)
SNAPSHOT_LOCK = "game_snapshots.csv.lock"
RECORD_LOCK = "game_data_records.csv.lock"

@st.cache_data(show_spinner=False)
def img_uri(path: str, max_px: int = 0) -> str:
    """讀圖並轉成可直接放進 <img src> / CSS url() 的 data URI (快取)。

    max_px > 0 時等比縮到長邊不超過 max_px 並以 JPEG 重新編碼。
    原因：卡背圖原檔 1000x1000、base64 後約 100KB，但畫面只顯示約 210px；
    這串字每次頁面重整都要經 websocket 送到瀏覽器，多人同時使用時很吃頻寬。
    改成 JPEG 縮圖後約 30KB (-70%)，且 JPEG 沒有相容性問題 (現場手機一定顯示得出來)。
    """
    try:
        if max_px > 0:
            from PIL import Image
            import io
            with Image.open(path) as im:
                im.thumbnail((max_px, max_px), Image.LANCZOS)
                if im.mode != "RGB":
                    im = im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")
                if im.mode == "RGBA":  # JPEG 不支援透明 -> 疊到白底
                    bg = Image.new("RGB", im.size, (255, 255, 255))
                    bg.paste(im, mask=im.split()[-1])
                    im = bg
                buf = io.BytesIO()
                im.save(buf, format="JPEG", quality=85, optimize=True)
                return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
        with open(path, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    except Exception:
        return ""


def hide_stale_js(duration_ms: int) -> str:
    """動畫播放期間隱藏 Streamlit 的『舊畫面殘影』(data-stale)，結束後自動還原。

    Streamlit 在腳本跑完前會保留上一輪的 DOM 並調暗，轉場動畫期間看起來像殘影。
    這段腳本從元件 iframe 注入一條 CSS 到母文件；還原用的計時器必須「建立在母文件的
    執行環境」，否則 iframe 一被移除，計時器的閉包就跟著失效、樣式永遠留著
    (那會害之後每次重整都閃爍)。
    """
    token = f"t{int(time.time() * 1000)}"
    return f"""
    <script>
      (function() {{
        var doc = window.parent.document, ID = 'ifrc-hide-stale';
        var old = doc.getElementById(ID);
        if (old) old.remove();

        var st = doc.createElement('style');
        st.id = ID;
        st.dataset.token = '{token}';
        st.textContent = "[data-stale='true']{{display:none!important;}}";
        doc.head.appendChild(st);

        // 在母文件執行環境建立還原計時器 (帶 token，避免誤刪後續動畫的樣式)
        var sc = doc.createElement('script');
        sc.textContent =
          "setTimeout(function(){{" +
          "  var e = document.getElementById('ifrc-hide-stale');" +
          "  if (e && e.dataset.token === '{token}') e.remove();" +
          "}}, {duration_ms});";
        doc.head.appendChild(sc);
        sc.remove();
      }})();
    </script>
    """


def decade_multiplier(rate: float) -> float:
    """某年化利率複利十年後的倍數"""
    return (1 + rate) ** 10


def autoplay_audio(file_path: str):
    """讀取音效檔並自動播放"""
    try:
        with open(file_path, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            mime = "audio/aac" if file_path.lower().endswith(".aac") else "audio/mpeg"
            md = f"""
                <audio autoplay>
                <source src="data:{mime};base64,{b64}" type="{mime}">
                </audio>
                """
            st.markdown(md, unsafe_allow_html=True)
    except Exception as e:
        # 如果找不到檔案或出錯，靜默失敗，不要讓程式崩潰
        pass
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

# 🔥 好牌/壞牌池 (供獨享版保底機制使用)：台股上漲的事件視為好牌
GOOD_CARDS = [k for k, v in EVENT_CARDS.items() if v['stock'] > 0]
BAD_CARDS = [k for k, v in EVENT_CARDS.items() if v['stock'] <= 0]

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
    lock = FileLock(RECORD_LOCK)
    try:
        with lock.acquire(timeout=10):
            file_exists = os.path.isfile(CSV_FILE)
            with open(CSV_FILE, mode='a', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=data.keys())
                if not file_exists: writer.writeheader()
                writer.writerow(data)
    except Exception as e:
        st.error(f"存檔失敗，請重試: {e}")
# ==========================================
# 📥 第一步：存檔函數 (請確保這段代碼放在最上面的函數定義區)
# ==========================================

SNAPSHOT_FILE = 'game_snapshots.csv'

def save_snapshot(name, year, assets, current_config):
    """
    記錄當下的資產快照與配置 (供後台即時讀取)
    """
    total = sum(assets.values())
    # 計算目前的 ROI
    roi = (total - 1000000) / 1000000 * 100
    
    # 防呆：如果 current_config 是空的，給預設值
    if current_config is None:
        current_config = {}
        
    # 整理配置字串
    config_str = " | ".join([f"{ASSET_NAMES.get(k, k)}:{float(v):.0f}%" for k, v in current_config.items()]) if current_config else "初始/未變動"

    data = {
        '更新時間': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        '姓名': name,
        '目前年份': year,
        '總資產': int(total),
        '報酬率(%)': round(roi, 1),
        '當下配置策略': config_str
    }
    
    # 寫入 CSV (如果檔案不存在會自動建立)
    lock = FileLock(SNAPSHOT_LOCK)
    try:
        with lock.acquire(timeout=10):
            file_exists = os.path.isfile(SNAPSHOT_FILE)
            with open(SNAPSHOT_FILE, mode='a', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=data.keys())
                if not file_exists: writer.writeheader()
                writer.writerow(data)
    except Exception as e:
        print(f"Snapshot Error: {e}")
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
if 'waiting_for_event' not in st.session_state: st.session_state.waiting_for_event = False

# 🔥 獨享版保底機制：整局三次抽卡中，隨機挑一次必出好牌 (恰好一次)
if 'lucky_draw_round' not in st.session_state: st.session_state.lucky_draw_round = random.randint(1, 3)
if 'draw_count' not in st.session_state: st.session_state.draw_count = 0
if 'solo_pick' not in st.session_state: st.session_state.solo_pick = None
if 'flip_pending' not in st.session_state: st.session_state.flip_pending = None
if 'jump_pending' not in st.session_state: st.session_state.jump_pending = False
if 'last_decade_report' not in st.session_state: st.session_state.last_decade_report = None

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
ASSET_NAMES = {'Dividend': '分紅收益', 'USBond': '美債', 'TWStock': '台股', 'Cash': '現金', 'Crypto': '加密幣'}
FINANCE_COLORS = {'分紅收益': '#F59E0B', '美債': '#3B82F6', '台股': '#EF4444', '現金': '#9CA3AF', '加密幣': '#8B5CF6'}

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
                st.session_state.jump_pending = False
                st.session_state.flip_pending = None
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
        #    st.metric("🟢 目前同時在線人數", f"{active_users} 人")
            st.markdown("---")            
            # 🔥 【加入這段】即時戰況看板
            if st.button("🔄 刷新戰況榜"):
                st.rerun()
                
            if os.path.exists(SNAPSHOT_FILE):
                try:
                    df_snap = pd.read_csv(SNAPSHOT_FILE)
                    if not df_snap.empty:
                        # 邏輯：依時間排序 -> 依姓名去重(留最新) -> 依資產排序
                        df_snap = df_snap.sort_values(by=['更新時間'], ascending=False)
                        df_leaderboard = df_snap.drop_duplicates(subset=['姓名'], keep='first')
                        df_leaderboard = df_leaderboard.sort_values(by='總資產', ascending=False).reset_index(drop=True)
                        
                        # 顯示第一名 Highlights
                        if len(df_leaderboard) > 0:
                            top1 = df_leaderboard.iloc[0]
                            st.info(f"🥇 目前領先: **{top1['姓名']}** (Year {top1['目前年份']})\n\n💰 資產: ${int(top1['總資產']):,}")
                        
                        # 顯示完整表格
                        st.dataframe(
                            df_leaderboard[['姓名', '目前年份', '總資產', '報酬率(%)', '當下配置策略']], 
                            hide_index=True,
                            use_container_width=True
                        )
                    else:
                        st.caption("等待玩家數據...")
                except Exception as e:
                    st.error(f"讀取錯誤: {e}")
            else:
                st.caption("尚無快照紀錄檔")

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
                if os.path.exists(SNAPSHOT_FILE):
                    os.remove(SNAPSHOT_FILE)
                st.success("數據已全面清空 (包含即時戰況與結算紀錄)！")
                time.sleep(1)
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
            IFRC <span style="color: #F59E0B;">x</span> TS <span style="color: #F59E0B;">x</span> 人生CEO
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
# 階段 0: 登入與模式選擇 (Login & Mode Selection)
# ==========================================
if st.session_state.stage == 'login':
    with st.container():
        st.markdown("<div style='text-align: center; margin-bottom: 5px;'></div>", unsafe_allow_html=True)
        
        # 圖片區塊 (保持置中)
        _, img_c, _ = st.columns([1, 1, 1])
        with img_c:
            image_path = "images/homepage.png"
            if os.path.exists(image_path):
                st.image(image_path, use_container_width=True) 
            else:
                st.info("📷 圖片讀取中...")

        st.markdown("<div style='text-align: center; color: #6B7280; font-size: 0.9rem; margin-bottom: 20px;'>扭轉命運的機會就在眼前，準備好了嗎？</div>", unsafe_allow_html=True)
        
        # 暱稱輸入區塊 (保持置中)
        _, input_c, _ = st.columns([1, 2, 1])
        with input_c:
            name_input = st.text_input("請輸入玩家暱稱", placeholder="例如: 小明", key="login_name")
            st.write("")
        
        st.markdown("<h5 style='text-align: center; color: #374151;'>選擇您的挑戰模式</h5>", unsafe_allow_html=True)
        
        # --- 🔥 核心修正：解決 Wide Mode 跑版 ---
        # 1. 先建立一個置中的「容器欄位」(center_container)
        #    比例 [3, 4, 3] 代表中間佔 40% 寬度，左右留白各 30%。
        #    這樣在大螢幕上不會太寬，在手機上也不會太擠。
        _, center_container, _ = st.columns([3, 4, 3])
        
        with center_container:
            # 2. 在這個限制好的容器內，再切分左右兩個按鈕
            #    gap="large" 讓兩個選項中間有一點好看的間距
            inner_c1, inner_c2 = st.columns(2, gap="large")
            
            # --- 左邊：派對版 ---
            with inner_c1:
                st.markdown("""
                <div style="text-align: center; background-color: #F3F4F6; padding: 10px; border-radius: 8px; border: 1px solid #E5E7EB; height: 100%;">
                    <div style="font-size: 1.2rem;">🎴</div>
                    <div style="font-weight: bold; color: #4B5563; margin-top: 4px;">派對版</div>
                    <div style="font-size: 0.75rem; color: #9CA3AF;">輸入實體卡號</div>
                </div>
                """, unsafe_allow_html=True)
                st.write("") # 間距
                if st.button("選擇多人 👥", type="secondary", key="btn_party", use_container_width=True):
                    if name_input.strip():
                        st.session_state.user_name = name_input
                        st.session_state.game_mode = 'party'
                        st.session_state.stage = 'setup'
                        st.session_state.data_saved = False
                        st.rerun()
                    else:
                        st.warning("⚠️ 請輸入暱稱")

            # --- 右邊：獨享版 ---
            with inner_c2:
                st.markdown("""
                <div style="text-align: center; background-color: #EFF6FF; padding: 10px; border-radius: 8px; border: 1px solid #BFDBFE; height: 100%;">
                    <div style="font-size: 1.2rem;">🎲</div>
                    <div style="font-weight: bold; color: #1E40AF; margin-top: 4px;">獨享版</div>
                    <div style="font-size: 0.75rem; color: #60A5FA;">系統隨機抽卡</div>
                </div>
                """, unsafe_allow_html=True)
                st.write("") # 間距
                # 這裡使用 primary type 讓獨享版看起來比較突出(或可自行調整)
                if st.button("選擇單人 👤", type="primary", key="btn_solo", use_container_width=True):
                    if name_input.strip():
                        st.session_state.user_name = name_input
                        st.session_state.game_mode = 'solo'
                        # 每局重抽保底位置：三次抽卡中隨機一次必為好牌
                        st.session_state.lucky_draw_round = random.randint(1, 3)
                        st.session_state.draw_count = 0
                        st.session_state.solo_pick = None
                        st.session_state.flip_pending = None
                        st.session_state.jump_pending = False
                        st.session_state.last_decade_report = None
                        st.session_state.stage = 'setup'
                        st.session_state.data_saved = False
                        st.rerun()
                    else:
                        st.warning("⚠️ 請輸入暱稱")

        # Footer
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
                "十年複利倍數": f"×{decade_multiplier(BASE_RATES[key]):.2f}",
                "每 10 萬變成": f"${int(100000 * decade_multiplier(BASE_RATES[key])):,}",
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
                "十年複利倍數": st.column_config.TextColumn("十年複利倍數", help="(1+年化報酬)^10，複利滾十年後會變成幾倍"),
                "每 10 萬變成": st.column_config.TextColumn("每 10 萬變成", help="放 10 萬進去，十年後在沒有事件衝擊下會變成多少"),
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
                config_dict = {k: v for k, v in zip(ASSET_KEYS, props)}
                st.session_state.config_history['Year 0'] = config_dict
                
                for i, key in enumerate(ASSET_KEYS):
                    st.session_state.assets[key] = initial_wealth * (props[i] / 100)
                
                record = {'Year': 0, 'Total': initial_wealth}
                record.update(st.session_state.assets)
                st.session_state.history.append(record)
                
                # 🔥 【加入這行】存下第 0 年狀態
                save_snapshot(st.session_state.user_name, 0, st.session_state.assets, config_dict)
                
                st.session_state.stage = 'playing'
                st.rerun()

# ==========================================
# 階段 2: 遊戲進行中 (Playing)
# ==========================================
elif st.session_state.stage == 'playing':
    total = sum(st.session_state.assets.values())
    roi = (total - st.session_state.history[0]['Total']) / st.session_state.history[0]['Total'] * 100
    
    # 🔥 修改處 1：建立一個儀表板的佔位符，把 Metric 都包進去
    metrics_placeholder = st.empty()
    
    with metrics_placeholder.container():
        # 這裡包著原本的儀表板代碼
        with st.container():
            c_year, c_wealth, c_roi = st.columns(3)
            c_year.metric("目前年份", f"第 {st.session_state.year} 年", delta=f"剩餘 {30-st.session_state.year} 年", delta_color="off")
            c_wealth.metric("總資產", f"${int(total):,}")
            c_roi.metric("累積報酬率", f"{roi:.1f}%", delta_color="normal")
            st.write("")
            st.progress(st.session_state.year / 30)

    current_year = st.session_state.year
    
# --- 1. 抽卡事件 ---
    if st.session_state.get('waiting_for_event', False):
        with st.container():
            # 1. 初始化局部狀態：是否已進入「輸入卡片代碼」階段
            # False = 還在看資產 (步驟一)
            # True  = 正在抽卡 (步驟二)
            if 'show_card_input' not in st.session_state:
                st.session_state.show_card_input = False

            # ==========================================
            # 🟢 步驟一：暴風雨前的寧靜 (只顯示資產)
            # ==========================================
            if not st.session_state.show_card_input:
                st.markdown(f"""<div style="text-align: center; margin-bottom: 20px;"><h2>🔔 第 {current_year} 年：資產檢視</h2></div>""", unsafe_allow_html=True)
                
                # 這裡顯示資產快照 (依您的需求，這時候才顯示)
                # 🔥 十年 IRR 貢獻明細：把「配置比例 × 年化報酬」直接換算成賺到的錢
                rpt = st.session_state.get('last_decade_report')
                if rpt:
                    st.markdown(f"#### 💹 第 {rpt['from_year']} → {rpt['to_year']} 年　各資產複利成長明細")
                    st.caption("這十年市場風平浪靜，純粹是「年化報酬率 × 複利十年」把你的錢變大。")

                    rows_html = ""
                    for k in ASSET_KEYS:
                        b, a = rpt['before'][k], rpt['after'][k]
                        rate = rpt['rates'][k]
                        mult = decade_multiplier(rate)
                        gain = a - b
                        color = FINANCE_COLORS[ASSET_NAMES[k]]
                        gain_color = '#10B981' if gain > 0 else ('#EF4444' if gain < 0 else '#6B7280')
                        bar_pct = min(100, (mult - 1) * 100 / 1.6) if mult > 1 else 0
                        rows_html += f"""
                        <tr>
                          <td style="padding:9px 8px; border-bottom:1px solid #F3F4F6;">
                            <span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:{color};margin-right:7px;"></span>
                            <b>{ASSET_NAMES[k]}</b>
                          </td>
                          <td style="padding:9px 8px; border-bottom:1px solid #F3F4F6; text-align:center; color:#374151;">
                            {rate*100:.0f}% / 年
                          </td>
                          <td style="padding:9px 8px; border-bottom:1px solid #F3F4F6; text-align:center;">
                            <b style="color:{color};">×{mult:.2f}</b>
                            <div style="height:4px;background:#F3F4F6;border-radius:99px;margin-top:4px;overflow:hidden;">
                              <div style="height:100%;width:{bar_pct:.0f}%;background:{color};"></div>
                            </div>
                          </td>
                          <td style="padding:9px 8px; border-bottom:1px solid #F3F4F6; text-align:right; color:#6B7280;">
                            ${int(b):,}
                          </td>
                          <td style="padding:9px 8px; border-bottom:1px solid #F3F4F6; text-align:right;">
                            <b>${int(a):,}</b>
                          </td>
                          <td style="padding:9px 8px; border-bottom:1px solid #F3F4F6; text-align:right; color:{gain_color}; font-weight:700;">
                            {'+' if gain >= 0 else '-'}${int(abs(gain)):,}
                          </td>
                        </tr>"""

                    tb, ta = sum(rpt['before'].values()), sum(rpt['after'].values())
                    st.markdown(f"""
                    <div style="overflow-x:auto;">
                    <table style="width:100%; border-collapse:collapse; background:#fff; border-radius:10px;
                                  font-size:14px; box-shadow:0 1px 3px rgba(0,0,0,.05);">
                      <thead>
                        <tr style="background:#F9FAFB; color:#6B7280; font-size:12px; text-align:left;">
                          <th style="padding:9px 8px;">資產</th>
                          <th style="padding:9px 8px; text-align:center;">年化報酬 (IRR)</th>
                          <th style="padding:9px 8px; text-align:center;">十年複利倍數</th>
                          <th style="padding:9px 8px; text-align:right;">十年前</th>
                          <th style="padding:9px 8px; text-align:right;">十年後</th>
                          <th style="padding:9px 8px; text-align:right;">賺到</th>
                        </tr>
                      </thead>
                      <tbody>{rows_html}</tbody>
                      <tfoot>
                        <tr style="background:#ECFDF5; font-weight:800; color:#065F46;">
                          <td style="padding:11px 8px;">合計</td>
                          <td></td><td></td>
                          <td style="padding:11px 8px; text-align:right;">${int(tb):,}</td>
                          <td style="padding:11px 8px; text-align:right;">${int(ta):,}</td>
                          <td style="padding:11px 8px; text-align:right;">+${int(ta-tb):,}</td>
                        </tr>
                      </tfoot>
                    </table>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown("---")

                render_asset_snapshot(st.session_state.assets, title="📊 請確認您的資產 (衝擊前)")
                
                st.write("")
                st.write("")
                
                # 下一步按鈕區域
                c_next1, c_next2, c_next3 = st.columns([1, 1, 1])
                with c_next2:
                    st.markdown("<div style='text-align: center; color: #6B7280; margin-bottom: 10px; font-size: 14px;'>確認目前資產無誤後，請進入命運環節...</div>", unsafe_allow_html=True)
                    # 按下按鈕後，切換狀態並重新整理頁面
                    if st.button("下一步：抽取命運卡 🎴", type="primary"):
                        st.session_state.show_card_input = True
                        st.rerun()

# ==========================================
            # 🔴 步驟二：輸入代碼與結算
            # ==========================================
            else:
                st.markdown(f"""<div style="text-align: center; margin-bottom: 20px;"><h2 style="color: #EF4444 !important;">⚡ 重大財經事件發生 (Year {current_year})</h2></div>""", unsafe_allow_html=True)
                
                # 確保變數存在
                if "event_card_input" not in st.session_state:
                    st.session_state.event_card_input = ""
                
                # 取得當前代碼 (如果有)
                current_input = st.session_state.get("event_card_input", "")
                clean_code = str(current_input).strip()
                
                # ----------------------------------------------------
                # 情況 A: 尚未抽卡 (Clean Code 為空) -> 顯示背面圖 + 操作區
                # ----------------------------------------------------
                if clean_code not in EVENT_CARDS:
                    # === 模式 A: 派對版 (背面圖 + 卡號輸入框) ===
                    if st.session_state.get('game_mode', 'party') == 'party':
                        _, cover_c, _ = st.columns([1, 1, 1])
                        with cover_c:
                            cover_img = "images/homepage.png"
                            if os.path.exists(cover_img):
                                st.image(cover_img, use_container_width=True)
                            else:
                                st.markdown("<div style='text-align: center; font-size: 80px;'>🎴</div>", unsafe_allow_html=True)

                        st.write("") # 增加一點間距

                        _, input_c, _ = st.columns([1, 2, 1]) # 置中縮窄
                        with input_c:
                            # key 綁定年份：避免上一輪輸入的卡號殘留，下一輪自動跳出結果
                            input_val = st.text_input(
                                "請輸入實體卡片代碼 (3碼)",
                                placeholder="例如: 101",
                                key=f"event_card_input_widget_{current_year}"
                            )
                            input_code = str(input_val).strip()
                            if input_code:
                                if input_code in EVENT_CARDS:
                                    st.session_state.event_card_input = input_code
                                    st.rerun() # 輸入後立即重整以顯示結果
                                else:
                                    st.error("❌ 查無此卡號，請確認實體卡片代碼 (101 ~ 112)")

                    # === 模式 B: 獨享版 (命運三選一) ===
                    else:
                        # 防呆：管理員直接跳轉進來時，補上保底機制狀態
                        if 'lucky_draw_round' not in st.session_state:
                            st.session_state.lucky_draw_round = random.randint(1, 3)
                        if 'draw_count' not in st.session_state:
                            st.session_state.draw_count = 0

                        back_uri = img_uri("images/homepage.png", 460)
                        pending = st.session_state.get('flip_pending')

                        # --------------------------------------------------
                        # 🎬 已選牌 -> 播放「真・3D 翻牌」動畫 (純前端 CSS)
                        # --------------------------------------------------
                        if pending:
                            autoplay_audio("sound_effect.aac")
                            front_uri = img_uri(f"images/{pending['card']}.png", 800)
                            flip_html = f"""
                            <style>
                              .flip-stage {{
                                display:flex; flex-direction:column; align-items:center;
                                justify-content:center; padding:10px 0;
                                font-family:'Inter','Noto Sans TC',sans-serif;
                              }}
                              .flip-label {{
                                color:#6B7280; font-size:15px; margin-bottom:14px; font-weight:600;
                                animation: labelSwap 1.8s ease forwards;
                              }}
                              @keyframes labelSwap {{
                                0%,60% {{ opacity:1; }} 75% {{ opacity:0; }} 100% {{ opacity:0; }}
                              }}
                              .flip-scene {{ width:min(440px,90vw); aspect-ratio:764/510; perspective:1400px; }}
                              .flip-card {{
                                position:relative; width:100%; height:100%;
                                transform-style:preserve-3d;
                                animation: spinFlip 1.6s cubic-bezier(.28,.72,.30,1) forwards;
                              }}
                              @keyframes spinFlip {{
                                0%   {{ transform: rotateY(0deg)   scale(.94); }}
                                55%  {{ transform: rotateY(520deg) scale(1.06); }}
                                100% {{ transform: rotateY(900deg) scale(1); }}
                              }}
                              .flip-face {{
                                position:absolute; inset:0; backface-visibility:hidden;
                                border-radius:14px; overflow:hidden;
                                box-shadow:0 14px 34px rgba(0,0,0,.28);
                                background:#fff;
                              }}
                              .flip-face img {{ width:100%; height:100%; object-fit:cover; display:block; }}
                              .flip-front {{ transform: rotateY(180deg); }}
                              .flip-glow {{
                                position:absolute; inset:-6px; border-radius:18px; pointer-events:none;
                                box-shadow:0 0 0 0 rgba(37,99,235,0);
                                animation: glowHit 0.7s ease-out 1.5s forwards;
                              }}
                              @keyframes glowHit {{
                                0%   {{ box-shadow:0 0 0 0 rgba(37,99,235,.55); }}
                                100% {{ box-shadow:0 0 34px 12px rgba(37,99,235,0); }}
                              }}
                            </style>
                            <div class="flip-stage">
                              <div class="flip-label">🎴 正在翻開命運卡 {pending['picked']}...</div>
                              <div class="flip-scene">
                                <div class="flip-card">
                                  <div class="flip-face flip-back"><img src="{back_uri}"></div>
                                  <div class="flip-face flip-front"><img src="{front_uri}"></div>
                                  <div class="flip-glow"></div>
                                </div>
                              </div>
                            </div>
                            """
                            components.html(hide_stale_js(2800) + flip_html, height=380)
                            # 動畫在瀏覽器端播放，伺服器只等它跑完 (不再逐格推送畫面)
                            time.sleep(2.3)
                            st.session_state.event_card_input = pending['card']
                            st.session_state.flip_pending = None
                            st.rerun()

                        # --------------------------------------------------
                        # 🎴 尚未選牌 -> 顯示三張「整張可點」的卡片
                        # --------------------------------------------------
                        st.markdown(f"""
                        <style>
                          div[class*="st-key-cardslot_"] div.stButton > button {{
                            height: 210px;
                            border-radius: 14px;
                            border: 2px solid #E5E7EB;
                            background-image: url("{back_uri}");
                            background-size: cover;
                            background-position: center;
                            box-shadow: 0 6px 16px rgba(0,0,0,.12);
                            transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
                            font-size: 0 !important;
                            padding: 0 !important;
                          }}
                          div[class*="st-key-cardslot_"] div.stButton > button:hover {{
                            transform: translateY(-10px) scale(1.03);
                            box-shadow: 0 16px 32px rgba(37,99,235,.32);
                            border-color: #2563EB;
                          }}
                          div[class*="st-key-cardslot_"] div.stButton > button:active {{
                            transform: translateY(-4px) scale(.99);
                          }}
                          .card-pos-label {{
                            text-align:center; font-weight:700; color:#4B5563;
                            margin-top:8px; font-size:15px; letter-spacing:1px;
                          }}
                        </style>
                        <div style='text-align: center; margin-bottom: 16px;'>
                            <div style='font-size: 1.15rem; font-weight: 700; color: #1E40AF;'>🔮 命運三選一</div>
                            <div style='color: #6B7280; font-size: 0.9rem; margin-top: 4px;'>憑直覺選一張吧！</div>
                        </div>
                        """, unsafe_allow_html=True)

                        picked_pos = None
                        card_cols = st.columns(3, gap="large")
                        for idx, pos in enumerate(['A', 'B', 'C']):
                            with card_cols[idx]:
                                with st.container(key=f"cardslot_{pos}_{current_year}"):
                                    if st.button(pos, use_container_width=True,
                                                 key=f"pick_{pos}_{current_year}"):
                                        picked_pos = pos
                                st.markdown(f"<div class='card-pos-label'>{pos}</div>",
                                            unsafe_allow_html=True)

                        if picked_pos:
                            # 🔥 保底機制：整局三次抽卡，恰好一次落在好牌池
                            # 玩家選 A/B/C 只是儀式感，實際結果由後台機率決定
                            st.session_state.draw_count += 1
                            if st.session_state.draw_count == st.session_state.lucky_draw_round:
                                final_card_id = random.choice(GOOD_CARDS)
                            else:
                                final_card_id = random.choice(BAD_CARDS)

                            # 另外兩張的翻牌結果：抽到壞牌時，未選的兩張必有一張好牌「擦肩而過」；
                            # 抽到好牌時，另外兩張都是壞牌，讓玩家覺得直覺神準
                            other_pos = [p for p in ['A', 'B', 'C'] if p != picked_pos]
                            bad_others = random.sample([c for c in BAD_CARDS if c != final_card_id], 2)
                            if final_card_id in GOOD_CARDS:
                                other_cards = bad_others
                            else:
                                other_cards = [random.choice(GOOD_CARDS), bad_others[0]]
                                random.shuffle(other_cards)
                            st.session_state.solo_pick = {
                                'picked': picked_pos,
                                'others': list(zip(other_pos, other_cards))
                            }
                            st.session_state.flip_pending = {'picked': picked_pos, 'card': final_card_id}
                            st.rerun()

                # 情況 B: 已有卡片代碼 -> 顯示結果與結算
                # ----------------------------------------------------
                else:
                    card_data = EVENT_CARDS[clean_code]
                    image_path = f"images/{clean_code}.png"
                    
                    # 顯示卡片結果區 (維持原樣)
                    col_img, col_desc = st.columns([1, 2])
                    with col_img:
                        if os.path.exists(image_path): st.image(image_path, use_container_width=True)
                        else: st.info(f"Card: {clean_code}")
                    with col_desc:
                        st.markdown(f"""<div style="background: #F0F9FF; border-left: 4px solid #3B82F6; padding: 16px; border-radius: 4px; height: 100%;"><h3 style="margin-top: 0; color: #1E40AF !important;">{card_data['name']}</h3><p style="font-size: 1.1rem; color: #374151;">{card_data['desc']}</p></div>""", unsafe_allow_html=True)
                    
                    st.write("")
                    st.write("#### 📊 市場衝擊預覽 (預估損益)")
                    
                    # 顯示損益方塊 (維持原樣)
                    cols = st.columns(5)
                    key_map = {'dividend': 'Dividend', 'bond': 'USBond', 'stock': 'TWStock', 'cash': 'Cash', 'crypto': 'Crypto'}
                    metrics = [('分紅收益', 'dividend'), ('美債', 'bond'), ('台股', 'stock'), ('現金', 'cash'), ('加密幣', 'crypto')]
                    
                    for i, (name, card_key) in enumerate(metrics):
                        asset_key = key_map[card_key]
                        pct_change = card_data[card_key]
                        current_val = st.session_state.assets[asset_key]
                        impact_val = current_val * (pct_change / 100)
                        
                        color = '#EF4444' if pct_change < 0 else ('#10B981' if pct_change > 0 else '#6B7280')
                        arrow = '▼' if pct_change < 0 else ('▲' if pct_change > 0 else '-')
                        sign = '' if pct_change < 0 else ('+' if pct_change > 0 else '')
                        bg_color = '#FEF2F2' if pct_change < 0 else '#ECFDF5'
                        
                        cols[i].markdown(f"""
                        <div style="text-align: center; background: #fff; padding: 12px 5px; border-radius: 8px; border: 1px solid #E5E7EB; height: 100%;">
                            <div style="color: #6B7280; font-size: 13px; margin-bottom: 2px;">{name}</div>
                            <div style="color: #1F2937; font-size: 14px; font-weight: 600; border-bottom: 1px dashed #E5E7EB; padding-bottom: 4px; margin-bottom: 4px;">現: ${int(current_val):,}</div>
                            <div style="color: {color}; font-size: 18px; font-weight: bold; line-height: 1.2;">{arrow} {abs(pct_change)}%</div>
                            <div style="color: {color}; font-size: 13px; font-weight: 600; margin-top: 4px; background-color: {bg_color}; padding: 2px 4px; border-radius: 4px;">{sign}${int(impact_val):,}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    # 🃏 獨享版：翻開另外兩張未選的牌 (三選一的戲劇感結尾)
                    solo_pick = st.session_state.get('solo_pick')
                    if st.session_state.get('game_mode') == 'solo' and solo_pick and solo_pick.get('others'):
                        st.write("")
                        others_html = ""
                        missed_good = False
                        for pos, cid in solo_pick['others']:
                            other_card = EVENT_CARDS[cid]
                            is_good = cid in GOOD_CARDS
                            if is_good: missed_good = True
                            chip_color = '#10B981' if is_good else '#EF4444'
                            chip_bg = '#ECFDF5' if is_good else '#FEF2F2'
                            chip_text = '📈 上漲行情' if is_good else '📉 下跌行情'
                            others_html += f"""
                            <div style="flex: 1; background: white; border: 1px solid #E5E7EB; border-radius: 8px; padding: 12px; text-align: center;">
                                <div style="color: #6B7280; font-size: 12px;">你沒選的 {pos}</div>
                                <div style="color: #1F2937; font-weight: 700; margin: 4px 0;">{other_card['name']}</div>
                                <div style="display: inline-block; color: {chip_color}; background: {chip_bg}; font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 999px;">{chip_text}</div>
                            </div>"""
                        tease_text = "😱 上漲行情就在隔壁，與你擦肩而過..." if missed_good else "🎯 你的直覺太神了！另外兩張都是災難！"
                        st.markdown(f"""
                        <div style="background: #F9FAFB; border: 1px dashed #D1D5DB; border-radius: 12px; padding: 16px;">
                            <div style="text-align: center; color: #4B5563; font-weight: 700; margin-bottom: 10px;">🃏 翻開另外兩張命運卡</div>
                            <div style="display: flex; gap: 12px;">{others_html}</div>
                            <div style="text-align: center; color: #6B7280; font-size: 13px; margin-top: 10px;">{tease_text}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    st.write("")
                    # 結算按鈕 (維持原樣)
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
                        st.session_state.show_card_input = False
                        st.session_state.event_card_input = ""
                        st.session_state.solo_pick = None
                        
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
            
            # 🔥 讓玩家在「做決定的當下」就看到各資產的十年複利威力
            st.markdown("##### 📐 接下來十年，每 $1 會變成多少？")
            rate_cols = st.columns(5)
            for i, k in enumerate(ASSET_KEYS):
                r = st.session_state.dynamic_rates[k]
                mult = decade_multiplier(r)
                color = FINANCE_COLORS[ASSET_NAMES[k]]
                rate_cols[i].markdown(f"""
                <div style="text-align:center; background:#fff; border:1px solid #E5E7EB;
                            border-top:3px solid {color}; border-radius:8px; padding:8px 4px;">
                  <div style="font-size:12px; color:#6B7280;">{ASSET_NAMES[k]}</div>
                  <div style="font-size:13px; color:#374151; font-weight:600;">{r*100:.0f}% / 年</div>
                  <div style="font-size:20px; font-weight:800; color:{color}; line-height:1.2;">×{mult:.2f}</div>
                  <div style="font-size:11px; color:#9CA3AF;">複利 10 年</div>
                </div>
                """, unsafe_allow_html=True)
            st.caption("⚠️ 這是「沒有事件衝擊」下的理論值；命運卡會大幅改寫結果。")
            st.write("")

            st.write("請調整下方比例 (預設為當前資產比例)：")
            
            c1, c2, c3, c4, c5 = st.columns(5)
            # 這裡的 input 改為 float 模式 (0.0 - 100.0)
            rb1 = c1.number_input(f"{ASSET_NAMES['Dividend']}", 0.0, 100.0, current_pcts['Dividend'], step=1.0, format="%.1f", key=f"rb1_{current_year}")
            rb2 = c2.number_input(f"{ASSET_NAMES['USBond']}", 0.0, 100.0, current_pcts['USBond'], step=1.0, format="%.1f", key=f"rb2_{current_year}")
            rb3 = c3.number_input(f"{ASSET_NAMES['TWStock']}", 0.0, 100.0, current_pcts['TWStock'], step=1.0, format="%.1f", key=f"rb3_{current_year}")
            rb4 = c4.number_input(f"{ASSET_NAMES['Cash']}", 0.0, 100.0, current_pcts['Cash'], step=1.0, format="%.1f", key=f"rb4_{current_year}")
            rb5 = c5.number_input(f"{ASSET_NAMES['Crypto']}", 0.0, 100.0, current_pcts['Crypto'], step=1.0, format="%.1f", key=f"rb5_{current_year}")
            
            # ... (上面是 rb1 ~ rb5 的 number_input 代碼) ...

            # 🔥 修正開始：先加總，然後強制四捨五入到小數點第 1 位
            raw_sum = rb1 + rb2 + rb3 + rb4 + rb5
            total_rb = round(raw_sum, 1)
            
            # 顯示即時計算結果，讓玩家知道現在是多少
            if total_rb == 100.0:
                st.success(f"✅ 目前總和: {total_rb}% (完美)")
            else:
                diff = round(100.0 - total_rb, 1)
                st.error(f"⚠️ 目前總和: {total_rb}% (還差 {diff:+.1f}%)")

            # 判斷邏輯：只要不等於 100.0 就擋住
            if total_rb != 100.0: 
                st.warning("請調整比例直到總和為 100% 才能繼續。")
            else:
                st.write("")
                if st.button("執行配置 ✅", type="primary"):
                    # 再次確認比例總和為 100 (或是自動歸一化，但在這裡我們信任 input)
                    props = [rb1, rb2, rb3, rb4, rb5]
                    
                    st.session_state.config_history[f'Year {current_year}'] = {k: v for k, v in zip(ASSET_KEYS, props)}
                    
                    # 更新資產數值
                    for i, key in enumerate(ASSET_KEYS):
                        st.session_state.assets[key] = current_total * (props[i] / 100)
                    
                    # 更新歷史紀錄
                    last_rec = st.session_state.history[-1]
                    last_rec.update(st.session_state.assets)
                    
                    st.session_state.waiting_for_rebalance = False
                    st.rerun()

# --- 3. 推進時間軸 ---
    elif current_year < 30:
        run_simulation = st.session_state.get('jump_pending', False)

        # 尚未啟動時光機 -> 顯示快照與按鈕
        if not run_simulation:
            with st.container():
                st.markdown(f"### ⏩ 推進時間軸: 第 {current_year+1} - {current_year+10} 年")

                if current_year == 0:
                    render_asset_snapshot(st.session_state.assets, title="📊 第 0 年初始配置確認")
                    st.write("")

                if current_year == 0:
                    c_back, c_run = st.columns([1, 4])
                    with c_back:
                        if st.button("⬅️ 返回重設"):
                            st.session_state.stage = 'setup'
                            st.session_state.history = []
                            st.rerun()
                    with c_run:
                        if st.button(f"🚀 啟動時光機 (前往第 {current_year+10} 年)", type="primary"):
                            st.session_state.jump_pending = True
                            st.rerun()  # 先重整，讓轉場動畫在乾淨的畫面上播放
                else:
                    if st.button(f"🚀 前往下一個十年 (Year {current_year+10})", type="primary"):
                        st.session_state.jump_pending = True
                        st.rerun()

        # --- ⏳ 轉場動畫與計算邏輯 (獨佔畫面) ---
        else:
            if True:
                # 動畫開始時，把上方年份/資產儀表板一起清掉
                metrics_placeholder.empty()

                transition_placeholder = st.empty()

                # 1. 決定過場圖片與標語
                if current_year == 0:
                    jump_img = "images/wait1.png"
                    jump_text = "🚀 3, 2, 1... 投資旅程正式展開！"
                elif current_year == 10:
                    jump_img = "images/wait2.png"
                    jump_text = "📈 十年過去了，市場風雲變色..."
                else:
                    jump_img = "images/wait3.png"
                    jump_text = "🏁 最後衝刺！迎向財富自由的終點！"

                # 2. 先算完十年複利 (才能把真實數字餵給前端動畫)
                before_assets = dict(st.session_state.assets)
                rates = st.session_state.dynamic_rates

                for y in range(1, 11):
                    for k in ASSET_KEYS:
                        st.session_state.assets[k] *= (1 + rates[k])
                    record = {'Year': current_year + y, 'Total': sum(st.session_state.assets.values())}
                    record.update(st.session_state.assets)
                    st.session_state.history.append(record)

                after_assets = dict(st.session_state.assets)

                # 3. 🔥 逐年資產跳動計數器 (純前端動畫，伺服器不再逐格推送畫面)
                anim_assets = [{
                    'name': ASSET_NAMES[k],
                    'color': FINANCE_COLORS[ASSET_NAMES[k]],
                    'rate': rates[k] * 100,
                    'from': before_assets[k],
                    'to': after_assets[k],
                } for k in ASSET_KEYS]

                anim_cfg = json.dumps({
                    'y0': current_year + 1,
                    'y1': current_year + 10,
                    'fromTotal': sum(before_assets.values()),
                    'toTotal': sum(after_assets.values()),
                    'assets': anim_assets,
                }, ensure_ascii=False)

                jump_uri = img_uri(jump_img, 480)
                img_tag = (f'<img class="jump-art" src="{jump_uri}">'
                           if jump_uri else '<div style="font-size:64px;margin:16px 0;">⏳ ➡️ 💰</div>')

                anim_html = f"""
                <style>
                  .tm-wrap {{
                    font-family:'Inter','Noto Sans TC',sans-serif; text-align:center;
                    padding:6px 0; color:#1F2937;
                  }}
                  .tm-title {{ font-size:1.35rem; font-weight:800; color:#2563EB; margin-bottom:10px; }}
                  .tm-year {{
                    display:inline-block; background:#EFF6FF; color:#1E40AF; border:1px solid #BFDBFE;
                    border-radius:999px; padding:4px 18px; font-size:1.05rem; font-weight:700;
                    letter-spacing:1px; margin-bottom:6px;
                  }}
                  .tm-total {{
                    font-size:2.9rem; font-weight:800; color:#111827;
                    font-variant-numeric:tabular-nums; line-height:1.15; margin:2px 0 2px 0;
                  }}
                  .tm-gain {{ font-size:1rem; font-weight:700; color:#10B981; margin-bottom:10px; }}
                  .jump-art {{ max-height:190px; border-radius:12px; margin:4px 0 12px 0; }}
                  .tm-bars {{
                    display:flex; gap:8px; justify-content:center; flex-wrap:wrap;
                    max-width:820px; margin:0 auto;
                  }}
                  .tm-chip {{
                    flex:1 1 140px; background:#fff; border:1px solid #E5E7EB; border-radius:10px;
                    padding:8px 6px; box-shadow:0 1px 3px rgba(0,0,0,.05);
                  }}
                  .tm-chip .nm {{ font-size:12px; color:#6B7280; }}
                  .tm-chip .rt {{
                    display:inline-block; font-size:11px; font-weight:700; color:#fff;
                    border-radius:999px; padding:1px 8px; margin:3px 0;
                  }}
                  .tm-chip .vl {{
                    font-size:15px; font-weight:700; color:#1F2937; font-variant-numeric:tabular-nums;
                  }}
                  .tm-track {{
                    height:6px; background:#E5E7EB; border-radius:99px; overflow:hidden;
                    max-width:520px; margin:12px auto 0 auto;
                  }}
                  .tm-fill {{ height:100%; width:0%; background:linear-gradient(90deg,#2563EB,#1E40AF); }}
                </style>
                <div class="tm-wrap">
                  <div class="tm-title">{jump_text}</div>
                  <div class="tm-year" id="tmYear">第 0 年</div>
                  <div class="tm-total" id="tmTotal">$0</div>
                  <div class="tm-gain" id="tmGain">&nbsp;</div>
                  {img_tag}
                  <div class="tm-bars" id="tmBars"></div>
                  <div class="tm-track"><div class="tm-fill" id="tmFill"></div></div>
                </div>
                <script>
                  const CFG = {anim_cfg};
                  const fmt = n => '$' + Math.round(n).toLocaleString('en-US');
                  const bars = document.getElementById('tmBars');
                  CFG.assets.forEach((a, i) => {{
                    const d = document.createElement('div');
                    d.className = 'tm-chip';
                    d.innerHTML = '<div class="nm">' + a.name + '</div>' +
                      '<div class="rt" style="background:' + a.color + '">' +
                      (a.rate >= 0 ? '+' : '') + a.rate.toFixed(0) + '% / 年</div>' +
                      '<div class="vl" id="chip' + i + '">' + fmt(a.from) + '</div>';
                    bars.appendChild(d);
                  }});
                  const DUR = 3000, t0 = performance.now();
                  // 依「複利曲線」內插，數字增長會越跑越快 —— 這就是複利的感覺
                  const geo = (a, b, p) => (a <= 0 ? b * p : a * Math.pow(b / a, p));
                  function frame(now) {{
                    const p = Math.min((now - t0) / DUR, 1);
                    const yr = Math.min(CFG.y1, CFG.y0 + Math.floor(p * (CFG.y1 - CFG.y0 + 1)));
                    document.getElementById('tmYear').textContent = '第 ' + yr + ' 年';
                    const tot = geo(CFG.fromTotal, CFG.toTotal, p);
                    document.getElementById('tmTotal').textContent = fmt(tot);
                    const gain = tot - CFG.fromTotal;
                    document.getElementById('tmGain').textContent =
                      (gain >= 0 ? '▲ +' : '▼ ') + fmt(Math.abs(gain)).replace('$', '$') + ' (複利累積中)';
                    CFG.assets.forEach((a, i) => {{
                      document.getElementById('chip' + i).textContent = fmt(geo(a.from, a.to, p));
                    }});
                    document.getElementById('tmFill').style.width = (p * 100) + '%';
                    if (p < 1) requestAnimationFrame(frame);
                  }}
                  requestAnimationFrame(frame);
                </script>
                """

                with transition_placeholder.container():
                    components.html(hide_stale_js(4000) + anim_html, height=560)
                    time.sleep(3.4)  # 等前端動畫播完 (期間不佔用運算資源)

                # 4. 收尾：推進年份、存快照、留下十年成長報告供下一頁顯示
                st.session_state.year += 10

                st.session_state.last_decade_report = {
                    'from_year': current_year,
                    'to_year': st.session_state.year,
                    'before': before_assets,
                    'after': after_assets,
                    'rates': dict(rates),
                }

                last_config_year = f"Year {current_year}"
                current_config = st.session_state.config_history.get(last_config_year, {})
                save_snapshot(st.session_state.user_name, st.session_state.year, st.session_state.assets, current_config)

                st.session_state.waiting_for_event = True
                st.session_state.jump_pending = False

                transition_placeholder.empty()
                st.rerun()
    # 🔥 記得移除原本放在最下面的 render_asset_snapshot 呼叫（因為已經搬到上面了）
    # if len(st.session_state.history) > 0 and current_year == 0: ... (這段請刪除或確保不會重複出現)


# ==========================================
# 階段 3: Finished
# ==========================================
elif st.session_state.stage == 'finished':
    # 🔥 【加入這段】確保第 30 年只存一次
    if 'final_snapshot_saved' not in st.session_state:
        final_config = st.session_state.config_history.get('Year 20', {})
        save_snapshot(st.session_state.user_name, 30, st.session_state.assets, final_config)
        st.session_state.final_snapshot_saved = True

    st.balloons()
    # ... (後面接原本的顯示邏輯)
    final_wealth = sum(st.session_state.assets.values())
    roi = (final_wealth - st.session_state.history[0]['Total']) / st.session_state.history[0]['Total'] * 100
    
 # --- 🏆 30年最終分級 (修正版) ---
    # 門檻對照 (與下方程式碼一致)：
    # <0 破產俱樂部 | <200 佛系定存族 | <300 佛系理財族 | <400 理財小白
    # <600 理財老手 | <800 投資理財老鳥 | <1200 自由財富號 | >=1200 投資界的神

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
