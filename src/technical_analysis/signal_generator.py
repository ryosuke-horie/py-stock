from typing import Dict, List, Optional, Tuple, Union, Callable, Any
import pandas as pd
import numpy as np
from datetime import datetime, time
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
from loguru import logger

from .indicators import TechnicalIndicators
from .support_resistance import SupportResistanceDetector


class SignalType(Enum):
    """シグナルタイプ"""
    BUY = "buy"
    SELL = "sell"
    NEUTRAL = "neutral"


class SignalStrength(Enum):
    """シグナル強度レベル"""
    WEAK = "weak"         # 0-40
    MODERATE = "moderate" # 41-70
    STRONG = "strong"     # 71-100


@dataclass
class TradingSignal:
    """トレーディングシグナル情報"""
    timestamp: datetime
    signal_type: SignalType
    strength: float  # 0-100
    price: float
    conditions_met: Dict[str, bool]
    indicators_used: Dict[str, float]
    confidence: float  # 0-1
    risk_level: str  # 'low', 'medium', 'high'
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    notes: str = ""


@dataclass
class SignalRule:
    """シグナルルール定義"""
    name: str
    description: str
    conditions: List[Dict[str, Any]]
    weight: float = 1.0
    enabled: bool = True
    category: str = "general"


@dataclass
class FilterCriteria:
    """フィルタリング条件"""
    min_volume: Optional[float] = None
    max_volume: Optional[float] = None
    allowed_hours: Optional[List[int]] = None
    min_volatility: Optional[float] = None
    max_volatility: Optional[float] = None
    market_session: Optional[str] = None  # 'asian', 'european', 'us'


@dataclass
class BacktestResult:
    """バックテスト結果"""
    total_signals: int
    winning_signals: int
    losing_signals: int
    win_rate: float
    avg_return_per_signal: float
    max_drawdown: float
    sharpe_ratio: float
    profit_factor: float
    signals_detail: List[Dict[str, Any]]


class SignalGenerator:
    """
    エントリーシグナル生成エンジン
    複数指標を組み合わせた高度な売買判定システム
    """
    
    def __init__(self, data: pd.DataFrame, config_file: Optional[str] = None):
        """
        初期化
        
        Args:
            data: OHLCV形式のDataFrame
            config_file: 設定ファイルパス
        """
        self.data = data.copy()
        self._validate_data()
        
        # 技術指標計算器初期化
        self.indicators = TechnicalIndicators(self.data)
        self.support_resistance = SupportResistanceDetector(self.data)
        
        # デフォルトルールセット
        self.rules = self._create_default_rules()
        
        # 設定ファイルがあれば読み込み
        if config_file and Path(config_file).exists():
            self.load_rules_from_file(config_file)
        
        # キャッシュ
        self._calculated_indicators = {}
        self._signals_cache = []
    
    def _validate_data(self):
        """データ検証"""
        required_columns = ['open', 'high', 'low', 'close', 'volume', 'timestamp']
        missing_columns = [col for col in required_columns if col not in self.data.columns]
        
        if missing_columns:
            raise ValueError(f"必要なカラムがありません: {missing_columns}")
        
        if len(self.data) < 50:
            logger.warning("シグナル生成には最低50件のデータを推奨します")
    
    # ==================== デフォルトルールセット ====================
    
    def _create_default_rules(self) -> Dict[str, SignalRule]:
        """デフォルトのシグナルルール作成"""
        rules = {}
        
        # 買いシグナルルール
        rules['ema_bullish_crossover'] = SignalRule(
            name="EMA強気クロスオーバー",
            description="EMA9 > EMA21 かつ EMA21が上昇トレンド",
            conditions=[
                {'indicator': 'ema_9', 'operator': '>', 'compare_to': 'ema_21'},
                {'indicator': 'ema_21_slope', 'operator': '>', 'value': 0},
            ],
            weight=1.5,
            category="trend"
        )
        
        rules['rsi_oversold_recovery'] = SignalRule(
            name="RSI過売り回復",
            description="RSI < 30から30以上への回復",
            conditions=[
                {'indicator': 'rsi_current', 'operator': '>', 'value': 30},
                {'indicator': 'rsi_previous', 'operator': '<', 'value': 30},
                {'indicator': 'rsi_current', 'operator': '<', 'value': 70},
            ],
            weight=1.2,
            category="momentum"
        )
        
        rules['bollinger_lower_bounce'] = SignalRule(
            name="ボリンジャーバンド下限反発",
            description="下限タッチから反発",
            conditions=[
                {'indicator': 'bb_percent_b_previous', 'operator': '<', 'value': 0.1},
                {'indicator': 'bb_percent_b_current', 'operator': '>', 'value': 0.15},
                {'indicator': 'close_change', 'operator': '>', 'value': 0},
            ],
            weight=1.3,
            category="volatility"
        )
        
        rules['volume_surge_bullish'] = SignalRule(
            name="出来高急増＋上昇",
            description="通常の2倍以上の出来高で価格上昇",
            conditions=[
                {'indicator': 'volume_ratio', 'operator': '>', 'value': 2.0},
                {'indicator': 'close_change', 'operator': '>', 'value': 0.005},
            ],
            weight=1.1,
            category="volume"
        )
        
        rules['support_level_bounce'] = SignalRule(
            name="サポートレベル反発",
            description="強いサポートレベルでの反発",
            conditions=[
                {'indicator': 'near_support', 'operator': '==', 'value': True},
                {'indicator': 'support_strength', 'operator': '>', 'value': 0.7},
                {'indicator': 'close_change', 'operator': '>', 'value': 0},
            ],
            weight=1.4,
            category="support_resistance"
        )
        
        # 売りシグナルルール
        rules['ema_bearish_crossover'] = SignalRule(
            name="EMA弱気クロスオーバー",
            description="EMA9 < EMA21 かつ EMA21が下降トレンド",
            conditions=[
                {'indicator': 'ema_9', 'operator': '<', 'compare_to': 'ema_21'},
                {'indicator': 'ema_21_slope', 'operator': '<', 'value': 0},
            ],
            weight=1.5,
            category="trend"
        )
        
        rules['rsi_overbought_reversal'] = SignalRule(
            name="RSI過買い反転",
            description="RSI > 70から70以下への下落",
            conditions=[
                {'indicator': 'rsi_current', 'operator': '<', 'value': 70},
                {'indicator': 'rsi_previous', 'operator': '>', 'value': 70},
                {'indicator': 'rsi_current', 'operator': '>', 'value': 30},
            ],
            weight=1.2,
            category="momentum"
        )
        
        rules['bollinger_upper_rejection'] = SignalRule(
            name="ボリンジャーバンド上限拒否",
            description="上限タッチから反落",
            conditions=[
                {'indicator': 'bb_percent_b_previous', 'operator': '>', 'value': 0.9},
                {'indicator': 'bb_percent_b_current', 'operator': '<', 'value': 0.85},
                {'indicator': 'close_change', 'operator': '<', 'value': 0},
            ],
            weight=1.3,
            category="volatility"
        )
        
        rules['volume_surge_bearish'] = SignalRule(
            name="出来高急増＋下落",
            description="通常の2倍以上の出来高で価格下落",
            conditions=[
                {'indicator': 'volume_ratio', 'operator': '>', 'value': 2.0},
                {'indicator': 'close_change', 'operator': '<', 'value': -0.005},
            ],
            weight=1.1,
            category="volume"
        )
        
        rules['resistance_level_rejection'] = SignalRule(
            name="レジスタンスレベル拒否",
            description="強いレジスタンスレベルでの拒否",
            conditions=[
                {'indicator': 'near_resistance', 'operator': '==', 'value': True},
                {'indicator': 'resistance_strength', 'operator': '>', 'value': 0.7},
                {'indicator': 'close_change', 'operator': '<', 'value': 0},
            ],
            weight=1.4,
            category="support_resistance"
        )
        
        # 確認シグナル（強度向上）
        rules['macd_confirmation'] = SignalRule(
            name="MACD確認",
            description="MACDラインがシグナルライン上/下",
            conditions=[
                {'indicator': 'macd_line', 'operator': '>', 'compare_to': 'macd_signal'},
            ],
            weight=0.8,
            category="confirmation"
        )
        
        rules['vwap_confirmation'] = SignalRule(
            name="VWAP確認",
            description="価格がVWAP上/下",
            conditions=[
                {'indicator': 'close', 'operator': '>', 'compare_to': 'vwap'},
            ],
            weight=0.7,
            category="confirmation"
        )
        
        return rules
    
    # ==================== 指標計算 ====================
    
    def _calculate_all_indicators(self) -> Dict[str, pd.Series]:
        """全ての必要な指標を計算"""
        if self._calculated_indicators:
            return self._calculated_indicators
        
        logger.info("技術指標計算中...")
        
        indicators = {}
        
        # 移動平均
        ma_data = self.indicators.moving_averages()
        indicators.update(ma_data)
        
        # RSI
        indicators['rsi'] = self.indicators.rsi(14)
        indicators['rsi_current'] = indicators['rsi']
        indicators['rsi_previous'] = indicators['rsi'].shift(1)
        
        # MACD
        macd_data = self.indicators.macd()
        indicators['macd_line'] = macd_data['macd']
        indicators['macd_signal'] = macd_data['macd_signal']
        indicators['macd_histogram'] = macd_data['macd_histogram']
        
        # ボリンジャーバンド
        bb_data = self.indicators.bollinger_bands()
        indicators.update(bb_data)
        indicators['bb_percent_b_current'] = indicators['bb_percent_b']
        indicators['bb_percent_b_previous'] = indicators['bb_percent_b'].shift(1)
        
        # VWAP
        indicators['vwap'] = self.indicators.vwap()
        
        # 価格変動
        indicators['close'] = self.data['close']
        indicators['close_change'] = self.data['close'].pct_change()
        
        # EMAの傾き
        indicators['ema_21_slope'] = indicators['ema_21'].diff()
        
        # 出来高比率
        indicators['volume_avg'] = self.data['volume'].rolling(20).mean()
        indicators['volume_ratio'] = self.data['volume'] / indicators['volume_avg']
        
        # ATR
        indicators['atr'] = self.indicators.atr(14)
        
        # サポート・レジスタンス
        sr_analysis = self.support_resistance.comprehensive_analysis()
        levels = sr_analysis['support_resistance_levels']
        
        # サポート・レジスタンス近接判定
        current_price = self.data['close']
        indicators['near_support'] = self._calculate_level_proximity(current_price, levels, 'support')
        indicators['near_resistance'] = self._calculate_level_proximity(current_price, levels, 'resistance')
        indicators['support_strength'] = self._get_level_strength(current_price, levels, 'support')
        indicators['resistance_strength'] = self._get_level_strength(current_price, levels, 'resistance')
        
        self._calculated_indicators = indicators
        logger.info("技術指標計算完了")
        
        return indicators
    
    def _calculate_level_proximity(self, prices: pd.Series, levels: List, level_type: str) -> pd.Series:
        """レベル近接判定"""
        proximity = pd.Series([False] * len(prices), index=prices.index)
        
        filtered_levels = [l for l in levels if l.level_type == level_type]
        
        for i, price in enumerate(prices):
            for level in filtered_levels:
                # 1%以内の近接判定
                if abs(price - level.price) / price <= 0.01:
                    proximity.iloc[i] = True
                    break
        
        return proximity
    
    def _get_level_strength(self, prices: pd.Series, levels: List, level_type: str) -> pd.Series:
        """レベル強度取得"""
        strength = pd.Series([0.0] * len(prices), index=prices.index)
        
        filtered_levels = [l for l in levels if l.level_type == level_type]
        
        for i, price in enumerate(prices):
            max_strength = 0.0
            for level in filtered_levels:
                if abs(price - level.price) / price <= 0.01:
                    max_strength = max(max_strength, level.strength)
            strength.iloc[i] = max_strength
        
        return strength
    
    # ==================== シグナル生成 ====================
    
    def generate_signals(self, 
                        filter_criteria: Optional[FilterCriteria] = None,
                        custom_rules: Optional[Dict[str, SignalRule]] = None) -> List[TradingSignal]:
        """
        シグナル生成
        
        Args:
            filter_criteria: フィルタリング条件
            custom_rules: カスタムルール
            
        Returns:
            生成されたシグナルのリスト
        """
        logger.info("シグナル生成開始...")
        
        # 指標計算
        indicators = self._calculate_all_indicators()
        
        # 使用するルール
        rules_to_use = custom_rules if custom_rules else self.rules
        
        signals = []
        
        # 各時点でシグナル判定
        for i in range(50, len(self.data)):  # 最初の50件は指標安定化のためスキップ
            row_data = {
                'index': i,
                'timestamp': self.data.iloc[i]['timestamp'],
                'close': self.data.iloc[i]['close'],
                'volume': self.data.iloc[i]['volume'],
                'indicators': {key: series.iloc[i] if i < len(series) else np.nan 
                              for key, series in indicators.items()}
            }
            
            # フィルタリング
            if filter_criteria and not self._passes_filter(row_data, filter_criteria):
                continue
            
            # シグナル評価
            signal = self._evaluate_signals_at_point(row_data, rules_to_use)
            
            if signal and signal.signal_type != SignalType.NEUTRAL:
                signals.append(signal)
        
        logger.info(f"シグナル生成完了: {len(signals)}件")
        self._signals_cache = signals
        
        return signals
    
    def _passes_filter(self, row_data: Dict, criteria: FilterCriteria) -> bool:
        """フィルタリング条件チェック"""
        # 出来高フィルター
        if criteria.min_volume and row_data['volume'] < criteria.min_volume:
            return False
        if criteria.max_volume and row_data['volume'] > criteria.max_volume:
            return False
        
        # 時間フィルター
        if criteria.allowed_hours:
            hour = row_data['timestamp'].hour
            if hour not in criteria.allowed_hours:
                return False
        
        # ボラティリティフィルター
        if criteria.min_volatility or criteria.max_volatility:
            atr = row_data['indicators'].get('atr', 0)
            volatility = atr / row_data['close'] if row_data['close'] > 0 else 0
            
            if criteria.min_volatility and volatility < criteria.min_volatility:
                return False
            if criteria.max_volatility and volatility > criteria.max_volatility:
                return False
        
        # 市場セッションフィルター
        if criteria.market_session:
            hour = row_data['timestamp'].hour
            if criteria.market_session == 'asian' and not (0 <= hour <= 8):
                return False
            elif criteria.market_session == 'european' and not (9 <= hour <= 16):
                return False
            elif criteria.market_session == 'us' and not (17 <= hour <= 23):
                return False
        
        return True
    
    def _evaluate_signals_at_point(self, row_data: Dict, rules: Dict[str, SignalRule]) -> Optional[TradingSignal]:
        """特定時点でのシグナル評価"""
        buy_score = 0.0
        sell_score = 0.0
        conditions_met = {}
        indicators_used = row_data['indicators'].copy()
        
        # 各ルールを評価
        for rule_name, rule in rules.items():
            if not rule.enabled:
                continue
            
            rule_result = self._evaluate_rule(rule, row_data)
            conditions_met[rule_name] = rule_result
            
            if rule_result:
                # ルールカテゴリに基づいてスコア加算
                if any(keyword in rule_name.lower() for keyword in ['bullish', 'oversold', 'bounce', 'support']):
                    buy_score += rule.weight
                elif any(keyword in rule_name.lower() for keyword in ['bearish', 'overbought', 'rejection', 'resistance']):
                    sell_score += rule.weight
                elif 'confirmation' in rule.category:
                    # 確認シグナルは既存のスコアを増強
                    if buy_score > sell_score:
                        buy_score += rule.weight
                    elif sell_score > buy_score:
                        sell_score += rule.weight
        
        # シグナル判定
        signal_type = SignalType.NEUTRAL
        final_score = 0.0
        
        if buy_score > sell_score and buy_score >= 2.0:  # 最低閾値
            signal_type = SignalType.BUY
            final_score = min(buy_score * 20, 100)  # 0-100スケール
        elif sell_score > buy_score and sell_score >= 2.0:
            signal_type = SignalType.SELL
            final_score = min(sell_score * 20, 100)
        
        if signal_type == SignalType.NEUTRAL:
            return None
        
        # リスクレベル判定
        risk_level = self._assess_risk_level(row_data, final_score)
        
        # ストップロス・利確計算
        stop_loss, take_profit = self._calculate_exit_levels(
            row_data['close'], signal_type, row_data['indicators']
        )
        
        return TradingSignal(
            timestamp=row_data['timestamp'],
            signal_type=signal_type,
            strength=final_score,
            price=row_data['close'],
            conditions_met=conditions_met,
            indicators_used=indicators_used,
            confidence=final_score / 100,
            risk_level=risk_level,
            stop_loss=stop_loss,
            take_profit=take_profit,
            notes=f"Score: Buy={buy_score:.1f}, Sell={sell_score:.1f}"
        )
    
    def _evaluate_rule(self, rule: SignalRule, row_data: Dict) -> bool:
        """ルール評価"""
        indicators = row_data['indicators']
        
        for condition in rule.conditions:
            if not self._evaluate_condition(condition, indicators):
                return False
        
        return True
    
    def _evaluate_condition(self, condition: Dict, indicators: Dict) -> bool:
        """条件評価"""
        indicator = condition['indicator']
        operator = condition['operator']
        
        if indicator not in indicators:
            return False
        
        left_value = indicators[indicator]
        
        if pd.isna(left_value):
            return False
        
        # 比較値の取得
        if 'compare_to' in condition:
            # 他の指標との比較
            compare_indicator = condition['compare_to']
            if compare_indicator not in indicators:
                return False
            right_value = indicators[compare_indicator]
            if pd.isna(right_value):
                return False
        elif 'value' in condition:
            # 固定値との比較
            right_value = condition['value']
        else:
            return False
        
        # 演算子評価
        if operator == '>':
            return left_value > right_value
        elif operator == '<':
            return left_value < right_value
        elif operator == '>=':
            return left_value >= right_value
        elif operator == '<=':
            return left_value <= right_value
        elif operator == '==':
            return left_value == right_value
        elif operator == '!=':
            return left_value != right_value
        else:
            return False
    
    def _assess_risk_level(self, row_data: Dict, signal_strength: float) -> str:
        """リスクレベル評価"""
        atr = row_data['indicators'].get('atr', 0)
        price = row_data['close']
        volatility = atr / price if price > 0 else 0
        
        # ボラティリティベースのリスク評価
        if volatility > 0.03:  # 3%以上
            return 'high'
        elif volatility > 0.015:  # 1.5-3%
            return 'medium'
        else:
            return 'low'
    
    def _calculate_exit_levels(self, entry_price: float, signal_type: SignalType, indicators: Dict) -> Tuple[Optional[float], Optional[float]]:
        """ストップロス・利確レベル計算"""
        atr = indicators.get('atr', entry_price * 0.02)  # デフォルトは2%
        
        if signal_type == SignalType.BUY:
            # 買いシグナル
            stop_loss = entry_price - (atr * 2)  # ATRの2倍
            take_profit = entry_price + (atr * 3)  # リスクリワード1:1.5
        else:
            # 売りシグナル
            stop_loss = entry_price + (atr * 2)
            take_profit = entry_price - (atr * 3)
        
        return stop_loss, take_profit
    
    # ==================== バックテスト ====================
    
    def backtest_signals(self, 
                        signals: Optional[List[TradingSignal]] = None,
                        holding_period: int = 10,
                        transaction_cost: float = 0.001) -> BacktestResult:
        """
        シグナルバックテスト
        
        Args:
            signals: テスト対象シグナル（Noneの場合は生成済みシグナル使用）
            holding_period: 保有期間（バー数）
            transaction_cost: 取引コスト（比率）
            
        Returns:
            バックテスト結果
        """
        if signals is None:
            signals = self._signals_cache if self._signals_cache else self.generate_signals()
        
        if not signals:
            logger.warning("バックテスト対象のシグナルがありません")
            return BacktestResult(0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, [])
        
        logger.info(f"バックテスト開始: {len(signals)}シグナル")
        
        results = []
        total_return = 0.0
        returns = []
        
        for signal in signals:
            # エントリー価格
            entry_price = signal.price
            entry_time = signal.timestamp
            
            # エグジット時点を探す
            entry_index = None
            for i, timestamp in enumerate(self.data['timestamp']):
                if timestamp >= entry_time:
                    entry_index = i
                    break
            
            if entry_index is None or entry_index + holding_period >= len(self.data):
                continue
            
            # エグジット価格
            exit_index = entry_index + holding_period
            exit_price = self.data.iloc[exit_index]['close']
            exit_time = self.data.iloc[exit_index]['timestamp']
            
            # リターン計算
            if signal.signal_type == SignalType.BUY:
                raw_return = (exit_price - entry_price) / entry_price
            else:  # SELL
                raw_return = (entry_price - exit_price) / entry_price
            
            # 取引コスト控除
            net_return = raw_return - (transaction_cost * 2)  # エントリー・エグジット両方
            
            total_return += net_return
            returns.append(net_return)
            
            # ストップロス・利確チェック
            stopped_out = False
            actual_exit_price = exit_price
            
            if signal.stop_loss and signal.take_profit:
                for j in range(entry_index + 1, exit_index + 1):
                    bar_low = self.data.iloc[j]['low']
                    bar_high = self.data.iloc[j]['high']
                    
                    if signal.signal_type == SignalType.BUY:
                        if bar_low <= signal.stop_loss:
                            actual_exit_price = signal.stop_loss
                            stopped_out = True
                            break
                        elif bar_high >= signal.take_profit:
                            actual_exit_price = signal.take_profit
                            stopped_out = True
                            break
                    else:  # SELL
                        if bar_high >= signal.stop_loss:
                            actual_exit_price = signal.stop_loss
                            stopped_out = True
                            break
                        elif bar_low <= signal.take_profit:
                            actual_exit_price = signal.take_profit
                            stopped_out = True
                            break
            
            # 最終リターン再計算
            if stopped_out:
                if signal.signal_type == SignalType.BUY:
                    final_return = (actual_exit_price - entry_price) / entry_price
                else:
                    final_return = (entry_price - actual_exit_price) / entry_price
                final_return -= (transaction_cost * 2)
            else:
                final_return = net_return
            
            results.append({
                'entry_time': entry_time,
                'exit_time': exit_time,
                'signal_type': signal.signal_type.value,
                'entry_price': entry_price,
                'exit_price': actual_exit_price,
                'return': final_return,
                'strength': signal.strength,
                'stopped_out': stopped_out
            })
        
        # 統計計算
        if not results:
            return BacktestResult(0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, [])
        
        winning_trades = [r for r in results if r['return'] > 0]
        losing_trades = [r for r in results if r['return'] <= 0]
        
        win_rate = len(winning_trades) / len(results)
        avg_return = np.mean([r['return'] for r in results])
        
        # ドローダウン計算
        cumulative_returns = np.cumsum([r['return'] for r in results])
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = running_max - cumulative_returns
        max_drawdown = np.max(drawdowns) if len(drawdowns) > 0 else 0.0
        
        # シャープレシオ
        returns_std = np.std([r['return'] for r in results])
        sharpe_ratio = avg_return / returns_std if returns_std > 0 else 0.0
        
        # プロフィットファクター
        gross_profit = sum(r['return'] for r in winning_trades)
        gross_loss = -sum(r['return'] for r in losing_trades)  # 正の値にする
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        return BacktestResult(
            total_signals=len(results),
            winning_signals=len(winning_trades),
            losing_signals=len(losing_trades),
            win_rate=win_rate,
            avg_return_per_signal=avg_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            profit_factor=profit_factor,
            signals_detail=results
        )
    
    # ==================== 設定管理 ====================
    
    def save_rules_to_file(self, file_path: str):
        """ルールセットをファイルに保存"""
        rules_data = {}
        for name, rule in self.rules.items():
            rules_data[name] = {
                'name': rule.name,
                'description': rule.description,
                'conditions': rule.conditions,
                'weight': rule.weight,
                'enabled': rule.enabled,
                'category': rule.category
            }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(rules_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"ルールセット保存完了: {file_path}")
    
    def load_rules_from_file(self, file_path: str):
        """ファイルからルールセットを読み込み"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)
            
            loaded_rules = {}
            for name, rule_dict in rules_data.items():
                loaded_rules[name] = SignalRule(**rule_dict)
            
            self.rules.update(loaded_rules)
            logger.info(f"ルールセット読み込み完了: {file_path}")
            
        except Exception as e:
            logger.error(f"ルールセット読み込みエラー: {e}")
    
    def add_custom_rule(self, name: str, rule: SignalRule):
        """カスタムルール追加"""
        self.rules[name] = rule
        logger.info(f"カスタムルール追加: {name}")
    
    def remove_rule(self, name: str):
        """ルール削除"""
        if name in self.rules:
            del self.rules[name]
            logger.info(f"ルール削除: {name}")
    
    def enable_rule(self, name: str, enabled: bool):
        """ルール有効/無効切り替え"""
        if name in self.rules:
            self.rules[name].enabled = enabled
            logger.info(f"ルール状態変更: {name} -> {enabled}")
    
    # ==================== 分析機能 ====================
    
    def analyze_signal_performance(self, 
                                  signals: Optional[List[TradingSignal]] = None) -> Dict[str, Any]:
        """シグナルパフォーマンス分析"""
        if signals is None:
            signals = self._signals_cache
        
        if not signals:
            return {}
        
        # 強度別分析
        strength_bins = {'weak': [], 'moderate': [], 'strong': []}
        for signal in signals:
            if signal.strength < 40:
                strength_bins['weak'].append(signal)
            elif signal.strength < 70:
                strength_bins['moderate'].append(signal)
            else:
                strength_bins['strong'].append(signal)
        
        # シグナルタイプ別分析
        buy_signals = [s for s in signals if s.signal_type == SignalType.BUY]
        sell_signals = [s for s in signals if s.signal_type == SignalType.SELL]
        
        # 時間帯別分析
        hourly_distribution = {}
        for signal in signals:
            hour = signal.timestamp.hour
            if hour not in hourly_distribution:
                hourly_distribution[hour] = 0
            hourly_distribution[hour] += 1
        
        return {
            'total_signals': len(signals),
            'signal_types': {
                'buy': len(buy_signals),
                'sell': len(sell_signals)
            },
            'strength_distribution': {
                'weak': len(strength_bins['weak']),
                'moderate': len(strength_bins['moderate']),
                'strong': len(strength_bins['strong'])
            },
            'hourly_distribution': hourly_distribution,
            'avg_strength': np.mean([s.strength for s in signals]),
            'avg_confidence': np.mean([s.confidence for s in signals])
        }
    
    def get_signal_summary(self) -> str:
        """シグナル要約取得"""
        if not self._signals_cache:
            return "シグナルが生成されていません"
        
        analysis = self.analyze_signal_performance()
        
        summary = f"""
シグナル生成サマリー:
- 総シグナル数: {analysis['total_signals']}
- 買いシグナル: {analysis['signal_types']['buy']}
- 売りシグナル: {analysis['signal_types']['sell']}
- 平均強度: {analysis['avg_strength']:.1f}
- 平均信頼度: {analysis['avg_confidence']:.2f}
- 強度分布: 弱{analysis['strength_distribution']['weak']} / 中{analysis['strength_distribution']['moderate']} / 強{analysis['strength_distribution']['strong']}
        """
        
        return summary.strip()
    
    def optimize_rules(self, target_metric: str = 'sharpe_ratio') -> Dict[str, Any]:
        """ルール最適化（簡易版）"""
        # 各ルールを個別に無効化してパフォーマンスを測定
        baseline_signals = self.generate_signals()
        baseline_backtest = self.backtest_signals(baseline_signals)
        baseline_score = getattr(baseline_backtest, target_metric, 0)
        
        rule_importance = {}
        
        for rule_name in self.rules.keys():
            # ルールを一時的に無効化
            original_state = self.rules[rule_name].enabled
            self.rules[rule_name].enabled = False
            
            # シグナル再生成・バックテスト
            test_signals = self.generate_signals()
            test_backtest = self.backtest_signals(test_signals)
            test_score = getattr(test_backtest, target_metric, 0)
            
            # 重要度計算（ベースラインからの変化）
            importance = baseline_score - test_score
            rule_importance[rule_name] = importance
            
            # 元の状態に戻す
            self.rules[rule_name].enabled = original_state
        
        # 結果をソート
        sorted_importance = sorted(rule_importance.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'baseline_score': baseline_score,
            'rule_importance': dict(sorted_importance),
            'most_important': sorted_importance[0] if sorted_importance else None,
            'least_important': sorted_importance[-1] if sorted_importance else None
        }