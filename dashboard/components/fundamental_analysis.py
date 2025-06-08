"""
ファンダメンタルズ分析タブコンポーネント

企業の財務健全性や成長性を評価し、中長期投資の判断材料を提供
"""

import streamlit as st
import pandas as pd
from typing import List, Optional
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.technical_analysis.fundamental_analysis import FundamentalAnalyzer
from src.technical_analysis.fundamental_visualization import FundamentalVisualizer


def render_fundamental_analysis_tab():
    """ファンダメンタルズ分析タブのレンダリング"""
    st.markdown("### 📊 ファンダメンタルズ分析")
    st.markdown("企業の財務健全性や成長性を分析し、中長期投資の判断材料を提供します。")
    
    # アナライザーとビジュアライザーの初期化
    analyzer = FundamentalAnalyzer()
    visualizer = FundamentalVisualizer()
    
    # サイドバー設定
    with st.sidebar:
        st.markdown("### 🎯 分析対象")
        
        # 分析対象銘柄の選択
        symbol = st.text_input(
            "銘柄コード",
            value="7203.T",
            help="分析したい銘柄コードを入力してください（例: 7203.T, AAPL）",
            key="fundamental_analysis_symbol"
        )
        
        # 同業他社比較用銘柄
        peer_symbols_input = st.text_area(
            "同業他社銘柄（カンマ区切り）",
            value="7201.T,7267.T,7269.T",
            help="比較したい同業他社の銘柄コードをカンマ区切りで入力してください"
        )
        
        # 分析期間設定
        years = st.slider(
            "成長トレンド分析期間（年）",
            min_value=3,
            max_value=10,
            value=5,
            help="過去何年分の財務データを分析するかを選択してください"
        )
        
        # 分析実行ボタン
        analyze_button = st.button("🔍 分析実行", type="primary")
    
    if analyze_button and symbol:
        try:
            # 進捗表示
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 1. 基本財務指標の取得
            status_text.text("基本財務指標を取得中...")
            progress_bar.progress(20)
            
            metrics = analyzer.get_financial_metrics(symbol)
            if not metrics:
                st.error(f"銘柄 {symbol} の財務データを取得できませんでした。銘柄コードを確認してください。")
                return
            
            # 2. 成長トレンド分析
            status_text.text("成長トレンド分析中...")
            progress_bar.progress(40)
            
            growth_trend = analyzer.analyze_growth_trend(symbol, years)
            if not growth_trend:
                st.warning(f"銘柄 {symbol} の成長トレンドデータが不十分です。財務諸表データが取得できない可能性があります。")
            
            # 3. 財務健全性スコア算出
            status_text.text("財務健全性スコア算出中...")
            progress_bar.progress(60)
            
            health_score = analyzer.calculate_health_score(symbol)
            
            # 4. 同業他社比較（オプション）
            comparison = None
            if peer_symbols_input.strip():
                status_text.text("同業他社比較分析中...")
                progress_bar.progress(80)
                
                peer_symbols = [s.strip() for s in peer_symbols_input.split(',') if s.strip()]
                comparison = analyzer.compare_with_peers(symbol, peer_symbols)
            
            # 5. 結果表示
            status_text.text("結果を表示中...")
            progress_bar.progress(100)
            
            # 進捗表示をクリア
            progress_bar.empty()
            status_text.empty()
            
            # 結果の表示
            display_analysis_results(
                symbol, metrics, growth_trend, health_score, comparison, visualizer
            )
            
        except Exception as e:
            st.error(f"分析中にエラーが発生しました: {str(e)}")
    
    elif not symbol:
        st.info("銘柄コードを入力して「分析実行」ボタンをクリックしてください。")
    
    else:
        # デフォルト表示（説明）
        display_feature_overview()


def display_analysis_results(
    symbol: str, 
    metrics, 
    growth_trend, 
    health_score, 
    comparison, 
    visualizer
):
    """分析結果の表示"""
    
    # 企業情報ヘッダー
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown(f"## 📈 {metrics.company_name} ({symbol})")
    
    with col2:
        if metrics.price:
            st.metric("現在株価", f"¥{metrics.price:,.0f}")
    
    with col3:
        if metrics.market_cap:
            market_cap_billion = metrics.market_cap / 1e9
            st.metric("時価総額", f"¥{market_cap_billion:.0f}B")
    
    # タブ分割表示
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 基本指標", "📈 成長トレンド", "🛡️ 健全性スコア", "🔄 同業他社比較"
    ])
    
    # 基本指標タブ
    with tab1:
        display_basic_metrics(metrics, visualizer)
    
    # 成長トレンドタブ
    with tab2:
        if growth_trend:
            display_growth_trend(growth_trend, visualizer)
        else:
            st.warning("成長トレンドデータを取得できませんでした。")
    
    # 健全性スコアタブ
    with tab3:
        if health_score:
            display_health_score(health_score, visualizer)
        else:
            st.warning("健全性スコアを計算できませんでした。")
    
    # 同業他社比較タブ
    with tab4:
        if comparison:
            display_peer_comparison(comparison, visualizer)
        else:
            st.info("同業他社比較を行うには、サイドバーで同業他社銘柄を入力してください。")


def display_basic_metrics(metrics, visualizer):
    """基本指標の表示"""
    st.markdown("### 📊 主要財務指標")
    
    # メトリクス表示
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 📈 収益性指標")
        if metrics.per:
            st.metric("PER（株価収益率）", f"{metrics.per:.1f}倍")
        if metrics.roe:
            st.metric("ROE（自己資本利益率）", f"{metrics.roe*100:.1f}%")
        if metrics.roa:
            st.metric("ROA（総資産利益率）", f"{metrics.roa*100:.1f}%")
    
    with col2:
        st.markdown("#### 💰 割安性指標")
        if metrics.pbr:
            st.metric("PBR（株価純資産倍率）", f"{metrics.pbr:.1f}倍")
        if metrics.dividend_yield:
            st.metric("配当利回り", f"{metrics.dividend_yield*100:.1f}%")
    
    with col3:
        st.markdown("#### 🛡️ 安全性指標")
        if metrics.current_ratio:
            st.metric("流動比率", f"{metrics.current_ratio:.1f}倍")
        if metrics.equity_ratio:
            st.metric("自己資本比率", f"{metrics.equity_ratio*100:.1f}%")
        if metrics.debt_ratio:
            st.metric("負債比率", f"{metrics.debt_ratio*100:.1f}%")
    
    # 指標サマリーチャート
    st.markdown("### 📊 指標サマリー")
    summary_chart = visualizer._create_metrics_summary_chart(metrics)
    st.plotly_chart(summary_chart, use_container_width=True)
    
    # 指標の解説
    with st.expander("📚 指標の説明"):
        st.markdown("""
        **PER（株価収益率）**: 株価 ÷ 1株当たり純利益。一般的に15-20倍が適正とされる。
        
        **PBR（株価純資産倍率）**: 株価 ÷ 1株当たり純資産。1倍を下回ると割安とされる。
        
        **ROE（自己資本利益率）**: 純利益 ÷ 自己資本。15%以上が優秀とされる。
        
        **配当利回り**: 1株当たり配当金 ÷ 株価。2-5%が一般的。
        
        **流動比率**: 流動資産 ÷ 流動負債。200%以上が理想的。
        
        **自己資本比率**: 自己資本 ÷ 総資産。50%以上が安全とされる。
        """)


def display_growth_trend(growth_trend, visualizer):
    """成長トレンドの表示"""
    st.markdown("### 📈 成長トレンド分析")
    
    # CAGR表示
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if growth_trend.revenue_cagr:
            cagr_color = "green" if growth_trend.revenue_cagr > 0 else "red"
            st.markdown(f"**売上CAGR**: <span style='color:{cagr_color}'>{growth_trend.revenue_cagr:.1%}</span>", 
                       unsafe_allow_html=True)
    
    with col2:
        if growth_trend.profit_cagr:
            cagr_color = "green" if growth_trend.profit_cagr > 0 else "red"
            st.markdown(f"**利益CAGR**: <span style='color:{cagr_color}'>{growth_trend.profit_cagr:.1%}</span>", 
                       unsafe_allow_html=True)
    
    with col3:
        if growth_trend.volatility:
            volatility_level = "低" if growth_trend.volatility < 0.2 else "中" if growth_trend.volatility < 0.5 else "高"
            st.markdown(f"**利益変動性**: {volatility_level} ({growth_trend.volatility:.1%})")
    
    # 成長トレンドチャート
    growth_chart = visualizer.plot_growth_trend(growth_trend)
    st.plotly_chart(growth_chart, use_container_width=True)
    
    # 成長性評価
    st.markdown("### 📈 成長性評価")
    
    revenue_growth_rating = evaluate_growth(growth_trend.revenue_cagr)
    profit_growth_rating = evaluate_growth(growth_trend.profit_cagr)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**売上成長性**: {revenue_growth_rating}")
    
    with col2:
        st.markdown(f"**利益成長性**: {profit_growth_rating}")


def display_health_score(health_score, visualizer):
    """健全性スコアの表示"""
    st.markdown("### 🛡️ 財務健全性スコア")
    
    # 総合スコア表示
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        score_color = get_score_color(health_score.total_score)
        st.markdown(f"""
        <div style='text-align: center; padding: 20px; border-radius: 10px; background-color: {score_color}20; border: 2px solid {score_color}'>
            <h2 style='color: {score_color}; margin: 0'>{health_score.total_score:.1f}点</h2>
            <h3 style='color: {score_color}; margin: 5px 0'>{health_score.health_level.value}</h3>
        </div>
        """, unsafe_allow_html=True)
    
    # レーダーチャート
    radar_chart = visualizer.plot_health_score_radar(health_score)
    st.plotly_chart(radar_chart, use_container_width=True)
    
    # スコア詳細
    st.markdown("### 📋 スコア詳細")
    
    score_df = pd.DataFrame([
        {"項目": "PER適正性", "スコア": health_score.score_breakdown.get('per', 0)},
        {"項目": "PBR適正性", "スコア": health_score.score_breakdown.get('pbr', 0)},
        {"項目": "ROE収益性", "スコア": health_score.score_breakdown.get('roe', 0)},
        {"項目": "流動性", "スコア": health_score.score_breakdown.get('liquidity', 0)},
        {"項目": "安定性", "スコア": health_score.score_breakdown.get('stability', 0)},
        {"項目": "配当性", "スコア": health_score.score_breakdown.get('dividend', 0)}
    ])
    
    st.dataframe(score_df, use_container_width=True)
    
    # 推奨事項
    if health_score.recommendations:
        st.markdown("### ⚠️ 注意事項・推奨事項")
        for i, recommendation in enumerate(health_score.recommendations, 1):
            st.warning(f"{i}. {recommendation}")


def display_peer_comparison(comparison, visualizer):
    """同業他社比較の表示"""
    st.markdown("### 🔄 同業他社比較分析")
    
    # 比較テーブル
    comparison_table = visualizer.plot_peer_comparison_table(comparison)
    st.plotly_chart(comparison_table, use_container_width=True)
    
    # ランキング表示
    st.markdown("### 🏆 ランキング")
    
    ranking_data = []
    for metric, rank in comparison.rank.items():
        ranking_data.append({
            "指標": metric.upper(),
            "順位": f"{rank}位 / {len(comparison.comparison_symbols) + 1}社",
            "業界平均": f"{comparison.industry_average.get(metric, 0):.2f}"
        })
    
    ranking_df = pd.DataFrame(ranking_data)
    st.dataframe(ranking_df, use_container_width=True)


def display_feature_overview():
    """機能概要の表示"""
    st.markdown("## 🎯 ファンダメンタルズ分析について")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 📊 提供機能
        
        **基本財務指標**
        - PER（株価収益率）
        - PBR（株価純資産倍率） 
        - ROE（自己資本利益率）
        - 配当利回り
        - 流動比率
        - 自己資本比率
        
        **成長性分析**
        - 売上・利益の成長率トレンド
        - 年平均成長率（CAGR）
        - 利益変動性の評価
        """)
    
    with col2:
        st.markdown("""
        ### 🛡️ 分析内容
        
        **財務健全性スコア**
        - 総合評価（100点満点）
        - 項目別詳細スコア
        - 改善提案
        
        **同業他社比較**
        - 業界内でのポジション
        - 各指標でのランキング
        - 業界平均との比較
        
        **投資判断サポート**
        - 割安/割高の評価
        - 成長性の評価
        - リスクレベルの評価
        """)
    
    st.info("左サイドバーで銘柄コードを入力し、「分析実行」ボタンをクリックして分析を開始してください。")


def evaluate_growth(cagr: Optional[float]) -> str:
    """成長率の評価"""
    if cagr is None:
        return "データ不足"
    elif cagr >= 0.15:
        return "🚀 非常に高い"
    elif cagr >= 0.10:
        return "📈 高い"
    elif cagr >= 0.05:
        return "📊 普通"
    elif cagr >= 0:
        return "📉 低い"
    else:
        return "📉 マイナス成長"


def get_score_color(score: float) -> str:
    """スコアに応じた色を取得"""
    if score >= 90:
        return "#4CAF50"  # 緑
    elif score >= 75:
        return "#8BC34A"  # 薄緑
    elif score >= 60:
        return "#FFC107"  # 黄
    elif score >= 40:
        return "#FF9800"  # オレンジ
    else:
        return "#F44336"  # 赤