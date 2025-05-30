"""
個人投資傾向分析モジュール

個人の投資行動パターンを分析し、損切りが遅い、利確が早いなどの
投資傾向を特定し、改善点を提案する
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from scipy import stats
from loguru import logger

from .trade_history_manager import TradeHistoryManager, TradeRecord, TradeStatus


class TendencyType(Enum):
    """投資傾向タイプ"""
    LOSS_CUTTING = "loss_cutting"          # 損切り傾向
    PROFIT_TAKING = "profit_taking"        # 利確傾向
    RISK_MANAGEMENT = "risk_management"    # リスク管理傾向
    TIMING = "timing"                      # タイミング傾向
    POSITION_SIZING = "position_sizing"    # ポジションサイズ傾向
    EMOTIONAL = "emotional"                # 感情的傾向


class TendencyLevel(Enum):
    """傾向レベル"""
    EXCELLENT = "excellent"    # 優秀
    GOOD = "good"             # 良好
    AVERAGE = "average"       # 平均的
    POOR = "poor"             # 要改善
    VERY_POOR = "very_poor"   # 大幅改善必要


@dataclass
class InvestmentTendency:
    """投資傾向データクラス"""
    tendency_type: TendencyType
    level: TendencyLevel
    score: float  # 0-100のスコア
    
    name: str
    description: str
    
    # 統計データ
    current_value: float
    benchmark_value: float
    percentile: float  # 同期間のトレーダーとの比較（0-100）
    
    # 傾向の詳細分析
    analysis_details: Dict[str, Any]
    
    # 改善提案
    improvement_suggestions: List[str]
    
    # 関連取引
    supporting_trades: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'tendency_type': self.tendency_type.value,
            'level': self.level.value,
            'score': self.score,
            'name': self.name,
            'description': self.description,
            'current_value': self.current_value,
            'benchmark_value': self.benchmark_value,
            'percentile': self.percentile,
            'analysis_details': self.analysis_details,
            'improvement_suggestions': self.improvement_suggestions,
            'supporting_trades': self.supporting_trades
        }


class TendencyAnalyzer:
    """個人投資傾向分析クラス"""
    
    def __init__(self, trade_manager: TradeHistoryManager):
        """
        初期化
        
        Args:
            trade_manager: 取引履歴管理インスタンス
        """
        self.trade_manager = trade_manager
        
        # ベンチマーク値（一般的な投資家の平均値）
        self.benchmarks = {
            'loss_cutting_speed': 2.5,  # 損切りまでの平均日数
            'profit_taking_speed': 3.0,  # 利確までの平均日数
            'win_rate': 0.55,           # 勝率
            'profit_factor': 1.5,       # 損益比
            'avg_loss_pct': -2.5,       # 平均損失率(%)
            'avg_win_pct': 4.0,         # 平均利益率(%)
            'position_consistency': 0.8, # ポジションサイズ一貫性
            'emotional_trades_ratio': 0.15  # 感情的取引の割合
        }
        
        logger.info("TendencyAnalyzer initialized")
    
    def analyze_tendencies(self, 
                          lookback_days: int = 90,
                          min_trades: int = 10) -> List[InvestmentTendency]:
        """
        投資傾向分析実行
        
        Args:
            lookback_days: 分析対象期間（日数）
            min_trades: 最小取引数
            
        Returns:
            分析された投資傾向リスト
        """
        try:
            # 分析対象期間の取引を取得
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)
            
            trades = self.trade_manager.get_closed_trades(
                start_date=start_date,
                end_date=end_date
            )
            
            if len(trades) < min_trades:
                logger.warning(f"Not enough trades for tendency analysis: {len(trades)}")
                return []
            
            logger.info(f"Analyzing tendencies for {len(trades)} trades")
            
            tendencies = []
            
            # 1. 損切り傾向分析
            loss_cutting_tendency = self._analyze_loss_cutting_tendency(trades)
            if loss_cutting_tendency:
                tendencies.append(loss_cutting_tendency)
            
            # 2. 利確傾向分析
            profit_taking_tendency = self._analyze_profit_taking_tendency(trades)
            if profit_taking_tendency:
                tendencies.append(profit_taking_tendency)
            
            # 3. リスク管理傾向分析
            risk_management_tendency = self._analyze_risk_management_tendency(trades)
            if risk_management_tendency:
                tendencies.append(risk_management_tendency)
            
            # 4. タイミング傾向分析
            timing_tendency = self._analyze_timing_tendency(trades)
            if timing_tendency:
                tendencies.append(timing_tendency)
            
            # 5. ポジションサイズ傾向分析
            position_sizing_tendency = self._analyze_position_sizing_tendency(trades)
            if position_sizing_tendency:
                tendencies.append(position_sizing_tendency)
            
            # 6. 感情的取引傾向分析
            emotional_tendency = self._analyze_emotional_tendency(trades)
            if emotional_tendency:
                tendencies.append(emotional_tendency)
            
            # スコア順にソート
            tendencies.sort(key=lambda x: x.score, reverse=True)
            
            logger.info(f"Analyzed {len(tendencies)} investment tendencies")
            return tendencies
            
        except Exception as e:
            logger.error(f"Error in tendency analysis: {e}")
            return []
    
    def _analyze_loss_cutting_tendency(self, trades: List[TradeRecord]) -> Optional[InvestmentTendency]:
        """損切り傾向分析"""
        try:
            # 損失取引を抽出
            loss_trades = [t for t in trades if t.realized_pnl and t.realized_pnl < 0]
            
            if len(loss_trades) < 3:
                return None
            
            # 損切りまでの時間を計算
            loss_cutting_times = []
            quick_cuts = 0
            slow_cuts = 0
            
            for trade in loss_trades:
                if trade.entry_time and trade.exit_time:
                    hold_hours = (trade.exit_time - trade.entry_time).total_seconds() / 3600
                    loss_cutting_times.append(hold_hours)
                    
                    if hold_hours <= 24:  # 1日以内
                        quick_cuts += 1
                    elif hold_hours >= 168:  # 1週間以上
                        slow_cuts += 1
            
            if not loss_cutting_times:
                return None
            
            avg_loss_cutting_hours = np.mean(loss_cutting_times)
            avg_loss_cutting_days = avg_loss_cutting_hours / 24
            
            # 平均損失率
            avg_loss_pct = np.mean([t.realized_pnl_pct for t in loss_trades if t.realized_pnl_pct])
            
            # ベンチマークとの比較
            benchmark_days = self.benchmarks['loss_cutting_speed']
            speed_ratio = avg_loss_cutting_days / benchmark_days
            
            # スコア計算（早い損切りほど高スコア）
            if speed_ratio <= 0.5:
                score = 95
                level = TendencyLevel.EXCELLENT
            elif speed_ratio <= 0.8:
                score = 85
                level = TendencyLevel.GOOD
            elif speed_ratio <= 1.2:
                score = 70
                level = TendencyLevel.AVERAGE
            elif speed_ratio <= 2.0:
                score = 50
                level = TendencyLevel.POOR
            else:
                score = 30
                level = TendencyLevel.VERY_POOR
            
            # 改善提案生成
            suggestions = []
            if speed_ratio > 1.5:
                suggestions.append("損切りタイミングが遅い傾向があります。事前にストップロスを設定することを推奨します")
            if avg_loss_pct < -5:
                suggestions.append("平均損失が大きすぎます。より厳格な損切りルールの設定を検討してください")
            if slow_cuts / len(loss_trades) > 0.3:
                suggestions.append("長期保有での損失が多いです。ポジション見直しの頻度を増やすことを推奨します")
            
            description = f"平均損切り期間{avg_loss_cutting_days:.1f}日、平均損失率{avg_loss_pct:.1f}%"
            
            return InvestmentTendency(
                tendency_type=TendencyType.LOSS_CUTTING,
                level=level,
                score=score,
                name="損切り傾向",
                description=description,
                current_value=avg_loss_cutting_days,
                benchmark_value=benchmark_days,
                percentile=self._calculate_percentile(speed_ratio, [0.5, 0.8, 1.2, 2.0]),
                analysis_details={
                    'avg_cutting_days': avg_loss_cutting_days,
                    'avg_loss_pct': avg_loss_pct,
                    'quick_cuts_ratio': quick_cuts / len(loss_trades),
                    'slow_cuts_ratio': slow_cuts / len(loss_trades),
                    'total_loss_trades': len(loss_trades)
                },
                improvement_suggestions=suggestions,
                supporting_trades=[t.trade_id for t in loss_trades[-5:]]  # 最新5件
            )
            
        except Exception as e:
            logger.error(f"Error in loss cutting tendency analysis: {e}")
            return None
    
    def _analyze_profit_taking_tendency(self, trades: List[TradeRecord]) -> Optional[InvestmentTendency]:
        """利確傾向分析"""
        try:
            # 利益取引を抽出
            profit_trades = [t for t in trades if t.realized_pnl and t.realized_pnl > 0]
            
            if len(profit_trades) < 3:
                return None
            
            # 利確までの時間を計算
            profit_taking_times = []
            quick_takes = 0
            patient_takes = 0
            
            for trade in profit_trades:
                if trade.entry_time and trade.exit_time:
                    hold_hours = (trade.exit_time - trade.entry_time).total_seconds() / 3600
                    profit_taking_times.append(hold_hours)
                    
                    if hold_hours <= 6:  # 6時間以内
                        quick_takes += 1
                    elif hold_hours >= 72:  # 3日以上
                        patient_takes += 1
            
            if not profit_taking_times:
                return None
            
            avg_profit_taking_hours = np.mean(profit_taking_times)
            avg_profit_taking_days = avg_profit_taking_hours / 24
            
            # 平均利益率
            avg_profit_pct = np.mean([t.realized_pnl_pct for t in profit_trades if t.realized_pnl_pct])
            
            # ベンチマークとの比較
            benchmark_days = self.benchmarks['profit_taking_speed']
            patience_ratio = avg_profit_taking_days / benchmark_days
            
            # スコア計算（適度な忍耐力が高スコア）
            if 0.8 <= patience_ratio <= 1.5:
                score = 90
                level = TendencyLevel.EXCELLENT
            elif 0.5 <= patience_ratio <= 2.0:
                score = 80
                level = TendencyLevel.GOOD
            elif patience_ratio < 0.5:
                score = 60  # 利確が早すぎる
                level = TendencyLevel.AVERAGE
            elif patience_ratio < 3.0:
                score = 50
                level = TendencyLevel.POOR
            else:
                score = 30
                level = TendencyLevel.VERY_POOR
            
            # 改善提案生成
            suggestions = []
            if patience_ratio < 0.5:
                suggestions.append("利確が早すぎる傾向があります。利益を伸ばす機会を逃している可能性があります")
            if avg_profit_pct < 2:
                suggestions.append("平均利益率が低いです。利確目標の見直しを推奨します")
            if quick_takes / len(profit_trades) > 0.5:
                suggestions.append("短時間での利確が多いです。より大きな利益を狙う戦略も検討してください")
            
            description = f"平均利確期間{avg_profit_taking_days:.1f}日、平均利益率{avg_profit_pct:.1f}%"
            
            return InvestmentTendency(
                tendency_type=TendencyType.PROFIT_TAKING,
                level=level,
                score=score,
                name="利確傾向",
                description=description,
                current_value=avg_profit_taking_days,
                benchmark_value=benchmark_days,
                percentile=self._calculate_percentile(patience_ratio, [0.5, 0.8, 1.5, 2.0]),
                analysis_details={
                    'avg_taking_days': avg_profit_taking_days,
                    'avg_profit_pct': avg_profit_pct,
                    'quick_takes_ratio': quick_takes / len(profit_trades),
                    'patient_takes_ratio': patient_takes / len(profit_trades),
                    'total_profit_trades': len(profit_trades)
                },
                improvement_suggestions=suggestions,
                supporting_trades=[t.trade_id for t in profit_trades[-5:]]  # 最新5件
            )
            
        except Exception as e:
            logger.error(f"Error in profit taking tendency analysis: {e}")
            return None
    
    def _analyze_risk_management_tendency(self, trades: List[TradeRecord]) -> Optional[InvestmentTendency]:
        """リスク管理傾向分析"""
        try:
            valid_trades = [t for t in trades if t.realized_pnl is not None]
            
            if len(valid_trades) < 5:
                return None
            
            # 基本統計
            winning_trades = [t for t in valid_trades if t.realized_pnl > 0]
            losing_trades = [t for t in valid_trades if t.realized_pnl < 0]
            
            win_rate = len(winning_trades) / len(valid_trades)
            
            # 損益比計算
            avg_win = np.mean([t.realized_pnl for t in winning_trades]) if winning_trades else 0
            avg_loss = abs(np.mean([t.realized_pnl for t in losing_trades])) if losing_trades else 1
            profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
            
            # ストップロス設定率
            stop_loss_set_trades = [t for t in valid_trades if t.stop_loss is not None]
            stop_loss_ratio = len(stop_loss_set_trades) / len(valid_trades)
            
            # 最大連続損失
            max_consecutive_losses = self._calculate_max_consecutive_losses(valid_trades)
            
            # ドローダウン計算
            cumulative_pnl = np.cumsum([t.realized_pnl for t in valid_trades])
            running_max = np.maximum.accumulate(cumulative_pnl)
            drawdown = cumulative_pnl - running_max
            max_drawdown_pct = (np.min(drawdown) / np.max(running_max)) * 100 if np.max(running_max) > 0 else 0
            
            # リスク管理スコア計算
            score = 0
            
            # 勝率評価（30点）
            if win_rate >= 0.6:
                score += 30
            elif win_rate >= 0.5:
                score += 25
            elif win_rate >= 0.4:
                score += 15
            else:
                score += 5
            
            # 損益比評価（30点）
            if profit_factor >= 2.0:
                score += 30
            elif profit_factor >= 1.5:
                score += 25
            elif profit_factor >= 1.2:
                score += 15
            elif profit_factor >= 1.0:
                score += 10
            else:
                score += 0
            
            # ストップロス設定率評価（20点）
            if stop_loss_ratio >= 0.8:
                score += 20
            elif stop_loss_ratio >= 0.6:
                score += 15
            elif stop_loss_ratio >= 0.4:
                score += 10
            else:
                score += 5
            
            # ドローダウン評価（20点）
            if abs(max_drawdown_pct) <= 5:
                score += 20
            elif abs(max_drawdown_pct) <= 10:
                score += 15
            elif abs(max_drawdown_pct) <= 20:
                score += 10
            else:
                score += 5
            
            # レベル決定
            if score >= 85:
                level = TendencyLevel.EXCELLENT
            elif score >= 70:
                level = TendencyLevel.GOOD
            elif score >= 55:
                level = TendencyLevel.AVERAGE
            elif score >= 40:
                level = TendencyLevel.POOR
            else:
                level = TendencyLevel.VERY_POOR
            
            # 改善提案生成
            suggestions = []
            if win_rate < 0.5:
                suggestions.append("勝率が低いです。エントリー条件の見直しを推奨します")
            if profit_factor < 1.5:
                suggestions.append("損益比が低いです。利確目標を高く、損切りを早くすることを検討してください")
            if stop_loss_ratio < 0.7:
                suggestions.append("ストップロス設定率が低いです。全ての取引でリスク管理を徹底してください")
            if abs(max_drawdown_pct) > 15:
                suggestions.append("最大ドローダウンが大きいです。ポジションサイズの見直しを推奨します")
            
            description = f"勝率{win_rate:.1%}、損益比{profit_factor:.2f}、最大DD{max_drawdown_pct:.1f}%"
            
            return InvestmentTendency(
                tendency_type=TendencyType.RISK_MANAGEMENT,
                level=level,
                score=score,
                name="リスク管理",
                description=description,
                current_value=score,
                benchmark_value=70,
                percentile=self._calculate_percentile(score, [40, 55, 70, 85]),
                analysis_details={
                    'win_rate': win_rate,
                    'profit_factor': profit_factor,
                    'stop_loss_ratio': stop_loss_ratio,
                    'max_drawdown_pct': max_drawdown_pct,
                    'max_consecutive_losses': max_consecutive_losses,
                    'total_trades': len(valid_trades)
                },
                improvement_suggestions=suggestions,
                supporting_trades=[t.trade_id for t in valid_trades[-10:]]  # 最新10件
            )
            
        except Exception as e:
            logger.error(f"Error in risk management tendency analysis: {e}")
            return None
    
    def _analyze_timing_tendency(self, trades: List[TradeRecord]) -> Optional[InvestmentTendency]:
        """タイミング傾向分析"""
        try:
            valid_trades = [t for t in trades if t.entry_time and t.realized_pnl is not None]
            
            if len(valid_trades) < 5:
                return None
            
            # 時間帯別成績
            time_performance = {
                'morning': [],    # 9:00-12:00
                'afternoon': [],  # 12:00-15:00
                'late': []       # 15:00-17:00
            }
            
            for trade in valid_trades:
                hour = trade.entry_time.hour
                if 9 <= hour < 12:
                    time_performance['morning'].append(trade.realized_pnl_pct or 0)
                elif 12 <= hour < 15:
                    time_performance['afternoon'].append(trade.realized_pnl_pct or 0)
                elif 15 <= hour < 17:
                    time_performance['late'].append(trade.realized_pnl_pct or 0)
            
            # 各時間帯の平均成績
            time_averages = {}
            for period, pnls in time_performance.items():
                if pnls:
                    time_averages[period] = np.mean(pnls)
                else:
                    time_averages[period] = 0
            
            # 最も成績の良い時間帯
            best_time = max(time_averages, key=time_averages.get)
            worst_time = min(time_averages, key=time_averages.get)
            
            # タイミング一貫性（分散）
            all_times = [t.entry_time.hour for t in valid_trades]
            time_consistency = 100 - (np.std(all_times) * 5)  # 標準偏差を調整
            time_consistency = max(0, min(100, time_consistency))
            
            # 曜日別分析
            weekday_performance = {}
            for trade in valid_trades:
                weekday = trade.entry_time.weekday()  # 0=月曜日
                if weekday not in weekday_performance:
                    weekday_performance[weekday] = []
                weekday_performance[weekday].append(trade.realized_pnl_pct or 0)
            
            weekday_averages = {day: np.mean(pnls) for day, pnls in weekday_performance.items() if pnls}
            
            # スコア計算
            score = 0
            
            # 時間帯パフォーマンス差異（40点）
            max_time_avg = max(time_averages.values())
            min_time_avg = min(time_averages.values())
            time_spread = max_time_avg - min_time_avg
            
            if max_time_avg > 2 and time_spread > 3:  # 明確に良い時間帯がある
                score += 35
            elif max_time_avg > 1:
                score += 25
            elif max_time_avg > 0:
                score += 15
            else:
                score += 5
            
            # 一貫性評価（30点）
            if time_consistency >= 80:
                score += 30
            elif time_consistency >= 60:
                score += 20
            elif time_consistency >= 40:
                score += 10
            else:
                score += 5
            
            # 全体的なタイミング成功率（30点）
            positive_timing_trades = [t for t in valid_trades if t.realized_pnl_pct and t.realized_pnl_pct > 1]
            timing_success_rate = len(positive_timing_trades) / len(valid_trades)
            
            if timing_success_rate >= 0.6:
                score += 30
            elif timing_success_rate >= 0.5:
                score += 20
            elif timing_success_rate >= 0.4:
                score += 10
            else:
                score += 5
            
            # レベル決定
            if score >= 80:
                level = TendencyLevel.EXCELLENT
            elif score >= 65:
                level = TendencyLevel.GOOD
            elif score >= 50:
                level = TendencyLevel.AVERAGE
            elif score >= 35:
                level = TendencyLevel.POOR
            else:
                level = TendencyLevel.VERY_POOR
            
            # 改善提案生成
            suggestions = []
            if time_spread > 5:
                suggestions.append(f"{best_time}の時間帯で最高の成績を記録しています。この時間帯での取引を増やすことを検討してください")
            if time_consistency < 60:
                suggestions.append("取引時間が不規則です。一定の時間帯に集中することで成績向上が期待できます")
            if worst_time in time_averages and time_averages[worst_time] < -1:
                suggestions.append(f"{worst_time}の時間帯での成績が悪いです。この時間帯の取引は避けることを推奨します")
            
            weekday_names = ['月曜日', '火曜日', '水曜日', '木曜日', '金曜日']
            description = f"最良時間帯: {best_time}、タイミング一貫性: {time_consistency:.0f}%"
            
            return InvestmentTendency(
                tendency_type=TendencyType.TIMING,
                level=level,
                score=score,
                name="タイミング",
                description=description,
                current_value=score,
                benchmark_value=60,
                percentile=self._calculate_percentile(score, [35, 50, 65, 80]),
                analysis_details={
                    'best_time_period': best_time,
                    'worst_time_period': worst_time,
                    'time_averages': time_averages,
                    'time_consistency': time_consistency,
                    'weekday_averages': weekday_averages,
                    'total_trades': len(valid_trades)
                },
                improvement_suggestions=suggestions,
                supporting_trades=[t.trade_id for t in valid_trades[-8:]]  # 最新8件
            )
            
        except Exception as e:
            logger.error(f"Error in timing tendency analysis: {e}")
            return None
    
    def _analyze_position_sizing_tendency(self, trades: List[TradeRecord]) -> Optional[InvestmentTendency]:
        """ポジションサイズ傾向分析"""
        try:
            valid_trades = [t for t in trades if t.quantity and t.entry_price]
            
            if len(valid_trades) < 5:
                return None
            
            # ポジション価値を計算
            position_values = []
            for trade in valid_trades:
                position_value = trade.quantity * trade.entry_price
                position_values.append(position_value)
            
            # 一貫性分析（変動係数）
            cv = np.std(position_values) / np.mean(position_values) if np.mean(position_values) > 0 else 1
            consistency_score = max(0, 100 - (cv * 100))
            
            # ポジションサイズと成績の関係
            trade_data = []
            for i, trade in enumerate(valid_trades):
                trade_data.append({
                    'position_value': position_values[i],
                    'pnl_pct': trade.realized_pnl_pct or 0,
                    'pnl': trade.realized_pnl or 0
                })
            
            df = pd.DataFrame(trade_data)
            
            # 大きなポジションと小さなポジションの成績比較
            median_size = df['position_value'].median()
            large_positions = df[df['position_value'] > median_size]
            small_positions = df[df['position_value'] <= median_size]
            
            large_avg_pnl_pct = large_positions['pnl_pct'].mean() if not large_positions.empty else 0
            small_avg_pnl_pct = small_positions['pnl_pct'].mean() if not small_positions.empty else 0
            
            # 適切なサイジング評価
            sizing_efficiency = 0
            if large_avg_pnl_pct > small_avg_pnl_pct + 1:  # 大きなポジションの方が良い成績
                sizing_efficiency = 80
            elif abs(large_avg_pnl_pct - small_avg_pnl_pct) < 1:  # 成績に差がない（良い一貫性）
                sizing_efficiency = 70
            else:  # 小さなポジションの方が良い成績
                sizing_efficiency = 50
            
            # 最大ポジション分析
            max_position = max(position_values)
            min_position = min(position_values)
            size_range_ratio = max_position / min_position if min_position > 0 else 10
            
            # スコア計算
            score = 0
            
            # 一貫性評価（40点）
            if consistency_score >= 80:
                score += 40
            elif consistency_score >= 60:
                score += 30
            elif consistency_score >= 40:
                score += 20
            else:
                score += 10
            
            # サイジング効率評価（35点）
            score += (sizing_efficiency / 100) * 35
            
            # 範囲適切性評価（25点）
            if 2 <= size_range_ratio <= 5:  # 適度な範囲
                score += 25
            elif 1.5 <= size_range_ratio <= 8:
                score += 20
            elif size_range_ratio <= 10:
                score += 15
            else:
                score += 5
            
            # レベル決定
            if score >= 85:
                level = TendencyLevel.EXCELLENT
            elif score >= 70:
                level = TendencyLevel.GOOD
            elif score >= 55:
                level = TendencyLevel.AVERAGE
            elif score >= 40:
                level = TendencyLevel.POOR
            else:
                level = TendencyLevel.VERY_POOR
            
            # 改善提案生成
            suggestions = []
            if consistency_score < 60:
                suggestions.append("ポジションサイズのばらつきが大きいです。より一貫したサイジングルールの確立を推奨します")
            if sizing_efficiency < 60:
                suggestions.append("ポジションサイズと成績の関係を見直してください。リスクに見合ったサイジングができていない可能性があります")
            if size_range_ratio > 10:
                suggestions.append("ポジションサイズの幅が大きすぎます。リスク管理の観点から範囲を制限することを推奨します")
            
            avg_position = np.mean(position_values)
            description = f"平均ポジション: ¥{avg_position:,.0f}、一貫性: {consistency_score:.0f}%"
            
            return InvestmentTendency(
                tendency_type=TendencyType.POSITION_SIZING,
                level=level,
                score=score,
                name="ポジションサイズ",
                description=description,
                current_value=consistency_score,
                benchmark_value=80,
                percentile=self._calculate_percentile(consistency_score, [40, 55, 70, 85]),
                analysis_details={
                    'avg_position_value': avg_position,
                    'consistency_score': consistency_score,
                    'size_range_ratio': size_range_ratio,
                    'large_positions_avg_pnl': large_avg_pnl_pct,
                    'small_positions_avg_pnl': small_avg_pnl_pct,
                    'total_trades': len(valid_trades)
                },
                improvement_suggestions=suggestions,
                supporting_trades=[t.trade_id for t in valid_trades[-6:]]  # 最新6件
            )
            
        except Exception as e:
            logger.error(f"Error in position sizing tendency analysis: {e}")
            return None
    
    def _analyze_emotional_tendency(self, trades: List[TradeRecord]) -> Optional[InvestmentTendency]:
        """感情的取引傾向分析"""
        try:
            valid_trades = [t for t in trades if t.realized_pnl is not None]
            
            if len(valid_trades) < 5:
                return None
            
            # 感情的取引の兆候を検出
            emotional_indicators = []
            
            # 1. 大きな損失後の即座の取引
            revenge_trades = 0
            for i in range(1, len(valid_trades)):
                prev_trade = valid_trades[i-1]
                curr_trade = valid_trades[i]
                
                if (prev_trade.realized_pnl and prev_trade.realized_pnl < -10000 and  # 大きな損失
                    prev_trade.exit_time and curr_trade.entry_time and
                    (curr_trade.entry_time - prev_trade.exit_time).total_seconds() < 3600):  # 1時間以内
                    revenge_trades += 1
                    emotional_indicators.append('revenge_trading')
            
            # 2. 異常に大きなポジションサイズ
            position_values = []
            for trade in valid_trades:
                if trade.quantity and trade.entry_price:
                    position_values.append(trade.quantity * trade.entry_price)
            
            if position_values:
                median_position = np.median(position_values)
                oversized_trades = 0
                for i, trade in enumerate(valid_trades):
                    if i < len(position_values) and position_values[i] > median_position * 3:
                        oversized_trades += 1
                        emotional_indicators.append('oversized_position')
            
            # 3. 短時間での決済（パニック決済）
            panic_exits = 0
            for trade in valid_trades:
                if (trade.entry_time and trade.exit_time and 
                    (trade.exit_time - trade.entry_time).total_seconds() < 1800 and  # 30分以内
                    trade.realized_pnl and trade.realized_pnl < 0):  # 損失
                    panic_exits += 1
                    emotional_indicators.append('panic_exit')
            
            # 4. 連続損失時の取引頻度増加
            loss_streaks = []
            current_streak = 0
            for trade in valid_trades:
                if trade.realized_pnl and trade.realized_pnl < 0:
                    current_streak += 1
                else:
                    if current_streak > 0:
                        loss_streaks.append(current_streak)
                    current_streak = 0
            
            max_loss_streak = max(loss_streaks) if loss_streaks else 0
            
            # 感情的取引率計算
            total_emotional_trades = revenge_trades + oversized_trades + panic_exits
            emotional_trade_ratio = total_emotional_trades / len(valid_trades)
            
            # スコア計算（低い感情的取引率ほど高スコア）
            score = 0
            
            # 感情的取引率評価（50点）
            if emotional_trade_ratio <= 0.05:
                score += 50
            elif emotional_trade_ratio <= 0.1:
                score += 40
            elif emotional_trade_ratio <= 0.2:
                score += 25
            elif emotional_trade_ratio <= 0.3:
                score += 15
            else:
                score += 5
            
            # 連続損失管理評価（30点）
            if max_loss_streak <= 2:
                score += 30
            elif max_loss_streak <= 3:
                score += 25
            elif max_loss_streak <= 5:
                score += 15
            else:
                score += 5
            
            # 冷静な決済評価（20点）
            if panic_exits == 0:
                score += 20
            elif panic_exits <= 1:
                score += 15
            elif panic_exits <= 2:
                score += 10
            else:
                score += 5
            
            # レベル決定
            if score >= 85:
                level = TendencyLevel.EXCELLENT
            elif score >= 70:
                level = TendencyLevel.GOOD
            elif score >= 55:
                level = TendencyLevel.AVERAGE
            elif score >= 40:
                level = TendencyLevel.POOR
            else:
                level = TendencyLevel.VERY_POOR
            
            # 改善提案生成
            suggestions = []
            if revenge_trades > 0:
                suggestions.append("大きな損失後の即座の取引が見られます。損失後は一度冷静になってから次の取引を検討してください")
            if oversized_trades > 0:
                suggestions.append("通常より大きなポジションでの取引が見られます。感情的になっている可能性があります")
            if panic_exits > 2:
                suggestions.append("短時間での損切りが多いです。事前のプランに従って冷静に判断することを推奨します")
            if max_loss_streak > 3:
                suggestions.append("連続損失が多いです。連敗時は一度取引を休止し、戦略を見直すことを推奨します")
            
            description = f"感情的取引率: {emotional_trade_ratio:.1%}、最大連敗: {max_loss_streak}回"
            
            return InvestmentTendency(
                tendency_type=TendencyType.EMOTIONAL,
                level=level,
                score=score,
                name="感情管理",
                description=description,
                current_value=emotional_trade_ratio * 100,
                benchmark_value=15,  # 15%以下が理想
                percentile=self._calculate_percentile(emotional_trade_ratio * 100, [5, 10, 20, 30]),
                analysis_details={
                    'emotional_trade_ratio': emotional_trade_ratio,
                    'revenge_trades': revenge_trades,
                    'oversized_trades': oversized_trades,
                    'panic_exits': panic_exits,
                    'max_loss_streak': max_loss_streak,
                    'total_trades': len(valid_trades)
                },
                improvement_suggestions=suggestions,
                supporting_trades=[t.trade_id for t in valid_trades if t.trade_id in [valid_trades[i].trade_id for i in range(len(valid_trades)) if any(indicator in emotional_indicators for indicator in emotional_indicators)]][:5]
            )
            
        except Exception as e:
            logger.error(f"Error in emotional tendency analysis: {e}")
            return None
    
    def _calculate_max_consecutive_losses(self, trades: List[TradeRecord]) -> int:
        """最大連続損失数を計算"""
        max_consecutive = 0
        current_consecutive = 0
        
        for trade in trades:
            if trade.realized_pnl and trade.realized_pnl < 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def _calculate_percentile(self, value: float, thresholds: List[float]) -> float:
        """パーセンタイル計算"""
        try:
            percentile = 50  # デフォルト
            
            if value <= thresholds[0]:
                percentile = 90
            elif value <= thresholds[1]:
                percentile = 70
            elif value <= thresholds[2]:
                percentile = 50
            elif value <= thresholds[3]:
                percentile = 30
            else:
                percentile = 10
            
            return percentile
            
        except Exception:
            return 50
    
    def generate_tendency_report(self, tendencies: List[InvestmentTendency]) -> Dict[str, Any]:
        """
        投資傾向レポート生成
        
        Args:
            tendencies: 投資傾向リスト
            
        Returns:
            レポート辞書
        """
        try:
            # 総合スコア計算
            if tendencies:
                overall_score = np.mean([t.score for t in tendencies])
            else:
                overall_score = 0
            
            # レベル別集計
            level_counts = {}
            for level in TendencyLevel:
                level_counts[level.value] = len([t for t in tendencies if t.level == level])
            
            # 改善優先度
            improvement_priorities = []
            poor_tendencies = [t for t in tendencies if t.level in [TendencyLevel.POOR, TendencyLevel.VERY_POOR]]
            poor_tendencies.sort(key=lambda x: x.score)
            
            for tendency in poor_tendencies[:3]:  # 上位3つ
                improvement_priorities.append({
                    'tendency': tendency.name,
                    'score': tendency.score,
                    'suggestions': tendency.improvement_suggestions
                })
            
            # 強み分析
            strengths = []
            excellent_tendencies = [t for t in tendencies if t.level == TendencyLevel.EXCELLENT]
            for tendency in excellent_tendencies:
                strengths.append({
                    'tendency': tendency.name,
                    'score': tendency.score,
                    'description': tendency.description
                })
            
            return {
                'overall_score': overall_score,
                'total_tendencies': len(tendencies),
                'level_distribution': level_counts,
                'strengths': strengths,
                'improvement_priorities': improvement_priorities,
                'detailed_tendencies': [t.to_dict() for t in tendencies],
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating tendency report: {e}")
            return {}
    
    def export_tendencies(self, tendencies: List[InvestmentTendency], output_path: str) -> bool:
        """
        投資傾向をJSONファイルにエクスポート
        
        Args:
            tendencies: 投資傾向リスト
            output_path: 出力ファイルパス
            
        Returns:
            成功した場合True
        """
        try:
            report = self.generate_tendency_report(tendencies)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Tendencies exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting tendencies: {e}")
            return False