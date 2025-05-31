"""市場環境分析機能のテスト"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.technical_analysis.market_environment import (
    MarketEnvironmentAnalyzer,
    MarketSentiment,
    RiskState,
    MarketEnvironment
)
from src.data_collector.stock_data_collector import StockDataCollector
from src.technical_analysis.indicators import TechnicalIndicators


class TestMarketEnvironmentAnalyzer:
    """MarketEnvironmentAnalyzerクラスのテスト"""
    
    @pytest.fixture
    def analyzer(self):
        """アナライザーのインスタンスを作成"""
        return MarketEnvironmentAnalyzer()
    
    @pytest.fixture
    def sample_index_data(self):
        """サンプルインデックスデータ"""
        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        
        # 日経225のサンプルデータ
        nikkei_data = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.uniform(27000, 28000, 30),
            'high': np.random.uniform(27500, 28500, 30),
            'low': np.random.uniform(26500, 27500, 30),
            'close': np.random.uniform(27000, 28000, 30),
            'volume': np.random.uniform(1000000, 2000000, 30)
        })
        
        # S&P500のサンプルデータ
        sp500_data = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.uniform(4200, 4300, 30),
            'high': np.random.uniform(4250, 4350, 30),
            'low': np.random.uniform(4150, 4250, 30),
            'close': np.random.uniform(4200, 4300, 30),
            'volume': np.random.uniform(1000000, 2000000, 30)
        })
        
        # VIXのサンプルデータ
        vix_data = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.uniform(15, 25, 30),
            'high': np.random.uniform(18, 28, 30),
            'low': np.random.uniform(12, 22, 30),
            'close': np.random.uniform(15, 25, 30),
            'volume': np.random.uniform(100000, 200000, 30)
        })
        
        return {
            'nikkei225': nikkei_data,
            'sp500': sp500_data,
            'vix': vix_data
        }
    
    def test_initialization(self, analyzer):
        """初期化のテスト"""
        assert analyzer is not None
        assert hasattr(analyzer, 'data_collector')
        assert hasattr(analyzer, 'validator')
        assert 'nikkei225' in analyzer.INDICES
        assert 'technology' in analyzer.SECTOR_ETFS
    
    def test_determine_market_sentiment(self, analyzer):
        """市場センチメント判定のテスト"""
        # 極度の恐怖（VIX > 50）
        sentiment = analyzer._determine_market_sentiment(55.0, {})
        assert sentiment == MarketSentiment.EXTREME_FEAR
        
        # 恐怖（VIX > 40）
        sentiment = analyzer._determine_market_sentiment(45.0, {})
        assert sentiment == MarketSentiment.FEAR
        
        # 極度の貪欲（VIX < 12）
        sentiment = analyzer._determine_market_sentiment(10.0, {})
        assert sentiment == MarketSentiment.EXTREME_GREED
        
        # 貪欲（VIX < 20）
        sentiment = analyzer._determine_market_sentiment(15.0, {})
        assert sentiment == MarketSentiment.GREED
        
        # 中立
        sentiment = analyzer._determine_market_sentiment(25.0, {})
        assert sentiment == MarketSentiment.NEUTRAL
    
    def test_determine_risk_state(self, analyzer):
        """リスク状態判定のテスト"""
        # リスクオン状態（低VIX + 成長セクター好調）
        indices_perf = {}
        vix = 15.0
        sector_perf = {
            'technology': 5.0,
            'financial': 4.0,
            'healthcare': 1.0,
            'consumer': 0.5
        }
        
        risk_state = analyzer._determine_risk_state(indices_perf, vix, sector_perf)
        assert risk_state == RiskState.RISK_ON
        
        # リスクオフ状態（高VIX + ディフェンシブセクター好調）
        vix = 35.0
        sector_perf = {
            'technology': -2.0,
            'financial': -3.0,
            'healthcare': 2.0,
            'consumer': 1.5
        }
        
        risk_state = analyzer._determine_risk_state(indices_perf, vix, sector_perf)
        assert risk_state == RiskState.RISK_OFF
    
    def test_calculate_indices_performance(self, analyzer, sample_index_data):
        """インデックスパフォーマンス計算のテスト"""
        performance = analyzer._calculate_indices_performance(sample_index_data)
        
        assert 'nikkei225' in performance
        assert 'sp500' in performance
        
        # 各インデックスに必要なメトリクスが含まれているか確認
        for index_name, perf in performance.items():
            if len(sample_index_data[index_name]) >= 2:
                assert 'daily' in perf
            if len(sample_index_data[index_name]) >= 20:
                assert 'volatility' in perf
    
    def test_identify_risk_factors(self, analyzer):
        """リスク要因特定のテスト"""
        indices_perf = {
            'nikkei225': {'daily': -4.0, 'volatility': 35.0},
            'sp500': {'daily': -3.5, 'volatility': 32.0}
        }
        vix = 45.0
        sentiment = MarketSentiment.EXTREME_FEAR
        sector_perf = {
            'technology': -5.0,
            'financial': -4.0,
            'healthcare': 2.0
        }
        
        risk_factors = analyzer._identify_risk_factors(
            indices_perf, vix, sentiment, sector_perf
        )
        
        assert len(risk_factors) > 0
        assert any("VIX指数が高水準" in factor for factor in risk_factors)
        assert any("極端な状態" in factor for factor in risk_factors)
        assert any("大幅下落" in factor for factor in risk_factors)
    
    def test_identify_opportunities(self, analyzer):
        """投資機会特定のテスト"""
        indices_perf = {
            'nikkei225': {'rsi': 25.0, 'volatility': 12.0},
            'sp500': {'rsi': 28.0, 'volatility': 14.0}
        }
        sentiment = MarketSentiment.EXTREME_FEAR
        sector_perf = {
            'technology': 5.0,
            'financial': 3.0,
            'healthcare': -1.0
        }
        
        opportunities = analyzer._identify_opportunities(
            indices_perf, sentiment, sector_perf
        )
        
        assert len(opportunities) > 0
        assert any("売られ過ぎ" in opp for opp in opportunities)
        assert any("極度の恐怖" in opp for opp in opportunities)
        assert any("好調" in opp for opp in opportunities)
    
    def test_analyze_market_breadth(self, analyzer):
        """市場の幅分析のテスト"""
        indices_perf = {
            'nikkei225': {'volatility': 20.0},
            'sp500': {'volatility': 18.0}
        }
        sector_perf = {
            'technology': 2.0,
            'financial': 1.5,
            'healthcare': -0.5,
            'consumer': -1.0,
            'industrial': 0.5,
            'energy': -2.0
        }
        
        breadth = analyzer._analyze_market_breadth(indices_perf, sector_perf)
        
        assert 'advance_decline_ratio' in breadth
        assert 'positive_sectors' in breadth
        assert 'negative_sectors' in breadth
        assert 'avg_volatility' in breadth
        
        # 上昇セクター比率の確認
        assert breadth['positive_sectors'] == 3
        assert breadth['negative_sectors'] == 3
        assert breadth['advance_decline_ratio'] == 50.0
    
    def test_generate_recommendation(self, analyzer):
        """投資推奨生成のテスト"""
        # 高リスク環境
        sentiment = MarketSentiment.EXTREME_FEAR
        risk_state = RiskState.RISK_OFF
        risk_factors = ["リスク1", "リスク2", "リスク3", "リスク4"]
        opportunities = []
        
        recommendation = analyzer._generate_recommendation(
            sentiment, risk_state, risk_factors, opportunities
        )
        
        assert "リスクが高く" in recommendation
        assert "リスクオフ" in recommendation
        assert "極度の恐怖" in recommendation
        
        # 低リスク環境
        sentiment = MarketSentiment.NEUTRAL
        risk_state = RiskState.RISK_ON
        risk_factors = []
        opportunities = ["機会1", "機会2"]
        
        recommendation = analyzer._generate_recommendation(
            sentiment, risk_state, risk_factors, opportunities
        )
        
        assert "安定" in recommendation
        assert "リスクオン" in recommendation
        assert "2つの投資機会" in recommendation
    
    @patch.object(MarketEnvironmentAnalyzer, '_fetch_indices_data')
    def test_analyze_market_environment(self, mock_fetch, analyzer, sample_index_data):
        """市場環境分析の統合テスト"""
        # モックデータの設定
        mock_fetch.return_value = sample_index_data
        
        # 分析実行
        env = analyzer.analyze_market_environment(period="5d", interval="1d")
        
        # 結果の検証
        assert isinstance(env, MarketEnvironment)
        assert env.timestamp is not None
        assert isinstance(env.market_sentiment, MarketSentiment)
        assert isinstance(env.risk_state, RiskState)
        assert isinstance(env.vix_level, float)
        assert isinstance(env.recommendation, str)
        assert isinstance(env.risk_factors, list)
        assert isinstance(env.opportunities, list)
    
    @patch.object(MarketEnvironmentAnalyzer, 'analyze_market_environment')
    def test_get_daily_market_report(self, mock_analyze, analyzer):
        """日次市場レポート生成のテスト"""
        # モック環境データ
        mock_env = MarketEnvironment(
            timestamp=datetime.now(),
            indices_performance={'nikkei225': {'daily': 1.5}},
            sector_performance={'technology': 2.0},
            market_sentiment=MarketSentiment.NEUTRAL,
            risk_state=RiskState.RISK_ON,
            vix_level=18.5,
            market_breadth={'advance_decline_ratio': 60.0},
            recommendation="テスト推奨",
            risk_factors=["リスク1"],
            opportunities=["機会1"]
        )
        mock_analyze.return_value = mock_env
        
        # レポート生成
        report = analyzer.get_daily_market_report()
        
        # レポート構造の検証
        assert 'report_date' in report
        assert 'executive_summary' in report
        assert 'indices_performance' in report
        assert 'sector_analysis' in report
        assert 'market_breadth' in report
        assert 'risk_assessment' in report
        assert 'opportunities' in report
        assert 'technical_levels' in report
        
        # エグゼクティブサマリーの検証
        summary = report['executive_summary']
        assert summary['market_sentiment'] == MarketSentiment.NEUTRAL.value
        assert summary['risk_state'] == RiskState.RISK_ON.value
        assert summary['vix_level'] == 18.5
        assert summary['recommendation'] == "テスト推奨"


class TestMarketEnvironmentAnalyzerErrorHandling:
    """MarketEnvironmentAnalyzerのエラーハンドリングのテスト"""
    
    @pytest.fixture
    def analyzer(self):
        """アナライザーのインスタンスを作成"""
        return MarketEnvironmentAnalyzer()
    
    @patch.object(StockDataCollector, 'get_stock_data')
    def test_fetch_indices_data_with_exception(self, mock_get_data, analyzer):
        """インデックスデータ取得でエラーが発生した場合のテスト"""
        # データ取得でエラーを発生させる
        mock_get_data.side_effect = Exception("Data fetch error")
        
        result = analyzer._fetch_indices_data("5d", "1d")
        
        # エラーが発生してもresultは空の辞書が返される
        assert result == {}
    
    def test_calculate_indices_performance_with_error(self, analyzer):
        """パフォーマンス計算でエラーが発生した場合のテスト"""
        # 不正なデータ構造
        indices_data = {
            'nikkei225': pd.DataFrame({'invalid_column': [1, 2, 3]})
        }
        
        result = analyzer._calculate_indices_performance(indices_data)
        
        # エラーが発生しても結果は返される
        assert isinstance(result, dict)
        assert 'nikkei225' not in result  # エラーのあったインデックスは含まれない
    
    @patch.object(StockDataCollector, 'get_stock_data')
    def test_analyze_sector_performance_with_exception(self, mock_get_data, analyzer):
        """セクターパフォーマンス分析でエラーが発生した場合のテスト"""
        # データ取得でエラーを発生させる
        mock_get_data.side_effect = Exception("Sector data error")
        
        result = analyzer._analyze_sector_performance("5d", "1d")
        
        # エラーが発生しても空の辞書が返される
        assert result == {}
    
    def test_calculate_key_levels_implementation(self, analyzer):
        """_calculate_key_levelsメソッドのテスト"""
        indices_perf = {
            'nikkei225': {'daily': 1.0},
            'sp500': {'daily': 0.5}
        }
        
        result = analyzer._calculate_key_levels(indices_perf)
        
        # nikkei225とsp500のキーレベルが含まれることを確認
        assert 'nikkei225' in result
        assert 'sp500' in result
        assert result['nikkei225']['current'] == "取得中"
        assert result['nikkei225']['support'] == "計算中"
        assert result['nikkei225']['resistance'] == "計算中"


class TestMarketEnvironmentAnalyzerEdgeCases:
    """MarketEnvironmentAnalyzerのエッジケースのテスト"""
    
    @pytest.fixture
    def analyzer(self):
        """アナライザーのインスタンスを作成"""
        return MarketEnvironmentAnalyzer()
    
    def test_calculate_indices_performance_empty_data(self, analyzer):
        """空のデータでパフォーマンス計算のテスト"""
        indices_data = {
            'nikkei225': pd.DataFrame()
        }
        
        result = analyzer._calculate_indices_performance(indices_data)
        
        assert result == {}
    
    def test_determine_market_sentiment_edge_values(self, analyzer):
        """境界値でのセンチメント判定のテスト"""
        # VIX = 12（境界値）
        sentiment = analyzer._determine_market_sentiment(12.0, {})
        assert sentiment == MarketSentiment.EXTREME_GREED
        
        # VIX = 20（境界値）
        sentiment = analyzer._determine_market_sentiment(20.0, {})
        assert sentiment == MarketSentiment.GREED
        
        # VIX = 30（境界値）
        sentiment = analyzer._determine_market_sentiment(30.0, {})
        assert sentiment == MarketSentiment.NEUTRAL
        
        # VIX = 40（境界値）
        sentiment = analyzer._determine_market_sentiment(40.0, {})
        assert sentiment == MarketSentiment.FEAR
        
        # VIX = 50（境界値）
        sentiment = analyzer._determine_market_sentiment(50.0, {})
        assert sentiment == MarketSentiment.EXTREME_FEAR
    
    def test_determine_market_sentiment_with_performance(self, analyzer):
        """パフォーマンスデータを含むセンチメント判定のテスト"""
        # 平均パフォーマンスが-2%未満
        indices_perf = {
            'nikkei225': {'daily': -3.0},
            'sp500': {'daily': -2.5}
        }
        sentiment = analyzer._determine_market_sentiment(25.0, indices_perf)
        assert sentiment == MarketSentiment.FEAR
        
        # 平均パフォーマンスが+2%超
        indices_perf = {
            'nikkei225': {'daily': 2.5},
            'sp500': {'daily': 3.0}
        }
        sentiment = analyzer._determine_market_sentiment(25.0, indices_perf)
        assert sentiment == MarketSentiment.GREED
    
    def test_determine_risk_state_equal_performance(self, analyzer):
        """グロースとディフェンシブセクターの成績が同等の場合のテスト"""
        indices_perf = {}
        vix = 25.0
        sector_perf = {
            'technology': 2.0,
            'financial': 2.0,
            'healthcare': 2.0,
            'consumer': 2.0
        }
        
        risk_state = analyzer._determine_risk_state(indices_perf, vix, sector_perf)
        
        # パフォーマンスが同等の場合は他の要因で決まる
        assert risk_state in [RiskState.RISK_ON, RiskState.RISK_OFF, RiskState.NEUTRAL]
    
    def test_analyze_market_breadth_no_sectors(self, analyzer):
        """セクターデータがない場合の市場の幅分析のテスト"""
        indices_perf = {
            'nikkei225': {'volatility': 20.0}
        }
        sector_perf = {}
        
        breadth = analyzer._analyze_market_breadth(indices_perf, sector_perf)
        
        # セクターデータがない場合はセクター関連のキーは含まれない
        assert 'positive_sectors' not in breadth
        assert 'negative_sectors' not in breadth
        assert 'advance_decline_ratio' not in breadth
        # ボラティリティは計算される
        assert 'avg_volatility' in breadth
        assert breadth['avg_volatility'] == 20.0
    
    def test_generate_recommendation_mixed_signals(self, analyzer):
        """混在したシグナルでの推奨生成のテスト"""
        # リスクオンだが恐怖センチメント
        sentiment = MarketSentiment.FEAR
        risk_state = RiskState.RISK_ON
        risk_factors = ["リスク1"]
        opportunities = ["機会1", "機会2"]
        
        recommendation = analyzer._generate_recommendation(
            sentiment, risk_state, risk_factors, opportunities
        )
        
        # 推奨が生成されることを確認
        assert len(recommendation) > 0
        assert isinstance(recommendation, str)
    
    def test_calculate_indices_performance_insufficient_data(self, analyzer):
        """データが不足している場合のパフォーマンス計算のテスト"""
        indices_data = {
            'nikkei225': pd.DataFrame({
                'timestamp': [datetime.now()],
                'close': [27000.0]
            })  # 1行のみ
        }
        
        result = analyzer._calculate_indices_performance(indices_data)
        
        # データが不足していても処理が続行される
        assert 'nikkei225' in result
        assert 'daily' not in result['nikkei225']  # 1日リターンは計算できない
    
    def test_get_current_vix_no_data(self, analyzer):
        """VIXデータがない場合のテスト"""
        indices_data = {
            'nikkei225': pd.DataFrame({'close': [27000.0]})
        }
        
        vix = analyzer._get_current_vix(indices_data)
        
        # デフォルト値が返される
        assert vix == 20.0
    
    @patch.object(TechnicalIndicators, 'rsi')
    def test_calculate_indices_performance_with_rsi_error(self, mock_rsi, analyzer):
        """RSI計算でエラーが発生した場合のテスト"""
        mock_rsi.return_value = pd.Series()  # 空のシリーズを返す
        
        indices_data = {
            'nikkei225': pd.DataFrame({
                'timestamp': pd.date_range(end=datetime.now(), periods=30),
                'open': np.random.uniform(27000, 28000, 30),
                'high': np.random.uniform(27500, 28500, 30),
                'low': np.random.uniform(26500, 27500, 30),
                'close': np.random.uniform(27000, 28000, 30),
                'volume': np.random.uniform(1000000, 2000000, 30)
            })
        }
        
        result = analyzer._calculate_indices_performance(indices_data)
        
        # RSIがなくても他の指標は計算される
        assert 'nikkei225' in result
        assert 'daily' in result['nikkei225']
        assert 'rsi' not in result['nikkei225']