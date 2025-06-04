"""
StockDataCollectorの配当・株式分割カラム対応テスト
Issue #88の修正確認用
"""

import pytest
import pandas as pd
import numpy as np
import sqlite3
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch
import sys

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.data_collector.stock_data_collector import StockDataCollector


class TestStockDataCollectorDividends:
    """配当・株式分割カラムに関するテスト"""
    
    def setup_method(self):
        """各テストメソッド実行前の初期化"""
        self.temp_dir = tempfile.mkdtemp()
        self.collector = StockDataCollector(cache_dir=self.temp_dir, max_workers=2)
        self.test_symbol = "7203.T"
    
    def teardown_method(self):
        """各テストメソッド実行後のクリーンアップ"""
        if hasattr(self, 'temp_dir') and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_save_to_cache_with_dividends_columns(self):
        """Dividendsと Stock Splitsカラムを含むデータの保存テスト"""
        # yfinanceから取得される実際のデータ構造を模倣
        dates = pd.date_range(start='2024-01-01', periods=5, freq='D')
        test_data = pd.DataFrame({
            'timestamp': dates,
            'open': [1000, 1001, 1002, 1003, 1004],
            'high': [1005, 1006, 1007, 1008, 1009],
            'low': [995, 996, 997, 998, 999],
            'close': [1002, 1003, 1004, 1005, 1006],
            'volume': [10000, 11000, 12000, 13000, 14000],
            'Dividends': [0.0, 0.0, 10.0, 0.0, 0.0],  # 配当情報
            'Stock Splits': [0.0, 0.0, 0.0, 2.0, 0.0],  # 株式分割情報
            'symbol': self.test_symbol,
            'interval': '1d',
            'created_at': datetime.now().isoformat()
        })
        
        # エラーが発生しないことを確認
        try:
            self.collector._save_to_cache(test_data)
        except Exception as e:
            pytest.fail(f"キャッシュ保存でエラーが発生しました: {str(e)}")
        
        # データベースに正しく保存されたことを確認
        with sqlite3.connect(self.collector.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM stock_data WHERE symbol = ?", (self.test_symbol,))
            count = cursor.fetchone()[0]
            assert count == len(test_data)
            
            # 保存されたカラムを確認（Dividends, Stock Splitsは含まれない）
            cursor.execute("SELECT * FROM stock_data WHERE symbol = ? LIMIT 1", (self.test_symbol,))
            row = cursor.fetchone()
            cursor.execute("PRAGMA table_info(stock_data)")
            columns = [col[1] for col in cursor.fetchall()]
            
            assert 'dividends' not in columns
            assert 'stock_splits' not in columns
    
    @patch('src.data_collector.stock_data_collector.yf.Ticker')
    def test_fetch_data_with_dividends_columns(self, mock_ticker):
        """yfinanceから配当・株式分割カラムを含むデータを取得するテスト"""
        # yfinanceの実際の応答を模倣
        mock_history_data = pd.DataFrame({
            'Open': [1000, 1001, 1002],
            'High': [1005, 1006, 1007],
            'Low': [995, 996, 997],
            'Close': [1002, 1003, 1004],
            'Volume': [10000, 11000, 12000],
            'Dividends': [0.0, 5.0, 0.0],
            'Stock Splits': [0.0, 0.0, 2.0]
        }, index=pd.date_range('2024-01-01', periods=3, freq='D'))
        
        mock_ticker_instance = Mock()
        mock_ticker_instance.history.return_value = mock_history_data
        mock_ticker.return_value = mock_ticker_instance
        
        # データ取得実行
        result = self.collector._fetch_data_yfinance(self.test_symbol, "1d", "3d")
        
        # 基本的なデータが取得できていることを確認
        assert result is not None
        assert len(result) == 3
        assert 'open' in result.columns
        assert 'close' in result.columns
        
        # 配当・株式分割カラムが処理されていることを確認
        # （フィルタリングにより削除されるか、またはマッピングされる）
        # 現在の実装では、これらのカラムは _save_to_cache でフィルタリングされる
    
    def test_database_schema_unchanged(self):
        """データベーススキーマが変更されていないことを確認"""
        with sqlite3.connect(self.collector.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(stock_data)")
            columns = [row[1] for row in cursor.fetchall()]
            
            # 既存のスキーマが保持されていることを確認
            expected_columns = ['symbol', 'interval', 'timestamp', 'open', 'high', 
                              'low', 'close', 'volume', 'created_at']
            for col in expected_columns:
                assert col in columns
            
            # 新しいカラムが追加されていないことを確認
            assert 'dividends' not in columns
            assert 'stock_splits' not in columns
    
    def test_backward_compatibility(self):
        """既存データとの後方互換性テスト"""
        # 既存形式のデータを保存
        old_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=3, freq='D'),
            'open': [1000, 1001, 1002],
            'high': [1005, 1006, 1007],
            'low': [995, 996, 997],
            'close': [1002, 1003, 1004],
            'volume': [10000, 11000, 12000],
            'symbol': '6758.T',
            'interval': '1d',
            'created_at': datetime.now().isoformat()
        })
        
        # 保存とロードが正常に動作することを確認
        self.collector._save_to_cache(old_data)
        loaded_data = self.collector._load_from_cache('6758.T', '1d')
        
        assert loaded_data is not None
        assert len(loaded_data) == len(old_data)
        assert set(loaded_data['symbol'].unique()) == {'6758.T'}
    
    @patch('src.data_collector.stock_data_collector.yf.Ticker')
    def test_full_pipeline_with_dividends(self, mock_ticker):
        """配当情報を含む完全なデータパイプラインテスト"""
        # モックデータの設定
        mock_history_data = pd.DataFrame({
            'Open': [1000, 1001],
            'High': [1005, 1006],
            'Low': [995, 996],
            'Close': [1002, 1003],
            'Volume': [10000, 11000],
            'Dividends': [0.0, 10.0],
            'Stock Splits': [0.0, 0.0]
        }, index=pd.date_range('2024-01-01', periods=2, freq='D'))
        
        mock_ticker_instance = Mock()
        mock_ticker_instance.history.return_value = mock_history_data
        mock_ticker.return_value = mock_ticker_instance
        
        # get_stock_dataを通じた完全なフロー
        result = self.collector.get_stock_data(self.test_symbol, "1d", "2d", use_cache=True)
        
        # データが正常に取得・保存されることを確認
        assert result is not None
        assert len(result) == 2
        
        # キャッシュから再度読み込めることを確認
        cached_result = self.collector.get_stock_data(self.test_symbol, "1d", use_cache=True)
        assert cached_result is not None
        assert len(cached_result) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])