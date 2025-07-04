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
from src.data_collector.symbol_manager import SymbolManager
from src.technical_analysis.indicators import TechnicalIndicators
from src.technical_analysis.signal_generator import SignalGenerator
from src.risk_management.risk_manager import RiskManager, RiskParameters
from dashboard.utils.dashboard_utils import DashboardUtils
from dashboard.components.watchlist import WatchlistComponent
from dashboard.components.charts import ChartComponent
from dashboard.components.signals import SignalComponent
from dashboard.components.alerts import AlertComponent
from dashboard.components.intelligent_alerts import IntelligentAlertComponent
from dashboard.components.backtest import BacktestComponent
from dashboard.components.market_environment import render_market_environment_tab
from dashboard.components.tax_calculation import render_tax_calculation_tab
from dashboard.components.fundamental_analysis import render_fundamental_analysis_tab
from dashboard.components.investment_story import render_investment_story_tab
from dashboard.components.portfolio_analysis import render_portfolio_analysis_tab
from dashboard.components.performance_tracking import render_performance_tracking_tab
from dashboard.components.education_glossary import render_education_glossary_tab
from dashboard.components.education_simulation import render_education_simulation_tab
from dashboard.components.education_cases import render_education_cases_tab
from dashboard.components.education_tutorial import render_education_tutorial_tab
from src.data_collector.watchlist_storage import WatchlistStorage

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
        self.symbol_manager = SymbolManager()
        
        # ウォッチリストストレージ初期化
        self.watchlist_storage = WatchlistStorage()
        
        # セッション状態の初期化
        self._initialize_session_state()
        
        # データ移行処理（初回のみ）
        self._migrate_watchlist_if_needed()
    
    def _initialize_session_state(self):
        """セッション状態の初期化"""
        if 'alerts' not in st.session_state:
            st.session_state.alerts = []
        
        if 'last_update' not in st.session_state:
            st.session_state.last_update = datetime.now()
            
        if 'auto_refresh' not in st.session_state:
            st.session_state.auto_refresh = False
        
        # ウォッチリストをDBから取得
        db_watchlist = self.watchlist_storage.get_symbols()
        if db_watchlist:
            st.session_state.watchlist = db_watchlist
        else:
            # DBが空の場合は空のウォッチリスト
            st.session_state.watchlist = []
        
        # 選択銘柄をウォッチリストの最初に設定
        if 'selected_symbol' not in st.session_state:
            st.session_state.selected_symbol = st.session_state.watchlist[0] if st.session_state.watchlist else None
    
    def _migrate_watchlist_if_needed(self):
        """必要に応じてウォッチリストを移行"""
        # DBが空でセッション状態にデフォルト値がある場合、移行を実行
        db_symbols = self.watchlist_storage.get_symbols()
        if not db_symbols and st.session_state.watchlist:
            self.watchlist_storage.migrate_from_session(st.session_state.watchlist)
    
    def run(self):
        """ダッシュボード実行"""
        # メインヘッダー
        st.markdown('<h1 class="main-header">📊 株式取引分析ダッシュボード</h1>', unsafe_allow_html=True)
        
        # サイドバー設定
        self.setup_sidebar()
        
        # メインコンテンツ
        main_tab1, main_tab2, main_tab3, main_tab4, main_tab5, main_tab6, main_tab7, main_tab8, main_tab9, main_tab10, main_tab11, main_tab12 = st.tabs([
            "🏠 概要", "🌍 市場環境", "📈 チャート分析", "🎯 シグナル", "🚨 アラート", "📊 バックテスト", "💰 税務・コスト", "📊 ファンダメンタルズ", "⚖️ ポートフォリオ", "📖 投資ストーリー", "📈 パフォーマンス追跡", "🎓 教育・学習"
        ])
        
        with main_tab1:
            self.show_overview()
        
        with main_tab2:
            render_market_environment_tab()
        
        with main_tab3:
            self.show_chart_analysis()
        
        with main_tab4:
            self.show_signals()
        
        with main_tab5:
            self.show_alerts()
        
        with main_tab6:
            self.show_backtest()
        
        with main_tab7:
            render_tax_calculation_tab()
        
        with main_tab8:
            render_fundamental_analysis_tab()
        
        with main_tab9:
            render_portfolio_analysis_tab()
        
        with main_tab10:
            render_investment_story_tab()
        
        with main_tab11:
            render_performance_tracking_tab()
        
        with main_tab12:
            self.show_education()
        
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
        new_company_name = st.sidebar.text_input(
            "会社名（任意）:",
            help="会社名を入力すると、ウォッチリストに表示されます。空欄の場合は自動取得されます。"
        )
        if st.sidebar.button("➕ 追加"):
            if new_symbol and new_symbol not in st.session_state.watchlist:
                # DBに追加（会社名も含む）
                if self.watchlist_storage.add_symbol(new_symbol.upper(), new_company_name.strip() if new_company_name else None):
                    # 成功した場合、セッション状態も更新
                    st.session_state.watchlist = self.watchlist_storage.get_symbols()
                    display_name = f"{new_symbol.upper()}" + (f" ({new_company_name.strip()})" if new_company_name.strip() else "")
                    st.success(f"銘柄を追加しました: {display_name}")
                    st.rerun()
                else:
                    st.error(f"銘柄の追加に失敗しました: {new_symbol}")
        
        # ウォッチリスト表示と削除
        watchlist_items = self.watchlist_storage.get_watchlist_items()
        for i, item in enumerate(watchlist_items):
            col1, col2 = st.sidebar.columns([3, 1])
            with col1:
                # 銘柄コード + 会社名表示
                display_name = item.symbol
                if item.name and item.name != "N/A":
                    display_name = f"{item.symbol} ({item.name})"
                st.write(display_name)
            with col2:
                if st.button("❌", key=f"del_{i}"):
                    # DBから削除
                    if self.watchlist_storage.remove_symbol(item.symbol):
                        # 成功した場合、セッション状態も更新
                        st.session_state.watchlist = self.watchlist_storage.get_symbols()
                        st.success(f"銘柄を削除しました: {display_name}")
                        st.rerun()
                    else:
                        st.error(f"銘柄の削除に失敗しました: {item.symbol}")
        
        st.sidebar.markdown("---")
        
        # 分析対象銘柄選択
        st.sidebar.markdown("### 🎯 分析対象銘柄")
        if st.session_state.watchlist:
            st.session_state.selected_symbol = st.sidebar.selectbox(
                "チャート・シグナル分析対象:",
                st.session_state.watchlist,
                index=st.session_state.watchlist.index(st.session_state.selected_symbol) 
                if st.session_state.selected_symbol in st.session_state.watchlist else 0
            )
        else:
            st.sidebar.info("📋 上記のウォッチリストに銘柄を追加すると、詳細な分析が可能になります。")
        
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
        
        # バックアップ管理
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 💾 バックアップ")
        
        # バックアップ統計表示
        backup_info = self.watchlist_storage.get_backup_info()
        if backup_info:
            st.sidebar.info(f"""
            **バックアップ数**: {backup_info.get('total_count', 0)}個  
            **使用容量**: {backup_info.get('disk_usage_mb', 0)}MB  
            **最新**: {backup_info.get('latest_backup', 'なし')[:10] if backup_info.get('latest_backup') else 'なし'}
            """)
        
        # 手動バックアップボタン
        if st.sidebar.button("💾 今すぐバックアップ"):
            with st.spinner("バックアップ作成中..."):
                backup_path = self.watchlist_storage.create_manual_backup()
                if backup_path:
                    st.sidebar.success("✅ バックアップ作成完了")
                else:
                    st.sidebar.error("❌ バックアップ作成失敗")
        
        # バックアップ一覧表示（展開可能）
        with st.sidebar.expander("📋 バックアップ一覧", expanded=False):
            backups = self.watchlist_storage.list_available_backups()
            if backups:
                for backup in backups[:5]:  # 最新5件表示
                    backup_time = backup.created_at.strftime("%m/%d %H:%M")
                    backup_type_icon = {
                        'auto': '🔄',
                        'manual': '👤', 
                        'before_operation': '⚠️'
                    }.get(backup.backup_type, '📁')
                    
                    st.sidebar.text(f"{backup_type_icon} {backup_time}")
                    st.sidebar.text(f"  {backup.operation_context or backup.backup_type}")
            else:
                st.sidebar.text("バックアップがありません")
        
        # システム情報
        st.sidebar.markdown("---")
        st.sidebar.markdown("### ℹ️ 現在の設定状況")
        
        # 選択された銘柄の表示改善
        selected_display = st.session_state.selected_symbol if st.session_state.selected_symbol else "未選択"
        
        st.sidebar.info(f"""
        **📋 ウォッチリスト**: {len(st.session_state.watchlist)}銘柄  
        **🚨 アクティブアラート**: {len([a for a in st.session_state.alerts if a.get('active', True)])}件  
        **🎯 分析対象銘柄**: {selected_display}  
        **📅 データ期間**: {period} ({interval}間隔)
        
        💡 **ヒント**: 各タブのサイドバーで個別に分析設定が可能です
        """)
    
    def show_overview(self):
        """概要ページ表示"""
        st.header("📊 市場概要")
        
        # ウォッチリスト価格表示
        watchlist_component = WatchlistComponent(self.data_collector, self.watchlist_storage)
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
        
        # インテリジェントアラートと従来アラートをタブで切り替え
        alert_mode = st.radio(
            "アラートモード",
            ["インテリジェントアラート（推奨）", "従来のアラート"],
            horizontal=True
        )
        
        if alert_mode == "インテリジェントアラート（推奨）":
            intelligent_alert_component = IntelligentAlertComponent()
            intelligent_alert_component.display()
        else:
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
            
            # WatchlistStorageからカスタム会社名を含む詳細情報を取得
            watchlist_items = self.watchlist_storage.get_watchlist_items()
            symbol_to_name = {item.symbol: item.name for item in watchlist_items}
            
            for i, symbol in enumerate(st.session_state.watchlist[:5]):  # 最大5銘柄
                try:
                    data = self.data_collector.get_stock_data(symbol, period="1d", interval="5m")
                    if data is not None and not data.empty:
                        # 正規化（開始価格を100として）
                        normalized_prices = (data['close'] / data['close'].iloc[0]) * 100
                        
                        # カスタム会社名を優先して使用、なければSymbolManagerから取得
                        custom_name = symbol_to_name.get(symbol)
                        if custom_name and custom_name != "N/A":
                            display_name = f"{symbol} ({custom_name})"
                        else:
                            # フォールバック: SymbolManagerから取得
                            symbol_info = self.symbol_manager.get_symbol_info(symbol)
                            if symbol_info['name'] != 'N/A':
                                display_name = f"{symbol} ({symbol_info['name']})"
                            else:
                                display_name = symbol
                        
                        fig.add_trace(go.Scatter(
                            x=data['timestamp'],
                            y=normalized_prices,
                            mode='lines',
                            name=display_name,
                            line=dict(color=colors[i % len(colors)]),
                            hovertemplate=f"{display_name}<br>価格: %{{y:.2f}}<br>時刻: %{{x}}<extra></extra>"
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
    
    def show_education(self):
        """教育・学習ページ表示"""
        st.header("🎓 教育・学習支援")
        
        # 教育機能のサブタブ
        edu_tab1, edu_tab2, edu_tab3, edu_tab4 = st.tabs([
            "📚 投資用語集", "🎮 練習モード", "📖 事例学習", "🎓 チュートリアル"
        ])
        
        with edu_tab1:
            render_education_glossary_tab()
        
        with edu_tab2:
            render_education_simulation_tab()
        
        with edu_tab3:
            render_education_cases_tab()
        
        with edu_tab4:
            render_education_tutorial_tab()


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