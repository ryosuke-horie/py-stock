from typing import Dict, List, Optional, Tuple
import re
from enum import Enum
from loguru import logger


class MarketType(Enum):
    """市場タイプ"""
    JAPAN = "japan"
    US = "us"
    UNKNOWN = "unknown"


class SymbolManager:
    """
    銘柄コード管理クラス
    日本株・米国株の銘柄コード形式を統一的に処理
    インデックスシンボルの管理機能を含む
    """
    
    # 日本株の主要市場コード
    JAPAN_MARKET_SUFFIXES = {
        ".T": "東証",
        ".JP": "東証",
        "": "東証（デフォルト）"
    }
    
    # 米国株の主要市場
    US_EXCHANGES = ["NYSE", "NASDAQ", "AMEX"]
    
    # 主要インデックスシンボル
    INDEX_SYMBOLS = {
        # 日本市場
        "^N225": {"name": "日経225", "market": "japan", "type": "index"},
        "^TOPX": {"name": "TOPIX", "market": "japan", "type": "index"},
        "1305.T": {"name": "TOPIX ETF", "market": "japan", "type": "etf"},
        "1321.T": {"name": "日経225 ETF", "market": "japan", "type": "etf"},
        
        # 米国市場
        "^GSPC": {"name": "S&P 500", "market": "us", "type": "index"},
        "^DJI": {"name": "ダウ平均", "market": "us", "type": "index"},
        "^IXIC": {"name": "NASDAQ総合", "market": "us", "type": "index"},
        "^VIX": {"name": "VIX指数", "market": "us", "type": "volatility"},
        
        # セクターETF（日本）
        "1475.T": {"name": "IT・情報通信セクターETF", "market": "japan", "type": "sector_etf"},
        "1615.T": {"name": "金融セクターETF", "market": "japan", "type": "sector_etf"},
        "1617.T": {"name": "消費財セクターETF", "market": "japan", "type": "sector_etf"},
        "1619.T": {"name": "資本財セクターETF", "market": "japan", "type": "sector_etf"},
        "1621.T": {"name": "ヘルスケアセクターETF", "market": "japan", "type": "sector_etf"},
        "1618.T": {"name": "エネルギーセクターETF", "market": "japan", "type": "sector_etf"},
    }
    
    def __init__(self):
        # 日本の主要銘柄コード例（実際の運用では外部データソースから取得）
        self.japan_symbols = {
            "7203": "トヨタ自動車",
            "9984": "ソフトバンクグループ",
            "6758": "ソニーグループ",
            "7974": "任天堂",
            "9983": "ファーストリテイリング",
            "6861": "キーエンス",
            "8306": "三菱UFJフィナンシャル・グループ",
            "4519": "中外製薬",
            "6954": "ファナック",
            "4568": "第一三共"
        }
        
        # 米国の主要銘柄コード例
        self.us_symbols = {
            "AAPL": "Apple Inc.",
            "MSFT": "Microsoft Corporation",
            "GOOGL": "Alphabet Inc.",
            "AMZN": "Amazon.com Inc.",
            "TSLA": "Tesla Inc.",
            "META": "Meta Platforms Inc.",
            "NVDA": "NVIDIA Corporation",
            "JPM": "JPMorgan Chase & Co.",
            "JNJ": "Johnson & Johnson",
            "V": "Visa Inc."
        }
    
    def detect_market_type(self, symbol: str) -> MarketType:
        """
        銘柄コードから市場タイプを判定
        
        Args:
            symbol: 銘柄コード
            
        Returns:
            市場タイプ
        """
        # インデックスシンボルのチェック
        if symbol in self.INDEX_SYMBOLS:
            market = self.INDEX_SYMBOLS[symbol].get("market", "unknown")
            if market == "japan":
                return MarketType.JAPAN
            elif market == "us":
                return MarketType.US
        
        # 日本株の判定
        if self._is_japan_stock(symbol):
            return MarketType.JAPAN
        
        # 米国株の判定
        elif self._is_us_stock(symbol):
            return MarketType.US
        
        else:
            return MarketType.UNKNOWN
    
    def _is_japan_stock(self, symbol: str) -> bool:
        """日本株かどうかの判定"""
        # インデックスシンボルの場合
        if symbol.startswith('^'):
            return False
        # 4桁数字のパターン（例: 7203, 7203.T）
        japan_pattern = r'^\d{4}(\.T|\.JP)?$'
        return bool(re.match(japan_pattern, symbol))
    
    def _is_us_stock(self, symbol: str) -> bool:
        """米国株かどうかの判定"""
        # インデックスシンボルの場合
        if symbol.startswith('^'):
            return False
        # 1-5文字のアルファベット（例: AAPL, MSFT）
        us_pattern = r'^[A-Z]{1,5}$'
        return bool(re.match(us_pattern, symbol))
    
    def normalize_symbol(self, symbol: str, market_type: Optional[MarketType] = None) -> str:
        """
        銘柄コードを正規化
        
        Args:
            symbol: 入力銘柄コード
            market_type: 市場タイプ（Noneの場合は自動判定）
            
        Returns:
            正規化された銘柄コード
        """
        symbol = symbol.upper().strip()
        
        # インデックスシンボルはそのまま返す
        if symbol in self.INDEX_SYMBOLS or symbol.startswith('^'):
            return symbol
        
        if market_type is None:
            market_type = self.detect_market_type(symbol)
        
        if market_type == MarketType.JAPAN:
            return self._normalize_japan_symbol(symbol)
        elif market_type == MarketType.US:
            return self._normalize_us_symbol(symbol)
        else:
            logger.warning(f"未知の市場タイプ: {symbol}")
            return symbol
    
    def _normalize_japan_symbol(self, symbol: str) -> str:
        """日本株銘柄コードの正規化"""
        # 4桁数字部分を抽出
        base_symbol = re.sub(r'[^0-9]', '', symbol)
        
        if len(base_symbol) == 4:
            # デフォルトで.Tサフィックスを追加（yfinance用）
            return f"{base_symbol}.T"
        else:
            logger.warning(f"無効な日本株コード: {symbol}")
            return symbol
    
    def _normalize_us_symbol(self, symbol: str) -> str:
        """米国株銘柄コードの正規化"""
        # アルファベットのみを抽出
        clean_symbol = re.sub(r'[^A-Z]', '', symbol)
        
        if 1 <= len(clean_symbol) <= 5:
            return clean_symbol
        else:
            logger.warning(f"無効な米国株コード: {symbol}")
            return symbol
    
    def get_symbol_info(self, symbol: str) -> Dict[str, str]:
        """
        銘柄情報取得
        
        Args:
            symbol: 銘柄コード
            
        Returns:
            銘柄情報の辞書
        """
        normalized = self.normalize_symbol(symbol)
        market_type = self.detect_market_type(symbol)
        
        info = {
            "original": symbol,
            "normalized": normalized,
            "market_type": market_type.value,
            "name": "N/A"
        }
        
        if market_type == MarketType.JAPAN:
            # 日本株の場合、.Tを除いたコードで検索
            base_code = normalized.replace(".T", "").replace(".JP", "")
            info["name"] = self.japan_symbols.get(base_code, "N/A")
        elif market_type == MarketType.US:
            info["name"] = self.us_symbols.get(normalized, "N/A")
        
        return info
    
    def validate_symbols(self, symbols: List[str]) -> Tuple[List[str], List[str]]:
        """
        銘柄コードリストの検証
        
        Args:
            symbols: 銘柄コードリスト
            
        Returns:
            (有効な銘柄リスト, 無効な銘柄リスト)
        """
        valid_symbols = []
        invalid_symbols = []
        
        for symbol in symbols:
            market_type = self.detect_market_type(symbol)
            if market_type != MarketType.UNKNOWN:
                normalized = self.normalize_symbol(symbol, market_type)
                valid_symbols.append(normalized)
            else:
                invalid_symbols.append(symbol)
                logger.warning(f"無効な銘柄コード: {symbol}")
        
        return valid_symbols, invalid_symbols
    
    def get_sample_symbols(self, market_type: MarketType, count: int = 5) -> List[str]:
        """
        サンプル銘柄コード取得
        
        Args:
            market_type: 市場タイプ
            count: 取得数
            
        Returns:
            サンプル銘柄コードリスト
        """
        if market_type == MarketType.JAPAN:
            symbols = list(self.japan_symbols.keys())[:count]
            return [self.normalize_symbol(s, MarketType.JAPAN) for s in symbols]
        elif market_type == MarketType.US:
            symbols = list(self.us_symbols.keys())[:count]
            return [self.normalize_symbol(s, MarketType.US) for s in symbols]
        else:
            return []
    
    def create_watchlist(self, name: str, symbols: List[str]) -> Dict[str, any]:
        """
        ウォッチリスト作成
        
        Args:
            name: ウォッチリスト名
            symbols: 銘柄コードリスト
            
        Returns:
            ウォッチリスト情報
        """
        valid_symbols, invalid_symbols = self.validate_symbols(symbols)
        
        watchlist = {
            "name": name,
            "symbols": valid_symbols,
            "invalid_symbols": invalid_symbols,
            "symbol_count": len(valid_symbols),
            "symbol_info": [self.get_symbol_info(s) for s in valid_symbols]
        }
        
        logger.info(f"ウォッチリスト作成: {name} ({len(valid_symbols)}銘柄)")
        
        if invalid_symbols:
            logger.warning(f"無効な銘柄: {invalid_symbols}")
        
        return watchlist
    
    def get_market_hours_info(self, market_type: MarketType) -> Dict[str, str]:
        """
        市場時間情報取得
        
        Args:
            market_type: 市場タイプ
            
        Returns:
            市場時間情報
        """
        if market_type == MarketType.JAPAN:
            return {
                "market": "東京証券取引所",
                "timezone": "Asia/Tokyo",
                "regular_hours": "09:00-11:30, 12:30-15:00",
                "notes": "昼休み: 11:30-12:30"
            }
        elif market_type == MarketType.US:
            return {
                "market": "米国市場",
                "timezone": "America/New_York",
                "regular_hours": "09:30-16:00",
                "pre_market": "04:00-09:30",
                "after_hours": "16:00-20:00"
            }
        else:
            return {"market": "不明", "timezone": "UTC"}
    
    def is_index_symbol(self, symbol: str) -> bool:
        """
        インデックスシンボルかどうかを判定
        
        Args:
            symbol: 銘柄コード
            
        Returns:
            インデックスシンボルの場合True
        """
        return symbol in self.INDEX_SYMBOLS or symbol.startswith('^')
    
    def get_index_info(self, symbol: str) -> Optional[Dict[str, str]]:
        """
        インデックス情報を取得
        
        Args:
            symbol: インデックスシンボル
            
        Returns:
            インデックス情報（存在しない場合はNone）
        """
        return self.INDEX_SYMBOLS.get(symbol)
    
    def get_indices_by_market(self, market: str) -> List[Tuple[str, Dict[str, str]]]:
        """
        市場別のインデックスリストを取得
        
        Args:
            market: 市場名（"japan" または "us"）
            
        Returns:
            インデックスのリスト [(symbol, info), ...]
        """
        indices = []
        for symbol, info in self.INDEX_SYMBOLS.items():
            if info.get("market") == market:
                indices.append((symbol, info))
        return indices
    
    def get_sector_etfs(self, market: str = "japan") -> List[Tuple[str, Dict[str, str]]]:
        """
        セクターETFのリストを取得
        
        Args:
            market: 市場名（デフォルトは"japan"）
            
        Returns:
            セクターETFのリスト [(symbol, info), ...]
        """
        sector_etfs = []
        for symbol, info in self.INDEX_SYMBOLS.items():
            if info.get("type") == "sector_etf" and info.get("market") == market:
                sector_etfs.append((symbol, info))
        return sector_etfs
    
    def get_volatility_indices(self) -> List[Tuple[str, Dict[str, str]]]:
        """
        ボラティリティ指数のリストを取得
        
        Returns:
            ボラティリティ指数のリスト [(symbol, info), ...]
        """
        vol_indices = []
        for symbol, info in self.INDEX_SYMBOLS.items():
            if info.get("type") == "volatility":
                vol_indices.append((symbol, info))
        return vol_indices