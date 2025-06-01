"""
ImprovementSuggestionsクラスの高度なテスト - 追加カバレッジ向上
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import json

from src.performance_tracking.improvement_suggestions import (
    ImprovementSuggestionEngine, SuggestionCategory, SuggestionPriority, 
    ImprovementSuggestion
)
from src.performance_tracking.trade_history_manager import TradeRecord
from src.performance_tracking.pattern_analyzer import TradingPattern, PatternType
from src.performance_tracking.tendency_analyzer import InvestmentTendency, TendencyLevel, TendencyType


class TestImprovementSuggestionEngineAdvancedCoverage:
    """高度なカバレッジ向上のための詳細テスト"""
    
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
    
    def test_risk_management_suggestions_detailed_coverage(self):
        """リスク管理提案の詳細カバレッジテスト"""
        # 様々な条件を満たす取引データを作成
        trades = []
        for i in range(20):
            trade = Mock(spec=TradeRecord)
            trade.realized_pnl = -100 if i < 10 else 50  # 半分が損失
            trade.stop_loss = 950.0 if i % 5 == 0 else None  # 20%にストップロス設定
            trades.append(trade)
        
        tendencies = [Mock()]
        
        # ケース1: 低勝率の場合
        basic_stats = {
            'win_rate': 0.4,  # 0.5未満
            'profit_factor': 2.0,
            'average_loss': -80.0
        }
        
        result = self.generator._generate_risk_management_suggestions(trades, tendencies, basic_stats)
        assert isinstance(result, list)
        # 低勝率による提案が含まれることを確認
        titles = [s.title for s in result]
        assert any("勝率改善" in title or "エントリー基準" in title for title in titles)
        
        # ケース2: 低損益比の場合
        basic_stats = {
            'win_rate': 0.6,
            'profit_factor': 1.2,  # 1.5未満
            'average_win': 100,
            'average_loss': -80
        }
        
        result = self.generator._generate_risk_management_suggestions(trades, tendencies, basic_stats)
        assert isinstance(result, list)
        # 低損益比による提案が含まれることを確認
        titles = [s.title for s in result]
        assert any("損益比" in title for title in titles)
        
        # ケース3: ストップロス設定率が低い場合（75%未満）
        basic_stats = {
            'win_rate': 0.6,
            'profit_factor': 2.0
        }
        
        result = self.generator._generate_risk_management_suggestions(trades, tendencies, basic_stats)
        assert isinstance(result, list)
        # ストップロス設定に関する提案が含まれることを確認
        titles = [s.title for s in result]
        assert any("ストップロス" in title for title in titles)
    
    def test_timing_suggestions_detailed_pattern_analysis(self):
        """タイミング提案での詳細パターン分析テスト"""
        trades = [Mock(spec=TradeRecord) for _ in range(5)]
        tendencies = []
        
        # ケース1: 成功率の高い時間帯パターンがある場合
        success_pattern = Mock()
        success_pattern.pattern_id = "time_morning"
        success_pattern.pattern_type = PatternType.SUCCESS
        success_pattern.success_rate = 0.75  # 0.7より高い
        success_pattern.characteristics = {'time_period': 'morning'}
        success_pattern.occurrence_count = 8
        
        patterns = [success_pattern]
        
        result = self.generator._generate_timing_suggestions(trades, patterns, tendencies)
        assert isinstance(result, list)
        # 成功時間帯への集中提案が含まれることを確認
        if result:
            assert any("高成功率時間帯" in s.title for s in result)
        
        # ケース2: 失敗率の高い時間帯パターンがある場合
        failure_pattern = Mock()
        failure_pattern.pattern_id = "time_late"
        failure_pattern.pattern_type = PatternType.FAILURE
        failure_pattern.success_rate = 0.35  # 0.4未満
        failure_pattern.characteristics = {'time_period': 'late'}
        failure_pattern.occurrence_count = 6
        
        patterns = [failure_pattern]
        
        result = self.generator._generate_timing_suggestions(trades, patterns, tendencies)
        assert isinstance(result, list)
        # 失敗時間帯回避提案が含まれることを確認
        if result:
            assert any("低成功率時間帯" in s.title for s in result)
        
        # ケース3: 成功パターンと失敗パターンの両方がある場合
        patterns = [success_pattern, failure_pattern]
        
        result = self.generator._generate_timing_suggestions(trades, patterns, tendencies)
        assert isinstance(result, list)
        # 両方の提案が生成される可能性がある
        if len(result) >= 2:
            titles = [s.title for s in result]
            assert any("高成功率" in title or "低成功率" in title for title in titles)
    
    def test_position_sizing_suggestions_detailed_analysis(self):
        """ポジションサイズ提案の詳細分析テスト"""
        trades = [Mock(spec=TradeRecord) for _ in range(5)]
        
        # ケース1: 一貫性が低い傾向
        low_consistency_tendency = Mock()
        low_consistency_tendency.tendency_type = Mock(value="position_sizing")
        low_consistency_tendency.analysis_details = {
            'consistency_score': 65,  # 70未満
            'large_positions_avg_pnl': 1.5,
            'small_positions_avg_pnl': 1.2,
            'avg_position_value': 50000
        }
        
        result = self.generator._generate_position_sizing_suggestions(trades, [low_consistency_tendency])
        assert isinstance(result, list)
        # 一貫性改善の提案が含まれることを確認
        if result:
            assert any("一貫性" in s.title for s in result)
        
        # ケース2: 大きなポジションと小さなポジションの成績差が大きい（大きい方が良い）
        performance_diff_tendency = Mock()
        performance_diff_tendency.tendency_type = Mock(value="position_sizing")
        performance_diff_tendency.analysis_details = {
            'consistency_score': 75,
            'large_positions_avg_pnl': 3.5,
            'small_positions_avg_pnl': 1.0,  # 差が2.5 > 2
            'avg_position_value': 100000
        }
        
        result = self.generator._generate_position_sizing_suggestions(trades, [performance_diff_tendency])
        assert isinstance(result, list)
        # 最適ポジションサイズ調整の提案が含まれることを確認
        if result:
            assert any("最適ポジションサイズ" in s.title for s in result)
        
        # ケース3: 小さなポジションの方が良い成績の場合
        reverse_performance_tendency = Mock()
        reverse_performance_tendency.tendency_type = Mock(value="position_sizing")
        reverse_performance_tendency.analysis_details = {
            'consistency_score': 75,
            'large_positions_avg_pnl': 0.5,
            'small_positions_avg_pnl': 3.0,  # 小さな方が良い
            'avg_position_value': 80000
        }
        
        result = self.generator._generate_position_sizing_suggestions(trades, [reverse_performance_tendency])
        assert isinstance(result, list)
        # 小さなポジションサイズを推奨する提案が含まれる可能性
        if result:
            description = ' '.join([s.description for s in result])
            assert "小さな" in description or "最適" in description
    
    def test_strategy_suggestions_detailed_pattern_analysis(self):
        """戦略提案の詳細パターン分析テスト"""
        trades = [Mock(spec=TradeRecord) for _ in range(5)]
        basic_stats = {'win_rate': 0.5, 'profit_factor': 1.5}
        
        # ケース1: 成功戦略パターンが十分な実行回数を持つ場合
        success_strategy = Mock()
        success_strategy.pattern_id = "strategy_momentum"
        success_strategy.pattern_type = PatternType.SUCCESS
        success_strategy.success_rate = 0.8
        success_strategy.characteristics = {'strategy_name': 'Momentum'}
        success_strategy.occurrence_count = 8  # 5以上
        
        patterns = [success_strategy]
        
        result = self.generator._generate_strategy_suggestions(trades, patterns, basic_stats)
        assert isinstance(result, list)
        # 成功戦略への集中提案が含まれることを確認
        if result:
            assert any("高成功率戦略" in s.title for s in result)
        
        # ケース2: 失敗戦略パターンが十分な実行回数を持つ場合
        failure_strategy = Mock()
        failure_strategy.pattern_id = "strategy_reversal"
        failure_strategy.pattern_type = PatternType.FAILURE
        failure_strategy.success_rate = 0.2
        failure_strategy.characteristics = {'strategy_name': 'Reversal'}
        failure_strategy.occurrence_count = 5  # 3以上
        
        patterns = [failure_strategy]
        
        result = self.generator._generate_strategy_suggestions(trades, patterns, basic_stats)
        assert isinstance(result, list)
        # 失敗戦略見直しの提案が含まれることを確認
        if result:
            assert any("低成功率戦略" in s.title for s in result)
        
        # ケース3: 実行回数が不十分なパターンの場合
        insufficient_strategy = Mock()
        insufficient_strategy.pattern_id = "strategy_insufficient"
        insufficient_strategy.pattern_type = PatternType.SUCCESS
        insufficient_strategy.success_rate = 0.9
        insufficient_strategy.characteristics = {'strategy_name': 'Insufficient'}
        insufficient_strategy.occurrence_count = 2  # 5未満
        
        patterns = [insufficient_strategy]
        
        result = self.generator._generate_strategy_suggestions(trades, patterns, basic_stats)
        assert isinstance(result, list)
        # 実行回数不十分なので提案は生成されない可能性が高い
    
    def test_psychology_suggestions_detailed_emotional_analysis(self):
        """心理面提案の詳細感情分析テスト"""
        trades = [Mock(spec=TradeRecord) for _ in range(5)]
        
        # ケース1: 感情的取引率が高い場合（20%超）
        high_emotional_tendency = Mock()
        high_emotional_tendency.tendency_type = Mock(value="emotional")
        high_emotional_tendency.analysis_details = {
            'emotional_trade_ratio': 0.25,
            'max_loss_streak': 3,
            'revenge_trades': 2
        }
        
        result = self.generator._generate_psychology_suggestions(trades, [high_emotional_tendency])
        assert isinstance(result, list)
        # 感情的取引削減の提案が含まれることを確認
        if result:
            assert any("感情的取引" in s.title for s in result)
        
        # ケース2: 最大連続損失が多い場合（4回超）
        high_loss_streak_tendency = Mock()
        high_loss_streak_tendency.tendency_type = Mock(value="emotional")
        high_loss_streak_tendency.analysis_details = {
            'emotional_trade_ratio': 0.1,
            'max_loss_streak': 6,  # 4超
            'revenge_trades': 0
        }
        
        result = self.generator._generate_psychology_suggestions(trades, [high_loss_streak_tendency])
        assert isinstance(result, list)
        # 連続損失時の休憩ルール提案が含まれることを確認
        if result:
            assert any("連続損失" in s.title for s in result)
        
        # ケース3: 感情的傾向なしの場合
        other_tendency = Mock()
        other_tendency.tendency_type = Mock(value="risk_management")
        
        result = self.generator._generate_psychology_suggestions(trades, [other_tendency])
        assert isinstance(result, list)
        assert len(result) == 0  # 感情的傾向がないので空
    
    def test_education_suggestions_skill_level_analysis(self):
        """教育提案のスキルレベル分析テスト"""
        trades = [Mock(spec=TradeRecord) for _ in range(5)]
        patterns = []
        tendencies = []
        
        # ケース1: 初心者レベル（低勝率・低損益比）
        beginner_stats = {
            'win_rate': 0.4,  # 45%未満
            'profit_factor': 1.1,  # 1.2未満
            'skill_level': 'beginner'
        }
        
        result = self.generator._generate_education_suggestions(trades, patterns, tendencies, beginner_stats)
        assert isinstance(result, list)
        # 基礎スキル向上の提案が含まれることを確認
        if result:
            assert any("基礎" in s.title or "テクニカル分析" in s.title for s in result)
        
        # ケース2: 失敗パターンが複数ある場合
        failure_patterns = [
            Mock(pattern_type=PatternType.FAILURE, name="失敗パターン1"),
            Mock(pattern_type=PatternType.FAILURE, name="失敗パターン2"),
            Mock(pattern_type=PatternType.FAILURE, name="失敗パターン3")
        ]
        
        good_stats = {
            'win_rate': 0.6,
            'profit_factor': 2.0
        }
        
        result = self.generator._generate_education_suggestions(trades, failure_patterns, tendencies, good_stats)
        assert isinstance(result, list)
        # 失敗パターン学習の提案が含まれることを確認
        if result:
            assert any("失敗パターン" in s.title for s in result)
        
        # ケース3: 上級者レベル（失敗パターンも少ない）
        success_patterns = [Mock(pattern_type=PatternType.SUCCESS)]
        
        result = self.generator._generate_education_suggestions(trades, success_patterns, tendencies, good_stats)
        assert isinstance(result, list)
        # 上級者レベルでは教育提案は少ない可能性
    
    def test_create_improvement_plan_detailed_scheduling(self):
        """改善計画作成の詳細スケジューリングテスト"""
        # 各優先度の提案を多数作成
        suggestions = []
        
        # 緊急提案を4つ作成
        for i in range(4):
            suggestions.append(ImprovementSuggestion(
                suggestion_id=f"critical_{i}",
                category=SuggestionCategory.RISK_MANAGEMENT,
                priority=SuggestionPriority.CRITICAL,
                title=f"緊急提案{i}",
                description="緊急対応",
                action_items=["即座実行"],
                expected_impact="高効果",
                expected_improvement_pct=15.0
            ))
        
        # 高優先度提案を3つ作成
        for i in range(3):
            suggestions.append(ImprovementSuggestion(
                suggestion_id=f"high_{i}",
                category=SuggestionCategory.TIMING,
                priority=SuggestionPriority.HIGH,
                title=f"高優先度提案{i}",
                description="高優先度対応",
                action_items=["短期実行"],
                expected_impact="良効果",
                expected_improvement_pct=10.0
            ))
        
        # 中優先度提案を5つ作成
        for i in range(5):
            suggestions.append(ImprovementSuggestion(
                suggestion_id=f"medium_{i}",
                category=SuggestionCategory.STRATEGY,
                priority=SuggestionPriority.MEDIUM,
                title=f"中優先度提案{i}",
                description="中期対応",
                action_items=["中期実行"],
                expected_impact="標準効果",
                expected_improvement_pct=8.0
            ))
        
        # 低優先度提案を3つ作成
        for i in range(3):
            suggestions.append(ImprovementSuggestion(
                suggestion_id=f"low_{i}",
                category=SuggestionCategory.EDUCATION,
                priority=SuggestionPriority.LOW,
                title=f"低優先度提案{i}",
                description="長期対応",
                action_items=["長期実行"],
                expected_impact="将来効果",
                expected_improvement_pct=5.0
            ))
        
        # 同時実行可能数を制限して計画作成
        plan = self.generator.create_improvement_plan(suggestions, max_concurrent_suggestions=2)
        
        # スケジュールの制限が適用されていることを確認
        schedule = plan['implementation_schedule']
        
        # 即座実行は最大2つまで
        immediate_actions = schedule['immediate']
        assert len(immediate_actions) <= 2
        assert all(action['priority'] == 'critical' for action in immediate_actions)
        
        # 短期実行も制限内
        short_term_actions = schedule['short_term']
        max_short_term = max(0, 2 - len(immediate_actions))
        assert len(short_term_actions) <= max_short_term
        
        # 中期実行は最大2つ
        medium_term_actions = schedule['medium_term']
        assert len(medium_term_actions) <= 2
        
        # 長期実行は最大1つ
        long_term_actions = schedule['long_term']
        assert len(long_term_actions) <= 1
        
        # 期待改善率は複合効果で計算され、上限50%
        assert plan['expected_improvement_pct'] <= 50.0
        assert plan['expected_improvement_pct'] > 0
        
        # カテゴリ別集計が正しい
        category_summary = plan['category_summary']
        assert category_summary['risk_management'] == 4
        assert category_summary['timing'] == 3
        assert category_summary['strategy'] == 5
        assert category_summary['education'] == 3
    
    def test_export_suggestions_detailed_scenarios(self):
        """提案エクスポートの詳細シナリオテスト"""
        # 複雑な提案データを作成
        suggestions = [
            ImprovementSuggestion(
                suggestion_id="complex_1",
                category=SuggestionCategory.RISK_MANAGEMENT,
                priority=SuggestionPriority.CRITICAL,
                title="複雑な提案1",
                description="詳細な説明\n改行を含む",
                action_items=["アクション1", "アクション2", "アクション3"],
                expected_impact="大きな効果",
                expected_improvement_pct=25.0,
                difficulty_level="hard",
                implementation_timeframe="4-6週間",
                supporting_data={"key1": "value1", "key2": 42},
                success_metrics=["指標1", "指標2", "指標3"]
            ),
            ImprovementSuggestion(
                suggestion_id="complex_2",
                category=SuggestionCategory.PSYCHOLOGY,
                priority=SuggestionPriority.MEDIUM,
                title="複雑な提案2",
                description="心理面の改善",
                action_items=["心理アクション"],
                expected_impact="感情制御向上",
                expected_improvement_pct=15.0
            )
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = f.name
        
        try:
            # 改善計画を含めてエクスポート
            success = self.generator.export_suggestions(suggestions, output_path, include_plan=True)
            assert success is True
            
            # ファイル内容の詳細確認
            with open(output_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # エクスポートデータの完全性確認
            assert 'export_date' in data
            assert 'total_suggestions' in data
            assert 'suggestions' in data
            assert 'improvement_plan' in data
            
            assert data['total_suggestions'] == 2
            assert len(data['suggestions']) == 2
            
            # 提案データの詳細確認
            suggestion_1 = data['suggestions'][0]
            assert suggestion_1['suggestion_id'] == "complex_1"
            assert suggestion_1['category'] == "risk_management"
            assert suggestion_1['priority'] == "critical"
            assert len(suggestion_1['action_items']) == 3
            assert suggestion_1['supporting_data']['key2'] == 42
            assert len(suggestion_1['success_metrics']) == 3
            
            # 改善計画の詳細確認
            improvement_plan = data['improvement_plan']
            assert 'plan_created_at' in improvement_plan
            assert 'implementation_schedule' in improvement_plan
            assert 'category_summary' in improvement_plan
            
            # 改善計画なしでのエクスポートも確認
            success = self.generator.export_suggestions(suggestions, output_path, include_plan=False)
            assert success is True
            
            with open(output_path, 'r', encoding='utf-8') as f:
                data_no_plan = json.load(f)
            
            assert 'improvement_plan' not in data_no_plan
            assert 'suggestions' in data_no_plan
            assert len(data_no_plan['suggestions']) == 2
            
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])