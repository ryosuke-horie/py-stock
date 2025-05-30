"""
FundamentalVisualizerクラスのユニットテスト
"""

import pytest
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from src.technical_analysis.fundamental_visualization import FundamentalVisualizer
from src.technical_analysis.fundamental_analysis import (
    FinancialMetrics, 
    GrowthTrend, 
    ComparisonResult, 
    HealthScoreResult,
    HealthScore
)


class TestFundamentalVisualizer:
    """FundamentalVisualizerのテストクラス"""
    
    def setup_method(self):
        """各テストメソッド実行前の初期化"""
        self.visualizer = FundamentalVisualizer()
        
        # テスト用データの作成
        self.sample_metrics = FinancialMetrics(
            symbol="7203.T",
            company_name="トヨタ自動車",
            per=15.2,
            pbr=1.8,
            roe=0.12,
            dividend_yield=0.025,
            current_ratio=1.5,
            equity_ratio=0.45,
            market_cap=5000000
        )
        
        self.sample_growth_trend = GrowthTrend(
            symbol="7203.T",
            years=[2020, 2021, 2022, 2023],
            revenue_trend=[2000000, 2200000, 2400000, 2500000],
            profit_trend=[100000, 120000, 140000, 150000],
            revenue_cagr=0.08,
            profit_cagr=0.14
        )
        
        self.sample_health_score = HealthScoreResult(
            symbol="7203.T",
            total_score=75.5,
            health_level=HealthScore.GOOD,
            score_breakdown={
                'per': 80.0,
                'pbr': 70.0,
                'roe': 85.0,
                'liquidity': 75.0,
                'stability': 80.0,
                'dividend': 65.0
            },
            recommendations=["ROEが良好", "流動性に注意"]
        )
        
        self.sample_comparison = ComparisonResult(
            target_symbol="7203.T",
            comparison_symbols=["7201.T", "7267.T"],
            metrics_comparison={
                'per': {"7203.T": 15.2, "7201.T": 12.8, "7267.T": 18.5},
                'pbr': {"7203.T": 1.8, "7201.T": 1.2, "7267.T": 2.1},
                'roe': {"7203.T": 0.12, "7201.T": 0.15, "7267.T": 0.08}
            },
            rank={
                'per': {"7203.T": 2, "7201.T": 1, "7267.T": 3},
                'pbr': {"7203.T": 2, "7201.T": 1, "7267.T": 3},
                'roe': {"7203.T": 2, "7201.T": 1, "7267.T": 3}
            },
            industry_average={'per': 15.5, 'pbr': 1.7, 'roe': 0.11}
        )
    
    def test_initialization(self):
        """初期化テスト"""
        visualizer = FundamentalVisualizer()
        
        assert hasattr(visualizer, 'color_palette')
        assert 'primary' in visualizer.color_palette
        assert 'secondary' in visualizer.color_palette
        assert 'success' in visualizer.color_palette
        assert 'warning' in visualizer.color_palette
    
    def test_plot_growth_trend(self):
        """成長トレンドグラフ作成テスト"""
        fig = self.visualizer.plot_growth_trend(self.sample_growth_trend)
        
        assert isinstance(fig, go.Figure)
        assert fig.data is not None
        assert len(fig.data) >= 2  # 売上と利益の2つの系列
        
        # データの確認
        revenue_trace = fig.data[0]
        profit_trace = fig.data[1]
        
        assert revenue_trace.name == '売上'
        assert profit_trace.name == '純利益'
        assert len(revenue_trace.x) == len(self.sample_growth_trend.years)
        assert len(revenue_trace.y) == len(self.sample_growth_trend.revenue_trend)
    
    def test_plot_growth_trend_with_none_cagr(self):
        """CAGR未設定の成長トレンドグラフテスト"""
        growth_trend_no_cagr = GrowthTrend(
            symbol="7203.T",
            years=[2020, 2021, 2022, 2023],
            revenue_trend=[2000000, 2200000, 2400000, 2500000],
            profit_trend=[100000, 120000, 140000, 150000],
            revenue_cagr=None,
            profit_cagr=None
        )
        
        fig = self.visualizer.plot_growth_trend(growth_trend_no_cagr)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 2
    
    def test_plot_financial_metrics_comparison(self):
        """財務指標比較グラフテスト"""
        metrics_list = [
            self.sample_metrics,
            FinancialMetrics(
                symbol="7201.T",
                company_name="日産自動車",
                per=12.8,
                pbr=1.2,
                roe=0.15,
                dividend_yield=0.03,
                current_ratio=1.8,
                equity_ratio=0.55
            )
        ]
        
        fig = self.visualizer.plot_financial_metrics_comparison(metrics_list)
        
        assert isinstance(fig, go.Figure)
        assert fig.data is not None
        assert len(fig.data) > 0
    
    def test_plot_financial_metrics_comparison_with_none_values(self):
        """None値を含む財務指標比較テスト"""
        metrics_with_none = FinancialMetrics(
            symbol="TEST.T",
            company_name="テスト会社",
            per=None,
            pbr=None,
            roe=0.10,
            dividend_yield=None,
            current_ratio=1.5,
            equity_ratio=0.40
        )
        
        fig = self.visualizer.plot_financial_metrics_comparison([metrics_with_none])
        
        assert isinstance(fig, go.Figure)
    
    def test_plot_health_score_radar(self):
        """健全性スコアレーダーチャートテスト"""
        fig = self.visualizer.plot_health_score_radar(self.sample_health_score)
        
        assert isinstance(fig, go.Figure)
        assert fig.data is not None
        assert len(fig.data) >= 1
        
        # レーダーチャートの確認
        radar_trace = fig.data[0]
        assert radar_trace.type == 'scatterpolar'
        assert radar_trace.fill == 'toself'
        assert len(radar_trace.r) > 0
        assert len(radar_trace.theta) > 0
    
    def test_plot_health_score_radar_different_health_levels(self):
        """異なる健全性レベルのレーダーチャートテスト"""
        health_levels = [
            HealthScore.EXCELLENT,
            HealthScore.GOOD,
            HealthScore.AVERAGE,
            HealthScore.POOR,
            HealthScore.CRITICAL
        ]
        
        for level in health_levels:
            health_score = HealthScoreResult(
                symbol="TEST.T",
                total_score=80.0,
                health_level=level,
                score_breakdown={
                    'per': 80.0,
                    'pbr': 70.0,
                    'roe': 85.0,
                    'liquidity': 75.0,
                    'stability': 80.0,
                    'dividend': 65.0
                },
                recommendations=[]
            )
            
            fig = self.visualizer.plot_health_score_radar(health_score)
            assert isinstance(fig, go.Figure)
    
    def test_plot_health_score_radar_empty_breakdown(self):
        """空のスコア内訳のレーダーチャートテスト"""
        empty_health_score = HealthScoreResult(
            symbol="EMPTY.T",
            total_score=0.0,
            health_level=HealthScore.CRITICAL,
            score_breakdown={},
            recommendations=[]
        )
        
        fig = self.visualizer.plot_health_score_radar(empty_health_score)
        
        assert isinstance(fig, go.Figure)
        # 空のデータの場合は空のFigureが返される
    
    def test_plot_peer_comparison_table(self):
        """同業他社比較テーブルテスト"""
        fig = self.visualizer.plot_peer_comparison_table(self.sample_comparison)
        
        assert isinstance(fig, go.Figure)
        assert fig.data is not None
        assert len(fig.data) >= 1
        
        # テーブルの確認
        table_trace = fig.data[0]
        assert table_trace.type == 'table'
        assert table_trace.header is not None
        assert table_trace.cells is not None
    
    def test_create_comprehensive_dashboard(self):
        """総合ダッシュボード作成テスト"""
        figures = self.visualizer.create_comprehensive_dashboard(
            symbol="7203.T",
            metrics=self.sample_metrics,
            growth_trend=self.sample_growth_trend,
            health_score=self.sample_health_score,
            comparison=self.sample_comparison
        )
        
        assert isinstance(figures, list)
        assert len(figures) >= 3  # 成長トレンド、健全性、比較テーブル、指標サマリー
        
        for fig in figures:
            assert isinstance(fig, go.Figure)
    
    def test_create_comprehensive_dashboard_partial_data(self):
        """部分的なデータでの総合ダッシュボードテスト"""
        figures = self.visualizer.create_comprehensive_dashboard(
            symbol="7203.T",
            metrics=self.sample_metrics,
            growth_trend=None,
            health_score=self.sample_health_score,
            comparison=None
        )
        
        assert isinstance(figures, list)
        assert len(figures) >= 1
    
    def test_create_metrics_summary_chart(self):
        """指標サマリーチャート作成テスト"""
        fig = self.visualizer._create_metrics_summary_chart(self.sample_metrics)
        
        assert isinstance(fig, go.Figure)
        assert fig.data is not None
        assert len(fig.data) >= 1
        
        # 横棒グラフの確認
        bar_trace = fig.data[0]
        assert bar_trace.type == 'bar'
        assert bar_trace.orientation == 'h'
    
    def test_create_metrics_summary_chart_with_none_values(self):
        """None値を含む指標サマリーチャートテスト"""
        metrics_with_none = FinancialMetrics(
            symbol="TEST.T",
            company_name="テスト会社",
            per=None,
            pbr=None,
            roe=None,
            dividend_yield=None,
            current_ratio=None,
            equity_ratio=None
        )
        
        fig = self.visualizer._create_metrics_summary_chart(metrics_with_none)
        
        assert isinstance(fig, go.Figure)
        # すべてNoneの場合は空のFigureが返される
    
    @patch('src.technical_analysis.fundamental_visualization.logger')
    def test_plot_growth_trend_with_exception(self, mock_logger):
        """成長トレンドグラフ作成時の例外処理テスト"""
        # 不正なデータを作成
        invalid_growth_trend = Mock()
        invalid_growth_trend.years = None
        
        fig = self.visualizer.plot_growth_trend(invalid_growth_trend)
        
        assert isinstance(fig, go.Figure)
        mock_logger.error.assert_called_once()
    
    @patch('src.technical_analysis.fundamental_visualization.logger')
    def test_plot_financial_metrics_comparison_with_exception(self, mock_logger):
        """財務指標比較グラフ作成時の例外処理テスト"""
        # 不正なデータを作成
        invalid_metrics = [Mock()]
        invalid_metrics[0].symbol = None
        
        fig = self.visualizer.plot_financial_metrics_comparison(invalid_metrics)
        
        assert isinstance(fig, go.Figure)
        mock_logger.error.assert_called_once()
    
    @patch('src.technical_analysis.fundamental_visualization.logger')
    def test_plot_health_score_radar_with_exception(self, mock_logger):
        """健全性スコアレーダーチャート作成時の例外処理テスト"""
        # 不正なデータを作成
        invalid_health_score = Mock()
        invalid_health_score.score_breakdown = None
        
        fig = self.visualizer.plot_health_score_radar(invalid_health_score)
        
        assert isinstance(fig, go.Figure)
        mock_logger.error.assert_called_once()
    
    @patch('src.technical_analysis.fundamental_visualization.logger')
    def test_plot_peer_comparison_table_with_exception(self, mock_logger):
        """同業他社比較テーブル作成時の例外処理テスト"""
        # 不正なデータを作成
        invalid_comparison = Mock()
        invalid_comparison.target_symbol = None
        
        fig = self.visualizer.plot_peer_comparison_table(invalid_comparison)
        
        assert isinstance(fig, go.Figure)
        mock_logger.error.assert_called_once()
    
    @patch('src.technical_analysis.fundamental_visualization.logger')
    def test_create_comprehensive_dashboard_with_exception(self, mock_logger):
        """総合ダッシュボード作成時の例外処理テスト"""
        # 不正なデータを作成（例外を発生させる）
        with patch.object(self.visualizer, 'plot_growth_trend', side_effect=Exception("Test error")):
            figures = self.visualizer.create_comprehensive_dashboard(
                symbol="TEST.T",
                metrics=self.sample_metrics,
                growth_trend=self.sample_growth_trend,
                health_score=self.sample_health_score
            )
            
            assert isinstance(figures, list)
            mock_logger.error.assert_called()
    
    def test_color_palette_values(self):
        """カラーパレットの値テスト"""
        palette = self.visualizer.color_palette
        
        # すべての色が16進数カラーコードであることを確認
        for color_name, color_value in palette.items():
            assert isinstance(color_value, str)
            assert color_value.startswith('#')
            assert len(color_value) == 7  # #RRGGBB形式
    
    def test_empty_comparison_result(self):
        """空の比較結果でのテーブル作成テスト"""
        empty_comparison = ComparisonResult(
            target_symbol="EMPTY.T",
            comparison_symbols=[],
            metrics_comparison={},
            rank={},
            industry_average={}
        )
        
        fig = self.visualizer.plot_peer_comparison_table(empty_comparison)
        
        assert isinstance(fig, go.Figure)
    
    def test_single_metric_comparison(self):
        """単一指標の比較グラフテスト"""
        single_metric = FinancialMetrics(
            symbol="SINGLE.T",
            company_name="シングル会社",
            per=15.0,
            pbr=None,
            roe=None,
            dividend_yield=None,
            current_ratio=None,
            equity_ratio=None
        )
        
        fig = self.visualizer.plot_financial_metrics_comparison([single_metric])
        
        assert isinstance(fig, go.Figure)
        # PERのみのデータでもグラフが作成されることを確認