"""
ポートフォリオ分析ダッシュボードコンポーネント

ポートフォリオリスク分析、相関分析、最適化提案を可視化する。
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.risk_management.portfolio_analyzer import PortfolioAnalyzer, PortfolioHolding
from src.risk_management.risk_manager import RiskManager, Position, PositionSide, RiskParameters
from src.data_collector.stock_data_collector import StockDataCollector


class PortfolioAnalysisComponent:
    """ポートフォリオ分析ダッシュボードコンポーネント"""
    
    def __init__(self):
        """初期化"""
        self.data_collector = StockDataCollector()
        self.portfolio_analyzer = PortfolioAnalyzer()
        
        # セッション状態の初期化
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """セッション状態の初期化"""
        if 'portfolio_positions' not in st.session_state:
            st.session_state.portfolio_positions = []
        
        if 'portfolio_analyzer' not in st.session_state:
            # サンプル用RiskManagerの作成
            risk_manager = RiskManager(initial_capital=10000000)  # 1000万円
            st.session_state.portfolio_analyzer = PortfolioAnalyzer(risk_manager)
        
        if 'price_data_cache' not in st.session_state:
            st.session_state.price_data_cache = {}
    
    def display(self):
        """ポートフォリオ分析画面の表示"""
        
        # タブ分割
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 ポートフォリオ概要", "📈 リスク分析", "🔗 相関分析", "⚖️ 最適化", "🎯 ストレステスト"
        ])
        
        with tab1:
            self.show_portfolio_overview()
        
        with tab2:
            self.show_risk_analysis()
        
        with tab3:
            self.show_correlation_analysis()
        
        with tab4:
            self.show_optimization()
        
        with tab5:
            self.show_stress_test()
    
    def show_portfolio_overview(self):
        """ポートフォリオ概要の表示"""
        st.header("📊 ポートフォリオ概要")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("保有ポジション設定")
            
            # ポジション追加フォーム
            with st.form("add_position_form"):
                symbol = st.text_input("銘柄コード", value="", key="portfolio_analysis_symbol")
                
                side = st.selectbox(
                    "ポジション",
                    ["LONG", "SHORT"],
                    format_func=lambda x: "買い" if x == "LONG" else "売り"
                )
                
                quantity = st.number_input("数量", min_value=1, value=100, step=100)
                
                entry_price = st.number_input("取得価格", min_value=0.01, value=2500.0, step=0.01)
                
                current_price = st.number_input("現在価格", min_value=0.01, value=2700.0, step=0.01)
                
                if st.form_submit_button("ポジションを追加"):
                    self._add_position(symbol, side, quantity, entry_price, current_price)
            
            # 既存ポジション表示
            if st.session_state.portfolio_positions:
                st.subheader("現在のポジション")
                
                positions_data = []
                for pos in st.session_state.portfolio_positions:
                    pnl = (pos.current_price - pos.entry_price) * pos.quantity if pos.side == PositionSide.LONG else (pos.entry_price - pos.current_price) * pos.quantity
                    pnl_rate = (pnl / (pos.entry_price * pos.quantity)) * 100
                    
                    positions_data.append({
                        "銘柄": pos.symbol,
                        "ポジション": "買い" if pos.side == PositionSide.LONG else "売り",
                        "数量": f"{pos.quantity:,}",
                        "取得価格": f"¥{pos.entry_price:,.0f}",
                        "現在価格": f"¥{pos.current_price:,.0f}",
                        "評価額": f"¥{pos.current_price * pos.quantity:,.0f}",
                        "損益": f"¥{pnl:,.0f}",
                        "損益率": f"{pnl_rate:+.2f}%"
                    })
                
                df = pd.DataFrame(positions_data)
                
                # 損益に応じた色分け
                def color_pnl(val):
                    if '+' in str(val):
                        return 'background-color: #e8f5e8; color: #2e7d32'
                    elif '-' in str(val):
                        return 'background-color: #ffebee; color: #c62828'
                    return ''
                
                styled_df = df.style.applymap(color_pnl, subset=['損益', '損益率'])
                st.dataframe(styled_df, use_container_width=True)
                
                # ポジションクリアボタン
                if st.button("全ポジションをクリア"):
                    st.session_state.portfolio_positions = []
                    st.rerun()
        
        with col2:
            self.show_portfolio_summary()
    
    def _add_position(self, symbol: str, side: str, quantity: int, entry_price: float, current_price: float):
        """ポジションを追加"""
        position = Position(
            symbol=symbol,
            side=PositionSide.LONG if side == "LONG" else PositionSide.SHORT,
            entry_price=entry_price,
            quantity=quantity,
            entry_time=datetime.now(),
            stop_loss=entry_price * 0.95 if side == "LONG" else entry_price * 1.05,
            take_profit=[entry_price * 1.1] if side == "LONG" else [entry_price * 0.9],
            current_price=current_price
        )
        
        position.update_price(current_price)
        st.session_state.portfolio_positions.append(position)
        
        # RiskManagerに追加
        risk_manager = st.session_state.portfolio_analyzer.risk_manager
        if risk_manager:
            risk_manager.positions[symbol] = position
        
        st.success(f"ポジションを追加しました: {symbol}")
        st.rerun()
    
    def show_portfolio_summary(self):
        """ポートフォリオサマリー表示"""
        st.subheader("ポートフォリオサマリー")
        
        if not st.session_state.portfolio_positions:
            st.info("ポジションを追加してください")
            return
        
        # 価格データの取得と設定
        self._update_price_data()
        
        # 分析実行
        analyzer = st.session_state.portfolio_analyzer
        summary = analyzer.get_portfolio_analysis_summary()
        
        if not summary:
            st.warning("分析データを取得できませんでした")
            return
        
        # メトリクス表示
        portfolio_overview = summary.get("portfolio_overview", {})
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "総評価額",
                f"¥{portfolio_overview.get('total_value', 0):,.0f}",
                delta=None
            )
        
        with col2:
            st.metric(
                "保有銘柄数",
                f"{portfolio_overview.get('num_holdings', 0)}銘柄",
                delta=None
            )
        
        with col3:
            total_pnl = sum(
                pos.unrealized_pnl or 0 for pos in st.session_state.portfolio_positions
            )
            st.metric(
                "含み損益",
                f"¥{total_pnl:,.0f}",
                delta=f"{(total_pnl / portfolio_overview.get('total_value', 1) * 100):+.2f}%" if portfolio_overview.get('total_value') else None
            )
        
        # 構成比円グラフ
        holdings = portfolio_overview.get("holdings", [])
        if holdings:
            fig = go.Figure(data=[go.Pie(
                labels=[h["symbol"] for h in holdings],
                values=[h["weight"] for h in holdings],
                hole=0.3,
                textinfo='label+percent',
                textposition='inside'
            )])
            
            fig.update_layout(
                title="ポートフォリオ構成比",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    def show_risk_analysis(self):
        """リスク分析の表示"""
        st.header("📈 リスク分析")
        
        if not st.session_state.portfolio_positions:
            st.info("ポートフォリオにポジションを追加してください")
            return
        
        self._update_price_data()
        analyzer = st.session_state.portfolio_analyzer
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("リスク指標")
            
            risk_metrics = analyzer.calculate_risk_metrics()
            
            # VaR計算
            var_results = analyzer.calculate_portfolio_var()
            
            # メトリクス表示
            metrics_data = [
                ["VaR (95%)", f"¥{var_results.get('var_historical', 0):,.0f}"],
                ["VaR (99%)", f"¥{analyzer.calculate_portfolio_var(0.99).get('var_historical', 0):,.0f}"],
                ["CVaR (95%)", f"¥{var_results.get('cvar', 0):,.0f}"],
                ["年率ボラティリティ", f"{risk_metrics.portfolio_volatility:.2%}"],
                ["シャープレシオ", f"{risk_metrics.sharpe_ratio:.3f}"],
                ["最大ドローダウン", f"{risk_metrics.max_drawdown:.2%}"],
                ["分散効果", f"{risk_metrics.diversification_ratio:.2f}"]
            ]
            
            metrics_df = pd.DataFrame(metrics_data, columns=["指標", "値"])
            st.table(metrics_df)
        
        with col2:
            st.subheader("リスク分布")
            
            # VaRの可視化
            confidence_levels = [0.90, 0.95, 0.99]
            var_values = []
            
            for cl in confidence_levels:
                var_result = analyzer.calculate_portfolio_var(cl)
                var_values.append(var_result.get('var_historical', 0))
            
            fig = go.Figure(data=[
                go.Bar(
                    x=[f"{cl:.0%}" for cl in confidence_levels],
                    y=var_values,
                    text=[f"¥{val:,.0f}" for val in var_values],
                    textposition='auto',
                    marker_color='red',
                    opacity=0.7
                )
            ])
            
            fig.update_layout(
                title="信頼度別VaR",
                xaxis_title="信頼度",
                yaxis_title="VaR (円)",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # 最適化提案
        summary = analyzer.get_portfolio_analysis_summary()
        suggestions = summary.get("optimization_suggestions", [])
        
        if suggestions:
            st.subheader("💡 最適化提案")
            for suggestion in suggestions:
                st.info(suggestion)
    
    def show_correlation_analysis(self):
        """相関分析の表示"""
        st.header("🔗 相関分析")
        
        if not st.session_state.portfolio_positions:
            st.info("ポートフォリオにポジションを追加してください")
            return
        
        self._update_price_data()
        analyzer = st.session_state.portfolio_analyzer
        
        correlation_analysis = analyzer.analyze_correlations()
        
        if correlation_analysis.correlation_matrix.empty:
            st.warning("相関分析に十分なデータがありません")
            return
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("相関行列")
            
            # 相関行列ヒートマップ
            corr_matrix = correlation_analysis.correlation_matrix
            
            fig = go.Figure(data=go.Heatmap(
                z=corr_matrix.values,
                x=corr_matrix.columns,
                y=corr_matrix.index,
                colorscale='RdBu',
                zmid=0,
                zmin=-1,
                zmax=1,
                text=np.round(corr_matrix.values, 3),
                texttemplate="%{text}",
                textfont={"size": 10},
                hovertemplate='%{x} vs %{y}<br>相関係数: %{z:.3f}<extra></extra>'
            ))
            
            fig.update_layout(
                title="銘柄間相関行列",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("相関統計")
            
            # 相関統計表示
            st.metric("平均相関", f"{correlation_analysis.average_correlation:.3f}")
            st.metric("最大相関", f"{correlation_analysis.max_correlation:.3f}")
            st.metric("最小相関", f"{correlation_analysis.min_correlation:.3f}")
            
            # 高相関ペア
            if correlation_analysis.high_correlation_pairs:
                st.subheader("高相関ペア（|r| ≥ 0.7）")
                
                high_corr_data = []
                for symbol1, symbol2, corr in correlation_analysis.high_correlation_pairs:
                    high_corr_data.append({
                        "銘柄1": symbol1,
                        "銘柄2": symbol2,
                        "相関係数": f"{corr:.3f}"
                    })
                
                if high_corr_data:
                    df = pd.DataFrame(high_corr_data)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("高相関ペアはありません")
            else:
                st.info("高相関ペアはありません")
    
    def show_optimization(self):
        """最適化の表示"""
        st.header("⚖️ ポートフォリオ最適化")
        
        if not st.session_state.portfolio_positions:
            st.info("ポートフォリオにポジションを追加してください")
            return
        
        self._update_price_data()
        analyzer = st.session_state.portfolio_analyzer
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("最適化設定")
            
            optimization_type = st.selectbox(
                "最適化タイプ",
                ["max_sharpe", "min_variance", "target_return"],
                format_func=lambda x: {
                    "max_sharpe": "最大シャープレシオ",
                    "min_variance": "最小分散",
                    "target_return": "目標リターン制約"
                }[x]
            )
            
            target_return = None
            if optimization_type == "target_return":
                target_return = st.number_input(
                    "目標年率リターン",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.1,
                    step=0.01,
                    format="%.2f"
                )
            
            if st.button("最適化実行"):
                with st.spinner("最適化計算中..."):
                    result = analyzer.optimize_portfolio(optimization_type, target_return)
                    
                    if result.optimal_weights:
                        st.success("最適化完了")
                        
                        # 最適化結果表示
                        st.subheader("最適化結果")
                        
                        st.metric("期待リターン", f"{result.expected_return:.2%}")
                        st.metric("期待ボラティリティ", f"{result.expected_volatility:.2%}")
                        st.metric("シャープレシオ", f"{result.sharpe_ratio:.3f}")
                        
                        # 最適ウェイト表示
                        weights_data = [
                            {"銘柄": symbol, "最適ウェイト": f"{weight:.1%}"}
                            for symbol, weight in result.optimal_weights.items()
                        ]
                        weights_df = pd.DataFrame(weights_data)
                        st.dataframe(weights_df, use_container_width=True)
                        
                        # 現在vs最適の比較
                        st.subheader("現在 vs 最適配分")
                        
                        current_weights = {}
                        total_value = sum(pos.current_price * pos.quantity for pos in st.session_state.portfolio_positions)
                        
                        for pos in st.session_state.portfolio_positions:
                            weight = (pos.current_price * pos.quantity) / total_value
                            current_weights[pos.symbol] = weight
                        
                        comparison_data = []
                        for symbol in result.optimal_weights.keys():
                            current = current_weights.get(symbol, 0)
                            optimal = result.optimal_weights[symbol]
                            diff = optimal - current
                            
                            comparison_data.append({
                                "銘柄": symbol,
                                "現在": f"{current:.1%}",
                                "最適": f"{optimal:.1%}",
                                "差分": f"{diff:+.1%}"
                            })
                        
                        comp_df = pd.DataFrame(comparison_data)
                        st.dataframe(comp_df, use_container_width=True)
                    
                    else:
                        st.error("最適化に失敗しました")
        
        with col2:
            st.subheader("効率的フロンティア")
            
            if st.button("効率的フロンティア生成"):
                with st.spinner("効率的フロンティア計算中..."):
                    frontier = analyzer.generate_efficient_frontier()
                    
                    if frontier["returns"]:
                        fig = go.Figure()
                        
                        fig.add_trace(go.Scatter(
                            x=frontier["volatilities"],
                            y=frontier["returns"],
                            mode='lines+markers',
                            name='効率的フロンティア',
                            line=dict(color='blue'),
                            hovertemplate='リスク: %{x:.2%}<br>リターン: %{y:.2%}<extra></extra>'
                        ))
                        
                        # 現在のポートフォリオをプロット
                        current_metrics = analyzer.calculate_risk_metrics()
                        current_return = sum(
                            pos.unrealized_pnl or 0 for pos in st.session_state.portfolio_positions
                        ) / sum(pos.current_price * pos.quantity for pos in st.session_state.portfolio_positions) * 252
                        
                        fig.add_trace(go.Scatter(
                            x=[current_metrics.portfolio_volatility],
                            y=[current_return],
                            mode='markers',
                            name='現在のポートフォリオ',
                            marker=dict(size=10, color='red'),
                            hovertemplate='現在のポートフォリオ<br>リスク: %{x:.2%}<br>リターン: %{y:.2%}<extra></extra>'
                        ))
                        
                        fig.update_layout(
                            title="効率的フロンティア",
                            xaxis_title="リスク（ボラティリティ）",
                            yaxis_title="リターン",
                            height=400
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.error("効率的フロンティアの生成に失敗しました")
    
    def show_stress_test(self):
        """ストレステストの表示"""
        st.header("🎯 ストレステスト")
        
        if not st.session_state.portfolio_positions:
            st.info("ポートフォリオにポジションを追加してください")
            return
        
        self._update_price_data()
        analyzer = st.session_state.portfolio_analyzer
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("モンテカルロシミュレーション設定")
            
            num_simulations = st.selectbox(
                "シミュレーション回数",
                [1000, 5000, 10000],
                index=1
            )
            
            time_horizon = st.selectbox(
                "時間軸（日数）",
                [1, 5, 10, 22, 63, 252],
                index=3,
                format_func=lambda x: f"{x}日" + (" (1営業日)" if x == 1 else " (1週間)" if x == 5 else " (2週間)" if x == 10 else " (1ヶ月)" if x == 22 else " (3ヶ月)" if x == 63 else " (1年)" if x == 252 else "")
            )
            
            if st.button("ストレステスト実行"):
                with st.spinner("モンテカルロシミュレーション実行中..."):
                    stress_result = analyzer.monte_carlo_stress_test(num_simulations, time_horizon)
                    
                    if stress_result:
                        st.success("ストレステスト完了")
                        
                        # 結果表示
                        st.subheader("ストレステスト結果")
                        
                        metrics_data = [
                            ["VaR (95%)", f"¥{stress_result.get('var_95', 0):,.0f}"],
                            ["VaR (99%)", f"¥{stress_result.get('var_99', 0):,.0f}"],
                            ["期待損失", f"¥{stress_result.get('expected_loss', 0):,.0f}"],
                            ["最悪ケース損失", f"¥{stress_result.get('worst_case', 0):,.0f}"],
                            ["損失確率", f"{stress_result.get('probability_of_loss', 0):.1f}%"]
                        ]
                        
                        metrics_df = pd.DataFrame(metrics_data, columns=["項目", "値"])
                        st.table(metrics_df)
                    else:
                        st.error("ストレステストに失敗しました")
        
        with col2:
            if st.button("シナリオ分析"):
                st.subheader("市場ショックシナリオ")
                
                # 市場急落シナリオの想定
                scenarios = [
                    {"name": "軽度下落", "shock": -0.05, "color": "orange"},
                    {"name": "中程度下落", "shock": -0.10, "color": "red"},
                    {"name": "重度下落", "shock": -0.20, "color": "darkred"},
                    {"name": "極度下落", "shock": -0.30, "color": "black"}
                ]
                
                total_value = sum(pos.current_price * pos.quantity for pos in st.session_state.portfolio_positions)
                
                scenario_data = []
                for scenario in scenarios:
                    shock_loss = total_value * abs(scenario["shock"])
                    scenario_data.append({
                        "シナリオ": scenario["name"],
                        "市場下落": f"{scenario['shock']:.0%}",
                        "推定損失": f"¥{shock_loss:,.0f}",
                        "残存価値": f"¥{total_value - shock_loss:,.0f}"
                    })
                
                df = pd.DataFrame(scenario_data)
                st.dataframe(df, use_container_width=True)
                
                # バーチャート
                fig = go.Figure(data=[
                    go.Bar(
                        x=[s["name"] for s in scenarios],
                        y=[total_value * abs(s["shock"]) for s in scenarios],
                        text=[f"¥{total_value * abs(s['shock']):,.0f}" for s in scenarios],
                        textposition='auto',
                        marker_color=[s["color"] for s in scenarios],
                        opacity=0.7
                    )
                ])
                
                fig.update_layout(
                    title="市場ショックシナリオ別損失額",
                    xaxis_title="シナリオ",
                    yaxis_title="推定損失額（円）",
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
    
    def _update_price_data(self):
        """価格データを更新"""
        try:
            symbols = [pos.symbol for pos in st.session_state.portfolio_positions]
            if not symbols:
                return
            
            price_data = {}
            for symbol in symbols:
                try:
                    # キャッシュチェック
                    cache_key = f"{symbol}_price_data"
                    if cache_key in st.session_state.price_data_cache:
                        cache_time, data = st.session_state.price_data_cache[cache_key]
                        if (datetime.now() - cache_time).seconds < 300:  # 5分キャッシュ
                            price_data[symbol] = data
                            continue
                    
                    # データ取得
                    data = self.data_collector.get_stock_data(symbol, period="1y", interval="1d")
                    if data is not None and not data.empty:
                        price_data[symbol] = data
                        # キャッシュ更新
                        st.session_state.price_data_cache[cache_key] = (datetime.now(), data)
                
                except Exception as e:
                    st.warning(f"価格データ取得エラー ({symbol}): {e}")
                    continue
            
            if price_data:
                st.session_state.portfolio_analyzer.set_price_history(price_data)
        
        except Exception as e:
            st.error(f"価格データ更新エラー: {e}")


def render_portfolio_analysis_tab():
    """ポートフォリオ分析タブのレンダリング"""
    component = PortfolioAnalysisComponent()
    component.display()