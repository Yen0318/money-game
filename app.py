import streamlit as st
import pandas as pd
import numpy as np
import os
import csv
from datetime import datetime

# ==========================================
# ⚙️ 後台設定區
# ==========================================
BASE_RATES = {
    'Dividend': 0.05, 'USBond': 0.04, 'TWStock': 0.08, 'Cash': 0.01, 'Crypto': 0.15
}

EVENT_CARDS = {
    "1. 平穩年代":      {"dividend": 5,  "bond": 3,  "stock": 8,   "cash": 0,  "crypto": 5,   "desc": "✨ 風調雨順，資產穩健增長"},
    "2. 全球金融海嘯":  {"dividend": -10,"bond": 15, "stock": -40, "cash": 0,  "crypto": -60, "desc": "🌊 股市崩盤！資金逃往避險資產"},
    "3. 升息循環":      {"dividend": 5,  "bond": -10,"stock": -15, "cash": 2,  "crypto": -30, "desc": "📈 央行升息，債券下跌，現金變香"},
    "4. 降息救市":      {"dividend": 10, "bond": 20, "stock": 25,  "cash": -2, "crypto": 40,  "desc": "💸 資金狂潮！全市場噴發"},
    "5. 台海緊張":      {"dividend": -5, "bond": 10, "stock": -30, "cash": -5, "crypto": 10,  "desc": "⚠️ 地緣風險，資金撤離台股"},
    "6. AI 科技革命":   {"dividend": 2,  "bond": -5, "stock": 50,  "cash": 0,  "crypto": 30,  "desc": "🤖 AI 浪潮爆發！科技股大漲"},
    "7. 惡性通膨":      {"dividend": 5,  "bond": -5, "stock": 10,  "cash": -15,"crypto": 50,  "desc": "🔥 錢變薄了！實體資產受惠"},
    "8. 債務違約危機":  {"dividend": -15,"bond": -20,"stock": -25, "cash": 5,  "crypto": -10, "desc": "📉 流動性枯竭，現金為王"},
    "9. 加密監管放寬":  {"dividend": 0,  "bond": 0,  "stock": 5,   "cash": 0,  "crypto": 100, "desc": "🚀 比特幣現貨 ETF 通過"},
    "10. 傳染病大流行": {"dividend": -5, "bond": 10, "stock": -20, "cash": 0,  "crypto": -10, "desc": "🦠 經濟停擺，避險情緒升溫"},
    "11. 能源危機":     {"dividend": 10, "bond": -5, "stock": -15, "cash": -5, "crypto": 0,  "desc": "🛢️ 油價飆漲，企業成本大增"},
    "12. 黃金十年":     {"dividend": 15, "bond": 5,  "stock": 30,  "cash": 0,  "crypto": 20,  "desc": "🌟 經濟奇蹟，萬物齊漲"},
}

CSV_FILE = 'game_data_records.csv'

# --- 存檔函數 ---
def save_data_to_csv(name, wealth, roi, cards, config_history, feedback):
    # 整理要存的資料欄位
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
    
    # 寫入 CSV (使用 utf-8-sig 讓 Excel 開啟不亂碼)
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=data.keys())
        if not file_exists:
            writer.writeheader() # 如果檔案不存在，先寫標題
        writer.writerow(data)

# --- 1. 頁面設定 ---
st.set_page_config(page_title="Flip Your Destiny", page_icon="💎", layout="wide")

# --- 2. CSS 美化 ---
st.markdown("""
    <style>
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
    h1 {
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 900 !important;
        font-size: 2.5rem !important;
        color: #FFFFFF !important;
        text-shadow: 3px 3px 6px rgba(0,0,0,0.8);
        text-align: center;
        margin-bottom: 10px !important;
    }
    h1 a, h2 a, h3 a { display: none !important; }
    div[data-testid="stExpander"], div[data-testid="stContainer"] {
        background: rgba( 255, 255, 255, 0.15 );
        backdrop-filter: blur( 12px );
        border-radius: 20px;
        border: 1px solid rgba( 255, 255, 255, 0.18 );
        padding: 20px;
        margin-bottom: 20px;
    }
    div.stButton > button {
        background: linear-gradient(90deg, #FDC830 0%, #F37335 100%);
        border: none; color: white; padding: 12px 24px;
        font-size: 18px; border-radius: 50px;
        width: 100%; font-weight: bold;
    }
    label { color: white !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 初始化 ---
ASSET_KEYS = ['Dividend', 'USBond', 'TWStock', 'Cash', 'Crypto']
ASSET_NAMES = {'Dividend': '分紅', 'USBond': '美債', 'TWStock': '台股', 'Cash': '現金', 'Crypto': '加密'}

if 'stage' not in st.session_state: st.session_state.stage = 'login'
if 'year' not in st.session_state: st.session_state.year = 0
if 'assets' not in st.session_state: st.session_state.assets = {k: 0 for k in ASSET_KEYS}
if 'history' not in st.session_state: st.session_state.history = []
if 'user_name' not in st.session_state: st.session_state.user_name = ""
if 'drawn_cards' not in st.session_state: st.session_state.drawn_cards = []
if 'config_history' not in st.session_state: st.session_state.config_history = {}
if 'data_saved' not in st.session_state: st.session_state.data_saved = False # 防止重複存檔

# --- 側邊欄 (加密版主持人後台) ---
ADMIN_PASSWORD = "tsts"  # 👈 你可以在這裡修改密碼！

if 'admin_unlocked' not in st.session_state:
    st.session_state.admin_unlocked = False

with st.sidebar:
    st.header("🕵️‍♂️ 主持人後台")
    
    # 如果還沒解鎖，顯示密碼框
    if not st.session_state.admin_unlocked:
        st.info("🔒 此區域受密碼保護")
        pwd_input = st.text_input("請輸入管理員密碼", type="password", key="admin_pwd_input")
        
        if pwd_input:
            if pwd_input == ADMIN_PASSWORD:
                st.session_state.admin_unlocked = True
                st.rerun()  # 密碼對了，刷新頁面進入後台
            else:
                st.error("❌ 密碼錯誤，請重新輸入")
    
    # 如果已經解鎖，顯示資料
    else:
        st.success("✅ 已登入管理員模式")
        
        # 顯示資料功能
        if os.path.exists(CSV_FILE):
            df_record = pd.read_csv(CSV_FILE)
            st.write(f"📊 目前紀錄：{len(df_record)} 筆")
            
            # 下載按鈕
            with open(CSV_FILE, "rb") as file:
                st.download_button(
                    label="📥 下載 Excel (CSV) 檔",
                    data=file,
                    file_name="game_results.csv",
                    mime="text/csv"
                )
            
            # 預覽數據
            with st.expander("🔎 查看詳細數據表"):
                st.dataframe(df_record)
        else:
            st.warning("📭 目前尚無任何遊戲紀錄")
            
        st.markdown("---")
        # 登出按鈕
        if st.button("🔒 鎖定後台 (登出)"):
            st.session_state.admin_unlocked = False
            st.rerun()

# --- 標題 ---
st.markdown("""
    <div style="text-align: center; padding: 10px 0;">
        <h1 style="color: #FFFFFF; text-shadow: 3px 3px 6px rgba(0,0,0,0.8); font-size: 40px; margin: 0; font-weight: 900;">
            💰 翻轉命運 30 年
        </h1>
        <h2 style="color: #FFD700; text-shadow: 2px 2px 4px rgba(0,0,0,0.8); font-size: 20px; margin-top: 5px; font-family: 'Helvetica', sans-serif;">
            (Flip Your Destiny)
        </h2>
        <div style="display: inline-block; background: rgba(0,0,0,0.3); padding: 5px 15px; border-radius: 20px; color: #E0E0E0; font-size: 14px; margin-top: 10px;">
            TS_IFRC_天行
        </div>
    </div>
""", unsafe_allow_html=True)
st.write("")

# ==========================================
# 階段 0: 登入
# ==========================================
if st.session_state.stage == 'login':
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        with st.container():
            st.markdown("### 👋 歡迎挑戰者")
            name_input = st.text_input("請輸入您的姓名 / 暱稱", placeholder="例如：Kevin")
            if st.button("開始挑戰"):
                if name_input.strip():
                    st.session_state.user_name = name_input
                    st.session_state.stage = 'setup'
                    st.session_state.data_saved = False # 重置存檔狀態
                    st.rerun()
                else:
                    st.warning("請輸入姓名才能開始喔！")

# ==========================================
# 階段 1: Setup
# ==========================================
elif st.session_state.stage == 'setup':
    with st.container():
        st.markdown(f"### 🚀 設定初始配置 (Player: {st.session_state.user_name})")
        initial_wealth = st.number_input("初始資金", value=1000000, step=100000)
        st.markdown("---")
        st.markdown("#### 📊 Year 0 資產配置")
        c1, c2, c3, c4, c5 = st.columns(5)
        p1 = c1.number_input(f"{ASSET_NAMES['Dividend']}", 0, 100, 20)
        p2 = c2.number_input(f"{ASSET_NAMES['USBond']}", 0, 100, 20)
        p3 = c3.number_input(f"{ASSET_NAMES['TWStock']}", 0, 100, 20)
        p4 = c4.number_input(f"{ASSET_NAMES['Cash']}", 0, 100, 20)
        p5 = c5.number_input(f"{ASSET_NAMES['Crypto']}", 0, 100, 20)
        
        if (p1+p2+p3+p4+p5) != 100:
            st.warning(f"目前總和: {p1+p2+p3+p4+p5}% (需為 100%)")
        else:
            if st.button("確認配置並出發"):
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
    
    # Dashboard
    total = sum(st.session_state.assets.values())
    roi = (total - st.session_state.history[0]['Total']) / st.session_state.history[0]['Total'] * 100
    
    with st.container():
        c1, c2, c3 = st.columns(3)
        c1.metric("年份", f"{st.session_state.year} / 30")
        c2.metric("財富累積", f"${int(total):,}")
        c3.metric("總報酬率", f"{roi:.1f}%")
        st.progress(st.session_state.year / 30)

    current_year = st.session_state.year
    
    # --- 流程控制區 (邏輯修復版) ---
    # 這裡的順序很重要：先檢查「有沒有待辦事項」，最後才看「能不能跑下一年」
    
    # 1. 優先處理：抽卡事件 (發生在 Year 10, 20, 30)
    if st.session_state.get('waiting_for_event', False):
        with st.container():
            st.markdown(f"""
                <div style="margin-top: 20px;">
                    <h2 style="text-align:center; color:#FFD700;">🃏 第 {current_year} 年：命運抽卡</h2>
                </div>
            """, unsafe_allow_html=True)
            
            selected_card = st.selectbox("選擇發生的事件", list(EVENT_CARDS.keys()), label_visibility="collapsed")
            card_data = EVENT_CARDS[selected_card]
            
            # 顯示卡片資訊
            st.markdown(f"""
                <div style="
                    background: rgba(0, 0, 0, 0.6);
                    border-left: 6px solid #FFD700;
                    border-radius: 10px;
                    padding: 20px;
                    color: #FFFFFF;
                    font-size: 1.3rem;
                    font-weight: bold;
                    margin-bottom: 20px;
                    box-shadow: 0 4px 10px rgba(0,0,0,0.3);">
                    📜 {card_data['desc']}
                </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("分紅", f"{card_data['dividend']}%")
            c2.metric("美債", f"{card_data['bond']}%")
            c3.metric("台股", f"{card_data['stock']}%")
            c4.metric("現金", f"{card_data['cash']}%")
            c5.metric("加密", f"{card_data['crypto']}%")
            
            if st.button("💥 接受命運衝擊"):
                st.session_state.assets['Dividend'] *= (1 + card_data['dividend']/100)
                st.session_state.assets['USBond']   *= (1 + card_data['bond']/100)
                st.session_state.assets['TWStock']  *= (1 + card_data['stock']/100)
                st.session_state.assets['Cash']     *= (1 + card_data['cash']/100)
                st.session_state.assets['Crypto']   *= (1 + card_data['crypto']/100)
                
                # 紀錄抽卡
                st.session_state.drawn_cards.append(f"Year {current_year}: {selected_card}")
                
                # 更新數據
                last_rec = st.session_state.history[-1]
                last_rec.update(st.session_state.assets)
                last_rec['Total'] = sum(st.session_state.assets.values())
                
                st.session_state.waiting_for_event = False
                
                # 關鍵邏輯：如果是第30年，直接結算；否則進入再平衡
                if current_year >= 30:
                    st.session_state.stage = 'finished'
                else:
                    st.session_state.waiting_for_rebalance = True
                st.rerun()

    # 2. 次要處理：再平衡 (發生在 Year 10, 20 事件後)
    elif st.session_state.get('waiting_for_rebalance', False):
        with st.container():
            current_total = sum(st.session_state.assets.values())
            
            # 帥氣儀表板
            st.markdown(f"""
                <div style="margin-bottom: 20px;">
                    <h3 style="color: white; margin-bottom: 10px;">⚖️ 資產再平衡 (Year {current_year})</h3>
                    <div style="
                        background: rgba(0, 0, 0, 0.6);
                        border-left: 6px solid #00FFD1;
                        border-radius: 10px;
                        padding: 20px;
                        color: #FFFFFF;
                        font-size: 1.5rem;
                        font-weight: bold;
                        box-shadow: 0 4px 15px rgba(0,255,209, 0.2);
                        display: flex; align-items: center;">
                        💰 目前總資產： 
                        <span style="color: #00FFD1; margin-left: 15px; font-family: monospace;">
                            ${int(current_total):,}
                        </span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            st.write("您可以決定接下來 10 年的資產配置比例：")
            
            c1, c2, c3, c4, c5 = st.columns(5)
            rb1 = c1.number_input(f"{ASSET_NAMES['Dividend']}", 0, 100, 20, key=f"rb1_{current_year}")
            rb2 = c2.number_input(f"{ASSET_NAMES['USBond']}", 0, 100, 20, key=f"rb2_{current_year}")
            rb3 = c3.number_input(f"{ASSET_NAMES['TWStock']}", 0, 100, 20, key=f"rb3_{current_year}")
            rb4 = c4.number_input(f"{ASSET_NAMES['Cash']}", 0, 100, 20, key=f"rb4_{current_year}")
            rb5 = c5.number_input(f"{ASSET_NAMES['Crypto']}", 0, 100, 20, key=f"rb5_{current_year}")
            
            total_rb = rb1 + rb2 + rb3 + rb4 + rb5
            
            if total_rb != 100:
                st.warning(f"目前配置: {total_rb}% (需等於 100%)")
            else:
                st.write("")
                if st.button("✅ 確認調整配置"):
                    props = [rb1, rb2, rb3, rb4, rb5]
                    st.session_state.config_history[f'Year {current_year}'] = {k: v for k, v in zip(ASSET_KEYS, props)}
                    for i, key in enumerate(ASSET_KEYS):
                        st.session_state.assets[key] = current_total * (props[i] / 100)
                    
                    last_rec = st.session_state.history[-1]
                    last_rec.update(st.session_state.assets)
                    st.session_state.waiting_for_rebalance = False
                    st.rerun()

    # 3. 正常跑分：如果上面都沒有待辦事項，且還沒到 30 年，才顯示跑分按鈕
    elif current_year < 30:
        with st.container():
            st.markdown(f"### ⚡ 準備進入: Year {current_year+1} - {current_year+10}")
            st.caption("複利計算中... 模擬十年後的資產變化")
            
            col_btn, _ = st.columns([1, 0.1])
            if col_btn.button(f"⏩ 執行這 10 年的複利"):
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

    # --- 圖表區 (放在最下面) ---
    st.markdown("---")
    if len(st.session_state.history) > 0:
        import plotly.express as px
        with st.container():
            df = pd.DataFrame(st.session_state.history)
            df_melted = df.melt(id_vars=['Year', 'Total'], value_vars=list(ASSET_KEYS), var_name='Asset_Type', value_name='Value')
            df_melted['Asset_Name'] = df_melted['Asset_Type'].map(ASSET_NAMES)
            
            fig = px.bar(
                df_melted, x="Year", y="Value", color="Asset_Name",
                title="📈 ASSET GROWTH TRACKER",
                color_discrete_map={'分紅': '#FF6B6B', '美債': '#4ECDC4', '台股': '#FFE66D', '現金': '#F7FFF7', '加密': '#C44569'},
                labels={"Value": "資產價值 ($)", "Year": "年份", "Asset_Name": "資產類別"}
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0.4)",
                font_color="white", font_family="Arial",
                title_font_size=20, title_font_color="#FFD700", title_x=0,
                legend_title_text="", hovermode="x unified", bargap=0.3,
                margin=dict(l=20, r=20, t=50, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=12, color="white"), bgcolor="rgba(0,0,0,0.5)")
            )
            fig.update_xaxes(showgrid=False, tickfont=dict(size=14, color="#FFD700"))
            fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.2)", tickfont=dict(size=12, color="white"))
            fig.update_traces(hovertemplate="%{y:,.0f}") 
            st.plotly_chart(fig, use_container_width=True)
# ==========================================
# 階段 3: Finished (自動存檔)
# ==========================================
elif st.session_state.stage == 'finished':
    st.balloons()
    
    final_wealth = sum(st.session_state.assets.values())
    roi = (final_wealth - st.session_state.history[0]['Total']) / st.session_state.history[0]['Total'] * 100
    
    with st.container():
        st.markdown(f"<h1 style='text-align: center;'>🏆 挑戰完成！ {st.session_state.user_name}</h1>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        c1.metric("最終資產", f"${int(final_wealth):,}")
        c2.metric("總報酬率", f"{roi:.1f}%")
        
        st.markdown("### 📝 請輸入反饋以完成紀錄")
        feedback = st.text_area("心得 / 建議", placeholder="寫下你的心得...")
        
# 存檔按鈕
        if st.button("💾 送出紀錄並結束"):
            if not st.session_state.data_saved:
                # 呼叫存檔函數
                save_data_to_csv(
                    st.session_state.user_name,
                    final_wealth,
                    roi,
                    st.session_state.drawn_cards,
                    st.session_state.config_history,
                    feedback
                )
                st.session_state.data_saved = True
                st.success("✅ 資料已自動儲存到後台！")
                
                # --- ✨ 新增這兩行：讓它停 1 秒後自動刷新頁面 ✨ ---
                import time
                time.sleep(1) # 讓玩家看清楚「成功」的綠色訊息
                st.rerun()    # 強制重整，側邊欄就會更新了
                # ---------------------------------------------
                
            else:
                st.info("您已經送出過了喔！")