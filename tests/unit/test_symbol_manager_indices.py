"""SymbolManagerのインデックス管理機能のテスト"""

import pytest
from src.data_collector.symbol_manager import SymbolManager, MarketType


class TestSymbolManagerIndices:
    """SymbolManagerのインデックス関連機能のテスト"""
    
    @pytest.fixture
    def symbol_manager(self):
        """SymbolManagerのインスタンスを作成"""
        return SymbolManager()
    
    def test_index_symbols_definition(self, symbol_manager):
        """インデックスシンボルの定義をテスト"""
        # 主要インデックスが定義されているか確認
        assert "^N225" in symbol_manager.INDEX_SYMBOLS
        assert "^GSPC" in symbol_manager.INDEX_SYMBOLS
        assert "^VIX" in symbol_manager.INDEX_SYMBOLS
        
        # セクターETFが定義されているか確認
        assert "1475.T" in symbol_manager.INDEX_SYMBOLS
        assert symbol_manager.INDEX_SYMBOLS["1475.T"]["type"] == "sector_etf"
    
    def test_is_index_symbol(self, symbol_manager):
        """インデックスシンボル判定のテスト"""
        # インデックスシンボル
        assert symbol_manager.is_index_symbol("^N225") is True
        assert symbol_manager.is_index_symbol("^GSPC") is True
        assert symbol_manager.is_index_symbol("^VIX") is True
        assert symbol_manager.is_index_symbol("1305.T") is True
        
        # 通常の銘柄
        assert symbol_manager.is_index_symbol("7203.T") is False
        assert symbol_manager.is_index_symbol("AAPL") is False
        
        # ^で始まる未定義のシンボル
        assert symbol_manager.is_index_symbol("^TEST") is True
    
    def test_get_index_info(self, symbol_manager):
        """インデックス情報取得のテスト"""
        # 存在するインデックス
        info = symbol_manager.get_index_info("^N225")
        assert info is not None
        assert info["name"] == "日経225"
        assert info["market"] == "japan"
        assert info["type"] == "index"
        
        # 存在しないインデックス
        info = symbol_manager.get_index_info("INVALID")
        assert info is None
    
    def test_get_indices_by_market(self, symbol_manager):
        """市場別インデックス取得のテスト"""
        # 日本市場
        japan_indices = symbol_manager.get_indices_by_market("japan")
        assert len(japan_indices) > 0
        assert any(symbol == "^N225" for symbol, _ in japan_indices)
        assert all(info["market"] == "japan" for _, info in japan_indices)
        
        # 米国市場
        us_indices = symbol_manager.get_indices_by_market("us")
        assert len(us_indices) > 0
        assert any(symbol == "^GSPC" for symbol, _ in us_indices)
        assert all(info["market"] == "us" for _, info in us_indices)
    
    def test_get_sector_etfs(self, symbol_manager):
        """セクターETF取得のテスト"""
        # 日本のセクターETF
        sector_etfs = symbol_manager.get_sector_etfs("japan")
        assert len(sector_etfs) > 0
        assert all(info["type"] == "sector_etf" for _, info in sector_etfs)
        assert all(info["market"] == "japan" for _, info in sector_etfs)
        
        # 特定のセクターETFが含まれているか確認
        symbols = [symbol for symbol, _ in sector_etfs]
        assert "1475.T" in symbols  # IT・情報通信
        assert "1615.T" in symbols  # 金融
    
    def test_get_volatility_indices(self, symbol_manager):
        """ボラティリティ指数取得のテスト"""
        vol_indices = symbol_manager.get_volatility_indices()
        assert len(vol_indices) > 0
        
        # VIX指数が含まれているか確認
        assert any(symbol == "^VIX" for symbol, _ in vol_indices)
        assert all(info["type"] == "volatility" for _, info in vol_indices)
    
    def test_detect_market_type_with_indices(self, symbol_manager):
        """インデックスシンボルの市場タイプ判定のテスト"""
        # 日本のインデックス
        assert symbol_manager.detect_market_type("^N225") == MarketType.JAPAN
        assert symbol_manager.detect_market_type("1305.T") == MarketType.JAPAN
        
        # 米国のインデックス
        assert symbol_manager.detect_market_type("^GSPC") == MarketType.US
        assert symbol_manager.detect_market_type("^VIX") == MarketType.US
        
        # 通常の銘柄も正しく判定されるか確認
        assert symbol_manager.detect_market_type("7203.T") == MarketType.JAPAN
        assert symbol_manager.detect_market_type("AAPL") == MarketType.US
    
    def test_normalize_symbol_with_indices(self, symbol_manager):
        """インデックスシンボルの正規化のテスト"""
        # インデックスシンボルはそのまま返される
        assert symbol_manager.normalize_symbol("^N225") == "^N225"
        assert symbol_manager.normalize_symbol("^gspc") == "^GSPC"  # 大文字化
        assert symbol_manager.normalize_symbol("1305.T") == "1305.T"
        
        # 通常の銘柄の正規化も影響を受けないか確認
        assert symbol_manager.normalize_symbol("7203") == "7203.T"
        assert symbol_manager.normalize_symbol("aapl") == "AAPL"
    
    def test_comprehensive_index_coverage(self, symbol_manager):
        """インデックスカバレッジの包括的テスト"""
        all_indices = symbol_manager.INDEX_SYMBOLS
        
        # 各インデックスが必要な属性を持っているか確認（テスト用データを除外）
        for symbol, info in all_indices.items():
            # テスト用のシンボルは除外
            if symbol.startswith("^TEST"):
                continue
                
            assert "name" in info
            assert "market" in info
            assert "type" in info
            assert info["market"] in ["japan", "us"]
            assert info["type"] in ["index", "etf", "sector_etf", "volatility"]
        
        # 最低限必要なインデックスが含まれているか確認
        required_indices = ["^N225", "^GSPC", "^VIX"]
        for required in required_indices:
            assert required in all_indices