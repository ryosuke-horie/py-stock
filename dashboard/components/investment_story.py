"""
投資ストーリー・シナリオ分析タブコンポーネント

分析結果を初心者にも理解しやすい自然言語のストーリー形式で提供し、
投資シナリオの自動生成、リスク要因の整理、用語解説付きレポートを表示
"""

import streamlit as st
import pandas as pd
from typing import List, Optional
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.technical_analysis.integrated_analysis import IntegratedAnalyzer
from src.technical_analysis.investment_story_generator import (
    ScenarioType, RiskLevel, InvestmentScenario, RiskFactor, GlossaryTerm
)


def render_investment_story_tab():
    """投資ストーリー・シナリオ分析タブのレンダリング"""
    st.markdown("### 📖 投資ストーリー・シナリオ分析")
    st.markdown("分析結果を分かりやすいストーリー形式で提供し、投資判断をサポートします。")
    
    # アナライザーの初期化
    analyzer = IntegratedAnalyzer()
    
    # サイドバー設定
    with st.sidebar:
        st.markdown("### 📖 投資ストーリー分析設定")
        
        # 分析対象銘柄の選択
        analysis_type = st.radio(
            "📈 分析タイプ",
            ["単一銘柄分析", "複数銘柄比較"],
            help="投資ストーリー作成のタイプを選択してください"
        )
        
        if analysis_type == "単一銘柄分析":
            symbol = st.text_input(
                "📖 分析対象銘柄",
                value="",
                help="投資ストーリーを作成したい銘柄コードを入力してください（例: 7203.T, AAPL）",
                key="investment_story_symbol"
            )
            
            # 同業他社比較オプション
            include_peers = st.checkbox(
                "同業他社比較を含める",
                value=False,
                help="同業他社との比較分析を含めるかどうか"
            )
            
            peer_symbols = []
            if include_peers:
                peer_symbols_input = st.text_area(
                    "同業他社銘柄（カンマ区切り）",
                    value="",
                    help="比較したい同業他社の銘柄コードをカンマ区切りで入力"
                )
                peer_symbols = [s.strip() for s in peer_symbols_input.split(',') if s.strip()]
            
            # 分析実行ボタン
            analyze_button = st.button("🔍 ストーリー分析実行", type="primary")
            
        else:  # 複数銘柄比較
            symbols_input = st.text_area(
                "比較銘柄（カンマ区切り）",
                value="",
                help="比較したい銘柄コードをカンマ区切りで入力してください"
            )
            
            symbols = [s.strip() for s in symbols_input.split(',') if s.strip()]
            
            # 比較分析実行ボタン
            analyze_button = st.button("🔍 比較分析実行", type="primary")
    
    # 分析実行
    if analyze_button:
        if analysis_type == "単一銘柄分析" and symbol:
            execute_single_analysis(analyzer, symbol, include_peers, peer_symbols)
        elif analysis_type == "複数銘柄比較" and len(symbols) >= 2:
            execute_comparison_analysis(analyzer, symbols)
        else:
            st.error("適切な銘柄コードを入力してください。")
    else:
        # デフォルト表示（機能説明）
        display_feature_overview()


def execute_single_analysis(
    analyzer: IntegratedAnalyzer,
    symbol: str,
    include_peers: bool,
    peer_symbols: List[str]
):
    """単一銘柄の統合分析実行"""
    try:
        # 進捗表示
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("統合分析を実行中...")
        progress_bar.progress(20)
        
        # 統合分析実行
        analysis_result = analyzer.generate_complete_analysis(
            symbol, include_peers, peer_symbols if include_peers else None
        )
        
        progress_bar.progress(100)
        status_text.empty()
        progress_bar.empty()
        
        # 結果表示
        if analysis_result.get('status') != 'error':
            display_single_analysis_results(analysis_result)
        else:
            st.error(f"分析中にエラーが発生しました: {analysis_result.get('error_message', '不明なエラー')}")
            
    except Exception as e:
        st.error(f"分析中にエラーが発生しました: {str(e)}")


def execute_comparison_analysis(analyzer: IntegratedAnalyzer, symbols: List[str]):
    """複数銘柄の比較分析実行"""
    try:
        # 進捗表示
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("複数銘柄の比較分析を実行中...")
        progress_bar.progress(20)
        
        # 比較分析実行
        comparison_result = analyzer.generate_comparison_report(symbols)
        
        progress_bar.progress(100)
        status_text.empty()
        progress_bar.empty()
        
        # 結果表示
        if comparison_result.get('status') != 'error':
            display_comparison_results(comparison_result)
        else:
            st.error(f"比較分析中にエラーが発生しました: {comparison_result.get('error_message', '不明なエラー')}")
            
    except Exception as e:
        st.error(f"比較分析中にエラーが発生しました: {str(e)}")


def display_single_analysis_results(analysis_result):
    """単一銘柄分析結果の表示"""
    symbol = analysis_result['symbol']
    investment_report = analysis_result.get('investment_report')
    summary = analysis_result.get('summary', {})
    
    # ヘッダー表示
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        company_name = "不明"
        if investment_report:
            company_name = investment_report.company_name
        st.markdown(f"## 📊 {company_name} ({symbol})")
    
    with col2:
        if investment_report:
            st.metric("現在株価", f"¥{investment_report.current_price:,.0f}")
    
    with col3:
        overall_score = summary.get('overall_score', 0)
        st.metric("総合スコア", f"{overall_score:.0f}点")
    
    # 投資判断サマリー
    st.markdown("### 🎯 投資判断サマリー")
    
    col1, col2 = st.columns(2)
    
    with col1:
        recommendation = summary.get('recommendation', '不明')
        score_color = get_recommendation_color(recommendation)
        st.markdown(f"""
        <div style='text-align: center; padding: 20px; border-radius: 10px; background-color: {score_color}20; border: 2px solid {score_color}'>
            <h3 style='color: {score_color}; margin: 0'>推奨判断</h3>
            <h2 style='color: {score_color}; margin: 5px 0'>{recommendation}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if investment_report:
            st.markdown(f"**全体評価**: {investment_report.overall_assessment}")
            st.markdown(f"**リスクレベル**: {investment_report.overall_risk_level.value}")
    
    # タブ分割表示
    if investment_report:
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📖 投資ストーリー", "📈 投資シナリオ", "⚠️ リスク分析", "📚 用語解説", "📊 詳細分析"
        ])
        
        with tab1:
            display_investment_story(investment_report)
        
        with tab2:
            display_investment_scenarios(investment_report.scenarios)
        
        with tab3:
            display_risk_analysis(investment_report.risk_factors)
        
        with tab4:
            display_glossary(investment_report.glossary)
        
        with tab5:
            display_detailed_analysis(analysis_result)


def display_investment_story(investment_report):
    """投資ストーリーの表示"""
    st.markdown("### 📖 投資ストーリー")
    
    # エグゼクティブサマリー
    st.markdown("#### 📋 エグゼクティブサマリー")
    st.markdown(investment_report.executive_summary)
    
    # 詳細分析
    st.markdown("#### 🔍 詳細分析")
    st.markdown(investment_report.detailed_analysis)


def display_investment_scenarios(scenarios: List[InvestmentScenario]):
    """投資シナリオの表示"""
    st.markdown("### 📈 投資シナリオ")
    
    for i, scenario in enumerate(scenarios):
        # シナリオタイプに応じた色設定
        if scenario.scenario_type == ScenarioType.OPTIMISTIC:
            color = "#28a745"  # 緑
            icon = "🚀"
        elif scenario.scenario_type == ScenarioType.PESSIMISTIC:
            color = "#dc3545"  # 赤
            icon = "📉"
        else:
            color = "#ffc107"  # 黄
            icon = "📊"
        
        # シナリオ表示
        st.markdown(f"""
        <div style='padding: 15px; margin: 10px 0; border-radius: 10px; border-left: 5px solid {color}; background-color: {color}10'>
            <h4 style='color: {color}; margin: 0'>{icon} {scenario.title}</h4>
            <p style='margin: 10px 0'><strong>発生確率:</strong> {scenario.probability:.0%}</p>
            <p style='margin: 10px 0'><strong>目標株価:</strong> ¥{scenario.price_target:,.0f}</p>
            <p style='margin: 10px 0'><strong>リスクレベル:</strong> {scenario.risk_level.value}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # ストーリー表示
        with st.expander(f"{scenario.scenario_type.value}シナリオの詳細"):
            st.markdown(scenario.story)
            
            st.markdown("**主要ポイント:**")
            for point in scenario.key_points:
                st.markdown(f"• {point}")


def display_risk_analysis(risk_factors: List[RiskFactor]):
    """リスク分析の表示"""
    st.markdown("### ⚠️ リスク分析")
    
    if not risk_factors:
        st.info("特定のリスク要因はありません。")
        return
    
    # リスク要因をテーブルで表示
    risk_data = []
    for risk in risk_factors:
        risk_data.append({
            "カテゴリ": risk.category,
            "説明": risk.description,
            "影響度": risk.impact,
            "発生可能性": risk.likelihood,
            "対策": risk.mitigation
        })
    
    risk_df = pd.DataFrame(risk_data)
    st.dataframe(risk_df, use_container_width=True)
    
    # リスクマトリックス表示
    st.markdown("#### 📊 リスクマトリックス")
    
    fig_data = []
    for risk in risk_factors:
        impact_score = {"高": 3, "中": 2, "低": 1}.get(risk.impact, 2)
        likelihood_score = {"高": 3, "中": 2, "低": 1}.get(risk.likelihood, 2)
        
        fig_data.append({
            "リスク要因": risk.category,
            "影響度": impact_score,
            "発生可能性": likelihood_score,
            "リスクレベル": impact_score * likelihood_score
        })
    
    if fig_data:
        import plotly.express as px
        df = pd.DataFrame(fig_data)
        
        fig = px.scatter(df, x="発生可能性", y="影響度", 
                        size="リスクレベル", color="リスクレベル",
                        hover_name="リスク要因",
                        title="リスクマトリックス",
                        labels={"発生可能性": "発生可能性", "影響度": "影響度"})
        
        fig.update_layout(
            xaxis=dict(range=[0.5, 3.5], tickvals=[1, 2, 3], ticktext=["低", "中", "高"]),
            yaxis=dict(range=[0.5, 3.5], tickvals=[1, 2, 3], ticktext=["低", "中", "高"])
        )
        
        st.plotly_chart(fig, use_container_width=True)


def display_glossary(glossary_terms: List[GlossaryTerm]):
    """用語解説の表示"""
    st.markdown("### 📚 用語解説")
    
    if not glossary_terms:
        st.info("このレポートに関連する専門用語の解説はありません。")
        return
    
    for term in glossary_terms:
        with st.expander(f"📖 {term.term}"):
            st.markdown(f"**定義**: {term.definition}")
            if term.example:
                st.markdown(f"**例**: {term.example}")


def display_detailed_analysis(analysis_result):
    """詳細分析の表示"""
    st.markdown("### 📊 詳細分析データ")
    
    fundamental = analysis_result.get('fundamental_analysis', {})
    technical = analysis_result.get('technical_analysis')
    summary = analysis_result.get('summary', {})
    
    # サマリー情報
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 💪 強み")
        for strength in summary.get('key_strengths', []):
            st.markdown(f"✅ {strength}")
    
    with col2:
        st.markdown("#### ⚠️ 懸念事項")
        for concern in summary.get('key_concerns', []):
            st.markdown(f"🔸 {concern}")
    
    # 次のアクション
    st.markdown("#### 📋 推奨アクション")
    for action in summary.get('next_actions', []):
        st.markdown(f"• {action}")
    
    # ファンダメンタルズデータ
    if fundamental.get('status') == 'success':
        st.markdown("#### 📈 ファンダメンタルズデータ")
        
        metrics = fundamental.get('metrics')
        if metrics:
            metrics_data = {
                "指標": ["PER", "PBR", "ROE", "配当利回り", "流動比率", "自己資本比率"],
                "値": [
                    f"{metrics.per:.1f}倍" if metrics.per else "N/A",
                    f"{metrics.pbr:.1f}倍" if metrics.pbr else "N/A",
                    f"{metrics.roe:.1%}" if metrics.roe else "N/A",
                    f"{metrics.dividend_yield:.1%}" if metrics.dividend_yield else "N/A",
                    f"{metrics.current_ratio:.1f}倍" if metrics.current_ratio else "N/A",
                    f"{metrics.equity_ratio:.1%}" if metrics.equity_ratio else "N/A",
                ]
            }
            st.dataframe(pd.DataFrame(metrics_data), use_container_width=True)
    
    # テクニカルデータ
    if technical:
        st.markdown("#### 📊 テクニカルデータ")
        
        technical_data = {
            "項目": ["トレンド", "モメンタム", "シグナル", "サポートライン", "レジスタンスライン"],
            "値": [
                technical.trend,
                technical.momentum,
                technical.signal,
                f"¥{technical.support_level:,.0f}" if technical.support_level else "N/A",
                f"¥{technical.resistance_level:,.0f}" if technical.resistance_level else "N/A",
            ]
        }
        st.dataframe(pd.DataFrame(technical_data), use_container_width=True)


def display_comparison_results(comparison_result):
    """比較分析結果の表示"""
    st.markdown("### 🔄 複数銘柄比較分析")
    
    symbols = comparison_result['symbols']
    individual_analyses = comparison_result.get('individual_analyses', {})
    comparison_summary = comparison_result.get('comparison_summary', {})
    
    # ランキング表示
    if comparison_summary.get('ranking'):
        st.markdown("#### 🏆 総合評価ランキング")
        
        ranking_data = []
        for i, rank_info in enumerate(comparison_summary['ranking']):
            ranking_data.append({
                "順位": i + 1,
                "銘柄": rank_info['symbol'],
                "総合スコア": f"{rank_info['score']:.0f}点",
                "推奨判断": rank_info['recommendation']
            })
        
        st.dataframe(pd.DataFrame(ranking_data), use_container_width=True)
    
    # カテゴリ別ベスト
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if comparison_summary.get('best_quality'):
            st.metric("🛡️ 最高品質", comparison_summary['best_quality'])
    
    with col2:
        if comparison_summary.get('best_growth'):
            st.metric("🚀 最高成長", comparison_summary['best_growth'])
    
    with col3:
        if comparison_summary.get('best_value'):
            st.metric("💰 最高バリュー", comparison_summary['best_value'])
    
    # 推奨事項
    if comparison_summary.get('recommendations'):
        st.markdown("#### 💡 推奨事項")
        for rec in comparison_summary['recommendations']:
            st.markdown(f"• {rec}")
    
    # 個別分析結果
    st.markdown("#### 📊 個別分析結果")
    
    for symbol in symbols:
        if symbol in individual_analyses:
            analysis = individual_analyses[symbol]
            summary = analysis.get('summary', {})
            
            with st.expander(f"{symbol} - 詳細分析"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("総合スコア", f"{summary.get('overall_score', 0):.0f}点")
                
                with col2:
                    st.metric("推奨判断", summary.get('recommendation', '不明'))
                
                if summary.get('key_strengths'):
                    st.markdown("**強み:**")
                    for strength in summary['key_strengths']:
                        st.markdown(f"✅ {strength}")
                
                if summary.get('key_concerns'):
                    st.markdown("**懸念事項:**")
                    for concern in summary['key_concerns']:
                        st.markdown(f"🔸 {concern}")


def display_feature_overview():
    """機能概要の表示"""
    st.markdown("## 🎯 投資ストーリー・シナリオ分析について")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 📖 提供機能
        
        **投資ストーリー生成**
        - 分析結果の自然言語での説明
        - 初心者にも分かりやすい表現
        - 投資判断の根拠を明確化
        
        **投資シナリオ分析**
        - 楽観・中立・悲観の3シナリオ
        - 各シナリオの発生確率
        - 目標株価の設定
        
        **リスク分析**
        - リスク要因の体系的整理
        - 影響度と発生可能性の評価
        - リスク軽減策の提案
        """)
    
    with col2:
        st.markdown("""
        ### 🛠️ 分析内容
        
        **統合分析**
        - ファンダメンタルズ分析との連携
        - テクニカル分析との統合
        - 総合的な投資判断
        
        **用語解説**
        - 投資初心者向けの解説
        - 具体例による理解促進
        - 専門用語の分かりやすい説明
        
        **比較分析**
        - 複数銘柄の同時比較
        - ランキング形式での表示
        - カテゴリ別のベスト選出
        """)
    
    st.info("左サイドバーで分析設定を行い、「分析実行」ボタンをクリックして開始してください。")


def get_recommendation_color(recommendation: str) -> str:
    """推奨判断に応じた色を取得"""
    if recommendation in ["買い推奨", "条件付き買い"]:
        return "#28a745"  # 緑
    elif recommendation in ["保有・様子見", "様子見"]:
        return "#ffc107"  # 黄
    elif recommendation in ["売り検討", "売り推奨"]:
        return "#dc3545"  # 赤
    else:
        return "#6c757d"  # グレー