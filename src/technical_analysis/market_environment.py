"""市場環境分析モジュール

このモジュールは市場全体の環境を分析し、投資判断を支援します。
主な機能：
- 主要インデックスの動向分析
- セクター別パフォーマンス分析
- 市場のリスクオン/オフ状態判定
- VIX指数による市場心理分析
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from enum import Enum

from ..data_collector.stock_data_collector import StockDataCollector
from ..technical_analysis.indicators import TechnicalIndicators
from ..utils.data_validator import DataValidator


class MarketSentiment(Enum):
    """市場センチメントの状態"""
    EXTREME_FEAR = "極度の恐怖"
    FEAR = "恐怖"
    NEUTRAL = "中立"
    GREED = "貪欲"
    EXTREME_GREED = "極度の貪欲"


class RiskState(Enum):
    """市場のリスク状態"""
    RISK_ON = "リスクオン"
    RISK_OFF = "リスクオフ"
    NEUTRAL = "中立"


@dataclass
class MarketEnvironment:
    """市場環境の分析結果"""
    timestamp: datetime
    indices_performance: Dict[str, Dict[str, float]]  # インデックス別パフォーマンス
    sector_performance: Dict[str, float]  # セクター別パフォーマンス
    market_sentiment: MarketSentiment  # 市場センチメント
    risk_state: RiskState  # リスクオン/オフ状態
    vix_level: float  # VIX指数
    market_breadth: Dict[str, float]  # 市場の幅（上昇/下落銘柄数など）
    recommendation: str  # 投資推奨
    risk_factors: List[str]  # リスク要因
    opportunities: List[str]  # 投資機会
    

class MarketEnvironmentAnalyzer:
    """市場環境分析クラス"""
    
    # 主要インデックスのシンボル定義
    INDICES = {
        "nikkei225": "^N225",
        "topix": "1305.T",  # TOPIX ETF
        "sp500": "^GSPC",
        "nasdaq": "^IXIC",
        "dow": "^DJI",
        "vix": "^VIX"
    }
    
    # セクターETFのシンボル定義（日本市場）
    SECTOR_ETFS = {
        "technology": "1475.T",  # IT・情報通信セクターETF
        "financial": "1615.T",   # 金融セクターETF
        "consumer": "1617.T",    # 消費財セクターETF
        "industrial": "1619.T",  # 資本財セクターETF
        "healthcare": "1621.T",  # ヘルスケアセクターETF
        "energy": "1618.T",      # エネルギーセクターETF
    }
    
    # VIX指数の閾値
    VIX_THRESHOLDS = {
        "extreme_low": 12,
        "low": 20,
        "normal": 30,
        "high": 40,
        "extreme_high": 50
    }
    
    def __init__(self):
        """初期化"""
        self.data_collector = StockDataCollector()
        self.validator = DataValidator()
        
    def analyze_market_environment(
        self,
        period: str = "5d",
        interval: str = "1d"
    ) -> MarketEnvironment:
        """市場環境の総合分析
        
        Args:
            period: 分析期間
            interval: データ間隔
            
        Returns:
            MarketEnvironment: 市場環境分析結果
        """
        # インデックスデータの取得
        indices_data = self._fetch_indices_data(period, interval)
        
        # インデックスパフォーマンスの計算
        indices_performance = self._calculate_indices_performance(indices_data)
        
        # セクターパフォーマンスの分析
        sector_performance = self._analyze_sector_performance(period, interval)
        
        # VIX指数の取得と市場センチメント判定
        vix_level = self._get_current_vix(indices_data)
        market_sentiment = self._determine_market_sentiment(vix_level, indices_performance)
        
        # リスクオン/オフ状態の判定
        risk_state = self._determine_risk_state(indices_performance, vix_level, sector_performance)
        
        # 市場の幅の分析
        market_breadth = self._analyze_market_breadth(indices_performance, sector_performance)
        
        # リスク要因と投資機会の特定
        risk_factors = self._identify_risk_factors(
            indices_performance, vix_level, market_sentiment, sector_performance
        )
        opportunities = self._identify_opportunities(
            indices_performance, market_sentiment, sector_performance
        )
        
        # 投資推奨の生成
        recommendation = self._generate_recommendation(
            market_sentiment, risk_state, risk_factors, opportunities
        )
        
        return MarketEnvironment(
            timestamp=datetime.now(),
            indices_performance=indices_performance,
            sector_performance=sector_performance,
            market_sentiment=market_sentiment,
            risk_state=risk_state,
            vix_level=vix_level,
            market_breadth=market_breadth,
            recommendation=recommendation,
            risk_factors=risk_factors,
            opportunities=opportunities
        )
    
    def _fetch_indices_data(self, period: str, interval: str) -> Dict[str, pd.DataFrame]:
        """インデックスデータの取得"""
        indices_data = {}
        
        for name, symbol in self.INDICES.items():
            try:
                data = self.data_collector.get_stock_data(symbol, interval=interval, period=period)
                if data is not None and not data.empty:
                    indices_data[name] = data
            except Exception as e:
                print(f"インデックス {name} ({symbol}) のデータ取得に失敗: {e}")
                
        return indices_data
    
    def _calculate_indices_performance(self, indices_data: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, float]]:
        """インデックスパフォーマンスの計算"""
        performance = {}
        
        for name, data in indices_data.items():
            if data.empty:
                continue
                
            try:
                current_price = data['close'].iloc[-1]
                
                # 各期間のリターンを計算
                returns = {}
                
                # 1日リターン
                if len(data) >= 2:
                    returns['daily'] = ((current_price / data['close'].iloc[-2]) - 1) * 100
                
                # 5日リターン
                if len(data) >= 5:
                    returns['weekly'] = ((current_price / data['close'].iloc[-5]) - 1) * 100
                
                # 20日リターン（約1ヶ月）
                if len(data) >= 20:
                    returns['monthly'] = ((current_price / data['close'].iloc[-20]) - 1) * 100
                
                # ボラティリティ（20日）
                if len(data) >= 20:
                    returns['volatility'] = data['close'].pct_change().rolling(20).std().iloc[-1] * np.sqrt(252) * 100
                
                # テクニカル指標
                indicators = TechnicalIndicators(data)
                rsi_data = indicators.rsi(14)
                if rsi_data is not None and not rsi_data.empty:
                    returns['rsi'] = rsi_data.iloc[-1]
                
                performance[name] = returns
                
            except Exception as e:
                print(f"インデックス {name} のパフォーマンス計算エラー: {e}")
                
        return performance
    
    def _analyze_sector_performance(self, period: str, interval: str) -> Dict[str, float]:
        """セクター別パフォーマンスの分析"""
        sector_performance = {}
        
        for sector, symbol in self.SECTOR_ETFS.items():
            try:
                data = self.data_collector.get_stock_data(symbol, interval=interval, period=period)
                if data is not None and not data.empty and len(data) >= 2:
                    # 期間リターンを計算
                    current_price = data['close'].iloc[-1]
                    start_price = data['close'].iloc[0]
                    performance = ((current_price / start_price) - 1) * 100
                    sector_performance[sector] = performance
            except Exception as e:
                print(f"セクター {sector} ({symbol}) のデータ取得エラー: {e}")
                
        return sector_performance
    
    def _get_current_vix(self, indices_data: Dict[str, pd.DataFrame]) -> float:
        """現在のVIX指数を取得"""
        if "vix" in indices_data and not indices_data["vix"].empty:
            return indices_data["vix"]['close'].iloc[-1]
        return 20.0  # デフォルト値
    
    def _determine_market_sentiment(
        self, 
        vix_level: float, 
        indices_performance: Dict[str, Dict[str, float]]
    ) -> MarketSentiment:
        """市場センチメントの判定"""
        # VIXベースの判定
        if vix_level >= self.VIX_THRESHOLDS["extreme_high"]:
            return MarketSentiment.EXTREME_FEAR
        elif vix_level >= self.VIX_THRESHOLDS["high"]:
            return MarketSentiment.FEAR
        elif vix_level <= self.VIX_THRESHOLDS["extreme_low"]:
            return MarketSentiment.EXTREME_GREED
        elif vix_level <= self.VIX_THRESHOLDS["low"]:
            return MarketSentiment.GREED
        
        # インデックスパフォーマンスを考慮
        avg_performance = 0
        count = 0
        
        for index_name, perf in indices_performance.items():
            if 'daily' in perf:
                avg_performance += perf['daily']
                count += 1
                
        if count > 0:
            avg_performance /= count
            
            if avg_performance < -2:
                return MarketSentiment.FEAR
            elif avg_performance > 2:
                return MarketSentiment.GREED
                
        return MarketSentiment.NEUTRAL
    
    def _determine_risk_state(
        self,
        indices_performance: Dict[str, Dict[str, float]],
        vix_level: float,
        sector_performance: Dict[str, float]
    ) -> RiskState:
        """リスクオン/オフ状態の判定"""
        risk_on_score = 0
        risk_off_score = 0
        
        # VIXレベルによる判定
        if vix_level < self.VIX_THRESHOLDS["low"]:
            risk_on_score += 2
        elif vix_level > self.VIX_THRESHOLDS["normal"]:
            risk_off_score += 2
            
        # セクターローテーションによる判定
        if sector_performance:
            # ディフェンシブセクター（ヘルスケア、消費財）
            defensive_performance = sum([
                sector_performance.get("healthcare", 0),
                sector_performance.get("consumer", 0)
            ]) / 2
            
            # グロースセクター（テクノロジー、金融）
            growth_performance = sum([
                sector_performance.get("technology", 0),
                sector_performance.get("financial", 0)
            ]) / 2
            
            if growth_performance > defensive_performance + 1:
                risk_on_score += 1
            elif defensive_performance > growth_performance + 1:
                risk_off_score += 1
                
        # 判定
        if risk_on_score > risk_off_score + 1:
            return RiskState.RISK_ON
        elif risk_off_score > risk_on_score + 1:
            return RiskState.RISK_OFF
        else:
            return RiskState.NEUTRAL
    
    def _analyze_market_breadth(
        self,
        indices_performance: Dict[str, Dict[str, float]],
        sector_performance: Dict[str, float]
    ) -> Dict[str, float]:
        """市場の幅を分析"""
        breadth = {}
        
        # セクターの上昇/下落比率
        if sector_performance:
            positive_sectors = sum(1 for perf in sector_performance.values() if perf > 0)
            negative_sectors = sum(1 for perf in sector_performance.values() if perf < 0)
            total_sectors = len(sector_performance)
            
            if total_sectors > 0:
                breadth['advance_decline_ratio'] = positive_sectors / total_sectors * 100
                breadth['positive_sectors'] = positive_sectors
                breadth['negative_sectors'] = negative_sectors
        
        # インデックスの平均ボラティリティ
        volatilities = []
        for index_perf in indices_performance.values():
            if 'volatility' in index_perf:
                volatilities.append(index_perf['volatility'])
                
        if volatilities:
            breadth['avg_volatility'] = np.mean(volatilities)
            
        return breadth
    
    def _identify_risk_factors(
        self,
        indices_performance: Dict[str, Dict[str, float]],
        vix_level: float,
        market_sentiment: MarketSentiment,
        sector_performance: Dict[str, float]
    ) -> List[str]:
        """リスク要因の特定"""
        risk_factors = []
        
        # VIXレベルのチェック
        if vix_level > self.VIX_THRESHOLDS["high"]:
            risk_factors.append(f"VIX指数が高水準（{vix_level:.1f}）で市場の不確実性が高い")
        
        # 市場センチメントのチェック
        if market_sentiment in [MarketSentiment.EXTREME_FEAR, MarketSentiment.EXTREME_GREED]:
            risk_factors.append(f"市場センチメントが極端な状態（{market_sentiment.value}）")
        
        # インデックスの急落チェック
        for name, perf in indices_performance.items():
            if 'daily' in perf and perf['daily'] < -3:
                risk_factors.append(f"{name}が大幅下落（{perf['daily']:.1f}%）")
        
        # セクターの偏りチェック
        if sector_performance:
            sector_returns = list(sector_performance.values())
            if sector_returns:
                std_dev = np.std(sector_returns)
                if std_dev > 5:
                    risk_factors.append("セクター間のパフォーマンス格差が大きい")
        
        # ボラティリティチェック
        high_vol_indices = []
        for name, perf in indices_performance.items():
            if 'volatility' in perf and perf['volatility'] > 30:
                high_vol_indices.append(name)
                
        if high_vol_indices:
            risk_factors.append(f"高ボラティリティのインデックス: {', '.join(high_vol_indices)}")
        
        return risk_factors
    
    def _identify_opportunities(
        self,
        indices_performance: Dict[str, Dict[str, float]],
        market_sentiment: MarketSentiment,
        sector_performance: Dict[str, float]
    ) -> List[str]:
        """投資機会の特定"""
        opportunities = []
        
        # 売られ過ぎのインデックス
        for name, perf in indices_performance.items():
            if 'rsi' in perf and perf['rsi'] < 30:
                opportunities.append(f"{name}がRSI{perf['rsi']:.1f}で売られ過ぎ水準")
        
        # 極度の恐怖時の逆張り機会
        if market_sentiment == MarketSentiment.EXTREME_FEAR:
            opportunities.append("極度の恐怖状態で逆張りの機会の可能性")
        
        # 好調なセクター
        if sector_performance:
            top_sectors = sorted(
                sector_performance.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:2]
            
            for sector, perf in top_sectors:
                if perf > 2:
                    opportunities.append(f"{sector}セクターが好調（{perf:.1f}%）")
        
        # 低ボラティリティ環境
        low_vol_indices = []
        for name, perf in indices_performance.items():
            if 'volatility' in perf and perf['volatility'] < 15:
                low_vol_indices.append(name)
                
        if len(low_vol_indices) >= 2:
            opportunities.append("低ボラティリティ環境で安定的な投資機会")
        
        return opportunities
    
    def _generate_recommendation(
        self,
        market_sentiment: MarketSentiment,
        risk_state: RiskState,
        risk_factors: List[str],
        opportunities: List[str]
    ) -> str:
        """投資推奨の生成"""
        # リスクレベルの評価
        risk_level = len(risk_factors)
        opportunity_level = len(opportunities)
        
        # 基本的な推奨
        if risk_level >= 4:
            base_recommendation = "現在の市場環境はリスクが高く、慎重な投資姿勢を推奨します。"
        elif risk_level >= 2:
            base_recommendation = "市場には一定のリスクが存在します。ポジションサイズに注意してください。"
        else:
            base_recommendation = "市場環境は比較的安定しています。"
            
        # リスク状態による調整
        if risk_state == RiskState.RISK_OFF:
            base_recommendation += " リスクオフ環境のため、ディフェンシブな銘柄選択を検討してください。"
        elif risk_state == RiskState.RISK_ON:
            base_recommendation += " リスクオン環境で、成長株への投資機会があります。"
            
        # センチメントによる調整
        if market_sentiment == MarketSentiment.EXTREME_FEAR:
            base_recommendation += " 極度の恐怖状態は逆張りの機会となる可能性がありますが、慎重に。"
        elif market_sentiment == MarketSentiment.EXTREME_GREED:
            base_recommendation += " 過熱感があるため、利益確定を検討する時期かもしれません。"
            
        # 機会の言及
        if opportunity_level > 0:
            base_recommendation += f" {opportunity_level}つの投資機会を検出しました。"
            
        return base_recommendation
    
    def get_daily_market_report(self) -> Dict[str, any]:
        """日次市場レポートの生成"""
        # 市場環境分析
        env = self.analyze_market_environment(period="5d", interval="1d")
        
        # レポートの構造化
        report = {
            "report_date": env.timestamp.strftime("%Y-%m-%d %H:%M"),
            "executive_summary": {
                "market_sentiment": env.market_sentiment.value,
                "risk_state": env.risk_state.value,
                "vix_level": env.vix_level,
                "recommendation": env.recommendation
            },
            "indices_performance": env.indices_performance,
            "sector_analysis": {
                "performance": env.sector_performance,
                "top_sectors": sorted(
                    env.sector_performance.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:3] if env.sector_performance else []
            },
            "market_breadth": env.market_breadth,
            "risk_assessment": {
                "risk_factors": env.risk_factors,
                "risk_count": len(env.risk_factors)
            },
            "opportunities": env.opportunities,
            "technical_levels": self._calculate_key_levels(env.indices_performance)
        }
        
        return report
    
    def _calculate_key_levels(self, indices_performance: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
        """主要インデックスのキーレベルを計算"""
        key_levels = {}
        
        # 簡易的な実装（実際にはより詳細な分析が必要）
        for index_name in ["nikkei225", "sp500"]:
            if index_name in indices_performance:
                # プレースホルダー
                key_levels[index_name] = {
                    "current": "取得中",
                    "support": "計算中",
                    "resistance": "計算中"
                }
                
        return key_levels