"""
バックテスト結果の可視化コンポーネント
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
from ..utils.dashboard_utils import DashboardUtils


class BacktestComponent:
    """バックテストコンポーネント"""
    
    def __init__(self, data_collector):
        """初期化"""
        self.data_collector = data_collector
        self.utils = DashboardUtils()
        
        # セッション状態初期化
        if 'backtest_results' not in st.session_state:
            st.session_state.backtest_results = {}
        
        if 'backtest_running' not in st.session_state:
            st.session_state.backtest_running = False
    
    def display(self, symbol: str):
        """バックテスト表示"""
        st.subheader("📊 バックテスト分析")
        
        # バックテスト設定
        self._display_backtest_settings(symbol)
        
        # バックテスト結果表示
        if symbol in st.session_state.backtest_results:
            self._display_backtest_results(symbol)
        else:
            st.info("バックテストを実行してください")
    
    def _display_backtest_settings(self, symbol: str):
        """バックテスト設定画面"""
        st.markdown("### ⚙️ バックテスト設定")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            test_period = st.selectbox(
                "テスト期間",
                ["1ヶ月", "3ヶ月", "6ヶ月", "1年"],
                index=1
            )
        
        with col2:
            initial_capital = st.number_input(
                "初期資本",
                min_value=100000,
                max_value=100000000,
                value=1000000,
                step=100000,
                format="%d"
            )
        
        with col3:
            position_size = st.slider(
                "ポジションサイズ(%)",
                min_value=1,
                max_value=100,
                value=10,
                step=1
            )
        
        with col4:
            commission_rate = st.number_input(
                "手数料率(%)",
                min_value=0.0,
                max_value=1.0,
                value=0.1,
                step=0.01,
                format="%.2f"
            )
        
        # 戦略設定
        st.markdown("#### 🎯 戦略設定")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # シグナル強度閾値
            signal_threshold = st.slider(
                "シグナル強度閾値",
                min_value=0,
                max_value=100,
                value=60,
                step=5
            )
            
            confidence_threshold = st.slider(
                "信頼度閾値",
                min_value=0.0,
                max_value=1.0,
                value=0.6,
                step=0.1
            )
        
        with col2:
            # リスク管理設定
            stop_loss_pct = st.slider(
                "ストップロス(%)",
                min_value=0.5,
                max_value=10.0,
                value=2.0,
                step=0.5
            )
            
            take_profit_pct = st.slider(
                "テイクプロフィット(%)",
                min_value=1.0,
                max_value=20.0,
                value=4.0,
                step=0.5
            )
        
        # 高度な設定
        with st.expander("🔧 高度な設定"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                max_holding_days = st.number_input(
                    "最大保有日数",
                    min_value=1,
                    max_value=30,
                    value=5
                )
            
            with col2:
                slippage = st.number_input(
                    "スリッページ(%)",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.05,
                    step=0.01
                )
            
            with col3:
                market_impact = st.checkbox("マーケットインパクト考慮", value=False)
        
        # バックテスト実行
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("🚀 バックテスト実行", type="primary", disabled=st.session_state.backtest_running):
                self._run_backtest(
                    symbol=symbol,
                    test_period=test_period,
                    initial_capital=initial_capital,
                    position_size=position_size,
                    commission_rate=commission_rate,
                    signal_threshold=signal_threshold,
                    confidence_threshold=confidence_threshold,
                    stop_loss_pct=stop_loss_pct,
                    take_profit_pct=take_profit_pct,
                    max_holding_days=max_holding_days,
                    slippage=slippage
                )
        
        with col2:
            if st.button("📊 複数戦略比較"):
                self._run_multi_strategy_comparison(symbol)
        
        with col3:
            if st.session_state.backtest_running:
                st.info("🔄 バックテスト実行中...")
    
    def _run_backtest(self, **kwargs):
        """バックテスト実行"""
        symbol = kwargs['symbol']
        
        try:
            st.session_state.backtest_running = True
            
            # プログレスバー
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # データ取得
            status_text.text("データを取得中...")
            progress_bar.progress(20)
            
            period_mapping = {
                "1ヶ月": "1mo",
                "3ヶ月": "3mo", 
                "6ヶ月": "6mo",
                "1年": "1y"
            }
            
            data = self.data_collector.get_stock_data(
                symbol,
                period=period_mapping[kwargs['test_period']],
                interval="1d"
            )
            
            if data is None or len(data) < 50:
                st.error("バックテストに十分なデータがありません")
                return
            
            # シグナル生成
            status_text.text("シグナルを生成中...")
            progress_bar.progress(40)
            
            signal_generator = SignalGenerator(data)
            signals = signal_generator.generate_signals(data)
            
            if signals is None or signals.empty:
                st.error("シグナルが生成できませんでした")
                return
            
            # バックテスト実行
            status_text.text("バックテストを実行中...")
            progress_bar.progress(60)
            
            backtest_results = self._execute_backtest_logic(
                data=data,
                signals=signals,
                **kwargs
            )
            
            # 結果保存
            status_text.text("結果を保存中...")
            progress_bar.progress(80)
            
            st.session_state.backtest_results[symbol] = backtest_results
            
            # 完了
            progress_bar.progress(100)
            status_text.text("バックテスト完了!")
            
            st.success("✅ バックテストが完了しました")
            st.rerun()
            
        except Exception as e:
            st.error(f"バックテストエラー: {e}")
        
        finally:
            st.session_state.backtest_running = False
    
    def _execute_backtest_logic(self, data: pd.DataFrame, signals: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """バックテストロジック実行"""
        # パラメータ取得
        initial_capital = kwargs['initial_capital']
        position_size_pct = kwargs['position_size'] / 100
        commission_rate = kwargs['commission_rate'] / 100
        signal_threshold = kwargs['signal_threshold']
        confidence_threshold = kwargs['confidence_threshold']
        stop_loss_pct = kwargs['stop_loss_pct'] / 100
        take_profit_pct = kwargs['take_profit_pct'] / 100
        max_holding_days = kwargs['max_holding_days']
        slippage = kwargs['slippage'] / 100
        
        # トレード履歴
        trades = []
        positions = []
        equity_curve = []
        
        capital = initial_capital
        position = None
        
        # シグナルをフィルタリング
        filtered_signals = signals[
            (signals['strength'] >= signal_threshold) &
            (signals['confidence'] >= confidence_threshold)
        ].copy()
        
        for i, (timestamp, signal_row) in enumerate(filtered_signals.iterrows()):
            current_price = data.loc[timestamp, 'close']
            
            # ポジション決済チェック
            if position is not None:
                hold_days = (timestamp - position['entry_time']).days
                
                # ストップロス・テイクプロフィット・最大保有期間チェック
                exit_reason = None
                exit_price = current_price
                
                if position['side'] == 'LONG':
                    if current_price <= position['stop_loss']:
                        exit_reason = 'Stop Loss'
                        exit_price = position['stop_loss']
                    elif current_price >= position['take_profit']:
                        exit_reason = 'Take Profit'
                        exit_price = position['take_profit']
                    elif hold_days >= max_holding_days:
                        exit_reason = 'Max Holding Period'
                
                elif position['side'] == 'SHORT':
                    if current_price >= position['stop_loss']:
                        exit_reason = 'Stop Loss'
                        exit_price = position['stop_loss']
                    elif current_price <= position['take_profit']:
                        exit_reason = 'Take Profit'
                        exit_price = position['take_profit']
                    elif hold_days >= max_holding_days:
                        exit_reason = 'Max Holding Period'
                
                # ポジション決済
                if exit_reason:
                    # スリッページ適用
                    if position['side'] == 'LONG':
                        exit_price *= (1 - slippage)
                    else:
                        exit_price *= (1 + slippage)
                    
                    # PnL計算
                    if position['side'] == 'LONG':
                        pnl = (exit_price - position['entry_price']) * position['quantity']
                    else:
                        pnl = (position['entry_price'] - exit_price) * position['quantity']
                    
                    # 手数料差し引き
                    commission = exit_price * position['quantity'] * commission_rate
                    net_pnl = pnl - commission - position['entry_commission']
                    
                    # 資本更新
                    capital += net_pnl
                    
                    # トレード記録
                    trade = {
                        'entry_time': position['entry_time'],
                        'exit_time': timestamp,
                        'side': position['side'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'quantity': position['quantity'],
                        'pnl': net_pnl,
                        'pnl_pct': (net_pnl / (position['entry_price'] * position['quantity'])) * 100,
                        'exit_reason': exit_reason,
                        'hold_days': hold_days
                    }
                    trades.append(trade)
                    
                    position = None
            
            # 新規ポジション判定
            if position is None and signal_row['signal'] in ['BUY', 'SELL']:
                side = 'LONG' if signal_row['signal'] == 'BUY' else 'SHORT'
                
                # ポジションサイズ計算
                position_value = capital * position_size_pct
                quantity = int(position_value / current_price)
                
                if quantity > 0:
                    # スリッページ適用
                    entry_price = current_price * (1 + slippage) if side == 'LONG' else current_price * (1 - slippage)
                    
                    # ストップロス・テイクプロフィット設定
                    if side == 'LONG':
                        stop_loss = entry_price * (1 - stop_loss_pct)
                        take_profit = entry_price * (1 + take_profit_pct)
                    else:
                        stop_loss = entry_price * (1 + stop_loss_pct)
                        take_profit = entry_price * (1 - take_profit_pct)
                    
                    # 手数料計算
                    entry_commission = entry_price * quantity * commission_rate
                    
                    # ポジション開設
                    position = {
                        'entry_time': timestamp,
                        'side': side,
                        'entry_price': entry_price,
                        'quantity': quantity,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'entry_commission': entry_commission
                    }
                    
                    positions.append(position.copy())
            
            # エクイティカーブ記録
            unrealized_pnl = 0
            if position:
                if position['side'] == 'LONG':
                    unrealized_pnl = (current_price - position['entry_price']) * position['quantity']
                else:
                    unrealized_pnl = (position['entry_price'] - current_price) * position['quantity']
            
            equity_curve.append({
                'timestamp': timestamp,
                'capital': capital,
                'unrealized_pnl': unrealized_pnl,
                'total_equity': capital + unrealized_pnl
            })
        
        # パフォーマンス統計計算
        performance_stats = self._calculate_performance_stats(trades, initial_capital, equity_curve)
        
        return {
            'trades': trades,
            'positions': positions,
            'equity_curve': equity_curve,
            'performance_stats': performance_stats,
            'settings': kwargs
        }
    
    def _calculate_performance_stats(self, trades: List[Dict], initial_capital: float, equity_curve: List[Dict]) -> Dict[str, Any]:
        """パフォーマンス統計計算"""
        if not trades:
            return {}
        
        # 基本統計
        total_trades = len(trades)
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] < 0]
        
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        total_pnl = sum(t['pnl'] for t in trades)
        final_capital = initial_capital + total_pnl
        total_return = (total_pnl / initial_capital) * 100
        
        # 勝敗統計
        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        
        # ドローダウン計算
        equity_values = [eq['total_equity'] for eq in equity_curve]
        running_max = np.maximum.accumulate(equity_values)
        drawdown = np.array(equity_values) - running_max
        max_drawdown = np.min(drawdown)
        max_drawdown_pct = (max_drawdown / initial_capital) * 100
        
        # シャープレシオ計算
        daily_returns = np.diff(equity_values) / equity_values[:-1]
        sharpe_ratio = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252) if np.std(daily_returns) > 0 else 0
        
        # その他統計
        avg_hold_days = np.mean([t['hold_days'] for t in trades])
        max_consecutive_wins = self._calculate_consecutive_wins(trades)
        max_consecutive_losses = self._calculate_consecutive_losses(trades)
        
        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_return': total_return,
            'final_capital': final_capital,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown_pct,
            'sharpe_ratio': sharpe_ratio,
            'avg_hold_days': avg_hold_days,
            'max_consecutive_wins': max_consecutive_wins,
            'max_consecutive_losses': max_consecutive_losses
        }
    
    def _calculate_consecutive_wins(self, trades: List[Dict]) -> int:
        """連続勝利数計算"""
        max_consecutive = 0
        current_consecutive = 0
        
        for trade in trades:
            if trade['pnl'] > 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def _calculate_consecutive_losses(self, trades: List[Dict]) -> int:
        """連続敗北数計算"""
        max_consecutive = 0
        current_consecutive = 0
        
        for trade in trades:
            if trade['pnl'] < 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def _display_backtest_results(self, symbol: str):
        """バックテスト結果表示"""
        results = st.session_state.backtest_results[symbol]
        
        st.markdown("### 📊 バックテスト結果")
        
        # パフォーマンス概要
        self._display_performance_overview(results['performance_stats'])
        
        # エクイティカーブ
        self._display_equity_curve(results['equity_curve'])
        
        # トレード分析
        self._display_trade_analysis(results['trades'])
        
        # 詳細統計
        self._display_detailed_statistics(results)
    
    def _display_performance_overview(self, stats: Dict[str, Any]):
        """パフォーマンス概要表示"""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_return = stats.get('total_return', 0)
            color = "normal" if total_return >= 0 else "inverse"
            st.metric(
                "総リターン",
                f"{total_return:.2f}%",
                delta=f"¥{stats.get('total_pnl', 0):,.0f}"
            )
        
        with col2:
            win_rate = stats.get('win_rate', 0) * 100
            st.metric(
                "勝率",
                f"{win_rate:.1f}%",
                delta=f"{stats.get('winning_trades', 0)}/{stats.get('total_trades', 0)}"
            )
        
        with col3:
            sharpe_ratio = stats.get('sharpe_ratio', 0)
            st.metric(
                "シャープレシオ",
                f"{sharpe_ratio:.2f}",
                delta=f"損益比: {stats.get('profit_factor', 0):.2f}"
            )
        
        with col4:
            max_dd = stats.get('max_drawdown_pct', 0)
            st.metric(
                "最大ドローダウン",
                f"{max_dd:.2f}%",
                delta=f"¥{stats.get('max_drawdown', 0):,.0f}"
            )
        
        # パフォーマンス評価
        self._display_performance_rating(stats)
    
    def _display_performance_rating(self, stats: Dict[str, Any]):
        """パフォーマンス評価表示"""
        win_rate = stats.get('win_rate', 0)
        profit_factor = stats.get('profit_factor', 0)
        sharpe_ratio = stats.get('sharpe_ratio', 0)
        total_return = stats.get('total_return', 0)
        
        # 評価スコア計算
        score = 0
        if win_rate >= 0.6: score += 25
        elif win_rate >= 0.5: score += 15
        elif win_rate >= 0.4: score += 5
        
        if profit_factor >= 2.0: score += 25
        elif profit_factor >= 1.5: score += 15
        elif profit_factor >= 1.2: score += 10
        elif profit_factor >= 1.0: score += 5
        
        if sharpe_ratio >= 1.5: score += 25
        elif sharpe_ratio >= 1.0: score += 15
        elif sharpe_ratio >= 0.5: score += 10
        
        if total_return >= 20: score += 25
        elif total_return >= 10: score += 15
        elif total_return >= 5: score += 10
        elif total_return >= 0: score += 5
        
        # 評価表示
        if score >= 80:
            st.success("🔥 優秀な戦略パフォーマンス")
        elif score >= 60:
            st.info("👍 良好な戦略パフォーマンス")
        elif score >= 40:
            st.warning("⚠️ 平均的な戦略パフォーマンス")
        else:
            st.error("❌ 改善が必要な戦略パフォーマンス")
    
    def _display_equity_curve(self, equity_curve: List[Dict]):
        """エクイティカーブ表示"""
        st.markdown("#### 📈 エクイティカーブ")
        
        if not equity_curve:
            st.info("エクイティデータがありません")
            return
        
        # データフレーム作成
        df = pd.DataFrame(equity_curve)
        
        fig = go.Figure()
        
        # エクイティカーブ
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['total_equity'],
            mode='lines',
            name='総資産',
            line=dict(color='blue', width=2),
            fill='tonexty',
            fillcolor='rgba(0,100,255,0.1)'
        ))
        
        # 初期資本線
        initial_capital = df['capital'].iloc[0]
        fig.add_hline(
            y=initial_capital,
            line_dash="dash",
            line_color="gray",
            annotation_text="初期資本"
        )
        
        fig.update_layout(
            title="エクイティカーブ",
            xaxis_title="日時",
            yaxis_title="資産価値 (¥)",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def _display_trade_analysis(self, trades: List[Dict]):
        """トレード分析表示"""
        st.markdown("#### 📊 トレード分析")
        
        if not trades:
            st.info("トレードデータがありません")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 損益分布ヒストグラム
            pnl_values = [t['pnl'] for t in trades]
            
            fig_hist = px.histogram(
                x=pnl_values,
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
        
        with col2:
            # 保有期間分布
            hold_days = [t['hold_days'] for t in trades]
            
            fig_hold = px.histogram(
                x=hold_days,
                title="保有期間分布",
                nbins=15,
                color_discrete_sequence=['#2ca02c']
            )
            fig_hold.update_layout(
                xaxis_title="保有日数",
                yaxis_title="トレード数",
                height=300
            )
            
            st.plotly_chart(fig_hold, use_container_width=True)
        
        # トレード詳細テーブル
        self._display_trades_table(trades)
    
    def _display_trades_table(self, trades: List[Dict]):
        """トレードテーブル表示"""
        st.markdown("#### 📄 トレード詳細 (最新20件)")
        
        # 最新20件のトレード
        recent_trades = trades[-20:] if len(trades) > 20 else trades
        
        # 表示用データフレーム作成
        df_data = []
        for trade in recent_trades:
            df_data.append({
                'エントリー日': trade['entry_time'].strftime('%m/%d'),
                'エグジット日': trade['exit_time'].strftime('%m/%d'),
                'サイド': trade['side'],
                'エントリー価格': f"¥{trade['entry_price']:.2f}",
                'エグジット価格': f"¥{trade['exit_price']:.2f}",
                '損益': f"¥{trade['pnl']:,.0f}",
                '損益率': f"{trade['pnl_pct']:+.2f}%",
                '保有日数': f"{trade['hold_days']}日",
                '決済理由': trade['exit_reason']
            })
        
        if df_data:
            df = pd.DataFrame(df_data)
            
            # スタイル適用
            def style_pnl(val):
                if '+' in val:
                    return 'background-color: #e8f5e8; color: #2e7d32'
                elif '-' in val:
                    return 'background-color: #ffebee; color: #c62828'
                else:
                    return ''
            
            def style_side(val):
                if val == 'LONG':
                    return 'background-color: #e3f2fd; color: #1976d2'
                else:
                    return 'background-color: #fce4ec; color: #c2185b'
            
            styled_df = df.style.applymap(style_pnl, subset=['損益', '損益率']) \
                               .applymap(style_side, subset=['サイド'])
            
            st.dataframe(styled_df, use_container_width=True)
    
    def _display_detailed_statistics(self, results: Dict[str, Any]):
        """詳細統計表示"""
        with st.expander("📊 詳細統計", expanded=False):
            stats = results['performance_stats']
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("平均勝ちトレード", f"¥{stats.get('avg_win', 0):,.0f}")
                st.metric("平均負けトレード", f"¥{stats.get('avg_loss', 0):,.0f}")
                st.metric("平均保有期間", f"{stats.get('avg_hold_days', 0):.1f}日")
            
            with col2:
                st.metric("最大連続勝利", f"{stats.get('max_consecutive_wins', 0)}回")
                st.metric("最大連続敗北", f"{stats.get('max_consecutive_losses', 0)}回")
                st.metric("最終資本", f"¥{stats.get('final_capital', 0):,.0f}")
            
            with col3:
                # バックテスト設定表示
                settings = results.get('settings', {})
                st.info(f"""
                **バックテスト設定:**
                - 期間: {settings.get('test_period', 'N/A')}
                - ポジションサイズ: {settings.get('position_size', 0)}%
                - 手数料率: {settings.get('commission_rate', 0)}%
                - シグナル閾値: {settings.get('signal_threshold', 0)}
                """)
    
    def _run_multi_strategy_comparison(self, symbol: str):
        """複数戦略比較実行"""
        st.info("🔄 複数戦略比較は開発中です")
        
        # 将来の実装:
        # - 複数の戦略パラメータでバックテスト実行
        # - 結果の比較表示
        # - 最適パラメータの提案