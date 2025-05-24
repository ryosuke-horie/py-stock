"""
ウォッチリストストレージのテスト
"""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime

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