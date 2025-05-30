"""
DataValidatorクラスのユニットテスト
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.data_validator import DataValidator


class TestDataValidator:
    """DataValidatorのテストクラス"""
    
    def setup_method(self):
        """各テストメソッド実行前の初期化"""
        self.validator = DataValidator()
        
        # 正常なテストデータ作成
        self.valid_data = self._create_valid_test_data()
        
        # 異常なテストデータ作成
        self.invalid_data = self._create_invalid_test_data()
    
    def _create_valid_test_data(self) -> pd.DataFrame:
        """正常なテストデータ作成"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='h')
        np.random.seed(42)
        
        # 現実的な株価データ生成
        base_price = 1000
        price_changes = np.random.normal(0, 0.01, 100)
        prices = [base_price]
        
        for change in price_changes[1:]:
            prices.append(prices[-1] * (1 + change))
        
        closes = np.array(prices)
        opens = closes * (1 + np.random.normal(0, 0.005, 100))
        highs = np.maximum(opens, closes) * (1 + np.random.uniform(0, 0.01, 100))
        lows = np.minimum(opens, closes) * (1 - np.random.uniform(0, 0.01, 100))
        volumes = np.random.randint(1000, 10000, 100)
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        })
    
    def _create_invalid_test_data(self) -> pd.DataFrame:
        """異常なテストデータ作成"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='h')
        
        data = pd.DataFrame({
            'timestamp': dates,
            'open': [1000] * 50,
            'high': [1010] * 50,
            'low': [990] * 50,
            'close': [1005] * 50,
            'volume': [5000] * 50
        })
        
        # 異常データを挿入
        data.loc[10, 'high'] = 800  # high < low
        data.loc[20, 'close'] = -100  # 負の価格
        data.loc[30, 'volume'] = -1000  # 負の出来高
        data.loc[40, 'open'] = np.nan  # 欠損値
        
        return data
    
    def test_initialization(self):
        """初期化テスト"""
        validator = DataValidator()
        
        assert validator.price_change_threshold == 0.2
        assert validator.volume_spike_threshold == 5.0
        assert validator.zero_volume_tolerance == 0.05
    
    def test_validate_dataframe_valid_data(self):
        """正常データの検証テスト"""
        result = self.validator.validate_dataframe(self.valid_data, "TEST")
        
        assert result["valid"] is True
        assert result["symbol"] == "TEST"
        assert result["record_count"] == 100
        assert "statistics" in result
        assert "anomalies" in result
        assert "quality_issues" in result
    
    def test_validate_dataframe_empty_data(self):
        """空データの検証テスト"""
        empty_df = pd.DataFrame()
        result = self.validator.validate_dataframe(empty_df, "EMPTY")
        
        assert result["valid"] is False
        assert "データが空です" in result["error"]
        assert result["symbol"] == "EMPTY"
    
    def test_validate_dataframe_none_data(self):
        """Noneデータの検証テスト"""
        result = self.validator.validate_dataframe(None, "NONE")
        
        assert result["valid"] is False
        assert "データが空です" in result["error"]
        assert result["symbol"] == "NONE"
    
    def test_validate_dataframe_missing_columns(self):
        """必要カラム不足の検証テスト"""
        incomplete_df = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=10),
            'close': [1000] * 10
        })
        
        result = self.validator.validate_dataframe(incomplete_df, "INCOMPLETE")
        
        assert result["valid"] is False
        assert "必要なカラムがありません" in result["error"]
        assert result["symbol"] == "INCOMPLETE"
    
    def test_validate_dataframe_invalid_data(self):
        """異常データの検証テスト"""
        result = self.validator.validate_dataframe(self.invalid_data, "INVALID")
        
        assert result["valid"] is False
        assert len(result["quality_issues"]["critical"]) > 0
        assert result["symbol"] == "INVALID"
    
    def test_calculate_basic_stats(self):
        """基本統計計算テスト"""
        stats = self.validator._calculate_basic_stats(self.valid_data)
        
        assert "price_range" in stats
        assert "volume_stats" in stats
        assert "missing_data" in stats
        assert "data_gaps" in stats
        
        # 価格統計の確認
        assert stats["price_range"]["min"] > 0
        assert stats["price_range"]["max"] > stats["price_range"]["min"]
        assert stats["price_range"]["mean_close"] > 0
        
        # 出来高統計の確認
        assert stats["volume_stats"]["total"] > 0
        assert stats["volume_stats"]["mean"] > 0
        assert stats["volume_stats"]["median"] > 0
        assert 0 <= stats["volume_stats"]["zero_volume_ratio"] <= 1
    
    def test_detect_anomalies(self):
        """異常値検出テスト"""
        # 異常値を含むデータ作成
        anomaly_data = self.valid_data.copy()
        
        # 価格の異常変動を挿入
        anomaly_data.loc[50, 'close'] = anomaly_data.loc[49, 'close'] * 1.5  # 50%上昇
        
        # 出来高スパイクを挿入
        anomaly_data.loc[60, 'volume'] = anomaly_data['volume'].mean() * 10
        
        # OHLC不整合を挿入
        anomaly_data.loc[70, 'high'] = anomaly_data.loc[70, 'low'] - 10
        
        anomalies = self.validator._detect_anomalies(anomaly_data)
        
        assert "price_anomalies" in anomalies
        assert "volume_anomalies" in anomalies
        assert "ohlc_inconsistencies" in anomalies
        
        # 異常値が検出されることを確認
        assert len(anomalies["price_anomalies"]) > 0
        assert len(anomalies["volume_anomalies"]) > 0
        assert len(anomalies["ohlc_inconsistencies"]) > 0
    
    def test_check_data_quality(self):
        """データ品質チェックテスト"""
        quality_issues = self.validator._check_data_quality(self.invalid_data)
        
        assert "critical" in quality_issues
        assert "warning" in quality_issues
        assert "info" in quality_issues
        
        # クリティカルな問題が検出されることを確認
        assert len(quality_issues["critical"]) > 0
        
        # 負の価格と欠損値が検出されることを確認
        critical_issues = quality_issues["critical"]
        has_negative_price = any("負の値" in issue for issue in critical_issues)
        has_missing_value = any("欠損値" in issue for issue in critical_issues)
        
        assert has_negative_price or has_missing_value
    
    def test_detect_time_gaps(self):
        """時系列ギャップ検出テスト"""
        # ギャップを含むデータ作成
        gap_data = self.valid_data.copy()
        
        # 意図的にギャップを作成（通常1時間間隔のところに6時間ギャップ）
        gap_data.loc[50, 'timestamp'] = gap_data.loc[49, 'timestamp'] + timedelta(hours=6)
        
        # 以降のタイムスタンプも調整
        for i in range(51, len(gap_data)):
            gap_data.loc[i, 'timestamp'] = gap_data.loc[i-1, 'timestamp'] + timedelta(hours=1)
        
        gaps = self.validator._detect_time_gaps(gap_data)
        
        assert len(gaps) > 0
        assert "start_time" in gaps[0]
        assert "end_time" in gaps[0]
        assert "gap_duration" in gaps[0]
        assert "expected_duration" in gaps[0]
    
    def test_clean_data(self):
        """データクリーニングテスト"""
        # 重複データを含むテストデータ作成
        dirty_data = self.valid_data.copy()
        
        # 重複行を追加
        dirty_data = pd.concat([dirty_data, dirty_data.iloc[[0, 1]]], ignore_index=True)
        
        # 負の価格を追加
        dirty_data.loc[len(dirty_data)] = dirty_data.iloc[0].copy()
        dirty_data.loc[len(dirty_data)-1, 'close'] = -100
        
        cleaned_data = self.validator.clean_data(dirty_data)
        
        # クリーニング後のデータサイズチェック
        assert len(cleaned_data) <= len(dirty_data)
        
        # 負の価格がないことを確認
        price_cols = ['open', 'high', 'low', 'close']
        for col in price_cols:
            assert (cleaned_data[col] > 0).all()
        
        # 負の出来高がないことを確認
        assert (cleaned_data['volume'] >= 0).all()
        
        # 時系列が昇順であることを確認
        assert cleaned_data['timestamp'].is_monotonic_increasing
    
    def test_clean_data_no_duplicates(self):
        """重複除去なしのクリーニングテスト"""
        dirty_data = self.valid_data.copy()
        dirty_data = pd.concat([dirty_data, dirty_data.iloc[[0]]], ignore_index=True)
        
        original_length = len(dirty_data)
        cleaned_data = self.validator.clean_data(dirty_data, remove_duplicates=False)
        
        # 重複除去されていないことを確認
        assert len(cleaned_data) == original_length
    
    def test_interpolate_missing_data_linear(self):
        """線形補間テスト"""
        # 欠損値を含むデータ作成
        missing_data = self.valid_data.copy()
        missing_data.loc[50, 'close'] = np.nan
        missing_data.loc[51, 'open'] = np.nan
        
        interpolated_data = self.validator.interpolate_missing_data(missing_data, method="linear")
        
        # 欠損値が補間されていることを確認
        assert interpolated_data['close'].isna().sum() == 0
        assert interpolated_data['open'].isna().sum() == 0
    
    def test_interpolate_missing_data_forward(self):
        """前方補間テスト"""
        missing_data = self.valid_data.copy()
        missing_data.loc[50, 'close'] = np.nan
        
        interpolated_data = self.validator.interpolate_missing_data(missing_data, method="forward")
        
        # 前方補間されていることを確認
        assert interpolated_data.loc[50, 'close'] == interpolated_data.loc[49, 'close']
    
    def test_interpolate_missing_data_backward(self):
        """後方補間テスト"""
        missing_data = self.valid_data.copy()
        missing_data.loc[50, 'close'] = np.nan
        
        interpolated_data = self.validator.interpolate_missing_data(missing_data, method="backward")
        
        # 後方補間されていることを確認
        assert interpolated_data.loc[50, 'close'] == interpolated_data.loc[51, 'close']
    
    def test_interpolate_missing_volume(self):
        """出来高の欠損値補間テスト"""
        missing_data = self.valid_data.copy()
        missing_data.loc[50, 'volume'] = np.nan
        
        interpolated_data = self.validator.interpolate_missing_data(missing_data)
        
        # 出来高の欠損値が0で補間されることを確認
        assert interpolated_data.loc[50, 'volume'] == 0
    
    def test_edge_cases(self):
        """エッジケースのテスト"""
        # 1行のデータ
        single_row = self.valid_data.iloc[[0]].copy()
        result = self.validator.validate_dataframe(single_row)
        assert result["valid"] is True
        
        # 空の統計計算
        empty_stats = self.validator._calculate_basic_stats(pd.DataFrame())
        assert empty_stats == {}
        
        # 時系列ギャップ検出（データが少ない場合）
        small_data = self.valid_data.iloc[:1].copy()
        gaps = self.validator._detect_time_gaps(small_data)
        assert len(gaps) == 0
    
    def test_threshold_configuration(self):
        """閾値設定テスト"""
        custom_validator = DataValidator()
        custom_validator.price_change_threshold = 0.1
        custom_validator.volume_spike_threshold = 3.0
        custom_validator.zero_volume_tolerance = 0.1
        
        # カスタム閾値での異常値検出
        anomaly_data = self.valid_data.copy()
        anomaly_data.loc[50, 'close'] = anomaly_data.loc[49, 'close'] * 1.15  # 15%上昇
        
        anomalies = custom_validator._detect_anomalies(anomaly_data)
        
        # より厳しい閾値で異常値が検出されることを確認
        assert len(anomalies["price_anomalies"]) > 0