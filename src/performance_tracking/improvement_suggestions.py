"""
改善提案自動生成モジュール

取引履歴、パターン分析、投資傾向分析の結果を基に、
具体的で実行可能な改善提案を自動生成する
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger

from .trade_history_manager import TradeHistoryManager, TradeRecord
from .pattern_analyzer import PatternAnalyzer, TradingPattern, PatternType
from .tendency_analyzer import TendencyAnalyzer, InvestmentTendency, TendencyLevel


class SuggestionCategory(Enum):
    """提案カテゴリ"""
    RISK_MANAGEMENT = "risk_management"
    TIMING = "timing"
    POSITION_SIZING = "position_sizing"
    STRATEGY = "strategy"
    PSYCHOLOGY = "psychology"
    EDUCATION = "education"


class SuggestionPriority(Enum):
    """提案優先度"""
    CRITICAL = "critical"   # 緊急
    HIGH = "high"          # 高
    MEDIUM = "medium"      # 中
    LOW = "low"           # 低


@dataclass
class ImprovementSuggestion:
    """改善提案データクラス"""
    suggestion_id: str
    category: SuggestionCategory
    priority: SuggestionPriority
    
    title: str
    description: str
    
    # 具体的なアクション
    action_items: List[str]
    
    # 期待される効果
    expected_impact: str
    expected_improvement_pct: Optional[float] = None
    
    # 実装の難易度
    difficulty_level: str = "medium"  # easy, medium, hard
    
    # 実装期間の目安
    implementation_timeframe: str = "1-2週間"
    
    # 関連データ
    supporting_data: Dict[str, Any] = None
    
    # 測定可能な目標
    success_metrics: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'suggestion_id': self.suggestion_id,
            'category': self.category.value,
            'priority': self.priority.value,
            'title': self.title,
            'description': self.description,
            'action_items': self.action_items,
            'expected_impact': self.expected_impact,
            'expected_improvement_pct': self.expected_improvement_pct,
            'difficulty_level': self.difficulty_level,
            'implementation_timeframe': self.implementation_timeframe,
            'supporting_data': self.supporting_data or {},
            'success_metrics': self.success_metrics or []
        }


class ImprovementSuggestionEngine:
    """改善提案自動生成エンジン"""
    
    def __init__(self, 
                 trade_manager: TradeHistoryManager,
                 pattern_analyzer: PatternAnalyzer,
                 tendency_analyzer: TendencyAnalyzer):
        """
        初期化
        
        Args:
            trade_manager: 取引履歴管理インスタンス
            pattern_analyzer: パターン分析インスタンス
            tendency_analyzer: 投資傾向分析インスタンス
        """
        self.trade_manager = trade_manager
        self.pattern_analyzer = pattern_analyzer
        self.tendency_analyzer = tendency_analyzer
        
        logger.info("ImprovementSuggestionEngine initialized")
    
    def generate_suggestions(self, 
                           lookback_days: int = 90,
                           min_trades: int = 10) -> List[ImprovementSuggestion]:
        """
        改善提案を生成
        
        Args:
            lookback_days: 分析対象期間（日数）
            min_trades: 最小取引数
            
        Returns:
            改善提案リスト
        """
        try:
            logger.info(f"Generating improvement suggestions for {lookback_days} days")
            
            # 基礎データを取得
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)
            
            trades = self.trade_manager.get_closed_trades(
                start_date=start_date,
                end_date=end_date
            )
            
            if len(trades) < min_trades:
                logger.warning(f"Not enough trades for suggestions: {len(trades)}")
                return []
            
            # 各種分析実行
            patterns = self.pattern_analyzer.analyze_patterns(lookback_days)
            tendencies = self.tendency_analyzer.analyze_tendencies(lookback_days)
            basic_stats = self.trade_manager.calculate_basic_stats(start_date, end_date)
            
            suggestions = []
            
            # 1. リスク管理関連の提案
            risk_suggestions = self._generate_risk_management_suggestions(
                trades, tendencies, basic_stats
            )
            suggestions.extend(risk_suggestions)
            
            # 2. タイミング関連の提案
            timing_suggestions = self._generate_timing_suggestions(
                trades, patterns, tendencies
            )
            suggestions.extend(timing_suggestions)
            
            # 3. ポジションサイズ関連の提案
            sizing_suggestions = self._generate_position_sizing_suggestions(
                trades, tendencies
            )
            suggestions.extend(sizing_suggestions)
            
            # 4. 戦略関連の提案
            strategy_suggestions = self._generate_strategy_suggestions(
                trades, patterns, basic_stats
            )
            suggestions.extend(strategy_suggestions)
            
            # 5. 心理・感情管理関連の提案
            psychology_suggestions = self._generate_psychology_suggestions(
                trades, tendencies
            )
            suggestions.extend(psychology_suggestions)
            
            # 6. 学習・教育関連の提案
            education_suggestions = self._generate_education_suggestions(
                trades, patterns, tendencies, basic_stats
            )
            suggestions.extend(education_suggestions)
            
            # 優先度順にソート
            priority_order = {
                SuggestionPriority.CRITICAL: 4,
                SuggestionPriority.HIGH: 3,
                SuggestionPriority.MEDIUM: 2,
                SuggestionPriority.LOW: 1
            }
            
            suggestions.sort(key=lambda x: priority_order[x.priority], reverse=True)
            
            logger.info(f"Generated {len(suggestions)} improvement suggestions")
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating improvement suggestions: {e}")
            return []
    
    def _generate_risk_management_suggestions(self,
                                           trades: List[TradeRecord],
                                           tendencies: List[InvestmentTendency],
                                           basic_stats: Dict[str, Any]) -> List[ImprovementSuggestion]:
        """リスク管理関連の提案生成"""
        suggestions = []
        
        try:
            # 損失取引分析
            loss_trades = [t for t in trades if t.realized_pnl and t.realized_pnl < 0]
            win_rate = basic_stats.get('win_rate', 0)
            profit_factor = basic_stats.get('profit_factor', 0)
            
            # 勝率が低い場合の提案
            if win_rate < 0.5:
                suggestion = ImprovementSuggestion(
                    suggestion_id="risk_001",
                    category=SuggestionCategory.RISK_MANAGEMENT,
                    priority=SuggestionPriority.HIGH,
                    title="勝率改善のためのエントリー基準見直し",
                    description=f"現在の勝率{win_rate:.1%}を改善するため、エントリー条件を厳格化することを推奨します",
                    action_items=[
                        "テクニカル指標の組み合わせ条件を追加",
                        "エントリー前の市場環境チェックを必須化",
                        "過去の失敗パターンをエントリー除外条件に追加",
                        "バックテストによるエントリー条件の検証"
                    ],
                    expected_impact="勝率を10-15%改善し、全体的な取引成績向上が期待されます",
                    expected_improvement_pct=12.5,
                    difficulty_level="medium",
                    implementation_timeframe="2-3週間",
                    supporting_data={
                        'current_win_rate': win_rate,
                        'target_win_rate': 0.55,
                        'total_trades': len(trades)
                    },
                    success_metrics=[
                        "月次勝率55%以上の達成",
                        "エントリー条件違反の取引数を50%削減"
                    ]
                )
                suggestions.append(suggestion)
            
            # 損益比が低い場合の提案
            if profit_factor < 1.5:
                suggestion = ImprovementSuggestion(
                    suggestion_id="risk_002",
                    category=SuggestionCategory.RISK_MANAGEMENT,
                    priority=SuggestionPriority.HIGH,
                    title="損益比改善のための利確・損切り戦略最適化",
                    description=f"現在の損益比{profit_factor:.2f}を改善するため、利確と損切りの戦略を見直すことを推奨します",
                    action_items=[
                        "利確目標を現在の1.5倍に引き上げ",
                        "損切りラインをより厳格に設定（-2%以内）",
                        "トレーリングストップの導入を検討",
                        "部分利確戦略の採用（50%利確後、残りを継続保有）"
                    ],
                    expected_impact="損益比を1.8以上に改善し、収益性を大幅に向上させます",
                    expected_improvement_pct=20.0,
                    difficulty_level="medium",
                    implementation_timeframe="1-2週間",
                    supporting_data={
                        'current_profit_factor': profit_factor,
                        'target_profit_factor': 1.8,
                        'avg_win': basic_stats.get('average_win', 0),
                        'avg_loss': basic_stats.get('average_loss', 0)
                    },
                    success_metrics=[
                        "損益比1.8以上の達成",
                        "平均利益の20%増加",
                        "平均損失の15%削減"
                    ]
                )
                suggestions.append(suggestion)
            
            # ストップロス設定率が低い場合
            stop_loss_set_count = len([t for t in trades if t.stop_loss is not None])
            stop_loss_ratio = stop_loss_set_count / len(trades) if trades else 0
            
            if stop_loss_ratio < 0.8:
                suggestion = ImprovementSuggestion(
                    suggestion_id="risk_003",
                    category=SuggestionCategory.RISK_MANAGEMENT,
                    priority=SuggestionPriority.CRITICAL,
                    title="ストップロス設定の徹底",
                    description=f"ストップロス設定率{stop_loss_ratio:.1%}と低いため、全取引でのリスク管理徹底が必要です",
                    action_items=[
                        "エントリー時の必須ストップロス設定ルール制定",
                        "リスク・リワード比1:2以上の確保を必須化",
                        "自動ストップロス発注システムの活用",
                        "ストップロス未設定時のアラート機能導入"
                    ],
                    expected_impact="最大損失を制限し、破綻リスクを大幅に削減します",
                    expected_improvement_pct=30.0,
                    difficulty_level="easy",
                    implementation_timeframe="1週間",
                    supporting_data={
                        'current_stop_loss_ratio': stop_loss_ratio,
                        'target_stop_loss_ratio': 1.0,
                        'trades_without_stop_loss': len(trades) - stop_loss_set_count
                    },
                    success_metrics=[
                        "ストップロス設定率100%の達成",
                        "最大単発損失を投資資金の2%以内に制限"
                    ]
                )
                suggestions.append(suggestion)
            
        except Exception as e:
            logger.error(f"Error generating risk management suggestions: {e}")
        
        return suggestions
    
    def _generate_timing_suggestions(self,
                                   trades: List[TradeRecord],
                                   patterns: List[TradingPattern],
                                   tendencies: List[InvestmentTendency]) -> List[ImprovementSuggestion]:
        """タイミング関連の提案生成"""
        suggestions = []
        
        try:
            # 時間帯パターンの分析
            time_patterns = [p for p in patterns if 'time_' in p.pattern_id]
            
            # 最も成功率の高い時間帯を特定
            best_time_pattern = None
            worst_time_pattern = None
            
            for pattern in time_patterns:
                if pattern.pattern_type == PatternType.SUCCESS:
                    if best_time_pattern is None or pattern.success_rate > best_time_pattern.success_rate:
                        best_time_pattern = pattern
                elif pattern.pattern_type == PatternType.FAILURE:
                    if worst_time_pattern is None or pattern.success_rate < worst_time_pattern.success_rate:
                        worst_time_pattern = pattern
            
            # 成功時間帯集中の提案
            if best_time_pattern and best_time_pattern.success_rate > 0.7:
                suggestion = ImprovementSuggestion(
                    suggestion_id="timing_001",
                    category=SuggestionCategory.TIMING,
                    priority=SuggestionPriority.MEDIUM,
                    title=f"高成功率時間帯({best_time_pattern.characteristics.get('time_period', '')})への取引集中",
                    description=f"{best_time_pattern.characteristics.get('time_period', '')}時間帯で成功率{best_time_pattern.success_rate:.1%}を記録しています",
                    action_items=[
                        f"{best_time_pattern.characteristics.get('time_period', '')}時間帯での取引比率を70%以上に向上",
                        "取引時間の計画的なスケジューリング",
                        "他の時間帯での取引を段階的に削減",
                        "時間帯別パフォーマンスの継続モニタリング"
                    ],
                    expected_impact="時間帯の最適化により全体の成功率向上が期待されます",
                    expected_improvement_pct=8.0,
                    difficulty_level="easy",
                    implementation_timeframe="1週間",
                    supporting_data={
                        'best_time_period': best_time_pattern.characteristics.get('time_period', ''),
                        'success_rate': best_time_pattern.success_rate,
                        'occurrence_count': best_time_pattern.occurrence_count
                    },
                    success_metrics=[
                        f"最適時間帯での取引比率70%以上",
                        "時間帯別成功率の向上"
                    ]
                )
                suggestions.append(suggestion)
            
            # 失敗時間帯回避の提案
            if worst_time_pattern and worst_time_pattern.success_rate < 0.4:
                suggestion = ImprovementSuggestion(
                    suggestion_id="timing_002",
                    category=SuggestionCategory.TIMING,
                    priority=SuggestionPriority.HIGH,
                    title=f"低成功率時間帯({worst_time_pattern.characteristics.get('time_period', '')})の取引回避",
                    description=f"{worst_time_pattern.characteristics.get('time_period', '')}時間帯で成功率{worst_time_pattern.success_rate:.1%}と低迷しています",
                    action_items=[
                        f"{worst_time_pattern.characteristics.get('time_period', '')}時間帯での新規エントリーを制限",
                        "この時間帯は既存ポジションの監視に専念",
                        "時間帯別の取引ルール策定",
                        "パフォーマンス改善まで段階的制限を継続"
                    ],
                    expected_impact="低成功率時間帯の回避により全体パフォーマンスが改善されます",
                    expected_improvement_pct=12.0,
                    difficulty_level="easy",
                    implementation_timeframe="即時",
                    supporting_data={
                        'worst_time_period': worst_time_pattern.characteristics.get('time_period', ''),
                        'success_rate': worst_time_pattern.success_rate,
                        'occurrence_count': worst_time_pattern.occurrence_count
                    },
                    success_metrics=[
                        f"問題時間帯での取引数50%削減",
                        "全体成功率の向上"
                    ]
                )
                suggestions.append(suggestion)
            
        except Exception as e:
            logger.error(f"Error generating timing suggestions: {e}")
        
        return suggestions
    
    def _generate_position_sizing_suggestions(self,
                                            trades: List[TradeRecord],
                                            tendencies: List[InvestmentTendency]) -> List[ImprovementSuggestion]:
        """ポジションサイズ関連の提案生成"""
        suggestions = []
        
        try:
            # ポジションサイズ傾向を取得
            position_tendency = next(
                (t for t in tendencies if t.tendency_type.value == "position_sizing"),
                None
            )
            
            if not position_tendency:
                return suggestions
            
            # 一貫性が低い場合の提案
            consistency_score = position_tendency.analysis_details.get('consistency_score', 0)
            if consistency_score < 70:
                suggestion = ImprovementSuggestion(
                    suggestion_id="sizing_001",
                    category=SuggestionCategory.POSITION_SIZING,
                    priority=SuggestionPriority.HIGH,
                    title="ポジションサイズ一貫性の改善",
                    description=f"ポジションサイズの一貫性{consistency_score:.0f}%と低く、計画的な資金管理が必要です",
                    action_items=[
                        "投資資金の固定パーセンテージでのポジションサイズ決定ルール策定",
                        "リスクベースのポジションサイジング手法の導入",
                        "最大ポジションサイズの上限設定（総資金の10%以内）",
                        "ポジションサイズ計算ツールの活用"
                    ],
                    expected_impact="一貫したポジションサイズによりリスク管理が改善されます",
                    expected_improvement_pct=15.0,
                    difficulty_level="medium",
                    implementation_timeframe="2週間",
                    supporting_data={
                        'current_consistency': consistency_score,
                        'target_consistency': 85.0,
                        'avg_position_value': position_tendency.analysis_details.get('avg_position_value', 0)
                    },
                    success_metrics=[
                        "ポジションサイズ一貫性85%以上の達成",
                        "ポジションサイズ変動係数0.3以下"
                    ]
                )
                suggestions.append(suggestion)
            
            # 大きなポジションと小さなポジションの成績差がある場合
            large_avg = position_tendency.analysis_details.get('large_positions_avg_pnl', 0)
            small_avg = position_tendency.analysis_details.get('small_positions_avg_pnl', 0)
            
            if abs(large_avg - small_avg) > 2:
                better_size = "大きな" if large_avg > small_avg else "小さな"
                suggestion = ImprovementSuggestion(
                    suggestion_id="sizing_002",
                    category=SuggestionCategory.POSITION_SIZING,
                    priority=SuggestionPriority.MEDIUM,
                    title=f"最適ポジションサイズへの調整",
                    description=f"{better_size}ポジションで良好な成績を記録しています。サイズ戦略の最適化を推奨します",
                    action_items=[
                        f"{better_size}ポジションサイズでの取引比率を増加",
                        "ポジションサイズと成績の関係を詳細分析",
                        "確信度に応じたポジションサイズ調整ルールの導入",
                        "段階的なポジションサイズ最適化の実施"
                    ],
                    expected_impact="最適なポジションサイズにより収益性が向上します",
                    expected_improvement_pct=10.0,
                    difficulty_level="medium",
                    implementation_timeframe="2-3週間",
                    supporting_data={
                        'large_positions_avg': large_avg,
                        'small_positions_avg': small_avg,
                        'better_approach': better_size
                    },
                    success_metrics=[
                        f"{better_size}ポジションサイズ取引の平均成績向上",
                        "全体的な収益率の改善"
                    ]
                )
                suggestions.append(suggestion)
            
        except Exception as e:
            logger.error(f"Error generating position sizing suggestions: {e}")
        
        return suggestions
    
    def _generate_strategy_suggestions(self,
                                     trades: List[TradeRecord],
                                     patterns: List[TradingPattern],
                                     basic_stats: Dict[str, Any]) -> List[ImprovementSuggestion]:
        """戦略関連の提案生成"""
        suggestions = []
        
        try:
            # 戦略パターンの分析
            strategy_patterns = [p for p in patterns if 'strategy_' in p.pattern_id]
            
            # 最も成功した戦略
            best_strategy = None
            worst_strategy = None
            
            for pattern in strategy_patterns:
                if pattern.pattern_type == PatternType.SUCCESS:
                    if best_strategy is None or pattern.success_rate > best_strategy.success_rate:
                        best_strategy = pattern
                elif pattern.pattern_type == PatternType.FAILURE:
                    if worst_strategy is None or pattern.success_rate < worst_strategy.success_rate:
                        worst_strategy = pattern
            
            # 成功戦略の集中提案
            if best_strategy and best_strategy.occurrence_count >= 5:
                strategy_name = best_strategy.characteristics.get('strategy_name', 'Unknown')
                suggestion = ImprovementSuggestion(
                    suggestion_id="strategy_001",
                    category=SuggestionCategory.STRATEGY,
                    priority=SuggestionPriority.MEDIUM,
                    title=f"高成功率戦略({strategy_name})への集中",
                    description=f"{strategy_name}戦略で成功率{best_strategy.success_rate:.1%}の優秀な成績を記録",
                    action_items=[
                        f"{strategy_name}戦略の取引比率を70%以上に向上",
                        "戦略の成功要因を詳細分析",
                        "戦略実行のチェックリスト作成",
                        "他の戦略は段階的に縮小"
                    ],
                    expected_impact="成功率の高い戦略への集中により全体成績が向上します",
                    expected_improvement_pct=15.0,
                    difficulty_level="medium",
                    implementation_timeframe="2-3週間",
                    supporting_data={
                        'strategy_name': strategy_name,
                        'success_rate': best_strategy.success_rate,
                        'occurrence_count': best_strategy.occurrence_count
                    },
                    success_metrics=[
                        f"{strategy_name}戦略比率70%以上の達成",
                        "全体成功率の向上"
                    ]
                )
                suggestions.append(suggestion)
            
            # 失敗戦略の見直し提案
            if worst_strategy and worst_strategy.occurrence_count >= 3:
                strategy_name = worst_strategy.characteristics.get('strategy_name', 'Unknown')
                suggestion = ImprovementSuggestion(
                    suggestion_id="strategy_002",
                    category=SuggestionCategory.STRATEGY,
                    priority=SuggestionPriority.HIGH,
                    title=f"低成功率戦略({strategy_name})の見直し",
                    description=f"{strategy_name}戦略で成功率{worst_strategy.success_rate:.1%}と低迷",
                    action_items=[
                        f"{strategy_name}戦略の使用を一時停止",
                        "戦略の失敗要因を詳細分析",
                        "戦略パラメータの最適化検討",
                        "改善まで他の戦略に注力"
                    ],
                    expected_impact="低成功率戦略の停止により全体パフォーマンスが改善されます",
                    expected_improvement_pct=20.0,
                    difficulty_level="easy",
                    implementation_timeframe="即時",
                    supporting_data={
                        'strategy_name': strategy_name,
                        'success_rate': worst_strategy.success_rate,
                        'occurrence_count': worst_strategy.occurrence_count
                    },
                    success_metrics=[
                        f"{strategy_name}戦略使用頻度の削減",
                        "全体成功率の向上"
                    ]
                )
                suggestions.append(suggestion)
            
        except Exception as e:
            logger.error(f"Error generating strategy suggestions: {e}")
        
        return suggestions
    
    def _generate_psychology_suggestions(self,
                                       trades: List[TradeRecord],
                                       tendencies: List[InvestmentTendency]) -> List[ImprovementSuggestion]:
        """心理・感情管理関連の提案生成"""
        suggestions = []
        
        try:
            # 感情管理傾向を取得
            emotional_tendency = next(
                (t for t in tendencies if t.tendency_type.value == "emotional"),
                None
            )
            
            if not emotional_tendency:
                return suggestions
            
            # 感情的取引率が高い場合
            emotional_ratio = emotional_tendency.analysis_details.get('emotional_trade_ratio', 0)
            if emotional_ratio > 0.2:
                suggestion = ImprovementSuggestion(
                    suggestion_id="psychology_001",
                    category=SuggestionCategory.PSYCHOLOGY,
                    priority=SuggestionPriority.HIGH,
                    title="感情的取引の削減",
                    description=f"感情的取引率{emotional_ratio:.1%}と高く、冷静な判断の妨げになっています",
                    action_items=[
                        "取引前のクールダウン時間（30分）の設定",
                        "大きな損失後の取引休止ルール（24時間）の導入",
                        "取引日記での感情状態記録の習慣化",
                        "取引計画からの逸脱防止チェックリストの作成"
                    ],
                    expected_impact="感情的取引の削減により判断の質が向上し、成績改善が期待されます",
                    expected_improvement_pct=18.0,
                    difficulty_level="medium",
                    implementation_timeframe="2-4週間",
                    supporting_data={
                        'current_emotional_ratio': emotional_ratio,
                        'target_emotional_ratio': 0.1,
                        'revenge_trades': emotional_tendency.analysis_details.get('revenge_trades', 0)
                    },
                    success_metrics=[
                        "感情的取引率10%以下の達成",
                        "大損後の即座取引の根絶"
                    ]
                )
                suggestions.append(suggestion)
            
            # 連続損失が多い場合
            max_loss_streak = emotional_tendency.analysis_details.get('max_loss_streak', 0)
            if max_loss_streak > 4:
                suggestion = ImprovementSuggestion(
                    suggestion_id="psychology_002",
                    category=SuggestionCategory.PSYCHOLOGY,
                    priority=SuggestionPriority.MEDIUM,
                    title="連続損失時の休憩ルール導入",
                    description=f"最大連続損失{max_loss_streak}回と多く、メンタル管理の改善が必要です",
                    action_items=[
                        "3連敗後の強制休憩ルール（24時間）の導入",
                        "連敗時の戦略見直しプロセスの確立",
                        "メンタルリセット手法の習得",
                        "連敗脱出のための段階的復帰プラン作成"
                    ],
                    expected_impact="連続損失の早期遮断により大きなドローダウンを防止できます",
                    expected_improvement_pct=25.0,
                    difficulty_level="medium",
                    implementation_timeframe="1-2週間",
                    supporting_data={
                        'max_loss_streak': max_loss_streak,
                        'target_max_streak': 3
                    },
                    success_metrics=[
                        "連続損失3回以下の維持",
                        "最大ドローダウンの削減"
                    ]
                )
                suggestions.append(suggestion)
            
        except Exception as e:
            logger.error(f"Error generating psychology suggestions: {e}")
        
        return suggestions
    
    def _generate_education_suggestions(self,
                                      trades: List[TradeRecord],
                                      patterns: List[TradingPattern],
                                      tendencies: List[InvestmentTendency],
                                      basic_stats: Dict[str, Any]) -> List[ImprovementSuggestion]:
        """学習・教育関連の提案生成"""
        suggestions = []
        
        try:
            # 全体的なパフォーマンスレベルに基づく提案
            win_rate = basic_stats.get('win_rate', 0)
            profit_factor = basic_stats.get('profit_factor', 0)
            
            # 初心者レベルの場合
            if win_rate < 0.45 or profit_factor < 1.2:
                suggestion = ImprovementSuggestion(
                    suggestion_id="education_001",
                    category=SuggestionCategory.EDUCATION,
                    priority=SuggestionPriority.MEDIUM,
                    title="基礎的なテクニカル分析スキル向上",
                    description="基本的な取引スキルの向上が全体的なパフォーマンス改善に重要です",
                    action_items=[
                        "移動平均線とトレンドラインの基礎学習",
                        "サポート・レジスタンスレベルの識別練習",
                        "ローソク足パターンの習得",
                        "デモ取引での実践練習（1ヶ月間）"
                    ],
                    expected_impact="基礎スキルの向上により判断精度が改善されます",
                    expected_improvement_pct=30.0,
                    difficulty_level="easy",
                    implementation_timeframe="4-6週間",
                    supporting_data={
                        'current_win_rate': win_rate,
                        'current_profit_factor': profit_factor,
                        'skill_level': 'beginner'
                    },
                    success_metrics=[
                        "テクニカル分析理解度テスト80%以上",
                        "デモ取引での成功率50%以上"
                    ]
                )
                suggestions.append(suggestion)
            
            # 特定パターンの学習提案
            failure_patterns = [p for p in patterns if p.pattern_type == PatternType.FAILURE]
            if len(failure_patterns) >= 2:
                suggestion = ImprovementSuggestion(
                    suggestion_id="education_002",
                    category=SuggestionCategory.EDUCATION,
                    priority=SuggestionPriority.LOW,
                    title="失敗パターンの詳細分析と学習",
                    description=f"{len(failure_patterns)}個の失敗パターンが特定されました。これらの学習が重要です",
                    action_items=[
                        "各失敗パターンの詳細分析レポート作成",
                        "失敗パターン回避のためのチェックリスト作成",
                        "同様のパターンでの過去事例研究",
                        "改善策の実装と効果測定"
                    ],
                    expected_impact="失敗パターンの理解により同様の失敗を予防できます",
                    expected_improvement_pct=15.0,
                    difficulty_level="medium",
                    implementation_timeframe="3-4週間",
                    supporting_data={
                        'failure_patterns_count': len(failure_patterns),
                        'patterns': [p.name for p in failure_patterns[:3]]
                    },
                    success_metrics=[
                        "失敗パターン発生頻度50%削減",
                        "パターン認識精度の向上"
                    ]
                )
                suggestions.append(suggestion)
            
        except Exception as e:
            logger.error(f"Error generating education suggestions: {e}")
        
        return suggestions
    
    def create_improvement_plan(self, 
                              suggestions: List[ImprovementSuggestion],
                              max_concurrent_suggestions: int = 3) -> Dict[str, Any]:
        """
        改善計画作成
        
        Args:
            suggestions: 改善提案リスト
            max_concurrent_suggestions: 同時実行可能な提案数
            
        Returns:
            改善計画辞書
        """
        try:
            if not suggestions:
                return {}
            
            # 優先度とカテゴリで分類
            critical_suggestions = [s for s in suggestions if s.priority == SuggestionPriority.CRITICAL]
            high_suggestions = [s for s in suggestions if s.priority == SuggestionPriority.HIGH]
            medium_suggestions = [s for s in suggestions if s.priority == SuggestionPriority.MEDIUM]
            low_suggestions = [s for s in suggestions if s.priority == SuggestionPriority.LOW]
            
            # 実装スケジュール作成
            immediate_actions = critical_suggestions[:max_concurrent_suggestions]
            short_term_actions = high_suggestions[:max_concurrent_suggestions - len(immediate_actions)]
            medium_term_actions = medium_suggestions[:2]
            long_term_actions = low_suggestions[:1]
            
            # 期待される改善効果計算
            total_expected_improvement = 0
            implemented_suggestions = immediate_actions + short_term_actions + medium_term_actions
            
            for suggestion in implemented_suggestions:
                if suggestion.expected_improvement_pct:
                    total_expected_improvement += suggestion.expected_improvement_pct
            
            # 改善効果は累積ではなく、複合効果として計算
            total_expected_improvement = min(total_expected_improvement * 0.7, 50)  # 上限50%
            
            improvement_plan = {
                'plan_created_at': datetime.now().isoformat(),
                'total_suggestions': len(suggestions),
                'expected_improvement_pct': total_expected_improvement,
                'implementation_schedule': {
                    'immediate': [s.to_dict() for s in immediate_actions],
                    'short_term': [s.to_dict() for s in short_term_actions],
                    'medium_term': [s.to_dict() for s in medium_term_actions],
                    'long_term': [s.to_dict() for s in long_term_actions]
                },
                'category_summary': {
                    'risk_management': len([s for s in suggestions if s.category == SuggestionCategory.RISK_MANAGEMENT]),
                    'timing': len([s for s in suggestions if s.category == SuggestionCategory.TIMING]),
                    'position_sizing': len([s for s in suggestions if s.category == SuggestionCategory.POSITION_SIZING]),
                    'strategy': len([s for s in suggestions if s.category == SuggestionCategory.STRATEGY]),
                    'psychology': len([s for s in suggestions if s.category == SuggestionCategory.PSYCHOLOGY]),
                    'education': len([s for s in suggestions if s.category == SuggestionCategory.EDUCATION])
                },
                'success_metrics': list(set([
                    metric for suggestion in implemented_suggestions 
                    for metric in (suggestion.success_metrics or [])
                ]))
            }
            
            return improvement_plan
            
        except Exception as e:
            logger.error(f"Error creating improvement plan: {e}")
            return {}
    
    def export_suggestions(self, 
                         suggestions: List[ImprovementSuggestion],
                         output_path: str,
                         include_plan: bool = True) -> bool:
        """
        改善提案をJSONファイルにエクスポート
        
        Args:
            suggestions: 改善提案リスト
            output_path: 出力ファイルパス
            include_plan: 改善計画を含めるかどうか
            
        Returns:
            成功した場合True
        """
        try:
            export_data = {
                'export_date': datetime.now().isoformat(),
                'total_suggestions': len(suggestions),
                'suggestions': [s.to_dict() for s in suggestions]
            }
            
            if include_plan:
                improvement_plan = self.create_improvement_plan(suggestions)
                export_data['improvement_plan'] = improvement_plan
            
            with open(output_path, 'w', encoding='utf-8') as f:
                import json
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Suggestions exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting suggestions: {e}")
            return False