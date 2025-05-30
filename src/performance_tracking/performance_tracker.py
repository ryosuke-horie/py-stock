"""
パフォーマンス追跡・学習メインモジュール

投資履歴の記録、パターン分析、投資傾向分析、改善提案生成を統合し、
包括的なパフォーマンス追跡・学習機能を提供する
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import pandas as pd
import json
from pathlib import Path
from loguru import logger

from .trade_history_manager import TradeHistoryManager, TradeRecord, TradeStatus, TradeDirection
from .pattern_analyzer import PatternAnalyzer, TradingPattern
from .tendency_analyzer import TendencyAnalyzer, InvestmentTendency
from .improvement_suggestions import ImprovementSuggestionEngine, ImprovementSuggestion


@dataclass
class PerformanceReport:
    """パフォーマンスレポートデータクラス"""
    report_id: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    
    # 基本統計
    basic_statistics: Dict[str, Any]
    
    # パターン分析結果
    trading_patterns: List[TradingPattern]
    
    # 投資傾向分析結果
    investment_tendencies: List[InvestmentTendency]
    
    # 改善提案
    improvement_suggestions: List[ImprovementSuggestion]
    
    # 改善計画
    improvement_plan: Dict[str, Any]
    
    # 総合評価
    overall_performance_score: float
    performance_level: str
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'report_id': self.report_id,
            'generated_at': self.generated_at.isoformat(),
            'period_start': self.period_start.isoformat(),
            'period_end': self.period_end.isoformat(),
            'basic_statistics': self.basic_statistics,
            'trading_patterns': [p.to_dict() for p in self.trading_patterns],
            'investment_tendencies': [t.to_dict() for t in self.investment_tendencies],
            'improvement_suggestions': [s.to_dict() for s in self.improvement_suggestions],
            'improvement_plan': self.improvement_plan,
            'overall_performance_score': self.overall_performance_score,
            'performance_level': self.performance_level
        }


class PerformanceTracker:
    """パフォーマンス追跡・学習メインクラス"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初期化
        
        Args:
            db_path: データベースファイルパス
        """
        # 各コンポーネントの初期化
        self.trade_manager = TradeHistoryManager(db_path)
        self.pattern_analyzer = PatternAnalyzer(self.trade_manager)
        self.tendency_analyzer = TendencyAnalyzer(self.trade_manager)
        self.suggestion_engine = ImprovementSuggestionEngine(
            self.trade_manager,
            self.pattern_analyzer,
            self.tendency_analyzer
        )
        
        logger.info("PerformanceTracker initialized")
    
    def record_trade(self, 
                    symbol: str,
                    direction: str,  # "LONG" or "SHORT"
                    entry_price: float,
                    quantity: int,
                    strategy_name: Optional[str] = None,
                    signal_strength: Optional[float] = None,
                    signal_confidence: Optional[float] = None,
                    stop_loss: Optional[float] = None,
                    take_profit: Optional[float] = None,
                    notes: Optional[str] = None) -> str:
        """
        新しい取引を記録
        
        Args:
            symbol: 銘柄コード
            direction: 取引方向
            entry_price: エントリー価格
            quantity: 数量
            strategy_name: 戦略名
            signal_strength: シグナル強度
            signal_confidence: シグナル信頼度
            stop_loss: ストップロス価格
            take_profit: テイクプロフィット価格
            notes: メモ
            
        Returns:
            取引ID
        """
        try:
            # 入力バリデーション
            if not symbol or not symbol.strip():
                logger.error("Symbol cannot be empty")
                return ""
            
            if direction.upper() not in ["LONG", "SHORT"]:
                logger.error(f"Invalid direction: {direction}")
                return ""
                
            if entry_price <= 0:
                logger.error(f"Invalid entry price: {entry_price}")
                return ""
                
            if quantity <= 0:
                logger.error(f"Invalid quantity: {quantity}")
                return ""
            
            # ユニークな取引IDを生成（マイクロ秒を含む）
            now = datetime.now()
            trade_id = f"{symbol.strip()}_{now.strftime('%Y%m%d_%H%M%S_%f')}"
            
            # TradeRecordオブジェクト作成
            trade = TradeRecord(
                trade_id=trade_id,
                symbol=symbol.strip(),
                direction=TradeDirection.LONG if direction.upper() == "LONG" else TradeDirection.SHORT,
                entry_time=now,
                entry_price=entry_price,
                quantity=quantity,
                strategy_name=strategy_name,
                signal_strength=signal_strength,
                signal_confidence=signal_confidence,
                stop_loss=stop_loss,
                take_profit=take_profit,
                notes=notes,
                status=TradeStatus.OPEN
            )
            
            # データベースに保存
            if self.trade_manager.add_trade(trade):
                logger.info(f"Trade recorded: {trade_id}")
                return trade_id
            else:
                logger.error(f"Failed to record trade: {trade_id}")
                return ""
                
        except Exception as e:
            logger.error(f"Error recording trade: {e}")
            return ""
    
    def close_trade(self, 
                   trade_id: str,
                   exit_price: float,
                   exit_reason: str,
                   exit_commission: float = 0.0) -> bool:
        """
        取引を決済
        
        Args:
            trade_id: 取引ID
            exit_price: 決済価格
            exit_reason: 決済理由
            exit_commission: 決済手数料
            
        Returns:
            成功した場合True
        """
        try:
            success = self.trade_manager.close_trade(
                trade_id=trade_id,
                exit_price=exit_price,
                exit_reason=exit_reason,
                exit_commission=exit_commission
            )
            
            if success:
                logger.info(f"Trade closed: {trade_id}")
            else:
                logger.error(f"Failed to close trade: {trade_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error closing trade: {e}")
            return False
    
    def get_open_positions(self, symbol: Optional[str] = None) -> List[TradeRecord]:
        """
        オープンポジション取得
        
        Args:
            symbol: 銘柄フィルタ
            
        Returns:
            オープンポジションリスト
        """
        return self.trade_manager.get_open_trades(symbol)
    
    def get_trading_history(self,
                           symbol: Optional[str] = None,
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None,
                           limit: Optional[int] = None) -> List[TradeRecord]:
        """
        取引履歴取得
        
        Args:
            symbol: 銘柄フィルタ
            start_date: 開始日フィルタ
            end_date: 終了日フィルタ
            limit: 取得件数制限
            
        Returns:
            取引履歴リスト
        """
        return self.trade_manager.get_closed_trades(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
    
    def analyze_performance(self, 
                          lookback_days: int = 90,
                          min_trades: int = 10) -> PerformanceReport:
        """
        包括的なパフォーマンス分析実行
        
        Args:
            lookback_days: 分析対象期間（日数）
            min_trades: 最小取引数
            
        Returns:
            パフォーマンスレポート
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)
            
            logger.info(f"Starting performance analysis for {lookback_days} days")
            
            # 基本統計取得
            basic_stats = self.trade_manager.calculate_basic_stats(
                start_date=start_date,
                end_date=end_date
            )
            
            # パターン分析実行
            patterns = self.pattern_analyzer.analyze_patterns(
                lookback_days=lookback_days,
                min_pattern_size=max(3, min_trades // 5)
            )
            
            # 投資傾向分析実行
            tendencies = self.tendency_analyzer.analyze_tendencies(
                lookback_days=lookback_days,
                min_trades=min_trades
            )
            
            # 改善提案生成
            suggestions = self.suggestion_engine.generate_suggestions(
                lookback_days=lookback_days,
                min_trades=min_trades
            )
            
            # 改善計画作成
            improvement_plan = self.suggestion_engine.create_improvement_plan(suggestions)
            
            # 総合パフォーマンススコア計算
            overall_score, performance_level = self._calculate_overall_performance_score(
                basic_stats, patterns, tendencies
            )
            
            # レポート作成
            report_id = f"perf_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            report = PerformanceReport(
                report_id=report_id,
                generated_at=datetime.now(),
                period_start=start_date,
                period_end=end_date,
                basic_statistics=basic_stats,
                trading_patterns=patterns,
                investment_tendencies=tendencies,
                improvement_suggestions=suggestions,
                improvement_plan=improvement_plan,
                overall_performance_score=overall_score,
                performance_level=performance_level
            )
            
            logger.info(f"Performance analysis completed: {report_id}")
            return report
            
        except Exception as e:
            logger.error(f"Error in performance analysis: {e}")
            # エラー時は空のレポートを返す
            return PerformanceReport(
                report_id="error_report",
                generated_at=datetime.now(),
                period_start=start_date,
                period_end=end_date,
                basic_statistics={},
                trading_patterns=[],
                investment_tendencies=[],
                improvement_suggestions=[],
                improvement_plan={},
                overall_performance_score=0.0,
                performance_level="Unknown"
            )
    
    def _calculate_overall_performance_score(self,
                                           basic_stats: Dict[str, Any],
                                           patterns: List[TradingPattern],
                                           tendencies: List[InvestmentTendency]) -> Tuple[float, str]:
        """
        総合パフォーマンススコア計算
        
        Args:
            basic_stats: 基本統計
            patterns: パターン分析結果
            tendencies: 投資傾向分析結果
            
        Returns:
            (スコア, レベル)のタプル
        """
        try:
            score = 0.0
            
            # 基本統計からのスコア（40点）
            win_rate = basic_stats.get('win_rate', 0)
            profit_factor = basic_stats.get('profit_factor', 0)
            
            # 勝率評価（20点）
            if win_rate >= 0.6:
                score += 20
            elif win_rate >= 0.5:
                score += 15
            elif win_rate >= 0.4:
                score += 10
            else:
                score += 5
            
            # 損益比評価（20点）
            if profit_factor >= 2.0:
                score += 20
            elif profit_factor >= 1.5:
                score += 15
            elif profit_factor >= 1.2:
                score += 10
            elif profit_factor >= 1.0:
                score += 5
            
            # パターン分析からのスコア（30点）
            if patterns:
                success_patterns = [p for p in patterns if p.pattern_type.value == "success"]
                failure_patterns = [p for p in patterns if p.pattern_type.value == "failure"]
                
                pattern_score = 0
                if len(success_patterns) > len(failure_patterns):
                    pattern_score = 25
                elif len(success_patterns) == len(failure_patterns):
                    pattern_score = 15
                else:
                    pattern_score = 5
                
                # 高信頼度パターンのボーナス
                high_confidence_patterns = [p for p in success_patterns if p.confidence_score > 0.8]
                if high_confidence_patterns:
                    pattern_score += 5
                
                score += pattern_score
            
            # 投資傾向からのスコア（30点）
            if tendencies:
                tendency_scores = [t.score for t in tendencies]
                avg_tendency_score = sum(tendency_scores) / len(tendency_scores)
                tendency_score = (avg_tendency_score / 100) * 30
                score += tendency_score
            
            # レベル決定
            if score >= 85:
                level = "エキスパート"
            elif score >= 70:
                level = "上級者"
            elif score >= 55:
                level = "中級者"
            elif score >= 40:
                level = "初級者"
            else:
                level = "初心者"
            
            return score, level
            
        except Exception as e:
            logger.error(f"Error calculating overall performance score: {e}")
            return 0.0, "Unknown"
    
    def generate_monthly_report(self, 
                              year: int, 
                              month: int) -> Optional[PerformanceReport]:
        """
        月次パフォーマンスレポート生成
        
        Args:
            year: 年
            month: 月
            
        Returns:
            月次レポート
        """
        try:
            # 月の開始日と終了日を計算
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1) - timedelta(days=1)
            
            # 期間内の取引を取得
            trades = self.trade_manager.get_closed_trades(
                start_date=start_date,
                end_date=end_date
            )
            
            if len(trades) < 5:  # 最小取引数
                logger.warning(f"Not enough trades for monthly report: {len(trades)}")
                return None
            
            # 分析期間を月次レポート用に調整
            period_days = (end_date - start_date).days
            
            return self.analyze_performance(
                lookback_days=period_days,
                min_trades=3
            )
            
        except Exception as e:
            logger.error(f"Error generating monthly report: {e}")
            return None
    
    def export_report(self, 
                     report: PerformanceReport,
                     output_path: str,
                     format_type: str = "json") -> bool:
        """
        レポートをファイルにエクスポート
        
        Args:
            report: パフォーマンスレポート
            output_path: 出力ファイルパス
            format_type: 出力形式（json, csv）
            
        Returns:
            成功した場合True
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format_type.lower() == "json":
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
                    
            elif format_type.lower() == "csv":
                # 基本統計をCSVで出力
                basic_stats_df = pd.DataFrame([report.basic_statistics])
                basic_stats_df.to_csv(output_path, index=False, encoding='utf-8')
                
            else:
                logger.error(f"Unsupported format type: {format_type}")
                return False
            
            logger.info(f"Report exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting report: {e}")
            return False
    
    def get_performance_summary(self, 
                              days: int = 30) -> Dict[str, Any]:
        """
        パフォーマンスサマリー取得
        
        Args:
            days: 過去の日数
            
        Returns:
            サマリー辞書
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            basic_stats = self.trade_manager.calculate_basic_stats(
                start_date=start_date,
                end_date=end_date
            )
            
            open_trades = self.trade_manager.get_open_trades()
            
            summary = {
                'period_days': days,
                'total_trades': basic_stats.get('total_trades', 0),
                'open_positions': len(open_trades),
                'win_rate': basic_stats.get('win_rate', 0),
                'total_pnl': basic_stats.get('total_pnl', 0),
                'profit_factor': basic_stats.get('profit_factor', 0),
                'average_hold_time_hours': basic_stats.get('average_hold_time_hours', 0),
                'last_updated': datetime.now().isoformat()
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {}
    
    def backup_data(self, backup_path: Optional[str] = None) -> bool:
        """
        データのバックアップ
        
        Args:
            backup_path: バックアップファイルパス
            
        Returns:
            成功した場合True
        """
        return self.trade_manager.backup_database(backup_path)
    
    def get_learning_insights(self, 
                            lookback_days: int = 90) -> Dict[str, Any]:
        """
        学習のための洞察取得
        
        Args:
            lookback_days: 分析対象期間（日数）
            
        Returns:
            学習洞察辞書
        """
        try:
            # パフォーマンス分析実行
            report = self.analyze_performance(lookback_days)
            
            # 主要な学習ポイントを抽出
            insights = {
                'performance_level': report.performance_level,
                'overall_score': report.overall_performance_score,
                'key_strengths': [],
                'major_weaknesses': [],
                'priority_improvements': [],
                'success_patterns': [],
                'failure_patterns': []
            }
            
            # 強みと弱みを特定
            for tendency in report.investment_tendencies:
                if tendency.score >= 80:
                    insights['key_strengths'].append({
                        'area': tendency.name,
                        'score': tendency.score,
                        'description': tendency.description
                    })
                elif tendency.score <= 50:
                    insights['major_weaknesses'].append({
                        'area': tendency.name,
                        'score': tendency.score,
                        'description': tendency.description
                    })
            
            # 優先改善事項
            for suggestion in report.improvement_suggestions[:3]:  # 上位3つ
                insights['priority_improvements'].append({
                    'title': suggestion.title,
                    'category': suggestion.category.value,
                    'priority': suggestion.priority.value,
                    'expected_impact': suggestion.expected_improvement_pct
                })
            
            # 成功・失敗パターン
            for pattern in report.trading_patterns:
                pattern_info = {
                    'name': pattern.name,
                    'success_rate': pattern.success_rate,
                    'occurrence_count': pattern.occurrence_count
                }
                
                if pattern.pattern_type.value == "success":
                    insights['success_patterns'].append(pattern_info)
                elif pattern.pattern_type.value == "failure":
                    insights['failure_patterns'].append(pattern_info)
            
            return insights
            
        except Exception as e:
            logger.error(f"Error getting learning insights: {e}")
            return {}
    
    def set_performance_goals(self, goals: Dict[str, float]) -> bool:
        """
        パフォーマンス目標設定
        
        Args:
            goals: 目標辞書（win_rate, profit_factor, etc.）
            
        Returns:
            成功した場合True
        """
        try:
            # TODO: 目標をデータベースに保存する機能を実装
            # 現在はログに記録のみ
            logger.info(f"Performance goals set: {goals}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting performance goals: {e}")
            return False
    
    def check_goal_progress(self, 
                          goals: Dict[str, float],
                          days: int = 30) -> Dict[str, Any]:
        """
        目標達成状況確認
        
        Args:
            goals: 目標辞書
            days: 確認期間
            
        Returns:
            進捗辞書
        """
        try:
            current_stats = self.get_performance_summary(days)
            
            progress = {}
            for goal_name, target_value in goals.items():
                current_value = current_stats.get(goal_name, 0)
                
                if target_value > 0:
                    achievement_rate = (current_value / target_value) * 100
                else:
                    achievement_rate = 0
                
                progress[goal_name] = {
                    'target': target_value,
                    'current': current_value,
                    'achievement_rate': achievement_rate,
                    'status': 'achieved' if achievement_rate >= 100 else 'in_progress'
                }
            
            return progress
            
        except Exception as e:
            logger.error(f"Error checking goal progress: {e}")
            return {}