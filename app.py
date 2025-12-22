import streamlit as st
import pandas as pd
import numpy as np
import os
import csv
from datetime import datetime
import plotly.express as px

# ==========================================
# ⚙️ 後台設定區 (Host Control)
# ==========================================
BASE_RATES = {
    'Dividend': 0.05, 'USBond': 0.04, 'TWStock': 0.08, 'Cash': 0.01, 'Crypto': 0.15
}

# 🔥 已根據表格更新事件卡數據
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

# --- 1. 頁面設定 ---
st.set_page_config(page_title="Flip Your Destiny - IFRC Edition", page_icon="🏦", layout="wide")

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
    
    /* 1. 一般按鈕 (白色底，深色字) */
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

    /* 2. Primary 按鈕 (藍色底) - 設定背景 */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--primary), var(--primary-dark)) !important;
        border: none !important;
        box-shadow: 0 4px 6px rgba(37, 99, 235, 0.2);
    }

    /* 🔥 3. 強力覆蓋：Primary 按鈕內的文字顏色 🔥 */
    div.stButton > button[kind="primary"],
    div.stButton > button[kind="primary"] > div,
    div.stButton > button[kind="primary"] p {
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
    }

    /* 4. Hover 狀態修正 */
    div.stButton > button[kind="primary"]:hover {
        box-shadow: 0 6px 10px rgba(37, 99, 235, 0.3) !important;
    }
    div.stButton > button[kind="primary"]:hover,
    div.stButton > button[kind="primary"]:hover > div,
    div.stButton > button[kind="primary"]:hover p {
        color: #FFFFFF !important;
    }
    
    /* 5. Focus/Active 狀態修正 */
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
ASSET_NAMES = {'Dividend': '高股息', 'USBond': '美債', 'TWStock': '台股', 'Cash': '現金', 'Crypto': '加密幣'}
FINANCE_COLORS = {'高股息': '#F59E0B', '美債': '#3B82F6', '台股': '#EF4444', '現金': '#9CA3AF', '加密幣': '#8B5CF6'}

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
            annotations=[dict(text='資產分佈', x=0.5, y=0.5, font_size=14, showarrow=False)]
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

with st.sidebar:
    st.markdown("### ⚙️ 管理員後台")
    if not st.session_state.admin_unlocked:
        st.info("🔒 需要管理員權限")
        pwd_input = st.text_input("輸入密碼", type="password", key="admin_pwd_input")
        if pwd_input == ADMIN_PASSWORD:
            st.session_state.admin_unlocked = True
            st.rerun()
    else:
        st.success("✅ 系統已解鎖")
        if os.path.exists(CSV_FILE):
            df_record = pd.read_csv(CSV_FILE)
            st.write(f"📊 總筆數: {len(df_record)}")
            with open(CSV_FILE, "rb") as file:
                st.download_button(label="📥 下載數據 CSV", data=file, file_name="game_results.csv", mime="text/csv")
        st.markdown("---")
        if st.button("🔒 鎖定系統"):
            st.session_state.admin_unlocked = False
            st.rerun()

# --- 標題 ---
st.markdown("""
    <div style="text-align: center; padding: 20px 0 40px 0;">
        <h1 style="font-size: 2.5rem; letter-spacing: -0.5px;">💰 翻轉命運 30 年</h1>
        <div style="color: #6B7280; font-size: 1.2rem; font-weight: 500;">Wealth Management Simulation</div>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 階段 0: 登入 (Login) 🔥 修改處：更新參數名稱
# ==========================================
if st.session_state.stage == 'login':
    with st.container():
        # 1. 歡迎文字
        st.markdown("<div style='text-align: center; margin-bottom: 10px;'>👋 歡迎來到資產模擬挑戰</div>", unsafe_allow_html=True)
        
        # 2. 圖片區 (使用 Columns 讓圖片置中且控制大小)
        # [1, 2, 1] 的比例意思是：左邊空1份、中間放圖佔2份、右邊空1份
        img_c1, img_c2, img_c3 = st.columns([1, 0.8, 1])
        
        with img_c2:
            image_path = "images/homepage.png"
            if os.path.exists(image_path):
                # 🔥 這裡改成 use_container_width=True
                st.image(image_path, use_container_width=True) 
            else:
                st.info("📷 圖片讀取中...")

        # 3. 輸入框與按鈕區
        st.markdown("<div style='text-align: center; color: #6B7280; font-size: 0.9rem; margin-bottom: 20px;'>扭轉命運的機會就在眼前，準備好了嗎？</div>", unsafe_allow_html=True)
        
        # 為了讓輸入框也不要太長，我們也稍微限縮一下寬度
        input_c1, input_c2, input_c3 = st.columns([1, 2, 1])
        with input_c2:
            name_input = st.text_input("請輸入玩家暱稱", placeholder="例如: 小明", key="login_name")
            st.write("") # 空行
            
            # 按鈕 (白字藍底)
            if st.button("▶ 確認並開始", type="primary"):
                if name_input.strip():
                    st.session_state.user_name = name_input
                    st.session_state.stage = 'setup'
                    st.session_state.data_saved = False
                    st.rerun()
                else:
                    st.warning("⚠️ 請輸入暱稱以開始遊戲")
# ==========================================
# 階段 1: Setup
# ==========================================
elif st.session_state.stage == 'setup':
    with st.container():
        st.markdown(f"### 🚀 初始資產配置 (玩家: {st.session_state.user_name})")
        col_cap, col_space = st.columns([1, 2])
        with col_cap:
            initial_wealth = st.number_input("💰 起始資金", value=1000000, step=100000, format="%d")
        
        st.markdown("---")
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
            if st.button("確認並開始 ✅", type="primary"):
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
    
    # --- 1. 抽卡事件 ---
    if st.session_state.get('waiting_for_event', False):
        with st.container():
            st.markdown(f"""<div style="text-align: center; margin-bottom: 20px;"><h2 style="color: #EF4444 !important;">⚡ 重大財經事件發生 (Year {current_year})</h2></div>""", unsafe_allow_html=True)
            
            render_asset_snapshot(st.session_state.assets, title="📊 衝擊前資產快照")
            st.markdown("---")
            
            col_input, col_status = st.columns([2, 1])
            input_code = col_input.text_input("請輸入事件卡代碼", placeholder="例如: 101", label_visibility="collapsed")
            clean_code = str(input_code).strip()
            
            if clean_code in EVENT_CARDS:
                card_data = EVENT_CARDS[clean_code]
                image_path = f"images/{clean_code}.png"
                col_img, col_desc = st.columns([2, 3])
                with col_img:
                    if os.path.exists(image_path): st.image(image_path, use_container_width=True)
                    else: st.info("📷 No Image")
                with col_desc:
                    st.markdown(f"""<div style="background: #F0F9FF; border-left: 4px solid #3B82F6; padding: 16px; border-radius: 4px; height: 100%;"><h3 style="margin-top: 0; color: #1E40AF !important;">{card_data['name']}</h3><p style="font-size: 1.1rem; color: #374151;">{card_data['desc']}</p></div>""", unsafe_allow_html=True)
                
                st.write("")
                st.write("#### 📊 市場衝擊預覽 (預估損益)")
                cols = st.columns(5)
                key_map = {'dividend': 'Dividend', 'bond': 'USBond', 'stock': 'TWStock', 'cash': 'Cash', 'crypto': 'Crypto'}
                metrics = [('高股息', 'dividend'), ('美債', 'bond'), ('台股', 'stock'), ('現金', 'cash'), ('加密幣', 'crypto')]
                
                for i, (name, card_key) in enumerate(metrics):
                    asset_key = key_map[card_key]
                    pct_change = card_data[card_key]
                    current_val = st.session_state.assets[asset_key]
                    impact_val = current_val * (pct_change / 100)
                    color = '#EF4444' if pct_change < 0 else ('#10B981' if pct_change > 0 else '#6B7280')
                    arrow = '▼' if pct_change < 0 else ('▲' if pct_change > 0 else '-')
                    sign = '' if pct_change < 0 else ('+' if pct_change > 0 else '')
                    
                    cols[i].markdown(f"""<div style="text-align: center; background: #fff; padding: 12px 5px; border-radius: 8px; border: 1px solid #E5E7EB; height: 100%;"><div style="color: #6B7280; font-size: 13px; margin-bottom: 4px;">{name}</div><div style="color: {color}; font-size: 20px; font-weight: bold; line-height: 1;">{arrow} {abs(pct_change)}%</div><div style="color: {color}; font-size: 14px; font-weight: 600; margin-top: 6px; background-color: {'#FEF2F2' if pct_change < 0 else '#ECFDF5'}; padding: 2px 4px; border-radius: 4px;">{sign}${int(impact_val):,}</div></div>""", unsafe_allow_html=True)

                st.write("")
                if st.button("接受市場波動 📉", type="primary"):
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
            
            c1, c2, c3, c4, c5 = st.columns(5)
            rb1 = c1.number_input(f"{ASSET_NAMES['Dividend']}", 0, 100, 20, key=f"rb1_{current_year}")
            rb2 = c2.number_input(f"{ASSET_NAMES['USBond']}", 0, 100, 20, key=f"rb2_{current_year}")
            rb3 = c3.number_input(f"{ASSET_NAMES['TWStock']}", 0, 100, 20, key=f"rb3_{current_year}")
            rb4 = c4.number_input(f"{ASSET_NAMES['Cash']}", 0, 100, 20, key=f"rb4_{current_year}")
            rb5 = c5.number_input(f"{ASSET_NAMES['Crypto']}", 0, 100, 20, key=f"rb5_{current_year}")
            
            total_rb = rb1 + rb2 + rb3 + rb4 + rb5
            if total_rb != 100: st.warning(f"⚠️ 比例總和錯誤: {total_rb}%")
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
            
            run_simulation = False
            
            if current_year == 0:
                c_back, c_run = st.columns([1, 4])
                with c_back:
                    if st.button("⬅️ 返回重設"):
                        st.session_state.stage = 'setup'
                        st.session_state.history = [] 
                        st.rerun()
                with c_run:
                    if st.button(f"執行 10 年資產模擬 ▶", type="primary"):
                        run_simulation = True
            else:
                if st.button(f"執行 10 年資產模擬 ▶", type="primary"):
                    run_simulation = True
            
            if run_simulation:
                for y in range(1, 11):
                    st.session_state.assets['Dividend'] *= (1 + BASE_RATES['Dividend']) * np.random.uniform(0.98, 1.02)
                    st.session_state.assets['USBond']   *= (1 + BASE_RATES['USBond']) * np.random.uniform(0.95, 1.05)
                    st.session_state.assets['TWStock']  *= (1 + BASE_RATES['TWStock']) * np.random.uniform(0.9, 1.1)
                    st.session_state.assets['Cash']     *= (1 + BASE_RATES['Cash'])
                    st.session_state.assets['Crypto']   *= (1 + BASE_RATES['Crypto']) * np.random.uniform(0.8, 1.2)
                    record = {'Year': current_year + y, 'Total': sum(st.session_state.assets.values())}
                    record.update(st.session_state.assets)
                    st.session_state.history.append(record)
                st.session_state.year += 10
                st.session_state.waiting_for_event = True
                st.rerun()

    # --- 圖表區 (堆疊面積圖) ---
    st.markdown("---")
    if len(st.session_state.history) > 0:
        with st.container():
            # 🔥 Year 0 特殊佈局: 資產快照放在最上面
            if current_year == 0:
                render_asset_snapshot(st.session_state.assets, title="📊 當前資產配置")
                st.markdown("---")
            
            st.subheader("📈 資產成長趨勢圖")
            df = pd.DataFrame(st.session_state.history)
            df_melted = df.melt(id_vars=['Year', 'Total'], value_vars=list(ASSET_KEYS), var_name='Asset_Type', value_name='Value')
            df_melted['Asset_Name'] = df_melted['Asset_Type'].map(ASSET_NAMES)
            
            fig = px.area(df_melted, x="Year", y="Value", color="Asset_Name", color_discrete_map=FINANCE_COLORS, template="plotly_white")
            fig.update_layout(
                hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None),
                margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(title="年份", showgrid=False, tickmode='linear'), yaxis=dict(title="資產價值 ($)", showgrid=True, gridcolor='#F3F4F6', tickformat=".2s")
            )
            fig.update_traces(hovertemplate="%{y:,.0f}")
            st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 階段 3: Finished
# ==========================================
elif st.session_state.stage == 'finished':
    st.balloons()
    final_wealth = sum(st.session_state.assets.values())
    roi = (final_wealth - st.session_state.history[0]['Total']) / st.session_state.history[0]['Total'] * 100
    
    with st.container():
        st.markdown(f"""<div style="text-align: center;"><h1 style="color: #F59E0B !important;">🏆 挑戰完成</h1><p style="font-size: 1.2rem;">恭喜玩家 <b>{st.session_state.user_name}</b> 完成 30 年投資模擬！</p></div>""", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        c1.markdown(f"""<div style="text-align: center; border: 1px solid #F59E0B; padding: 24px; background: #FFFBEB; border-radius: 12px;"><div style="color: #92400E; font-size: 14px; font-weight: 600;">最終資產總額</div><div style="color: #D97706; font-size: 36px; font-weight: 800; font-family: 'Inter';">${int(final_wealth):,}</div></div>""", unsafe_allow_html=True)
        roi_color = '#EF4444' if roi < 0 else '#10B981'
        bg_color = '#FEF2F2' if roi < 0 else '#ECFDF5'
        border_color = '#FCA5A5' if roi < 0 else '#6EE7B7'
        c2.markdown(f"""<div style="text-align: center; border: 1px solid {border_color}; padding: 24px; background: {bg_color}; border-radius: 12px;"><div style="color: #374151; font-size: 14px; font-weight: 600;">總累積報酬率</div><div style="color: {roi_color}; font-size: 36px; font-weight: 800; font-family: 'Inter';">{roi:.1f}%</div></div>""", unsafe_allow_html=True)
        
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