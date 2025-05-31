"""
インテリジェントアラートシステム
市場状況に応じて動的にアラート条件を調整し、ノイズを除去した重要なアラートのみを通知

仕様:
- 市場ボラティリティに基づく動的閾値調整
- 複合条件アラート（テクニカル + ファンダメンタル）
- ノイズフィルタリングによるアラート最適化
- 優先度に応じた通知管理
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AlertPriority(Enum):
    """アラート優先度"""
    CRITICAL = "critical"  # 緊急：即座に対応が必要
    HIGH = "high"          # 高：重要な市場変動
    MEDIUM = "medium"      # 中：通常のシグナル
    LOW = "low"            # 低：参考情報
    INFO = "info"          # 情報：記録のみ


class MarketCondition(Enum):
    """市場状況"""
    EXTREME_VOLATILITY = "extreme_volatility"  # 極端なボラティリティ
    HIGH_VOLATILITY = "high_volatility"        # 高ボラティリティ
    NORMAL = "normal"                          # 通常
    LOW_VOLATILITY = "low_volatility"          # 低ボラティリティ
    CONSOLIDATION = "consolidation"            # レンジ相場


@dataclass
class DynamicThreshold:
    """動的閾値設定"""
    base_value: float
    current_value: float
    min_value: float
    max_value: float
    adjustment_factor: float = 1.0
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class AlertCondition:
    """アラート条件"""
    condition_type: str
    threshold: DynamicThreshold
    operator: str  # 'greater', 'less', 'equal', 'between'
    enabled: bool = True
    weight: float = 1.0  # 複合条件での重み


@dataclass
class CompositeAlert:
    """複合アラート"""
    alert_id: str
    symbol: str
    conditions: List[AlertCondition]
    min_conditions_met: int = 1  # 最小条件数
    priority_mapping: Dict[int, AlertPriority] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True


class IntelligentAlertSystem:
    """インテリジェントアラートシステム"""
    
    def __init__(self):
        """初期化"""
        self.alerts: Dict[str, CompositeAlert] = {}
        self.market_conditions: Dict[str, MarketCondition] = {}
        self.alert_history: List[Dict[str, Any]] = []
        self.noise_filter_window = 300  # 5分（秒）
        self.priority_cooldown = {
            AlertPriority.CRITICAL: 60,    # 1分
            AlertPriority.HIGH: 300,       # 5分
            AlertPriority.MEDIUM: 900,     # 15分
            AlertPriority.LOW: 1800,       # 30分
            AlertPriority.INFO: 3600       # 1時間
        }
        
    def analyze_market_condition(self, data: pd.DataFrame, symbol: str) -> MarketCondition:
        """
        市場状況を分析
        
        Parameters:
        -----------
        data : pd.DataFrame
            価格データ（OHLCV）
        symbol : str
            銘柄コード
            
        Returns:
        --------
        MarketCondition
            現在の市場状況
        """
        if len(data) < 20:
            return MarketCondition.NORMAL
            
        # ボラティリティ計算（ATR使用）
        # カラム名の大文字小文字を統一
        data_cols = data.columns
        high_col = 'High' if 'High' in data_cols else 'high'
        low_col = 'Low' if 'Low' in data_cols else 'low'
        close_col = 'Close' if 'Close' in data_cols else 'close'
        
        high_low = data[high_col] - data[low_col]
        high_close = abs(data[high_col] - data[close_col].shift(1))
        low_close = abs(data[low_col] - data[close_col].shift(1))
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=14).mean()
        current_atr = atr.iloc[-1]
        avg_atr = atr.mean()
        
        # 価格変動率
        returns = data[close_col].pct_change()
        current_volatility = returns.rolling(window=20).std().iloc[-1]
        avg_volatility = returns.rolling(window=20).std().mean()
        
        # ボラティリティ比率
        volatility_ratio = current_volatility / avg_volatility if avg_volatility > 0 else 1.0
        atr_ratio = current_atr / avg_atr if avg_atr > 0 else 1.0
        
        # 市場状況判定
        if volatility_ratio > 2.0 or atr_ratio > 2.0:
            condition = MarketCondition.EXTREME_VOLATILITY
        elif volatility_ratio > 1.5 or atr_ratio > 1.5:
            condition = MarketCondition.HIGH_VOLATILITY
        elif volatility_ratio < 0.5 and atr_ratio < 0.5:
            condition = MarketCondition.CONSOLIDATION
        elif volatility_ratio < 0.7 or atr_ratio < 0.7:
            condition = MarketCondition.LOW_VOLATILITY
        else:
            condition = MarketCondition.NORMAL
            
        self.market_conditions[symbol] = condition
        logger.info(f"{symbol} - Market condition: {condition.value}, Volatility ratio: {volatility_ratio:.2f}")
        
        return condition
        
    def adjust_thresholds(self, symbol: str, market_condition: MarketCondition):
        """
        市場状況に応じて閾値を動的に調整
        
        Parameters:
        -----------
        symbol : str
            銘柄コード
        market_condition : MarketCondition
            市場状況
        """
        # 市場状況に応じた調整係数
        adjustment_factors = {
            MarketCondition.EXTREME_VOLATILITY: 2.0,   # 閾値を緩める
            MarketCondition.HIGH_VOLATILITY: 1.5,      # やや緩める
            MarketCondition.NORMAL: 1.0,               # 標準
            MarketCondition.LOW_VOLATILITY: 0.8,       # やや厳しく
            MarketCondition.CONSOLIDATION: 0.6         # 厳しく
        }
        
        factor = adjustment_factors.get(market_condition, 1.0)
        
        # 該当銘柄のアラートの閾値を調整
        for alert_id, alert in self.alerts.items():
            if alert.symbol == symbol and alert.is_active:
                for condition in alert.conditions:
                    if condition.enabled:
                        # 基準値に調整係数を適用
                        new_value = condition.threshold.base_value * factor
                        # 最小値・最大値の範囲内に収める
                        new_value = max(condition.threshold.min_value,
                                      min(new_value, condition.threshold.max_value))
                        
                        condition.threshold.current_value = new_value
                        condition.threshold.adjustment_factor = factor
                        condition.threshold.last_updated = datetime.now()
                        
                        logger.debug(f"Adjusted threshold for {alert_id}/{condition.condition_type}: "
                                   f"{condition.threshold.base_value} -> {new_value}")
    
    def create_composite_alert(self, 
                             symbol: str,
                             conditions: List[Dict[str, Any]],
                             min_conditions: int = 1,
                             priority_rules: Optional[Dict[int, str]] = None) -> str:
        """
        複合条件アラートを作成
        
        Parameters:
        -----------
        symbol : str
            銘柄コード
        conditions : List[Dict[str, Any]]
            条件リスト
        min_conditions : int
            最小満たすべき条件数
        priority_rules : Dict[int, str]
            条件数に応じた優先度マッピング
            
        Returns:
        --------
        str
            アラートID
        """
        alert_id = f"{symbol}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 条件をAlertConditionオブジェクトに変換
        alert_conditions = []
        for cond in conditions:
            threshold = DynamicThreshold(
                base_value=cond['threshold'],
                current_value=cond['threshold'],
                min_value=cond.get('min_threshold', cond['threshold'] * 0.5),
                max_value=cond.get('max_threshold', cond['threshold'] * 2.0)
            )
            
            alert_condition = AlertCondition(
                condition_type=cond['type'],
                threshold=threshold,
                operator=cond.get('operator', 'greater'),
                weight=cond.get('weight', 1.0)
            )
            alert_conditions.append(alert_condition)
        
        # 優先度マッピング設定
        if priority_rules is None:
            priority_rules = {
                1: AlertPriority.LOW,
                2: AlertPriority.MEDIUM,
                3: AlertPriority.HIGH,
                4: AlertPriority.CRITICAL
            }
        
        priority_mapping = {k: AlertPriority(v) if isinstance(v, str) else v 
                          for k, v in priority_rules.items()}
        
        # アラート作成
        alert = CompositeAlert(
            alert_id=alert_id,
            symbol=symbol,
            conditions=alert_conditions,
            min_conditions_met=min_conditions,
            priority_mapping=priority_mapping
        )
        
        self.alerts[alert_id] = alert
        logger.info(f"Created composite alert {alert_id} for {symbol} with {len(conditions)} conditions")
        
        return alert_id
    
    def evaluate_alert(self, 
                      alert_id: str,
                      market_data: Dict[str, float],
                      technical_data: Dict[str, float],
                      fundamental_data: Optional[Dict[str, float]] = None) -> Optional[Dict[str, Any]]:
        """
        アラート条件を評価
        
        Parameters:
        -----------
        alert_id : str
            アラートID
        market_data : Dict[str, float]
            市場データ（価格、出来高等）
        technical_data : Dict[str, float]
            テクニカル指標データ
        fundamental_data : Dict[str, float]
            ファンダメンタルデータ
            
        Returns:
        --------
        Dict[str, Any] or None
            発火したアラート情報、または None
        """
        if alert_id not in self.alerts:
            return None
            
        alert = self.alerts[alert_id]
        if not alert.is_active:
            return None
        
        # 全データを統合
        all_data = {**market_data, **technical_data}
        if fundamental_data:
            all_data.update(fundamental_data)
        
        # 各条件を評価
        conditions_met = []
        total_weight = 0
        
        for condition in alert.conditions:
            if not condition.enabled:
                continue
                
            value = all_data.get(condition.condition_type)
            if value is None:
                continue
            
            threshold = condition.threshold.current_value
            is_met = False
            
            # 条件評価
            if condition.operator == 'greater':
                is_met = value > threshold
            elif condition.operator == 'less':
                is_met = value < threshold
            elif condition.operator == 'equal':
                is_met = abs(value - threshold) < 0.001
            elif condition.operator == 'between':
                # betweenの場合、thresholdは(min, max)のタプルと仮定
                if isinstance(threshold, (list, tuple)) and len(threshold) == 2:
                    is_met = threshold[0] <= value <= threshold[1]
            
            if is_met:
                conditions_met.append({
                    'type': condition.condition_type,
                    'value': value,
                    'threshold': threshold,
                    'weight': condition.weight
                })
                total_weight += condition.weight
        
        # 最小条件数チェック
        if len(conditions_met) < alert.min_conditions_met:
            return None
        
        # 優先度決定
        num_conditions_met = len(conditions_met)
        priority = alert.priority_mapping.get(num_conditions_met, AlertPriority.MEDIUM)
        
        # より細かい優先度調整（重み考慮）
        if total_weight > sum(c.weight for c in alert.conditions) * 0.8:
            # 重みの80%以上が満たされた場合、優先度を上げる
            priority = self._increase_priority(priority)
        
        alert_info = {
            'alert_id': alert_id,
            'symbol': alert.symbol,
            'timestamp': datetime.now(),
            'conditions_met': conditions_met,
            'total_conditions': len(alert.conditions),
            'priority': priority,
            'market_condition': self.market_conditions.get(alert.symbol, MarketCondition.NORMAL),
            'data': all_data
        }
        
        return alert_info
    
    def apply_noise_filter(self, alert_info: Dict[str, Any]) -> bool:
        """
        ノイズフィルタリングを適用
        
        Parameters:
        -----------
        alert_info : Dict[str, Any]
            アラート情報
            
        Returns:
        --------
        bool
            True: アラートを通知、False: フィルタリング
        """
        symbol = alert_info['symbol']
        priority = alert_info['priority']
        current_time = alert_info['timestamp']
        
        # 最近の同一銘柄・同一優先度のアラートをチェック
        recent_alerts = [
            alert for alert in self.alert_history
            if alert['symbol'] == symbol
            and alert['priority'] == priority
            and (current_time - alert['timestamp']).total_seconds() < self.noise_filter_window
        ]
        
        # ノイズフィルタリング判定
        if recent_alerts:
            # 優先度別のクールダウン時間チェック
            cooldown = self.priority_cooldown.get(priority, 300)
            last_alert = max(recent_alerts, key=lambda x: x['timestamp'])
            time_since_last = (current_time - last_alert['timestamp']).total_seconds()
            
            if time_since_last < cooldown:
                logger.debug(f"Filtered alert for {symbol} due to cooldown "
                           f"({time_since_last:.0f}s < {cooldown}s)")
                return False
        
        # 市場状況によるフィルタリング調整
        market_condition = alert_info.get('market_condition', MarketCondition.NORMAL)
        
        # 極端なボラティリティ時は、低優先度アラートをフィルタ
        if market_condition == MarketCondition.EXTREME_VOLATILITY:
            if priority in [AlertPriority.LOW, AlertPriority.INFO]:
                logger.debug(f"Filtered low priority alert for {symbol} "
                           f"due to extreme market volatility")
                return False
        
        # レンジ相場時は、頻繁なアラートをフィルタ
        elif market_condition == MarketCondition.CONSOLIDATION:
            if len(recent_alerts) > 2:  # 5分以内に3回以上
                logger.debug(f"Filtered alert for {symbol} due to "
                           f"frequent alerts in consolidation")
                return False
        
        return True
    
    def process_alert(self, alert_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        アラートを処理（ノイズフィルタリング適用）
        
        Parameters:
        -----------
        alert_info : Dict[str, Any]
            アラート情報
            
        Returns:
        --------
        Dict[str, Any] or None
            処理されたアラート情報、またはNone（フィルタリングされた場合）
        """
        # ノイズフィルタリング
        if not self.apply_noise_filter(alert_info):
            return None
        
        # アラート履歴に追加
        self.alert_history.append(alert_info)
        
        # 履歴の保持期間管理（24時間）
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.alert_history = [
            alert for alert in self.alert_history
            if alert['timestamp'] > cutoff_time
        ]
        
        return alert_info
    
    def get_notification_method(self, priority: AlertPriority) -> List[str]:
        """
        優先度に応じた通知方法を取得
        
        Parameters:
        -----------
        priority : AlertPriority
            アラート優先度
            
        Returns:
        --------
        List[str]
            通知方法のリスト
        """
        notification_methods = {
            AlertPriority.CRITICAL: ['sound', 'popup', 'email', 'push'],
            AlertPriority.HIGH: ['sound', 'popup', 'push'],
            AlertPriority.MEDIUM: ['popup', 'push'],
            AlertPriority.LOW: ['popup'],
            AlertPriority.INFO: []  # 記録のみ
        }
        
        return notification_methods.get(priority, ['popup'])
    
    def _increase_priority(self, priority: AlertPriority) -> AlertPriority:
        """優先度を1段階上げる"""
        priority_order = [
            AlertPriority.INFO,
            AlertPriority.LOW,
            AlertPriority.MEDIUM,
            AlertPriority.HIGH,
            AlertPriority.CRITICAL
        ]
        
        current_index = priority_order.index(priority)
        if current_index < len(priority_order) - 1:
            return priority_order[current_index + 1]
        return priority
    
    def get_active_alerts_summary(self) -> Dict[str, Any]:
        """
        アクティブアラートのサマリーを取得
        
        Returns:
        --------
        Dict[str, Any]
            アラートサマリー
        """
        active_alerts = [alert for alert in self.alerts.values() if alert.is_active]
        
        summary = {
            'total_active': len(active_alerts),
            'by_symbol': {},
            'by_priority': {p.value: 0 for p in AlertPriority},
            'recent_alerts': []
        }
        
        # 銘柄別集計
        for alert in active_alerts:
            if alert.symbol not in summary['by_symbol']:
                summary['by_symbol'][alert.symbol] = 0
            summary['by_symbol'][alert.symbol] += 1
        
        # 最近のアラート（過去1時間）
        cutoff_time = datetime.now() - timedelta(hours=1)
        recent = [
            alert for alert in self.alert_history
            if alert['timestamp'] > cutoff_time
        ]
        
        # 優先度別集計
        for alert in recent:
            priority_value = alert['priority'].value
            summary['by_priority'][priority_value] += 1
        
        # 最新5件
        summary['recent_alerts'] = sorted(
            recent,
            key=lambda x: x['timestamp'],
            reverse=True
        )[:5]
        
        return summary