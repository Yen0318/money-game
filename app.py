import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# ⚙️ 後台設定區 (Host Control)
# ==========================================
BASE_RATES = {
    'Dividend': 0.06, 'USBond': 0.03, 'TWStock': 0.07, 'Cash': -0.03, 'Crypto': 0.10
}

EVENT_CARDS = {
    "1. 平穩年代":      {"dividend": 5,  "bond": 3,  "stock": 8,   "cash": 0,  "crypto": 5,   "desc": "✨ 風調雨順，資產穩健增長 (Steady Growth)"},
    "2. 全球金融海嘯":  {"dividend": -10,"bond": 15, "stock": -40, "cash": 0,  "crypto": -60, "desc": "🌊 股市崩盤！資金逃往避險資產 (Market Crash)"},
    "3. 升息循環":      {"dividend": 5,  "bond": -10,"stock": -15, "cash": 2,  "crypto": -30, "desc": "📈 央行升息，債券下跌，現金變香 (Rate Hike)"},
    "4. 降息救市":      {"dividend": 10, "bond": 20, "stock": 25,  "cash": -2, "crypto": 40,  "desc": "💸 資金狂潮！全市場噴發 (Money Printing)"},
    "5. 台海緊張":      {"dividend": -5, "bond": 10, "stock": -30, "cash": -5, "crypto": 10,  "desc": "⚠️ 地緣風險，資金撤離台股 (Geopolitical Risk)"},
    "6. AI 科技革命":   {"dividend": 2,  "bond": -5, "stock": 50,  "cash": 0,  "crypto": 30,  "desc": "🤖 AI 浪潮爆發！科技股大漲 (AI Revolution)"},
    "7. 惡性通膨":      {"dividend": 5,  "bond": -5, "stock": 10,  "cash": -15,"crypto": 50,  "desc": "🔥 錢變薄了！實體資產受惠 (Hyperinflation)"},
    "8. 債務違約危機":  {"dividend": -15,"bond": -20,"stock": -25, "cash": 5,  "crypto": -10, "desc": "📉 流動性枯竭，現金為王 (Credit Crisis)"},
    "9. 加密監管放寬":  {"dividend": 0,  "bond": 0,  "stock": 5,   "cash": 0,  "crypto": 100, "desc": "🚀 比特幣現貨 ETF 通過 (Crypto Bull)"},
    "10. 傳染病大流行": {"dividend": -5, "bond": 10, "stock": -20, "cash": 0,  "crypto": -10, "desc": "🦠 經濟停擺，避險情緒升溫 (Pandemic)"},
    "11. 能源危機":     {"dividend": 10, "bond": -5, "stock": -15, "cash": -5, "crypto": 0,  "desc": "🛢️ 油價飆漲，企業成本大增 (Energy Crisis)"},
    "12. 黃金十年":     {"dividend": 15, "bond": 5,  "stock": 30,  "cash": 0,  "crypto": 20,  "desc": "🌟 經濟奇蹟，萬物齊漲 (Golden Era)"},
}

# --- 1. 頁面設定 ---
st.set_page_config(page_title="翻轉命運 30 年 (Flip Your Destiny)", page_icon="💎TS＿IFRC💎", layout="wide", initial_sidebar_state="collapsed")

# --- 2. ✨ 網美級 CSS (最終完美版) ✨ ---
st.markdown("""
    <style>
    /* A. 背景：極光流體漸層 */
    .stApp {
        background: linear-gradient(-45deg, #ee7752, #e73c7e, #23a6d5, #23d5ab);
        background-size: 400% 400%;
        animation: gradient 15s ease infinite;
        color: white;
    }
    @keyframes gradient {
        0% {background-position: 0% 50%;}
        50% {background-position: 100% 50%;}
        100% {background-position: 0% 50%;}
    }

 /* B. 標題：清晰度修復 */
    h1 {
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 900 !important;
        
        /* 👇👇👇 修改這裡 (原本是 4rem) 👇👇👇 */
        font-size: 2.5rem !important;  
        /* 建議：電腦版用 3rem 或 4rem，手機若覺得太大可改為 2rem 或 2.5rem */
        /* 1rem 大約等於 16px，所以 2.5rem 大約是 40px */
        
        color: #FFFFFF !important;
        text-shadow: 4px 4px 10px rgba(0,0,0,0.8);
        text-align: center;
        margin-bottom: 10px !important;
    }
    
    /* 隱藏討厭的連結符號 */
    h1 a, h2 a, h3 a { display: none !important; }
    
    .subtitle {
        text-align: center; color: rgba(255,255,255,0.95);
        margin-top: -15px; margin-bottom: 30px;
        
        /* 👇👇👇 修改這裡 (原本是 1.3rem) 👇👇👇 */
        font-size: 1.0rem; 
        /* 建議：想要小一點精緻一點，可以改 1.0rem 或 16px */
        
        font-weight: 600;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.6);
    }

    /* C. 毛玻璃卡片 */
    div[data-testid="stExpander"], div[data-testid="stContainer"] {
        background: rgba( 255, 255, 255, 0.1 );
        box-shadow: 0 8px 32px 0 rgba( 31, 38, 135, 0.37 );
        backdrop-filter: blur( 10px );
        -webkit-backdrop-filter: blur( 10px );
        border-radius: 20px;
        border: 1px solid rgba( 255, 255, 255, 0.2 );
        padding: 20px;
        margin-bottom: 20px;
    }

    /* D. 數據指標 */
    div[data-testid="stMetricLabel"] {
        color: rgba(255,255,255,0.9) !important;
        font-size: 1.1rem !important; font-weight: 600;
        text-shadow: 1px 1px 2px black;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2.8rem !important; color: #ffffff !important;
        font-family: 'Futura', sans-serif;
        text-shadow: 2px 2px 5px rgba(0,0,0,0.8);
    }

    /* E. 按鈕美化 */
    div.stButton > button {
        background: linear-gradient(90deg, #FDC830 0%, #F37335 100%);
        border: none; color: white; padding: 15px 32px;
        font-size: 20px; border-radius: 50px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.3);
        width: 100%; font-weight: bold;
    }
    div.stButton > button:hover {
        transform: scale(1.02);
        background: linear-gradient(90deg, #F37335 0%, #FDC830 100%);
    }

    /* F. 進度條 */
    div[data-testid="stProgress"] > div > div {
        background-color: #00FFD1 !important;
    }
    
    /* G. 側邊欄 */
    section[data-testid="stSidebar"] { background-color: #0E1117; }

    /* H. ✨✨ 重點修復：提示框 (st.info) ✨✨ */
    div[data-testid="stAlert"] {
        background-color: rgba(0, 0, 0, 0.7) !important; /* 深黑底，對比強 */
        color: #ffffff !important;
        border: 2px solid #FFD700 !important; /* 金色邊框 */
        border-radius: 15px;
        padding: 20px;
    }
    /* 讓提示框裡面的文字變大、變亮白 */
    div[data-testid="stAlert"] p, div[data-testid="stAlert"] div {
        color: #ffffff !important;
        font-size: 1.3rem !important;
        font-weight: bold !important;
        text-shadow: 1px 1px 2px black;
    }
    /* 讓提示框的 icon 變金色 */
    div[data-testid="stAlert"] svg {
        fill: #FFD700 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 初始化 ---
ASSET_KEYS = ['Dividend', 'USBond', 'TWStock', 'Cash', 'Crypto']
ASSET_NAMES = {'Dividend': '分紅', 'USBond': '美債', 'TWStock': '台股', 'Cash': '現金', 'Crypto': '加密'}
COLORS = ["#FF6B6B", "#4ECDC4", "#FFE66D", "#F7FFF7", "#C44569"] 

if 'stage' not in st.session_state: st.session_state.stage = 'setup'
if 'year' not in st.session_state: st.session_state.year = 0
if 'assets' not in st.session_state: st.session_state.assets = {k: 0 for k in ASSET_KEYS}
if 'history' not in st.session_state: st.session_state.history = []

# --- 側邊欄 ---
with st.sidebar:
    st.header("⚙️ Host Control")
    st.json(BASE_RATES)

# --- 主標題區 (使用新的 class) ---
st.title("💰翻轉命運 30 年💰")
st.markdown("<div class='subtitle'>Flip Your Destiny_TS_IFRC_天行</div>", unsafe_allow_html=True)
st.write("")

# ==========================================
# 階段 1: 初始設定 (Setup)
# ==========================================
if st.session_state.stage == 'setup':
    
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        with st.container():
            st.markdown("### 🚀 起始資金")
            initial_wealth = st.number_input("輸入初始資金", value=1000000, step=100000, label_visibility="collapsed")
            
            st.markdown("---")
            st.markdown("### 🏦 資產配置 (Max 100%)")
            
            c1, c2, c3, c4, c5 = st.columns(5)
            p1 = c1.number_input(f"💵 {ASSET_NAMES['Dividend']}", 0, 100, 20)
            p2 = c2.number_input(f"🧊 {ASSET_NAMES['USBond']}", 0, 100, 20)
            p3 = c3.number_input(f"🔥 {ASSET_NAMES['TWStock']}", 0, 100, 20)
            p4 = c4.number_input(f"🥥 {ASSET_NAMES['Cash']}", 0, 100, 20)
            p5 = c5.number_input(f"🚀 {ASSET_NAMES['Crypto']}", 0, 100, 20)
            
            total_p = p1 + p2 + p3 + p4 + p5
            
            if total_p != 100:
                st.warning(f"⚠️ 目前配置: {total_p}% (需等於 100%)")
                st.progress(min(total_p/100, 1.0))
            else:
                st.write("")
                if st.button("✨ 通往財富自由之路 ✨"):
                    props = [p1, p2, p3, p4, p5]
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
    
    # --- 1. 頂部儀表板 (Dashboard) ---
    total = sum(st.session_state.assets.values())
    roi = (total - st.session_state.history[0]['Total']) / st.session_state.history[0]['Total'] * 100
    
    with st.container():
        c1, c2, c3 = st.columns(3)
        c1.metric("年份", f"{st.session_state.year} / 30")
        c2.metric("財富累積", f"${int(total):,}")
        c3.metric("總報酬率", f"{roi:.1f}%", delta_color="off")
        st.progress(st.session_state.year / 30)

    st.write("") # 空行
    current_year = st.session_state.year
    
    # --- 2. 控制按鈕與劇情區 (移到中間！) ---
    if current_year < 30:
        # A. 跑分階段
        if current_year in [0, 10, 20] and not st.session_state.get('waiting_for_event', False):
            with st.container():
                st.markdown(f"### ⚡ 下一個階段: Year {current_year+1} - {current_year+10}")
                st.caption("複利計算中... 模擬十年後的資產變化")
                
                col_btn, _ = st.columns([1, 0.1])
                if col_btn.button(f"⏩ 十年之後..."):
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

        # B. 抽卡階段
        elif st.session_state.get('waiting_for_event', False):
            with st.container():
                st.markdown(f"<h2 style='text-align:center; color:#FFD700;'>🃏 命運時刻: 第 {current_year} 年</h2>", unsafe_allow_html=True)
                
                selected_card = st.selectbox("選擇發生的事件", list(EVENT_CARDS.keys()), label_visibility="collapsed")
                card_data = EVENT_CARDS[selected_card]
                
                st.info(f"{card_data['desc']}")
                
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("分紅", f"{card_data['dividend']}%")
                c2.metric("美債", f"{card_data['bond']}%")
                c3.metric("台股", f"{card_data['stock']}%")
                c4.metric("現金", f"{card_data['cash']}%")
                c5.metric("加密", f"{card_data['crypto']}%")
                
                if st.button("💥 命運卡牌！"):
                    st.session_state.assets['Dividend'] *= (1 + card_data['dividend']/100)
                    st.session_state.assets['USBond']   *= (1 + card_data['bond']/100)
                    st.session_state.assets['TWStock']  *= (1 + card_data['stock']/100)
                    st.session_state.assets['Cash']     *= (1 + card_data['cash']/100)
                    st.session_state.assets['Crypto']   *= (1 + card_data['crypto']/100)
                    
                    last_rec = st.session_state.history[-1]
                    last_rec.update(st.session_state.assets)
                    last_rec['Total'] = sum(st.session_state.assets.values())
                    
                    st.session_state.waiting_for_event = False
                    if st.session_state.year == 30:
                        st.session_state.stage = 'finished'
                    st.rerun()

    # --- 3. 圖表區 (現在移到最下面了！) ---
    st.markdown("---") # 加一條分隔線比較好看
    if len(st.session_state.history) > 0:
        import plotly.express as px
        
        with st.container():
            df = pd.DataFrame(st.session_state.history)
            df_melted = df.melt(id_vars=['Year', 'Total'], 
                                value_vars=list(ASSET_KEYS),
                                var_name='Asset_Type', 
                                value_name='Value')
            df_melted['Asset_Name'] = df_melted['Asset_Type'].map(ASSET_NAMES)
            
            fig = px.bar(
                df_melted, 
                x="Year", 
                y="Value", 
                color="Asset_Name",
                title="📈 ASSET GROWTH TRACKER",
                color_discrete_map={
                    '分紅': '#FF6B6B', '美債': '#4ECDC4', '台股': '#FFE66D',
                    '現金': '#F7FFF7', '加密': '#C44569'
                },
                labels={"Value": "資產價值 ($)", "Year": "年份", "Asset_Name": "資產類別"}
            )
            
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",   
                paper_bgcolor="rgba(0,0,0,0.4)", 
                font_color="white",
                font_family="Arial",
                title_font_size=20,
                title_font_color="#FFD700",
                title_x=0,
                legend_title_text="",
                hovermode="x unified",
                bargap=0.3,
                margin=dict(l=20, r=20, t=50, b=20),
                legend=dict(
                    orientation="h",
                    yanchor="bottom", y=1.02,
                    xanchor="right", x=1,
                    font=dict(size=12, color="white"),
                    bgcolor="rgba(0,0,0,0.5)"
                )
            )
            fig.update_xaxes(showgrid=False, tickfont=dict(size=14, color="#FFD700"))
            fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.2)", tickfont=dict(size=12, color="white"))
            fig.update_traces(hovertemplate="%{y:,.0f}") 

            st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 階段 3: 結算 (Finished)
# ==========================================
elif st.session_state.stage == 'finished':
    st.balloons()
    
    with st.container():
        st.markdown("<h1 style='text-align: center; font-size: 80px;'>🏆</h1>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: #fff;'>FINANCIAL FREEDOM</h1>", unsafe_allow_html=True)
        
        final_wealth = sum(st.session_state.assets.values())
        initial = st.session_state.history[0]['Total']
        roi = (final_wealth - initial) / initial * 100
        
        c1, c2 = st.columns(2)
        c1.metric("FINAL ASSETS", f"${int(final_wealth):,}")
        c2.metric("TOTAL RETURN", f"{roi:.1f}%")
        
        df = pd.DataFrame(st.session_state.history)
        df_renamed = df.rename(columns=ASSET_NAMES)
        chart_cols = list(ASSET_NAMES.values())
        st.area_chart(df_renamed.set_index('Year')[chart_cols], color=COLORS)

    if st.button("🔄 RESTART GAME"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()