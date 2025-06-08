"""
ファンダメンタル分析ダッシュボードコンポーネントのユニットテスト
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Streamlitのインポートを条件付きで行う
try:
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    STREAMLIT_TEST_AVAILABLE = True
except ImportError:
    STREAMLIT_TEST_AVAILABLE = False
    st = None

from src.technical_analysis.fundamental_analysis import (
    FundamentalAnalyzer,
    FinancialMetrics,
    GrowthTrend,
    HealthScoreResult,
    HealthScore
)


@pytest.mark.skipif(not STREAMLIT_TEST_AVAILABLE, reason="Streamlit not available")
class TestFundamentalAnalysisDashboardErrorHandling:
    """ダッシュボードのエラーハンドリングテスト（Issue #97対応）"""
    
    @pytest.fixture
    def mock_analyzer(self):
        """モックアナライザー"""
        return Mock(spec=FundamentalAnalyzer)
    
    @pytest.fixture
    def mock_visualizer(self):
        """モックビジュアライザー"""
        return Mock()
    
    @patch('dashboard.components.fundamental_analysis.FundamentalAnalyzer')
    @patch('dashboard.components.fundamental_analysis.FundamentalVisualizer')
    @patch('streamlit.warning')
    def test_growth_trend_data_insufficient_warning(self, mock_st_warning, mock_visualizer_class, mock_analyzer_class):
        """成長トレンドデータ不足時の警告表示テスト"""
        from dashboard.components.fundamental_analysis import display_analysis_results
        
        # モックの設定
        mock_analyzer = Mock()
        mock_visualizer = Mock()
        mock_analyzer_class.return_value = mock_analyzer
        mock_visualizer_class.return_value = mock_visualizer
        
        # 基本指標は正常、成長トレンドはNone
        mock_metrics = FinancialMetrics(
            symbol='TEST',
            company_name='Test Company',
            price=100.0,
            market_cap=1000000000
        )
        
        growth_trend = None  # 成長トレンドデータなし
        health_score = Mock()
        comparison = None
        
        # テスト実行
        display_analysis_results(
            'TEST', 
            mock_metrics, 
            growth_trend, 
            health_score, 
            comparison, 
            mock_visualizer
        )
        
        # 警告メッセージが表示されることを確認
        mock_st_warning.assert_called_with("成長トレンドデータを取得できませんでした。")
    
    @patch('dashboard.components.fundamental_analysis.FundamentalAnalyzer')
    @patch('dashboard.components.fundamental_analysis.FundamentalVisualizer')
    @patch('streamlit.warning')
    def test_health_score_calculation_failure_warning(self, mock_st_warning, mock_visualizer_class, mock_analyzer_class):
        """健全性スコア計算失敗時の警告表示テスト"""
        from dashboard.components.fundamental_analysis import display_analysis_results
        
        # モックの設定
        mock_analyzer = Mock()
        mock_visualizer = Mock()
        mock_analyzer_class.return_value = mock_analyzer
        mock_visualizer_class.return_value = mock_visualizer
        
        # 基本指標は正常、健全性スコアはNone
        mock_metrics = FinancialMetrics(
            symbol='TEST',
            company_name='Test Company',
            price=100.0,
            market_cap=1000000000
        )
        
        growth_trend = Mock()
        health_score = None  # 健全性スコア計算失敗
        comparison = None
        
        # テスト実行
        display_analysis_results(
            'TEST', 
            mock_metrics, 
            growth_trend, 
            health_score, 
            comparison, 
            mock_visualizer
        )
        
        # 警告メッセージが表示されることを確認
        mock_st_warning.assert_called_with("健全性スコアを計算できませんでした。")
    
    @patch('dashboard.components.fundamental_analysis.FundamentalAnalyzer')
    @patch('dashboard.components.fundamental_analysis.st')
    def test_enhanced_error_message_display(self, mock_st, mock_analyzer_class):
        """改善されたエラーメッセージ表示のテスト"""
        from dashboard.components.fundamental_analysis import render_fundamental_analysis_tab
        
        # モックの設定
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer
        
        # 基本財務指標の取得は成功
        mock_metrics = FinancialMetrics(
            symbol='TEST',
            company_name='Test Company',
            price=100.0
        )
        mock_analyzer.get_financial_metrics.return_value = mock_metrics
        
        # 成長トレンド分析は失敗
        mock_analyzer.analyze_growth_trend.return_value = None
        
        # 健全性スコア計算は成功
        mock_health_score = HealthScoreResult(
            symbol='TEST',
            total_score=75.0,
            score_breakdown={},
            health_level=HealthScore.GOOD,
            recommendations=[]
        )
        mock_analyzer.calculate_health_score.return_value = mock_health_score
        
        # サイドバーの模擬設定
        mock_st.sidebar.text_input.return_value = 'TEST'
        mock_st.sidebar.text_area.return_value = 'PEER1,PEER2'
        mock_st.sidebar.slider.return_value = 5
        mock_st.sidebar.button.return_value = True
        
        # テスト実行
        render_fundamental_analysis_tab()
        
        # 改善されたエラーメッセージが表示されることを確認
        expected_warning = "銘柄 TEST の成長トレンドデータが不十分です。財務諸表データが取得できない可能性があります。"
        mock_st.warning.assert_called_with(expected_warning)
    
    @patch('dashboard.components.fundamental_analysis.FundamentalAnalyzer')
    @patch('dashboard.components.fundamental_analysis.st')
    def test_comprehensive_error_handling_flow(self, mock_st, mock_analyzer_class):
        """包括的なエラーハンドリングフローのテスト"""
        from dashboard.components.fundamental_analysis import render_fundamental_analysis_tab
        
        # モックの設定
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer
        
        # 全ての分析が失敗するケース
        mock_analyzer.get_financial_metrics.return_value = None
        mock_analyzer.analyze_growth_trend.return_value = None
        mock_analyzer.calculate_health_score.return_value = None
        mock_analyzer.compare_with_peers.return_value = None
        
        # サイドバーの模擬設定
        mock_st.sidebar.text_input.return_value = 'INVALID'
        mock_st.sidebar.text_area.return_value = ''
        mock_st.sidebar.slider.return_value = 5
        mock_st.sidebar.button.return_value = True
        
        # テスト実行
        render_fundamental_analysis_tab()
        
        # エラーメッセージが表示されることを確認
        mock_st.error.assert_called_with("銘柄 INVALID の財務データを取得できませんでした。銘柄コードを確認してください。")
    
    @patch('dashboard.components.fundamental_analysis.FundamentalAnalyzer')
    @patch('dashboard.components.fundamental_analysis.st')
    def test_partial_success_scenario(self, mock_st, mock_analyzer_class):
        """部分的成功シナリオのテスト"""
        from dashboard.components.fundamental_analysis import render_fundamental_analysis_tab
        
        # モックの設定
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer
        
        # 基本指標は成功、その他は失敗
        mock_metrics = FinancialMetrics(
            symbol='PARTIAL',
            company_name='Partial Success Company',
            price=50.0,
            market_cap=500000000
        )
        mock_analyzer.get_financial_metrics.return_value = mock_metrics
        mock_analyzer.analyze_growth_trend.return_value = None
        mock_analyzer.calculate_health_score.return_value = None
        mock_analyzer.compare_with_peers.return_value = None
        
        # サイドバーの模擬設定
        mock_st.sidebar.text_input.return_value = 'PARTIAL'
        mock_st.sidebar.text_area.return_value = 'PEER1'
        mock_st.sidebar.slider.return_value = 5
        mock_st.sidebar.button.return_value = True
        
        # テスト実行
        render_fundamental_analysis_tab()
        
        # 部分的な成功でも適切に処理されることを確認
        # エラーは表示されず、警告のみ表示される
        mock_st.error.assert_not_called()
        mock_st.warning.assert_called()


@pytest.mark.skipif(not STREAMLIT_TEST_AVAILABLE, reason="Streamlit not available")
class TestFundamentalAnalysisDashboardComponents:
    """ダッシュボードコンポーネントの単体テスト"""
    
    @patch('streamlit.columns')
    @patch('streamlit.metric')
    @patch('streamlit.markdown')
    def test_display_basic_metrics_with_complete_data(self, mock_markdown, mock_metric, mock_columns):
        """完全な基本指標データの表示テスト"""
        from dashboard.components.fundamental_analysis import display_basic_metrics
        
        # 完全な財務指標データ
        metrics = FinancialMetrics(
            symbol='COMPLETE',
            company_name='Complete Company',
            per=15.0,
            pbr=1.2,
            roe=0.18,
            roa=0.12,
            dividend_yield=0.025,
            current_ratio=2.5,
            equity_ratio=0.60,
            debt_ratio=0.25
        )
        
        mock_visualizer = Mock()
        mock_visualizer._create_metrics_summary_chart.return_value = Mock()
        
        # カラム分割のモック
        mock_col1, mock_col2, mock_col3 = Mock(), Mock(), Mock()
        mock_columns.return_value = [mock_col1, mock_col2, mock_col3]
        
        # テスト実行
        display_basic_metrics(metrics, mock_visualizer)
        
        # 適切にカラムが作成されることを確認
        mock_columns.assert_called_with(3)
        
        # ビジュアライザーが呼ばれることを確認
        mock_visualizer._create_metrics_summary_chart.assert_called_once_with(metrics)
    
    @patch('streamlit.columns')
    @patch('streamlit.metric')
    @patch('streamlit.markdown')
    def test_display_basic_metrics_with_partial_data(self, mock_markdown, mock_metric, mock_columns):
        """部分的な基本指標データの表示テスト"""
        from dashboard.components.fundamental_analysis import display_basic_metrics
        
        # 部分的な財務指標データ
        metrics = FinancialMetrics(
            symbol='PARTIAL',
            company_name='Partial Company',
            per=15.0,
            pbr=None,  # データなし
            roe=0.18,
            roa=None,  # データなし
            dividend_yield=None,  # データなし
            current_ratio=2.5,
            equity_ratio=None,  # データなし
            debt_ratio=0.25
        )
        
        mock_visualizer = Mock()
        mock_visualizer._create_metrics_summary_chart.return_value = Mock()
        
        # カラム分割のモック
        mock_col1, mock_col2, mock_col3 = Mock(), Mock(), Mock()
        mock_columns.return_value = [mock_col1, mock_col2, mock_col3]
        
        # テスト実行
        display_basic_metrics(metrics, mock_visualizer)
        
        # 部分的なデータでも適切に処理されることを確認
        mock_columns.assert_called_with(3)
        mock_visualizer._create_metrics_summary_chart.assert_called_once_with(metrics)
    
    @patch('streamlit.columns')
    @patch('streamlit.markdown')
    def test_display_growth_trend_with_valid_data(self, mock_markdown, mock_columns):
        """有効な成長トレンドデータの表示テスト"""
        from dashboard.components.fundamental_analysis import display_growth_trend
        
        # 有効な成長トレンドデータ
        growth_trend = GrowthTrend(
            symbol='GROWTH',
            revenue_trend=[800, 900, 1000],
            profit_trend=[80, 90, 100],
            years=['2022', '2023', '2024'],
            revenue_cagr=0.12,
            profit_cagr=0.15,
            volatility=0.08
        )
        
        mock_visualizer = Mock()
        mock_visualizer.plot_growth_trend.return_value = Mock()
        
        # カラム分割のモック
        mock_col1, mock_col2, mock_col3 = Mock(), Mock(), Mock()
        mock_columns.return_value = [mock_col1, mock_col2, mock_col3]
        
        # テスト実行
        display_growth_trend(growth_trend, mock_visualizer)
        
        # 適切にカラムが作成されることを確認
        mock_columns.assert_called()
        
        # ビジュアライザーが呼ばれることを確認
        mock_visualizer.plot_growth_trend.assert_called_once_with(growth_trend)
    
    def test_evaluate_growth_function(self):
        """成長率評価関数のテスト"""
        from dashboard.components.fundamental_analysis import evaluate_growth
        
        # 各成長率レベルのテスト
        assert evaluate_growth(None) == "データ不足"
        assert evaluate_growth(0.20) == "🚀 非常に高い"
        assert evaluate_growth(0.12) == "📈 高い"
        assert evaluate_growth(0.07) == "📊 普通"
        assert evaluate_growth(0.02) == "📉 低い"
        assert evaluate_growth(-0.05) == "📉 マイナス成長"
    
    def test_get_score_color_function(self):
        """スコア色取得関数のテスト"""
        from dashboard.components.fundamental_analysis import get_score_color
        
        # 各スコアレベルの色テスト
        assert get_score_color(95) == "#4CAF50"  # 緑
        assert get_score_color(80) == "#8BC34A"  # 薄緑
        assert get_score_color(65) == "#FFC107"  # 黄
        assert get_score_color(45) == "#FF9800"  # オレンジ
        assert get_score_color(30) == "#F44336"  # 赤


if __name__ == "__main__":
    pytest.main([__file__])