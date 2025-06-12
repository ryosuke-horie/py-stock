"""
ファンダメンタルズ分析モジュールのユニットテスト
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.technical_analysis.fundamental_analysis import (
    FundamentalAnalyzer,
    FinancialMetrics,
    GrowthTrend,
    ComparisonResult,
    HealthScoreResult,
    HealthScore
)


class TestFundamentalAnalyzer:
    """FundamentalAnalyzerクラスのテスト"""
    
    @pytest.fixture
    def analyzer(self):
        """アナライザーのフィクスチャ"""
        return FundamentalAnalyzer()
    
    @pytest.fixture
    def mock_ticker_info(self):
        """模擬銘柄情報"""
        return {
            'longName': 'Test Company Inc.',
            'trailingPE': 15.5,
            'priceToBook': 1.2,
            'returnOnEquity': 0.18,
            'returnOnAssets': 0.12,
            'dividendYield': 0.025,
            'currentPrice': 100.0,
            'marketCap': 1000000000
        }
    
    @pytest.fixture
    def mock_balance_sheet(self):
        """模擬貸借対照表データ"""
        data = {
            'Current Assets': 500000000,
            'Current Liabilities': 200000000,
            'Total Equity Gross Minority Interest': 800000000,
            'Total Assets': 1200000000,
            'Total Debt': 300000000
        }
        return pd.DataFrame([data]).T
    
    @pytest.fixture
    def mock_financials(self):
        """模擬損益計算書データ"""
        dates = [
            datetime(2024, 12, 31),
            datetime(2023, 12, 31),
            datetime(2022, 12, 31),
            datetime(2021, 12, 31),
            datetime(2020, 12, 31)
        ]
        
        data = {
            dates[0]: [1000000000, 100000000],
            dates[1]: [900000000, 85000000],
            dates[2]: [800000000, 70000000],
            dates[3]: [750000000, 60000000],
            dates[4]: [700000000, 50000000]
        }
        
        df = pd.DataFrame(data, index=['Total Revenue', 'Net Income'])
        return df
    
    def test_init(self, analyzer):
        """初期化テスト"""
        assert analyzer._cache == {}
        assert analyzer._cache_expire_hours == 24
    
    @patch('src.technical_analysis.fundamental_analysis.yf.Ticker')
    def test_get_ticker_info_success(self, mock_ticker, analyzer, mock_ticker_info):
        """銘柄情報取得成功テスト"""
        # モックの設定
        mock_instance = Mock()
        mock_instance.info = mock_ticker_info
        mock_ticker.return_value = mock_instance
        
        # テスト実行
        result = analyzer._get_ticker_info('TEST')
        
        # 検証
        assert result == mock_ticker_info
        mock_ticker.assert_called_once_with('TEST')
    
    @patch('src.technical_analysis.fundamental_analysis.yf.Ticker')
    def test_get_ticker_info_cache(self, mock_ticker, analyzer, mock_ticker_info):
        """銘柄情報キャッシュテスト"""
        # モックの設定
        mock_instance = Mock()
        mock_instance.info = mock_ticker_info
        mock_ticker.return_value = mock_instance
        
        # 初回取得
        result1 = analyzer._get_ticker_info('TEST')
        
        # 2回目取得（キャッシュから）
        result2 = analyzer._get_ticker_info('TEST')
        
        # 検証
        assert result1 == result2 == mock_ticker_info
        mock_ticker.assert_called_once()  # 1回だけ呼ばれる
    
    @patch('src.technical_analysis.fundamental_analysis.yf.Ticker')
    def test_get_financial_data_success(self, mock_ticker, analyzer, mock_financials, mock_balance_sheet):
        """財務データ取得成功テスト"""
        # モックの設定
        mock_instance = Mock()
        mock_instance.financials = mock_financials
        mock_instance.balance_sheet = mock_balance_sheet
        mock_ticker.return_value = mock_instance
        
        # テスト実行
        financials, balance_sheet = analyzer._get_financial_data('TEST')
        
        # 検証
        assert not financials.empty
        assert not balance_sheet.empty
        mock_ticker.assert_called_once_with('TEST')
    
    @patch('src.technical_analysis.fundamental_analysis.yf.Ticker')
    def test_get_financial_metrics_success(self, mock_ticker, analyzer, mock_ticker_info, mock_balance_sheet, mock_financials):
        """財務指標取得成功テスト"""
        # モックの設定
        mock_instance = Mock()
        mock_instance.info = mock_ticker_info
        mock_instance.financials = mock_financials
        mock_instance.balance_sheet = mock_balance_sheet
        mock_ticker.return_value = mock_instance
        
        # テスト実行
        result = analyzer.get_financial_metrics('TEST')
        
        # 検証
        assert isinstance(result, FinancialMetrics)
        assert result.symbol == 'TEST'
        assert result.company_name == 'Test Company Inc.'
        assert result.per == 15.5
        assert result.pbr == 1.2
        assert result.roe == 0.18
        assert result.dividend_yield == 0.025
        assert result.price == 100.0
        assert result.market_cap == 1000000000
        
        # 計算された指標の検証
        assert result.current_ratio == 2.5  # 500M / 200M
        assert result.equity_ratio == pytest.approx(0.6667, rel=1e-3)  # 800M / 1200M
        assert result.debt_ratio == 0.25  # 300M / 1200M
    
    def test_calculate_cagr(self, analyzer):
        """CAGR計算テスト"""
        # 正常ケース
        values = [100, 110, 121, 133.1]
        cagr = analyzer._calculate_cagr(values)
        assert cagr == pytest.approx(0.1, rel=1e-2)  # 10%成長
        
        # データ不足ケース
        values = [100]
        cagr = analyzer._calculate_cagr(values)
        assert cagr is None
        
        # NaN含有ケース（実際のテストケースを修正）
        values = [100, np.nan, 121, 133.1]
        cagr = analyzer._calculate_cagr(values)
        # NaNを除去すると [100, 121, 133.1] となり、実際のCAGRを計算
        expected_cagr = ((133.1 / 100) ** (1 / 2)) - 1
        assert cagr == pytest.approx(expected_cagr, rel=1e-2)
        
        # 負の値ケース（負の値は除外されるため、[110, 121]で計算される）
        values = [-100, 110, 121]
        cagr = analyzer._calculate_cagr(values)
        # 負の値を除外すると [110, 121] となり、CAGR = (121/110)^(1/1) - 1 = 0.1
        assert cagr == pytest.approx(0.1, rel=1e-2)
    
    @patch('src.technical_analysis.fundamental_analysis.yf.Ticker')
    def test_analyze_growth_trend(self, mock_ticker, analyzer, mock_financials):
        """成長トレンド分析テスト"""
        # モックの設定
        mock_instance = Mock()
        mock_instance.financials = mock_financials
        mock_instance.balance_sheet = pd.DataFrame()
        mock_ticker.return_value = mock_instance
        
        # テスト実行
        result = analyzer.analyze_growth_trend('TEST')
        
        # 検証
        assert isinstance(result, GrowthTrend)
        assert result.symbol == 'TEST'
        assert len(result.revenue_trend) == 5
        assert len(result.profit_trend) == 5
        assert result.revenue_cagr is not None
        assert result.profit_cagr is not None
        assert result.volatility is not None
    
    def test_calculate_health_score_excellent(self, analyzer):
        """財務健全性スコア計算テスト（優秀）"""
        # 理想的な財務指標
        metrics = FinancialMetrics(
            symbol='TEST',
            company_name='Test Company',
            per=15.0,  # 理想範囲
            pbr=1.5,   # 理想範囲
            roe=0.20,  # 20% (優秀)
            dividend_yield=0.03,  # 3% (理想範囲)
            current_ratio=2.5,    # 250% (優秀)
            equity_ratio=0.60     # 60% (優秀)
        )
        
        with patch.object(analyzer, 'get_financial_metrics', return_value=metrics):
            result = analyzer.calculate_health_score('TEST')
        
        # 検証
        assert isinstance(result, HealthScoreResult)
        assert result.symbol == 'TEST'
        assert result.total_score >= 90
        assert result.health_level == HealthScore.EXCELLENT
        assert len(result.recommendations) == 0  # 推奨事項なし
    
    def test_calculate_health_score_poor(self, analyzer):
        """財務健全性スコア計算テスト（注意）"""
        # 問題のある財務指標
        metrics = FinancialMetrics(
            symbol='TEST',
            company_name='Test Company',
            per=50.0,   # 高すぎる
            pbr=5.0,    # 高すぎる
            roe=0.03,   # 3% (低い)
            dividend_yield=0.001,  # 0.1% (低い)
            current_ratio=0.8,     # 80% (低い)
            equity_ratio=0.15      # 15% (低い)
        )
        
        with patch.object(analyzer, 'get_financial_metrics', return_value=metrics):
            result = analyzer.calculate_health_score('TEST')
        
        # 検証
        assert isinstance(result, HealthScoreResult)
        assert result.symbol == 'TEST'
        assert result.total_score < 60
        assert result.health_level in [HealthScore.POOR, HealthScore.CRITICAL]
        assert len(result.recommendations) > 0  # 推奨事項あり
    
    def test_compare_with_peers(self, analyzer):
        """同業他社比較テスト"""
        # モック財務指標データ
        metrics_data = {
            'TARGET': FinancialMetrics(
                symbol='TARGET', company_name='Target Co',
                per=15.0, pbr=1.2, roe=0.18, dividend_yield=0.025
            ),
            'PEER1': FinancialMetrics(
                symbol='PEER1', company_name='Peer 1',
                per=12.0, pbr=1.5, roe=0.15, dividend_yield=0.03
            ),
            'PEER2': FinancialMetrics(
                symbol='PEER2', company_name='Peer 2',
                per=18.0, pbr=1.0, roe=0.20, dividend_yield=0.02
            )
        }
        
        def mock_get_metrics(symbol):
            return metrics_data.get(symbol)
        
        with patch.object(analyzer, 'get_financial_metrics', side_effect=mock_get_metrics):
            result = analyzer.compare_with_peers('TARGET', ['PEER1', 'PEER2'])
        
        # 検証
        assert isinstance(result, ComparisonResult)
        assert result.target_symbol == 'TARGET'
        assert result.comparison_symbols == ['PEER1', 'PEER2']
        assert 'per' in result.metrics_comparison
        assert 'per' in result.rank
        assert 'per' in result.industry_average
    
    def test_get_comprehensive_analysis(self, analyzer):
        """総合分析テスト"""
        # モックデータの設定
        mock_metrics = FinancialMetrics(symbol='TEST', company_name='Test Co')
        mock_growth = GrowthTrend(symbol='TEST', revenue_trend=[], profit_trend=[], years=[])
        mock_health = HealthScoreResult(
            symbol='TEST', total_score=80.0, score_breakdown={},
            health_level=HealthScore.GOOD, recommendations=[]
        )
        mock_comparison = ComparisonResult(
            target_symbol='TEST', comparison_symbols=[],
            metrics_comparison={}, rank={}, industry_average={}
        )
        
        with patch.object(analyzer, 'get_financial_metrics', return_value=mock_metrics), \
             patch.object(analyzer, 'analyze_growth_trend', return_value=mock_growth), \
             patch.object(analyzer, 'calculate_health_score', return_value=mock_health), \
             patch.object(analyzer, 'compare_with_peers', return_value=mock_comparison):
            
            result = analyzer.get_comprehensive_analysis('TEST', ['PEER1'])
        
        # 検証
        assert 'metrics' in result
        assert 'growth_trend' in result
        assert 'health_score' in result
        assert 'peer_comparison' in result
        assert result['metrics'] == mock_metrics
        assert result['growth_trend'] == mock_growth
        assert result['health_score'] == mock_health
        assert result['peer_comparison'] == mock_comparison


class TestDataClasses:
    """データクラスのテスト"""
    
    def test_financial_metrics_creation(self):
        """FinancialMetricsデータクラステスト"""
        metrics = FinancialMetrics(
            symbol='TEST',
            company_name='Test Company',
            per=15.0,
            pbr=1.2,
            roe=0.18
        )
        
        assert metrics.symbol == 'TEST'
        assert metrics.company_name == 'Test Company'
        assert metrics.per == 15.0
        assert metrics.pbr == 1.2
        assert metrics.roe == 0.18
    
    def test_growth_trend_creation(self):
        """GrowthTrendデータクラステスト"""
        trend = GrowthTrend(
            symbol='TEST',
            revenue_trend=[100, 110, 121],
            profit_trend=[10, 12, 14],
            years=['2022', '2023', '2024'],
            revenue_cagr=0.1,
            profit_cagr=0.18
        )
        
        assert trend.symbol == 'TEST'
        assert trend.revenue_trend == [100, 110, 121]
        assert trend.profit_trend == [10, 12, 14]
        assert trend.years == ['2022', '2023', '2024']
        assert trend.revenue_cagr == 0.1
        assert trend.profit_cagr == 0.18
    
    def test_health_score_enum(self):
        """HealthScoreEnumテスト"""
        assert HealthScore.EXCELLENT.value == "優秀"
        assert HealthScore.GOOD.value == "良好"
        assert HealthScore.AVERAGE.value == "普通"
        assert HealthScore.POOR.value == "注意"
        assert HealthScore.CRITICAL.value == "危険"


class TestFundamentalAnalyzerErrorHandling:
    """エラーハンドリングと例外処理のテスト"""
    
    @pytest.fixture
    def analyzer(self):
        return FundamentalAnalyzer()
    
    @patch('src.technical_analysis.fundamental_analysis.yf.Ticker')
    def test_get_ticker_info_exception(self, mock_ticker, analyzer):
        """銘柄情報取得時の例外処理テスト"""
        # yfinanceで例外が発生するケース
        mock_ticker.side_effect = Exception("Network error")
        
        result = analyzer._get_ticker_info('INVALID')
        
        # 例外時は空辞書を返す
        assert result == {}
    
    @patch('src.technical_analysis.fundamental_analysis.yf.Ticker')
    def test_get_financial_data_exception(self, mock_ticker, analyzer):
        """財務データ取得時の例外処理テスト"""
        # yfinanceで例外が発生するケース
        mock_ticker.side_effect = Exception("API error")
        
        financials, balance_sheet = analyzer._get_financial_data('INVALID')
        
        # 例外時は空のDataFrameを返す
        assert financials.empty
        assert balance_sheet.empty
    
    @patch('src.technical_analysis.fundamental_analysis.yf.Ticker')
    def test_get_ticker_info_cache_hit(self, mock_ticker, analyzer):
        """キャッシュヒット時のテスト"""
        # 事前にキャッシュに設定
        cache_key = "info_TEST"
        test_data = {"test": "data"}
        analyzer._cache[cache_key] = (test_data, datetime.now())
        
        result = analyzer._get_ticker_info('TEST')
        
        # キャッシュから取得されることを確認
        assert result == test_data
        # yfinanceが呼ばれないことを確認
        mock_ticker.assert_not_called()
    
    @patch('src.technical_analysis.fundamental_analysis.yf.Ticker')
    def test_get_financial_data_cache_hit(self, mock_ticker, analyzer):
        """財務データキャッシュヒット時のテスト"""
        # 事前にキャッシュに設定
        cache_key = "financials_TEST"
        test_financials = pd.DataFrame({"test": [1, 2, 3]})
        test_balance = pd.DataFrame({"balance": [4, 5, 6]})
        analyzer._cache[cache_key] = ((test_financials, test_balance), datetime.now())
        
        financials, balance_sheet = analyzer._get_financial_data('TEST')
        
        # キャッシュから取得されることを確認
        pd.testing.assert_frame_equal(financials, test_financials)
        pd.testing.assert_frame_equal(balance_sheet, test_balance)
        # yfinanceが呼ばれないことを確認
        mock_ticker.assert_not_called()
    
    @patch('src.technical_analysis.fundamental_analysis.yf.Ticker')
    def test_get_financial_metrics_no_info(self, mock_ticker, analyzer):
        """銘柄情報が取得できない場合のテスト"""
        # 空の銘柄情報を返すモック
        mock_instance = Mock()
        mock_instance.info = {}
        mock_ticker.return_value = mock_instance
        
        result = analyzer.get_financial_metrics('EMPTY')
        
        # 情報がない場合はNoneを返す
        assert result is None
    
    @patch('src.technical_analysis.fundamental_analysis.yf.Ticker')
    def test_get_financial_metrics_missing_data(self, mock_ticker, analyzer):
        """一部のデータが欠損している場合のテスト"""
        # 一部のフィールドのみ含む銘柄情報
        mock_instance = Mock()
        mock_instance.info = {
            'longName': 'Test Company',
            'trailingPE': 15.0,
            # その他のフィールドは欠損
        }
        mock_ticker.return_value = mock_instance
        
        result = analyzer.get_financial_metrics('PARTIAL')
        
        # 取得できたフィールドのみ設定される
        assert result is not None
        assert result.company_name == 'Test Company'
        assert result.per == 15.0
        assert result.pbr is None  # 欠損フィールドはNone
        assert result.roe is None
    
    @patch('src.technical_analysis.fundamental_analysis.yf.Ticker')
    def test_analyze_growth_trend_empty_data(self, mock_ticker, analyzer):
        """空の財務データでの成長トレンド分析テスト"""
        # 空のDataFrameを返すモック
        mock_instance = Mock()
        mock_instance.financials = pd.DataFrame()
        mock_instance.balance_sheet = pd.DataFrame()
        mock_ticker.return_value = mock_instance
        
        result = analyzer.analyze_growth_trend('EMPTY')
        
        # 空データの場合はNoneを返す
        assert result is None
    
    @patch('src.technical_analysis.fundamental_analysis.yf.Ticker')
    def test_analyze_growth_trend_insufficient_data(self, mock_ticker, analyzer):
        """データ不足時の成長トレンド分析テスト"""
        # 1年分のデータのみ
        dates = [datetime(2024, 12, 31)]
        data = {dates[0]: [1000000000, 100000000]}
        insufficient_data = pd.DataFrame(data, index=['Total Revenue', 'Net Income'])
        
        mock_instance = Mock()
        mock_instance.financials = insufficient_data
        mock_instance.balance_sheet = pd.DataFrame()
        mock_ticker.return_value = mock_instance
        
        result = analyzer.analyze_growth_trend('INSUFFICIENT')
        
        # データ不足の場合はNoneが返される（今回の改善で仕様変更）
        assert result is None


class TestFundamentalAnalyzerEdgeCases:
    """エッジケースと境界値テスト"""
    
    @pytest.fixture
    def analyzer(self):
        return FundamentalAnalyzer()
    
    @patch('src.technical_analysis.fundamental_analysis.yf.Ticker')
    def test_get_financial_metrics_zero_values(self, mock_ticker, analyzer):
        """ゼロ値を含む財務指標のテスト"""
        mock_instance = Mock()
        mock_instance.info = {
            'longName': 'Zero Company',
            'trailingPE': 0,  # ゼロPER
            'priceToBook': 0,  # ゼロPBR
            'returnOnEquity': 0,  # ゼロROE
            'dividendYield': 0,  # 配当なし
            'currentPrice': 0.01,  # 極小株価
            'marketCap': 1000
        }
        mock_ticker.return_value = mock_instance
        
        result = analyzer.get_financial_metrics('ZERO')
        
        assert result is not None
        assert result.per == 0
        assert result.pbr == 0
        assert result.roe == 0
        assert result.dividend_yield == 0
        assert result.price == 0.01
    
    @patch('src.technical_analysis.fundamental_analysis.yf.Ticker')
    def test_get_financial_metrics_negative_values(self, mock_ticker, analyzer):
        """負の値を含む財務指標のテスト"""
        mock_instance = Mock()
        mock_instance.info = {
            'longName': 'Negative Company',
            'trailingPE': -15.0,  # 負のPER（赤字企業）
            'returnOnEquity': -0.05,  # 負のROE
            'returnOnAssets': -0.03,  # 負のROA
            'currentPrice': 50.0,
            'marketCap': 500000000
        }
        mock_ticker.return_value = mock_instance
        
        result = analyzer.get_financial_metrics('NEGATIVE')
        
        assert result is not None
        assert result.per == -15.0
        assert result.roe == -0.05
        assert result.roa == -0.03
    
    @patch('src.technical_analysis.fundamental_analysis.yf.Ticker')
    def test_get_financial_metrics_extreme_values(self, mock_ticker, analyzer):
        """極端な値を含む財務指標のテスト"""
        mock_instance = Mock()
        mock_instance.info = {
            'longName': 'Extreme Company',
            'trailingPE': 1000.0,  # 極端に高いPER
            'priceToBook': 100.0,  # 極端に高いPBR
            'returnOnEquity': 2.0,  # 200%ROE
            'dividendYield': 0.5,  # 50%配当利回り
            'currentPrice': 10000.0,  # 高株価
            'marketCap': 1000000000000  # 1兆円企業
        }
        mock_ticker.return_value = mock_instance
        
        result = analyzer.get_financial_metrics('EXTREME')
        
        assert result is not None
        assert result.per == 1000.0
        assert result.pbr == 100.0
        assert result.roe == 2.0
        assert result.dividend_yield == 0.5
        assert result.market_cap == 1000000000000
    
    @patch('src.technical_analysis.fundamental_analysis.yf.Ticker')
    def test_analyze_growth_trend_zero_revenue(self, mock_ticker, analyzer):
        """売上ゼロ期間を含む成長トレンド分析テスト"""
        dates = [
            datetime(2024, 12, 31),
            datetime(2023, 12, 31),
            datetime(2022, 12, 31)
        ]
        
        # 2023年の売上がゼロ
        data = {
            dates[0]: [1000000000, 100000000],
            dates[1]: [0, -50000000],  # 売上ゼロ、赤字
            dates[2]: [800000000, 70000000]
        }
        
        financials = pd.DataFrame(data, index=['Total Revenue', 'Net Income'])
        
        mock_instance = Mock()
        mock_instance.financials = financials
        mock_instance.balance_sheet = pd.DataFrame()
        mock_ticker.return_value = mock_instance
        
        result = analyzer.analyze_growth_trend('ZERO_REVENUE')
        
        # ゼロ値でも適切に処理されることを確認
        assert result is not None
        assert isinstance(result.revenue_cagr, (float, type(None)))
        assert isinstance(result.profit_cagr, (float, type(None)))
    
    @patch('src.technical_analysis.fundamental_analysis.yf.Ticker')
    def test_analyze_growth_trend_mixed_positive_negative(self, mock_ticker, analyzer):
        """正負混在の財務データテスト"""
        dates = [
            datetime(2024, 12, 31),
            datetime(2023, 12, 31),
            datetime(2022, 12, 31)
        ]
        
        # 利益が正負混在
        data = {
            dates[0]: [1000000000, 100000000],   # 黒字
            dates[1]: [900000000, -50000000],    # 赤字
            dates[2]: [800000000, 80000000]      # 黒字
        }
        
        financials = pd.DataFrame(data, index=['Total Revenue', 'Net Income'])
        
        mock_instance = Mock()
        mock_instance.financials = financials
        mock_instance.balance_sheet = pd.DataFrame()
        mock_ticker.return_value = mock_instance
        
        result = analyzer.analyze_growth_trend('MIXED_DATA')
        
        # 正負混在でも適切に処理されることを確認
        assert result is not None
        assert isinstance(result.revenue_cagr, (float, type(None)))
        assert isinstance(result.profit_cagr, (float, type(None)))


class TestFundamentalAnalyzerEnhancedErrorHandling:
    """今回の改善内容（Issue #97対応）のテスト"""
    
    @pytest.fixture
    def analyzer(self):
        return FundamentalAnalyzer()
    
    @patch('src.technical_analysis.fundamental_analysis.yf.Ticker')
    @patch('src.technical_analysis.fundamental_analysis.logger')
    def test_analyze_growth_trend_empty_financials_warning_log(self, mock_logger, mock_ticker, analyzer):
        """空の財務諸表データ時の警告ログテスト"""
        # 空のDataFrameを返すモック
        mock_instance = Mock()
        mock_instance.financials = pd.DataFrame()
        mock_instance.balance_sheet = pd.DataFrame()
        mock_ticker.return_value = mock_instance
        
        result = analyzer.analyze_growth_trend('EMPTY_TEST')
        
        # 結果確認
        assert result is None
        
        # 警告ログが出力されることを確認
        mock_logger.warning.assert_called_with("財務諸表データが空です: EMPTY_TEST")
    
    @patch('src.technical_analysis.fundamental_analysis.yf.Ticker')
    @patch('src.technical_analysis.fundamental_analysis.logger')
    def test_analyze_growth_trend_alternative_revenue_search(self, mock_logger, mock_ticker, analyzer):
        """代替売上データ検索のテスト"""
        dates = [
            datetime(2024, 12, 31),
            datetime(2023, 12, 31),
            datetime(2022, 12, 31)
        ]
        
        # "Total Revenue"がない代わりに"Revenue"がある財務データ
        data = {
            dates[0]: [1000000000, 100000000],
            dates[1]: [900000000, 85000000],
            dates[2]: [800000000, 70000000]
        }
        
        # "Total Revenue"ではなく"Revenue"と"Net Income"を使用
        financials = pd.DataFrame(data, index=['Revenue', 'Net Income'])
        
        mock_instance = Mock()
        mock_instance.financials = financials
        mock_instance.balance_sheet = pd.DataFrame()
        mock_ticker.return_value = mock_instance
        
        result = analyzer.analyze_growth_trend('ALT_REVENUE_TEST')
        
        # 結果確認
        assert result is not None
        assert len(result.revenue_trend) == 3
        assert result.revenue_trend[-1] == 1000000000  # 2024年のRevenue（最新）
        
        # 代替項目発見のログが出力されることを確認
        mock_logger.info.assert_any_call("売上データを代替項目で発見: Revenue")
    
    @patch('src.technical_analysis.fundamental_analysis.yf.Ticker')
    @patch('src.technical_analysis.fundamental_analysis.logger')
    def test_analyze_growth_trend_alternative_profit_search(self, mock_logger, mock_ticker, analyzer):
        """代替利益データ検索のテスト"""
        dates = [
            datetime(2024, 12, 31),
            datetime(2023, 12, 31),
            datetime(2022, 12, 31)
        ]
        
        # "Net Income"がない代わりに"Profit"がある財務データ
        data = {
            dates[0]: [1000000000, 100000000],
            dates[1]: [900000000, 85000000],
            dates[2]: [800000000, 70000000]
        }
        
        # "Total Revenue"と"Profit"を使用
        financials = pd.DataFrame(data, index=['Total Revenue', 'Profit'])
        
        mock_instance = Mock()
        mock_instance.financials = financials
        mock_instance.balance_sheet = pd.DataFrame()
        mock_ticker.return_value = mock_instance
        
        result = analyzer.analyze_growth_trend('ALT_PROFIT_TEST')
        
        # 結果確認
        assert result is not None
        assert len(result.profit_trend) == 3
        assert result.profit_trend[-1] == 100000000  # 2024年のProfit（最新）
        
        # 代替項目発見のログが出力されることを確認
        mock_logger.info.assert_any_call("利益データを代替項目で発見: Profit")
    
    @patch('src.technical_analysis.fundamental_analysis.yf.Ticker')
    @patch('src.technical_analysis.fundamental_analysis.logger')
    def test_analyze_growth_trend_missing_data_warning(self, mock_logger, mock_ticker, analyzer):
        """売上・利益データが見つからない場合の警告ログテスト"""
        dates = [
            datetime(2024, 12, 31),
            datetime(2023, 12, 31)
        ]
        
        # 売上・利益データが存在しない財務データ
        data = {
            dates[0]: [1000000000, 50000000],
            dates[1]: [900000000, 45000000]
        }
        
        # 関係ない項目のみ
        financials = pd.DataFrame(data, index=['Other Income', 'Other Expense'])
        
        mock_instance = Mock()
        mock_instance.financials = financials
        mock_instance.balance_sheet = pd.DataFrame()
        mock_ticker.return_value = mock_instance
        
        result = analyzer.analyze_growth_trend('MISSING_DATA_TEST')
        
        # 結果確認（データ不足でNoneが返される）
        assert result is None
        
        # 売上・利益データが見つからない警告ログが出力されることを確認
        mock_logger.warning.assert_any_call("売上データが見つかりません: MISSING_DATA_TEST, 2024")
        mock_logger.warning.assert_any_call("利益データが見つかりません: MISSING_DATA_TEST, 2024")
        mock_logger.warning.assert_any_call("成長トレンド分析に十分なデータがありません: MISSING_DATA_TEST")
    
    @patch('src.technical_analysis.fundamental_analysis.yf.Ticker')
    @patch('src.technical_analysis.fundamental_analysis.logger')
    def test_analyze_growth_trend_insufficient_valid_data(self, mock_logger, mock_ticker, analyzer):
        """有効データ不足時の処理テスト"""
        dates = [
            datetime(2024, 12, 31),
            datetime(2023, 12, 31),
            datetime(2022, 12, 31)
        ]
        
        # 売上データが1件、利益データが1件のみ有効
        data = {
            dates[0]: [1000000000, np.nan],  # 売上のみ
            dates[1]: [np.nan, 85000000],    # 利益のみ
            dates[2]: [np.nan, np.nan]       # どちらもなし
        }
        
        financials = pd.DataFrame(data, index=['Total Revenue', 'Net Income'])
        
        mock_instance = Mock()
        mock_instance.financials = financials
        mock_instance.balance_sheet = pd.DataFrame()
        mock_ticker.return_value = mock_instance
        
        result = analyzer.analyze_growth_trend('INSUFFICIENT_VALID_DATA_TEST')
        
        # 結果確認（有効データが2件未満のためNoneが返される）
        assert result is None
        
        # 有効データ数のログが出力されることを確認
        mock_logger.info.assert_any_call("有効な売上データ数: 1/3")
        mock_logger.info.assert_any_call("有効な利益データ数: 1/3")
        mock_logger.warning.assert_any_call("成長トレンド分析に十分なデータがありません: INSUFFICIENT_VALID_DATA_TEST")
    
    @patch('src.technical_analysis.fundamental_analysis.yf.Ticker')
    @patch('src.technical_analysis.fundamental_analysis.logger')
    def test_analyze_growth_trend_financial_index_logging(self, mock_logger, mock_ticker, analyzer):
        """財務諸表インデックス情報ログテスト"""
        dates = [datetime(2024, 12, 31), datetime(2023, 12, 31)]
        data = {
            dates[0]: [1000000000, 100000000],
            dates[1]: [900000000, 85000000]
        }
        
        financials = pd.DataFrame(data, index=['Total Revenue', 'Net Income'])
        
        mock_instance = Mock()
        mock_instance.financials = financials
        mock_instance.balance_sheet = pd.DataFrame()
        mock_ticker.return_value = mock_instance
        
        result = analyzer.analyze_growth_trend('INDEX_LOG_TEST')
        
        # 結果確認
        assert result is not None
        
        # 財務諸表インデックス情報のログが出力されることを確認
        expected_index_list = ['Total Revenue', 'Net Income']
        mock_logger.info.assert_any_call(f"財務諸表の行インデックス: {expected_index_list}")
    
    @patch('src.technical_analysis.fundamental_analysis.yf.Ticker')
    @patch('src.technical_analysis.fundamental_analysis.logger')
    def test_analyze_growth_trend_sufficient_single_type_data(self, mock_logger, mock_ticker, analyzer):
        """一方のデータのみ十分な場合の処理テスト"""
        dates = [
            datetime(2024, 12, 31),
            datetime(2023, 12, 31),
            datetime(2022, 12, 31)
        ]
        
        # 売上データは十分、利益データは不足
        data = {
            dates[0]: [1000000000, np.nan],
            dates[1]: [900000000, 85000000],
            dates[2]: [800000000, np.nan]
        }
        
        financials = pd.DataFrame(data, index=['Total Revenue', 'Net Income'])
        
        mock_instance = Mock()
        mock_instance.financials = financials
        mock_instance.balance_sheet = pd.DataFrame()
        mock_ticker.return_value = mock_instance
        
        result = analyzer.analyze_growth_trend('SINGLE_TYPE_SUFFICIENT_TEST')
        
        # 結果確認（売上データが十分なので分析結果が返される）
        assert result is not None
        assert len(result.revenue_trend) == 3
        assert result.revenue_cagr is not None
        
        # 有効データ数のログが出力されることを確認
        mock_logger.info.assert_any_call("有効な売上データ数: 3/3")
        mock_logger.info.assert_any_call("有効な利益データ数: 1/3")
    
    @patch('src.technical_analysis.fundamental_analysis.yf.Ticker')
    @patch('src.technical_analysis.fundamental_analysis.logger')
    def test_analyze_growth_trend_case_insensitive_search(self, mock_logger, mock_ticker, analyzer):
        """大文字小文字を区別しない検索のテスト"""
        dates = [datetime(2024, 12, 31), datetime(2023, 12, 31)]
        data = {
            dates[0]: [1000000000, 100000000],
            dates[1]: [900000000, 85000000]
        }
        
        # 小文字の項目名
        financials = pd.DataFrame(data, index=['revenue', 'profit'])
        
        mock_instance = Mock()
        mock_instance.financials = financials
        mock_instance.balance_sheet = pd.DataFrame()
        mock_ticker.return_value = mock_instance
        
        result = analyzer.analyze_growth_trend('CASE_INSENSITIVE_TEST')
        
        # 結果確認
        assert result is not None
        assert len(result.revenue_trend) == 2
        assert len(result.profit_trend) == 2
        
        # 代替項目発見のログが出力されることを確認
        mock_logger.info.assert_any_call("売上データを代替項目で発見: revenue")
        mock_logger.info.assert_any_call("利益データを代替項目で発見: profit")


class TestFundamentalAnalyzerAdvancedFeatures:
    """高度な機能のテスト"""
    
    @pytest.fixture
    def analyzer(self):
        return FundamentalAnalyzer()
    
    @patch('src.technical_analysis.fundamental_analysis.yf.Ticker')
    def test_get_financial_metrics_comprehensive(self, mock_ticker, analyzer):
        """包括的な財務指標取得テスト"""
        # 完全な財務データを模擬
        mock_instance = Mock()
        mock_instance.info = {
            'longName': 'Comprehensive Test Company Inc.',
            'trailingPE': 18.5,
            'priceToBook': 2.1,
            'returnOnEquity': 0.15,
            'returnOnAssets': 0.08,
            'dividendYield': 0.035,
            'currentPrice': 125.50,
            'marketCap': 5000000000,
            'sector': 'Technology',
            'industry': 'Software',
            'country': 'Japan'
        }
        mock_ticker.return_value = mock_instance
        
        result = analyzer.get_financial_metrics('COMPREHENSIVE')
        
        # 全フィールドが正しく設定されることを確認
        assert result is not None
        assert result.symbol == 'COMPREHENSIVE'
        assert result.company_name == 'Comprehensive Test Company Inc.'
        assert result.per == 18.5
        assert result.pbr == 2.1
        assert result.roe == 0.15
        assert result.roa == 0.08
        assert result.dividend_yield == 0.035
        assert result.price == 125.50
        assert result.market_cap == 5000000000
        assert isinstance(result.updated_at, datetime)
    
    def test_cache_expiration_behavior(self, analyzer):
        """キャッシュ有効期限の動作テスト"""
        # 期限切れのキャッシュデータを設定
        cache_key = "info_EXPIRED"
        old_time = datetime.now() - timedelta(hours=25)  # 25時間前（期限切れ）
        test_data = {"expired": "data"}
        analyzer._cache[cache_key] = (test_data, old_time)
        
        # キャッシュ内容確認
        assert cache_key in analyzer._cache
        
        # 期限切れキャッシュは新しいリクエストで更新される
        with patch('src.technical_analysis.fundamental_analysis.yf.Ticker') as mock_ticker:
            mock_instance = Mock()
            mock_instance.info = {"fresh": "data"}
            mock_ticker.return_value = mock_instance
            
            result = analyzer._get_ticker_info('EXPIRED')
            
            # 新しいデータが取得されることを確認
            assert result == {"fresh": "data"}
            mock_ticker.assert_called_once_with('EXPIRED')
    
    def test_multiple_symbols_cache_separation(self, analyzer):
        """複数銘柄のキャッシュ分離テスト"""
        # 複数銘柄のキャッシュを設定
        symbols = ['SYMBOL1', 'SYMBOL2', 'SYMBOL3']
        
        for i, symbol in enumerate(symbols):
            cache_key = f"info_{symbol}"
            test_data = {f"data_{symbol}": i}
            analyzer._cache[cache_key] = (test_data, datetime.now())
        
        # 各銘柄のキャッシュが独立していることを確認
        for i, symbol in enumerate(symbols):
            result = analyzer._get_ticker_info(symbol)
            assert result == {f"data_{symbol}": i}
    
    def test_cache_memory_efficiency(self, analyzer):
        """キャッシュメモリ効率テスト"""
        # 大量のキャッシュデータを設定
        for i in range(100):
            cache_key = f"info_SYMBOL{i}"
            test_data = {"data": f"value_{i}"}
            analyzer._cache[cache_key] = (test_data, datetime.now())
        
        # キャッシュサイズが適切であることを確認
        assert len(analyzer._cache) == 100
        
        # 個別のキャッシュアクセスが正常であることを確認
        result = analyzer._get_ticker_info('SYMBOL50')
        assert result == {"data": "value_50"}


class TestDividendYieldNormalization:
    """配当利回り正規化のテスト"""
    
    @pytest.fixture
    def analyzer(self):
        """アナライザーのフィクスチャ"""
        return FundamentalAnalyzer()
    
    def test_normalize_dividend_yield_decimal_format(self, analyzer):
        """小数形式の配当利回り（0.025 = 2.5%）のテスト"""
        # 正常な小数形式
        result = analyzer._normalize_dividend_yield(0.025, 2.5, 100.0)
        assert result == 0.025
        
        # 配当金と株価から計算可能で小数形式が正しい場合
        result = analyzer._normalize_dividend_yield(0.03, 3.0, 100.0)
        assert result == 0.03
    
    def test_normalize_dividend_yield_percentage_format(self, analyzer):
        """パーセンテージ形式の配当利回り（2.5 = 2.5%）のテスト"""
        # パーセンテージ形式を小数形式に変換
        result = analyzer._normalize_dividend_yield(2.5, 2.5, 100.0)
        assert result == 0.025
        
        # マミヤ・オーピーのケース（Issue #95）
        result = analyzer._normalize_dividend_yield(12.22, 165.0, 1362.0)
        assert abs(result - 0.1222) < 0.0001
    
    def test_normalize_dividend_yield_heuristic_judgment(self, analyzer):
        """配当金・株価情報がない場合のヒューリスティック判定"""
        # 1を超える値はパーセンテージ形式と判定
        result = analyzer._normalize_dividend_yield(5.5, None, None)
        assert result == 0.055
        
        # 1以下の値は小数形式と判定
        result = analyzer._normalize_dividend_yield(0.035, None, None)
        assert result == 0.035
    
    def test_normalize_dividend_yield_edge_cases(self, analyzer):
        """エッジケースのテスト"""
        # None の場合
        result = analyzer._normalize_dividend_yield(None, 2.5, 100.0)
        assert result is None
        
        # 0の場合
        result = analyzer._normalize_dividend_yield(0.0, 0.0, 100.0)  
        assert result == 0.0
        
        # 株価が0の場合
        result = analyzer._normalize_dividend_yield(2.5, 2.5, 0.0)
        assert result == 0.025  # ヒューリスティック判定
    
    def test_normalize_dividend_yield_boundary_values(self, analyzer):
        """境界値のテスト"""
        # 境界値 1.0
        result = analyzer._normalize_dividend_yield(1.0, None, None)
        assert result == 1.0  # 1以下なので小数形式と判定
        
        # 境界値を少し超える値
        result = analyzer._normalize_dividend_yield(1.01, None, None)
        assert result == 0.0101  # 1を超えるのでパーセンテージ形式と判定


if __name__ == "__main__":
    pytest.main([__file__])