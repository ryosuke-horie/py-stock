"""
シグナル発生履歴とパフォーマンス表示コンポーネント
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.technical_analysis.signal_generator import SignalGenerator
from ..data.signal_storage import SignalStorage
from ..utils.dashboard_utils import DashboardUtils


class SignalComponent:
    """シグナル表示コンポーネント"""
    
    def __init__(self, data_collector):
        """初期化"""
        self.data_collector = data_collector
        self.signal_storage = SignalStorage()
        self.utils = DashboardUtils()
        
        # セッション状態初期化
        if 'signal_monitoring' not in st.session_state:
            st.session_state.signal_monitoring = False
        if 'virtual_trading' not in st.session_state:
            st.session_state.virtual_trading = False
    
    def display(self, symbol: str, period: str = "1d", interval: str = "5m"):
        """シグナル分析表示"""
        st.header(f"🎯 シグナル分析: {symbol}")
        
        # 制御パネル
        self._display_control_panel()
        
        # タブ構成
        signal_tab1, signal_tab2, signal_tab3, signal_tab4 = st.tabs([
            "📊 リアルタイムシグナル", "📈 シグナル履歴", "🎯 パフォーマンス統計", "🎲 仮想トレード"
        ])
        
        with signal_tab1:
            self._display_realtime_signals(symbol, period, interval)
        
        with signal_tab2:
            self._display_signal_history(symbol)
        
        with signal_tab3:
            self._display_performance_stats(symbol)
        
        with signal_tab4:
            self._display_virtual_trading(symbol)
    
    def _display_control_panel(self):
        """制御パネル表示"""
        st.markdown("### ⚙️ シグナル監視設定")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.session_state.signal_monitoring = st.checkbox(
                "シグナル監視開始",
                value=st.session_state.signal_monitoring,
                help="選択された銘柄のシグナルをリアルタイム監視"
            )
        
        with col2:
            st.session_state.virtual_trading = st.checkbox(
                "仮想トレード有効",
                value=st.session_state.virtual_trading,
                help="シグナルに基づく仮想トレードを実行"
            )
        
        with col3:
            signal_threshold = st.slider(
                "シグナル強度閾値",
                min_value=0.0,
                max_value=100.0,
                value=60.0,
                step=5.0,
                help="この値以上の強度のシグナルのみ表示"
            )
            st.session_state.signal_threshold = signal_threshold
        
        with col4:
            confidence_threshold = st.slider(
                "信頼度閾値", 
                min_value=0.0,
                max_value=1.0,
                value=0.6,
                step=0.1,
                help="この値以上の信頼度のシグナルのみ表示"
            )
            st.session_state.confidence_threshold = confidence_threshold
        
        # 監視対象銘柄設定
        if st.session_state.signal_monitoring:
            st.info("🔴 シグナル監視中... ウォッチリストの銘柄を監視しています")
    
    def _display_realtime_signals(self, symbol: str, period: str, interval: str):
        """リアルタイムシグナル表示"""
        st.subheader(f"📊 {symbol} - 現在のシグナル状況")
        
        try:
            # データ取得
            with st.spinner("最新データを取得中..."):
                data = self.data_collector.get_stock_data(symbol, period=period, interval=interval)
            
            if data is None or data.empty:
                st.error("データを取得できませんでした")
                return
            
            # シグナル生成
            signal_generator = SignalGenerator(data)
            signals = signal_generator.generate_signals()
            
            if not signals:
                st.warning("シグナルが生成されませんでした")
                return
            
            # 最新シグナル取得
            latest_signal = signals[-1]
            current_price = data['close'].iloc[-1]
            
            # シグナルデータ準備
            signal_data = {
                'symbol': symbol,
                'signal': latest_signal.signal_type.value,
                'strength': latest_signal.strength,
                'confidence': latest_signal.confidence,
                'entry_price': latest_signal.price,
                'stop_loss': latest_signal.stop_loss,
                'take_profit': latest_signal.take_profit,
                'timestamp': latest_signal.timestamp,
                'active_rules': list(latest_signal.conditions_met.keys()),
                'volume': data['volume'].iloc[-1] if 'volume' in data.columns else 0
            }
            
            # 閾値チェック
            if (signal_data['strength'] >= st.session_state.signal_threshold and 
                signal_data['confidence'] >= st.session_state.confidence_threshold):
                
                # シグナル保存（監視モード時）
                if st.session_state.signal_monitoring:
                    self._save_signal_if_new(signal_data)
            
            # シグナル表示
            self._display_current_signal(signal_data, current_price)
            
            # シグナル詳細
            self._display_signal_details(latest_signal, data)
            
            # シグナル強度履歴チャート（TradingSignalリストをDataFrameに変換）
            signals_df = self._convert_signals_to_dataframe(signals)
            if not signals_df.empty:
                self._display_signal_strength_chart(signals_df, symbol)
        
        except Exception as e:
            st.error(f"シグナル分析エラー: {e}")
    
    def _display_current_signal(self, signal_data: Dict[str, Any], current_price: float):
        """現在のシグナル表示"""
        col1, col2, col3, col4 = st.columns(4)
        
        # シグナル色判定
        signal_color = {
            'BUY': '🟢',
            'SELL': '🔴', 
            'HOLD': '🟡'
        }.get(signal_data['signal'], '⚪')
        
        with col1:
            st.metric(
                "シグナル",
                f"{signal_color} {signal_data['signal']}",
                delta=f"強度: {signal_data['strength']:.1f}"
            )
        
        with col2:
            st.metric(
                "現在価格",
                f"¥{current_price:.2f}",
                delta=f"信頼度: {signal_data['confidence']:.2f}"
            )
        
        with col3:
            if signal_data['entry_price']:
                entry_diff = ((current_price - signal_data['entry_price']) / signal_data['entry_price']) * 100
                st.metric(
                    "推奨エントリー",
                    f"¥{signal_data['entry_price']:.2f}",
                    delta=f"{entry_diff:+.2f}%"
                )
            else:
                st.metric("推奨エントリー", "N/A")
        
        with col4:
            signal_time = signal_data['timestamp']
            time_diff = datetime.now() - signal_time
            st.metric(
                "シグナル時刻",
                signal_time.strftime('%H:%M:%S'),
                delta=f"{int(time_diff.total_seconds()//60)}分前"
            )
        
        # アクションアラート
        if signal_data['signal'] in ['BUY', 'SELL']:
            if (signal_data['strength'] >= 80 and signal_data['confidence'] >= 0.8):
                st.success(f"🔥 強力な{signal_data['signal']}シグナル発生！ 即座のアクションを検討してください。")
            elif (signal_data['strength'] >= 70 and signal_data['confidence'] >= 0.7):
                st.info(f"📈 {signal_data['signal']}シグナル発生。慎重に検討してください。")
    
    def _display_signal_details(self, latest_signal, data: pd.DataFrame):
        """シグナル詳細表示"""
        st.markdown("### 📋 シグナル詳細")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**有効ルール:**")
            # TradingSignalオブジェクトのconditions_metを使用
            active_rules = [rule for rule, active in latest_signal.conditions_met.items() if active]
            
            if active_rules:
                for rule in active_rules:
                    st.success(f"✅ {rule}")
            else:
                st.info("アクティブなルールがありません")
        
        with col2:
            st.markdown("**市場状況:**")
            current_price = data['close'].iloc[-1]
            
            # 移動平均との比較
            if len(data) >= 20:
                sma_20 = data['close'].rolling(20).mean().iloc[-1]
                sma_diff = ((current_price - sma_20) / sma_20) * 100
                trend_emoji = "📈" if sma_diff > 0 else "📉" if sma_diff < 0 else "➡️"
                st.info(f"{trend_emoji} SMA20比: {sma_diff:+.2f}%")
            
            # 出来高比較
            if 'volume' in data.columns and len(data) >= 5:
                current_volume = data['volume'].iloc[-1]
                avg_volume = data['volume'].rolling(5).mean().iloc[-1]
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
                volume_emoji = "🔊" if volume_ratio > 1.5 else "🔉" if volume_ratio > 0.8 else "🔇"
                st.info(f"{volume_emoji} 出来高比: {volume_ratio:.2f}x")
        
        # エントリー・エグジット戦略
        if latest_signal.get('entry_price') and latest_signal.get('stop_loss'):
            st.markdown("### 🎯 エントリー・エグジット戦略")
            
            entry_price = latest_signal['entry_price']
            stop_loss = latest_signal['stop_loss']
            take_profits = latest_signal.get('take_profit', [])
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.info(f"**エントリー:** ¥{entry_price:.2f}")
            
            with col2:
                risk_pct = abs((entry_price - stop_loss) / entry_price) * 100
                st.error(f"**ストップロス:** ¥{stop_loss:.2f} (-{risk_pct:.1f}%)")
            
            with col3:
                if take_profits:
                    st.success(f"**テイクプロフィット:** ¥{take_profits[0]:.2f}")
                    if len(take_profits) > 1:
                        st.success(f"**TP2:** ¥{take_profits[1]:.2f}")
    
    def _display_signal_strength_chart(self, signals: pd.DataFrame, symbol: str):
        """シグナル強度履歴チャート"""
        st.markdown("### 📊 シグナル強度履歴")
        
        if len(signals) < 10:
            st.info("履歴データが不十分です（最低10件必要）")
            return
        
        # 最新50件のみ表示
        recent_signals = signals.tail(50)
        
        fig = make_subplots(
            rows=2, cols=1,
            row_heights=[0.7, 0.3],
            vertical_spacing=0.1,
            subplot_titles=["シグナル強度", "信頼度"]
        )
        
        # シグナル別色分け
        colors = {
            'BUY': '#00c851',
            'SELL': '#ff4444', 
            'HOLD': '#ffc107'
        }
        
        # シグナル強度プロット
        for signal_type in recent_signals['signal'].unique():
            mask = recent_signals['signal'] == signal_type
            signal_data = recent_signals[mask]
            
            fig.add_trace(
                go.Scatter(
                    x=signal_data['timestamp'],
                    y=signal_data['strength'],
                    mode='markers+lines',
                    name=f'{signal_type} シグナル',
                    marker=dict(
                        color=colors.get(signal_type, '#666'),
                        size=8,
                        opacity=0.8
                    ),
                    line=dict(color=colors.get(signal_type, '#666'), width=1)
                ),
                row=1, col=1
            )
        
        # 信頼度プロット
        fig.add_trace(
            go.Scatter(
                x=recent_signals['timestamp'],
                y=recent_signals['confidence'],
                mode='lines',
                name='信頼度',
                line=dict(color='blue', width=2),
                fill='tonexty',
                fillcolor='rgba(0,100,255,0.1)'
            ),
            row=2, col=1
        )
        
        # 閾値線
        fig.add_hline(
            y=st.session_state.signal_threshold,
            line_dash="dash",
            line_color="red",
            annotation_text="強度閾値",
            row=1, col=1
        )
        
        fig.add_hline(
            y=st.session_state.confidence_threshold,
            line_dash="dash", 
            line_color="orange",
            annotation_text="信頼度閾値",
            row=2, col=1
        )
        
        fig.update_layout(
            height=500,
            showlegend=True,
            title=f"{symbol} - シグナル履歴 (最新50件)"
        )
        
        fig.update_yaxes(title_text="強度", range=[0, 100], row=1, col=1)
        fig.update_yaxes(title_text="信頼度", range=[0, 1], row=2, col=1)
        
        st.plotly_chart(fig, use_container_width=True)
    
    def _display_signal_history(self, symbol: str):
        """シグナル履歴表示"""
        st.subheader("📈 シグナル発生履歴")
        
        # フィルター設定
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            days_back = st.selectbox(
                "表示期間",
                [7, 14, 30, 60, 90],
                index=2,
                format_func=lambda x: f"過去{x}日"
            )
        
        with col2:
            signal_filter = st.selectbox(
                "シグナルタイプ",
                ["ALL", "BUY", "SELL", "HOLD"],
                index=0
            )
        
        with col3:
            min_strength = st.slider(
                "最低強度",
                0.0, 100.0, 50.0, 5.0
            )
        
        with col4:
            min_confidence = st.slider(
                "最低信頼度",
                0.0, 1.0, 0.5, 0.1
            )
        
        # データ取得
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        signals_df = self.signal_storage.get_signals(
            symbol=symbol,
            signal_type=None if signal_filter == "ALL" else signal_filter,
            start_date=start_date,
            end_date=end_date
        )
        
        if signals_df.empty:
            st.info("指定期間内にシグナルデータがありません")
            return
        
        # フィルタリング
        filtered_df = signals_df[
            (signals_df['strength'] >= min_strength) &
            (signals_df['confidence'] >= min_confidence)
        ]
        
        if filtered_df.empty:
            st.warning("フィルター条件に一致するシグナルがありません")
            return
        
        # シグナル履歴テーブル
        self._display_signals_table(filtered_df)
        
        # シグナル統計
        self._display_signal_statistics(filtered_df, days_back)
    
    def _display_signals_table(self, signals_df: pd.DataFrame):
        """シグナルテーブル表示"""
        # 表示用データフレーム作成
        display_df = signals_df.copy()
        display_df['日時'] = display_df['timestamp'].dt.strftime('%m/%d %H:%M')
        display_df['シグナル'] = display_df['signal_type']
        display_df['強度'] = display_df['strength'].round(1)
        display_df['信頼度'] = display_df['confidence'].round(2)
        display_df['エントリー価格'] = display_df['entry_price'].round(2)
        
        # 有効ルール数計算
        display_df['有効ルール数'] = display_df['active_rules'].apply(len)
        
        # 表示カラム選択
        show_columns = ['日時', 'シグナル', '強度', '信頼度', 'エントリー価格', '有効ルール数']
        table_df = display_df[show_columns]
        
        # スタイル適用
        def style_signal(val):
            colors = {
                'BUY': 'background-color: #e8f5e8; color: #2e7d32',
                'SELL': 'background-color: #ffebee; color: #c62828',
                'HOLD': 'background-color: #fff3e0; color: #f57c00'
            }
            return colors.get(val, '')
        
        def style_strength(val):
            if val >= 80:
                return 'background-color: #e8f5e8; color: #2e7d32; font-weight: bold'
            elif val >= 60:
                return 'background-color: #fff3e0; color: #f57c00'
            else:
                return 'background-color: #ffebee; color: #c62828'
        
        styled_df = table_df.style.applymap(style_signal, subset=['シグナル']) \
                                  .applymap(style_strength, subset=['強度'])
        
        st.dataframe(styled_df, use_container_width=True, height=400)
        
        # 詳細表示（選択行）
        if len(signals_df) > 0:
            selected_idx = st.selectbox(
                "詳細表示するシグナルを選択:",
                range(len(signals_df)),
                format_func=lambda i: f"{signals_df.iloc[i]['timestamp'].strftime('%m/%d %H:%M')} - {signals_df.iloc[i]['signal_type']}"
            )
            
            if selected_idx is not None:
                self._display_signal_detail_popup(signals_df.iloc[selected_idx])
    
    def _display_signal_detail_popup(self, signal_row: pd.Series):
        """シグナル詳細ポップアップ"""
        with st.expander(f"📋 シグナル詳細: {signal_row['timestamp'].strftime('%Y/%m/%d %H:%M')}", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("シグナル", signal_row['signal_type'])
                st.metric("強度", f"{signal_row['strength']:.1f}")
                st.metric("信頼度", f"{signal_row['confidence']:.2f}")
            
            with col2:
                if not pd.isna(signal_row['entry_price']):
                    st.metric("エントリー価格", f"¥{signal_row['entry_price']:.2f}")
                if not pd.isna(signal_row['stop_loss']):
                    st.metric("ストップロス", f"¥{signal_row['stop_loss']:.2f}")
                st.metric("出来高", f"{signal_row['volume']:,.0f}")
            
            with col3:
                st.metric("市場状況", signal_row.get('market_condition', 'N/A'))
                
                # テイクプロフィット表示
                tp_levels = []
                for tp_col in ['take_profit_1', 'take_profit_2', 'take_profit_3']:
                    if tp_col in signal_row and not pd.isna(signal_row[tp_col]):
                        tp_levels.append(signal_row[tp_col])
                
                if tp_levels:
                    tp_text = ", ".join([f"¥{tp:.2f}" for tp in tp_levels])
                    st.info(f"TP: {tp_text}")
            
            # 有効ルール表示
            if signal_row['active_rules']:
                st.markdown("**有効ルール:**")
                for rule in signal_row['active_rules']:
                    st.success(f"✅ {rule}")
    
    def _display_signal_statistics(self, signals_df: pd.DataFrame, days: int):
        """シグナル統計表示"""
        st.markdown("### 📊 シグナル統計")
        
        # 基本統計
        total_signals = len(signals_df)
        signal_counts = signals_df['signal_type'].value_counts()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("総シグナル数", total_signals)
        
        with col2:
            buy_count = signal_counts.get('BUY', 0)
            buy_pct = (buy_count / total_signals * 100) if total_signals > 0 else 0
            st.metric("買いシグナル", f"{buy_count} ({buy_pct:.1f}%)")
        
        with col3:
            sell_count = signal_counts.get('SELL', 0) 
            sell_pct = (sell_count / total_signals * 100) if total_signals > 0 else 0
            st.metric("売りシグナル", f"{sell_count} ({sell_pct:.1f}%)")
        
        with col4:
            avg_strength = signals_df['strength'].mean()
            st.metric("平均強度", f"{avg_strength:.1f}")
        
        # シグナル分布チャート
        col1, col2 = st.columns(2)
        
        with col1:
            # シグナルタイプ分布
            fig_pie = px.pie(
                values=signal_counts.values,
                names=signal_counts.index,
                title="シグナルタイプ分布",
                color_discrete_map={
                    'BUY': '#00c851',
                    'SELL': '#ff4444',
                    'HOLD': '#ffc107'
                }
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # 強度分布ヒストグラム
            fig_hist = px.histogram(
                signals_df,
                x='strength',
                title="シグナル強度分布",
                nbins=20,
                color_discrete_sequence=['#1f77b4']
            )
            fig_hist.update_layout(
                xaxis_title="強度",
                yaxis_title="件数"
            )
            st.plotly_chart(fig_hist, use_container_width=True)
    
    def _display_performance_stats(self, symbol: str):
        """パフォーマンス統計表示"""
        st.subheader("🎯 パフォーマンス統計")
        
        # 期間設定
        col1, col2 = st.columns(2)
        
        with col1:
            perf_period = st.selectbox(
                "分析期間",
                [7, 14, 30, 60, 90],
                index=2,
                format_func=lambda x: f"過去{x}日",
                key="perf_period"
            )
        
        with col2:
            strategy_name = st.selectbox(
                "戦略",
                ["デフォルト戦略", "RSI戦略", "MACD戦略", "複合戦略"],
                index=0
            )
        
        # パフォーマンス計算
        performance = self.signal_storage.calculate_strategy_performance(
            strategy_name=strategy_name,
            symbol=symbol,
            days=perf_period
        )
        
        if performance['total_trades'] == 0:
            st.info(f"過去{perf_period}日間のトレードデータがありません")
            return
        
        # パフォーマンスメトリクス表示
        self._display_performance_metrics(performance)
        
        # パフォーマンス履歴チャート
        self._display_performance_charts(symbol, perf_period)
    
    def _display_performance_metrics(self, performance: Dict[str, Any]):
        """パフォーマンスメトリクス表示"""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "総トレード数",
                performance['total_trades'],
                delta=f"勝: {performance['winning_trades']}, 負: {performance['losing_trades']}"
            )
        
        with col2:
            win_rate = performance['win_rate'] * 100
            color = "normal" if win_rate >= 50 else "inverse"
            st.metric(
                "勝率",
                f"{win_rate:.1f}%",
                delta=f"損益比: {performance['profit_factor']:.2f}"
            )
        
        with col3:
            total_pnl = performance['total_pnl']
            pnl_color = "normal" if total_pnl >= 0 else "inverse"
            st.metric(
                "総損益",
                f"¥{total_pnl:,.0f}",
                delta=f"平均: {performance['avg_return']:.2f}%"
            )
        
        with col4:
            max_dd = abs(performance['max_drawdown'])
            st.metric(
                "最大ドローダウン",
                f"¥{max_dd:,.0f}",
                delta=f"シャープ: {performance['sharpe_ratio']:.2f}"
            )
        
        # 詳細統計
        with st.expander("📊 詳細統計", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("平均勝ちトレード", f"¥{performance['avg_win']:,.0f}")
                st.metric("平均負けトレード", f"¥{performance['avg_loss']:,.0f}")
            
            with col2:
                avg_hold = performance['avg_hold_duration']
                if avg_hold > 60:
                    hold_display = f"{avg_hold/60:.1f}時間"
                else:
                    hold_display = f"{avg_hold:.0f}分"
                st.metric("平均保持期間", hold_display)
                st.metric("手数料合計", f"¥{performance['commission_total']:,.0f}")
            
            with col3:
                roi = (performance['total_pnl'] / 1000000) * 100  # 仮定資本1M円
                st.metric("ROI", f"{roi:.2f}%")
                
                # パフォーマンス評価
                if win_rate >= 60 and performance['profit_factor'] >= 1.5:
                    st.success("🔥 優秀なパフォーマンス")
                elif win_rate >= 50 and performance['profit_factor'] >= 1.2:
                    st.info("👍 良好なパフォーマンス")
                else:
                    st.warning("⚠️ 改善が必要")
    
    def _display_performance_charts(self, symbol: str, days: int):
        """パフォーマンスチャート表示"""
        # パフォーマンス記録取得
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        perf_df = self.signal_storage.get_performance_records(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        if perf_df.empty:
            st.info("パフォーマンスデータがありません")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 累積損益曲線
            perf_df_sorted = perf_df.sort_values('entry_time')
            cumulative_pnl = perf_df_sorted['pnl'].cumsum()
            
            fig_cum = go.Figure()
            fig_cum.add_trace(go.Scatter(
                x=perf_df_sorted['entry_time'],
                y=cumulative_pnl,
                mode='lines',
                name='累積損益',
                line=dict(color='blue', width=2),
                fill='tonexty',
                fillcolor='rgba(0,100,255,0.1)'
            ))
            
            fig_cum.update_layout(
                title="累積損益曲線",
                xaxis_title="日時",
                yaxis_title="累積損益 (¥)",
                height=300
            )
            
            st.plotly_chart(fig_cum, use_container_width=True)
        
        with col2:
            # 損益分布ヒストグラム
            fig_hist = px.histogram(
                perf_df,
                x='pnl',
                title="損益分布",
                nbins=20,
                color_discrete_sequence=['#ff7f0e']
            )
            fig_hist.update_layout(
                xaxis_title="損益 (¥)",
                yaxis_title="トレード数",
                height=300
            )
            
            st.plotly_chart(fig_hist, use_container_width=True)
    
    def _display_virtual_trading(self, symbol: str):
        """仮想トレード表示"""
        st.subheader("🎲 仮想トレードシミュレーション")
        
        if not st.session_state.virtual_trading:
            st.info("仮想トレードを有効にしてください")
            return
        
        st.success("🔄 仮想トレード実行中...")
        
        # 仮想トレード設定
        col1, col2, col3 = st.columns(3)
        
        with col1:
            virtual_capital = st.number_input(
                "仮想資本",
                min_value=100000,
                max_value=10000000,
                value=1000000,
                step=100000,
                format="%d"
            )
        
        with col2:
            position_size_pct = st.slider(
                "ポジションサイズ(%)",
                min_value=1,
                max_value=10,
                value=2,
                step=1
            )
        
        with col3:
            auto_execute = st.checkbox(
                "自動実行",
                help="シグナル発生時に自動でトレードを実行"
            )
        
        # 現在のポジション状況（仮想）
        st.markdown("### 📊 現在のポジション")
        
        # ダミーデータでポジション表示
        positions_data = {
            '銘柄': [symbol],
            'ポジション': ['LONG'],
            '数量': [100],
            'エントリー価格': [2150.00],
            '現在価格': [2180.00],
            '含み損益': ['+3,000'],
            '含み損益率': ['+1.40%']
        }
        
        positions_df = pd.DataFrame(positions_data)
        st.dataframe(positions_df, use_container_width=True)
        
        # 仮想トレード履歴
        st.markdown("### 📈 仮想トレード履歴")
        
        # ダミーの履歴データ
        trade_history = pd.DataFrame({
            '日時': pd.date_range('2024-01-01', periods=10, freq='D'),
            'シグナル': ['BUY', 'SELL', 'BUY', 'SELL', 'BUY', 'SELL', 'BUY', 'SELL', 'BUY', 'SELL'],
            'エントリー': [2100, 2150, 2080, 2120, 2200, 2250, 2180, 2220, 2160, 2200],
            'エグジット': [2150, 2130, 2120, 2100, 2250, 2230, 2220, 2200, 2200, 2180],
            '損益': [5000, -2000, 4000, -2000, 5000, -2000, 4000, -2000, 4000, -2000],
            '損益率': [2.38, -0.93, 1.92, -0.95, 2.27, -0.89, 1.83, -0.90, 1.85, -0.91]
        })
        
        st.dataframe(trade_history.tail(10), use_container_width=True)
        
        # 仮想トレード統計
        total_pnl = trade_history['損益'].sum()
        win_rate = len(trade_history[trade_history['損益'] > 0]) / len(trade_history) * 100
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("仮想総損益", f"¥{total_pnl:,}")
        
        with col2:
            st.metric("仮想勝率", f"{win_rate:.1f}%")
        
        with col3:
            roi = (total_pnl / virtual_capital) * 100
            st.metric("仮想ROI", f"{roi:.2f}%")
    
    def _save_signal_if_new(self, signal_data: Dict[str, Any]):
        """新しいシグナルの場合のみ保存"""
        try:
            # 最近のシグナルと比較（重複チェック）
            recent_signals = self.signal_storage.get_signals(
                symbol=signal_data['symbol'],
                start_date=datetime.now() - timedelta(minutes=30),
                limit=1
            )
            
            # 同じシグナルが30分以内に記録されていない場合のみ保存
            if recent_signals is None or recent_signals.empty or (len(recent_signals) > 0 and recent_signals.iloc[0]['signal_type'] != signal_data['signal']):
                self.signal_storage.store_signal(signal_data)
                st.success(f"✅ 新しい{signal_data['signal']}シグナルを記録しました")
        
        except Exception as e:
            st.error(f"シグナル保存エラー: {e}")
    
    def _convert_signals_to_dataframe(self, signals: List) -> pd.DataFrame:
        """TradingSignalリストをDataFrameに変換"""
        if not signals:
            return pd.DataFrame()
        
        try:
            data = []
            for signal in signals:
                data.append({
                    'timestamp': signal.timestamp,
                    'signal_type': signal.signal_type.value,
                    'strength': signal.strength,
                    'confidence': signal.confidence,
                    'price': signal.price,
                    'stop_loss': signal.stop_loss,
                    'take_profit': signal.take_profit,
                    'risk_level': signal.risk_level,
                    'notes': signal.notes
                })
            
            return pd.DataFrame(data)
        except Exception as e:
            st.error(f"シグナル変換エラー: {e}")
            return pd.DataFrame()