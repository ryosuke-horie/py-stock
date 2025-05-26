"""
ニュース・センチメント分析コンポーネント
MCPサーバからニュース情報を取得して表示します
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import asyncio
from typing import Dict, List, Any

def render_news_sentiment_analysis():
    """ニュース・センチメント分析UIをレンダリング"""
    
    st.subheader("📰 ニュース・センチメント分析")
    
    # 銘柄選択
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        symbol = st.text_input(
            "銘柄コード", 
            value="AAPL",
            placeholder="例: AAPL, 7203.T",
            help="日本株は「7203.T」、米国株は「AAPL」の形式で入力"
        )
    
    with col2:
        days = st.selectbox(
            "分析期間",
            options=[1, 3, 7, 14, 30],
            index=2,
            help="過去何日分のニュースを分析するか"
        )
    
    with col3:
        language = st.selectbox(
            "言語",
            options=["both", "ja", "en"],
            format_func=lambda x: {"both": "日英両方", "ja": "日本語", "en": "英語"}[x],
            help="収集するニュースの言語"
        )
    
    # 分析実行ボタン
    if st.button("🔍 ニュース分析実行", type="primary"):
        if symbol:
            with st.spinner("ニュースを収集・分析中..."):
                analysis_result = fetch_news_analysis(symbol, days, language)
                
                if analysis_result:
                    display_analysis_results(analysis_result)
                else:
                    st.error("ニュース分析に失敗しました。銘柄コードを確認してください。")
        else:
            st.warning("銘柄コードを入力してください")
    
    # デモデータ表示
    st.markdown("---")
    if st.checkbox("デモデータを表示"):
        demo_data = get_demo_analysis_data()
        display_analysis_results(demo_data)

def fetch_news_analysis(symbol: str, days: int, language: str) -> Dict[str, Any]:
    """
    MCPサーバからニュース分析結果を取得
    実際の実装ではMCPクライアントを使用
    """
    # TODO: 実際のMCPクライアント実装
    # 現在はモックデータを返す
    return get_demo_analysis_data(symbol, days, language)

def display_analysis_results(data: Dict[str, Any]):
    """分析結果を表示"""
    
    # 概要メトリクス
    display_summary_metrics(data)
    
    # センチメント分析結果
    display_sentiment_analysis(data)
    
    # 重要度分析
    display_importance_analysis(data)
    
    # ニュース一覧
    display_news_list(data)
    
    # 投資判断への示唆
    display_investment_insights(data)

def display_summary_metrics(data: Dict[str, Any]):
    """概要メトリクスを表示"""
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "ニュース件数",
            data.get("newsCount", 0),
            help="分析対象のニュース記事数"
        )
    
    with col2:
        sentiment_score = data.get("sentimentSummary", {}).get("averageScore", 0)
        sentiment_delta = "ポジティブ" if sentiment_score > 0.1 else "ネガティブ" if sentiment_score < -0.1 else "ニュートラル"
        st.metric(
            "平均センチメント",
            f"{sentiment_score:.3f}",
            delta=sentiment_delta,
            help="ニュース全体の感情スコア平均"
        )
    
    with col3:
        avg_importance = data.get("importanceStatistics", {}).get("averageImportance", 0)
        st.metric(
            "平均重要度",
            f"{avg_importance:.1f}",
            help="ニュースの重要度平均（100点満点）"
        )
    
    with col4:
        critical_count = data.get("importanceStatistics", {}).get("criticalNewsCount", 0)
        st.metric(
            "緊急ニュース",
            critical_count,
            delta="要注意" if critical_count > 0 else None,
            help="重要度90点以上のニュース件数"
        )

def display_sentiment_analysis(data: Dict[str, Any]):
    """センチメント分析結果を表示"""
    
    st.subheader("📊 センチメント分析")
    
    sentiment_data = data.get("sentimentSummary", {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        # センチメント分布（ドーナツチャート）
        labels = ['ポジティブ', 'ネガティブ', 'ニュートラル']
        values = [
            sentiment_data.get("positiveCount", 0),
            sentiment_data.get("negativeCount", 0),
            sentiment_data.get("neutralCount", 0)
        ]
        colors = ['#2E8B57', '#DC143C', '#808080']
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            marker_colors=colors
        )])
        fig_pie.update_layout(
            title="センチメント分布",
            showlegend=True,
            height=300
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # センチメントスコア範囲表示
        score = sentiment_data.get("averageScore", 0)
        
        # ゲージチャート風の表示
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "総合センチメントスコア"},
            delta={'reference': 0},
            gauge={
                'axis': {'range': [-1, 1]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [-1, -0.5], 'color': "red"},
                    {'range': [-0.5, 0], 'color': "orange"},
                    {'range': [0, 0.5], 'color': "lightgreen"},
                    {'range': [0.5, 1], 'color': "green"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 0.9
                }
            }
        ))
        fig_gauge.update_layout(height=300)
        st.plotly_chart(fig_gauge, use_container_width=True)

def display_importance_analysis(data: Dict[str, Any]):
    """重要度分析を表示"""
    
    st.subheader("⚡ 重要度分析")
    
    importance_data = data.get("importanceStatistics", {})
    
    # 重要度分布
    col1, col2 = st.columns(2)
    
    with col1:
        high_count = importance_data.get("highImportanceCount", 0)
        critical_count = importance_data.get("criticalNewsCount", 0)
        total_news = data.get("newsCount", 1)
        
        # 重要度レベル別の分布
        importance_levels = {
            "緊急 (90+)": critical_count,
            "高 (80-89)": high_count - critical_count,
            "中程度 (50-79)": total_news - high_count,
            "低 (<50)": 0  # 簡略化
        }
        
        df_importance = pd.DataFrame([
            {"レベル": k, "件数": v} for k, v in importance_levels.items() if v > 0
        ])
        
        if not df_importance.empty:
            fig_bar = px.bar(
                df_importance,
                x="レベル",
                y="件数",
                title="重要度レベル別ニュース分布",
                color="件数",
                color_continuous_scale="Reds"
            )
            fig_bar.update_layout(height=300)
            st.plotly_chart(fig_bar, use_container_width=True)
    
    with col2:
        # 重要度の説明
        st.markdown("""
        **重要度レベルの説明:**
        
        - 🔴 **緊急 (90+)**: 即座に投資判断に影響
        - 🟠 **高 (80-89)**: 投資戦略の見直しが必要
        - 🟡 **中程度 (50-79)**: 注意深く監視
        - 🟢 **低 (<50)**: 軽微な影響
        """)
        
        avg_importance = importance_data.get("averageImportance", 0)
        if avg_importance >= 80:
            st.error("⚠️ 高重要度のニュースが多数検出されています")
        elif avg_importance >= 60:
            st.warning("📊 中程度の重要度のニュースが中心です")
        else:
            st.info("📰 一般的なニュースが中心です")

def display_news_list(data: Dict[str, Any]):
    """ニュース一覧を表示"""
    
    st.subheader("📋 重要ニュース一覧")
    
    top_news = data.get("topNews", [])
    
    if not top_news:
        st.info("該当するニュースが見つかりませんでした")
        return
    
    for i, news in enumerate(top_news[:10]):  # 上位10件を表示
        with st.expander(f"#{i+1} {news.get('title', 'タイトルなし')}", expanded=i < 3):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**内容:** {news.get('content', '')}")
                st.markdown(f"**ソース:** {news.get('source', '')} | **言語:** {news.get('language', '').upper()}")
                st.markdown(f"**カテゴリ:** {news.get('category', '')}")
                
                if news.get('url'):
                    st.markdown(f"[📖 記事を読む]({news['url']})")
            
            with col2:
                # センチメント表示
                sentiment = news.get('sentiment', {})
                score = sentiment.get('score', 0)
                interpretation = sentiment.get('interpretation', 'ニュートラル')
                
                if score > 0.1:
                    st.success(f"😊 {interpretation}")
                elif score < -0.1:
                    st.error(f"😞 {interpretation}")
                else:
                    st.info(f"😐 {interpretation}")
                
                st.metric("スコア", f"{score:.3f}")
                
                # 重要度表示
                importance = news.get('importance', {})
                importance_score = importance.get('overallScore', 0)
                importance_level = importance.get('level', '低')
                
                if importance_score >= 90:
                    st.error(f"🔴 {importance_level}")
                elif importance_score >= 80:
                    st.warning(f"🟠 {importance_level}")
                elif importance_score >= 60:
                    st.info(f"🟡 {importance_level}")
                else:
                    st.success(f"🟢 {importance_level}")
                
                st.metric("重要度", f"{importance_score:.1f}/100")

def display_investment_insights(data: Dict[str, Any]):
    """投資判断への示唆を表示"""
    
    st.subheader("💡 投資判断への示唆")
    
    insights = data.get("investmentInsights", [])
    
    if insights:
        for insight in insights:
            st.info(f"💡 {insight}")
    else:
        st.info("💡 特に大きな材料は見当たらず、テクニカル分析重視の局面です")
    
    # 総合判断
    sentiment_summary = data.get("sentimentSummary", {})
    avg_sentiment = sentiment_summary.get("averageScore", 0)
    overall_sentiment = sentiment_summary.get("overallSentiment", "neutral")
    
    st.markdown("---")
    st.markdown("**総合判断:**")
    
    if overall_sentiment == "positive" and avg_sentiment > 0.3:
        st.success("🟢 **買い優勢**: ポジティブなニュースが多く、買い要因が強い")
    elif overall_sentiment == "negative" and avg_sentiment < -0.3:
        st.error("🔴 **売り優勢**: ネガティブなニュースが多く、売り要因が強い")
    else:
        st.info("🟡 **中立**: ニュース要因は限定的、テクニカル分析を重視")

def get_demo_analysis_data(symbol: str = "AAPL", days: int = 7, language: str = "both") -> Dict[str, Any]:
    """デモ用の分析データを生成"""
    
    return {
        "symbol": symbol,
        "analysisDate": datetime.now().isoformat(),
        "newsCount": 15,
        "sentimentSummary": {
            "averageScore": 0.15,
            "overallSentiment": "positive",
            "positiveCount": 8,
            "negativeCount": 3,
            "neutralCount": 4
        },
        "importanceStatistics": {
            "averageImportance": 67.5,
            "highImportanceCount": 5,
            "criticalNewsCount": 1
        },
        "topNews": [
            {
                "id": "demo1",
                "title": f"{symbol}：第3四半期決算が市場予想を上回る好結果",
                "content": f"{symbol}の最新四半期決算が発表され、売上・利益ともに市場予想を大幅に上回る結果となりました。特に主力事業の好調が目立ち...",
                "url": "https://example.com/news1",
                "publishedAt": (datetime.now() - timedelta(hours=2)).isoformat(),
                "source": "経済新聞",
                "language": "ja",
                "category": "earnings",
                "sentiment": {
                    "score": 0.75,
                    "magnitude": 0.85,
                    "interpretation": "非常にポジティブ"
                },
                "importance": {
                    "overallScore": 92.0,
                    "level": "緊急"
                }
            },
            {
                "id": "demo2", 
                "title": f"{symbol} announces strategic partnership with major tech company",
                "content": f"{symbol} has announced a new strategic partnership that is expected to drive significant growth in the coming quarters...",
                "url": "https://example.com/news2",
                "publishedAt": (datetime.now() - timedelta(hours=6)).isoformat(),
                "source": "Bloomberg",
                "language": "en",
                "category": "partnership",
                "sentiment": {
                    "score": 0.45,
                    "magnitude": 0.65,
                    "interpretation": "ポジティブ"
                },
                "importance": {
                    "overallScore": 78.0,
                    "level": "高"
                }
            },
            {
                "id": "demo3",
                "title": f"{symbol}：新製品発表で投資家の注目集める",
                "content": f"{symbol}が新製品ラインナップを発表し、革新的な技術が投資家の注目を集めています...",
                "url": "https://example.com/news3", 
                "publishedAt": (datetime.now() - timedelta(days=1)).isoformat(),
                "source": "投資ニュース",
                "language": "ja",
                "category": "general",
                "sentiment": {
                    "score": 0.25,
                    "magnitude": 0.55,
                    "interpretation": "軽くポジティブ"
                },
                "importance": {
                    "overallScore": 65.0,
                    "level": "中"
                }
            }
        ],
        "investmentInsights": [
            "市場センチメントは強いポジティブを示しており、買い要因が多い",
            "決算関連のニュースが多く、業績動向に注目",
            "緊急度の高いニュースが1件あり、注意が必要"
        ]
    }

if __name__ == "__main__":
    render_news_sentiment_analysis()