"""
ポートフォリオ分析機能のテストケース
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from src.risk_management.portfolio_analyzer import (
    PortfolioAnalyzer, PortfolioHolding, RiskMetrics, CorrelationAnalysis, OptimizationResult
)
from src.risk_management.risk_manager import RiskManager, Position, PositionSide, RiskParameters


@pytest.fixture
def sample_price_data():
    """サンプル価格データを提供"""
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    np.random.seed(42)  # 再現可能な結果のため
    
    # 3銘柄のサンプルデータ
    symbols = ['AAPL', 'GOOGL', 'MSFT']
    price_data = {}
    
    for i, symbol in enumerate(symbols):
        # 各銘柄で異なる傾向のリターンを生成
        returns = np.random.normal(0.0005 + i * 0.0001, 0.02, len(dates))
        prices = [100 + i * 50]  # 初期価格
        
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        price_data[symbol] = pd.DataFrame({
            'Date': dates,
            'Open': prices,
            'High': [p * 1.02 for p in prices],
            'Low': [p * 0.98 for p in prices],
            'Close': prices,
            'Volume': np.random.randint(1000000, 5000000, len(dates))
        }).set_index('Date')
    
    return price_data


@pytest.fixture
def sample_positions():
    """サンプルポジションを提供"""
    return [
        Position(
            symbol='AAPL',
            side=PositionSide.LONG,
            entry_price=150.0,
            quantity=100,
            entry_time=datetime.now() - timedelta(days=30),
            stop_loss=140.0,
            take_profit=[160.0, 170.0],
            current_price=155.0
        ),
        Position(
            symbol='GOOGL',
            side=PositionSide.LONG,
            entry_price=2800.0,
            quantity=10,
            entry_time=datetime.now() - timedelta(days=20),
            stop_loss=2600.0,
            take_profit=[3000.0, 3200.0],
            current_price=2900.0
        ),
        Position(
            symbol='MSFT',
            side=PositionSide.LONG,
            entry_price=300.0,
            quantity=50,
            entry_time=datetime.now() - timedelta(days=10),
            stop_loss=280.0,
            take_profit=[320.0, 340.0],
            current_price=310.0
        )
    ]


@pytest.fixture
def portfolio_analyzer():
    """PortfolioAnalyzerインスタンスを提供"""
    return PortfolioAnalyzer()


@pytest.fixture
def portfolio_analyzer_with_risk_manager(sample_positions):
    """RiskManager付きPortfolioAnalyzerを提供"""
    risk_params = RiskParameters()
    risk_manager = RiskManager(risk_params, initial_capital=1000000)
    
    # サンプルポジションを追加
    for position in sample_positions:
        position.update_price(position.current_price)
        risk_manager.positions[position.symbol] = position
    
    analyzer = PortfolioAnalyzer(risk_manager)
    return analyzer


class TestPortfolioHolding:
    """PortfolioHoldingクラスのテスト"""
    
    def test_portfolio_holding_creation(self):
        """ポートフォリオ保有銘柄作成のテスト"""
        holding = PortfolioHolding(
            symbol='AAPL',
            quantity=100,
            current_price=150.0,
            market_value=15000.0,
            weight=50.0
        )
        
        assert holding.symbol == 'AAPL'
        assert holding.quantity == 100
        assert holding.current_price == 150.0
        assert holding.market_value == 15000.0
        assert holding.weight == 50.0
    
    def test_from_position(self, sample_positions):
        """Positionからの作成テスト"""
        position = sample_positions[0]  # AAPL
        portfolio_value = 100000.0
        
        holding = PortfolioHolding.from_position(position, portfolio_value)
        
        assert holding.symbol == 'AAPL'
        assert holding.quantity == 100
        assert holding.current_price == 155.0
        assert holding.market_value == 15500.0
        assert holding.weight == 15.5  # 15500/100000 * 100


class TestPortfolioAnalyzer:
    """PortfolioAnalyzerクラスのテスト"""
    
    def test_init(self, portfolio_analyzer):
        """初期化のテスト"""
        assert portfolio_analyzer.risk_manager is None
        assert portfolio_analyzer.price_history == {}
        assert portfolio_analyzer.returns_cache is None
        assert portfolio_analyzer.cache_timestamp is None
    
    def test_set_price_history(self, portfolio_analyzer, sample_price_data):
        """価格履歴設定のテスト"""
        portfolio_analyzer.set_price_history(sample_price_data)
        
        assert len(portfolio_analyzer.price_history) == 3
        assert 'AAPL' in portfolio_analyzer.price_history
        assert 'GOOGL' in portfolio_analyzer.price_history
        assert 'MSFT' in portfolio_analyzer.price_history
        assert portfolio_analyzer.returns_cache is None  # キャッシュクリア
    
    def test_calculate_returns(self, portfolio_analyzer, sample_price_data):
        """リターン計算のテスト"""
        portfolio_analyzer.set_price_history(sample_price_data)
        
        returns_df = portfolio_analyzer._calculate_returns(periods=100)
        
        assert not returns_df.empty
        assert len(returns_df.columns) == 3
        assert 'AAPL' in returns_df.columns
        assert len(returns_df) == 99  # 100期間から1期間減る（pct_change）
        
        # キャッシュされることを確認
        assert portfolio_analyzer.returns_cache is not None
        assert portfolio_analyzer.cache_timestamp is not None
    
    def test_get_portfolio_holdings_empty(self, portfolio_analyzer):
        """空のポートフォリオ保有銘柄取得のテスト"""
        holdings = portfolio_analyzer.get_portfolio_holdings()
        assert holdings == []
    
    def test_get_portfolio_holdings(self, portfolio_analyzer_with_risk_manager):
        """ポートフォリオ保有銘柄取得のテスト"""
        holdings = portfolio_analyzer_with_risk_manager.get_portfolio_holdings()
        
        assert len(holdings) == 3
        
        # AAPL holdings check
        aapl_holding = next(h for h in holdings if h.symbol == 'AAPL')
        assert aapl_holding.quantity == 100
        assert aapl_holding.current_price == 155.0
        assert aapl_holding.market_value == 15500.0
    
    def test_calculate_portfolio_var_empty(self, portfolio_analyzer):
        """空のポートフォリオVaR計算のテスト"""
        var_result = portfolio_analyzer.calculate_portfolio_var()
        
        assert var_result['var'] == 0.0
        assert var_result['cvar'] == 0.0
        assert var_result['portfolio_value'] == 0.0
    
    def test_calculate_portfolio_var(self, portfolio_analyzer_with_risk_manager, sample_price_data):
        """ポートフォリオVaR計算のテスト"""
        portfolio_analyzer_with_risk_manager.set_price_history(sample_price_data)
        
        var_result = portfolio_analyzer_with_risk_manager.calculate_portfolio_var(0.95, 1)
        
        assert 'var_historical' in var_result
        assert 'cvar' in var_result
        assert 'portfolio_value' in var_result
        assert var_result['portfolio_value'] > 0
        assert var_result['confidence_level'] == 0.95
        assert var_result['holding_period'] == 1
    
    def test_analyze_correlations_empty(self, portfolio_analyzer):
        """空データでの相関分析のテスト"""
        correlation_analysis = portfolio_analyzer.analyze_correlations()
        
        assert correlation_analysis.correlation_matrix.empty
        assert correlation_analysis.average_correlation == 0.0
        assert correlation_analysis.max_correlation == 0.0
        assert correlation_analysis.min_correlation == 0.0
        assert correlation_analysis.high_correlation_pairs == []
    
    def test_analyze_correlations(self, portfolio_analyzer, sample_price_data):
        """相関分析のテスト"""
        portfolio_analyzer.set_price_history(sample_price_data)
        
        correlation_analysis = portfolio_analyzer.analyze_correlations()
        
        assert not correlation_analysis.correlation_matrix.empty
        assert correlation_analysis.correlation_matrix.shape == (3, 3)
        assert isinstance(correlation_analysis.average_correlation, float)
        assert isinstance(correlation_analysis.max_correlation, float)
        assert isinstance(correlation_analysis.min_correlation, float)
        assert isinstance(correlation_analysis.high_correlation_pairs, list)
    
    def test_calculate_risk_metrics_empty(self, portfolio_analyzer):
        """空データでのリスク指標計算のテスト"""
        risk_metrics = portfolio_analyzer.calculate_risk_metrics()
        
        assert risk_metrics.portfolio_var_95 == 0
        assert risk_metrics.portfolio_var_99 == 0
        assert risk_metrics.portfolio_cvar_95 == 0
        assert risk_metrics.portfolio_volatility == 0
        assert risk_metrics.sharpe_ratio == 0
        assert risk_metrics.max_drawdown == 0
        assert risk_metrics.diversification_ratio == 0
    
    def test_calculate_risk_metrics(self, portfolio_analyzer_with_risk_manager, sample_price_data):
        """リスク指標計算のテスト"""
        portfolio_analyzer_with_risk_manager.set_price_history(sample_price_data)
        
        risk_metrics = portfolio_analyzer_with_risk_manager.calculate_risk_metrics()
        
        assert isinstance(risk_metrics, RiskMetrics)
        assert risk_metrics.portfolio_volatility >= 0
        assert isinstance(risk_metrics.sharpe_ratio, float)
        assert risk_metrics.max_drawdown >= 0
        assert risk_metrics.diversification_ratio >= 0
    
    def test_optimize_portfolio_empty(self, portfolio_analyzer):
        """空データでのポートフォリオ最適化のテスト"""
        result = portfolio_analyzer.optimize_portfolio("max_sharpe")
        
        assert result.optimal_weights == {}
        assert result.expected_return == 0
        assert result.expected_volatility == 0
        assert result.sharpe_ratio == 0
        assert result.optimization_type == "max_sharpe"
    
    def test_optimize_portfolio_max_sharpe(self, portfolio_analyzer, sample_price_data):
        """最大シャープレシオ最適化のテスト"""
        portfolio_analyzer.set_price_history(sample_price_data)
        
        result = portfolio_analyzer.optimize_portfolio("max_sharpe")
        
        assert isinstance(result, OptimizationResult)
        assert result.optimization_type == "max_sharpe"
        
        if result.optimal_weights:  # 最適化が成功した場合
            assert len(result.optimal_weights) == 3
            assert abs(sum(result.optimal_weights.values()) - 1.0) < 0.01  # 重みの合計≈1
            assert all(w >= 0 for w in result.optimal_weights.values())  # 非負制約
    
    def test_optimize_portfolio_min_variance(self, portfolio_analyzer, sample_price_data):
        """最小分散最適化のテスト"""
        portfolio_analyzer.set_price_history(sample_price_data)
        
        result = portfolio_analyzer.optimize_portfolio("min_variance")
        
        assert result.optimization_type == "min_variance"
        
        if result.optimal_weights:
            assert len(result.optimal_weights) == 3
            assert abs(sum(result.optimal_weights.values()) - 1.0) < 0.01
    
    def test_optimize_portfolio_target_return(self, portfolio_analyzer, sample_price_data):
        """目標リターン制約最適化のテスト"""
        portfolio_analyzer.set_price_history(sample_price_data)
        
        result = portfolio_analyzer.optimize_portfolio("target_return", target_return=0.1)
        
        assert result.optimization_type == "target_return"
        
        if result.optimal_weights:
            assert len(result.optimal_weights) == 3
            assert abs(sum(result.optimal_weights.values()) - 1.0) < 0.01
    
    def test_monte_carlo_stress_test_empty(self, portfolio_analyzer):
        """空データでのモンテカルロストレステストのテスト"""
        result = portfolio_analyzer.monte_carlo_stress_test(100, 5)
        
        assert result['var_95'] == 0
        assert result['var_99'] == 0
        assert result['expected_loss'] == 0
        assert result['worst_case'] == 0
    
    def test_monte_carlo_stress_test(self, portfolio_analyzer_with_risk_manager, sample_price_data):
        """モンテカルロストレステストのテスト"""
        portfolio_analyzer_with_risk_manager.set_price_history(sample_price_data)
        
        result = portfolio_analyzer_with_risk_manager.monte_carlo_stress_test(1000, 5)
        
        assert 'var_95' in result
        assert 'var_99' in result
        assert 'expected_loss' in result
        assert 'worst_case' in result
        assert 'probability_of_loss' in result
        assert result['simulations'] == 1000
        assert result['time_horizon'] == 5
        assert result['portfolio_value'] > 0
    
    def test_generate_efficient_frontier_empty(self, portfolio_analyzer):
        """空データでの効率的フロンティア生成のテスト"""
        frontier = portfolio_analyzer.generate_efficient_frontier(10)
        
        assert frontier['returns'] == []
        assert frontier['volatilities'] == []
        assert frontier['sharpe_ratios'] == []
    
    def test_generate_efficient_frontier(self, portfolio_analyzer, sample_price_data):
        """効率的フロンティア生成のテスト"""
        portfolio_analyzer.set_price_history(sample_price_data)
        
        frontier = portfolio_analyzer.generate_efficient_frontier(5)  # 少ない点数でテスト
        
        assert isinstance(frontier['returns'], list)
        assert isinstance(frontier['volatilities'], list)
        assert isinstance(frontier['sharpe_ratios'], list)
        
        # 成功した場合のチェック
        if frontier['returns']:
            assert len(frontier['returns']) == len(frontier['volatilities'])
            assert len(frontier['returns']) == len(frontier['sharpe_ratios'])
    
    def test_get_portfolio_analysis_summary_empty(self, portfolio_analyzer):
        """空データでのポートフォリオ分析サマリーのテスト"""
        summary = portfolio_analyzer.get_portfolio_analysis_summary()
        
        # 空の場合でもエラーにならないことを確認
        assert isinstance(summary, dict)
    
    def test_get_portfolio_analysis_summary(self, portfolio_analyzer_with_risk_manager, sample_price_data):
        """ポートフォリオ分析サマリーのテスト"""
        portfolio_analyzer_with_risk_manager.set_price_history(sample_price_data)
        
        summary = portfolio_analyzer_with_risk_manager.get_portfolio_analysis_summary()
        
        assert 'portfolio_overview' in summary
        assert 'risk_metrics' in summary
        assert 'correlation_analysis' in summary
        assert 'stress_test' in summary
        assert 'optimization_suggestions' in summary
        
        portfolio_overview = summary['portfolio_overview']
        assert portfolio_overview['total_value'] > 0
        assert portfolio_overview['num_holdings'] == 3
        assert len(portfolio_overview['holdings']) == 3
    
    def test_generate_optimization_suggestions(self, portfolio_analyzer_with_risk_manager):
        """最適化提案生成のテスト"""
        # モックデータでテスト
        risk_metrics = RiskMetrics(0, 0, 0, 0.4, 0.3, 0.25, 1.1)  # 高ボラティリティ、低シャープレシオ
        correlation_analysis = CorrelationAnalysis(
            correlation_matrix=pd.DataFrame(),
            average_correlation=0.5,
            max_correlation=0.9,
            min_correlation=0.1,
            high_correlation_pairs=[('A', 'B', 0.8), ('C', 'D', 0.75), ('E', 'F', 0.9), ('G', 'H', 0.85)]
        )
        
        suggestions = portfolio_analyzer_with_risk_manager._generate_optimization_suggestions(
            risk_metrics, correlation_analysis
        )
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        
        # 高ボラティリティに対する提案があることを確認
        high_vol_suggestion = any('ボラティリティが高い' in s for s in suggestions)
        assert high_vol_suggestion
        
        # 高相関ペアに対する提案があることを確認
        high_corr_suggestion = any('高い相関' in s for s in suggestions)
        assert high_corr_suggestion


class TestRiskMetrics:
    """RiskMetricsクラスのテスト"""
    
    def test_risk_metrics_creation(self):
        """リスク指標作成のテスト"""
        metrics = RiskMetrics(
            portfolio_var_95=10000.0,
            portfolio_var_99=15000.0,
            portfolio_cvar_95=12000.0,
            portfolio_volatility=0.15,
            sharpe_ratio=1.2,
            max_drawdown=0.08,
            diversification_ratio=1.5
        )
        
        assert metrics.portfolio_var_95 == 10000.0
        assert metrics.portfolio_var_99 == 15000.0
        assert metrics.portfolio_cvar_95 == 12000.0
        assert metrics.portfolio_volatility == 0.15
        assert metrics.sharpe_ratio == 1.2
        assert metrics.max_drawdown == 0.08
        assert metrics.diversification_ratio == 1.5


class TestCorrelationAnalysis:
    """CorrelationAnalysisクラスのテスト"""
    
    def test_correlation_analysis_creation(self):
        """相関分析結果作成のテスト"""
        corr_matrix = pd.DataFrame(
            [[1.0, 0.5, 0.3], [0.5, 1.0, 0.7], [0.3, 0.7, 1.0]],
            index=['A', 'B', 'C'],
            columns=['A', 'B', 'C']
        )
        
        analysis = CorrelationAnalysis(
            correlation_matrix=corr_matrix,
            average_correlation=0.5,
            max_correlation=0.7,
            min_correlation=0.3,
            high_correlation_pairs=[('B', 'C', 0.7)]
        )
        
        assert analysis.correlation_matrix.shape == (3, 3)
        assert analysis.average_correlation == 0.5
        assert analysis.max_correlation == 0.7
        assert analysis.min_correlation == 0.3
        assert len(analysis.high_correlation_pairs) == 1
        assert analysis.high_correlation_pairs[0] == ('B', 'C', 0.7)


class TestOptimizationResult:
    """OptimizationResultクラスのテスト"""
    
    def test_optimization_result_creation(self):
        """最適化結果作成のテスト"""
        result = OptimizationResult(
            optimal_weights={'A': 0.4, 'B': 0.3, 'C': 0.3},
            expected_return=0.12,
            expected_volatility=0.18,
            sharpe_ratio=0.67,
            optimization_type='max_sharpe'
        )
        
        assert result.optimal_weights == {'A': 0.4, 'B': 0.3, 'C': 0.3}
        assert result.expected_return == 0.12
        assert result.expected_volatility == 0.18
        assert result.sharpe_ratio == 0.67
        assert result.optimization_type == 'max_sharpe'


class TestIntegration:
    """統合テスト"""
    
    def test_full_analysis_workflow(self, portfolio_analyzer_with_risk_manager, sample_price_data):
        """完全な分析ワークフローのテスト"""
        analyzer = portfolio_analyzer_with_risk_manager
        analyzer.set_price_history(sample_price_data)
        
        # 1. ポートフォリオ保有銘柄取得
        holdings = analyzer.get_portfolio_holdings()
        assert len(holdings) > 0
        
        # 2. VaR計算
        var_result = analyzer.calculate_portfolio_var()
        assert var_result['portfolio_value'] > 0
        
        # 3. 相関分析
        correlation_analysis = analyzer.analyze_correlations()
        assert not correlation_analysis.correlation_matrix.empty
        
        # 4. リスク指標計算
        risk_metrics = analyzer.calculate_risk_metrics()
        assert risk_metrics.portfolio_volatility >= 0
        
        # 5. ストレステスト
        stress_result = analyzer.monte_carlo_stress_test(100, 5)  # 少ない回数でテスト
        assert 'var_95' in stress_result
        
        # 6. 最適化
        opt_result = analyzer.optimize_portfolio("max_sharpe")
        assert opt_result.optimization_type == "max_sharpe"
        
        # 7. 総合サマリー
        summary = analyzer.get_portfolio_analysis_summary()
        assert 'portfolio_overview' in summary
        assert 'risk_metrics' in summary
    
    @patch('numpy.random.multivariate_normal')
    def test_monte_carlo_with_mock(self, mock_random, portfolio_analyzer_with_risk_manager, sample_price_data):
        """モックを使用したモンテカルロテストの確定的テスト"""
        analyzer = portfolio_analyzer_with_risk_manager
        analyzer.set_price_history(sample_price_data)
        
        # 確定的な結果のためのモック設定
        mock_random.return_value = np.array([[0.01, 0.01, 0.01]] * 5)  # 5日間の固定リターン
        
        result = analyzer.monte_carlo_stress_test(10, 5)
        
        assert result['simulations'] == 10
        assert result['time_horizon'] == 5
        assert result['portfolio_value'] > 0
        assert 'var_95' in result