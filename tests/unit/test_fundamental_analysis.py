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


if __name__ == "__main__":
    pytest.main([__file__])