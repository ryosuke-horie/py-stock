"""
ファンダメンタルズ分析の可視化モジュール

成長性トレンドの可視化機能、財務指標の比較チャート、
健全性スコアのレーダーチャートなどを提供
"""

from typing import Dict, List, Optional
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from loguru import logger

from .fundamental_analysis import (
    FinancialMetrics, 
    GrowthTrend, 
    ComparisonResult, 
    HealthScoreResult,
    HealthScore
)


class FundamentalVisualizer:
    """ファンダメンタルズ分析可視化クラス"""
    
    def __init__(self):
        """初期化"""
        self.color_palette = {
            'primary': '#1f77b4',
            'secondary': '#ff7f0e',
            'success': '#2ca02c',
            'warning': '#d62728',
            'info': '#9467bd',
            'light': '#8c564b',
            'dark': '#e377c2'
        }
    
    def plot_growth_trend(self, growth_trend: GrowthTrend) -> go.Figure:
        """成長トレンドのグラフを作成"""
        try:
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('売上推移', '利益推移'),
                vertical_spacing=0.15
            )
            
            # 売上トレンド
            fig.add_trace(
                go.Scatter(
                    x=growth_trend.years,
                    y=growth_trend.revenue_trend,
                    mode='lines+markers',
                    name='売上',
                    line=dict(color=self.color_palette['primary'], width=3),
                    marker=dict(size=8)
                ),
                row=1, col=1
            )
            
            # 利益トレンド
            fig.add_trace(
                go.Scatter(
                    x=growth_trend.years,
                    y=growth_trend.profit_trend,
                    mode='lines+markers',
                    name='純利益',
                    line=dict(color=self.color_palette['success'], width=3),
                    marker=dict(size=8)
                ),
                row=2, col=1
            )
            
            # レイアウト設定
            fig.update_layout(
                title=f'{growth_trend.symbol} 成長トレンド分析',
                height=500,
                showlegend=True,
                template='plotly_white'
            )
            
            # Y軸のフォーマット
            fig.update_yaxes(title_text="売上 (百万円)", tickformat=',.0f', row=1, col=1)
            fig.update_yaxes(title_text="純利益 (百万円)", tickformat=',.0f', row=2, col=1)
            fig.update_xaxes(title_text="年度", row=2, col=1)
            
            # CAGR情報を注釈として追加
            if growth_trend.revenue_cagr is not None:
                fig.add_annotation(
                    text=f"売上CAGR: {growth_trend.revenue_cagr:.1%}",
                    xref="paper", yref="paper",
                    x=0.02, y=0.98,
                    showarrow=False,
                    bgcolor="rgba(255, 255, 255, 0.8)",
                    bordercolor="black",
                    borderwidth=1
                )
            
            if growth_trend.profit_cagr is not None:
                fig.add_annotation(
                    text=f"利益CAGR: {growth_trend.profit_cagr:.1%}",
                    xref="paper", yref="paper",
                    x=0.02, y=0.48,
                    showarrow=False,
                    bgcolor="rgba(255, 255, 255, 0.8)",
                    bordercolor="black",
                    borderwidth=1
                )
            
            logger.info(f"成長トレンドグラフ作成完了: {growth_trend.symbol}")
            return fig
            
        except Exception as e:
            logger.error(f"成長トレンドグラフ作成エラー: {str(e)}")
            return go.Figure()
    
    def plot_financial_metrics_comparison(
        self, 
        metrics_list: List[FinancialMetrics],
        title: str = "財務指標比較"
    ) -> go.Figure:
        """複数企業の財務指標を比較するグラフ"""
        try:
            symbols = [m.symbol for m in metrics_list]
            
            fig = make_subplots(
                rows=2, cols=3,
                subplot_titles=['PER', 'PBR', 'ROE (%)', '配当利回り (%)', '流動比率', '自己資本比率 (%)'],
                vertical_spacing=0.15,
                horizontal_spacing=0.1
            )
            
            # PER
            per_values = [m.per for m in metrics_list if m.per is not None]
            per_symbols = [m.symbol for m in metrics_list if m.per is not None]
            if per_values:
                fig.add_trace(
                    go.Bar(x=per_symbols, y=per_values, name='PER', 
                          marker_color=self.color_palette['primary']),
                    row=1, col=1
                )
            
            # PBR
            pbr_values = [m.pbr for m in metrics_list if m.pbr is not None]
            pbr_symbols = [m.symbol for m in metrics_list if m.pbr is not None]
            if pbr_values:
                fig.add_trace(
                    go.Bar(x=pbr_symbols, y=pbr_values, name='PBR',
                          marker_color=self.color_palette['secondary']),
                    row=1, col=2
                )
            
            # ROE
            roe_values = [m.roe * 100 for m in metrics_list if m.roe is not None]
            roe_symbols = [m.symbol for m in metrics_list if m.roe is not None]
            if roe_values:
                fig.add_trace(
                    go.Bar(x=roe_symbols, y=roe_values, name='ROE',
                          marker_color=self.color_palette['success']),
                    row=1, col=3
                )
            
            # 配当利回り
            dividend_values = [m.dividend_yield * 100 for m in metrics_list if m.dividend_yield is not None]
            dividend_symbols = [m.symbol for m in metrics_list if m.dividend_yield is not None]
            if dividend_values:
                fig.add_trace(
                    go.Bar(x=dividend_symbols, y=dividend_values, name='配当利回り',
                          marker_color=self.color_palette['warning']),
                    row=2, col=1
                )
            
            # 流動比率
            current_values = [m.current_ratio for m in metrics_list if m.current_ratio is not None]
            current_symbols = [m.symbol for m in metrics_list if m.current_ratio is not None]
            if current_values:
                fig.add_trace(
                    go.Bar(x=current_symbols, y=current_values, name='流動比率',
                          marker_color=self.color_palette['info']),
                    row=2, col=2
                )
            
            # 自己資本比率
            equity_values = [m.equity_ratio * 100 for m in metrics_list if m.equity_ratio is not None]
            equity_symbols = [m.symbol for m in metrics_list if m.equity_ratio is not None]
            if equity_values:
                fig.add_trace(
                    go.Bar(x=equity_symbols, y=equity_values, name='自己資本比率',
                          marker_color=self.color_palette['light']),
                    row=2, col=3
                )
            
            fig.update_layout(
                title=title,
                height=600,
                showlegend=False,
                template='plotly_white'
            )
            
            logger.info(f"財務指標比較グラフ作成完了: {len(metrics_list)}社")
            return fig
            
        except Exception as e:
            logger.error(f"財務指標比較グラフ作成エラー: {str(e)}")
            return go.Figure()
    
    def plot_health_score_radar(self, health_score: HealthScoreResult) -> go.Figure:
        """財務健全性スコアのレーダーチャート"""
        try:
            # スコア項目の日本語ラベル
            labels_map = {
                'per': 'PER適正性',
                'pbr': 'PBR適正性', 
                'roe': 'ROE収益性',
                'liquidity': '流動性',
                'stability': '安定性',
                'dividend': '配当性'
            }
            
            # データの準備
            categories = []
            values = []
            
            for metric, score in health_score.score_breakdown.items():
                if metric in labels_map:
                    categories.append(labels_map[metric])
                    values.append(score)
            
            if not categories:
                logger.warning("レーダーチャート用のデータが不足しています")
                return go.Figure()
            
            # レーダーチャートの作成
            fig = go.Figure()
            
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                name=health_score.symbol,
                line_color=self.color_palette['primary'],
                fillcolor=f"{self.color_palette['primary']}30"  # 透明度30%
            ))
            
            # 健全性レベルに応じた色の設定
            if health_score.health_level == HealthScore.EXCELLENT:
                color = self.color_palette['success']
            elif health_score.health_level == HealthScore.GOOD:
                color = self.color_palette['primary']
            elif health_score.health_level == HealthScore.AVERAGE:
                color = self.color_palette['secondary']
            elif health_score.health_level == HealthScore.POOR:
                color = self.color_palette['warning']
            else:  # CRITICAL
                color = self.color_palette['warning']
            
            fig.update_traces(line_color=color, fillcolor=f"{color}30")
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100],
                        tickvals=[20, 40, 60, 80, 100],
                        ticktext=['20', '40', '60', '80', '100']
                    )),
                title=f'{health_score.symbol} 財務健全性スコア: {health_score.total_score:.1f}点 ({health_score.health_level.value})',
                template='plotly_white',
                height=500
            )
            
            logger.info(f"健全性スコアレーダーチャート作成完了: {health_score.symbol}")
            return fig
            
        except Exception as e:
            logger.error(f"健全性スコアレーダーチャート作成エラー: {str(e)}")
            return go.Figure()
    
    def plot_peer_comparison_table(self, comparison: ComparisonResult) -> go.Figure:
        """同業他社比較テーブル"""
        try:
            # データの準備
            symbols = [comparison.target_symbol] + comparison.comparison_symbols
            metrics_names = list(comparison.metrics_comparison.keys())
            
            # テーブル用データの作成
            table_data = []
            for symbol in symbols:
                row = [symbol]
                for metric in metrics_names:
                    if symbol in comparison.metrics_comparison[metric]:
                        value = comparison.metrics_comparison[metric][symbol]
                        # パーセンテージ表示が適切な指標の処理
                        if metric in ['roe', 'dividend_yield', 'equity_ratio']:
                            row.append(f"{value*100:.1f}%")
                        else:
                            row.append(f"{value:.2f}")
                    else:
                        row.append("N/A")
                    
                    # ランキング情報を追加
                    if symbol in comparison.rank.get(metric, {}):
                        rank = comparison.rank[metric][symbol]
                        row[-1] += f" ({rank}位)"
                
                table_data.append(row)
            
            # カラムヘッダー
            headers = ['銘柄'] + [metric.upper() for metric in metrics_names]
            
            # テーブルの作成
            fig = go.Figure(data=[go.Table(
                header=dict(
                    values=headers,
                    fill_color=self.color_palette['primary'],
                    font=dict(color='white', size=12),
                    align="center"
                ),
                cells=dict(
                    values=list(zip(*table_data)),
                    fill_color=[['lightgray' if i == 0 else 'white' for i in range(len(table_data))]],
                    align="center",
                    font=dict(size=11)
                )
            )])
            
            fig.update_layout(
                title=f'{comparison.target_symbol} 同業他社比較',
                height=400,
                template='plotly_white'
            )
            
            logger.info(f"同業他社比較テーブル作成完了: {comparison.target_symbol}")
            return fig
            
        except Exception as e:
            logger.error(f"同業他社比較テーブル作成エラー: {str(e)}")
            return go.Figure()
    
    def create_comprehensive_dashboard(
        self,
        symbol: str,
        metrics: FinancialMetrics,
        growth_trend: GrowthTrend,
        health_score: HealthScoreResult,
        comparison: Optional[ComparisonResult] = None
    ) -> List[go.Figure]:
        """総合ダッシュボード用のチャート群を作成"""
        try:
            figures = []
            
            # 1. 成長トレンド
            if growth_trend:
                figures.append(self.plot_growth_trend(growth_trend))
            
            # 2. 健全性スコアレーダーチャート
            if health_score:
                figures.append(self.plot_health_score_radar(health_score))
            
            # 3. 同業他社比較
            if comparison:
                figures.append(self.plot_peer_comparison_table(comparison))
            
            # 4. 基本指標サマリー
            if metrics:
                summary_fig = self._create_metrics_summary_chart(metrics)
                figures.append(summary_fig)
            
            logger.info(f"総合ダッシュボード作成完了: {symbol} ({len(figures)}個のチャート)")
            return figures
            
        except Exception as e:
            logger.error(f"総合ダッシュボード作成エラー: {str(e)}")
            return []
    
    def _create_metrics_summary_chart(self, metrics: FinancialMetrics) -> go.Figure:
        """基本指標サマリーチャート"""
        try:
            # 指標の表示用データ
            data = []
            
            if metrics.per is not None:
                data.append({"指標": "PER", "値": metrics.per, "単位": "倍"})
            if metrics.pbr is not None:
                data.append({"指標": "PBR", "値": metrics.pbr, "単位": "倍"})
            if metrics.roe is not None:
                data.append({"指標": "ROE", "値": metrics.roe * 100, "単位": "%"})
            if metrics.dividend_yield is not None:
                data.append({"指標": "配当利回り", "値": metrics.dividend_yield * 100, "単位": "%"})
            if metrics.current_ratio is not None:
                data.append({"指標": "流動比率", "値": metrics.current_ratio, "単位": "倍"})
            if metrics.equity_ratio is not None:
                data.append({"指標": "自己資本比率", "値": metrics.equity_ratio * 100, "単位": "%"})
            
            if not data:
                return go.Figure()
            
            df = pd.DataFrame(data)
            
            # 横棒グラフ
            fig = go.Figure(go.Bar(
                x=df['値'],
                y=df['指標'],
                orientation='h',
                marker_color=self.color_palette['primary'],
                text=[f"{row['値']:.1f}{row['単位']}" for _, row in df.iterrows()],
                textposition='auto'
            ))
            
            fig.update_layout(
                title=f'{metrics.symbol} 主要財務指標',
                xaxis_title="値",
                height=400,
                template='plotly_white'
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"指標サマリーチャート作成エラー: {str(e)}")
            return go.Figure()