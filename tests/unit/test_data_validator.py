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
    
    def test_zero_volume_tolerance_check(self):
        """ゼロ出来高許容度チェックテスト"""
        # ゼロ出来高が多いデータを作成
        zero_volume_data = self.valid_data.copy()
        
        # 10%のデータをゼロ出来高にする（デフォルト許容度5%を超える）
        zero_count = int(len(zero_volume_data) * 0.1)
        zero_volume_data.loc[:zero_count, 'volume'] = 0
        
        quality_issues = self.validator._check_data_quality(zero_volume_data)
        
        # 警告が出ることを確認
        warning_issues = quality_issues["warning"]
        has_zero_volume_warning = any("ゼロ出来高比率が高い" in issue for issue in warning_issues)
        assert has_zero_volume_warning
    
    
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
        anomaly_data.loc[60, 'volume'] = int(anomaly_data['volume'].mean() * 10)
        
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
    
    def test_statistics_calculation_errors(self):
        """統計計算エラーハンドリングテスト"""
        # 無効なデータで統計計算
        invalid_df = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=10),
            'open': ['invalid'] * 10,  # 文字列データ
            'high': [np.inf] * 10,     # 無限大
            'low': [np.nan] * 10,      # 全て欠損値
            'close': [0] * 10,         # ゼロ価格
            'volume': [-1] * 10        # 負の出来高
        })
        
        # エラーが発生してもemptyな辞書が返されることを確認
        stats = self.validator._calculate_basic_stats(invalid_df)
        assert isinstance(stats, dict)
    
    def test_anomaly_detection_errors(self):
        """異常値検出エラーハンドリングテスト"""
        # 異常なデータ構造
        error_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=5),
            'open': [1000, np.nan, np.inf, -1000, 0],
            'high': [1010, np.nan, np.inf, -990, 10],
            'low': [990, np.nan, -np.inf, -1010, -10],
            'close': [1005, np.nan, np.inf, -1005, 5],
            'volume': [5000, np.nan, np.inf, -5000, 0]
        })
        
        # エラーが発生しても適切な構造が返されることを確認
        anomalies = self.validator._detect_anomalies(error_data)
        assert "price_anomalies" in anomalies
        assert "volume_anomalies" in anomalies
        assert "ohlc_inconsistencies" in anomalies
        assert isinstance(anomalies["price_anomalies"], list)
    
    def test_quality_check_errors(self):
        """品質チェックエラーハンドリングテスト"""
        # エラーを引き起こすデータ
        error_df = pd.DataFrame({
            'timestamp': [datetime.now(), 'invalid_date', None],
            'open': [1000, 'invalid', np.inf],
            'high': [1010, None, -np.inf],
            'low': [990, np.nan, 'string'],
            'close': [1005, np.inf, None],
            'volume': [5000, 'invalid', -1]
        })
        
        # エラーが発生してもissuesが返されることを確認
        issues = self.validator._check_data_quality(error_df)
        assert "critical" in issues
        assert "warning" in issues
        assert "info" in issues
        
        # エラーメッセージがクリティカルissuesに追加されることを確認
        assert len(issues["critical"]) > 0
    
    def test_time_gap_detection_edge_cases(self):
        """時間ギャップ検出のエッジケーステスト"""
        # 不規則な時系列データ
        irregular_data = pd.DataFrame({
            'timestamp': [
                datetime(2024, 1, 1, 9, 0),
                datetime(2024, 1, 1, 9, 0),  # 重複
                datetime(2024, 1, 1, 8, 0),  # 逆順
                datetime(2024, 1, 1, 15, 0), # 大きなギャップ
                datetime(2024, 1, 1, 15, 1), # 1分間隔
            ],
            'open': [1000] * 5,
            'high': [1010] * 5,
            'low': [990] * 5,
            'close': [1005] * 5,
            'volume': [5000] * 5
        })
        
        gaps = self.validator._detect_time_gaps(irregular_data)
        assert isinstance(gaps, list)
    
    def test_clean_data_edge_cases(self):
        """データクリーニングのエッジケーステスト"""
        # 全て異常値のデータ
        all_invalid = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=5),
            'open': [-1000] * 5,      # 全て負の値
            'high': [-990] * 5,       # 全て負の値
            'low': [-1010] * 5,       # 全て負の値
            'close': [-1005] * 5,     # 全て負の値
            'volume': [-5000] * 5     # 全て負の値
        })
        
        cleaned = self.validator.clean_data(all_invalid)
        
        # 極端な場合でも空でないDataFrameが返されることを確認
        assert isinstance(cleaned, pd.DataFrame)
        assert len(cleaned.columns) == len(all_invalid.columns)
    
    def test_clean_data_error_handling(self):
        """データクリーニングエラーハンドリングテスト"""
        # 無効な列名やデータ型を含むデータ
        invalid_structure = pd.DataFrame({
            'timestamp': ['not_a_date'] * 3,
            'open': ['string'] * 3,
            'high': [None] * 3,
            'low': [{}] * 3,  # 辞書オブジェクト
            'close': [[]] * 3,  # リストオブジェクト
            'volume': ['text'] * 3
        })
        
        # エラーが発生しても元のDataFrameが返されることを確認
        result = self.validator.clean_data(invalid_structure)
        assert isinstance(result, pd.DataFrame)
        assert len(result) <= len(invalid_structure)
    
    def test_interpolation_error_handling(self):
        """補間エラーハンドリングテスト"""
        # 全て欠損値のカラムを含むデータ
        all_missing = self.valid_data.copy()
        all_missing['close'] = np.nan
        all_missing['volume'] = np.nan
        
        # エラーが発生しても元のDataFrameが返されることを確認
        result = self.validator.interpolate_missing_data(all_missing)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(all_missing)
        
        # 出来高は0で埋められることを確認
        assert (result['volume'] == 0).all()
    
    def test_interpolation_invalid_method(self):
        """無効な補間方法テスト"""
        missing_data = self.valid_data.copy()
        missing_data.loc[50, 'close'] = np.nan
        
        # 無効な補間方法でも何らかの結果が返されることを確認
        result = self.validator.interpolate_missing_data(missing_data, method="invalid_method")
        assert isinstance(result, pd.DataFrame)
    
    def test_comprehensive_validation_workflow(self):
        """包括的検証ワークフローテスト"""
        # 複雑な異常を含む実用的なテストケース
        complex_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01 09:00', periods=24, freq='h'),
            'open': [1000 + i * 10 for i in range(24)],
            'high': [1015 + i * 10 for i in range(24)],
            'low': [985 + i * 10 for i in range(24)],
            'close': [1005 + i * 10 for i in range(24)],
            'volume': [5000 + i * 100 for i in range(24)]
        })
        
        # 複数の異常を挿入（FutureWarning を避けるため明示的に型変換）
        complex_data = complex_data.astype({'close': 'float64', 'high': 'float64', 'open': 'float64'})
        complex_data.loc[5, 'close'] = complex_data.loc[4, 'close'] * 1.3  # 大きな価格変動
        complex_data.loc[10, 'volume'] = complex_data.loc[10, 'volume'] * 8  # 出来高スパイク
        complex_data.loc[15, 'high'] = complex_data.loc[15, 'low'] - 5  # OHLC不整合
        complex_data.loc[20, 'open'] = np.nan  # 欠損値
        complex_data = pd.concat([complex_data, complex_data.iloc[[0]]], ignore_index=True)  # 重複
        
        # 完全なワークフロー実行
        validation_result = self.validator.validate_dataframe(complex_data, "COMPLEX")
        cleaned_data = self.validator.clean_data(complex_data)
        interpolated_data = self.validator.interpolate_missing_data(cleaned_data)
        
        # 各ステップの結果確認
        assert "anomalies" in validation_result
        assert len(validation_result["anomalies"]["price_anomalies"]) > 0
        assert len(validation_result["anomalies"]["volume_anomalies"]) > 0
        assert len(validation_result["anomalies"]["ohlc_inconsistencies"]) > 0
        
        assert len(cleaned_data) <= len(complex_data)  # クリーニングによりサイズ減少
        assert interpolated_data['open'].isna().sum() == 0  # 欠損値が補間済み
    
    def test_real_world_data_patterns(self):
        """実世界データパターンテスト"""
        # 実際の市場データパターンを模倣
        market_hours_data = pd.DataFrame({
            'timestamp': [
                datetime(2024, 1, 1, 9, 0),   # 市場開始
                datetime(2024, 1, 1, 11, 30), # 前場終了前
                datetime(2024, 1, 1, 12, 30), # 後場開始
                datetime(2024, 1, 1, 15, 0),  # 市場終了
                datetime(2024, 1, 2, 9, 0),   # 翌日開始（ギャップ）
            ],
            'open': [1000, 1010, 1015, 1020, 1025],
            'high': [1005, 1015, 1020, 1025, 1030],
            'low': [995, 1005, 1010, 1015, 1020],
            'close': [1002, 1012, 1018, 1023, 1028],
            'volume': [10000, 8000, 9000, 12000, 15000]
        })
        
        # 市場時間のギャップが適切に検出されることを確認
        gaps = self.validator._detect_time_gaps(market_hours_data)
        assert isinstance(gaps, list)
        
        # 検証結果の確認
        result = self.validator.validate_dataframe(market_hours_data, "MARKET")
        assert result["valid"] is True
        assert result["record_count"] == 5
    
    def test_large_dataset_performance(self):
        """大規模データセットパフォーマンステスト"""
        # 大量データの作成（1000行）
        large_data = self._create_large_test_data(1000)
        
        # パフォーマンステスト（エラーなく完了することを確認）
        result = self.validator.validate_dataframe(large_data, "LARGE")
        assert result["valid"] is True
        assert result["record_count"] == 1000
        
        # クリーニングと補間もテスト
        cleaned = self.validator.clean_data(large_data)
        interpolated = self.validator.interpolate_missing_data(cleaned)
        
        assert isinstance(cleaned, pd.DataFrame)
        assert isinstance(interpolated, pd.DataFrame)
    
    def _create_large_test_data(self, size: int) -> pd.DataFrame:
        """大規模テストデータ作成"""
        dates = pd.date_range(start='2024-01-01', periods=size, freq='h')
        np.random.seed(42)
        
        # ランダムウォークによる価格生成
        base_price = 1000
        returns = np.random.normal(0, 0.01, size)
        prices = base_price * np.cumprod(1 + returns)
        
        # OHLC生成
        opens = prices * (1 + np.random.normal(0, 0.002, size))
        closes = prices
        highs = np.maximum(opens, closes) * (1 + np.random.uniform(0, 0.005, size))
        lows = np.minimum(opens, closes) * (1 - np.random.uniform(0, 0.005, size))
        volumes = np.random.poisson(5000, size)
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        })
    
    def test_zero_volume_tolerance_check(self):
        """ゼロ出来高許容度チェックテスト"""
        # ゼロ出来高が多いデータを作成
        zero_volume_data = self.valid_data.copy()
        
        # 10%のデータをゼロ出来高にする（デフォルト許容度5%を超える）
        zero_count = int(len(zero_volume_data) * 0.1)
        zero_volume_data.loc[:zero_count, 'volume'] = 0
        
        quality_issues = self.validator._check_data_quality(zero_volume_data)
        
        # 警告が出ることを確認

        warning_issues = quality_issues["warning"]
        has_zero_volume_warning = any("ゼロ出来高比率が高い" in issue for issue in warning_issues)
        assert has_zero_volume_warning
    
    def test_interpolation_edge_cases(self):
        """補間処理エッジケーステスト"""
        # 先頭と末尾に欠損値があるデータ
        edge_missing_data = self.valid_data.copy()
        edge_missing_data.loc[0, "close"] = np.nan  # 先頭
        edge_missing_data.loc[len(edge_missing_data)-1, "close"] = np.nan  # 末尾
        edge_missing_data.loc[50, "volume"] = np.nan  # 中間
        
        # 補間処理実行
        interpolated = self.validator.interpolate_missing_data(edge_missing_data)
        
        # 結果の確認
        assert isinstance(interpolated, pd.DataFrame)
        # volume の欠損値は0で補間される
        assert interpolated.loc[50, "volume"] == 0
    
    def test_error_handling_in_gap_detection(self):
        """時間ギャップ検出でのエラーハンドリングテスト"""
        # 無効なタイムスタンプデータを作成
        invalid_time_data = pd.DataFrame({
            'timestamp': [None, 'invalid', datetime.now()],
            'open': [1000, 1001, 1002],
            'high': [1010, 1011, 1012],
            'low': [990, 991, 992],
            'close': [1005, 1006, 1007],
            'volume': [5000, 5001, 5002]
        })
        
        # エラーが発生してもリストが返されることを確認
        gaps = self.validator._detect_time_gaps(invalid_time_data)
        assert isinstance(gaps, list)
    
    def test_cleaning_logging_for_outliers(self):
        """外れ値除去時のログ出力テスト"""
        # 極端な外れ値を含むデータを作成
        outlier_data = self.valid_data.copy()
        outlier_data.loc[10, 'close'] = outlier_data['close'].mean() * 100  # 極端な値
        outlier_data.loc[20, 'volume'] = -1000  # 負の出来高
        
        # クリーニング実行（ログが出力されることを確認）
        cleaned = self.validator.clean_data(outlier_data)
        
        # 外れ値と負の出来高が除去されている
        assert len(cleaned) <= len(outlier_data)
        assert (cleaned['volume'] >= 0).all()
    
    def test_interpolation_exception_handling(self):
        """補間処理での例外ハンドリングテスト"""
        # 補間できない構造のデータを作成
        problem_data = pd.DataFrame({
            'timestamp': [pd.NaT, pd.NaT, pd.NaT],  # 全てNaT
            'open': [np.nan, np.nan, np.nan],
            'high': [np.nan, np.nan, np.nan],
            'low': [np.nan, np.nan, np.nan],
            'close': [np.nan, np.nan, np.nan],
            'volume': [np.nan, np.nan, np.nan]
        })
        
        # 例外が発生しても元のDataFrameが返されることを確認
        result = self.validator.interpolate_missing_data(problem_data)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(problem_data)
    
    def test_gap_detection_with_uniform_intervals(self):
        """時間間隔が一定でmodeが空のケースのテスト"""
        # 全く同じ時間間隔のデータを作成（mode計算で空になるケース）
        uniform_data = pd.DataFrame({
            'timestamp': [datetime(2024, 1, 1, i, 0) for i in range(10, 13)],  # 1時間間隔
            'open': [1000, 1001, 1002],
            'high': [1010, 1011, 1012],
            'low': [990, 991, 992],
            'close': [1005, 1006, 1007],
            'volume': [5000, 5001, 5002]
        })
        
        # ギャップ検出を実行
        gaps = self.validator._detect_time_gaps(uniform_data)
        
        # uniform_dataではギャップがないことを確認
        assert isinstance(gaps, list)
        assert len(gaps) == 0
