"""
税務・コスト計算コンポーネント

投資に関わる税金や手数料などのコスト計算をダッシュボードで表示する。
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, date, timedelta
from decimal import Decimal
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.tax_calculation.tax_calculator import TaxCalculator, TradeRecord
from src.tax_calculation.fee_calculator import FeeCalculator, MarketType
from src.tax_calculation.nisa_manager import NisaManager, NisaInvestment, NisaType
from src.tax_calculation.profit_loss_simulator import ProfitLossSimulator, TradePosition


class TaxCalculationComponent:
    """税務・コスト計算コンポーネント"""
    
    def __init__(self):
        """初期化"""
        self.tax_calculator = TaxCalculator()
        self.fee_calculator = FeeCalculator()
        self.nisa_manager = NisaManager()
        self.pnl_simulator = ProfitLossSimulator()
        
        # セッション状態の初期化
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """セッション状態の初期化"""
        if 'tax_trades' not in st.session_state:
            st.session_state.tax_trades = []
        
        if 'nisa_investments' not in st.session_state:
            st.session_state.nisa_investments = []
        
        if 'pnl_positions' not in st.session_state:
            st.session_state.pnl_positions = []
    
    def display(self):
        """税務・コスト計算画面の表示"""
        
        # タブ分割
        tab1, tab2, tab3, tab4 = st.tabs([
            "💰 手数料計算", "📊 税務計算", "🎯 NISA管理", "📈 損益通算"
        ])
        
        with tab1:
            self.show_fee_calculation()
        
        with tab2:
            self.show_tax_calculation()
        
        with tab3:
            self.show_nisa_management()
        
        with tab4:
            self.show_profit_loss_simulation()
    
    def show_fee_calculation(self):
        """手数料計算の表示"""
        st.header("💰 証券会社別手数料計算")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("計算条件設定")
            
            # 投資金額入力
            amount = st.number_input(
                "投資金額（円）",
                min_value=1000,
                max_value=10000000,
                value=100000,
                step=10000
            )
            
            # 市場区分選択
            market_type_names = {
                "東京証券取引所": MarketType.TOKYO_STOCK,
                "米国株": MarketType.US_STOCK,
                "その他外国株": MarketType.FOREIGN_STOCK
            }
            
            selected_market = st.selectbox(
                "市場区分",
                list(market_type_names.keys())
            )
            market_type = market_type_names[selected_market]
            
            # 手数料計算実行
            if st.button("手数料を計算"):
                self._calculate_and_display_fees(Decimal(str(amount)), market_type)
        
        with col2:
            st.subheader("証券会社比較")
            self._show_broker_comparison(Decimal(str(amount)), market_type)
    
    def _calculate_and_display_fees(self, amount: Decimal, market_type: MarketType):
        """手数料計算と表示"""
        try:
            # 証券会社別比較
            comparison = self.fee_calculator.compare_brokers(amount, market_type)
            
            # 最安証券会社
            cheapest_broker, cheapest_fee = self.fee_calculator.get_cheapest_broker(amount, market_type)
            
            # 結果表示
            st.success(f"最安手数料: {cheapest_broker}証券 - {cheapest_fee}円")
            
            # 比較表作成
            comparison_data = []
            for broker, fee in comparison.items():
                round_trip_fee = fee * 2
                fee_rate = (fee / amount * 100) if amount > 0 else Decimal('0')
                
                impact = self.fee_calculator.calculate_fee_impact(amount, broker, market_type)
                
                comparison_data.append({
                    "証券会社": broker,
                    "片道手数料": f"{fee:,.0f}円",
                    "往復手数料": f"{round_trip_fee:,.0f}円",
                    "手数料率": f"{fee_rate:.3f}%",
                    "損益分岐点": f"{impact['breakeven_rate']:.3f}%"
                })
            
            df = pd.DataFrame(comparison_data)
            st.dataframe(df, use_container_width=True)
            
        except Exception as e:
            st.error(f"手数料計算エラー: {e}")
    
    def _show_broker_comparison(self, amount: Decimal, market_type: MarketType):
        """証券会社比較チャート"""
        try:
            comparison = self.fee_calculator.compare_brokers(amount, market_type)
            
            if comparison:
                # 手数料比較バーチャート
                brokers = list(comparison.keys())
                fees = [float(fee) for fee in comparison.values()]
                
                fig = go.Figure(data=[
                    go.Bar(
                        x=brokers,
                        y=fees,
                        text=[f'{fee:.0f}円' for fee in fees],
                        textposition='auto',
                        marker_color=['#2E8B57' if fee == min(fees) else '#4682B4' for fee in fees]
                    )
                ])
                
                fig.update_layout(
                    title=f"証券会社別手数料比較 ({market_type.value})",
                    xaxis_title="証券会社",
                    yaxis_title="手数料（円）",
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # 投資金額別手数料推移
                amounts = [10000, 50000, 100000, 200000, 500000, 1000000, 3000000]
                
                fig2 = go.Figure()
                
                for broker in brokers:
                    broker_fees = []
                    for amt in amounts:
                        fee = self.fee_calculator.calculate_fee(Decimal(str(amt)), broker, market_type)
                        broker_fees.append(float(fee))
                    
                    fig2.add_trace(go.Scatter(
                        x=amounts,
                        y=broker_fees,
                        mode='lines+markers',
                        name=f"{broker}証券",
                        hovertemplate=f"{broker}証券<br>投資額: %{{x:,}}円<br>手数料: %{{y:.0f}}円<extra></extra>"
                    ))
                
                fig2.update_layout(
                    title="投資金額別手数料推移",
                    xaxis_title="投資金額（円）",
                    yaxis_title="手数料（円）",
                    height=400,
                    xaxis_type="log"
                )
                
                st.plotly_chart(fig2, use_container_width=True)
        
        except Exception as e:
            st.error(f"比較チャート作成エラー: {e}")
    
    def show_tax_calculation(self):
        """税務計算の表示"""
        st.header("📊 投資税務計算")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("取引記録入力")
            
            # 取引記録フォーム
            with st.form("trade_form"):
                symbol = st.text_input("銘柄コード", value="7203.T", key="tax_calc_trade_symbol")
                
                action = st.selectbox("売買区分", ["buy", "sell"])
                
                quantity = st.number_input("数量", min_value=1, value=100)
                
                price = st.number_input("価格", min_value=0.01, value=2500.0, step=0.01)
                
                fee = st.number_input("手数料", min_value=0.0, value=55.0, step=1.0)
                
                trade_date = st.date_input("取引日", value=date.today())
                
                account_type = st.selectbox(
                    "口座区分", 
                    ["taxable", "nisa", "tsumitate_nisa"],
                    format_func=lambda x: {"taxable": "課税口座", "nisa": "NISA", "tsumitate_nisa": "つみたてNISA"}[x]
                )
                
                if st.form_submit_button("取引を追加"):
                    trade = TradeRecord(
                        symbol=symbol,
                        date=trade_date,
                        action=action,
                        quantity=int(quantity),
                        price=Decimal(str(price)),
                        fee=Decimal(str(fee)),
                        account_type=account_type
                    )
                    
                    self.tax_calculator.add_trade(trade)
                    st.session_state.tax_trades.append(trade)
                    st.success("取引を追加しました")
        
        with col2:
            st.subheader("税務サマリー")
            
            if st.session_state.tax_trades:
                # 現在価格（サンプル）
                current_prices = {
                    "7203.T": Decimal("2700"),
                    "9984.T": Decimal("8200"),
                    "6758.T": Decimal("16500")
                }
                
                # 税務サマリー取得
                current_year = datetime.now().year
                summary = self.tax_calculator.get_tax_summary(current_prices, current_year)
                
                # メトリクス表示
                col2_1, col2_2 = st.columns(2)
                
                with col2_1:
                    st.metric(
                        "実現利益",
                        f"{summary.realized_profit:,.0f}円",
                        delta=None
                    )
                    
                    st.metric(
                        "含み益",
                        f"{summary.unrealized_profit:,.0f}円",
                        delta=None
                    )
                
                with col2_2:
                    st.metric(
                        "譲渡益税",
                        f"{summary.capital_gains_tax:,.0f}円",
                        delta=None
                    )
                    
                    st.metric(
                        "税引き後利益",
                        f"{summary.net_profit:,.0f}円",
                        delta=f"{summary.net_profit - summary.realized_profit:,.0f}円"
                    )
                
                # 取引履歴表示
                st.subheader("取引履歴")
                
                trades_data = []
                for trade in st.session_state.tax_trades:
                    trades_data.append({
                        "日付": trade.date.strftime("%Y-%m-%d"),
                        "銘柄": trade.symbol,
                        "売買": "買い" if trade.action == "buy" else "売り",
                        "数量": f"{trade.quantity:,}株",
                        "価格": f"{trade.price:,.0f}円",
                        "手数料": f"{trade.fee:,.0f}円",
                        "口座": {"taxable": "課税", "nisa": "NISA", "tsumitate_nisa": "つみたて"}[trade.account_type]
                    })
                
                if trades_data:
                    df = pd.DataFrame(trades_data)
                    st.dataframe(df, use_container_width=True)
            
            else:
                st.info("取引記録がありません。左側のフォームから取引を追加してください。")
    
    def show_nisa_management(self):
        """NISA管理の表示"""
        st.header("🎯 NISA枠管理")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("NISA投資入力")
            
            # NISA投資フォーム
            with st.form("nisa_form"):
                symbol = st.text_input("銘柄コード", value="1570.T", key="tax_calc_nisa_symbol")
                
                amount = st.number_input("投資金額（円）", min_value=1000, value=100000, step=1000)
                
                nisa_type_names = {
                    "成長投資枠": NisaType.GROWTH,
                    "つみたて投資枠": NisaType.TSUMITATE
                }
                
                selected_nisa_type = st.selectbox(
                    "NISA区分",
                    list(nisa_type_names.keys())
                )
                nisa_type = nisa_type_names[selected_nisa_type]
                
                investment_date = st.date_input("投資日", value=date.today())
                
                if st.form_submit_button("NISA投資を追加"):
                    investment = NisaInvestment(
                        symbol=symbol,
                        date=investment_date,
                        amount=Decimal(str(amount)),
                        nisa_type=nisa_type
                    )
                    
                    if self.nisa_manager.add_investment(investment):
                        st.session_state.nisa_investments.append(investment)
                        st.success("NISA投資を追加しました")
                    else:
                        st.error("NISA投資限度額を超過しています")
        
        with col2:
            st.subheader("NISA利用状況")
            
            current_year = datetime.now().year
            status = self.nisa_manager.get_nisa_status(current_year)
            
            # NISA枠利用状況
            st.metric(
                "成長投資枠利用額",
                f"{status.growth_used:,.0f}円",
                delta=f"残り {status.growth_remaining:,.0f}円"
            )
            
            st.metric(
                "つみたて投資枠利用額",
                f"{status.tsumitate_used:,.0f}円",
                delta=f"残り {status.tsumitate_remaining:,.0f}円"
            )
            
            # NISA枠使用率
            total_limit = Decimal('3600000')  # 年間限度額合計
            usage_rate = (status.total_used / total_limit * 100) if total_limit > 0 else 0
            
            st.metric(
                "年間枠使用率",
                f"{usage_rate:.1f}%",
                delta=f"{status.total_used:,.0f}円 / {total_limit:,.0f}円"
            )
            
            # NISA枠可視化
            fig = go.Figure(data=[
                go.Bar(
                    name='使用済み',
                    x=['成長投資枠', 'つみたて投資枠'],
                    y=[float(status.growth_used), float(status.tsumitate_used)],
                    marker_color='#FF6B6B'
                ),
                go.Bar(
                    name='残り枠',
                    x=['成長投資枠', 'つみたて投資枠'],
                    y=[float(status.growth_remaining), float(status.tsumitate_remaining)],
                    marker_color='#4ECDC4'
                )
            ])
            
            fig.update_layout(
                title=f"{current_year}年 NISA枠利用状況",
                xaxis_title="NISA区分",
                yaxis_title="金額（円）",
                barmode='stack',
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # NISA投資履歴
        if st.session_state.nisa_investments:
            st.subheader("NISA投資履歴")
            
            nisa_data = []
            for inv in st.session_state.nisa_investments:
                nisa_data.append({
                    "日付": inv.date.strftime("%Y-%m-%d"),
                    "銘柄": inv.symbol,
                    "金額": f"{inv.amount:,.0f}円",
                    "区分": {"growth": "成長投資枠", "tsumitate": "つみたて投資枠"}[inv.nisa_type.value]
                })
            
            df = pd.DataFrame(nisa_data)
            st.dataframe(df, use_container_width=True)
    
    def show_profit_loss_simulation(self):
        """損益通算シミュレーションの表示"""
        st.header("📈 損益通算シミュレーション")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("ポジション入力")
            
            # ポジション入力フォーム
            with st.form("position_form"):
                symbol = st.text_input("銘柄コード", value="7203.T", key="tax_calc_profit_loss_symbol")
                
                entry_price = st.number_input("取得価格", min_value=0.01, value=2500.0, step=0.01)
                
                quantity = st.number_input("数量", min_value=1, value=100)
                
                current_price = st.number_input("現在価格", min_value=0.01, value=2700.0, step=0.01)
                
                entry_date = st.date_input("取得日", value=date.today() - timedelta(days=30))
                
                if st.form_submit_button("ポジションを追加"):
                    position = TradePosition(
                        symbol=symbol,
                        entry_date=entry_date,
                        entry_price=Decimal(str(entry_price)),
                        quantity=int(quantity),
                        current_price=Decimal(str(current_price))
                    )
                    
                    self.pnl_simulator.add_position(position)
                    st.session_state.pnl_positions.append(position)
                    st.success("ポジションを追加しました")
        
        with col2:
            st.subheader("損益分析")
            
            if st.session_state.pnl_positions:
                # 損益計算
                unrealized_profit, unrealized_loss = self.pnl_simulator.calculate_unrealized_pnl()
                
                # メトリクス表示
                st.metric(
                    "含み益",
                    f"{unrealized_profit:,.0f}円",
                    delta=None
                )
                
                st.metric(
                    "含み損",
                    f"{unrealized_loss:,.0f}円",
                    delta=None
                )
                
                net_pnl = unrealized_profit - unrealized_loss
                st.metric(
                    "純含み損益",
                    f"{net_pnl:,.0f}円",
                    delta=None,
                    delta_color="normal" if net_pnl >= 0 else "inverse"
                )
                
                # 税務最適化シミュレーション
                current_year = datetime.now().year
                optimization = self.pnl_simulator.simulate_tax_optimization(current_year)
                
                st.subheader("税務最適化提案")
                
                if optimization.optimization_suggestions:
                    for suggestion in optimization.optimization_suggestions:
                        st.info(suggestion)
                else:
                    st.success("現在の状況は税務的に最適化されています")
        
        # ポジション一覧
        if st.session_state.pnl_positions:
            st.subheader("保有ポジション一覧")
            
            position_data = []
            for pos in st.session_state.pnl_positions:
                if not pos.is_closed:
                    unrealized_pnl = pos.unrealized_pnl or Decimal('0')
                    pnl_rate = (unrealized_pnl / (pos.entry_price * pos.quantity) * 100) if pos.entry_price > 0 else 0
                    
                    position_data.append({
                        "銘柄": pos.symbol,
                        "取得日": pos.entry_date.strftime("%Y-%m-%d"),
                        "取得価格": f"{pos.entry_price:,.0f}円",
                        "現在価格": f"{pos.current_price:,.0f}円" if pos.current_price else "未設定",
                        "数量": f"{pos.quantity:,}株",
                        "含み損益": f"{unrealized_pnl:,.0f}円",
                        "損益率": f"{pnl_rate:+.2f}%"
                    })
            
            if position_data:
                df = pd.DataFrame(position_data)
                
                # 損益に応じた色分け
                def color_pnl(val):
                    if '円' in val:
                        amount = float(val.replace('円', '').replace(',', ''))
                        if amount > 0:
                            return 'background-color: #e8f5e8; color: #2e7d32'
                        elif amount < 0:
                            return 'background-color: #ffebee; color: #c62828'
                    return ''
                
                styled_df = df.style.applymap(color_pnl, subset=['含み損益'])
                st.dataframe(styled_df, use_container_width=True)


def render_tax_calculation_tab():
    """税務・コスト計算タブのレンダリング"""
    component = TaxCalculationComponent()
    component.display()