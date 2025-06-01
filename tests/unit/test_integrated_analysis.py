"""
統合分析モジュールのユニットテスト
"""

import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import Mock, patch

from src.technical_analysis.integrated_analysis import IntegratedAnalyzer
from src.technical_analysis.investment_story_generator import TechnicalAnalysisData, InvestmentReport
from src.technical_analysis.fundamental_analysis import FinancialMetrics, GrowthTrend, HealthScoreResult, HealthScore


class TestIntegratedAnalyzer:
    """IntegratedAnalyzerクラスのテスト"""
    
    @pytest.fixture
    def analyzer(self):
        """アナライザーのフィクスチャ"""
        return IntegratedAnalyzer()
    
    @pytest.fixture
    def sample_stock_data(self):
        """サンプル株価データ"""
        dates = pd.date_range(start='2024-01-01', periods=60, freq='D')
        prices = 1000 + (pd.Series(range(60)) * 2)  # 上昇トレンド
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices + 10,
            'low': prices - 10,
            'close': prices + 5,
            'volume': [1000000] * 60
        })
    
    @pytest.fixture
    def sample_fundamental_results(self):
        """サンプルファンダメンタル分析結果"""
        metrics = FinancialMetrics(
            symbol="TEST",
            company_name="Test Company",
            per=15.0,
            pbr=1.2,
            roe=0.18,
            price=1000.0
        )
        
        growth_trend = GrowthTrend(
            symbol="TEST",
            revenue_trend=[100, 110, 121],
            profit_trend=[10, 12, 14],
            years=["2022", "2023", "2024"],
            revenue_cagr=0.10
        )
        
        health_score = HealthScoreResult(
            symbol="TEST",
            total_score=85.0,
            score_breakdown={'per': 90},
            health_level=HealthScore.GOOD,
            recommendations=[]
        )
        
        return {
            'metrics': metrics,
            'growth_trend': growth_trend,
            'health_score': health_score,
            'peer_comparison': None,
            'status': 'success'
        }
    
    def test_initialization(self, analyzer):
        """初期化テスト"""
        assert analyzer.fundamental_analyzer is not None
        assert analyzer.story_generator is not None
        assert analyzer.data_collector is not None
    
    @patch('src.technical_analysis.integrated_analysis.IntegratedAnalyzer._perform_fundamental_analysis')
    @patch('src.technical_analysis.integrated_analysis.IntegratedAnalyzer._perform_basic_technical_analysis')
    @patch('src.technical_analysis.integrated_analysis.IntegratedAnalyzer._generate_investment_story')
    def test_generate_complete_analysis_success(
        self, mock_story, mock_technical, mock_fundamental, analyzer, sample_fundamental_results
    ):
        """完全統合分析成功テスト"""
        
        # モックの設定
        mock_fundamental.return_value = sample_fundamental_results
        mock_technical.return_value = TechnicalAnalysisData(
            trend="上昇", momentum="強い", signal="買い"
        )
        mock_story.return_value = Mock(spec=InvestmentReport)
        
        # テスト実行
        result = analyzer.generate_complete_analysis("TEST")
        
        # 検証
        assert result['symbol'] == "TEST"
        assert 'analysis_date' in result
        assert 'fundamental_analysis' in result
        assert 'technical_analysis' in result
        assert 'investment_report' in result
        assert 'summary' in result
        
        mock_fundamental.assert_called_once_with("TEST", True, None)
        mock_technical.assert_called_once_with("TEST")
        mock_story.assert_called_once()
    
    @patch('src.technical_analysis.integrated_analysis.IntegratedAnalyzer._perform_fundamental_analysis')
    def test_generate_complete_analysis_error(self, mock_fundamental, analyzer):
        """完全統合分析エラーテスト"""
        
        # エラーを発生させる
        mock_fundamental.side_effect = Exception("Test error")
        
        # テスト実行
        result = analyzer.generate_complete_analysis("TEST")
        
        # 検証
        assert result['symbol'] == "TEST"
        assert result.get('status') == 'error'
        assert 'error_message' in result
    
    def test_perform_fundamental_analysis_success(self, analyzer):
        """ファンダメンタル分析実行成功テスト"""
        
        with patch.object(analyzer.fundamental_analyzer, 'get_financial_metrics') as mock_metrics, \
             patch.object(analyzer.fundamental_analyzer, 'analyze_growth_trend') as mock_growth, \
             patch.object(analyzer.fundamental_analyzer, 'calculate_health_score') as mock_health, \
             patch.object(analyzer.fundamental_analyzer, 'compare_with_peers') as mock_compare:
            
            # モックの設定
            mock_metrics.return_value = Mock()
            mock_growth.return_value = Mock()
            mock_health.return_value = Mock()
            mock_compare.return_value = Mock()
            
            # テスト実行
            result = analyzer._perform_fundamental_analysis("TEST", True, ["PEER1"])
            
            # 検証
            assert result['status'] == 'success'
            assert 'metrics' in result
            assert 'growth_trend' in result
            assert 'health_score' in result
            assert 'peer_comparison' in result
            
            mock_metrics.assert_called_once_with("TEST")
            mock_growth.assert_called_once_with("TEST")
            mock_health.assert_called_once_with("TEST")
            mock_compare.assert_called_once_with("TEST", ["PEER1"])
    
    def test_perform_fundamental_analysis_error(self, analyzer):
        """ファンダメンタル分析実行エラーテスト"""
        
        with patch.object(analyzer.fundamental_analyzer, 'get_financial_metrics') as mock_metrics:
            # エラーを発生させる
            mock_metrics.side_effect = Exception("Test error")
            
            # テスト実行
            result = analyzer._perform_fundamental_analysis("TEST", False, None)
            
            # 検証
            assert result['status'] == 'error'
            assert 'error_message' in result
            assert result['metrics'] is None
    
    def test_perform_basic_technical_analysis_success(self, analyzer, sample_stock_data):
        """基本テクニカル分析成功テスト"""
        
        with patch.object(analyzer.data_collector, 'get_stock_data') as mock_data:
            mock_data.return_value = sample_stock_data
            
            # テスト実行
            result = analyzer._perform_basic_technical_analysis("TEST")
            
            # 検証
            assert isinstance(result, TechnicalAnalysisData)
            assert result.trend in ["上昇", "下降", "横ばい"]
            assert result.momentum in ["強い", "普通", "弱い"]
            assert result.signal in ["買い", "売り", "中立"]
            assert result.support_level is not None
            assert result.resistance_level is not None
    
    def test_perform_basic_technical_analysis_no_data(self, analyzer):
        """テクニカル分析データなしテスト"""
        
        with patch.object(analyzer.data_collector, 'get_stock_data') as mock_data:
            mock_data.return_value = None
            
            # テスト実行
            result = analyzer._perform_basic_technical_analysis("TEST")
            
            # 検証
            assert result is None
    
    def test_perform_basic_technical_analysis_uptrend(self, analyzer):
        """上昇トレンドのテクニカル分析テスト"""
        
        # 上昇トレンドのデータを作成
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        base_price = 1000
        uptrend_prices = [base_price + i * 10 for i in range(30)]
        
        stock_data = pd.DataFrame({
            'timestamp': dates,
            'close': uptrend_prices,
            'high': [p + 5 for p in uptrend_prices],
            'low': [p - 5 for p in uptrend_prices]
        })
        
        with patch.object(analyzer.data_collector, 'get_stock_data') as mock_data:
            mock_data.return_value = stock_data
            
            # テスト実行
            result = analyzer._perform_basic_technical_analysis("TEST")
            
            # 検証
            assert result.trend == "上昇"
            assert result.momentum in ["強い", "普通"]
            assert result.signal in ["買い", "中立"]
    
    def test_perform_basic_technical_analysis_downtrend(self, analyzer):
        """下降トレンドのテクニカル分析テスト"""
        
        # 下降トレンドのデータを作成
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        base_price = 1000
        downtrend_prices = [base_price - i * 10 for i in range(30)]
        
        stock_data = pd.DataFrame({
            'timestamp': dates,
            'close': downtrend_prices,
            'high': [p + 5 for p in downtrend_prices],
            'low': [p - 5 for p in downtrend_prices]
        })
        
        with patch.object(analyzer.data_collector, 'get_stock_data') as mock_data:
            mock_data.return_value = stock_data
            
            # テスト実行
            result = analyzer._perform_basic_technical_analysis("TEST")
            
            # 検証
            assert result.trend == "下降"
            assert result.signal in ["売り", "中立"]
    
    def test_generate_investment_story_success(self, analyzer, sample_fundamental_results):
        """投資ストーリー生成成功テスト"""
        
        technical_data = TechnicalAnalysisData(
            trend="上昇", momentum="強い", signal="買い"
        )
        
        with patch.object(analyzer.story_generator, 'generate_comprehensive_report') as mock_report:
            mock_report.return_value = Mock(spec=InvestmentReport)
            
            # テスト実行
            result = analyzer._generate_investment_story("TEST", sample_fundamental_results, technical_data)
            
            # 検証
            assert result is not None
            mock_report.assert_called_once()
            
            # 呼び出し引数の確認
            call_args = mock_report.call_args
            assert call_args[1]['symbol'] == "TEST"
            assert call_args[1]['financial_metrics'] == sample_fundamental_results['metrics']
            assert call_args[1]['technical_data'] == technical_data
    
    def test_generate_investment_story_error(self, analyzer, sample_fundamental_results):
        """投資ストーリー生成エラーテスト"""
        
        with patch.object(analyzer.story_generator, 'generate_comprehensive_report') as mock_report:
            mock_report.side_effect = Exception("Test error")
            
            # テスト実行
            result = analyzer._generate_investment_story("TEST", sample_fundamental_results, None)
            
            # 検証
            assert result is None
    
    def test_create_analysis_summary_high_score(self, analyzer, sample_fundamental_results):
        """高スコア分析サマリー作成テスト"""
        
        technical_data = TechnicalAnalysisData(
            trend="上昇", momentum="強い", signal="買い"
        )
        
        mock_report = Mock()
        mock_report.overall_assessment = "魅力的"
        mock_report.recommendation = "買い推奨"
        
        # テスト実行
        summary = analyzer._create_analysis_summary(
            "TEST", sample_fundamental_results, technical_data, mock_report
        )
        
        # 検証
        assert summary['symbol'] == "TEST"
        assert summary['overall_score'] > 70  # 高スコア
        assert summary['recommendation'] in ["買い推奨", "条件付き買い"]
        assert len(summary['key_strengths']) > 0
        assert len(summary['next_actions']) > 0
    
    def test_create_analysis_summary_low_score(self, analyzer):
        """低スコア分析サマリー作成テスト"""
        
        # 低スコアのファンダメンタル結果
        low_fundamental = {
            'status': 'success',
            'health_score': HealthScoreResult(
                symbol="TEST",
                total_score=30.0,
                score_breakdown={},
                health_level=HealthScore.CRITICAL,
                recommendations=["改善が必要"]
            ),
            'growth_trend': GrowthTrend(
                symbol="TEST",
                revenue_trend=[],
                profit_trend=[],
                years=[],
                revenue_cagr=-0.05  # マイナス成長
            )
        }
        
        technical_data = TechnicalAnalysisData(
            trend="下降", momentum="弱い", signal="売り"
        )
        
        # テスト実行
        summary = analyzer._create_analysis_summary(
            "TEST", low_fundamental, technical_data, None
        )
        
        # 検証
        assert summary['overall_score'] < 50  # 低スコア
        assert summary['recommendation'] in ["売り検討", "保有・様子見"]
        assert len(summary['key_concerns']) > 0
    
    def test_create_error_analysis(self, analyzer):
        """エラー分析結果作成テスト"""
        
        result = analyzer._create_error_analysis("TEST", "Test error message")
        
        # 検証
        assert result['symbol'] == "TEST"
        assert result['status'] == 'error'
        assert result['error_message'] == "Test error message"
        assert result['summary']['recommendation'] == "データ不足により判断不可"
        assert "分析データの取得に失敗" in result['summary']['key_concerns']
    
    @patch('src.technical_analysis.integrated_analysis.IntegratedAnalyzer.generate_complete_analysis')
    def test_generate_comparison_report_success(self, mock_analysis, analyzer):
        """比較レポート生成成功テスト"""
        
        # モック分析結果
        mock_analysis.side_effect = [
            {
                'symbol': 'SYMBOL1',
                'summary': {'overall_score': 80, 'recommendation': '買い推奨'}
            },
            {
                'symbol': 'SYMBOL2', 
                'summary': {'overall_score': 60, 'recommendation': '保有'}
            }
        ]
        
        # テスト実行
        result = analyzer.generate_comparison_report(['SYMBOL1', 'SYMBOL2'])
        
        # 検証
        assert result['comparison_type'] == 'multi_symbol'
        assert result['symbols'] == ['SYMBOL1', 'SYMBOL2']
        assert 'individual_analyses' in result
        assert 'comparison_summary' in result
        
        # 個別分析が2回実行されることを確認
        assert mock_analysis.call_count == 2
    
    @patch('src.technical_analysis.integrated_analysis.IntegratedAnalyzer.generate_complete_analysis')
    def test_generate_comparison_report_error(self, mock_analysis, analyzer):
        """比較レポート生成エラーテスト"""
        
        # エラーを発生させる
        mock_analysis.side_effect = Exception("Test error")
        
        # テスト実行
        result = analyzer.generate_comparison_report(['SYMBOL1'])
        
        # 検証
        assert result['status'] == 'error'
        assert 'error_message' in result
    
    def test_create_comparison_summary(self, analyzer):
        """比較サマリー作成テスト"""
        
        # テスト用比較結果
        comparison_results = {
            'SYMBOL1': {
                'summary': {
                    'overall_score': 85,
                    'recommendation': '買い推奨',
                    'key_strengths': ['高成長性'],
                    'key_concerns': []
                },
                'fundamental_analysis': {
                    'health_score': HealthScoreResult(
                        symbol="SYMBOL1",
                        total_score=90,
                        score_breakdown={},
                        health_level=HealthScore.EXCELLENT,
                        recommendations=[]
                    ),
                    'growth_trend': GrowthTrend(
                        symbol="SYMBOL1",
                        revenue_trend=[],
                        profit_trend=[],
                        years=[],
                        revenue_cagr=0.15
                    ),
                    'metrics': FinancialMetrics(
                        symbol="SYMBOL1",
                        company_name="Company 1",
                        per=12.0
                    )
                }
            },
            'SYMBOL2': {
                'summary': {
                    'overall_score': 70,
                    'recommendation': '保有',
                    'key_strengths': [],
                    'key_concerns': []
                },
                'fundamental_analysis': {
                    'health_score': HealthScoreResult(
                        symbol="SYMBOL2",
                        total_score=75,
                        score_breakdown={},
                        health_level=HealthScore.GOOD,
                        recommendations=[]
                    ),
                    'growth_trend': None,
                    'metrics': None
                }
            }
        }
        
        # テスト実行
        summary = analyzer._create_comparison_summary(comparison_results)
        
        # 検証
        assert len(summary['ranking']) == 2
        assert summary['ranking'][0]['symbol'] == 'SYMBOL1'  # 高スコアが1位
        assert summary['ranking'][1]['symbol'] == 'SYMBOL2'
        
        # カテゴリ別ベストの確認
        assert summary['best_quality'] == 'SYMBOL1'  # 健全性スコア90
        assert summary['best_growth'] == 'SYMBOL1'   # 成長率15%
        assert summary['best_value'] == 'SYMBOL1'    # PER12倍
        
        # 推奨事項があることを確認
        assert len(summary['recommendations']) > 0
    
    def test_create_comparison_summary_empty(self, analyzer):
        """空の比較サマリー作成テスト"""
        
        comparison_results = {}
        
        # テスト実行
        summary = analyzer._create_comparison_summary(comparison_results)
        
        # 検証
        assert summary['ranking'] == []
        assert summary['best_value'] is None
        assert summary['best_growth'] is None
        assert summary['best_quality'] is None


class TestIntegratedAnalyzerErrorHandling:
    """IntegratedAnalyzerのエラーハンドリングのテスト"""
    
    @pytest.fixture
    def analyzer(self):
        """アナライザーのフィクスチャ"""
        return IntegratedAnalyzer()
    
    def test_perform_fundamental_analysis_partial_errors(self, analyzer):
        """ファンダメンタル分析の部分的エラーテスト"""
        
        with patch.object(analyzer.fundamental_analyzer, 'get_financial_metrics') as mock_metrics, \
             patch.object(analyzer.fundamental_analyzer, 'analyze_growth_trend') as mock_growth, \
             patch.object(analyzer.fundamental_analyzer, 'calculate_health_score') as mock_health:
            
            # 一部のメソッドでエラーを発生させる
            mock_metrics.return_value = Mock()
            mock_growth.side_effect = Exception("Growth analysis error")
            mock_health.return_value = Mock()
            
            # テスト実行
            result = analyzer._perform_fundamental_analysis("TEST", False, None)
            
            # 検証
            assert result['status'] == 'error'
            assert 'Growth analysis error' in result['error_message']
            assert result['metrics'] is None
            assert result['growth_trend'] is None
    
    def test_perform_basic_technical_analysis_calculation_error(self, analyzer):
        """テクニカル分析の計算エラーテスト"""
        
        # エラーを引き起こすデータ（不正な値）
        error_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=30),
            'close': [None] * 30  # Noneで埋められたデータ
        })
        
        with patch.object(analyzer.data_collector, 'get_stock_data') as mock_data:
            mock_data.return_value = error_data
            
            # テスト実行
            result = analyzer._perform_basic_technical_analysis("TEST")
            
            # 検証（エラー時はデフォルト値のTechnicalAnalysisDataを返す）
            assert result is not None
            assert result.trend == "不明"
            assert result.momentum == "普通"
            assert result.signal == "中立"
    
    def test_generate_investment_story_none_inputs(self, analyzer):
        """投資ストーリー生成でNone入力のテスト"""
        
        # Noneのファンダメンタル結果
        fundamental_results = {
            'status': 'error',
            'metrics': None,
            'growth_trend': None,
            'health_score': None
        }
        
        with patch.object(analyzer.story_generator, 'generate_comprehensive_report') as mock_report:
            # ストーリー生成でエラーを起こす
            mock_report.side_effect = Exception("Story generation error")
            
            # テスト実行
            result = analyzer._generate_investment_story("TEST", fundamental_results, None)
            
            # 検証（エラー時はNoneを返す）
            assert result is None
    
    def test_create_analysis_summary_missing_data(self, analyzer):
        """データ欠損時の分析サマリー作成テスト"""
        
        # 不完全なファンダメンタルデータ
        incomplete_fundamental = {
            'status': 'error',
            'health_score': None,
            'growth_trend': None,
            'metrics': None
        }
        
        # テスト実行
        summary = analyzer._create_analysis_summary(
            "TEST", incomplete_fundamental, None, None
        )
        
        # 検証
        assert summary['overall_score'] < 50  # 低スコア
        assert summary['recommendation'] in ["データ不足により判断不可", "売り検討", "保有・様子見"]
        # データが不完全でもサマリーが作成されることを確認
        assert 'key_concerns' in summary
    
    @patch('src.technical_analysis.integrated_analysis.IntegratedAnalyzer.generate_complete_analysis')
    def test_generate_comparison_report_mixed_results(self, mock_analysis, analyzer):
        """比較レポート生成で一部エラーのテスト"""
        
        # 一部成功、一部エラーの結果
        mock_analysis.side_effect = [
            {
                'symbol': 'SYMBOL1',
                'summary': {'overall_score': 80, 'recommendation': '買い推奨'}
            },
            {
                'symbol': 'SYMBOL2',
                'status': 'error',
                'error_message': 'Analysis failed'
            }
        ]
        
        # テスト実行
        result = analyzer.generate_comparison_report(['SYMBOL1', 'SYMBOL2'])
        
        # 検証
        assert result['comparison_type'] == 'multi_symbol'
        assert len(result['individual_analyses']) == 2
        assert result['individual_analyses']['SYMBOL2']['status'] == 'error'


class TestIntegratedAnalyzerEdgeCases:
    """IntegratedAnalyzerのエッジケースのテスト"""
    
    @pytest.fixture
    def analyzer(self):
        """アナライザーのフィクスチャ"""
        return IntegratedAnalyzer()
    
    def test_perform_basic_technical_analysis_insufficient_data(self, analyzer):
        """データ不足時のテクニカル分析テスト"""
        
        # 20日未満のデータ（high、lowカラムも含む）
        short_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=10),
            'close': [100 + i for i in range(10)],
            'high': [105 + i for i in range(10)],
            'low': [95 + i for i in range(10)]
        })
        
        with patch.object(analyzer.data_collector, 'get_stock_data') as mock_data:
            mock_data.return_value = short_data
            
            # テスト実行
            result = analyzer._perform_basic_technical_analysis("TEST")
            
            # 検証
            assert result is not None
            assert result.trend == "横ばい"  # データ不足時は横ばい
    
    def test_create_analysis_summary_extreme_values(self, analyzer):
        """極端な値での分析サマリー作成テスト"""
        
        # 非常に高いスコアのファンダメンタル結果
        extreme_fundamental = {
            'status': 'success',
            'health_score': HealthScoreResult(
                symbol="TEST",
                total_score=100.0,
                score_breakdown={},
                health_level=HealthScore.EXCELLENT,
                recommendations=[]
            ),
            'growth_trend': GrowthTrend(
                symbol="TEST",
                revenue_trend=[],
                profit_trend=[],
                years=[],
                revenue_cagr=0.50  # 50%成長
            )
        }
        
        technical_data = TechnicalAnalysisData(
            trend="上昇", momentum="強い", signal="買い"
        )
        
        # テスト実行
        summary = analyzer._create_analysis_summary(
            "TEST", extreme_fundamental, technical_data, None
        )
        
        # 検証
        assert summary['overall_score'] <= 100  # 100を超えない
        assert summary['recommendation'] == "買い推奨"
    
    def test_create_comparison_summary_single_symbol(self, analyzer):
        """単一銘柄での比較サマリー作成テスト"""
        
        comparison_results = {
            'SINGLE': {
                'summary': {
                    'overall_score': 75,
                    'recommendation': '保有'
                },
                'fundamental_analysis': {
                    'health_score': HealthScoreResult(
                        symbol="SINGLE",
                        total_score=85,  # 80以上に変更
                        score_breakdown={},
                        health_level=HealthScore.EXCELLENT,
                        recommendations=[]
                    )
                }
            }
        }
        
        # テスト実行
        summary = analyzer._create_comparison_summary(comparison_results)
        
        # 検証
        assert len(summary['ranking']) == 1
        assert summary['best_quality'] == 'SINGLE'
        assert len(summary['recommendations']) >= 1
        # 推奨事項にSINGLEが含まれることを確認
        recommendations_text = ' '.join(summary['recommendations'])
        assert 'SINGLE' in recommendations_text
    
    def test_create_comparison_summary_no_fundamental_data(self, analyzer):
        """ファンダメンタルデータなしでの比較サマリー作成テスト"""
        
        comparison_results = {
            'NO_FUND': {
                'summary': {
                    'overall_score': 50,
                    'recommendation': '様子見'
                },
                'fundamental_analysis': {
                    'health_score': None,
                    'growth_trend': None,
                    'metrics': None
                }
            }
        }
        
        # テスト実行
        summary = analyzer._create_comparison_summary(comparison_results)
        
        # 検証
        assert summary['best_quality'] is None
        assert summary['best_growth'] is None
        assert summary['best_value'] is None


if __name__ == "__main__":
    pytest.main([__file__])