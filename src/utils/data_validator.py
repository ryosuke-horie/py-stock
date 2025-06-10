from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger


class DataValidator:
    """
    株価データ検証クラス
    データ品質チェック、異常値検出、欠損値処理
    """
    
    def __init__(self):
        # 異常値検出の閾値
        self.price_change_threshold = 0.2  # 20%以上の価格変動
        self.volume_spike_threshold = 5.0  # 通常の5倍以上の出来高
        self.zero_volume_tolerance = 0.05  # 5%までのゼロ出来高は許容
    
    def validate_dataframe(self, df: pd.DataFrame, symbol: str = "") -> Dict[str, Any]:
        """
        DataFrameの基本検証
        
        Args:
            df: 株価データのDataFrame
            symbol: 銘柄コード（ログ用）
            
        Returns:
            検証結果の辞書
        """
        if df is None or df.empty:
            return {
                "valid": False,
                "error": "データが空です",
                "symbol": symbol
            }
        
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return {
                "valid": False,
                "error": f"必要なカラムがありません: {missing_columns}",
                "symbol": symbol
            }
        
        # 基本統計
        stats = self._calculate_basic_stats(df)
        
        # 異常値検出
        anomalies = self._detect_anomalies(df)
        
        # データ品質チェック
        quality_issues = self._check_data_quality(df)
        
        result = {
            "valid": len(quality_issues["critical"]) == 0,
            "symbol": symbol,
            "record_count": len(df),
            "date_range": {
                "start": df['timestamp'].min(),
                "end": df['timestamp'].max()
            },
            "statistics": stats,
            "anomalies": anomalies,
            "quality_issues": quality_issues
        }
        
        if result["valid"]:
            logger.info(f"データ検証OK: {symbol} ({len(df)}件)")
        else:
            logger.warning(f"データ検証NG: {symbol} - {quality_issues['critical']}")
        
        return result
    
    def _calculate_basic_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """基本統計の計算"""
        try:
            price_cols = ['open', 'high', 'low', 'close']
            
            stats = {
                "price_range": {
                    "min": df[price_cols].min().min(),
                    "max": df[price_cols].max().max(),
                    "mean_close": df['close'].mean()
                },
                "volume_stats": {
                    "total": df['volume'].sum(),
                    "mean": df['volume'].mean(),
                    "median": df['volume'].median(),
                    "zero_volume_ratio": (df['volume'] == 0).sum() / len(df)
                },
                "missing_data": {
                    col: df[col].isna().sum() for col in df.columns
                },
                "data_gaps": self._detect_time_gaps(df)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"統計計算エラー: {e}")
            return {}
    
    def _detect_anomalies(self, df: pd.DataFrame) -> Dict[str, List]:
        """異常値検出"""
        anomalies = {
            "price_anomalies": [],
            "volume_anomalies": [],
            "ohlc_inconsistencies": []
        }
        
        try:
            # 価格変動の異常検出
            df_temp = df.copy()  # 元のDataFrameを変更しないようにコピー
            df_temp['price_change'] = df_temp['close'].pct_change(fill_method=None)
            # FutureWarning を避けるため、explicit に float64 を指定
            df_temp['price_change'] = df_temp['price_change'].astype('float64')
            extreme_changes = df_temp[abs(df_temp['price_change']) > self.price_change_threshold]
            
            for idx, row in extreme_changes.iterrows():
                anomalies["price_anomalies"].append({
                    "timestamp": row['timestamp'],
                    "change_rate": float(row['price_change']),  # numpy型を明示的にfloatに変換
                    "price": float(row['close'])
                })
            
            # 出来高の異常検出
            volume_mean = df['volume'].mean()
            volume_spikes = df[df['volume'] > volume_mean * self.volume_spike_threshold]
            
            for idx, row in volume_spikes.iterrows():
                anomalies["volume_anomalies"].append({
                    "timestamp": row['timestamp'],
                    "volume": row['volume'],
                    "ratio_to_mean": row['volume'] / volume_mean
                })
            
            # OHLC整合性チェック
            ohlc_issues = df[
                (df['high'] < df['low']) |
                (df['high'] < df['open']) |
                (df['high'] < df['close']) |
                (df['low'] > df['open']) |
                (df['low'] > df['close'])
            ]
            
            for idx, row in ohlc_issues.iterrows():
                anomalies["ohlc_inconsistencies"].append({
                    "timestamp": row['timestamp'],
                    "open": row['open'],
                    "high": row['high'],
                    "low": row['low'],
                    "close": row['close']
                })
                
        except Exception as e:
            logger.error(f"異常値検出エラー: {e}")
        
        return anomalies
    
    def _check_data_quality(self, df: pd.DataFrame) -> Dict[str, List]:
        """データ品質チェック"""
        issues = {
            "critical": [],
            "warning": [],
            "info": []
        }
        
        try:
            # 重複データチェック
            duplicates = df.duplicated(subset=['timestamp']).sum()
            if duplicates > 0:
                issues["warning"].append(f"重複データ: {duplicates}件")
            
            # 欠損値チェック
            for col in ['open', 'high', 'low', 'close']:
                missing_count = df[col].isna().sum()
                if missing_count > 0:
                    issues["critical"].append(f"{col}カラムに欠損値: {missing_count}件")
            
            # 負の価格チェック
            for col in ['open', 'high', 'low', 'close']:
                negative_count = (df[col] <= 0).sum()
                if negative_count > 0:
                    issues["critical"].append(f"{col}カラムに負の値: {negative_count}件")
            
            # 出来高チェック
            negative_volume = (df['volume'] < 0).sum()
            if negative_volume > 0:
                issues["critical"].append(f"負の出来高: {negative_volume}件")
            
            zero_volume_ratio = (df['volume'] == 0).sum() / len(df)
            if zero_volume_ratio > self.zero_volume_tolerance:
                issues["warning"].append(f"ゼロ出来高比率が高い: {zero_volume_ratio:.2%}")
            
            # 時系列の順序チェック
            if not df['timestamp'].is_monotonic_increasing:
                issues["warning"].append("時系列データが昇順ではありません")
                
        except Exception as e:
            logger.error(f"品質チェックエラー: {e}")
            issues["critical"].append(f"品質チェック処理エラー: {e}")
        
        return issues
    
    def _detect_time_gaps(self, df: pd.DataFrame) -> List[Dict]:
        """時系列データのギャップ検出"""
        gaps = []
        
        try:
            if len(df) < 2:
                return gaps
            
            # 時間差を計算
            df_sorted = df.sort_values('timestamp')
            time_diffs = df_sorted['timestamp'].diff()
            
            # 通常の間隔を推定（最頻値）
            mode_diff = time_diffs.mode()
            if len(mode_diff) > 0:
                expected_interval = mode_diff.iloc[0]
                
                # 期待値の2倍以上のギャップを検出
                large_gaps = time_diffs[time_diffs > expected_interval * 2]
                
                for idx, gap in large_gaps.items():
                    if idx > 0:  # 最初の行はNaNなのでスキップ
                        gaps.append({
                            "start_time": df_sorted.iloc[idx-1]['timestamp'],
                            "end_time": df_sorted.iloc[idx]['timestamp'],
                            "gap_duration": gap,
                            "expected_duration": expected_interval
                        })
                        
        except Exception as e:
            logger.error(f"時間ギャップ検出エラー: {e}")
        
        return gaps
    
    def clean_data(self, df: pd.DataFrame, remove_duplicates: bool = True) -> pd.DataFrame:
        """
        データクリーニング
        
        Args:
            df: 元のDataFrame
            remove_duplicates: 重複除去フラグ
            
        Returns:
            クリーニング済みのDataFrame
        """
        cleaned_df = df.copy()
        
        try:
            # 重複除去
            if remove_duplicates:
                before_count = len(cleaned_df)
                cleaned_df = cleaned_df.drop_duplicates(subset=['timestamp'])
                after_count = len(cleaned_df)
                if before_count != after_count:
                    logger.info(f"重複データ除去: {before_count - after_count}件")
            
            # 時系列ソート
            cleaned_df = cleaned_df.sort_values('timestamp').reset_index(drop=True)
            
            # 異常値の処理（極端な外れ値を除去）
            price_cols = ['open', 'high', 'low', 'close']
            for col in price_cols:
                # 負の値を除去
                cleaned_df = cleaned_df[cleaned_df[col] > 0]
                
                # 外れ値の除去（IQR法）
                Q1 = cleaned_df[col].quantile(0.25)
                Q3 = cleaned_df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 3 * IQR  # 通常は1.5だが、株価の変動を考慮して3に
                upper_bound = Q3 + 3 * IQR
                
                before_count = len(cleaned_df)
                cleaned_df = cleaned_df[
                    (cleaned_df[col] >= max(lower_bound, 0)) & 
                    (cleaned_df[col] <= upper_bound)
                ]
                after_count = len(cleaned_df)
                
                if before_count != after_count:
                    logger.info(f"{col}カラムの外れ値除去: {before_count - after_count}件")
            
            # 負の出来高を除去
            before_count = len(cleaned_df)
            cleaned_df = cleaned_df[cleaned_df['volume'] >= 0]
            after_count = len(cleaned_df)
            
            if before_count != after_count:
                logger.info(f"負の出来高除去: {before_count - after_count}件")
            
            logger.info(f"データクリーニング完了: {len(df)} -> {len(cleaned_df)}件")
            
        except Exception as e:
            logger.error(f"データクリーニングエラー: {e}")
            return df
        
        return cleaned_df
    
    def interpolate_missing_data(
        self, 
        df: pd.DataFrame, 
        method: str = "linear"
    ) -> pd.DataFrame:
        """
        欠損データの補間
        
        Args:
            df: 元のDataFrame
            method: 補間方法 ('linear', 'forward', 'backward')
            
        Returns:
            補間済みのDataFrame
        """
        interpolated_df = df.copy()
        
        try:
            price_cols = ['open', 'high', 'low', 'close']
            
            for col in price_cols:
                missing_before = interpolated_df[col].isna().sum()
                
                if missing_before > 0:
                    if method == "linear":
                        interpolated_df[col] = interpolated_df[col].interpolate(method='linear')
                    elif method == "forward":
                        interpolated_df[col] = interpolated_df[col].ffill()
                    elif method == "backward":
                        interpolated_df[col] = interpolated_df[col].bfill()
                    
                    missing_after = interpolated_df[col].isna().sum()
                    if missing_before != missing_after:
                        logger.info(f"{col}カラムの欠損値補間: {missing_before - missing_after}件")
            
            # 出来高の欠損値は0で埋める
            volume_missing = interpolated_df['volume'].isna().sum()
            if volume_missing > 0:
                interpolated_df['volume'] = interpolated_df['volume'].fillna(0)
                logger.info(f"出来高の欠損値を0で補間: {volume_missing}件")
                
        except Exception as e:
            logger.error(f"補間処理エラー: {e}")
            return df
        
        return interpolated_df