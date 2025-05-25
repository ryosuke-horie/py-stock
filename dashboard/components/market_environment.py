"""市場環境分析のダッシュボードコンポーネント"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from typing import Dict, List

from src.technical_analysis.market_environment import (
    MarketEnvironmentAnalyzer, 
    MarketSentiment, 
    RiskState
)
from src.data_collector.stock_data_collector import StockDataCollector


def render_market_environment_tab():
    """市場環境分析タブのレンダリング"""
    st.header("📊 市場環境分析")
    
    # サイドバーで設定
    with st.sidebar:
        st.subheader("市場環境分析設定")
        
        # 分析期間の選択
        period = st.selectbox(
            "分析期間",
            ["1d", "5d", "1mo", "3mo"],
            index=1,
            help="市場環境を分析する期間"
        )
        
        # データ間隔の選択
        interval = st.selectbox(
            "データ間隔",
            ["1m", "5m", "1h", "1d"],
            index=3,
            help="価格データの時間間隔"
        )
        
        # 自動更新の設定
        auto_refresh = st.checkbox("自動更新", value=False)
        if auto_refresh:
            refresh_interval = st.slider(
                "更新間隔（秒）",
                min_value=30,
                max_value=300,
                value=60,
                step=30
            )
            st.info(f"{refresh_interval}秒ごとに自動更新されます")
    
    # 分析の実行
    analyzer = MarketEnvironmentAnalyzer()
    
    try:
        with st.spinner("市場環境を分析中..."):
            # 市場環境分析の実行
            env = analyzer.analyze_market_environment(period=period, interval=interval)
            report = analyzer.get_daily_market_report()
        
        # サマリーセクション
        render_market_summary(env, report)
        
        # タブで詳細情報を表示
        tab1, tab2, tab3, tab4 = st.tabs([
            "📈 インデックス", 
            "🏢 セクター分析", 
            "⚠️ リスク評価",
            "📊 詳細レポート"
        ])
        
        with tab1:
            render_indices_performance(env.indices_performance)
        
        with tab2:
            render_sector_analysis(env.sector_performance)
        
        with tab3:
            render_risk_assessment(env)
        
        with tab4:
            render_detailed_report(report)
            
    except Exception as e:
        st.error(f"市場環境分析でエラーが発生しました: {str(e)}")
        st.info("インターネット接続を確認し、しばらくしてから再度お試しください。")


def render_market_summary(env, report):
    """市場サマリーの表示"""
    st.subheader("📋 市場環境サマリー")
    
    # メトリクスの表示
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # 市場センチメントの色分け
        sentiment_color = get_sentiment_color(env.market_sentiment)
        st.metric(
            "市場センチメント",
            env.market_sentiment.value,
            delta=None,
            help="VIX指数と市場動向から判定"
        )
        st.markdown(f"<div style='background-color:{sentiment_color};height:4px;'></div>", 
                   unsafe_allow_html=True)
    
    with col2:
        # リスク状態の色分け
        risk_color = get_risk_state_color(env.risk_state)
        st.metric(
            "リスク状態",
            env.risk_state.value,
            delta=None,
            help="市場全体のリスクオン/オフ状態"
        )
        st.markdown(f"<div style='background-color:{risk_color};height:4px;'></div>", 
                   unsafe_allow_html=True)
    
    with col3:
        st.metric(
            "VIX指数",
            f"{env.vix_level:.2f}",
            delta=f"{get_vix_change(env.vix_level):.2f}%",
            help="市場の恐怖指数"
        )
    
    with col4:
        if env.market_breadth:
            breadth_ratio = env.market_breadth.get('advance_decline_ratio', 0)
            st.metric(
                "上昇セクター比率",
                f"{breadth_ratio:.0f}%",
                delta=None,
                help="上昇しているセクターの割合"
            )
    
    # 投資推奨の表示
    st.info(f"💡 **投資推奨**: {env.recommendation}")
    
    # 主要なリスクと機会の表示
    col1, col2 = st.columns(2)
    
    with col1:
        if env.risk_factors:
            st.warning(f"**リスク要因** ({len(env.risk_factors)}件)")
            for risk in env.risk_factors[:3]:  # 上位3件を表示
                st.write(f"• {risk}")
            if len(env.risk_factors) > 3:
                st.write(f"... 他{len(env.risk_factors) - 3}件")
    
    with col2:
        if env.opportunities:
            st.success(f"**投資機会** ({len(env.opportunities)}件)")
            for opp in env.opportunities[:3]:  # 上位3件を表示
                st.write(f"• {opp}")
            if len(env.opportunities) > 3:
                st.write(f"... 他{len(env.opportunities) - 3}件")


def render_indices_performance(indices_performance: Dict[str, Dict[str, float]]):
    """インデックスパフォーマンスの表示"""
    st.subheader("📈 主要インデックスパフォーマンス")
    
    if not indices_performance:
        st.warning("インデックスデータを取得できませんでした")
        return
    
    # データフレームの作成
    data = []
    for index_name, perf in indices_performance.items():
        row = {"インデックス": get_index_display_name(index_name)}
        row.update(perf)
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # パフォーマンステーブルの表示
    if 'daily' in df.columns:
        # スタイル付きのデータフレーム表示
        styled_df = df.style.format({
            'daily': '{:.2f}%',
            'weekly': '{:.2f}%',
            'monthly': '{:.2f}%',
            'volatility': '{:.2f}%',
            'rsi': '{:.1f}'
        }).background_gradient(subset=['daily', 'weekly', 'monthly'], cmap='RdYlGn', center=0)
        
        st.dataframe(styled_df, use_container_width=True)
    
    # パフォーマンスチャート
    if len(df) > 0 and 'daily' in df.columns:
        fig = go.Figure()
        
        # 日次リターンの棒グラフ
        colors = ['red' if x < 0 else 'green' for x in df['daily']]
        fig.add_trace(go.Bar(
            x=df['インデックス'],
            y=df['daily'],
            name='日次リターン',
            marker_color=colors
        ))
        
        fig.update_layout(
            title="インデックス日次パフォーマンス",
            xaxis_title="インデックス",
            yaxis_title="リターン (%)",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # RSIゲージの表示
    if 'rsi' in df.columns:
        st.subheader("📊 RSI指標")
        cols = st.columns(min(len(df), 4))
        
        for idx, (_, row) in enumerate(df.iterrows()):
            if idx < len(cols) and pd.notna(row.get('rsi')):
                with cols[idx]:
                    render_rsi_gauge(row['インデックス'], row['rsi'])


def render_sector_analysis(sector_performance: Dict[str, float]):
    """セクター分析の表示"""
    st.subheader("🏢 セクター別パフォーマンス")
    
    if not sector_performance:
        st.warning("セクターデータを取得できませんでした")
        return
    
    # データの準備
    sectors_df = pd.DataFrame([
        {"セクター": get_sector_display_name(k), "パフォーマンス": v}
        for k, v in sector_performance.items()
    ])
    sectors_df = sectors_df.sort_values("パフォーマンス", ascending=False)
    
    # セクターパフォーマンスの棒グラフ
    fig = px.bar(
        sectors_df,
        x="パフォーマンス",
        y="セクター",
        orientation='h',
        color="パフォーマンス",
        color_continuous_scale="RdYlGn",
        color_continuous_midpoint=0
    )
    
    fig.update_layout(
        title="セクター別パフォーマンス（期間リターン）",
        xaxis_title="リターン (%)",
        yaxis_title="",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # セクターローテーション分析
    st.subheader("🔄 セクターローテーション分析")
    
    # 上位・下位セクターの表示
    col1, col2 = st.columns(2)
    
    with col1:
        st.success("**好調セクター TOP3**")
        for idx, row in sectors_df.head(3).iterrows():
            st.write(f"• {row['セクター']}: {row['パフォーマンス']:.2f}%")
    
    with col2:
        st.error("**不調セクター TOP3**")
        for idx, row in sectors_df.tail(3).iterrows():
            st.write(f"• {row['セクター']}: {row['パフォーマンス']:.2f}%")


def render_risk_assessment(env):
    """リスク評価の表示"""
    st.subheader("⚠️ リスク評価")
    
    # リスクメーター
    risk_score = len(env.risk_factors)
    max_risk = 10
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=risk_score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "リスクレベル"},
        gauge={
            'axis': {'range': [None, max_risk]},
            'bar': {'color': "darkred"},
            'steps': [
                {'range': [0, 3], 'color': "lightgreen"},
                {'range': [3, 6], 'color': "yellow"},
                {'range': [6, max_risk], 'color': "lightcoral"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 7
            }
        }
    ))
    
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)
    
    # リスク要因の詳細
    if env.risk_factors:
        st.warning(f"**検出されたリスク要因** ({len(env.risk_factors)}件)")
        for i, risk in enumerate(env.risk_factors, 1):
            st.write(f"{i}. {risk}")
    else:
        st.success("現在、重大なリスク要因は検出されていません")
    
    # VIX履歴チャート（プレースホルダー）
    st.subheader("📈 VIX指数トレンド")
    st.info("VIX指数の履歴チャートは今後実装予定です")


def render_detailed_report(report: Dict):
    """詳細レポートの表示"""
    st.subheader("📊 詳細市場レポート")
    
    # レポート日時
    st.write(f"**レポート生成日時**: {report['report_date']}")
    
    # エグゼクティブサマリー
    with st.expander("📋 エグゼクティブサマリー", expanded=True):
        summary = report['executive_summary']
        st.json(summary)
    
    # インデックス詳細
    with st.expander("📈 インデックス詳細パフォーマンス"):
        st.json(report['indices_performance'])
    
    # セクター分析詳細
    with st.expander("🏢 セクター分析詳細"):
        st.json(report['sector_analysis'])
    
    # 市場の幅
    with st.expander("📊 市場の幅（Market Breadth）"):
        st.json(report['market_breadth'])
    
    # リスク評価詳細
    with st.expander("⚠️ リスク評価詳細"):
        st.json(report['risk_assessment'])
    
    # 投資機会
    with st.expander("💡 投資機会"):
        opportunities = report.get('opportunities', [])
        if opportunities:
            for opp in opportunities:
                st.write(f"• {opp}")
        else:
            st.write("現在、特筆すべき投資機会は検出されていません")


# ヘルパー関数
def get_sentiment_color(sentiment: MarketSentiment) -> str:
    """センチメントに応じた色を返す"""
    colors = {
        MarketSentiment.EXTREME_FEAR: "#8B0000",
        MarketSentiment.FEAR: "#FF4500",
        MarketSentiment.NEUTRAL: "#FFD700",
        MarketSentiment.GREED: "#90EE90",
        MarketSentiment.EXTREME_GREED: "#006400"
    }
    return colors.get(sentiment, "#808080")


def get_risk_state_color(risk_state: RiskState) -> str:
    """リスク状態に応じた色を返す"""
    colors = {
        RiskState.RISK_OFF: "#FF6B6B",
        RiskState.NEUTRAL: "#FFD93D",
        RiskState.RISK_ON: "#6BCF7F"
    }
    return colors.get(risk_state, "#808080")


def get_vix_change(current_vix: float) -> float:
    """VIX変化率を計算（仮実装）"""
    # 実際には前日のVIXと比較する必要がある
    return 0.0


def get_index_display_name(index_name: str) -> str:
    """インデックス名の表示用変換"""
    names = {
        "nikkei225": "日経225",
        "topix": "TOPIX",
        "sp500": "S&P 500",
        "nasdaq": "NASDAQ",
        "dow": "ダウ平均",
        "vix": "VIX指数"
    }
    return names.get(index_name, index_name)


def get_sector_display_name(sector: str) -> str:
    """セクター名の表示用変換"""
    names = {
        "technology": "テクノロジー",
        "financial": "金融",
        "consumer": "消費財",
        "industrial": "資本財",
        "healthcare": "ヘルスケア",
        "energy": "エネルギー"
    }
    return names.get(sector, sector)


def render_rsi_gauge(name: str, rsi: float):
    """RSIゲージの表示"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=rsi,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': name, 'font': {'size': 14}},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 30], 'color': "lightgreen"},
                {'range': [30, 70], 'color': "lightyellow"},
                {'range': [70, 100], 'color': "lightcoral"}
            ]
        }
    ))
    
    fig.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)