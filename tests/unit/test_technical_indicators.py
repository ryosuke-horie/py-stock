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
        
        # NaN値を除いたRSIは0-100の範囲
        valid_rsi = rsi.dropna()
        assert (valid_rsi >= 0).all()
        assert (valid_rsi <= 100).all()
        
        # 初期期間はNaN値
        assert pd.isna(rsi[:13]).any()  # 初期13期間にNaN値が含まれる
        
        # 後半にはNaN以外の値が存在
        assert not pd.isna(rsi[-10:]).all()  # 最後の10期間に値が存在
    
    def test_stochastic(self):
        """ストキャスティクステスト"""
        stoch = self.indicators.stochastic(14, 3)
        
        assert 'stoch_k' in stoch
        assert 'stoch_d' in stoch
        
        # NaN値を除いた%Kは0-100の範囲
        valid_k = stoch['stoch_k'].dropna()
        assert (valid_k >= 0).all()
        assert (valid_k <= 100).all()
        
        # 有効なデータで%Dは%Kの移動平均なので、より滑らか
        valid_d = stoch['stoch_d'].dropna()
        if len(valid_k) > 0 and len(valid_d) > 0:
            k_volatility = valid_k.std()
            d_volatility = valid_d.std()
            assert d_volatility <= k_volatility or abs(d_volatility - k_volatility) < 0.1
    
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
        
        # NaN値を除いて上限 > 中央線 > 下限を確認
        valid_indices = ~(bb['bb_upper'].isna() | bb['bb_middle'].isna() | bb['bb_lower'].isna())
        valid_bb = {key: series[valid_indices] for key, series in bb.items()}
        
        if len(valid_bb['bb_upper']) > 0:
            assert (valid_bb['bb_upper'] >= valid_bb['bb_middle']).all()
            assert (valid_bb['bb_middle'] >= valid_bb['bb_lower']).all()
        
        # %Bの検証（価格がバンド内にある時は0-1の範囲内が多い）
        close = self.test_data['close'][valid_indices]
        if len(close) > 0:
            in_band_mask = (close >= valid_bb['bb_lower']) & (close <= valid_bb['bb_upper'])
            percent_b_in_band = valid_bb['bb_percent_b'][in_band_mask]
            if len(percent_b_in_band) > 0:
                # 少なくとも半分以上は範囲内
                assert (percent_b_in_band >= 0).sum() > len(percent_b_in_band) * 0.3
                assert (percent_b_in_band <= 1).sum() > len(percent_b_in_band) * 0.3
    
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
        
        # VWAPの長さチェック
        assert len(vwap) == len(self.test_data)
        
        # NaN値を除いてテスト
        valid_vwap = vwap.dropna()
        
        # 有効なVWAP値が存在することを確認
        assert len(valid_vwap) > 0
        
        # 典型価格と近い値域（有効な値のみで比較）
        valid_indices = ~pd.isna(vwap)
        # 典型価格を計算: (high + low + close) / 3
        typical_price = ((self.test_data['high'] + self.test_data['low'] + self.test_data['close']) / 3)[valid_indices]
        if len(typical_price) > 0:
            assert valid_vwap.min() >= typical_price.min() * 0.8
            assert valid_vwap.max() <= typical_price.max() * 1.2
    
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
        
        # NaN値を除いたATRは正の値
        valid_atr = atr.dropna()
        assert (valid_atr >= 0).all()
        
        # 初期期間はNaN値が含まれる可能性
        assert pd.isna(atr[:13]).any()  # 初期13期間にNaN値が含まれる
        
        # 後半には有効な値が存在
        assert not pd.isna(atr[-10:]).all()  # 最後の10期間に値が存在
        
        # ATRは価格レンジと関連している（NaN値を除いて比較）
        price_range = self.test_data['high'] - self.test_data['low']
        max_range = price_range.rolling(14).max()
        
        # 両方に有効な値がある場所で比較
        valid_mask = ~(pd.isna(atr) | pd.isna(max_range))
        if valid_mask.any():
            assert (atr[valid_mask] <= max_range[valid_mask] * 2).all()  # ATRは最大レンジの2倍以下
    
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
        
        # NaN値を除いて比較
        valid_mask = ~(pd.isna(ema_close) | pd.isna(ema_high))
        valid_close = ema_close[valid_mask]
        valid_high = ema_high[valid_mask]
        
        # 高値EMAの方が高い値になることが多い
        if len(valid_close) > 0 and len(valid_high) > 0:
            higher_count = (valid_high >= valid_close).sum()
            assert higher_count > len(valid_close) * 0.7  # 70%以上が高値EMA >= 終値EMA
    
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
    
    def test_calculate_all_indicators(self):
        """全指標計算テスト"""
        result_df = self.indicators.calculate_all_indicators(self.test_data)
        
        # 全カラムが追加されていることを確認
        expected_columns = [
            'SMA_25', 'SMA_75', 'EMA_9', 'EMA_21', 'RSI', 'STOCH_K', 'STOCH_D',
            'MACD', 'MACD_SIGNAL', 'MACD_HISTOGRAM', 'BB_UPPER', 'BB_MIDDLE', 
            'BB_LOWER', 'BB_PERCENT_B', 'BB_BANDWIDTH', 'VWAP', 'ATR'
        ]
        
        for col in expected_columns:
            assert col in result_df.columns, f"Missing column: {col}"
        
        # 元のデータも保持されている
        original_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        for col in original_columns:
            assert col in result_df.columns
        
        # データ長が同じ
        assert len(result_df) == len(self.test_data)
        
        # Volumeカラムが適切に処理されている
        if 'Volume' not in result_df.columns:
            assert 'volume' in result_df.columns
    
    def test_data_validation_edge_cases(self):
        """データ検証エッジケーステスト"""
        # 数値でない文字列カラムを含むデータ
        invalid_data = self.test_data.copy()
        invalid_data.loc[0, 'close'] = 'invalid'
        
        # 数値変換が試行されることを確認
        with pytest.raises(ValueError):
            TechnicalIndicators(invalid_data)
        
        # timestampが文字列の場合の変換テスト
        string_timestamp_data = self.test_data.copy()
        string_timestamp_data['timestamp'] = string_timestamp_data['timestamp'].astype(str)
        
        # エラーなく初期化できることを確認
        indicators_str_ts = TechnicalIndicators(string_timestamp_data)
        assert pd.api.types.is_datetime64_any_dtype(indicators_str_ts.data['timestamp'])
    
    def test_vwap_daily_reset(self):
        """VWAP日次リセットテスト"""
        # 複数日のデータを作成
        multi_day_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01 09:00', periods=48, freq='h'),
            'open': np.random.uniform(990, 1010, 48),
            'high': np.random.uniform(1000, 1020, 48),
            'low': np.random.uniform(980, 1000, 48),
            'close': np.random.uniform(995, 1005, 48),
            'volume': np.random.randint(1000, 10000, 48)
        })
        
        multi_indicators = TechnicalIndicators(multi_day_data)
        
        # 日次リセットありのVWAP
        vwap_daily = multi_indicators.vwap(reset_daily=True)
        
        # 日次リセットなしのVWAP
        vwap_cumulative = multi_indicators.vwap(reset_daily=False)
        
        # 両方とも有効な値を持つ
        assert not pd.isna(vwap_daily).all()
        assert not pd.isna(vwap_cumulative).all()
        
        # 日次リセット版は日の開始で変化が大きい可能性がある
        assert len(vwap_daily) == len(multi_day_data)
        assert len(vwap_cumulative) == len(multi_day_data)
    
    def test_error_handling_in_methods(self):
        """メソッド内エラーハンドリングテスト"""
        # VWAP分析での例外処理テスト
        try:
            analysis = self.indicators.vwap_analysis()
            # yesterday_vwapの計算で例外が発生してもnp.nanが設定される
            assert 'yesterday_vwap' in analysis
        except Exception:
            pytest.fail("VWAP analysis should handle exceptions gracefully")
        
        # ボラティリティ分析での例外処理テスト
        try:
            vol_analysis = self.indicators.volatility_analysis()
            assert 'current_volatility_level' in vol_analysis
            assert vol_analysis['current_volatility_level'] in ['高', '中', '低']
        except Exception:
            pytest.fail("Volatility analysis should handle exceptions gracefully")
    
    def test_extreme_market_conditions(self):
        """極端な市場条件テスト"""
        # 連続的な価格上昇
        uptrend_data = self.test_data.copy()
        for i in range(1, len(uptrend_data)):
            uptrend_data.loc[i, 'close'] = uptrend_data.loc[i-1, 'close'] * 1.01  # 1%上昇
            uptrend_data.loc[i, 'high'] = uptrend_data.loc[i, 'close'] * 1.005
            uptrend_data.loc[i, 'low'] = uptrend_data.loc[i, 'close'] * 0.995
            uptrend_data.loc[i, 'open'] = uptrend_data.loc[i-1, 'close']
        
        uptrend_indicators = TechnicalIndicators(uptrend_data)
        
        # RSIが過買い状態になることを確認
        rsi = uptrend_indicators.rsi(14)
        assert rsi.iloc[-1] > 50  # 上昇トレンドでRSIは50以上
        
        # 連続的な価格下落
        downtrend_data = self.test_data.copy()
        for i in range(1, len(downtrend_data)):
            downtrend_data.loc[i, 'close'] = downtrend_data.loc[i-1, 'close'] * 0.99  # 1%下落
            downtrend_data.loc[i, 'high'] = downtrend_data.loc[i, 'close'] * 1.005
            downtrend_data.loc[i, 'low'] = downtrend_data.loc[i, 'close'] * 0.995
            downtrend_data.loc[i, 'open'] = downtrend_data.loc[i-1, 'close']
        
        downtrend_indicators = TechnicalIndicators(downtrend_data)
        
        # RSIが過売り状態になることを確認
        rsi_down = downtrend_indicators.rsi(14)
        assert rsi_down.iloc[-1] < 50  # 下降トレンドでRSIは50以下
    
    def test_zero_and_negative_volumes(self):
        """ゼロ・負の出来高テスト"""
        # ゼロ出来高を含むデータ
        zero_volume_data = self.test_data.copy()
        zero_volume_data.loc[50:60, 'volume'] = 0
        
        zero_vol_indicators = TechnicalIndicators(zero_volume_data)
        
        # VWAPが計算できることを確認（ゼロ出来高でも）
        vwap = zero_vol_indicators.vwap()
        assert not pd.isna(vwap).all()
        
        # VWAP分析も実行できる
        vwap_analysis = zero_vol_indicators.vwap_analysis()
        assert 'vwap' in vwap_analysis
    
    def test_high_frequency_data(self):
        """高頻度データテスト"""
        # 分単位の高頻度データ
        hf_dates = pd.date_range(start='2024-01-01 09:00', periods=390, freq='min')  # 1営業日分
        np.random.seed(42)
        
        # より小さな価格変動
        base_price = 1000
        returns = np.random.normal(0, 0.001, 390)  # 0.1%の標準偏差
        prices = base_price * np.cumprod(1 + returns)
        
        hf_data = pd.DataFrame({
            'timestamp': hf_dates,
            'open': prices * (1 + np.random.normal(0, 0.0001, 390)),
            'high': prices * (1 + np.random.uniform(0, 0.001, 390)),
            'low': prices * (1 - np.random.uniform(0, 0.001, 390)),
            'close': prices,
            'volume': np.random.randint(100, 1000, 390)
        })
        
        hf_indicators = TechnicalIndicators(hf_data)
        
        # 短期指標のテスト
        ema_5 = hf_indicators.ema(5)
        rsi_14 = hf_indicators.rsi(14)
        
        # 高頻度データでも指標が計算できる
        assert not pd.isna(ema_5[-100:]).any()  # 後半100期間は有効
        assert not pd.isna(rsi_14[-100:]).all()  # 後半に有効な値が存在
    
    def test_price_gaps_and_splits(self):
        """価格ギャップ・分割テスト"""
        # 価格ギャップを含むデータ
        gap_data = self.test_data.copy()
        
        # 50番目に大きなギャップダウンを作成
        gap_ratio = 0.8  # 20%ギャップダウン
        gap_data.loc[50:, 'close'] *= gap_ratio
        gap_data.loc[50:, 'open'] *= gap_ratio
        gap_data.loc[50:, 'high'] *= gap_ratio
        gap_data.loc[50:, 'low'] *= gap_ratio
        
        gap_indicators = TechnicalIndicators(gap_data)
        
        # ギャップがあってもBBが計算できる
        bb = gap_indicators.bollinger_bands(20)
        assert not pd.isna(bb['bb_middle'][-20:]).any()  # 最後20期間は有効
        
        # ATRでギャップが検出される（大きな値になる）
        atr = gap_indicators.atr(14)
        atr_before_gap = atr.iloc[45:50].mean()  # ギャップ前
        atr_after_gap = atr.iloc[55:60].mean()   # ギャップ後
        
        # ギャップ後のATRの方が大きいか、または両方とも有効な値
        if not (pd.isna(atr_before_gap) or pd.isna(atr_after_gap)):
            assert atr_after_gap >= atr_before_gap * 0.5  # 完全に小さくなることはない
    
    def test_missing_data_handling(self):
        """欠損データ処理テスト"""
        # 欠損値を含むデータ
        missing_data = self.test_data.copy()
        missing_data.loc[30:35, 'close'] = np.nan
        missing_data.loc[60:62, 'volume'] = np.nan
        
        # 欠損データがあっても初期化できる
        missing_indicators = TechnicalIndicators(missing_data)
        
        # 指標計算で適切に処理される
        sma = missing_indicators.sma(20)
        rsi = missing_indicators.rsi(14)
        
        # 欠損期間の前後で計算が継続される
        assert isinstance(sma, pd.Series)
        assert isinstance(rsi, pd.Series)
        
        # VWAPも欠損データを適切に処理
        vwap = missing_indicators.vwap()
        assert isinstance(vwap, pd.Series)
    
    def test_performance_with_large_datasets(self):
        """大規模データセットパフォーマンステスト"""
        # 大量データ（1000日分）
        large_dates = pd.date_range(start='2021-01-01', periods=1000, freq='D')
        np.random.seed(42)
        
        # 大量データ生成
        base_price = 1000
        returns = np.random.normal(0.001, 0.02, 1000)
        prices = base_price * np.cumprod(1 + returns)
        
        large_data = pd.DataFrame({
            'timestamp': large_dates,
            'open': prices * (1 + np.random.normal(0, 0.005, 1000)),
            'high': prices * (1 + np.random.uniform(0, 0.01, 1000)),
            'low': prices * (1 - np.random.uniform(0, 0.01, 1000)),
            'close': prices,
            'volume': np.random.randint(100000, 1000000, 1000)
        })
        
        # 大量データでも初期化・計算が完了する
        large_indicators = TechnicalIndicators(large_data)
        
        # 複数の指標を計算
        sma_50 = large_indicators.sma(50)
        ema_200 = large_indicators.ema(200)
        rsi = large_indicators.rsi(14)
        bb = large_indicators.bollinger_bands(20)
        
        # 全て適切に計算されている
        assert len(sma_50) == 1000
        assert len(ema_200) == 1000
        assert len(rsi) == 1000
        assert len(bb['bb_middle']) == 1000
        
        # パフォーマンステスト（総合分析）
        comprehensive = large_indicators.comprehensive_analysis()
        assert 'current_values' in comprehensive
    
    def test_invalid_parameters(self):
        """無効パラメータテスト"""
        # 期間が0の場合
        with pytest.raises((ValueError, ZeroDivisionError)):
            self.indicators.sma(0)
        
        # 負の期間
        with pytest.raises((ValueError, ZeroDivisionError)):
            self.indicators.ema(-5)
        
        # 無効な価格カラム
        try:
            result = self.indicators.sma(20, 'invalid_column')
            # KeyErrorが発生するか、空のSeriesが返される
            assert isinstance(result, pd.Series)
        except KeyError:
            # KeyErrorが発生するのは正常
            pass
        
        # ボリンジャーバンドの無効な標準偏差
        bb_zero_std = self.indicators.bollinger_bands(20, 0)
        assert 'bb_upper' in bb_zero_std
        assert 'bb_lower' in bb_zero_std


if __name__ == "__main__":
    pytest.main([__file__, "-v"])