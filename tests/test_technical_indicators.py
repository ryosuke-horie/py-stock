"""
TechnicalIndicatorsクラスのテスト
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from datetime import datetime, timedelta

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from src.technical_analysis.indicators import TechnicalIndicators


class TestTechnicalIndicators:
    """TechnicalIndicatorsのテストクラス"""
    
    def setup_method(self):
        """各テストメソッド実行前の初期化"""
        # サンプルデータ作成（100日分）
        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        
        # 価格データ生成（リアルな株価パターン）
        base_price = 1000
        returns = np.random.normal(0.001, 0.02, 100)  # 日次リターン
        
        prices = [base_price]
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        # OHLCV生成
        closes = np.array(prices)
        opens = closes * (1 + np.random.normal(0, 0.005, 100))
        highs = np.maximum(opens, closes) * (1 + np.random.uniform(0, 0.01, 100))
        lows = np.minimum(opens, closes) * (1 - np.random.uniform(0, 0.01, 100))
        volumes = np.random.randint(100000, 1000000, 100)
        
        self.test_data = pd.DataFrame({
            'timestamp': dates,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        })
        
        self.indicators = TechnicalIndicators(self.test_data)
    
    def test_initialization(self):
        """初期化テスト"""
        assert len(self.indicators.data) == 100
        assert 'hlc3' in self.indicators.data.columns
        assert 'ohlc4' in self.indicators.data.columns
        assert pd.api.types.is_datetime64_any_dtype(self.indicators.data['timestamp'])
    
    def test_initialization_invalid_data(self):
        """無効データでの初期化テスト"""
        # 必要カラムが不足
        invalid_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=10),
            'close': np.random.randn(10)
        })
        
        with pytest.raises(ValueError, match="必要なカラムがありません"):
            TechnicalIndicators(invalid_data)
        
        # データが不足
        minimal_data = pd.DataFrame({
            'timestamp': [datetime.now()],
            'open': [100], 'high': [101], 'low': [99], 'close': [100], 'volume': [1000]
        })
        
        with pytest.raises(ValueError, match="データが不足しています"):
            TechnicalIndicators(minimal_data)
    
    def test_sma(self):
        """SMAテスト"""
        sma_20 = self.indicators.sma(20)
        
        # 20期間目から値が存在する
        assert pd.isna(sma_20[:19]).all()
        assert not pd.isna(sma_20[19:]).any()
        
        # 手動計算と比較（20期間目）
        manual_sma = self.test_data['close'][:20].mean()
        assert abs(sma_20.iloc[19] - manual_sma) < 0.001
        
        # キャッシュテスト
        sma_20_cached = self.indicators.sma(20)
        pd.testing.assert_series_equal(sma_20, sma_20_cached)
    
    def test_ema(self):
        """EMAテスト"""
        ema_20 = self.indicators.ema(20)
        
        # 全期間で値が存在する
        assert not pd.isna(ema_20).any()
        
        # 最新値が最後の価格に近い（短期EMAの特性）
        ema_5 = self.indicators.ema(5)
        assert abs(ema_5.iloc[-1] - self.test_data['close'].iloc[-1]) < abs(ema_20.iloc[-1] - self.test_data['close'].iloc[-1])
    
    def test_moving_averages(self):
        """移動平均セットテスト"""
        ma_set = self.indicators.moving_averages()
        
        expected_keys = ['sma_25', 'sma_75', 'ema_9', 'ema_21']
        assert all(key in ma_set for key in expected_keys)
        
        # EMAの方がSMAより価格に敏感
        assert abs(ma_set['ema_9'].iloc[-1] - self.test_data['close'].iloc[-1]) <= abs(ma_set['sma_25'].iloc[-1] - self.test_data['close'].iloc[-1])
    
    def test_rsi(self):
        """RSIテスト"""
        rsi = self.indicators.rsi(14)
        
        # RSIは0-100の範囲
        assert (rsi >= 0).all()
        assert (rsi <= 100).all()
        
        # 14期間目から値が存在
        assert pd.isna(rsi[:13]).all()
        assert not pd.isna(rsi[14:]).any()
    
    def test_stochastic(self):
        """ストキャスティクステスト"""
        stoch = self.indicators.stochastic(14, 3)
        
        assert 'stoch_k' in stoch
        assert 'stoch_d' in stoch
        
        # %Kは0-100の範囲
        assert (stoch['stoch_k'] >= 0).all()
        assert (stoch['stoch_k'] <= 100).all()
        
        # %Dは%Kの移動平均なので、より滑らか
        k_volatility = stoch['stoch_k'].std()
        d_volatility = stoch['stoch_d'].std()
        assert d_volatility <= k_volatility
    
    def test_macd(self):
        """MACDテスト"""
        macd_data = self.indicators.macd(12, 26, 9)
        
        expected_keys = ['macd', 'macd_signal', 'macd_histogram']
        assert all(key in macd_data for key in expected_keys)
        
        # ヒストグラム = MACD - シグナル
        calculated_histogram = macd_data['macd'] - macd_data['macd_signal']
        pd.testing.assert_series_equal(
            macd_data['macd_histogram'], 
            calculated_histogram, 
            check_names=False
        )
    
    def test_macd_signals(self):
        """MACDシグナルテスト"""
        signals = self.indicators.macd_signals()
        
        expected_keys = ['macd_bullish', 'macd_bearish', 'macd_momentum_change']
        assert all(key in signals for key in expected_keys)
        
        # シグナルはブール値
        for signal in signals.values():
            assert signal.dtype == bool
    
    def test_bollinger_bands(self):
        """ボリンジャーバンドテスト"""
        bb = self.indicators.bollinger_bands(20, 2.0)
        
        expected_keys = ['bb_upper', 'bb_middle', 'bb_lower', 'bb_percent_b', 'bb_bandwidth']
        assert all(key in bb for key in expected_keys)
        
        # 上限 > 中央線 > 下限
        assert (bb['bb_upper'] >= bb['bb_middle']).all()
        assert (bb['bb_middle'] >= bb['bb_lower']).all()
        
        # %Bの検証（価格がバンド内にある時は0-1の範囲内が多い）
        close = self.test_data['close']
        in_band_mask = (close >= bb['bb_lower']) & (close <= bb['bb_upper'])
        percent_b_in_band = bb['bb_percent_b'][in_band_mask]
        assert (percent_b_in_band >= 0).most()  # 大部分が0以上
        assert (percent_b_in_band <= 1).most()  # 大部分が1以下
    
    def test_bollinger_signals(self):
        """ボリンジャーバンドシグナルテスト"""
        signals = self.indicators.bollinger_signals()
        
        expected_keys = ['bb_upper_breakout', 'bb_lower_breakout', 'bb_upper_return', 'bb_lower_return', 'bb_squeeze']
        assert all(key in signals for key in expected_keys)
        
        # シグナルはブール値
        for signal in signals.values():
            assert signal.dtype == bool
    
    def test_vwap(self):
        """VWAPテスト"""
        vwap = self.indicators.vwap(reset_daily=False)
        
        # VWAPは累積なので単調性がある傾向（必須ではない）
        assert len(vwap) == len(self.test_data)
        assert not pd.isna(vwap).any()
        
        # 典型価格と近い値域
        typical_price = self.test_data['hlc3']
        assert vwap.min() >= typical_price.min() * 0.9
        assert vwap.max() <= typical_price.max() * 1.1
    
    def test_vwap_analysis(self):
        """VWAP分析テスト"""
        analysis = self.indicators.vwap_analysis()
        
        expected_keys = ['vwap', 'vwap_deviation', 'current_price_vs_vwap', 'vwap_deviation_current']
        assert all(key in analysis for key in expected_keys)
        
        # 乖離率は百分率
        assert abs(analysis['vwap_deviation_current']) < 50  # 通常は50%以内
        
        # 価格とVWAPの関係
        assert analysis['current_price_vs_vwap'] in ['above', 'below']
    
    def test_atr(self):
        """ATRテスト"""
        atr = self.indicators.atr(14)
        
        # ATRは正の値
        assert (atr >= 0).all()
        
        # 14期間目から値が存在
        assert pd.isna(atr[:13]).all()
        assert not pd.isna(atr[14:]).any()
        
        # ATRは価格レンジより小さい（通常）
        price_range = self.test_data['high'] - self.test_data['low']
        assert (atr <= price_range.rolling(14).max()).all()
    
    def test_volatility_analysis(self):
        """ボラティリティ分析テスト"""
        vol_analysis = self.indicators.volatility_analysis()
        
        expected_keys = ['atr', 'atr_ratio', 'current_volatility_level', 'current_atr', 'avg_atr_ratio', 'return_volatility']
        assert all(key in vol_analysis for key in expected_keys)
        
        # ボラティリティレベル
        assert vol_analysis['current_volatility_level'] in ['高', '中', '低']
        
        # ATR比率は百分率
        assert 0 < vol_analysis['atr_ratio'].mean() < 50  # 通常は0-50%の範囲
    
    def test_comprehensive_analysis(self):
        """総合分析テスト"""
        analysis = self.indicators.comprehensive_analysis()
        
        # 必要なセクションが存在
        expected_sections = [
            'timestamp', 'ohlcv', 'moving_averages', 'rsi', 'stochastic', 
            'macd', 'macd_signals', 'bollinger_bands', 'bollinger_signals',
            'vwap_analysis', 'volatility_analysis', 'current_values'
        ]
        assert all(section in analysis for section in expected_sections)
        
        # current_valuesの検証
        current = analysis['current_values']
        assert 0 <= current['rsi_current'] <= 100
        assert 0 <= current['stoch_k_current'] <= 100
        assert 0 <= current['stoch_d_current'] <= 100
        assert 0 <= current['bb_percent_b_current'] <= 2  # バンド外も考慮
        assert current['atr_current'] > 0
    
    def test_get_trading_signals(self):
        """取引シグナルテスト"""
        signals = self.indicators.get_trading_signals()
        
        # 買いシグナル
        buy_signals = ['rsi_oversold', 'stoch_oversold', 'macd_bullish', 'price_above_vwap', 'bb_lower_return']
        # 売りシグナル
        sell_signals = ['rsi_overbought', 'stoch_overbought', 'macd_bearish', 'price_below_vwap', 'bb_upper_return']
        # 中立シグナル
        neutral_signals = ['bb_squeeze', 'rsi_neutral']
        
        all_signals = buy_signals + sell_signals + neutral_signals
        assert all(signal in signals for signal in all_signals)
        
        # 全てブール値
        for signal_name, signal_value in signals.items():
            assert isinstance(signal_value, (bool, np.bool_))
        
        # 論理的整合性チェック
        # RSIの過買い・過売りは排他的（ただし中立域はある）
        if signals['rsi_oversold']:
            assert not signals['rsi_overbought']
        if signals['rsi_overbought']:
            assert not signals['rsi_oversold']
    
    def test_cache_functionality(self):
        """キャッシュ機能テスト"""
        # 最初の計算
        rsi1 = self.indicators.rsi(14)
        
        # キャッシュから取得
        rsi2 = self.indicators.rsi(14)
        
        # 同じ結果
        pd.testing.assert_series_equal(rsi1, rsi2)
        
        # キャッシュキーが存在
        cache_key = self.indicators._get_cache_key('rsi', period=14, price_column='close')
        assert cache_key in self.indicators._cache
    
    def test_different_price_columns(self):
        """異なる価格カラムでのテスト"""
        # 終値ベース
        ema_close = self.indicators.ema(20, 'close')
        
        # 高値ベース
        ema_high = self.indicators.ema(20, 'high')
        
        # 高値EMAの方が高い値になるはず
        assert (ema_high >= ema_close).most()
    
    def test_edge_cases(self):
        """エッジケーステスト"""
        # 期間が1の場合
        sma_1 = self.indicators.sma(1)
        pd.testing.assert_series_equal(sma_1, self.test_data['close'], check_names=False)
        
        # 期間がデータ長と同じ場合
        sma_full = self.indicators.sma(len(self.test_data))
        assert not pd.isna(sma_full.iloc[-1])
        
        # 期間がデータ長より大きい場合
        sma_large = self.indicators.sma(len(self.test_data) + 1)
        assert pd.isna(sma_large).all()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])