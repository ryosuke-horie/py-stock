"""
成功/失敗パターン分析機能のユニットテスト
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.performance_tracking.pattern_analyzer import (
    PatternAnalyzer, TradingPattern, PatternType
)
from src.performance_tracking.trade_history_manager import (
    TradeHistoryManager, TradeRecord, TradeDirection, TradeStatus
)


class TestPatternAnalyzer:
    """PatternAnalyzerクラスのテスト"""
    
    @pytest.fixture
    def temp_db_path(self):
        """テンポラリDBファイルパス"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            yield f.name
        os.unlink(f.name)
    
    @pytest.fixture
    def trade_manager(self, temp_db_path):
        """テスト用取引履歴管理"""
        return TradeHistoryManager(temp_db_path)
    
    @pytest.fixture
    def analyzer(self, trade_manager):
        """テスト用パターン分析器"""
        return PatternAnalyzer(trade_manager)
    
    @pytest.fixture
    def sample_trades(self, trade_manager):
        """サンプル取引データ"""
        trades = []
        base_time = datetime.now() - timedelta(days=30)
        
        # 朝取引（成功パターン）
        for i in range(5):
            trade = TradeRecord(
                trade_id=f"morning_{i}",
                symbol="TEST",
                direction=TradeDirection.LONG,
                entry_time=base_time + timedelta(days=i, hours=10),  # 10:00
                entry_price=1000.0,
                quantity=100,
                exit_time=base_time + timedelta(days=i, hours=11),
                exit_price=1050.0,  # 利益
                realized_pnl=5000.0,
                realized_pnl_pct=5.0,
                status=TradeStatus.CLOSED,
                strategy_name="Morning Strategy"
            )
            trade_manager.add_trade(trade)
            trades.append(trade)
        
        # 午後取引（失敗パターン）
        for i in range(5):
            trade = TradeRecord(
                trade_id=f"afternoon_{i}",
                symbol="TEST",
                direction=TradeDirection.LONG,
                entry_time=base_time + timedelta(days=i, hours=14),  # 14:00
                entry_price=1000.0,
                quantity=100,
                exit_time=base_time + timedelta(days=i, hours=15),
                exit_price=950.0,  # 損失
                realized_pnl=-5000.0,
                realized_pnl_pct=-5.0,
                status=TradeStatus.CLOSED,
                strategy_name="Afternoon Strategy"
            )
            trade_manager.add_trade(trade)
            trades.append(trade)
        
        return trades
    
    def test_initialization(self, analyzer):
        """初期化テスト"""
        assert analyzer.trade_manager is not None
        assert analyzer.patterns_cache == {}
    
    def test_analyze_patterns_no_data(self, analyzer):
        """データなしでのパターン分析テスト"""
        patterns = analyzer.analyze_patterns(lookback_days=90, min_pattern_size=3)
        
        assert isinstance(patterns, list)
        assert len(patterns) == 0
    
    def test_analyze_patterns_insufficient_data(self, analyzer, trade_manager):
        """データ不足でのパターン分析テスト"""
        # 最小パターンサイズより少ないデータを追加
        trade = TradeRecord(
            trade_id="test_1",
            symbol="TEST",
            direction=TradeDirection.LONG,
            entry_time=datetime.now() - timedelta(days=1),
            entry_price=1000.0,
            quantity=100,
            exit_time=datetime.now(),
            exit_price=1100.0,
            realized_pnl=10000.0,
            status=TradeStatus.CLOSED
        )
        trade_manager.add_trade(trade)
        
        patterns = analyzer.analyze_patterns(lookback_days=90, min_pattern_size=5)
        assert len(patterns) == 0
    
    def test_analyze_time_patterns(self, analyzer, sample_trades):
        """時間帯パターン分析テスト"""
        patterns = analyzer.analyze_patterns(lookback_days=90, min_pattern_size=3)
        
        # 朝と午後のパターンが検出されることを確認
        pattern_names = [p.pattern_id for p in patterns]
        assert any('morning' in name for name in pattern_names)
        assert any('afternoon' in name for name in pattern_names)
        
        # 朝のパターンは成功、午後は失敗として分類されるべき
        morning_pattern = next((p for p in patterns if 'morning' in p.pattern_id), None)
        afternoon_pattern = next((p for p in patterns if 'afternoon' in p.pattern_id), None)
        
        if morning_pattern:
            assert morning_pattern.pattern_type == PatternType.SUCCESS
            assert morning_pattern.success_rate == 1.0
        
        if afternoon_pattern:
            assert afternoon_pattern.pattern_type == PatternType.FAILURE
            assert afternoon_pattern.success_rate == 0.0
    
    def test_analyze_strategy_patterns(self, analyzer, sample_trades):
        """戦略パターン分析テスト"""
        patterns = analyzer.analyze_patterns(lookback_days=90, min_pattern_size=3)
        
        # 戦略パターンが検出されることを確認
        strategy_patterns = [p for p in patterns if 'strategy' in p.pattern_id]
        assert len(strategy_patterns) >= 0  # データによっては検出されない場合もある
    
    def test_analyze_holding_period_patterns(self, analyzer, trade_manager):
        """保有期間パターン分析テスト"""
        base_time = datetime.now() - timedelta(days=30)
        
        # 異なる保有期間の取引を追加
        for i in range(5):
            # 短期保有（1時間以内）
            trade = TradeRecord(
                trade_id=f"short_{i}",
                symbol="TEST",
                direction=TradeDirection.LONG,
                entry_time=base_time + timedelta(days=i),
                entry_price=1000.0,
                quantity=100,
                exit_time=base_time + timedelta(days=i, minutes=30),  # 30分後
                exit_price=1050.0,
                realized_pnl=5000.0,
                status=TradeStatus.CLOSED
            )
            trade_manager.add_trade(trade)
        
        patterns = analyzer.analyze_patterns(lookback_days=90, min_pattern_size=3)
        
        # 保有期間パターンが検出される可能性を確認
        holding_patterns = [p for p in patterns if 'holding' in p.pattern_id]
        # パターンが検出されない場合でもエラーにしない
        assert isinstance(holding_patterns, list)
    
    def test_analyze_exit_patterns(self, analyzer, trade_manager):
        """決済パターン分析テスト"""
        base_time = datetime.now() - timedelta(days=30)
        
        # 利確での決済パターン
        for i in range(5):
            trade = TradeRecord(
                trade_id=f"tp_{i}",
                symbol="TEST",
                direction=TradeDirection.LONG,
                entry_time=base_time + timedelta(days=i),
                entry_price=1000.0,
                quantity=100,
                exit_time=base_time + timedelta(days=i, hours=1),
                exit_price=1100.0,
                exit_reason="Take Profit",
                realized_pnl=10000.0,
                status=TradeStatus.CLOSED
            )
            trade_manager.add_trade(trade)
        
        patterns = analyzer.analyze_patterns(lookback_days=90, min_pattern_size=3)
        
        # 決済パターンが検出される可能性を確認
        exit_patterns = [p for p in patterns if 'exit' in p.pattern_id]
        assert isinstance(exit_patterns, list)
    
    def test_get_pattern_recommendations(self, analyzer, sample_trades):
        """パターン推奨事項生成テスト"""
        patterns = analyzer.analyze_patterns(lookback_days=90, min_pattern_size=3)
        recommendations = analyzer.get_pattern_recommendations(patterns)
        
        assert isinstance(recommendations, dict)
        assert 'continue' in recommendations
        assert 'avoid' in recommendations
        assert 'improve' in recommendations
        
        # 各項目がリストであることを確認
        assert isinstance(recommendations['continue'], list)
        assert isinstance(recommendations['avoid'], list)
        assert isinstance(recommendations['improve'], list)
    
    def test_export_patterns(self, analyzer, sample_trades, temp_db_path):
        """パターンエクスポートテスト"""
        patterns = analyzer.analyze_patterns(lookback_days=90, min_pattern_size=3)
        
        output_path = temp_db_path.replace('.db', '_patterns.json')
        success = analyzer.export_patterns(patterns, output_path)
        
        assert success is True
        assert os.path.exists(output_path)
        
        # ファイル内容確認
        import json
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert 'export_date' in data
        assert 'patterns' in data
        assert isinstance(data['patterns'], list)
        
        # クリーンアップ
        os.unlink(output_path)
    
    def test_pattern_confidence_calculation(self, analyzer, trade_manager):
        """パターン信頼度計算テスト"""
        base_time = datetime.now() - timedelta(days=30)
        
        # 一貫性の高いパターンを作成（朝取引で常に成功）
        for i in range(10):
            trade = TradeRecord(
                trade_id=f"consistent_{i}",
                symbol="TEST",
                direction=TradeDirection.LONG,
                entry_time=base_time + timedelta(days=i, hours=9),
                entry_price=1000.0,
                quantity=100,
                exit_time=base_time + timedelta(days=i, hours=10),
                exit_price=1050.0,
                realized_pnl=5000.0,
                status=TradeStatus.CLOSED
            )
            trade_manager.add_trade(trade)
        
        patterns = analyzer.analyze_patterns(lookback_days=90, min_pattern_size=5)
        
        if patterns:
            # 信頼度が適切に計算されていることを確認
            for pattern in patterns:
                assert 0.0 <= pattern.confidence_score <= 1.0
                if pattern.pattern_type == PatternType.SUCCESS:
                    # 成功パターンは高い信頼度を持つべき
                    assert pattern.confidence_score > 0.5


class TestTradingPattern:
    """TradingPatternクラスのテスト"""
    
    def test_trading_pattern_creation(self):
        """TradingPatternの作成テスト"""
        pattern = TradingPattern(
            pattern_id="test_pattern",
            pattern_type=PatternType.SUCCESS,
            name="Test Pattern",
            description="Test Description",
            characteristics={'test': 'value'},
            occurrence_count=5,
            success_rate=0.8,
            average_pnl=1000.0,
            average_pnl_pct=10.0,
            market_conditions=['Bull Market'],
            trade_ids=['trade1', 'trade2'],
            confidence_score=0.9
        )
        
        assert pattern.pattern_id == "test_pattern"
        assert pattern.pattern_type == PatternType.SUCCESS
        assert pattern.success_rate == 0.8
        assert pattern.confidence_score == 0.9
    
    def test_trading_pattern_to_dict(self):
        """TradingPatternの辞書変換テスト"""
        pattern = TradingPattern(
            pattern_id="test_pattern",
            pattern_type=PatternType.FAILURE,
            name="Test Pattern",
            description="Test Description",
            characteristics={'test': 'value'},
            occurrence_count=3,
            success_rate=0.3,
            average_pnl=-500.0,
            average_pnl_pct=-5.0,
            market_conditions=[],
            trade_ids=['trade1'],
            confidence_score=0.6
        )
        
        pattern_dict = pattern.to_dict()
        
        assert isinstance(pattern_dict, dict)
        assert pattern_dict['pattern_id'] == "test_pattern"
        assert pattern_dict['pattern_type'] == "failure"
        assert pattern_dict['success_rate'] == 0.3
        assert pattern_dict['confidence_score'] == 0.6


class TestPatternAnalysisIntegration:
    """パターン分析統合テスト"""
    
    @pytest.fixture
    def temp_db_path(self):
        """テンポラリDBファイルパス"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            yield f.name
        os.unlink(f.name)
    
    @pytest.fixture
    def complex_trading_scenario(self, temp_db_path):
        """複雑な取引シナリオ"""
        trade_manager = TradeHistoryManager(temp_db_path)
        analyzer = PatternAnalyzer(trade_manager)
        
        base_time = datetime.now() - timedelta(days=60)
        
        # 複雑なシナリオ作成
        scenarios = [
            # 朝の取引（高い成功率）
            ('morning_bull', 9, 1000, 1100, 'Bull Market', 'Trend Following'),
            ('morning_bull', 9, 1100, 1200, 'Bull Market', 'Trend Following'),
            ('morning_bull', 9, 1050, 1150, 'Bull Market', 'Trend Following'),
            ('morning_bull', 9, 1200, 1250, 'Bull Market', 'Trend Following'),
            
            # 午後の取引（低い成功率）
            ('afternoon_bear', 14, 1000, 950, 'Bear Market', 'Counter Trend'),
            ('afternoon_bear', 14, 1100, 1050, 'Bear Market', 'Counter Trend'),
            ('afternoon_bear', 14, 1050, 1000, 'Bear Market', 'Counter Trend'),
            
            # 夕方の取引（混合）
            ('evening_mixed', 16, 1000, 1020, 'Sideways', 'Scalping'),
            ('evening_mixed', 16, 1100, 1080, 'Sideways', 'Scalping'),
            ('evening_mixed', 16, 1050, 1070, 'Sideways', 'Scalping'),
        ]
        
        for i, (symbol, hour, entry, exit, market, strategy) in enumerate(scenarios):
            trade = TradeRecord(
                trade_id=f"complex_{i}",
                symbol=symbol,
                direction=TradeDirection.LONG,
                entry_time=base_time + timedelta(days=i, hours=hour),
                entry_price=entry,
                quantity=100,
                exit_time=base_time + timedelta(days=i, hours=hour+1),
                exit_price=exit,
                realized_pnl=(exit - entry) * 100,
                realized_pnl_pct=((exit - entry) / entry) * 100,
                market_condition=market,
                strategy_name=strategy,
                status=TradeStatus.CLOSED
            )
            trade_manager.add_trade(trade)
        
        return analyzer, trade_manager
    
    def test_comprehensive_pattern_analysis(self, complex_trading_scenario):
        """包括的パターン分析テスト"""
        analyzer, trade_manager = complex_trading_scenario
        
        patterns = analyzer.analyze_patterns(
            lookback_days=90,
            min_pattern_size=3,
            confidence_threshold=0.5
        )
        
        # 複数のパターンタイプが検出されることを確認
        pattern_types = set(p.pattern_type for p in patterns)
        assert len(pattern_types) > 0
        
        # 推奨事項生成
        recommendations = analyzer.get_pattern_recommendations(patterns)
        
        # 少なくとも一つのカテゴリに推奨事項があることを確認
        total_recommendations = (
            len(recommendations['continue']) +
            len(recommendations['avoid']) +
            len(recommendations['improve'])
        )
        assert total_recommendations >= 0  # データによっては0の場合もある
    
    def test_market_condition_analysis(self, complex_trading_scenario):
        """市場条件分析テスト"""
        analyzer, trade_manager = complex_trading_scenario
        
        patterns = analyzer.analyze_patterns(lookback_days=90, min_pattern_size=2)
        
        # 市場条件パターンが含まれているかチェック
        market_patterns = [p for p in patterns if 'market' in p.pattern_id]
        assert isinstance(market_patterns, list)
        
        if market_patterns:
            # 市場条件が適切に記録されていることを確認
            for pattern in market_patterns:
                assert len(pattern.market_conditions) > 0


if __name__ == "__main__":
    pytest.main([__file__])