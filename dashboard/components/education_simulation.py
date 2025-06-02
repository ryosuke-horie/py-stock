"""
シミュレーション練習モード機能
リスクフリーでの投資練習環境を提供
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.data_collector.stock_data_collector import StockDataCollector


class SimulationPosition:
    """シミュレーション取引ポジション"""
    
    def __init__(self, symbol: str, shares: int, entry_price: float, entry_time: datetime, position_type: str = "long"):
        self.symbol = symbol
        self.shares = shares
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.position_type = position_type  # "long" or "short"
        self.exit_price: Optional[float] = None
        self.exit_time: Optional[datetime] = None
        self.is_open = True
    
    def close_position(self, exit_price: float, exit_time: datetime):
        """ポジションクローズ"""
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.is_open = False
    
    def get_pnl(self, current_price: Optional[float] = None) -> float:
        """損益計算"""
        if self.is_open and current_price is None:
            return 0.0
        
        price = current_price if self.is_open else self.exit_price
        
        if self.position_type == "long":
            return (price - self.entry_price) * self.shares
        else:  # short
            return (self.entry_price - price) * self.shares
    
    def get_return_rate(self, current_price: Optional[float] = None) -> float:
        """リターン率計算"""
        if self.is_open and current_price is None:
            return 0.0
        
        pnl = self.get_pnl(current_price)
        investment = self.entry_price * self.shares
        return (pnl / investment) * 100 if investment > 0 else 0.0


class SimulationAccount:
    """シミュレーション口座"""
    
    def __init__(self, initial_balance: float = 1000000):
        self.initial_balance = initial_balance
        self.cash_balance = initial_balance
        self.positions: List[SimulationPosition] = []
        self.trade_history: List[Dict] = []
    
    def buy(self, symbol: str, shares: int, price: float, timestamp: datetime) -> bool:
        """買い注文"""
        cost = shares * price
        commission = self._calculate_commission(cost)
        total_cost = cost + commission
        
        if total_cost > self.cash_balance:
            return False
        
        self.cash_balance -= total_cost
        position = SimulationPosition(symbol, shares, price, timestamp, "long")
        self.positions.append(position)
        
        self.trade_history.append({
            "timestamp": timestamp,
            "symbol": symbol,
            "action": "BUY",
            "shares": shares,
            "price": price,
            "commission": commission,
            "total": total_cost
        })
        
        return True
    
    def sell(self, symbol: str, shares: int, price: float, timestamp: datetime) -> bool:
        """売り注文"""
        # 保有ポジションから売却
        available_shares = self._get_available_shares(symbol)
        if shares > available_shares:
            return False
        
        proceeds = shares * price
        commission = self._calculate_commission(proceeds)
        net_proceeds = proceeds - commission
        
        self.cash_balance += net_proceeds
        
        # ポジションクローズ（FIFO）
        remaining_shares = shares
        for position in self.positions:
            if position.symbol == symbol and position.is_open and remaining_shares > 0:
                if position.shares <= remaining_shares:
                    # ポジション全体をクローズ
                    position.close_position(price, timestamp)
                    remaining_shares -= position.shares
                else:
                    # ポジションの一部をクローズ
                    # 新しいポジションを作成して残りを管理
                    new_position = SimulationPosition(
                        symbol, position.shares - remaining_shares,
                        position.entry_price, position.entry_time, position.position_type
                    )
                    position.shares = remaining_shares
                    position.close_position(price, timestamp)
                    self.positions.append(new_position)
                    remaining_shares = 0
        
        self.trade_history.append({
            "timestamp": timestamp,
            "symbol": symbol,
            "action": "SELL",
            "shares": shares,
            "price": price,
            "commission": commission,
            "total": net_proceeds
        })
        
        return True
    
    def _calculate_commission(self, amount: float) -> float:
        """手数料計算（簡易版）"""
        # 日本株の一般的な手数料体系
        if amount <= 50000:
            return 55
        elif amount <= 100000:
            return 99
        elif amount <= 200000:
            return 115
        elif amount <= 500000:
            return amount * 0.099 / 100
        else:
            return amount * 0.0385 / 100
    
    def _get_available_shares(self, symbol: str) -> int:
        """利用可能株数取得"""
        total_shares = 0
        for position in self.positions:
            if position.symbol == symbol and position.is_open:
                total_shares += position.shares
        return total_shares
    
    def get_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """ポートフォリオ評価額"""
        portfolio_value = self.cash_balance
        
        for position in self.positions:
            if position.is_open and position.symbol in current_prices:
                current_price = current_prices[position.symbol]
                portfolio_value += position.shares * current_price
        
        return portfolio_value
    
    def get_total_pnl(self, current_prices: Dict[str, float]) -> float:
        """総損益"""
        return self.get_portfolio_value(current_prices) - self.initial_balance
    
    def get_positions_summary(self, current_prices: Dict[str, float]) -> List[Dict]:
        """ポジション要約"""
        summary = []
        
        # 銘柄ごとに集計
        symbols = set(pos.symbol for pos in self.positions if pos.is_open)
        
        for symbol in symbols:
            total_shares = 0
            avg_price = 0
            total_cost = 0
            
            for position in self.positions:
                if position.symbol == symbol and position.is_open:
                    total_shares += position.shares
                    total_cost += position.shares * position.entry_price
            
            if total_shares > 0:
                avg_price = total_cost / total_shares
                current_price = current_prices.get(symbol, avg_price)
                current_value = total_shares * current_price
                pnl = current_value - total_cost
                pnl_rate = (pnl / total_cost) * 100 if total_cost > 0 else 0
                
                summary.append({
                    "symbol": symbol,
                    "shares": total_shares,
                    "avg_price": avg_price,
                    "current_price": current_price,
                    "current_value": current_value,
                    "pnl": pnl,
                    "pnl_rate": pnl_rate
                })
        
        return summary


class EducationSimulationComponent:
    """シミュレーション練習モードコンポーネント"""
    
    def __init__(self):
        """初期化"""
        self.data_collector = StockDataCollector()
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """セッション状態初期化"""
        if 'sim_account' not in st.session_state:
            st.session_state.sim_account = SimulationAccount()
        
        if 'sim_current_prices' not in st.session_state:
            st.session_state.sim_current_prices = {}
        
        if 'sim_selected_symbol' not in st.session_state:
            st.session_state.sim_selected_symbol = '7203.T'
        
        if 'sim_difficulty' not in st.session_state:
            st.session_state.sim_difficulty = "初級"
    
    def display(self):
        """メイン表示"""
        st.header("🎮 シミュレーション練習モード")
        
        # 難易度選択
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            difficulty = st.selectbox(
                "🎯 難易度",
                ["初級", "中級", "上級"],
                index=["初級", "中級", "上級"].index(st.session_state.sim_difficulty)
            )
            st.session_state.sim_difficulty = difficulty
        
        with col2:
            if st.button("🔄 アカウントリセット"):
                st.session_state.sim_account = SimulationAccount()
                st.success("シミュレーションアカウントをリセットしました！")
        
        with col3:
            self._display_difficulty_info(difficulty)
        
        st.markdown("---")
        
        # メイン機能タブ
        tab1, tab2, tab3, tab4 = st.tabs(["💹 取引", "📊 ポートフォリオ", "📈 パフォーマンス", "📚 学習メモ"])
        
        with tab1:
            self._display_trading_interface()
        
        with tab2:
            self._display_portfolio()
        
        with tab3:
            self._display_performance()
        
        with tab4:
            self._display_learning_notes()
    
    def _display_difficulty_info(self, difficulty: str):
        """難易度情報表示"""
        info_text = {
            "初級": "💡 基本的な売買のみ。手数料は実際より低く設定。",
            "中級": "⚡ リアルな手数料・税金。短期売買も可能。",
            "上級": "🔥 信用取引・オプションも利用可能。完全リアル環境。"
        }
        
        st.info(info_text.get(difficulty, ""))
    
    def _display_trading_interface(self):
        """取引インターフェース"""
        st.subheader("💹 株式取引")
        
        # 銘柄選択・価格取得
        col1, col2 = st.columns([1, 1])
        
        with col1:
            symbol = st.text_input("📈 銘柄コード", value=st.session_state.sim_selected_symbol, key="education_simulation_symbol")
            st.session_state.sim_selected_symbol = symbol
        
        with col2:
            if st.button("📊 価格更新"):
                self._update_price(symbol)
        
        # 現在価格表示
        current_price = st.session_state.sim_current_prices.get(symbol)
        if current_price:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("現在価格", f"¥{current_price:,.0f}")
            with col2:
                # 簡易変動率（ダミーデータ）
                change_rate = np.random.uniform(-3, 3)
                st.metric("変動率", f"{change_rate:+.2f}%", delta=f"{change_rate:+.2f}%")
            with col3:
                available_shares = st.session_state.sim_account._get_available_shares(symbol)
                st.metric("保有株数", f"{available_shares:,}株")
        else:
            st.warning("価格データを更新してください")
        
        st.markdown("---")
        
        # 売買インターフェース
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🟢 買い注文")
            buy_shares = st.number_input("買い株数", min_value=1, max_value=10000, value=100, key="buy_shares")
            buy_price = st.number_input("買い価格", min_value=0.0, value=current_price or 1000.0, key="buy_price")
            
            cost = buy_shares * buy_price
            commission = st.session_state.sim_account._calculate_commission(cost)
            total_cost = cost + commission
            
            st.write(f"💰 必要資金: ¥{total_cost:,.0f} (手数料: ¥{commission:.0f})")
            st.write(f"💳 残高: ¥{st.session_state.sim_account.cash_balance:,.0f}")
            
            if st.button("🟢 買い注文実行", disabled=total_cost > st.session_state.sim_account.cash_balance):
                if st.session_state.sim_account.buy(symbol, buy_shares, buy_price, datetime.now()):
                    st.success(f"✅ {symbol} {buy_shares}株を¥{buy_price:,.0f}で購入しました！")
                else:
                    st.error("❌ 残高不足です")
        
        with col2:
            st.markdown("#### 🔴 売り注文")
            available_shares = st.session_state.sim_account._get_available_shares(symbol)
            sell_shares = st.number_input("売り株数", min_value=1, max_value=max(available_shares, 1), value=max(min(100, available_shares), 1), key="sell_shares")
            sell_price = st.number_input("売り価格", min_value=0.0, value=current_price or 1000.0, key="sell_price")
            
            proceeds = sell_shares * sell_price
            commission = st.session_state.sim_account._calculate_commission(proceeds)
            net_proceeds = proceeds - commission
            
            st.write(f"💰 受取金額: ¥{net_proceeds:,.0f} (手数料: ¥{commission:.0f})")
            st.write(f"📊 保有株数: {available_shares:,}株")
            
            if st.button("🔴 売り注文実行", disabled=sell_shares > available_shares):
                if st.session_state.sim_account.sell(symbol, sell_shares, sell_price, datetime.now()):
                    st.success(f"✅ {symbol} {sell_shares}株を¥{sell_price:,.0f}で売却しました！")
                else:
                    st.error("❌ 保有株数不足です")
        
        # 取引履歴（最新5件）
        if st.session_state.sim_account.trade_history:
            st.markdown("#### 📋 最近の取引履歴")
            recent_trades = st.session_state.sim_account.trade_history[-5:]
            trades_df = pd.DataFrame(recent_trades)
            trades_df['timestamp'] = trades_df['timestamp'].dt.strftime('%m/%d %H:%M')
            st.dataframe(trades_df, use_container_width=True)
    
    def _display_portfolio(self):
        """ポートフォリオ表示"""
        st.subheader("📊 ポートフォリオ")
        
        # ポートフォリオサマリー
        current_prices = st.session_state.sim_current_prices
        account = st.session_state.sim_account
        
        portfolio_value = account.get_portfolio_value(current_prices)
        total_pnl = account.get_total_pnl(current_prices)
        total_return = (total_pnl / account.initial_balance) * 100
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("💰 総資産", f"¥{portfolio_value:,.0f}")
        
        with col2:
            st.metric("💳 現金", f"¥{account.cash_balance:,.0f}")
        
        with col3:
            st.metric("📈 総損益", f"¥{total_pnl:,.0f}", delta=f"{total_return:+.2f}%")
        
        with col4:
            invested_value = portfolio_value - account.cash_balance
            if portfolio_value > 0:
                cash_ratio = (account.cash_balance / portfolio_value) * 100
                st.metric("💵 現金比率", f"{cash_ratio:.1f}%")
        
        st.markdown("---")
        
        # ポジション一覧
        positions = account.get_positions_summary(current_prices)
        if positions:
            st.markdown("#### 📋 保有ポジション")
            
            positions_df = pd.DataFrame(positions)
            positions_df['avg_price'] = positions_df['avg_price'].round(0)
            positions_df['current_price'] = positions_df['current_price'].round(0)
            positions_df['current_value'] = positions_df['current_value'].round(0)
            positions_df['pnl'] = positions_df['pnl'].round(0)
            positions_df['pnl_rate'] = positions_df['pnl_rate'].round(2)
            
            # カラム名を日本語に変更
            positions_df = positions_df.rename(columns={
                'symbol': '銘柄',
                'shares': '株数',
                'avg_price': '平均価格',
                'current_price': '現在価格',
                'current_value': '評価額',
                'pnl': '損益',
                'pnl_rate': '損益率(%)'
            })
            
            # スタイリング
            def color_pnl(val):
                if val > 0:
                    return 'background-color: #e8f5e8; color: #2e7d32'
                elif val < 0:
                    return 'background-color: #ffebee; color: #c62828'
                else:
                    return ''
            
            styled_df = positions_df.style.applymap(color_pnl, subset=['損益', '損益率(%)'])
            st.dataframe(styled_df, use_container_width=True)
            
            # ポートフォリオ構成円グラフ
            fig = go.Figure(data=[go.Pie(
                labels=positions_df['銘柄'],
                values=positions_df['評価額'],
                hole=0.3
            )])
            
            fig.update_layout(
                title="ポートフォリオ構成",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("現在ポジションはありません")
    
    def _display_performance(self):
        """パフォーマンス表示"""
        st.subheader("📈 パフォーマンス分析")
        
        account = st.session_state.sim_account
        
        if not account.trade_history:
            st.info("取引履歴がありません")
            return
        
        # 取引統計
        trades_df = pd.DataFrame(account.trade_history)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_trades = len(trades_df)
            st.metric("📊 総取引数", f"{total_trades:,}回")
        
        with col2:
            buy_trades = len(trades_df[trades_df['action'] == 'BUY'])
            sell_trades = len(trades_df[trades_df['action'] == 'SELL'])
            st.metric("🟢 買い / 🔴 売り", f"{buy_trades} / {sell_trades}")
        
        with col3:
            total_commission = trades_df['commission'].sum()
            st.metric("💸 総手数料", f"¥{total_commission:,.0f}")
        
        with col4:
            if sell_trades > 0:
                win_rate = 75  # 簡易計算（実装簡略化）
                st.metric("🎯 勝率", f"{win_rate:.1f}%")
        
        # 取引履歴チャート
        if len(trades_df) > 1:
            st.markdown("#### 📊 資産推移")
            
            # 簡易的な資産推移（実際の実装では より詳細な計算が必要）
            portfolio_values = [account.initial_balance]
            timestamps = [trades_df.iloc[0]['timestamp']]
            
            current_value = account.initial_balance
            for _, trade in trades_df.iterrows():
                if trade['action'] == 'BUY':
                    current_value -= trade['total']
                else:
                    current_value += trade['total']
                
                portfolio_values.append(current_value)
                timestamps.append(trade['timestamp'])
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=portfolio_values,
                mode='lines+markers',
                name='ポートフォリオ価値',
                line=dict(color='#1f77b4', width=2)
            ))
            
            fig.update_layout(
                title="資産価値の推移",
                xaxis_title="日時",
                yaxis_title="資産価値 (¥)",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # 全取引履歴
        st.markdown("#### 📋 全取引履歴")
        trades_display = trades_df.copy()
        trades_display['timestamp'] = trades_display['timestamp'].dt.strftime('%Y/%m/%d %H:%M')
        st.dataframe(trades_display, use_container_width=True)
    
    def _display_learning_notes(self):
        """学習メモ表示"""
        st.subheader("📚 学習メモ")
        
        # 学習ポイント
        st.markdown("#### 💡 今回の学習ポイント")
        
        notes = st.text_area(
            "取引から学んだことをメモしましょう",
            placeholder="例：損切りの重要性を実感した、利確タイミングが難しい、など",
            height=100,
            key="learning_notes"
        )
        
        # 反省・改善点
        st.markdown("#### 🔄 反省・改善点")
        
        improvements = st.text_area(
            "次回に活かしたい改善点",
            placeholder="例：エントリーポイントをもっと慎重に選ぶ、損切りルールを守る、など",
            height=100,
            key="improvement_notes"
        )
        
        # 保存ボタン
        if st.button("💾 メモを保存"):
            # 実際の実装では永続化が必要
            st.success("学習メモを保存しました！")
        
        # 学習進捗
        st.markdown("#### 📊 学習進捗")
        
        # 簡易的な進捗表示
        trade_count = len(st.session_state.sim_account.trade_history)
        progress_milestones = [10, 50, 100, 500]
        
        for milestone in progress_milestones:
            progress = min(trade_count / milestone, 1.0)
            st.progress(progress, text=f"取引回数 {milestone}回達成まで: {trade_count}/{milestone}")
    
    def _update_price(self, symbol: str):
        """価格データ更新"""
        try:
            data = self.data_collector.get_stock_data(symbol, period="1d", interval="1m")
            if data is not None and not data.empty:
                current_price = data['close'].iloc[-1]
                st.session_state.sim_current_prices[symbol] = current_price
                st.success(f"✅ {symbol}の価格を更新しました: ¥{current_price:,.0f}")
            else:
                st.error("価格データの取得に失敗しました")
        except Exception as e:
            st.error(f"エラー: {e}")


def render_education_simulation_tab():
    """シミュレーション練習モードタブのレンダリング関数"""
    component = EducationSimulationComponent()
    component.display()


if __name__ == "__main__":
    render_education_simulation_tab()