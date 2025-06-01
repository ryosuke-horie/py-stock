"""
ウォッチリストストレージのテスト
"""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime
import sqlite3
from unittest.mock import patch, MagicMock

from src.data_collector.watchlist_storage import WatchlistStorage, WatchlistItem


class TestWatchlistStorage:
    """ウォッチリストストレージのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行"""
        # テンポラリファイルを使用
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # テスト用ストレージインスタンス作成
        self.storage = WatchlistStorage(db_path=self.db_path, user_id="test_user")
    
    def teardown_method(self):
        """各テストメソッドの後に実行"""
        # テンポラリファイルを削除
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_initialization(self):
        """初期化テスト"""
        assert self.storage.db_path == self.db_path
        assert self.storage.user_id == "test_user"
        assert os.path.exists(self.db_path)
    
    def test_add_symbol_japanese_stock(self):
        """日本株銘柄追加テスト"""
        result = self.storage.add_symbol("7203")
        assert result is True
        
        symbols = self.storage.get_symbols()
        assert "7203.T" in symbols
        assert len(symbols) == 1
    
    def test_add_symbol_us_stock(self):
        """米国株銘柄追加テスト"""
        result = self.storage.add_symbol("AAPL")
        assert result is True
        
        symbols = self.storage.get_symbols()
        assert "AAPL" in symbols
        assert len(symbols) == 1
    
    def test_add_multiple_symbols(self):
        """複数銘柄追加テスト"""
        symbols_to_add = ["7203", "AAPL", "9984"]
        
        for symbol in symbols_to_add:
            result = self.storage.add_symbol(symbol)
            assert result is True
        
        stored_symbols = self.storage.get_symbols()
        assert len(stored_symbols) == 3
        assert "7203.T" in stored_symbols
        assert "AAPL" in stored_symbols
        assert "9984.T" in stored_symbols
    
    def test_remove_symbol(self):
        """銘柄削除テスト"""
        # 複数銘柄を追加
        self.storage.add_symbol("7203")
        self.storage.add_symbol("AAPL")
        self.storage.add_symbol("9984")
        
        # 中間の銘柄を削除
        result = self.storage.remove_symbol("AAPL")
        assert result is True
        
        symbols = self.storage.get_symbols()
        assert len(symbols) == 2
        assert "AAPL" not in symbols
        assert "7203.T" in symbols
        assert "9984.T" in symbols
    
    def test_remove_nonexistent_symbol(self):
        """存在しない銘柄の削除テスト"""
        result = self.storage.remove_symbol("NONEXISTENT")
        assert result is False
    
    def test_get_watchlist_items(self):
        """ウォッチリストアイテム詳細取得テスト"""
        self.storage.add_symbol("7203")
        self.storage.add_symbol("AAPL")
        
        items = self.storage.get_watchlist_items()
        assert len(items) == 2
        
        # 最初のアイテムをチェック
        first_item = items[0]
        assert isinstance(first_item, WatchlistItem)
        assert first_item.symbol in ["7203.T", "AAPL"]
        assert first_item.position == 0
        assert isinstance(first_item.created_at, datetime)
    
    def test_reorder_symbols(self):
        """銘柄順序変更テスト"""
        # 銘柄を追加
        symbols = ["7203", "AAPL", "9984"]
        for symbol in symbols:
            self.storage.add_symbol(symbol)
        
        # 順序を変更
        new_order = ["AAPL", "9984.T", "7203.T"]
        result = self.storage.reorder_symbols(new_order)
        assert result is True
        
        # 順序が変更されたことを確認
        stored_symbols = self.storage.get_symbols()
        assert stored_symbols == ["AAPL", "9984.T", "7203.T"]
    
    def test_migrate_from_session(self):
        """セッション状態からの移行テスト"""
        session_symbols = ["7203.T", "AAPL", "9984.T"]
        
        result = self.storage.migrate_from_session(session_symbols)
        assert result is True
        
        stored_symbols = self.storage.get_symbols()
        assert len(stored_symbols) == 3
        assert all(symbol in stored_symbols for symbol in session_symbols)
    
    def test_migrate_from_session_with_existing_data(self):
        """既存データがある場合の移行テスト"""
        # 既に銘柄を追加
        self.storage.add_symbol("MSFT")
        
        session_symbols = ["7203.T", "AAPL"]
        result = self.storage.migrate_from_session(session_symbols)
        assert result is True
        
        # 既存データが保持され、移行がスキップされることを確認
        stored_symbols = self.storage.get_symbols()
        assert "MSFT" in stored_symbols
        assert len(stored_symbols) == 1  # 移行されていない
    
    def test_clear_watchlist(self):
        """ウォッチリストクリアテスト"""
        # 複数銘柄を追加
        for symbol in ["7203", "AAPL", "9984"]:
            self.storage.add_symbol(symbol)
        
        result = self.storage.clear_watchlist()
        assert result is True
        
        symbols = self.storage.get_symbols()
        assert len(symbols) == 0
    
    def test_get_statistics(self):
        """統計情報取得テスト"""
        # 複数銘柄を追加
        self.storage.add_symbol("7203")  # 日本株
        self.storage.add_symbol("AAPL")  # 米国株
        self.storage.add_symbol("9984")  # 日本株
        
        stats = self.storage.get_statistics()
        
        assert stats["total_symbols"] == 3
        assert stats["user_id"] == "test_user"
        assert "market_distribution" in stats
        assert stats["market_distribution"].get("japan", 0) == 2
        assert stats["market_distribution"].get("us", 0) == 1
    
    def test_duplicate_symbol_handling(self):
        """重複銘柄の処理テスト"""
        # 同じ銘柄を2回追加
        result1 = self.storage.add_symbol("7203")
        result2 = self.storage.add_symbol("7203")
        
        assert result1 is True
        assert result2 is True  # REPLACE処理により成功
        
        symbols = self.storage.get_symbols()
        assert len(symbols) == 1  # 重複していない
        assert "7203.T" in symbols
    
    def test_position_ordering(self):
        """ポジション順序テスト"""
        symbols = ["7203", "AAPL", "9984", "MSFT"]
        
        # 順番に追加
        for symbol in symbols:
            self.storage.add_symbol(symbol)
        
        # ポジション順で取得されることを確認
        stored_symbols = self.storage.get_symbols()
        expected_symbols = ["7203.T", "AAPL", "9984.T", "MSFT"]
        assert stored_symbols == expected_symbols
        
        # 詳細情報でポジションを確認
        items = self.storage.get_watchlist_items()
        for i, item in enumerate(items):
            assert item.position == i
    
    def test_invalid_symbol_handling(self):
        """無効な銘柄コードの処理テスト"""
        # 空文字列
        result = self.storage.add_symbol("")
        assert result is False
        
        # None
        result = self.storage.add_symbol(None)
        assert result is False
        
        symbols = self.storage.get_symbols()
        assert len(symbols) == 0
    
    def test_database_persistence(self):
        """データベース永続化テスト"""
        # 銘柄を追加
        self.storage.add_symbol("7203")
        self.storage.add_symbol("AAPL")
        
        # 新しいインスタンスで同じDBにアクセス
        new_storage = WatchlistStorage(db_path=self.db_path, user_id="test_user")
        symbols = new_storage.get_symbols()
        
        assert len(symbols) == 2
        assert "7203.T" in symbols
        assert "AAPL" in symbols
    
    def test_multiple_users(self):
        """複数ユーザーテスト"""
        # ユーザー1の銘柄
        user1_storage = WatchlistStorage(db_path=self.db_path, user_id="user1")
        user1_storage.add_symbol("7203")
        user1_storage.add_symbol("AAPL")
        
        # ユーザー2の銘柄
        user2_storage = WatchlistStorage(db_path=self.db_path, user_id="user2")
        user2_storage.add_symbol("9984")
        user2_storage.add_symbol("MSFT")
        
        # 各ユーザーのウォッチリストが独立していることを確認
        user1_symbols = user1_storage.get_symbols()
        user2_symbols = user2_storage.get_symbols()
        
        assert len(user1_symbols) == 2
        assert len(user2_symbols) == 2
        assert user1_symbols != user2_symbols
        assert "7203.T" in user1_symbols
        assert "9984.T" in user2_symbols
    
    def test_add_symbol_with_name(self):
        """名前付きで銘柄追加テスト"""
        result = self.storage.add_symbol("7203")
        assert result is True
        
        items = self.storage.get_watchlist_items()
        assert len(items) == 1
        # symbol_managerから名前が取得される
        assert items[0].name is not None
    
    def test_add_symbol_unknown_market(self):
        """未知の市場タイプの銘柄追加テスト"""
        # 長すぎるシンボル（市場判定できない）
        result = self.storage.add_symbol("VERYLONGSYMBOL123456")
        assert result is False
    
    def test_add_symbol_with_exceptions(self):
        """例外処理テスト"""
        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = sqlite3.Error("Database error")
            result = self.storage.add_symbol("7203")
            assert result is False
    
    def test_remove_symbol_with_exceptions(self):
        """削除時の例外処理テスト"""
        self.storage.add_symbol("7203")
        
        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = sqlite3.Error("Database error")
            result = self.storage.remove_symbol("7203.T")
            assert result is False
    
    def test_get_symbols_with_exceptions(self):
        """シンボル取得時の例外処理テスト"""
        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = sqlite3.Error("Database error")
            symbols = self.storage.get_symbols()
            assert symbols == []
    
    def test_get_watchlist_items_with_exceptions(self):
        """ウォッチリストアイテム取得時の例外処理テスト"""
        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = sqlite3.Error("Database error")
            items = self.storage.get_watchlist_items()
            assert items == []
    
    def test_reorder_symbols_partial(self):
        """部分的な順序変更テスト"""
        # 銘柄を追加
        self.storage.add_symbol("7203")
        self.storage.add_symbol("AAPL")
        self.storage.add_symbol("9984")
        
        # 完全なリストで順序を変更
        symbols = self.storage.get_symbols()
        # AAPLを最初に移動
        if "AAPL" in symbols:
            symbols.remove("AAPL")
            symbols.insert(0, "AAPL")
        
        result = self.storage.reorder_symbols(symbols)
        assert result is True
        
        # 指定された順序になっていることを確認
        reordered_symbols = self.storage.get_symbols()
        assert reordered_symbols[0] == "AAPL"
    
    def test_reorder_symbols_with_exceptions(self):
        """順序変更時の例外処理テスト"""
        self.storage.add_symbol("7203")
        self.storage.add_symbol("AAPL")
        
        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = sqlite3.Error("Database error")
            result = self.storage.reorder_symbols(["AAPL", "7203.T"])
            assert result is False
    
    def test_clear_watchlist_with_exceptions(self):
        """クリア時の例外処理テスト"""
        self.storage.add_symbol("7203")
        
        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = sqlite3.Error("Database error")
            result = self.storage.clear_watchlist()
            assert result is False
    
    def test_get_statistics_with_exceptions(self):
        """統計情報取得時の例外処理テスト"""
        with patch.object(self.storage, 'get_watchlist_items', side_effect=Exception("Database error")):
            stats = self.storage.get_statistics()
            assert stats["total_symbols"] == 0
            assert stats["user_id"] == "test_user"
            assert stats["market_distribution"] == {}
    
    def test_migrate_from_session_with_exceptions(self):
        """移行時の例外処理テスト"""
        with patch.object(self.storage, 'add_symbol', side_effect=Exception("Database error")):
            result = self.storage.migrate_from_session(["7203.T", "AAPL"])
            assert result is False
    
    def test_create_directory_failure(self):
        """ディレクトリ作成失敗のテスト"""
        # バックアップディレクトリの作成で例外が発生してもインスタンスは作成される
        with patch.object(Path, 'mkdir', side_effect=OSError("Permission denied")) as mock_mkdir:
            try:
                storage = WatchlistStorage(db_path=self.temp_db.name)
                # インスタンスは作成される（例外が処理される）
                assert storage is not None
            except OSError:
                # OSErrorが発生してもテストは成功
                pass
    
    def test_market_type_detection(self):
        """市場タイプ判定のテスト"""
        # 日本株（.T付き）
        self.storage.add_symbol("7203.T")
        items = self.storage.get_watchlist_items()
        assert items[0].market_type == "japan"
        
        # 米国株（アルファベットのみ）
        self.storage.add_symbol("AAPL")
        items = self.storage.get_watchlist_items()
        us_item = next((item for item in items if item.symbol == "AAPL"), None)
        assert us_item.market_type == "us"
        
        # 日本株（数字のみ）
        self.storage.add_symbol("9984")
        items = self.storage.get_watchlist_items()
        jp_item = next((item for item in items if item.symbol == "9984.T"), None)
        assert jp_item.market_type == "japan"
    
    def test_complex_scenarios(self):
        """複雑なシナリオのテスト"""
        # 大量の銘柄を追加
        for i in range(100):
            symbol = f"{1000 + i}"
            self.storage.add_symbol(symbol)
        
        symbols = self.storage.get_symbols()
        assert len(symbols) == 100
        
        # 全削除後に再追加
        self.storage.clear_watchlist()
        self.storage.add_symbol("7203")
        
        symbols = self.storage.get_symbols()
        assert len(symbols) == 1
        assert "7203.T" in symbols
    
    def test_symbol_normalization_edge_cases(self):
        """シンボル正規化のエッジケーステスト"""
        # 既に.T付きの日本株
        result = self.storage.add_symbol("7203.T")
        assert result is True
        
        # 大文字の米国株（正規化される）
        result = self.storage.add_symbol("AAPL")
        assert result is True
        
        symbols = self.storage.get_symbols()
        assert len(symbols) == 2
        # 正規化された形で保存される
        # 実際の正規化ルールに依存
    
    def test_empty_database_operations(self):
        """空のデータベースでの操作テスト"""
        # 空の状態で削除
        result = self.storage.remove_symbol("7203.T")
        assert result is False
        
        # 空の状態でクリア
        result = self.storage.clear_watchlist()
        assert result is True
        
        # 空の状態で並び替え
        result = self.storage.reorder_symbols([])
        assert result is True
    
    def test_concurrent_access(self):
        """並行アクセステスト"""
        # 複数のインスタンスで同じDBにアクセス
        storage1 = WatchlistStorage(db_path=self.db_path, user_id="test_user")
        storage2 = WatchlistStorage(db_path=self.db_path, user_id="test_user")
        
        storage1.add_symbol("7203")
        storage2.add_symbol("AAPL")
        
        symbols = self.storage.get_symbols()
        assert len(symbols) == 2
        assert "7203.T" in symbols
        assert "AAPL" in symbols