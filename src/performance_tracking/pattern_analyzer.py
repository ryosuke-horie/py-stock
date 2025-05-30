"""
成功/失敗パターン分析モジュール

取引履歴から成功パターンと失敗パターンを自動抽出し、
投資スキル向上のための洞察を提供する
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from loguru import logger

from .trade_history_manager import TradeHistoryManager, TradeRecord, TradeStatus


class PatternType(Enum):
    """パターンタイプ"""
    SUCCESS = "success"
    FAILURE = "failure"
    NEUTRAL = "neutral"


@dataclass
class TradingPattern:
    """取引パターンデータクラス"""
    pattern_id: str
    pattern_type: PatternType
    name: str
    description: str
    
    # パターンの特徴
    characteristics: Dict[str, Any]
    
    # 統計情報
    occurrence_count: int
    success_rate: float
    average_pnl: float
    average_pnl_pct: float
    
    # 市場条件
    market_conditions: List[str]
    
    # 関連取引ID
    trade_ids: List[str]
    
    # 信頼度スコア
    confidence_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'pattern_id': self.pattern_id,
            'pattern_type': self.pattern_type.value,
            'name': self.name,
            'description': self.description,
            'characteristics': self.characteristics,
            'occurrence_count': self.occurrence_count,
            'success_rate': self.success_rate,
            'average_pnl': self.average_pnl,
            'average_pnl_pct': self.average_pnl_pct,
            'market_conditions': self.market_conditions,
            'trade_ids': self.trade_ids,
            'confidence_score': self.confidence_score
        }


class PatternAnalyzer:
    """成功/失敗パターン分析クラス"""
    
    def __init__(self, trade_manager: TradeHistoryManager):
        """
        初期化
        
        Args:
            trade_manager: 取引履歴管理インスタンス
        """
        self.trade_manager = trade_manager
        self.patterns_cache = {}
        
        logger.info("PatternAnalyzer initialized")
    
    def analyze_patterns(self, 
                        lookback_days: int = 90,
                        min_pattern_size: int = 3,
                        confidence_threshold: float = 0.7) -> List[TradingPattern]:
        """
        パターン分析実行
        
        Args:
            lookback_days: 分析対象期間（日数）
            min_pattern_size: 最小パターンサイズ
            confidence_threshold: 信頼度閾値
            
        Returns:
            発見されたパターンのリスト
        """
        try:
            # 分析対象期間の取引を取得
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)
            
            trades = self.trade_manager.get_closed_trades(
                start_date=start_date,
                end_date=end_date
            )
            
            if len(trades) < min_pattern_size:
                logger.warning(f"Not enough trades for pattern analysis: {len(trades)}")
                return []
            
            logger.info(f"Analyzing patterns for {len(trades)} trades")
            
            # パターン分析実行
            patterns = []
            
            # 1. 時間帯パターン分析
            time_patterns = self._analyze_time_patterns(trades, min_pattern_size)
            patterns.extend(time_patterns)
            
            # 2. 保有期間パターン分析
            holding_patterns = self._analyze_holding_period_patterns(trades, min_pattern_size)
            patterns.extend(holding_patterns)
            
            # 3. 市場条件パターン分析
            market_patterns = self._analyze_market_condition_patterns(trades, min_pattern_size)
            patterns.extend(market_patterns)
            
            # 4. 利確・損切りパターン分析
            exit_patterns = self._analyze_exit_patterns(trades, min_pattern_size)
            patterns.extend(exit_patterns)
            
            # 5. 戦略パターン分析
            strategy_patterns = self._analyze_strategy_patterns(trades, min_pattern_size)
            patterns.extend(strategy_patterns)
            
            # 6. 銘柄パターン分析
            symbol_patterns = self._analyze_symbol_patterns(trades, min_pattern_size)
            patterns.extend(symbol_patterns)
            
            # 信頼度でフィルタリング
            filtered_patterns = [p for p in patterns if p.confidence_score >= confidence_threshold]
            
            # 成功率でソート
            filtered_patterns.sort(key=lambda x: x.success_rate, reverse=True)
            
            logger.info(f"Found {len(filtered_patterns)} significant patterns")
            return filtered_patterns
            
        except Exception as e:
            logger.error(f"Error in pattern analysis: {e}")
            return []
    
    def _analyze_time_patterns(self, trades: List[TradeRecord], min_size: int) -> List[TradingPattern]:
        """時間帯パターン分析"""
        patterns = []
        
        try:
            # 取引を時間帯別にグループ化
            time_groups = {
                'morning': [],    # 9:00-12:00
                'afternoon': [],  # 12:00-15:00
                'late': []       # 15:00-17:00
            }
            
            for trade in trades:
                if not trade.entry_time:
                    continue
                    
                hour = trade.entry_time.hour
                if 9 <= hour < 12:
                    time_groups['morning'].append(trade)
                elif 12 <= hour < 15:
                    time_groups['afternoon'].append(trade)
                elif 15 <= hour < 17:
                    time_groups['late'].append(trade)
            
            # 各時間帯の成績を分析
            for time_period, period_trades in time_groups.items():
                if len(period_trades) < min_size:
                    continue
                
                winning_trades = [t for t in period_trades if t.realized_pnl > 0]
                success_rate = len(winning_trades) / len(period_trades)
                avg_pnl = np.mean([t.realized_pnl for t in period_trades if t.realized_pnl])
                avg_pnl_pct = np.mean([t.realized_pnl_pct for t in period_trades if t.realized_pnl_pct])
                
                # 成功・失敗の判定
                if success_rate >= 0.6 and avg_pnl > 0:
                    pattern_type = PatternType.SUCCESS
                elif success_rate <= 0.4 or avg_pnl < 0:
                    pattern_type = PatternType.FAILURE
                else:
                    pattern_type = PatternType.NEUTRAL
                
                # 信頼度計算（取引数とパフォーマンスの一貫性）
                confidence = min(1.0, len(period_trades) / 20) * (abs(success_rate - 0.5) * 2)
                
                pattern = TradingPattern(
                    pattern_id=f"time_{time_period}",
                    pattern_type=pattern_type,
                    name=f"{time_period.capitalize()} Trading Pattern",
                    description=f"{time_period}の取引において成功率{success_rate:.1%}を記録",
                    characteristics={
                        'time_period': time_period,
                        'entry_hour_range': self._get_time_range(time_period)
                    },
                    occurrence_count=len(period_trades),
                    success_rate=success_rate,
                    average_pnl=avg_pnl,
                    average_pnl_pct=avg_pnl_pct,
                    market_conditions=[],
                    trade_ids=[t.trade_id for t in period_trades],
                    confidence_score=confidence
                )
                
                patterns.append(pattern)
                
        except Exception as e:
            logger.error(f"Error in time pattern analysis: {e}")
        
        return patterns
    
    def _analyze_holding_period_patterns(self, trades: List[TradeRecord], min_size: int) -> List[TradingPattern]:
        """保有期間パターン分析"""
        patterns = []
        
        try:
            # 保有期間を計算
            holding_periods = []
            valid_trades = []
            
            for trade in trades:
                if trade.entry_time and trade.exit_time:
                    holding_hours = (trade.exit_time - trade.entry_time).total_seconds() / 3600
                    holding_periods.append(holding_hours)
                    valid_trades.append(trade)
            
            if len(valid_trades) < min_size:
                return patterns
            
            # 保有期間を分類
            holding_categories = {
                'ultra_short': (0, 1),     # 1時間以内
                'short': (1, 24),          # 1日以内
                'medium': (24, 168),       # 1週間以内
                'long': (168, float('inf')) # 1週間以上
            }
            
            for category, (min_hours, max_hours) in holding_categories.items():
                category_trades = [
                    valid_trades[i] for i, hours in enumerate(holding_periods)
                    if min_hours <= hours < max_hours
                ]
                
                if len(category_trades) < min_size:
                    continue
                
                winning_trades = [t for t in category_trades if t.realized_pnl > 0]
                success_rate = len(winning_trades) / len(category_trades)
                avg_pnl = np.mean([t.realized_pnl for t in category_trades if t.realized_pnl])
                avg_pnl_pct = np.mean([t.realized_pnl_pct for t in category_trades if t.realized_pnl_pct])
                
                # パターンタイプ判定
                if success_rate >= 0.6 and avg_pnl > 0:
                    pattern_type = PatternType.SUCCESS
                elif success_rate <= 0.4 or avg_pnl < 0:
                    pattern_type = PatternType.FAILURE
                else:
                    pattern_type = PatternType.NEUTRAL
                
                confidence = min(1.0, len(category_trades) / 15) * (abs(success_rate - 0.5) * 2)
                
                pattern = TradingPattern(
                    pattern_id=f"holding_{category}",
                    pattern_type=pattern_type,
                    name=f"{category.replace('_', ' ').title()} Holding Pattern",
                    description=f"{category}保有での成功率{success_rate:.1%}",
                    characteristics={
                        'holding_category': category,
                        'min_hours': min_hours,
                        'max_hours': max_hours if max_hours != float('inf') else None
                    },
                    occurrence_count=len(category_trades),
                    success_rate=success_rate,
                    average_pnl=avg_pnl,
                    average_pnl_pct=avg_pnl_pct,
                    market_conditions=[],
                    trade_ids=[t.trade_id for t in category_trades],
                    confidence_score=confidence
                )
                
                patterns.append(pattern)
                
        except Exception as e:
            logger.error(f"Error in holding period pattern analysis: {e}")
        
        return patterns
    
    def _analyze_market_condition_patterns(self, trades: List[TradeRecord], min_size: int) -> List[TradingPattern]:
        """市場条件パターン分析"""
        patterns = []
        
        try:
            # 市場条件別でグループ化
            condition_groups = {}
            
            for trade in trades:
                if trade.market_condition:
                    condition = trade.market_condition
                    if condition not in condition_groups:
                        condition_groups[condition] = []
                    condition_groups[condition].append(trade)
            
            for condition, condition_trades in condition_groups.items():
                if len(condition_trades) < min_size:
                    continue
                
                winning_trades = [t for t in condition_trades if t.realized_pnl > 0]
                success_rate = len(winning_trades) / len(condition_trades)
                avg_pnl = np.mean([t.realized_pnl for t in condition_trades if t.realized_pnl])
                avg_pnl_pct = np.mean([t.realized_pnl_pct for t in condition_trades if t.realized_pnl_pct])
                
                # パターンタイプ判定
                if success_rate >= 0.6 and avg_pnl > 0:
                    pattern_type = PatternType.SUCCESS
                elif success_rate <= 0.4 or avg_pnl < 0:
                    pattern_type = PatternType.FAILURE
                else:
                    pattern_type = PatternType.NEUTRAL
                
                confidence = min(1.0, len(condition_trades) / 10) * (abs(success_rate - 0.5) * 2)
                
                pattern = TradingPattern(
                    pattern_id=f"market_{condition.lower().replace(' ', '_')}",
                    pattern_type=pattern_type,
                    name=f"Market Condition: {condition}",
                    description=f"{condition}市場環境での成功率{success_rate:.1%}",
                    characteristics={
                        'market_condition': condition
                    },
                    occurrence_count=len(condition_trades),
                    success_rate=success_rate,
                    average_pnl=avg_pnl,
                    average_pnl_pct=avg_pnl_pct,
                    market_conditions=[condition],
                    trade_ids=[t.trade_id for t in condition_trades],
                    confidence_score=confidence
                )
                
                patterns.append(pattern)
                
        except Exception as e:
            logger.error(f"Error in market condition pattern analysis: {e}")
        
        return patterns
    
    def _analyze_exit_patterns(self, trades: List[TradeRecord], min_size: int) -> List[TradingPattern]:
        """利確・損切りパターン分析"""
        patterns = []
        
        try:
            # 決済理由別でグループ化
            exit_groups = {}
            
            for trade in trades:
                if trade.exit_reason:
                    reason = trade.exit_reason
                    if reason not in exit_groups:
                        exit_groups[reason] = []
                    exit_groups[reason].append(trade)
            
            for reason, reason_trades in exit_groups.items():
                if len(reason_trades) < min_size:
                    continue
                
                winning_trades = [t for t in reason_trades if t.realized_pnl > 0]
                success_rate = len(winning_trades) / len(reason_trades)
                avg_pnl = np.mean([t.realized_pnl for t in reason_trades if t.realized_pnl])
                avg_pnl_pct = np.mean([t.realized_pnl_pct for t in reason_trades if t.realized_pnl_pct])
                
                # パターンタイプ判定
                if success_rate >= 0.6 and avg_pnl > 0:
                    pattern_type = PatternType.SUCCESS
                elif success_rate <= 0.4 or avg_pnl < 0:
                    pattern_type = PatternType.FAILURE
                else:
                    pattern_type = PatternType.NEUTRAL
                
                confidence = min(1.0, len(reason_trades) / 8) * (abs(success_rate - 0.5) * 2)
                
                pattern = TradingPattern(
                    pattern_id=f"exit_{reason.lower().replace(' ', '_')}",
                    pattern_type=pattern_type,
                    name=f"Exit Pattern: {reason}",
                    description=f"{reason}による決済の成功率{success_rate:.1%}",
                    characteristics={
                        'exit_reason': reason
                    },
                    occurrence_count=len(reason_trades),
                    success_rate=success_rate,
                    average_pnl=avg_pnl,
                    average_pnl_pct=avg_pnl_pct,
                    market_conditions=[],
                    trade_ids=[t.trade_id for t in reason_trades],
                    confidence_score=confidence
                )
                
                patterns.append(pattern)
                
        except Exception as e:
            logger.error(f"Error in exit pattern analysis: {e}")
        
        return patterns
    
    def _analyze_strategy_patterns(self, trades: List[TradeRecord], min_size: int) -> List[TradingPattern]:
        """戦略パターン分析"""
        patterns = []
        
        try:
            # 戦略別でグループ化
            strategy_groups = {}
            
            for trade in trades:
                if trade.strategy_name:
                    strategy = trade.strategy_name
                    if strategy not in strategy_groups:
                        strategy_groups[strategy] = []
                    strategy_groups[strategy].append(trade)
            
            for strategy, strategy_trades in strategy_groups.items():
                if len(strategy_trades) < min_size:
                    continue
                
                winning_trades = [t for t in strategy_trades if t.realized_pnl > 0]
                success_rate = len(winning_trades) / len(strategy_trades)
                avg_pnl = np.mean([t.realized_pnl for t in strategy_trades if t.realized_pnl])
                avg_pnl_pct = np.mean([t.realized_pnl_pct for t in strategy_trades if t.realized_pnl_pct])
                
                # パターンタイプ判定
                if success_rate >= 0.6 and avg_pnl > 0:
                    pattern_type = PatternType.SUCCESS
                elif success_rate <= 0.4 or avg_pnl < 0:
                    pattern_type = PatternType.FAILURE
                else:
                    pattern_type = PatternType.NEUTRAL
                
                confidence = min(1.0, len(strategy_trades) / 12) * (abs(success_rate - 0.5) * 2)
                
                pattern = TradingPattern(
                    pattern_id=f"strategy_{strategy.lower().replace(' ', '_')}",
                    pattern_type=pattern_type,
                    name=f"Strategy: {strategy}",
                    description=f"{strategy}戦略の成功率{success_rate:.1%}",
                    characteristics={
                        'strategy_name': strategy
                    },
                    occurrence_count=len(strategy_trades),
                    success_rate=success_rate,
                    average_pnl=avg_pnl,
                    average_pnl_pct=avg_pnl_pct,
                    market_conditions=[],
                    trade_ids=[t.trade_id for t in strategy_trades],
                    confidence_score=confidence
                )
                
                patterns.append(pattern)
                
        except Exception as e:
            logger.error(f"Error in strategy pattern analysis: {e}")
        
        return patterns
    
    def _analyze_symbol_patterns(self, trades: List[TradeRecord], min_size: int) -> List[TradingPattern]:
        """銘柄パターン分析"""
        patterns = []
        
        try:
            # 銘柄別でグループ化
            symbol_groups = {}
            
            for trade in trades:
                symbol = trade.symbol
                if symbol not in symbol_groups:
                    symbol_groups[symbol] = []
                symbol_groups[symbol].append(trade)
            
            for symbol, symbol_trades in symbol_groups.items():
                if len(symbol_trades) < min_size:
                    continue
                
                winning_trades = [t for t in symbol_trades if t.realized_pnl > 0]
                success_rate = len(winning_trades) / len(symbol_trades)
                avg_pnl = np.mean([t.realized_pnl for t in symbol_trades if t.realized_pnl])
                avg_pnl_pct = np.mean([t.realized_pnl_pct for t in symbol_trades if t.realized_pnl_pct])
                
                # パターンタイプ判定
                if success_rate >= 0.6 and avg_pnl > 0:
                    pattern_type = PatternType.SUCCESS
                elif success_rate <= 0.4 or avg_pnl < 0:
                    pattern_type = PatternType.FAILURE
                else:
                    pattern_type = PatternType.NEUTRAL
                
                confidence = min(1.0, len(symbol_trades) / 8) * (abs(success_rate - 0.5) * 2)
                
                pattern = TradingPattern(
                    pattern_id=f"symbol_{symbol.replace('.', '_')}",
                    pattern_type=pattern_type,
                    name=f"Symbol: {symbol}",
                    description=f"{symbol}での取引成功率{success_rate:.1%}",
                    characteristics={
                        'symbol': symbol
                    },
                    occurrence_count=len(symbol_trades),
                    success_rate=success_rate,
                    average_pnl=avg_pnl,
                    average_pnl_pct=avg_pnl_pct,
                    market_conditions=[],
                    trade_ids=[t.trade_id for t in symbol_trades],
                    confidence_score=confidence
                )
                
                patterns.append(pattern)
                
        except Exception as e:
            logger.error(f"Error in symbol pattern analysis: {e}")
        
        return patterns
    
    def _get_time_range(self, time_period: str) -> Tuple[int, int]:
        """時間帯の範囲を取得"""
        ranges = {
            'morning': (9, 12),
            'afternoon': (12, 15),
            'late': (15, 17)
        }
        return ranges.get(time_period, (9, 17))
    
    def get_pattern_recommendations(self, patterns: List[TradingPattern]) -> Dict[str, List[str]]:
        """
        パターンベースの推奨事項を生成
        
        Args:
            patterns: 分析されたパターンリスト
            
        Returns:
            推奨事項辞書
        """
        recommendations = {
            'continue': [],  # 継続すべきパターン
            'avoid': [],     # 避けるべきパターン
            'improve': []    # 改善可能なパターン
        }
        
        try:
            for pattern in patterns:
                if pattern.pattern_type == PatternType.SUCCESS and pattern.confidence_score > 0.7:
                    recommendations['continue'].append(
                        f"{pattern.name}: {pattern.description}を継続することを推奨"
                    )
                elif pattern.pattern_type == PatternType.FAILURE and pattern.confidence_score > 0.6:
                    recommendations['avoid'].append(
                        f"{pattern.name}: {pattern.description}を避けることを推奨"
                    )
                elif pattern.pattern_type == PatternType.NEUTRAL and pattern.confidence_score > 0.5:
                    recommendations['improve'].append(
                        f"{pattern.name}: {pattern.description}の改善の余地あり"
                    )
            
        except Exception as e:
            logger.error(f"Error generating pattern recommendations: {e}")
        
        return recommendations
    
    def export_patterns(self, patterns: List[TradingPattern], output_path: str) -> bool:
        """
        パターンをJSONファイルにエクスポート
        
        Args:
            patterns: パターンリスト
            output_path: 出力ファイルパス
            
        Returns:
            成功した場合True
        """
        try:
            data = {
                'export_date': datetime.now().isoformat(),
                'patterns': [pattern.to_dict() for pattern in patterns]
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Patterns exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting patterns: {e}")
            return False