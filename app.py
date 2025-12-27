import os
import csv
import copy
from datetime import datetime
from pathlib import Path
import pandas as pd
import plotly.express as px
from shiny import App, Inputs, Outputs, Session, reactive, render, ui, req
from shinywidgets import output_widget, render_widget

# ==========================================
# ⚙️ 全域設定 (常數)
# ==========================================
BASE_RATES = {
    'Dividend': 0.06, 'USBond': 0.03, 'TWStock': 0.07, 'Cash': 0.0, 'Crypto': 0.1
}

ASSET_KEYS = ['Dividend', 'USBond', 'TWStock', 'Cash', 'Crypto']
ASSET_NAMES = {'Dividend': '分紅收益', 'USBond': '美債', 'TWStock': '台股', 'Cash': '現金', 'Crypto': '加密幣'}
FINANCE_COLORS = {'分紅收益': '#F59E0B', '美債': '#3B82F6', '台股': '#EF4444', '現金': '#9CA3AF', '加密幣': '#8B5CF6'}

# 注意：這裡的 key 是小寫，對應卡片資料結構
KEY_MAPPING = {'Dividend': 'dividend', 'USBond': 'bond', 'TWStock': 'stock', 'Cash': 'cash', 'Crypto': 'crypto'}

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
ADMIN_PASSWORD = "tsts"

# CSS 樣式
custom_css = """
:root { --primary: #2563EB; --primary-dark: #1E40AF; --secondary: #F59E0B; --bg-main: #F3F4F6; }
body { font-family: 'Inter', 'Noto Sans TC', sans-serif; background-color: var(--bg-main); color: #1F2937; }
.card { border-radius: 12px; border: 1px solid #E5E7EB; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05); background: white; padding: 20px; margin-bottom: 20px; }
.btn-primary { background: linear-gradient(135deg, var(--primary), var(--primary-dark)) !important; border: none; color: white !important; font-weight: 600; }
.btn-primary:hover { box-shadow: 0 6px 10px rgba(37, 99, 235, 0.3); opacity: 0.9; }
h1 { color: var(--primary-dark); font-weight: 800; text-align: center; }
.metric-box { text-align: center; border: 1px solid #E5E7EB; border-radius: 8px; padding: 10px; background: white; }
.metric-val { font-size: 1.5rem; font-weight: 800; color: var(--primary-dark); }
.metric-label { font-size: 0.9rem; color: #6B7280; }
/* Table Style */
.asset-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
.asset-table th { text-align: left; padding: 8px; color: #6B7280; font-size: 0.9rem; border-bottom: 2px solid #E5E7EB; }
.asset-table td { padding: 12px 8px; border-bottom: 1px solid #F3F4F6; font-weight: 500; }
.impact-box { padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 10px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
"""

# ==========================================
# 🖥️ UI 介面設計
# ==========================================
app_ui = ui.page_fluid(
    ui.head_content(ui.tags.style(custom_css)),
    
    # 1. 標題區
    ui.div(
        ui.div("IFRC x TS", style="font-size: 0.9rem; font-weight: 800; color: #9CA3AF; letter-spacing: 3px; margin-bottom: 8px; text-transform: uppercase; text-align: center; margin-top: 20px;"),
        ui.h1("💰 扭轉命運 30 年", style="margin: 0; padding: 0;"),
        ui.div("Wealth Management Simulation", style="color: #6B7280; font-size: 1.2rem; font-weight: 500; margin-top: 8px; text-align: center; margin-bottom: 30px;"),
    ),

    # ✨ 使用 ui.layout_sidebar 來正確包覆側邊欄
    ui.layout_sidebar(
        # 2. 側邊欄
        ui.sidebar(
            ui.h3("🏦 管理員後台"),
            ui.input_password("admin_pwd", "管理員密碼"),
            ui.panel_conditional(
                f"input.admin_pwd == '{ADMIN_PASSWORD}'",
                ui.h4("🔓 已解鎖", style="color: green"),
                ui.input_action_button("admin_reset_game", "🔥 清空當前遊戲狀態"),
                ui.input_action_button("admin_clear_csv", "🧹 清空歷史 CSV"),
                ui.hr(),
                ui.download_button("admin_download_csv", "📥 下載 CSV"),
            ),
            bg="#FFFFFF", open="closed"
        ),
        
        # 3. 主要內容區
        ui.navset_hidden(
            # --- Page 1: Login ---
            ui.nav_panel("login",
                ui.layout_columns(
                    ui.div(), # spacer
                    ui.div(
                        ui.div(
                            ui.img(src="images/homepage.png", style="max-width: 100%; border-radius: 12px;"),
                            style="text-align: center; margin-bottom: 20px;"
                        ),
                        ui.div("扭轉命運的機會就在眼前，準備好了嗎？", style="text-align: center; color: #6B7280; margin-bottom: 20px;"),
                        ui.input_text("user_name", "請輸入玩家暱稱", placeholder="例如: 小明"),
                        ui.input_action_button("start_game", "▶ 開始挑戰", class_="btn-primary", style="width: 100%; margin-top: 10px;"),
                        class_="card"
                    ),
                    ui.div(), # spacer
                    col_widths=(3, 6, 3)
                ),
                ui.div(
                    ui.div(
                        ui.HTML("<b>製作團隊 IFRC x TS</b><br>🔹 總策劃：Yen/全家/Color/EN/Liya/小天/Yuna/Renee<br>🔹 技術支援：Yen<br>🔹 美術支援：Liya<br>🔹 遊戲設計：天行 & IFRC"),
                        style="display: inline-block; text-align: left; background: white; padding: 15px 30px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); color: #4B5563; font-size: 13px;"
                    ),
                    style="text-align: center; margin-top: 30px;"
                )
            ),

            # --- Page 2: Setup (Year 0) ---
            ui.nav_panel("setup",
                ui.layout_columns(
                    ui.div(
                        ui.h3("🚀 初始資產配置"),
                        ui.p("請分配您的 $1,000,000 資金，總和必須為 100%。"),
                        ui.output_ui("setup_rates_table"), 
                        class_="card"
                    ),
                    ui.div(
                        ui.h4("第 0 年配置"),
                        ui.input_numeric("p_div", f"{ASSET_NAMES['Dividend']} %", 20, min=0, max=100),
                        ui.input_numeric("p_bond", f"{ASSET_NAMES['USBond']} %", 20, min=0, max=100),
                        ui.input_numeric("p_stock", f"{ASSET_NAMES['TWStock']} %", 20, min=0, max=100),
                        ui.input_numeric("p_cash", f"{ASSET_NAMES['Cash']} %", 20, min=0, max=100),
                        ui.input_numeric("p_crypto", f"{ASSET_NAMES['Crypto']} %", 20, min=0, max=100),
                        ui.output_ui("setup_status"), 
                        ui.input_action_button("confirm_setup", "確定配置 ✅", class_="btn-primary", style="width: 100%"),
                        class_="card"
                    ),
                    col_widths=(7, 5)
                )
            ),

            # --- Page 3: Playing ---
            ui.nav_panel("playing",
                # Top Dashboard
                ui.div(
                    ui.layout_columns(
                        ui.div(ui.div("目前年份", class_="metric-label"), ui.output_text("ui_year", inline=True), class_="metric-box"),
                        ui.div(ui.div("總資產", class_="metric-label"), ui.output_text("ui_wealth", inline=True), class_="metric-box"),
                        ui.div(ui.div("累積報酬率", class_="metric-label"), ui.output_text("ui_roi", inline=True), class_="metric-box"),
                    ),
                    style="margin-bottom: 20px;"
                ),
                
                ui.div(ui.output_ui("ui_progress_bar"), style="margin-bottom: 20px;"),

                # Dynamic Interaction Area
                ui.output_ui("game_interaction_area"),
                
                ui.br(),
                ui.layout_columns(
                    ui.div(
                        ui.h4("📊 當前資產分佈"),
                        output_widget("chart_assets_now"),
                        class_="card"
                    ),
                    ui.div(
                        ui.h4("💰 資產詳細清單"),
                        # 🔥 新增：這裡顯示實際金額表格
                        ui.output_ui("ui_current_assets_detail"),
                        class_="card"
                    ),
                    col_widths=(6, 6)
                )
            ),

            # --- Page 4: Finished ---
            ui.nav_panel("finished",
                ui.div(
                    ui.h1("🏆 挑戰完成！", style="color: #F59E0B"),
                    ui.output_ui("ig_share_card"), 
                    ui.br(),
                    ui.layout_columns(
                        ui.div(ui.div("最終資產", style="color: #92400E"), ui.div(ui.output_text("final_wealth_text"), style="font-size: 32px; font-weight: 800; color: #D97706"), style="background: #FFFBEB; padding: 20px; border-radius: 12px; border: 1px solid #F59E0B"),
                        ui.div(ui.div("總報酬率", style="color: #065F46"), ui.div(ui.output_text("final_roi_text"), style="font-size: 32px; font-weight: 800; color: #059669"), style="background: #ECFDF5; padding: 20px; border-radius: 12px; border: 1px solid #10B981"),
                    ),
                    ui.hr(),
                    ui.h4("📈 歷史資產走勢"),
                    output_widget("chart_history_area"),
                    ui.hr(),
                    ui.h4("🎛️ 歷史配置策略"),
                    output_widget("chart_config_history"),
                    ui.hr(),
                    ui.h4("🎴 命運歷程"),
                    ui.output_ui("history_cards_list"),
                    ui.hr(),
                    ui.input_text_area("feedback", "請留下您的心得", width="100%"),
                    ui.input_action_button("save_finish", "💾 儲存並結束", class_="btn-primary"),
                    ui.br(), ui.br(),
                    ui.input_action_button("restart_game", "🔄 開啟新挑戰"),
                    style="text-align: center; padding: 20px;"
                )
            ),

            id="wizard" 
        )
    )
)

# ==========================================
# 🧠 Server 邏輯核心
# ==========================================
def server(input: Inputs, output: Outputs, session: Session):
    
    # --- Reactive State ---
    game_state = reactive.Value({
        "year": 0,
        "assets": {k: 0 for k in ASSET_KEYS},
        "history": [],
        "config_history": {},
        "drawn_cards": [],
        "sub_stage": "wait_jump", 
        "dynamic_rates": BASE_RATES.copy(),
        "user_name": ""
    })
    
    # --- 1. Login ---
    @reactive.Effect
    @reactive.event(input.start_game)
    def _():
        name = input.user_name().strip()
        if name:
            gs = copy.deepcopy(game_state.get())
            gs["user_name"] = name
            game_state.set(gs)
            ui.update_navs("wizard", selected="setup")
        else:
            ui.notification_show("請輸入暱稱！", type="error")

    # --- 2. Setup ---
    @render.ui
    def setup_rates_table():
        rows = ""
        risk_map = {'Dividend': '低', 'USBond': '極低', 'TWStock': '中高', 'Cash': '無', 'Crypto': '極高'}
        for k in ASSET_KEYS:
            rows += f"<tr><td>{ASSET_NAMES[k]}</td><td>{int(BASE_RATES[k]*100)}%</td><td>{risk_map[k]}</td></tr>"
        return ui.HTML(f"<table class='table table-striped'><thead><tr><th>資產</th><th>年化</th><th>風險</th></tr></thead><tbody>{rows}</tbody></table>")

    @render.ui
    def setup_status():
        try:
            v1, v2, v3, v4, v5 = input.p_div(), input.p_bond(), input.p_stock(), input.p_cash(), input.p_crypto()
            if any(x is None for x in [v1, v2, v3, v4, v5]):
                return ui.div()
                
            total = v1 + v2 + v3 + v4 + v5
            color = "green" if abs(total - 100) < 0.1 else "red"
            return ui.div(f"目前總和: {total}% (目標: 100%)", style=f"color: {color}; font-weight: bold; margin: 10px 0;")
        except:
            return ui.div()

    @reactive.Effect
    @reactive.event(input.confirm_setup)
    def _():
        try:
            total = input.p_div() + input.p_bond() + input.p_stock() + input.p_cash() + input.p_crypto()
        except TypeError:
            return 

        if abs(total - 100) > 0.1:
            ui.notification_show("比例總和必須為 100%！", type="error")
            return

        initial = 1000000
        props = [input.p_div(), input.p_bond(), input.p_stock(), input.p_cash(), input.p_crypto()]
        gs = copy.deepcopy(game_state.get())
        
        new_assets = {}
        for i, k in enumerate(ASSET_KEYS):
            new_assets[k] = initial * (props[i] / 100)
            
        gs["assets"] = new_assets
        gs["history"] = [{'Year': 0, 'Total': initial, **new_assets}]
        gs["config_history"]['Year 0'] = {k: v for k, v in zip(ASSET_KEYS, props)}
        gs["year"] = 0
        gs["sub_stage"] = "wait_jump"
        game_state.set(gs)
        ui.update_navs("wizard", selected="playing")

    # --- 3. Playing Core Logic ---
    @render.text 
    def ui_year(): return f"第 {game_state.get()['year']} 年"
    
    @render.text 
    def ui_wealth(): return f"${int(sum(game_state.get()['assets'].values())):,}"
    
    @render.text 
    def ui_roi(): 
        hist = game_state.get()['history']
        if not hist: return "0%"
        start = hist[0]['Total']
        curr = sum(game_state.get()['assets'].values())
        return f"{(curr - start) / start * 100:.1f}%"

    @render.ui
    def ui_progress_bar():
        y = game_state.get()['year']
        pct = (y / 30) * 100
        return ui.HTML(f'<div style="width:100%; background:#E5E7EB; height:8px; border-radius:4px;"><div style="width:{pct}%; background:var(--primary); height:100%; border-radius:4px;"></div></div>')

    # 🔥 新增功能 1: 顯示當前資產詳細金額表格
    @render.ui
    def ui_current_assets_detail():
        assets = game_state.get()['assets']
        total = sum(assets.values())
        
        rows = ""
        for k in ASSET_KEYS:
            val = assets[k]
            pct = (val / total * 100) if total > 0 else 0
            rows += f"""
            <tr>
                <td style="color:{FINANCE_COLORS[ASSET_NAMES[k]]}; font-weight:bold;">{ASSET_NAMES[k]}</td>
                <td>${int(val):,}</td>
                <td>{pct:.1f}%</td>
            </tr>
            """
        
        return ui.HTML(f"""
        <table class="asset-table">
            <thead>
                <tr>
                    <th>項目</th>
                    <th>金額 ($)</th>
                    <th>佔比</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        """)

    @render.ui
    def game_interaction_area():
        gs = game_state.get()
        sub = gs["sub_stage"]
        year = gs["year"]
        
        if sub == "wait_jump":
            btn_txt = f"🚀 啟動時光機 (前往第 {year+10} 年)" if year == 0 else f"🚀 前往下一個十年 (Year {year+10})"
            return ui.div(
                ui.h3(f"⏩ 準備推進: 第 {year+1} - {year+10} 年"),
                ui.input_action_button("btn_jump_time", btn_txt, class_="btn-primary", style="font-size: 1.2rem; padding: 15px; width: 100%;"),
                class_="card", style="background: #F0F9FF; border-left: 5px solid #3B82F6;"
            )

        elif sub == "event_input":
            return ui.div(
                ui.h2(f"⚡ 重大財經事件發生 (Year {year})", style="color: #EF4444; text-align: center;"),
                ui.layout_columns(
                    ui.div(
                        ui.input_text("event_code_input", "請輸入卡片代碼 (3碼)", placeholder="例如: 101"),
                        ui.output_ui("event_card_display"),
                        # 🔥 新增功能 2: 顯示衝擊預覽
                        ui.output_ui("event_impact_preview"),
                        ui.output_ui("event_apply_btn_area") 
                    ),
                    ui.div(
                        ui.output_ui("event_card_image") 
                    )
                ),
                class_="card"
            )

        elif sub == "rebalance":
            inputs = [ui.input_numeric(f"rb_{k}", f"{ASSET_NAMES[k]} %", 0, min=0, max=100) for k in ASSET_KEYS]
            return ui.div(
                ui.h3(f"⚖️ 資產再平衡 (Year {year})"),
                ui.p("衝擊已發生，請調整您的投資組合。"),
                ui.layout_columns(*inputs),
                ui.output_ui("rebalance_status"), 
                ui.input_action_button("btn_confirm_rebalance", "執行配置 ✅", class_="btn-primary"),
                class_="card", style="background: #ECFDF5; border-left: 5px solid #10B981;"
            )
        return ui.div()

    # --- Jump Logic ---
    @reactive.Effect
    @reactive.event(input.btn_jump_time)
    def _():
        gs = copy.deepcopy(game_state.get())
        current_year = gs["year"]
        rates = gs["dynamic_rates"]
        
        for _ in range(10):
            for k in ASSET_KEYS:
                gs["assets"][k] *= (1 + rates[k])
            current_year += 1
            rec = {'Year': current_year, 'Total': sum(gs["assets"].values()), **gs["assets"]}
            gs["history"].append(rec)
            
        gs["year"] = current_year
        gs["sub_stage"] = "event_input"
        game_state.set(gs)

    # --- Event Logic ---
    @render.ui
    def event_card_image():
        try:
            code = input.event_code_input().strip()
        except:
            code = ""
            
        if code in EVENT_CARDS:
             return ui.img(src=f"images/{code}.png", style="width: 100%; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);")
        else:
             return ui.img(src="images/homepage.png", style="width: 100%; opacity: 0.5;")

    @render.ui
    def event_card_display():
        try:
            code = input.event_code_input().strip()
        except:
            return ui.div()
            
        if code in EVENT_CARDS:
            card = EVENT_CARDS[code]
            return ui.div(
                ui.h3(card['name'], style="color: #1E40AF;"),
                ui.p(card['desc'], style="font-size: 1.1rem;"),
                style="background: #EFF6FF; padding: 15px; border-radius: 8px; margin-top: 10px;"
            )
        return ui.div()

    # 🔥 實作功能 2: 計算並顯示衝擊影響金額
    @render.ui
    def event_impact_preview():
        try:
            code = input.event_code_input().strip()
        except:
            return ui.div()
            
        if code in EVENT_CARDS:
            card = EVENT_CARDS[code]
            assets = game_state.get()['assets']
            
            impact_html = ""
            for k in ASSET_KEYS:
                card_key = KEY_MAPPING[k]
                pct_change = card[card_key]
                
                # 計算實際影響金額
                current_val = assets[k]
                impact_val = current_val * (pct_change / 100)
                
                # 決定顏色 (正為綠，負為紅)
                if pct_change < 0:
                    bg_color = "#FEF2F2"
                    text_color = "#EF4444"
                    sign = "-"
                    arrow = "▼"
                elif pct_change > 0:
                    bg_color = "#ECFDF5"
                    text_color = "#10B981"
                    sign = "+"
                    arrow = "▲"
                else:
                    bg_color = "#F3F4F6"
                    text_color = "#6B7280"
                    sign = ""
                    arrow = "-"

                impact_html += f"""
                <div style="flex: 1; background: {bg_color}; padding: 8px; border-radius: 8px; margin: 0 4px; text-align: center; border: 1px solid {text_color}33;">
                    <div style="font-size: 11px; color: #6B7280;">{ASSET_NAMES[k]}</div>
                    <div style="font-size: 16px; font-weight: bold; color: {text_color};">{arrow} {abs(pct_change)}%</div>
                    <div style="font-size: 12px; font-weight: 600; color: {text_color}; margin-top: 4px;">
                        {sign}${int(abs(impact_val)):,}
                    </div>
                </div>
                """

            return ui.HTML(f"""
                <div style="margin-top: 15px;">
                    <h5 style="color: #4B5563; font-size: 0.9rem;">📉 資產衝擊預覽 (預估損益)</h5>
                    <div style="display: flex; justify-content: space-between; gap: 4px;">
                        {impact_html}
                    </div>
                </div>
            """)
        return ui.div()

    @render.ui
    def event_apply_btn_area():
        try:
            code = input.event_code_input().strip()
        except:
            return ui.div()
            
        if code in EVENT_CARDS:
            return ui.input_action_button("btn_apply_event", "迎接命運衝擊 📉", class_="btn-primary", style="margin-top: 15px; width: 100%;")
        return ui.div()

    @reactive.Effect
    @reactive.event(input.btn_apply_event)
    def _():
        try:
            code = input.event_code_input().strip()
        except: return

        if code not in EVENT_CARDS: return
        
        card = EVENT_CARDS[code]
        gs = copy.deepcopy(game_state.get())
        
        for k in ASSET_KEYS:
            card_key = KEY_MAPPING[k]
            pct = card[card_key]
            gs["assets"][k] = gs["assets"][k] * (1 + pct/100)

        gs["drawn_cards"].append(f"第 {gs['year']} 年: [{code}] {card['name']}")
        rec = gs["history"][-1]
        rec.update(gs["assets"])
        rec['Total'] = sum(gs["assets"].values())
        
        if gs["year"] >= 30:
            ui.update_navs("wizard", selected="finished")
        else:
            gs["sub_stage"] = "rebalance"
            total = sum(gs["assets"].values())
            for k in ASSET_KEYS:
                pct = (gs["assets"][k] / total * 100) if total > 0 else 0
                ui.update_numeric(f"rb_{k}", value=round(pct, 1))
                
        game_state.set(gs)
        ui.update_text("event_code_input", value="")

    # --- Rebalance Logic ---
    @render.ui
    def rebalance_status():
        if game_state.get()["sub_stage"] != "rebalance":
            return ui.div()
            
        try:
            values = []
            for k in ASSET_KEYS:
                val = input[f"rb_{k}"]()
                if val is None: return ui.div()
                values.append(val)
            
            total = sum(values)
            color = "green" if abs(total - 100) < 0.1 else "red"
            return ui.div(f"合計: {total:.1f}%", style=f"color: {color}; font-weight: bold;")
        except KeyError:
            return ui.div()

    @reactive.Effect
    @reactive.event(input.btn_confirm_rebalance)
    def _():
        try:
            values = [input[f"rb_{k}"]() for k in ASSET_KEYS]
            if any(v is None for v in values): return
            
            total = sum(values)
            if abs(total - 100) > 0.1:
                ui.notification_show("比例總和必須為 100%！", type="error")
                return
                
            gs = copy.deepcopy(game_state.get())
            current_total = sum(gs["assets"].values())
            
            for i, k in enumerate(ASSET_KEYS):
                gs["assets"][k] = current_total * (values[i] / 100)
                
            gs["config_history"][f"Year {gs['year']}"] = {k: v for k, v in zip(ASSET_KEYS, values)}
            gs["history"][-1].update(gs["assets"])
            gs["sub_stage"] = "wait_jump"
            game_state.set(gs)
        except KeyError:
            pass

    # --- Charts ---
    @render_widget
    def chart_assets_now():
        assets = game_state.get()['assets']
        df = pd.DataFrame({'Asset': [ASSET_NAMES[k] for k in ASSET_KEYS], 'Value': list(assets.values())})
        fig = px.pie(df, values='Value', names='Asset', color='Asset', color_discrete_map=FINANCE_COLORS, hole=0.5)
        fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=250)
        return fig

    # --- Finished Logic ---
    @render.text
    def final_wealth_text():
        return f"${int(sum(game_state.get()['assets'].values())):,}"
        
    @render.text
    def final_roi_text():
        hist = game_state.get()['history']
        if not hist: return "0%"
        start = hist[0]['Total']
        curr = sum(game_state.get()['assets'].values())
        return f"{(curr - start) / start * 100:+.1f}%"

    @render.ui
    def ig_share_card():
        hist = game_state.get()['history']
        if not hist: return ui.div()
        final_w = sum(game_state.get()['assets'].values())
        roi = (final_w - hist[0]['Total']) / hist[0]['Total'] * 100
        
        if roi < 0:
            title, desc, bg = "💸 破產俱樂部", "黑天鵝來襲！波動性吃掉了你的本金...", "linear-gradient(135deg, #7f1d1d, #ef4444)"
        elif roi < 200:
            title, desc, bg = "🐢 佛系定存族", "這30年你只贏了帳面，卻輸給了真實通膨。", "linear-gradient(135deg, #4b5563, #9ca3af)"
        elif roi < 600:
            title, desc, bg = "💼 理財老手", "表現穩健！這是大多數普通人退休目標。", "linear-gradient(135deg, #059669, #34d399)"
        elif roi < 1200:
            title, desc, bg = "🚀 自由財富號", "眼光精準！你的資產成長速度驚人。", "linear-gradient(135deg, #7c3aed, #a78bfa)"
        else:
            title, desc, bg = "👑 投資界的神", "30年資產翻了10倍以上，巴菲特都要叫你老師！", "linear-gradient(135deg, #b45309, #fbbf24)"

        return ui.HTML(f"""
        <div style="width: 100%; max-width: 380px; margin: 0 auto; background: {bg}; border-radius: 20px; padding: 30px 20px; color: white; box-shadow: 0 10px 25px rgba(0,0,0,0.3); text-align: center; border: 4px solid rgba(255,255,255,0.2);">
            <div style="font-size: 40px; margin-bottom: 10px;">{title.split(' ')[0]}</div>
            <div style="font-size: 28px; font-weight: 800;">{title.split(' ')[1]}</div>
            <div style="font-style: italic; opacity: 0.9; margin: 10px 0;">“{desc}”</div>
            <div style="background: rgba(255,255,255,0.9); color: #1F2937; border-radius: 12px; padding: 10px; margin: 15px 0;">
                <div style="font-size: 12px;">最終資產</div>
                <div style="font-size: 32px; font-weight: 800;">${int(final_w):,}</div>
            </div>
            <div style="font-size: 12px; opacity: 0.8;">玩家: {game_state.get()['user_name']} | ROI: {roi:+.1f}%</div>
        </div>
        """)

    @render_widget
    def chart_history_area():
        df = pd.DataFrame(game_state.get()['history'])
        if df.empty: return None
        df_melt = df.melt(id_vars=['Year', 'Total'], value_vars=ASSET_KEYS, var_name='Asset_Type', value_name='Value')
        df_melt['Asset_Name'] = df_melt['Asset_Type'].map(ASSET_NAMES)
        fig = px.area(df_melt, x="Year", y="Value", color="Asset_Name", color_discrete_map=FINANCE_COLORS)
        return fig

    @render_widget
    def chart_config_history():
        cfg = game_state.get()['config_history']
        if not cfg: return None
        df_c = pd.DataFrame(cfg).T.rename(columns=ASSET_NAMES).reset_index().melt(id_vars='index', var_name='Asset', value_name='Pct')
        fig = px.bar(df_c, x='index', y='Pct', color='Asset', color_discrete_map=FINANCE_COLORS)
        return fig

    @render.ui
    def history_cards_list():
        cards = game_state.get()['drawn_cards']
        if not cards: return ui.p("無事件發生")
        items = [ui.div(c, style="background: #FFF7ED; padding: 10px; border-left: 4px solid #F59E0B; margin-bottom: 5px;") for c in cards]
        return ui.div(*items)

    @reactive.Effect
    @reactive.event(input.save_finish)
    def _():
        gs = game_state.get()
        roi = (sum(gs['assets'].values()) - 1000000) / 1000000 * 100
        
        file_exists = os.path.isfile(CSV_FILE)
        data = {
            '時間': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            '姓名': gs['user_name'],
            '最終資產': int(sum(gs['assets'].values())),
            '報酬率(%)': round(roi, 1),
            '抽卡歷程': " | ".join(gs['drawn_cards']),
            '配置_Year0': str(gs['config_history'].get('Year 0', '')),
            '玩家反饋': input.feedback()
        }
        with open(CSV_FILE, mode='a', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=data.keys())
            if not file_exists: writer.writeheader()
            writer.writerow(data)
        
        ui.notification_show("✅ 數據已儲存！", type="message")

    @reactive.Effect
    @reactive.event(input.restart_game, input.admin_reset_game)
    def _():
        game_state.set({
            "year": 0, "assets": {k: 0 for k in ASSET_KEYS}, "history": [],
            "config_history": {}, "drawn_cards": [], "sub_stage": "wait_jump",
            "dynamic_rates": BASE_RATES.copy(), "user_name": ""
        })
        ui.update_navs("wizard", selected="login")

    @render.download(filename="game_data_records.csv")
    def admin_download_csv():
        if os.path.exists(CSV_FILE):
            return CSV_FILE

# ⚠️ Confirm Static Directory
app_dir = Path(__file__).parent
app = App(app_ui, server, static_assets=app_dir / "www")

if __name__ == "__main__":
    app.run()