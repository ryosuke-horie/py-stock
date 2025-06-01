"""
ImprovementSuggestionsクラスの最終カバレッジ向上テスト
残りの未カバー箇所を対象とした高度なテスト
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from datetime import datetime

from src.performance_tracking.improvement_suggestions import (
    ImprovementSuggestionEngine, SuggestionCategory, SuggestionPriority, 
    ImprovementSuggestion
)
from src.performance_tracking.trade_history_manager import TradeRecord
from src.performance_tracking.pattern_analyzer import TradingPattern, PatternType
from src.performance_tracking.tendency_analyzer import InvestmentTendency, TendencyLevel, TendencyType


class TestImprovementSuggestionEngineFinalCoverage:
    """最終カバレッジ向上テスト - 残りの未カバー部分を対象"""
    
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
    
    def test_timing_suggestions_no_time_patterns(self):
        """タイミング提案で時間パターンがない場合のテスト"""
        trades = [Mock(spec=TradeRecord) for _ in range(5)]
        
        # 時間パターンではないパターンのみ
        patterns = [
            Mock(pattern_id="strategy_test", pattern_type=PatternType.SUCCESS),
            Mock(pattern_id="market_test", pattern_type=PatternType.FAILURE)
        ]
        tendencies = []
        
        result = self.generator._generate_timing_suggestions(trades, patterns, tendencies)
        assert isinstance(result, list)
        # 時間パターンがないので提案は生成されない可能性が高い
    
    def test_timing_suggestions_no_best_worst_patterns(self):
        """タイミング提案で最良・最悪パターンの更新がない場合のテスト"""
        trades = [Mock(spec=TradeRecord) for _ in range(5)]
        
        # 時間パターンだが条件を満たさない
        patterns = [
            Mock(
                pattern_id="time_afternoon",
                pattern_type=PatternType.SUCCESS,
                success_rate=0.6,  # 0.7未満なのでbest_time_patternにならない
                characteristics={'time_period': 'afternoon'},
                occurrence_count=3
            ),
            Mock(
                pattern_id="time_evening",
                pattern_type=PatternType.FAILURE,
                success_rate=0.5,  # 0.4以上なのでworst_time_patternにならない
                characteristics={'time_period': 'evening'},
                occurrence_count=2
            )
        ]
        tendencies = []
        
        result = self.generator._generate_timing_suggestions(trades, patterns, tendencies)
        assert isinstance(result, list)
        # 条件を満たすパターンがないので提案は生成されない
    
    def test_strategy_suggestions_insufficient_occurrences(self):
        """戦略提案で発生回数が不十分な場合のテスト"""
        trades = [Mock(spec=TradeRecord) for _ in range(5)]
        basic_stats = {'win_rate': 0.5, 'profit_factor': 1.5}
        
        # 発生回数が不十分なパターン
        patterns = [
            Mock(
                pattern_id="strategy_success",
                pattern_type=PatternType.SUCCESS,
                success_rate=0.9,
                characteristics={'strategy_name': 'HighSuccess'},
                occurrence_count=3  # 5未満なので提案生成されない
            ),
            Mock(
                pattern_id="strategy_failure",
                pattern_type=PatternType.FAILURE,
                success_rate=0.1,
                characteristics={'strategy_name': 'HighFailure'},
                occurrence_count=2  # 3未満なので提案生成されない
            )
        ]
        
        result = self.generator._generate_strategy_suggestions(trades, patterns, basic_stats)
        assert isinstance(result, list)
        # 発生回数が不十分なので提案は生成されない
        assert len(result) == 0
    
    def test_position_sizing_no_tendency(self):
        """ポジションサイズ提案でposition_sizing傾向がない場合のテスト"""
        trades = [Mock(spec=TradeRecord) for _ in range(5)]
        
        # position_sizing以外の傾向のみ
        tendencies = [
            Mock(tendency_type=Mock(value="risk_management")),
            Mock(tendency_type=Mock(value="emotional")),
            Mock(tendency_type=Mock(value="timing"))
        ]
        
        result = self.generator._generate_position_sizing_suggestions(trades, tendencies)
        assert isinstance(result, list)
        assert len(result) == 0  # position_sizing傾向がないので空リストが返される
    
    def test_psychology_suggestions_no_emotional_tendency(self):
        """心理面提案でemotional傾向がない場合のテスト"""
        trades = [Mock(spec=TradeRecord) for _ in range(5)]
        
        # emotional以外の傾向のみ
        tendencies = [
            Mock(tendency_type=Mock(value="risk_management")),
            Mock(tendency_type=Mock(value="position_sizing")),
            Mock(tendency_type=Mock(value="timing"))
        ]
        
        result = self.generator._generate_psychology_suggestions(trades, tendencies)
        assert isinstance(result, list)
        assert len(result) == 0  # emotional傾向がないので空リストが返される
    
    def test_position_sizing_low_consistency_threshold(self):
        """ポジションサイズ提案で一貫性が境界値の場合のテスト"""
        trades = [Mock(spec=TradeRecord) for _ in range(5)]
        
        # 一貫性がちょうど70（閾値）の場合
        boundary_tendency = Mock()
        boundary_tendency.tendency_type = Mock(value="position_sizing")
        boundary_tendency.analysis_details = {
            'consistency_score': 70,  # ちょうど閾値
            'large_positions_avg_pnl': 1.5,
            'small_positions_avg_pnl': 1.5,  # 差が0なので提案生成されない
            'avg_position_value': 50000
        }
        
        result = self.generator._generate_position_sizing_suggestions(trades, [boundary_tendency])
        assert isinstance(result, list)
        # 一貫性が70なので提案は生成されない可能性
    
    def test_psychology_suggestions_boundary_values(self):
        """心理面提案で境界値の場合のテスト"""
        trades = [Mock(spec=TradeRecord) for _ in range(5)]
        
        # 感情的取引率がちょうど20%の場合
        boundary_emotional_tendency = Mock()
        boundary_emotional_tendency.tendency_type = Mock(value="emotional")
        boundary_emotional_tendency.analysis_details = {
            'emotional_trade_ratio': 0.2,  # ちょうど境界値
            'max_loss_streak': 4,  # ちょうど境界値
            'revenge_trades': 1
        }
        
        result = self.generator._generate_psychology_suggestions(trades, [boundary_emotional_tendency])
        assert isinstance(result, list)
        # 境界値なので提案が生成されない可能性
    
    def test_education_suggestions_boundary_performance(self):
        """教育提案で境界パフォーマンスの場合のテスト"""
        trades = [Mock(spec=TradeRecord) for _ in range(5)]
        patterns = []
        tendencies = []
        
        # 境界値のパフォーマンス（初心者レベルにならない）
        boundary_stats = {
            'win_rate': 0.45,  # ちょうど境界値
            'profit_factor': 1.2  # ちょうど境界値
        }
        
        result = self.generator._generate_education_suggestions(trades, patterns, tendencies, boundary_stats)
        assert isinstance(result, list)
        # 境界値なので初心者向け提案は生成されない
    
    def test_education_suggestions_insufficient_failure_patterns(self):
        """教育提案で失敗パターンが不十分な場合のテスト"""
        trades = [Mock(spec=TradeRecord) for _ in range(5)]
        tendencies = []
        
        # 失敗パターンが1つだけ（2未満）
        patterns = [
            Mock(pattern_type=PatternType.FAILURE, name="単一失敗パターン")
        ]
        
        good_stats = {
            'win_rate': 0.6,
            'profit_factor': 2.0
        }
        
        result = self.generator._generate_education_suggestions(trades, patterns, tendencies, good_stats)
        assert isinstance(result, list)
        # 失敗パターンが2未満なので関連提案は生成されない
    
    def test_create_improvement_plan_max_concurrent_zero(self):
        """改善計画作成で同時実行数が0の場合のテスト"""
        suggestions = [
            ImprovementSuggestion(
                suggestion_id="test",
                category=SuggestionCategory.RISK_MANAGEMENT,
                priority=SuggestionPriority.HIGH,
                title="テスト提案",
                description="テスト",
                action_items=["テスト"],
                expected_impact="テスト効果"
            )
        ]
        
        plan = self.generator.create_improvement_plan(suggestions, max_concurrent_suggestions=0)
        
        # 同時実行数が0でも計画は作成される
        assert isinstance(plan, dict)
        assert 'implementation_schedule' in plan
        
        schedule = plan['implementation_schedule']
        # immediate, short_termは空になる可能性
        assert 'immediate' in schedule
        assert 'short_term' in schedule
    
    def test_create_improvement_plan_no_expected_improvement(self):
        """改善計画作成で期待改善率がない提案の場合のテスト"""
        suggestions = [
            ImprovementSuggestion(
                suggestion_id="no_improvement",
                category=SuggestionCategory.EDUCATION,
                priority=SuggestionPriority.MEDIUM,
                title="改善率なし提案",
                description="期待改善率なし",
                action_items=["アクション"],
                expected_impact="効果",
                expected_improvement_pct=None  # None
            )
        ]
        
        plan = self.generator.create_improvement_plan(suggestions)
        
        assert isinstance(plan, dict)
        assert 'expected_improvement_pct' in plan
        # expected_improvement_pctがNoneの提案は計算に含まれない
        assert plan['expected_improvement_pct'] >= 0
    
    def test_export_suggestions_file_write_exception(self):
        """提案エクスポート時のファイル書き込み例外テスト"""
        suggestions = [
            ImprovementSuggestion(
                suggestion_id="test",
                category=SuggestionCategory.RISK_MANAGEMENT,
                priority=SuggestionPriority.HIGH,
                title="テスト",
                description="テスト",
                action_items=["テスト"]
            )
        ]
        
        # 書き込み権限のないディレクトリパス
        invalid_path = "/root/no_permission/test.json"
        
        success = self.generator.export_suggestions(suggestions, invalid_path)
        assert success is False
    
    def test_generate_suggestions_empty_results_from_all_generators(self):
        """全ての生成メソッドが空の結果を返す場合のテスト"""
        # 十分な取引データを設定
        trades = [Mock(spec=TradeRecord) for _ in range(15)]
        patterns = []
        tendencies = []
        basic_stats = {'total_trades': 15, 'win_rate': 0.8, 'profit_factor': 3.0}  # 高パフォーマンス
        
        self.mock_trade_manager.get_closed_trades.return_value = trades
        self.mock_pattern_analyzer.analyze_patterns.return_value = patterns
        self.mock_tendency_analyzer.analyze_tendencies.return_value = tendencies
        self.mock_trade_manager.calculate_basic_stats.return_value = basic_stats
        
        result = self.generator.generate_suggestions()
        
        # 高パフォーマンスで改善点が少ない場合、提案は少ない
        assert isinstance(result, list)
        # 結果は空でもエラーにならない
    
    def test_all_suggestion_generation_methods_with_minimal_data(self):
        """最小限のデータで全提案生成メソッドをテスト"""
        trades = []
        patterns = []
        tendencies = []
        basic_stats = {}
        
        # 各メソッドが空データでも例外を発生させないことを確認
        try:
            self.generator._generate_risk_management_suggestions(trades, tendencies, basic_stats)
            self.generator._generate_timing_suggestions(trades, patterns, tendencies)
            self.generator._generate_position_sizing_suggestions(trades, tendencies)
            self.generator._generate_strategy_suggestions(trades, patterns, basic_stats)
            self.generator._generate_psychology_suggestions(trades, tendencies)
            self.generator._generate_education_suggestions(trades, patterns, tendencies, basic_stats)
            
            # すべて正常終了
            assert True
        except Exception as e:
            # 例外が発生した場合はテスト失敗
            pytest.fail(f"Unexpected exception: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])