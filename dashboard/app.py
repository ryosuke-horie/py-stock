"""
株式取引分析ダッシュボード
Streamlitベースのリアルタイム監視用Webインターフェース
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.data_collector.stock_data_collector import StockDataCollector
from src.technical_analysis.indicators import TechnicalIndicators
from src.technical_analysis.signal_generator import SignalGenerator
from src.risk_management.risk_manager import RiskManager, RiskParameters
from dashboard.utils.dashboard_utils import DashboardUtils
from dashboard.components.watchlist import WatchlistComponent
from dashboard.components.charts import ChartComponent
from dashboard.components.signals import SignalComponent
from dashboard.components.alerts import AlertComponent
from dashboard.components.backtest import BacktestComponent

# ページ設定
st.set_page_config(
    page_title="株式取引分析ダッシュボード",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
        color: #1f77b4;
    }
    
    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    
    .positive {
        color: #00c851;
        font-weight: bold;
    }
    
    .negative {
        color: #ff4444;
        font-weight: bold;
    }
    
    .neutral {
        color: #6c757d;
        font-weight: bold;
    }
    
    .sidebar-section {
        margin: 1rem 0;
        padding: 1rem;
        border: 1px solid #e0e0e0;
        border-radius: 0.5rem;
        background-color: white;
    }
    
    .alert-high {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .alert-medium {
        background-color: #fff3e0;
        border-left: 4px solid #ff9800;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .alert-low {
        background-color: #e8f5e8;
        border-left: 4px solid #4caf50;
        padding: 1rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

class StockDashboard:
    """株式取引分析ダッシュボードのメインクラス"""
    
    def __init__(self):
        """初期化"""
        self.data_collector = StockDataCollector()
        self.utils = DashboardUtils()
        
        # セッション状態の初期化
        if 'watchlist' not in st.session_state:
            st.session_state.watchlist = ['7203.T', '6758.T', '9984.T', 'AAPL', 'MSFT']
        
        if 'alerts' not in st.session_state:
            st.session_state.alerts = []
        
        if 'last_update' not in st.session_state:
            st.session_state.last_update = datetime.now()
            
        if 'auto_refresh' not in st.session_state:
            st.session_state.auto_refresh = False
            
        if 'selected_symbol' not in st.session_state:
            st.session_state.selected_symbol = '7203.T'
    
    def run(self):
        """ダッシュボード実行"""
        # メインヘッダー
        st.markdown('<h1 class="main-header">📊 株式取引分析ダッシュボード</h1>', unsafe_allow_html=True)
        
        # サイドバー設定
        self.setup_sidebar()
        
        # メインコンテンツ
        main_tab1, main_tab2, main_tab3, main_tab4, main_tab5 = st.tabs([
            "🏠 概要", "📈 チャート分析", "🎯 シグナル", "🚨 アラート", "📊 バックテスト"
        ])
        
        with main_tab1:
            self.show_overview()
        
        with main_tab2:
            self.show_chart_analysis()
        
        with main_tab3:
            self.show_signals()
        
        with main_tab4:
            self.show_alerts()
        
        with main_tab5:
            self.show_backtest()
        
        # 自動更新
        if st.session_state.auto_refresh:
            time.sleep(30)  # 30秒間隔で更新
            st.rerun()
    
    def setup_sidebar(self):
        """サイドバー設定"""
        st.sidebar.title("⚙️ 設定")
        
        # 自動更新設定
        st.sidebar.markdown("### 🔄 自動更新")
        st.session_state.auto_refresh = st.sidebar.checkbox(
            "自動更新を有効にする（30秒間隔）",
            value=st.session_state.auto_refresh
        )
        
        # 手動更新ボタン
        if st.sidebar.button("🔄 今すぐ更新"):
            st.session_state.last_update = datetime.now()
            st.rerun()
        
        # 最終更新時刻表示
        st.sidebar.write(f"最終更新: {st.session_state.last_update.strftime('%H:%M:%S')}")
        
        st.sidebar.markdown("---")
        
        # ウォッチリスト管理
        st.sidebar.markdown("### 📋 ウォッチリスト")
        
        # 新しい銘柄追加
        new_symbol = st.sidebar.text_input("銘柄コードを追加:")
        if st.sidebar.button("➕ 追加"):
            if new_symbol and new_symbol not in st.session_state.watchlist:
                st.session_state.watchlist.append(new_symbol.upper())
                st.rerun()
        
        # ウォッチリスト表示と削除
        for i, symbol in enumerate(st.session_state.watchlist):
            col1, col2 = st.sidebar.columns([3, 1])
            with col1:
                st.write(symbol)
            with col2:
                if st.button("❌", key=f"del_{i}"):
                    st.session_state.watchlist.remove(symbol)
                    st.rerun()
        
        st.sidebar.markdown("---")
        
        # 分析対象銘柄選択
        st.sidebar.markdown("### 🎯 分析対象")
        st.session_state.selected_symbol = st.sidebar.selectbox(
            "詳細分析する銘柄:",
            st.session_state.watchlist,
            index=st.session_state.watchlist.index(st.session_state.selected_symbol) 
            if st.session_state.selected_symbol in st.session_state.watchlist else 0
        )
        
        # データ取得期間設定
        st.sidebar.markdown("### 📅 データ設定")
        period = st.sidebar.selectbox(
            "取得期間:",
            ["1d", "5d", "1mo", "3mo", "6mo", "1y"],
            index=2
        )
        
        interval = st.sidebar.selectbox(
            "データ間隔:",
            ["1m", "5m", "15m", "30m", "1h", "1d"],
            index=4
        )
        
        st.session_state.period = period
        st.session_state.interval = interval
        
        # システム情報
        st.sidebar.markdown("---")
        st.sidebar.markdown("### ℹ️ システム情報")
        st.sidebar.info(f"""
        **ウォッチリスト**: {len(st.session_state.watchlist)}銘柄  
        **アクティブアラート**: {len([a for a in st.session_state.alerts if a.get('active', True)])}件  
        **分析対象**: {st.session_state.selected_symbol}  
        **データ期間**: {period} ({interval}間隔)
        """)
    
    def show_overview(self):
        """概要ページ表示"""
        st.header("📊 市場概要")
        
        # ウォッチリスト価格表示
        watchlist_component = WatchlistComponent(self.data_collector)
        watchlist_component.display(st.session_state.watchlist)
        
        # 市場サマリー
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📈 ウォッチリスト価格動向")
            self.show_watchlist_chart()
        
        with col2:
            st.subheader("🎯 今日のシグナル")
            self.show_daily_signals()
    
    def show_chart_analysis(self):
        """チャート分析ページ表示"""
        st.header(f"📈 チャート分析: {st.session_state.selected_symbol}")
        
        chart_component = ChartComponent(self.data_collector)
        chart_component.display(
            st.session_state.selected_symbol,
            st.session_state.period,
            st.session_state.interval
        )
    
    def show_signals(self):
        """シグナルページ表示"""
        st.header("🎯 売買シグナル分析")
        
        signal_component = SignalComponent(self.data_collector)
        signal_component.display(
            st.session_state.selected_symbol,
            st.session_state.period,
            st.session_state.interval
        )
    
    def show_alerts(self):
        """アラートページ表示"""
        st.header("🚨 アラート管理")
        
        alert_component = AlertComponent()
        alert_component.display()
    
    def show_backtest(self):
        """バックテストページ表示"""
        st.header("📊 バックテスト結果")
        
        backtest_component = BacktestComponent(self.data_collector)
        backtest_component.display(st.session_state.selected_symbol)
    
    def show_watchlist_chart(self):
        """ウォッチリストチャート表示"""
        try:
            # 簡易チャート作成
            fig = go.Figure()
            
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
            
            for i, symbol in enumerate(st.session_state.watchlist[:5]):  # 最大5銘柄
                try:
                    data = self.data_collector.get_stock_data(symbol, period="1d", interval="5m")
                    if data is not None and not data.empty:
                        # 正規化（開始価格を100として）
                        normalized_prices = (data['close'] / data['close'].iloc[0]) * 100
                        
                        fig.add_trace(go.Scatter(
                            x=data['timestamp'],
                            y=normalized_prices,
                            mode='lines',
                            name=symbol,
                            line=dict(color=colors[i % len(colors)]),
                            hovertemplate=f"{symbol}<br>価格: %{{y:.2f}}<br>時刻: %{{x}}<extra></extra>"
                        ))
                except Exception as e:
                    st.warning(f"データ取得エラー ({symbol}): {e}")
                    continue
            
            fig.update_layout(
                title="ウォッチリスト価格動向（正規化済み）",
                xaxis_title="時刻",
                yaxis_title="相対価格 (開始時=100)",
                height=400,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"チャート作成エラー: {e}")
    
    def show_daily_signals(self):
        """本日のシグナル表示"""
        try:
            signals_data = []
            
            for symbol in st.session_state.watchlist:
                try:
                    data = self.data_collector.get_stock_data(symbol, period="1d", interval="5m")
                    if data is not None and not data.empty:
                        signal_generator = SignalGenerator(data)
                        signals = signal_generator.generate_signals(data)
                        
                        if signals is not None and not signals.empty:
                            latest_signal = signals.iloc[-1]
                            signals_data.append({
                                '銘柄': symbol,
                                'シグナル': latest_signal['signal'],
                                '強度': f"{latest_signal['strength']:.1f}",
                                '信頼度': f"{latest_signal['confidence']:.2f}",
                                '時刻': latest_signal['timestamp'].strftime('%H:%M')
                            })
                except Exception:
                    continue
            
            if signals_data:
                df = pd.DataFrame(signals_data)
                
                # シグナル別の色分け
                def color_signal(val):
                    if val == 'BUY':
                        return 'background-color: #e8f5e8; color: #2e7d32'
                    elif val == 'SELL':
                        return 'background-color: #ffebee; color: #c62828'
                    else:
                        return 'background-color: #f5f5f5; color: #666'
                
                styled_df = df.style.applymap(color_signal, subset=['シグナル'])
                st.dataframe(styled_df, use_container_width=True)
            else:
                st.info("シグナルデータがありません")
                
        except Exception as e:
            st.error(f"シグナル取得エラー: {e}")


def main():
    """メイン実行関数"""
    try:
        dashboard = StockDashboard()
        dashboard.run()
    except Exception as e:
        st.error(f"ダッシュボード実行エラー: {e}")
        st.exception(e)


if __name__ == "__main__":
    main()