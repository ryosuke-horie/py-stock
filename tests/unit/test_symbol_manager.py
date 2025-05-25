"""
SymbolManagerクラスのテスト
"""

import pytest
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from src.data_collector.symbol_manager import SymbolManager, MarketType


class TestSymbolManager:
    """SymbolManagerのテストクラス"""
    
    def setup_method(self):
        """各テストメソッド実行前の初期化"""
        self.symbol_manager = SymbolManager()
    
    def test_detect_market_type_japan(self):
        """日本株の市場タイプ判定テスト"""
        # 4桁数字のパターン
        assert self.symbol_manager.detect_market_type("7203") == MarketType.JAPAN
        assert self.symbol_manager.detect_market_type("9984") == MarketType.JAPAN
        
        # .Tサフィックス付き
        assert self.symbol_manager.detect_market_type("7203.T") == MarketType.JAPAN
        assert self.symbol_manager.detect_market_type("9984.T") == MarketType.JAPAN
        
        # .JPサフィックス付き
        assert self.symbol_manager.detect_market_type("7203.JP") == MarketType.JAPAN
    
    def test_detect_market_type_us(self):
        """米国株の市場タイプ判定テスト"""
        # 一般的な米国株コード
        assert self.symbol_manager.detect_market_type("AAPL") == MarketType.US
        assert self.symbol_manager.detect_market_type("MSFT") == MarketType.US
        assert self.symbol_manager.detect_market_type("GOOGL") == MarketType.US
        
        # 1文字のコード
        assert self.symbol_manager.detect_market_type("V") == MarketType.US
        
        # 5文字のコード
        assert self.symbol_manager.detect_market_type("GOOGL") == MarketType.US
    
    def test_detect_market_type_unknown(self):
        """未知の市場タイプ判定テスト"""
        # 無効なパターン
        assert self.symbol_manager.detect_market_type("123") == MarketType.UNKNOWN
        assert self.symbol_manager.detect_market_type("12345") == MarketType.UNKNOWN
        assert self.symbol_manager.detect_market_type("TOOLONG") == MarketType.UNKNOWN
        assert self.symbol_manager.detect_market_type("7203.INVALID") == MarketType.UNKNOWN
    
    def test_normalize_symbol_japan(self):
        """日本株銘柄コード正規化テスト"""
        # 4桁数字 -> .T付きに正規化
        assert self.symbol_manager.normalize_symbol("7203") == "7203.T"
        assert self.symbol_manager.normalize_symbol("9984") == "9984.T"
        
        # 既に.T付きの場合はそのまま
        assert self.symbol_manager.normalize_symbol("7203.T") == "7203.T"
        
        # .JP -> .Tに正規化
        assert self.symbol_manager.normalize_symbol("7203.JP") == "7203.T"
    
    def test_normalize_symbol_us(self):
        """米国株銘柄コード正規化テスト"""
        # 大文字変換
        assert self.symbol_manager.normalize_symbol("aapl") == "AAPL"
        assert self.symbol_manager.normalize_symbol("msft") == "MSFT"
        
        # 既に大文字の場合はそのまま
        assert self.symbol_manager.normalize_symbol("GOOGL") == "GOOGL"
        
        # 空白削除
        assert self.symbol_manager.normalize_symbol(" AAPL ") == "AAPL"
    
    def test_get_symbol_info(self):
        """銘柄情報取得テスト"""
        # 日本株（既知銘柄）
        info = self.symbol_manager.get_symbol_info("7203")
        assert info["original"] == "7203"
        assert info["normalized"] == "7203.T"
        assert info["market_type"] == "japan"
        assert info["name"] == "トヨタ自動車"
        
        # 米国株（既知銘柄）
        info = self.symbol_manager.get_symbol_info("AAPL")
        assert info["original"] == "AAPL"
        assert info["normalized"] == "AAPL"
        assert info["market_type"] == "us"
        assert info["name"] == "Apple Inc."
        
        # 未知銘柄
        info = self.symbol_manager.get_symbol_info("1234")
        assert info["name"] == "N/A"
    
    def test_validate_symbols(self):
        """銘柄コード検証テスト"""
        symbols = ["7203", "AAPL", "INVALID", "9984", "MSFT", "123"]
        
        valid, invalid = self.symbol_manager.validate_symbols(symbols)
        
        # 有効な銘柄
        assert "7203.T" in valid
        assert "AAPL" in valid
        assert "9984.T" in valid
        assert "MSFT" in valid
        
        # 無効な銘柄
        assert "INVALID" in invalid
        assert "123" in invalid
    
    def test_create_watchlist(self):
        """ウォッチリスト作成テスト"""
        symbols = ["7203", "AAPL", "INVALID", "9984"]
        
        watchlist = self.symbol_manager.create_watchlist("テスト", symbols)
        
        assert watchlist["name"] == "テスト"
        assert len(watchlist["symbols"]) == 3  # 有効な銘柄数
        assert len(watchlist["invalid_symbols"]) == 1  # 無効な銘柄数
        assert watchlist["symbol_count"] == 3
        assert "7203.T" in watchlist["symbols"]
        assert "AAPL" in watchlist["symbols"]
        assert "9984.T" in watchlist["symbols"]
        assert "INVALID" in watchlist["invalid_symbols"]
    
    def test_get_sample_symbols(self):
        """サンプル銘柄取得テスト"""
        # 日本株サンプル
        japan_samples = self.symbol_manager.get_sample_symbols(MarketType.JAPAN, 3)
        assert len(japan_samples) == 3
        for symbol in japan_samples:
            assert symbol.endswith(".T")
        
        # 米国株サンプル
        us_samples = self.symbol_manager.get_sample_symbols(MarketType.US, 3)
        assert len(us_samples) == 3
        for symbol in us_samples:
            assert symbol.isupper()
            assert not symbol.endswith(".T")
        
        # 未知の市場タイプ
        unknown_samples = self.symbol_manager.get_sample_symbols(MarketType.UNKNOWN, 3)
        assert len(unknown_samples) == 0
    
    def test_get_market_hours_info(self):
        """市場時間情報取得テスト"""
        # 日本市場
        japan_info = self.symbol_manager.get_market_hours_info(MarketType.JAPAN)
        assert "東京証券取引所" in japan_info["market"]
        assert japan_info["timezone"] == "Asia/Tokyo"
        assert "09:00-11:30" in japan_info["regular_hours"]
        
        # 米国市場
        us_info = self.symbol_manager.get_market_hours_info(MarketType.US)
        assert "米国市場" in us_info["market"]
        assert us_info["timezone"] == "America/New_York"
        assert "09:30-16:00" in us_info["regular_hours"]
        
        # 未知の市場
        unknown_info = self.symbol_manager.get_market_hours_info(MarketType.UNKNOWN)
        assert unknown_info["market"] == "不明"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])