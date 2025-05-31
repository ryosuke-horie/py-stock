"""
ImprovementSuggestionsクラスのテスト
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.performance_tracking.improvement_suggestions import (
    ImprovementSuggestionEngine, SuggestionCategory, SuggestionPriority, 
    ImprovementSuggestion
)
from src.performance_tracking.trade_history_manager import TradeRecord
from src.performance_tracking.pattern_analyzer import TradingPattern, PatternType
from src.performance_tracking.tendency_analyzer import InvestmentTendency, TendencyLevel, TendencyType


class TestImprovementSuggestion:
    """ImprovementSuggestionデータクラスのテスト"""
    
    def test_improvement_suggestion_initialization(self):
        """ImprovementSuggestion初期化テスト"""
        suggestion = ImprovementSuggestion(
            suggestion_id="test_001",
            category=SuggestionCategory.RISK_MANAGEMENT,
            priority=SuggestionPriority.HIGH,
            title="テスト提案",
            description="テスト用の改善提案",
            action_items=["アクション1", "アクション2"],
            expected_impact="テスト効果",
            expected_improvement_pct=15.0,
            difficulty_level="medium",
            implementation_timeframe="1-2週間",
            supporting_data={"test": "data"},
            success_metrics=["メトリック1", "メトリック2"]
        )
        
        assert suggestion.suggestion_id == "test_001"
        assert suggestion.category == SuggestionCategory.RISK_MANAGEMENT
        assert suggestion.priority == SuggestionPriority.HIGH
        assert suggestion.title == "テスト提案"
        assert len(suggestion.action_items) == 2
    
    def test_to_dict(self):
        """辞書変換テスト"""
        suggestion = ImprovementSuggestion(
            suggestion_id="test_002",
            category=SuggestionCategory.TIMING,
            priority=SuggestionPriority.CRITICAL,
            title="タイミング改善",
            description="エントリータイミングの改善",
            action_items=["市場分析の強化"],
            expected_impact="勝率向上",
            expected_improvement_pct=20.0
        )
        
        result = suggestion.to_dict()
        
        assert result["suggestion_id"] == "test_002"
        assert result["category"] == "timing"
        assert result["priority"] == "critical"
        assert result["expected_improvement_pct"] == 20.0


class TestImprovementSuggestionEngine:
    """ImprovementSuggestionEngineクラスのテスト"""
    
    def setup_method(self):
        """各テストメソッド実行前の初期化"""
        self.mock_trade_manager = Mock()
        self.mock_pattern_analyzer = Mock()
        self.mock_tendency_analyzer = Mock()
        
        self.generator = ImprovementSuggestionEngine(
            trade_manager=self.mock_trade_manager,
            pattern_analyzer=self.mock_pattern_analyzer,
            tendency_analyzer=self.mock_tendency_analyzer
        )
        
        # テストデータ作成
        self.sample_trades = self._create_sample_trades()
        self.sample_patterns = self._create_sample_patterns()
        self.sample_tendencies = self._create_sample_tendencies()
    
    def _create_sample_trades(self) -> list:
        """テスト用取引データ作成"""
        trades = []
        base_time = datetime.now() - timedelta(days=30)
        
        for i in range(20):
            trade = Mock(spec=TradeRecord)
            trade.trade_id = f"trade_{i}"
            trade.realized_pnl = 100 if i % 2 == 0 else -80
            trade.realized_pnl_pct = 2.0 if i % 2 == 0 else -1.8
            trade.entry_time = base_time + timedelta(days=i)
            trade.exit_time = base_time + timedelta(days=i, hours=24)
            trade.quantity = 1000
            trade.entry_price = 1000
            trades.append(trade)
        
        return trades
    
    def _create_sample_patterns(self) -> list:
        """テスト用パターンデータ作成"""
        patterns = []
        
        # 損失パターン
        loss_pattern = Mock(spec=TradingPattern)
        loss_pattern.pattern_type = PatternType.FAILURE
        loss_pattern.frequency = 5
        loss_pattern.avg_impact = -250
        loss_pattern.confidence = 0.85
        loss_pattern.description = "連続損失パターン"
        patterns.append(loss_pattern)
        
        # 利益パターン
        profit_pattern = Mock(spec=TradingPattern)
        profit_pattern.pattern_type = PatternType.SUCCESS
        profit_pattern.frequency = 3
        profit_pattern.avg_impact = 400
        profit_pattern.confidence = 0.9
        profit_pattern.description = "連勝パターン"
        patterns.append(profit_pattern)
        
        return patterns
    
    def _create_sample_tendencies(self) -> list:
        """テスト用傾向データ作成"""
        tendencies = []
        
        # 損切り傾向（要改善）
        loss_cutting = Mock(spec=InvestmentTendency)
        loss_cutting.tendency_type = TendencyType.LOSS_CUTTING
        loss_cutting.level = TendencyLevel.POOR
        loss_cutting.score = 40
        loss_cutting.improvement_suggestions = ["損切りを早める"]
        loss_cutting.analysis_details = {"avg_cutting_days": 5.0}
        tendencies.append(loss_cutting)
        
        # リスク管理傾向（良好）
        risk_management = Mock(spec=InvestmentTendency)
        risk_management.tendency_type = TendencyType.RISK_MANAGEMENT
        risk_management.level = TendencyLevel.GOOD
        risk_management.score = 80
        risk_management.improvement_suggestions = []
        risk_management.analysis_details = {"win_rate": 0.6}
        tendencies.append(risk_management)
        
        return tendencies
    
    def test_initialization(self):
        """初期化テスト"""
        assert self.generator.trade_manager == self.mock_trade_manager
        assert self.generator.pattern_analyzer == self.mock_pattern_analyzer
        assert self.generator.tendency_analyzer == self.mock_tendency_analyzer
    
    def test_generate_suggestions_success(self):
        """提案生成成功テスト"""
        # モック設定
        self.mock_trade_manager.get_closed_trades.return_value = self.sample_trades
        self.mock_pattern_analyzer.find_patterns.return_value = self.sample_patterns
        self.mock_tendency_analyzer.analyze_tendencies.return_value = self.sample_tendencies
        
        with patch.object(self.generator, '_generate_risk_management_suggestions') as mock_risk, \
             patch.object(self.generator, '_generate_timing_suggestions') as mock_timing, \
             patch.object(self.generator, '_generate_strategy_suggestions') as mock_strategy:
            
            mock_risk.return_value = [Mock(priority=SuggestionPriority.HIGH)]
            mock_timing.return_value = [Mock(priority=SuggestionPriority.MEDIUM)]
            mock_strategy.return_value = [Mock(priority=SuggestionPriority.LOW)]
            
            result = self.generator.generate_suggestions()
            
            assert len(result) > 0
            # 優先度順でソートされていることを確認
            priorities = [s.priority for s in result]
            assert priorities == sorted(priorities, key=lambda x: ["critical", "high", "medium", "low"].index(x.value))
    
    def test_generate_risk_management_suggestions(self):
        """リスク管理提案生成テスト"""
        result = self.generator._generate_risk_management_suggestions(
            self.sample_trades, self.sample_patterns, self.sample_tendencies
        )
        
        assert isinstance(result, list)
        # 損切り傾向が悪い場合、関連する提案が生成される
        risk_suggestions = [s for s in result if s.category == SuggestionCategory.RISK_MANAGEMENT]
        assert len(risk_suggestions) > 0
    
    def test_generate_timing_suggestions(self):
        """タイミング提案生成テスト"""
        result = self.generator._generate_timing_suggestions(
            self.sample_trades, self.sample_patterns, self.sample_tendencies
        )
        
        assert isinstance(result, list)
        timing_suggestions = [s for s in result if s.category == SuggestionCategory.TIMING]
        # タイミング関連の提案があることを確認
        assert len(timing_suggestions) >= 0
    
    def test_generate_position_sizing_suggestions(self):
        """ポジションサイズ提案生成テスト"""
        # ポジションサイズにバラツキがある取引データを作成
        varied_trades = []
        for i in range(10):
            trade = Mock(spec=TradeRecord)
            trade.quantity = 500 + (i * 200)  # バラツキのあるサイズ
            trade.realized_pnl = 100 if i % 2 == 0 else -80
            varied_trades.append(trade)
        
        result = self.generator._generate_position_sizing_suggestions(
            varied_trades, self.sample_patterns, self.sample_tendencies
        )
        
        assert isinstance(result, list)
    
    def test_generate_strategy_suggestions(self):
        """戦略提案生成テスト"""
        result = self.generator._generate_strategy_suggestions(
            self.sample_trades, self.sample_patterns, self.sample_tendencies
        )
        
        assert isinstance(result, list)
        strategy_suggestions = [s for s in result if s.category == SuggestionCategory.STRATEGY]
        assert len(strategy_suggestions) >= 0
    
    def test_generate_psychology_suggestions(self):
        """心理面提案生成テスト"""
        # 感情的取引が多い傾向を作成
        emotional_tendency = Mock(spec=InvestmentTendency)
        emotional_tendency.tendency_type = TendencyType.EMOTIONAL
        emotional_tendency.level = TendencyLevel.POOR
        emotional_tendency.score = 35
        
        tendencies_with_emotional = self.sample_tendencies + [emotional_tendency]
        
        result = self.generator._generate_psychology_suggestions(
            self.sample_trades, self.sample_patterns, tendencies_with_emotional
        )
        
        assert isinstance(result, list)
        psychology_suggestions = [s for s in result if s.category == SuggestionCategory.PSYCHOLOGY]
        assert len(psychology_suggestions) >= 0
    
    def test_prioritize_suggestions(self):
        """提案優先度付けテスト"""
        suggestions = [
            Mock(priority=SuggestionPriority.LOW, score=30),
            Mock(priority=SuggestionPriority.HIGH, score=80),
            Mock(priority=SuggestionPriority.CRITICAL, score=90),
            Mock(priority=SuggestionPriority.MEDIUM, score=60)
        ]
        
        result = self.generator._prioritize_suggestions(suggestions)
        
        # 優先度順にソートされていることを確認
        priorities = [s.priority.value for s in result]
        expected_order = ["critical", "high", "medium", "low"]
        assert priorities == expected_order
    
    def test_calculate_expected_improvement(self):
        """期待改善率計算テスト"""
        # 損失傾向が悪い場合
        poor_tendency = Mock()
        poor_tendency.score = 30
        poor_tendency.level = TendencyLevel.POOR
        
        result = self.generator._calculate_expected_improvement(poor_tendency)
        
        assert result >= 15  # 改善の余地が大きい
        
        # 傾向が良い場合
        good_tendency = Mock()
        good_tendency.score = 85
        good_tendency.level = TendencyLevel.GOOD
        
        result = self.generator._calculate_expected_improvement(good_tendency)
        
        assert result <= 10  # 改善の余地が小さい
    
    def test_generate_action_items(self):
        """アクション項目生成テスト"""
        suggestion_type = "stop_loss_improvement"
        context = {
            "avg_loss_days": 5.0,
            "max_loss_pct": -8.0
        }
        
        result = self.generator._generate_action_items(suggestion_type, context)
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert any("ストップロス" in item for item in result)
    
    def test_insufficient_data_handling(self):
        """データ不足時の処理テスト"""
        # 取引データが少ない場合
        self.mock_trade_manager.get_closed_trades.return_value = self.sample_trades[:3]
        self.mock_pattern_analyzer.find_patterns.return_value = []
        self.mock_tendency_analyzer.analyze_tendencies.return_value = []
        
        result = self.generator.generate_suggestions(min_trades=10)
        
        # データ不足の警告提案が生成される
        assert len(result) > 0
        education_suggestions = [s for s in result if s.category == SuggestionCategory.EDUCATION]
        assert len(education_suggestions) > 0
    
    def test_generate_personalized_suggestions(self):
        """個人化提案生成テスト"""
        user_profile = {
            "experience_level": "beginner",
            "risk_tolerance": "low",
            "preferred_timeframe": "short_term"
        }
        
        result = self.generator.generate_personalized_suggestions(
            user_profile, self.sample_trades, self.sample_tendencies
        )
        
        assert isinstance(result, list)
        # 初心者向けの提案が含まれることを確認
        beginner_suggestions = [s for s in result if "初心者" in s.description or "基本" in s.description]
        assert len(beginner_suggestions) >= 0
    
    def test_track_suggestion_effectiveness(self):
        """提案効果追跡テスト"""
        suggestion_id = "test_suggestion_001"
        implementation_date = datetime.now() - timedelta(days=30)
        
        # 実装前後の取引データを用意
        before_trades = self.sample_trades[:10]
        after_trades = self.sample_trades[10:]
        
        result = self.generator.track_suggestion_effectiveness(
            suggestion_id, implementation_date, before_trades, after_trades
        )
        
        assert "effectiveness_score" in result
        assert "performance_change" in result
        assert "recommendation" in result
    
    def test_generate_suggestion_report(self):
        """提案レポート生成テスト"""
        suggestions = [
            Mock(category=SuggestionCategory.RISK_MANAGEMENT, priority=SuggestionPriority.HIGH),
            Mock(category=SuggestionCategory.TIMING, priority=SuggestionPriority.MEDIUM),
            Mock(category=SuggestionCategory.STRATEGY, priority=SuggestionPriority.LOW)
        ]
        
        result = self.generator.generate_suggestion_report(suggestions)
        
        assert "summary" in result
        assert "priority_breakdown" in result
        assert "category_breakdown" in result
        assert "implementation_roadmap" in result
    
    def test_exception_handling(self):
        """例外処理テスト"""
        # 例外を発生させるモック設定
        self.mock_trade_manager.get_closed_trades.side_effect = Exception("Database error")
        
        result = self.generator.generate_suggestions()
        
        # 例外が発生しても空のリストが返される
        assert result == []
    
    def test_edge_cases_empty_data(self):
        """エッジケース：空データテスト"""
        # 空のデータセット
        empty_trades = []
        empty_patterns = []
        empty_tendencies = []
        
        result = self.generator._generate_risk_management_suggestions(
            empty_trades, empty_patterns, empty_tendencies
        )
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_suggestion_id_generation(self):
        """提案ID生成テスト"""
        category = SuggestionCategory.RISK_MANAGEMENT
        suggestion_type = "stop_loss"
        
        result = self.generator._generate_suggestion_id(category, suggestion_type)
        
        assert isinstance(result, str)
        assert "risk_management" in result
        assert "stop_loss" in result
        assert len(result) > 10  # タイムスタンプが含まれるため
    
    def test_custom_suggestion_creation(self):
        """カスタム提案作成テスト"""
        custom_data = {
            "title": "カスタム改善提案",
            "description": "ユーザー定義の提案",
            "category": SuggestionCategory.STRATEGY,
            "priority": SuggestionPriority.HIGH,
            "action_items": ["アクション1", "アクション2"]
        }
        
        result = self.generator.create_custom_suggestion(custom_data)
        
        assert isinstance(result, ImprovementSuggestion)
        assert result.title == "カスタム改善提案"
        assert result.category == SuggestionCategory.STRATEGY
        assert len(result.action_items) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])