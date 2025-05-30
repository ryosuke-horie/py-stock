from typing import Dict, List, Optional, Tuple, Union
import pandas as pd
import numpy as np
from datetime import datetime, date
from loguru import logger
import warnings

warnings.filterwarnings('ignore', category=FutureWarning)


class TechnicalIndicators:
    """
    テクニカル指標計算クラス
    デイトレード用の主要テクニカル指標を提供
    """
    
    def __init__(self, data: pd.DataFrame):
        """
        初期化
        
        Args:
            data: OHLCV形式のDataFrame
                  必須カラム: open, high, low, close, volume, timestamp
        """
        self.data = data.copy()
        self._validate_data()
        self._prepare_data()
        
        # 計算済み指標のキャッシュ
        self._cache = {}
    
    def _validate_data(self):
        """データ検証"""
        required_columns = ['open', 'high', 'low', 'close', 'volume', 'timestamp']
        missing_columns = [col for col in required_columns if col not in self.data.columns]
        
        if missing_columns:
            raise ValueError(f"必要なカラムがありません: {missing_columns}")
        
        if len(self.data) < 2:
            raise ValueError("データが不足しています（最低2行必要）")
        
        # データ型確認
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if not pd.api.types.is_numeric_dtype(self.data[col]):
                try:
                    self.data[col] = pd.to_numeric(self.data[col])
                except ValueError:
                    raise ValueError(f"{col}カラムを数値に変換できません")
    
    def _prepare_data(self):
        """データ前処理"""
        # timestampをdatetimeに変換
        if not pd.api.types.is_datetime64_any_dtype(self.data['timestamp']):
            self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])
        
        # 時系列ソート
        self.data = self.data.sort_values('timestamp').reset_index(drop=True)
        
        # 典型価格（HL2, HLC3, OHLC4）を事前計算
        self.data['hl2'] = (self.data['high'] + self.data['low']) / 2
        self.data['hlc3'] = (self.data['high'] + self.data['low'] + self.data['close']) / 3
        self.data['ohlc4'] = (self.data['open'] + self.data['high'] + self.data['low'] + self.data['close']) / 4
    
    def _get_cache_key(self, indicator_name: str, **params) -> str:
        """キャッシュキー生成"""
        param_str = "_".join([f"{k}={v}" for k, v in sorted(params.items())])
        return f"{indicator_name}_{param_str}"
    
    def _cache_result(self, key: str, result: Union[pd.Series, Dict]):
        """結果をキャッシュ"""
        self._cache[key] = result
    
    def _get_cached_result(self, key: str) -> Optional[Union[pd.Series, Dict]]:
        """キャッシュされた結果を取得"""
        return self._cache.get(key)
    
    # ==================== 移動平均 ====================
    
    def sma(self, period: int, price_column: str = 'close') -> pd.Series:
        """
        Simple Moving Average（単純移動平均）
        
        Args:
            period: 期間
            price_column: 価格カラム名
            
        Returns:
            SMA値のSeries
        """
        cache_key = self._get_cache_key('sma', period=period, price_column=price_column)
        cached = self._get_cached_result(cache_key)
        if cached is not None:
            return cached
        
        sma_values = self.data[price_column].rolling(window=period, min_periods=period).mean()
        self._cache_result(cache_key, sma_values)
        
        return sma_values
    
    def ema(self, period: int, price_column: str = 'close') -> pd.Series:
        """
        Exponential Moving Average（指数移動平均）
        
        Args:
            period: 期間
            price_column: 価格カラム名
            
        Returns:
            EMA値のSeries
        """
        cache_key = self._get_cache_key('ema', period=period, price_column=price_column)
        cached = self._get_cached_result(cache_key)
        if cached is not None:
            return cached
        
        ema_values = self.data[price_column].ewm(span=period, adjust=False).mean()
        self._cache_result(cache_key, ema_values)
        
        return ema_values
    
    def moving_averages(self) -> Dict[str, pd.Series]:
        """
        デイトレード用移動平均セット
        
        Returns:
            各移動平均のDict
        """
        return {
            'sma_25': self.sma(25),
            'sma_75': self.sma(75),
            'ema_9': self.ema(9),
            'ema_21': self.ema(21)
        }
    
    # ==================== RSI ====================
    
    def rsi(self, period: int = 14, price_column: str = 'close') -> pd.Series:
        """
        Relative Strength Index
        
        Args:
            period: 期間（デフォルト: 14）
            price_column: 価格カラム名
            
        Returns:
            RSI値のSeries（0-100）
        """
        cache_key = self._get_cache_key('rsi', period=period, price_column=price_column)
        cached = self._get_cached_result(cache_key)
        if cached is not None:
            return cached
        
        prices = self.data[price_column]
        delta = prices.diff()
        
        gain = (delta.where(delta > 0, 0)).rolling(window=period, min_periods=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=period).mean()
        
        rs = gain / loss
        rsi_values = 100 - (100 / (1 + rs))
        
        self._cache_result(cache_key, rsi_values)
        return rsi_values
    
    # ==================== ストキャスティクス ====================
    
    def stochastic(self, k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
        """
        Stochastic Oscillator
        
        Args:
            k_period: %K期間（デフォルト: 14）
            d_period: %D期間（デフォルト: 3）
            
        Returns:
            %Kと%DのDict
        """
        cache_key = self._get_cache_key('stochastic', k_period=k_period, d_period=d_period)
        cached = self._get_cached_result(cache_key)
        if cached is not None:
            return cached
        
        high = self.data['high']
        low = self.data['low']
        close = self.data['close']
        
        # %K計算
        lowest_low = low.rolling(window=k_period, min_periods=k_period).min()
        highest_high = high.rolling(window=k_period, min_periods=k_period).max()
        k_percent = 100 * (close - lowest_low) / (highest_high - lowest_low)
        
        # %D計算（%Kの移動平均）
        d_percent = k_percent.rolling(window=d_period, min_periods=d_period).mean()
        
        result = {
            'stoch_k': k_percent,
            'stoch_d': d_percent
        }
        
        self._cache_result(cache_key, result)
        return result
    
    # ==================== MACD ====================
    
    def macd(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Dict[str, pd.Series]:
        """
        MACD (Moving Average Convergence Divergence)
        
        Args:
            fast_period: 短期EMA期間（デフォルト: 12）
            slow_period: 長期EMA期間（デフォルト: 26）
            signal_period: シグナル線期間（デフォルト: 9）
            
        Returns:
            MACD、シグナル、ヒストグラムのDict
        """
        cache_key = self._get_cache_key('macd', fast=fast_period, slow=slow_period, signal=signal_period)
        cached = self._get_cached_result(cache_key)
        if cached is not None:
            return cached
        
        fast_ema = self.ema(fast_period)
        slow_ema = self.ema(slow_period)
        
        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        histogram = macd_line - signal_line
        
        result = {
            'macd': macd_line,
            'macd_signal': signal_line,
            'macd_histogram': histogram
        }
        
        self._cache_result(cache_key, result)
        return result
    
    def macd_signals(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Dict[str, pd.Series]:
        """
        MACDシグナル検出
        
        Returns:
            買いシグナル、売りシグナルのDict
        """
        macd_data = self.macd(fast_period, slow_period, signal_period)
        macd_line = macd_data['macd']
        signal_line = macd_data['macd_signal']
        histogram = macd_data['macd_histogram']
        
        # ゴールデンクロス（買いシグナル）
        bullish_cross = (
            (macd_line > signal_line) & 
            (macd_line.shift(1) <= signal_line.shift(1))
        )
        
        # デッドクロス（売りシグナル）
        bearish_cross = (
            (macd_line < signal_line) & 
            (macd_line.shift(1) >= signal_line.shift(1))
        )
        
        # ヒストグラムの傾き変化
        histogram_trend_change = (
            (histogram > histogram.shift(1)) & 
            (histogram.shift(1) < histogram.shift(2))
        )
        
        return {
            'macd_bullish': bullish_cross,
            'macd_bearish': bearish_cross,
            'macd_momentum_change': histogram_trend_change
        }
    
    # ==================== ボリンジャーバンド ====================
    
    def bollinger_bands(self, period: int = 20, std_dev: float = 2.0) -> Dict[str, pd.Series]:
        """
        Bollinger Bands
        
        Args:
            period: 期間（デフォルト: 20）
            std_dev: 標準偏差の倍数（デフォルト: 2.0）
            
        Returns:
            上限、中央線、下限のDict
        """
        cache_key = self._get_cache_key('bollinger', period=period, std_dev=std_dev)
        cached = self._get_cached_result(cache_key)
        if cached is not None:
            return cached
        
        close = self.data['close']
        middle = close.rolling(window=period, min_periods=period).mean()
        std = close.rolling(window=period, min_periods=period).std()
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        # %B（バンド内位置）
        percent_b = (close - lower) / (upper - lower)
        
        # バンド幅
        bandwidth = (upper - lower) / middle
        
        result = {
            'bb_upper': upper,
            'bb_middle': middle,
            'bb_lower': lower,
            'bb_percent_b': percent_b,
            'bb_bandwidth': bandwidth
        }
        
        self._cache_result(cache_key, result)
        return result
    
    def bollinger_signals(self, period: int = 20, std_dev: float = 2.0) -> Dict[str, pd.Series]:
        """
        ボリンジャーバンドシグナル検出
        
        Returns:
            各種シグナルのDict
        """
        bb_data = self.bollinger_bands(period, std_dev)
        close = self.data['close']
        
        # バンド突破シグナル
        upper_breakout = close > bb_data['bb_upper']
        lower_breakout = close < bb_data['bb_lower']
        
        # バンド回帰シグナル
        upper_return = (close < bb_data['bb_upper']) & (close.shift(1) >= bb_data['bb_upper'].shift(1))
        lower_return = (close > bb_data['bb_lower']) & (close.shift(1) <= bb_data['bb_lower'].shift(1))
        
        # スクイーズ検出（バンド幅が狭くなっている状態）
        bandwidth = bb_data['bb_bandwidth']
        squeeze = bandwidth < bandwidth.rolling(window=20, min_periods=20).quantile(0.1)
        
        return {
            'bb_upper_breakout': upper_breakout,
            'bb_lower_breakout': lower_breakout,
            'bb_upper_return': upper_return,
            'bb_lower_return': lower_return,
            'bb_squeeze': squeeze
        }
    
    # ==================== VWAP ====================
    
    def vwap(self, reset_daily: bool = True) -> pd.Series:
        """
        Volume Weighted Average Price
        
        Args:
            reset_daily: 日次リセットするかどうか
            
        Returns:
            VWAP値のSeries
        """
        cache_key = self._get_cache_key('vwap', reset_daily=reset_daily)
        cached = self._get_cached_result(cache_key)
        if cached is not None:
            return cached
        
        typical_price = self.data['hlc3']
        volume = self.data['volume']
        pv = typical_price * volume
        
        if reset_daily:
            # 日次でリセット
            date_groups = self.data['timestamp'].dt.date
            vwap_values = pd.Series(index=self.data.index, dtype=float)
            
            for date_val in date_groups.unique():
                mask = date_groups == date_val
                daily_pv = pv[mask].cumsum()
                daily_volume = volume[mask].cumsum()
                vwap_values[mask] = daily_pv / daily_volume
        else:
            # 累積VWAP
            cum_pv = pv.cumsum()
            cum_volume = volume.cumsum()
            vwap_values = cum_pv / cum_volume
        
        self._cache_result(cache_key, vwap_values)
        return vwap_values
    
    def vwap_analysis(self) -> Dict[str, Union[pd.Series, float]]:
        """
        VWAP分析
        
        Returns:
            VWAP関連指標のDict
        """
        vwap_values = self.vwap()
        close = self.data['close']
        
        # VWAP乖離率
        vwap_deviation = (close - vwap_values) / vwap_values * 100
        
        # 前日VWAP（可能な場合）
        try:
            timestamps = self.data['timestamp']
            yesterday = timestamps.iloc[-1].date() - pd.Timedelta(days=1)
            yesterday_mask = timestamps.dt.date == yesterday
            
            if yesterday_mask.any():
                yesterday_vwap = self.vwap().loc[yesterday_mask].iloc[-1]
            else:
                yesterday_vwap = np.nan
        except:
            yesterday_vwap = np.nan
        
        # 現在価格とVWAPの関係
        current_price = close.iloc[-1]
        current_vwap = vwap_values.iloc[-1]
        price_vs_vwap = "above" if current_price > current_vwap else "below"
        
        return {
            'vwap': vwap_values,
            'vwap_deviation': vwap_deviation,
            'yesterday_vwap': yesterday_vwap,
            'current_price_vs_vwap': price_vs_vwap,
            'vwap_deviation_current': vwap_deviation.iloc[-1]
        }
    
    # ==================== ATR ====================
    
    def atr(self, period: int = 14) -> pd.Series:
        """
        Average True Range（平均真の値幅）
        
        Args:
            period: 期間（デフォルト: 14）
            
        Returns:
            ATR値のSeries
        """
        cache_key = self._get_cache_key('atr', period=period)
        cached = self._get_cached_result(cache_key)
        if cached is not None:
            return cached
        
        high = self.data['high']
        low = self.data['low']
        close = self.data['close']
        
        # True Range計算
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # ATR（True Rangeの移動平均）
        atr_values = true_range.rolling(window=period, min_periods=period).mean()
        
        self._cache_result(cache_key, atr_values)
        return atr_values
    
    def volatility_analysis(self, atr_period: int = 14) -> Dict[str, Union[pd.Series, float]]:
        """
        ボラティリティ分析
        
        Args:
            atr_period: ATR期間
            
        Returns:
            ボラティリティ関連指標のDict
        """
        atr_values = self.atr(atr_period)
        close = self.data['close']
        
        # ATR比率（価格に対するATRの割合）
        atr_ratio = atr_values / close * 100
        
        # ボラティリティレベル判定
        current_atr_ratio = atr_ratio.iloc[-1]
        avg_atr_ratio = atr_ratio.rolling(window=50, min_periods=20).mean().iloc[-1]
        
        if current_atr_ratio > avg_atr_ratio * 1.5:
            volatility_level = "高"
        elif current_atr_ratio < avg_atr_ratio * 0.5:
            volatility_level = "低"
        else:
            volatility_level = "中"
        
        # 日次リターンの標準偏差
        daily_returns = close.pct_change()
        return_volatility = daily_returns.rolling(window=20, min_periods=10).std() * 100
        
        return {
            'atr': atr_values,
            'atr_ratio': atr_ratio,
            'current_volatility_level': volatility_level,
            'current_atr': atr_values.iloc[-1],
            'avg_atr_ratio': avg_atr_ratio,
            'return_volatility': return_volatility
        }
    
    # ==================== 総合分析 ====================
    
    def comprehensive_analysis(self) -> Dict[str, any]:
        """
        総合テクニカル分析
        
        Returns:
            全指標を含む総合分析結果
        """
        logger.info("総合テクニカル分析を実行中...")
        
        result = {
            'timestamp': self.data['timestamp'].iloc[-1],
            'ohlcv': {
                'open': self.data['open'].iloc[-1],
                'high': self.data['high'].iloc[-1],
                'low': self.data['low'].iloc[-1],
                'close': self.data['close'].iloc[-1],
                'volume': self.data['volume'].iloc[-1]
            },
            'moving_averages': self.moving_averages(),
            'rsi': self.rsi(),
            'stochastic': self.stochastic(),
            'macd': self.macd(),
            'macd_signals': self.macd_signals(),
            'bollinger_bands': self.bollinger_bands(),
            'bollinger_signals': self.bollinger_signals(),
            'vwap_analysis': self.vwap_analysis(),
            'volatility_analysis': self.volatility_analysis()
        }
        
        # 現在値の抽出
        current_values = {
            'rsi_current': result['rsi'].iloc[-1],
            'stoch_k_current': result['stochastic']['stoch_k'].iloc[-1],
            'stoch_d_current': result['stochastic']['stoch_d'].iloc[-1],
            'macd_current': result['macd']['macd'].iloc[-1],
            'macd_signal_current': result['macd']['macd_signal'].iloc[-1],
            'bb_percent_b_current': result['bollinger_bands']['bb_percent_b'].iloc[-1],
            'atr_current': result['volatility_analysis']['current_atr']
        }
        
        result['current_values'] = current_values
        
        logger.info("総合テクニカル分析完了")
        return result
    
    def get_trading_signals(self) -> Dict[str, bool]:
        """
        取引シグナル総合判定
        
        Returns:
            各種シグナルの真偽値Dict
        """
        # 各指標の現在値取得
        rsi_current = self.rsi().iloc[-1]
        stoch = self.stochastic()
        stoch_k = stoch['stoch_k'].iloc[-1]
        stoch_d = stoch['stoch_d'].iloc[-1]
        
        macd_signals = self.macd_signals()
        bb_signals = self.bollinger_signals()
        
        close = self.data['close'].iloc[-1]
        vwap_current = self.vwap().iloc[-1]
        
        # シグナル判定
        signals = {
            # 買いシグナル
            'rsi_oversold': rsi_current < 30,
            'stoch_oversold': stoch_k < 20 and stoch_d < 20,
            'macd_bullish': macd_signals['macd_bullish'].iloc[-1],
            'price_above_vwap': close > vwap_current,
            'bb_lower_return': bb_signals['bb_lower_return'].iloc[-1],
            
            # 売りシグナル
            'rsi_overbought': rsi_current > 70,
            'stoch_overbought': stoch_k > 80 and stoch_d > 80,
            'macd_bearish': macd_signals['macd_bearish'].iloc[-1],
            'price_below_vwap': close < vwap_current,
            'bb_upper_return': bb_signals['bb_upper_return'].iloc[-1],
            
            # 中立シグナル
            'bb_squeeze': bb_signals['bb_squeeze'].iloc[-1],
            'rsi_neutral': 30 <= rsi_current <= 70
        }
        
        return signals
    
    def calculate_all_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        全てのテクニカル指標を計算してDataFrameとして返す
        
        Args:
            data: OHLCV形式のDataFrame（Date列をインデックスとして持つ）
            
        Returns:
            指標を追加したDataFrame
        """
        # データのコピーを作成
        result_df = data.copy()
        
        # 移動平均
        ma = self.moving_averages()
        for key, series in ma.items():
            result_df[key.upper()] = series
        
        # RSI
        result_df['RSI'] = self.rsi()
        
        # ストキャスティクス
        stoch = self.stochastic()
        result_df['STOCH_K'] = stoch['stoch_k']
        result_df['STOCH_D'] = stoch['stoch_d']
        
        # MACD
        macd_data = self.macd()
        result_df['MACD'] = macd_data['macd']
        result_df['MACD_SIGNAL'] = macd_data['macd_signal']
        result_df['MACD_HISTOGRAM'] = macd_data['macd_histogram']
        
        # ボリンジャーバンド
        bb = self.bollinger_bands()
        result_df['BB_UPPER'] = bb['bb_upper']
        result_df['BB_MIDDLE'] = bb['bb_middle']
        result_df['BB_LOWER'] = bb['bb_lower']
        result_df['BB_PERCENT_B'] = bb['bb_percent_b']
        result_df['BB_BANDWIDTH'] = bb['bb_bandwidth']
        
        # VWAP
        result_df['VWAP'] = self.vwap()
        
        # ATR
        result_df['ATR'] = self.atr()
        
        # Volume列が元のデータに含まれていることを確認
        if 'Volume' not in result_df.columns and 'volume' in self.data.columns:
            result_df['Volume'] = self.data['volume']
        
        return result_df