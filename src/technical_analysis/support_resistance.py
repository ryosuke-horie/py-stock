from typing import Dict, List, Optional, Tuple, Union, NamedTuple
import pandas as pd
import numpy as np
from datetime import datetime, time
from dataclasses import dataclass
from scipy.signal import argrelextrema
from loguru import logger
import warnings

warnings.filterwarnings('ignore', category=FutureWarning)


@dataclass
class SupportResistanceLevel:
    """サポート・レジスタンスレベル情報"""
    price: float
    level_type: str  # 'support' or 'resistance'
    strength: float  # 0-1の強度スコア
    touch_count: int  # タッチ回数
    total_volume: float  # 累積出来高
    last_touch_index: int  # 最後にタッチした位置
    formation_time: datetime  # 形成時刻
    confidence: float  # 信頼度スコア


@dataclass
class PivotPoint:
    """ピボットポイント情報"""
    pivot: float
    resistance_levels: Dict[str, float]  # R1, R2, R3
    support_levels: Dict[str, float]     # S1, S2, S3


@dataclass
class BreakoutEvent:
    """ブレイクアウトイベント情報"""
    timestamp: datetime
    price: float
    level_broken: float
    level_type: str  # 'support' or 'resistance'
    direction: str   # 'upward' or 'downward'
    volume: float
    strength: float
    confirmed: bool


class SupportResistanceDetector:
    """
    サポート・レジスタンス自動検出クラス
    価格水準の重要ポイント特定と分析
    """
    
    def __init__(self, data: pd.DataFrame, 
                 min_touches: int = 2,
                 tolerance_percent: float = 0.5,
                 lookback_period: int = 50):
        """
        初期化
        
        Args:
            data: OHLCV形式のDataFrame
            min_touches: レベル認定に必要な最小タッチ回数
            tolerance_percent: 価格レベル認定の許容誤差（%）
            lookback_period: 分析対象期間
        """
        self.data = data.copy()
        self.min_touches = min_touches
        self.tolerance_percent = tolerance_percent / 100
        self.lookback_period = lookback_period
        
        self._validate_data()
        self._prepare_data()
        
        # キャッシュ
        self._levels_cache = {}
        self._pivots_cache = {}
    
    def _validate_data(self):
        """データ検証"""
        required_columns = ['open', 'high', 'low', 'close', 'volume', 'timestamp']
        missing_columns = [col for col in required_columns if col not in self.data.columns]
        
        if missing_columns:
            raise ValueError(f"必要なカラムがありません: {missing_columns}")
        
        if len(self.data) < self.lookback_period:
            logger.warning(f"データが不足しています。推奨: {self.lookback_period}件以上")
    
    def _prepare_data(self):
        """データ前処理"""
        # timestampをdatetimeに変換
        if not pd.api.types.is_datetime64_any_dtype(self.data['timestamp']):
            self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])
        
        # 時系列ソート
        self.data = self.data.sort_values('timestamp').reset_index(drop=True)
        
        # 時間帯情報を追加
        self.data['hour'] = self.data['timestamp'].dt.hour
        self.data['minute'] = self.data['timestamp'].dt.minute
        self.data['time_of_day'] = self.data['timestamp'].dt.time
    
    # ==================== ピボット検出 ====================
    
    def find_swing_highs_lows(self, 
                              window: int = 5,
                              min_periods: int = 20) -> Dict[str, List[Tuple[int, float]]]:
        """
        スイング高値・安値の検出
        
        Args:
            window: 検出ウィンドウサイズ
            min_periods: 最小データ期間
            
        Returns:
            高値・安値のインデックスと価格のDict
        """
        if len(self.data) < min_periods:
            return {'highs': [], 'lows': []}
        
        highs = self.data['high'].values
        lows = self.data['low'].values
        
        # scipy.signalを使った極値検出
        high_indices = argrelextrema(highs, np.greater, order=window)[0]
        low_indices = argrelextrema(lows, np.less, order=window)[0]
        
        # 結果をタプルのリストに変換
        swing_highs = [(idx, highs[idx]) for idx in high_indices]
        swing_lows = [(idx, lows[idx]) for idx in low_indices]
        
        # 強度順でソート
        swing_highs.sort(key=lambda x: x[1], reverse=True)
        swing_lows.sort(key=lambda x: x[1])
        
        return {
            'highs': swing_highs,
            'lows': swing_lows
        }
    
    def find_price_clusters(self,
                           prices: List[float],
                           indices: List[int],
                           tolerance: Optional[float] = None) -> List[Dict]:
        """
        価格クラスター検出（類似価格レベルのグループ化）
        
        Args:
            prices: 価格リスト
            indices: インデックスリスト
            tolerance: クラスター許容誤差
            
        Returns:
            クラスター情報のリスト
        """
        if tolerance is None:
            tolerance = self.tolerance_percent
        
        if not prices:
            return []
        
        clusters = []
        used_indices = set()
        
        for i, (price, idx) in enumerate(zip(prices, indices)):
            if idx in used_indices:
                continue
            
            # 現在価格の周辺をクラスター化
            cluster_prices = [price]
            cluster_indices = [idx]
            cluster_volumes = [self.data.iloc[idx]['volume']]
            
            # 許容誤差内の価格を検索
            for j, (other_price, other_idx) in enumerate(zip(prices, indices)):
                if other_idx in used_indices or i == j:
                    continue
                
                if abs(other_price - price) / price <= tolerance:
                    cluster_prices.append(other_price)
                    cluster_indices.append(other_idx)
                    cluster_volumes.append(self.data.iloc[other_idx]['volume'])
                    used_indices.add(other_idx)
            
            used_indices.add(idx)
            
            # クラスター情報を作成
            if len(cluster_prices) >= self.min_touches:
                cluster = {
                    'average_price': np.mean(cluster_prices),
                    'price_range': (min(cluster_prices), max(cluster_prices)),
                    'touch_count': len(cluster_prices),
                    'total_volume': sum(cluster_volumes),
                    'indices': sorted(cluster_indices),
                    'timestamps': [self.data.iloc[idx]['timestamp'] for idx in cluster_indices],
                    'strength': self._calculate_level_strength(cluster_prices, cluster_volumes, cluster_indices)
                }
                clusters.append(cluster)
        
        return sorted(clusters, key=lambda x: x['strength'], reverse=True)
    
    def _calculate_level_strength(self,
                                 prices: List[float],
                                 volumes: List[float],
                                 indices: List[int]) -> float:
        """
        レベル強度計算
        
        Args:
            prices: 価格リスト
            volumes: 出来高リスト  
            indices: インデックスリスト
            
        Returns:
            強度スコア (0-1)
        """
        # タッチ回数による強度
        touch_strength = min(len(prices) / 10, 1.0)
        
        # 出来高による強度
        avg_volume = np.mean(volumes)
        total_avg_volume = self.data['volume'].mean()
        volume_strength = min(avg_volume / total_avg_volume, 2.0) / 2.0
        
        # 価格の一貫性による強度
        price_std = np.std(prices)
        avg_price = np.mean(prices)
        consistency_strength = max(0, 1.0 - (price_std / avg_price) / self.tolerance_percent)
        
        # 時間的分散による強度
        time_span = max(indices) - min(indices)
        max_span = min(len(self.data) - 1, self.lookback_period)
        time_strength = min(time_span / max_span, 1.0)
        
        # 重み付き平均
        weights = [0.3, 0.3, 0.25, 0.15]  # タッチ, 出来高, 一貫性, 時間
        strengths = [touch_strength, volume_strength, consistency_strength, time_strength]
        
        return sum(w * s for w, s in zip(weights, strengths))
    
    # ==================== サポート・レジスタンス検出 ====================
    
    def detect_support_resistance_levels(self,
                                       min_strength: float = 0.3,
                                       max_levels: int = 10) -> List[SupportResistanceLevel]:
        """
        サポート・レジスタンスレベル検出
        
        Args:
            min_strength: 最小強度閾値
            max_levels: 最大検出数
            
        Returns:
            検出されたレベルのリスト
        """
        cache_key = f"sr_levels_{min_strength}_{max_levels}"
        if cache_key in self._levels_cache:
            return self._levels_cache[cache_key]
        
        # スイング高値・安値検出
        swings = self.find_swing_highs_lows()
        
        all_levels = []
        
        # レジスタンス検出（高値から）
        if swings['highs']:
            high_prices = [price for _, price in swings['highs']]
            high_indices = [idx for idx, _ in swings['highs']]
            
            resistance_clusters = self.find_price_clusters(high_prices, high_indices)
            
            for cluster in resistance_clusters:
                if cluster['strength'] >= min_strength:
                    level = SupportResistanceLevel(
                        price=cluster['average_price'],
                        level_type='resistance',
                        strength=cluster['strength'],
                        touch_count=cluster['touch_count'],
                        total_volume=cluster['total_volume'],
                        last_touch_index=max(cluster['indices']),
                        formation_time=cluster['timestamps'][0],
                        confidence=self._calculate_confidence(cluster)
                    )
                    all_levels.append(level)
        
        # サポート検出（安値から）
        if swings['lows']:
            low_prices = [price for _, price in swings['lows']]
            low_indices = [idx for idx, _ in swings['lows']]
            
            support_clusters = self.find_price_clusters(low_prices, low_indices)
            
            for cluster in support_clusters:
                if cluster['strength'] >= min_strength:
                    level = SupportResistanceLevel(
                        price=cluster['average_price'],
                        level_type='support',
                        strength=cluster['strength'],
                        touch_count=cluster['touch_count'],
                        total_volume=cluster['total_volume'],
                        last_touch_index=max(cluster['indices']),
                        formation_time=cluster['timestamps'][0],
                        confidence=self._calculate_confidence(cluster)
                    )
                    all_levels.append(level)
        
        # 強度順でソートして上位を返す
        sorted_levels = sorted(all_levels, key=lambda x: x.strength, reverse=True)
        result = sorted_levels[:max_levels]
        
        self._levels_cache[cache_key] = result
        return result
    
    def _calculate_confidence(self, cluster: Dict) -> float:
        """
        信頼度スコア計算
        
        Args:
            cluster: クラスター情報
            
        Returns:
            信頼度スコア (0-1)
        """
        # 基本強度
        base_confidence = cluster['strength']
        
        # 最近のタッチによるボーナス
        recent_indices = [idx for idx in cluster['indices'] 
                         if len(self.data) - idx <= self.lookback_period // 2]
        recency_bonus = len(recent_indices) / len(cluster['indices']) * 0.2
        
        # 出来高の一貫性
        volumes = [self.data.iloc[idx]['volume'] for idx in cluster['indices']]
        volume_consistency = 1.0 - (np.std(volumes) / np.mean(volumes)) if np.mean(volumes) > 0 else 0
        volume_bonus = min(volume_consistency, 0.3)
        
        return min(base_confidence + recency_bonus + volume_bonus, 1.0)
    
    # ==================== ピボットポイント ====================
    
    def calculate_pivot_points(self, period_type: str = 'daily') -> PivotPoint:
        """
        ピボットポイント計算
        
        Args:
            period_type: 計算期間タイプ ('daily', 'weekly', 'previous_session')
            
        Returns:
            ピボットポイント情報
        """
        cache_key = f"pivot_{period_type}"
        if cache_key in self._pivots_cache:
            return self._pivots_cache[cache_key]
        
        # 期間に応じたHLC取得
        if period_type == 'previous_session':
            # 前セッションのデータ
            if len(self.data) >= 2:
                high = self.data['high'].iloc[-2]
                low = self.data['low'].iloc[-2]
                close = self.data['close'].iloc[-2]
            else:
                high = self.data['high'].iloc[-1]
                low = self.data['low'].iloc[-1]
                close = self.data['close'].iloc[-1]
        
        elif period_type == 'daily':
            # 当日または最新データの高値・安値・終値
            if len(self.data) >= 24:  # 1日分のデータがある場合
                recent_data = self.data.tail(24)
                high = recent_data['high'].max()
                low = recent_data['low'].min()
                close = self.data['close'].iloc[-1]
            else:
                high = self.data['high'].max()
                low = self.data['low'].min()
                close = self.data['close'].iloc[-1]
        
        elif period_type == 'weekly':
            # 週次データ
            if len(self.data) >= 168:  # 1週間分のデータがある場合
                recent_data = self.data.tail(168)
                high = recent_data['high'].max()
                low = recent_data['low'].min()
                close = self.data['close'].iloc[-1]
            else:
                high = self.data['high'].max()
                low = self.data['low'].min()
                close = self.data['close'].iloc[-1]
        
        else:
            raise ValueError(f"未対応の期間タイプ: {period_type}")
        
        # 標準ピボットポイント計算
        pivot = (high + low + close) / 3
        
        # レジスタンスレベル
        r1 = 2 * pivot - low
        r2 = pivot + (high - low)
        r3 = high + 2 * (pivot - low)
        
        # サポートレベル
        s1 = 2 * pivot - high
        s2 = pivot - (high - low)
        s3 = low - 2 * (high - pivot)
        
        result = PivotPoint(
            pivot=pivot,
            resistance_levels={'R1': r1, 'R2': r2, 'R3': r3},
            support_levels={'S1': s1, 'S2': s2, 'S3': s3}
        )
        
        self._pivots_cache[cache_key] = result
        return result
    
    def calculate_camarilla_pivots(self) -> Dict[str, float]:
        """
        カマリラピボット計算
        
        Returns:
            カマリラピボットレベル
        """
        if len(self.data) == 0:
            return {}
        
        # 前日のHLC
        high = self.data['high'].iloc[-1]
        low = self.data['low'].iloc[-1]
        close = self.data['close'].iloc[-1]
        
        range_value = high - low
        
        # カマリラピボット係数
        coefficients = {
            'H1': 1.1/12, 'H2': 1.1/6, 'H3': 1.1/4, 'H4': 1.1/2,
            'L1': 1.1/12, 'L2': 1.1/6, 'L3': 1.1/4, 'L4': 1.1/2
        }
        
        camarilla = {}
        camarilla['H1'] = close + coefficients['H1'] * range_value
        camarilla['H2'] = close + coefficients['H2'] * range_value
        camarilla['H3'] = close + coefficients['H3'] * range_value
        camarilla['H4'] = close + coefficients['H4'] * range_value
        
        camarilla['L1'] = close - coefficients['L1'] * range_value
        camarilla['L2'] = close - coefficients['L2'] * range_value
        camarilla['L3'] = close - coefficients['L3'] * range_value
        camarilla['L4'] = close - coefficients['L4'] * range_value
        
        return camarilla
    
    # ==================== ブレイクアウト検出 ====================
    
    def detect_breakouts(self,
                        levels: List[SupportResistanceLevel],
                        confirmation_bars: int = 2,
                        volume_threshold: float = 1.5) -> List[BreakoutEvent]:
        """
        ブレイクアウト検出
        
        Args:
            levels: 監視対象レベル
            confirmation_bars: 確認期間
            volume_threshold: 出来高閾値倍率
            
        Returns:
            ブレイクアウトイベントリスト
        """
        if len(self.data) < confirmation_bars + 1:
            return []
        
        breakouts = []
        avg_volume = self.data['volume'].rolling(window=20).mean()
        
        # 最新の価格データをチェック
        for i in range(len(self.data) - confirmation_bars, len(self.data)):
            if i < confirmation_bars:
                continue
            
            current_bar = self.data.iloc[i]
            current_price = current_bar['close']
            current_volume = current_bar['volume']
            
            for level in levels:
                # ブレイクアウト判定
                if level.level_type == 'resistance':
                    # 上抜けブレイクアウト
                    if (current_price > level.price and 
                        self.data.iloc[i-1]['close'] <= level.price):
                        
                        # 確認期間での継続チェック
                        confirmed = all(
                            self.data.iloc[j]['close'] > level.price 
                            for j in range(i, min(i + confirmation_bars, len(self.data)))
                        )
                        
                        # 出来高確認
                        volume_confirmed = current_volume > avg_volume.iloc[i] * volume_threshold
                        
                        breakout = BreakoutEvent(
                            timestamp=current_bar['timestamp'],
                            price=current_price,
                            level_broken=level.price,
                            level_type='resistance',
                            direction='upward',
                            volume=current_volume,
                            strength=level.strength,
                            confirmed=confirmed and volume_confirmed
                        )
                        breakouts.append(breakout)
                
                elif level.level_type == 'support':
                    # 下抜けブレイクアウト
                    if (current_price < level.price and 
                        self.data.iloc[i-1]['close'] >= level.price):
                        
                        # 確認期間での継続チェック
                        confirmed = all(
                            self.data.iloc[j]['close'] < level.price 
                            for j in range(i, min(i + confirmation_bars, len(self.data)))
                        )
                        
                        # 出来高確認
                        volume_confirmed = current_volume > avg_volume.iloc[i] * volume_threshold
                        
                        breakout = BreakoutEvent(
                            timestamp=current_bar['timestamp'],
                            price=current_price,
                            level_broken=level.price,
                            level_type='support',
                            direction='downward',
                            volume=current_volume,
                            strength=level.strength,
                            confirmed=confirmed and volume_confirmed
                        )
                        breakouts.append(breakout)
        
        return sorted(breakouts, key=lambda x: x.timestamp)
    
    # ==================== 時間帯分析 ====================
    
    def analyze_time_based_strength(self,
                                   levels: List[SupportResistanceLevel]) -> Dict[str, Dict]:
        """
        時間帯別強度分析
        
        Args:
            levels: 分析対象レベル
            
        Returns:
            時間帯別強度情報
        """
        time_analysis = {}
        
        # 時間帯区分
        time_periods = {
            'asian_session': (time(0, 0), time(8, 59)),
            'european_session': (time(9, 0), time(16, 59)),
            'us_session': (time(17, 0), time(23, 59)),
            'pre_market': (time(4, 0), time(8, 59)),
            'market_hours': (time(9, 0), time(15, 59)),
            'after_hours': (time(16, 0), time(19, 59))
        }
        
        for period_name, (start_time, end_time) in time_periods.items():
            period_data = self.data[
                (self.data['time_of_day'] >= start_time) & 
                (self.data['time_of_day'] <= end_time)
            ]
            
            if len(period_data) == 0:
                continue
            
            period_analysis = {
                'total_bars': len(period_data),
                'avg_volume': period_data['volume'].mean(),
                'avg_volatility': ((period_data['high'] - period_data['low']) / period_data['close']).mean(),
                'level_touches': {},
                'breakout_frequency': 0
            }
            
            # 各レベルでの時間帯別タッチ分析
            for level in levels:
                level_key = f"{level.level_type}_{level.price:.2f}"
                
                # レベル近辺でのタッチ検出
                tolerance = level.price * self.tolerance_percent
                touches = period_data[
                    (period_data['low'] <= level.price + tolerance) & 
                    (period_data['high'] >= level.price - tolerance)
                ]
                
                if len(touches) > 0:
                    period_analysis['level_touches'][level_key] = {
                        'touch_count': len(touches),
                        'avg_volume_at_touch': touches['volume'].mean(),
                        'price_rejection_rate': self._calculate_rejection_rate(touches, level),
                        'strength_in_period': level.strength * (len(touches) / len(period_data))
                    }
            
            time_analysis[period_name] = period_analysis
        
        return time_analysis
    
    def _calculate_rejection_rate(self, touches: pd.DataFrame, level: SupportResistanceLevel) -> float:
        """
        価格拒否率計算
        
        Args:
            touches: タッチデータ
            level: レベル情報
            
        Returns:
            拒否率 (0-1)
        """
        if len(touches) == 0:
            return 0.0
        
        rejections = 0
        
        for _, bar in touches.iterrows():
            if level.level_type == 'resistance':
                # レジスタンスでの拒否: 高値でタッチして終値が下
                if bar['high'] >= level.price and bar['close'] < level.price:
                    rejections += 1
            else:  # support
                # サポートでの拒否: 安値でタッチして終値が上
                if bar['low'] <= level.price and bar['close'] > level.price:
                    rejections += 1
        
        return rejections / len(touches)
    
    # ==================== 総合分析 ====================
    
    def comprehensive_analysis(self) -> Dict[str, any]:
        """
        総合サポレジ分析
        
        Returns:
            包括的な分析結果
        """
        logger.info("サポート・レジスタンス総合分析を実行中...")
        
        # 基本レベル検出
        levels = self.detect_support_resistance_levels()
        
        # ピボットポイント
        daily_pivots = self.calculate_pivot_points('daily')
        camarilla_pivots = self.calculate_camarilla_pivots()
        
        # ブレイクアウト検出
        breakouts = self.detect_breakouts(levels)
        
        # 時間帯分析
        time_analysis = self.analyze_time_based_strength(levels)
        
        # 現在価格との関係分析
        current_price = self.data['close'].iloc[-1]
        nearest_support = self._find_nearest_level(levels, current_price, 'support')
        nearest_resistance = self._find_nearest_level(levels, current_price, 'resistance')
        
        # 市場状況判定
        market_condition = self._assess_market_condition(levels, breakouts)
        
        result = {
            'timestamp': self.data['timestamp'].iloc[-1],
            'current_price': current_price,
            'support_resistance_levels': levels,
            'pivot_points': daily_pivots,
            'camarilla_pivots': camarilla_pivots,
            'recent_breakouts': breakouts[-5:] if breakouts else [],
            'time_based_analysis': time_analysis,
            'nearest_support': nearest_support,
            'nearest_resistance': nearest_resistance,
            'market_condition': market_condition,
            'trading_recommendations': self._generate_trading_recommendations(
                levels, nearest_support, nearest_resistance, breakouts
            )
        }
        
        logger.info("サポート・レジスタンス分析完了")
        return result
    
    def _find_nearest_level(self, 
                           levels: List[SupportResistanceLevel], 
                           price: float, 
                           level_type: str) -> Optional[SupportResistanceLevel]:
        """最も近いレベルを検索"""
        filtered_levels = [l for l in levels if l.level_type == level_type]
        
        if not filtered_levels:
            return None
        
        if level_type == 'support':
            # 現在価格より下で最も近いサポート
            below_levels = [l for l in filtered_levels if l.price < price]
            if below_levels:
                return max(below_levels, key=lambda x: x.price)
        else:  # resistance
            # 現在価格より上で最も近いレジスタンス
            above_levels = [l for l in filtered_levels if l.price > price]
            if above_levels:
                return min(above_levels, key=lambda x: x.price)
        
        # 該当なしの場合は最も強いレベルを返す
        return max(filtered_levels, key=lambda x: x.strength)
    
    def _assess_market_condition(self, 
                                levels: List[SupportResistanceLevel],
                                breakouts: List[BreakoutEvent]) -> str:
        """市場状況判定"""
        current_price = self.data['close'].iloc[-1]
        
        # 最近のブレイクアウト
        recent_breakouts = [b for b in breakouts if 
                           (self.data['timestamp'].iloc[-1] - b.timestamp).days <= 1]
        
        # 価格位置分析
        support_levels = [l.price for l in levels if l.level_type == 'support']
        resistance_levels = [l.price for l in levels if l.level_type == 'resistance']
        
        supports_below = len([p for p in support_levels if p < current_price])
        resistances_above = len([p for p in resistance_levels if p > current_price])
        
        # 判定ロジック
        if recent_breakouts:
            latest_breakout = recent_breakouts[-1]
            if latest_breakout.direction == 'upward' and latest_breakout.confirmed:
                return "強気ブレイクアウト"
            elif latest_breakout.direction == 'downward' and latest_breakout.confirmed:
                return "弱気ブレイクアウト"
        
        if supports_below >= 2 and resistances_above >= 2:
            return "レンジ相場"
        elif supports_below > resistances_above:
            return "上昇トレンド"
        elif resistances_above > supports_below:
            return "下降トレンド"
        else:
            return "中立"
    
    def _generate_trading_recommendations(self,
                                        levels: List[SupportResistanceLevel],
                                        nearest_support: Optional[SupportResistanceLevel],
                                        nearest_resistance: Optional[SupportResistanceLevel],
                                        breakouts: List[BreakoutEvent]) -> List[str]:
        """トレーディング推奨事項生成"""
        recommendations = []
        current_price = self.data['close'].iloc[-1]
        
        # サポート・レジスタンス基準の推奨
        if nearest_support and nearest_resistance:
            support_distance = (current_price - nearest_support.price) / current_price
            resistance_distance = (nearest_resistance.price - current_price) / current_price
            
            if support_distance < 0.02:  # サポート近辺
                recommendations.append(f"サポート{nearest_support.price:.2f}近辺でのリバウンド狙い")
                recommendations.append(f"ストップロス: {nearest_support.price * 0.995:.2f}")
            
            if resistance_distance < 0.02:  # レジスタンス近辺
                recommendations.append(f"レジスタンス{nearest_resistance.price:.2f}での戻り売り検討")
                recommendations.append(f"ストップロス: {nearest_resistance.price * 1.005:.2f}")
            
            # リスクリワード分析
            if nearest_support and nearest_resistance:
                risk = current_price - nearest_support.price
                reward = nearest_resistance.price - current_price
                if reward > 0 and risk > 0:
                    rr_ratio = reward / risk
                    if rr_ratio > 2:
                        recommendations.append(f"良好なリスクリワード比: 1:{rr_ratio:.1f}")
        
        # ブレイクアウト基準の推奨
        recent_breakouts = [b for b in breakouts if 
                           (self.data['timestamp'].iloc[-1] - b.timestamp).days <= 1]
        
        for breakout in recent_breakouts:
            if breakout.confirmed:
                if breakout.direction == 'upward':
                    recommendations.append(f"上抜けブレイクアウト後の押し目買い機会")
                else:
                    recommendations.append(f"下抜けブレイクアウト後の戻り売り機会")
        
        # 一般的な注意事項
        if not recommendations:
            recommendations.append("明確なセットアップなし - 様子見推奨")
        
        return recommendations