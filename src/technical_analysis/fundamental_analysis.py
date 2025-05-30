"""
ファンダメンタルズ分析モジュール

PER、PBR、ROE、配当利回りなどの基本指標を自動取得し、
売上・利益の成長率トレンド分析、同業他社との比較分析機能、
財務健全性スコアの算出を行う
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import yfinance as yf
from dataclasses import dataclass
from loguru import logger
from enum import Enum


class HealthScore(Enum):
    """財務健全性スコア評価レベル"""

    EXCELLENT = "優秀"
    GOOD = "良好"
    AVERAGE = "普通"
    POOR = "注意"
    CRITICAL = "危険"


@dataclass
class FinancialMetrics:
    """基本財務指標データクラス"""

    symbol: str
    company_name: str
    per: Optional[float] = None  # 株価収益率
    pbr: Optional[float] = None  # 株価純資産倍率
    roe: Optional[float] = None  # 自己資本利益率
    dividend_yield: Optional[float] = None  # 配当利回り
    current_ratio: Optional[float] = None  # 流動比率
    equity_ratio: Optional[float] = None  # 自己資本比率
    debt_ratio: Optional[float] = None  # 負債比率
    roa: Optional[float] = None  # 総資産利益率
    revenue_growth: Optional[float] = None  # 売上成長率
    profit_growth: Optional[float] = None  # 利益成長率
    price: Optional[float] = None  # 現在株価
    market_cap: Optional[float] = None  # 時価総額
    updated_at: datetime = None


@dataclass
class GrowthTrend:
    """成長トレンドデータクラス"""

    symbol: str
    revenue_trend: List[float]  # 売上推移
    profit_trend: List[float]  # 利益推移
    years: List[str]  # 年度
    revenue_cagr: Optional[float] = None  # 売上年平均成長率
    profit_cagr: Optional[float] = None  # 利益年平均成長率
    volatility: Optional[float] = None  # 変動性


@dataclass
class ComparisonResult:
    """業界比較結果データクラス"""

    target_symbol: str
    comparison_symbols: List[str]
    metrics_comparison: Dict[str, Dict[str, float]]
    rank: Dict[str, int]
    industry_average: Dict[str, float]


@dataclass
class HealthScoreResult:
    """財務健全性スコア結果"""

    symbol: str
    total_score: float
    score_breakdown: Dict[str, float]
    health_level: HealthScore
    recommendations: List[str]


class FundamentalAnalyzer:
    """ファンダメンタルズ分析メインクラス"""

    def __init__(self):
        """初期化"""
        self._cache = {}
        self._cache_expire_hours = 24  # キャッシュ有効期限24時間

    def _get_ticker_info(self, symbol: str) -> Dict:
        """yfinanceから銘柄情報を取得（キャッシュ機能付き）"""
        cache_key = f"info_{symbol}"
        now = datetime.now()

        # キャッシュチェック
        if cache_key in self._cache:
            cache_data, cache_time = self._cache[cache_key]
            if now - cache_time < timedelta(hours=self._cache_expire_hours):
                return cache_data

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # キャッシュに保存
            self._cache[cache_key] = (info, now)

            logger.info(f"銘柄情報取得成功: {symbol}")
            return info

        except Exception as e:
            logger.error(f"銘柄情報取得エラー {symbol}: {str(e)}")
            return {}

    def _get_financial_data(self, symbol: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """財務諸表データを取得"""
        cache_key = f"financials_{symbol}"
        now = datetime.now()

        # キャッシュチェック
        if cache_key in self._cache:
            cache_data, cache_time = self._cache[cache_key]
            if now - cache_time < timedelta(hours=self._cache_expire_hours):
                return cache_data

        try:
            ticker = yf.Ticker(symbol)

            # 損益計算書と貸借対照表を取得
            financials = ticker.financials
            balance_sheet = ticker.balance_sheet

            # キャッシュに保存
            self._cache[cache_key] = (financials, balance_sheet)

            logger.info(f"財務データ取得成功: {symbol}")
            return financials, balance_sheet

        except Exception as e:
            logger.error(f"財務データ取得エラー {symbol}: {str(e)}")
            return pd.DataFrame(), pd.DataFrame()

    def get_financial_metrics(self, symbol: str) -> Optional[FinancialMetrics]:
        """基本財務指標を取得・計算"""
        try:
            info = self._get_ticker_info(symbol)
            if not info:
                return None

            financials, balance_sheet = self._get_financial_data(symbol)

            # 基本指標の取得
            metrics = FinancialMetrics(
                symbol=symbol,
                company_name=info.get("longName", symbol),
                per=info.get("trailingPE"),
                pbr=info.get("priceToBook"),
                roe=info.get("returnOnEquity"),
                dividend_yield=info.get("dividendYield"),
                price=info.get("currentPrice"),
                market_cap=info.get("marketCap"),
                updated_at=datetime.now(),
            )

            # 財務諸表から追加指標を計算
            if not balance_sheet.empty and len(balance_sheet.columns) > 0:
                latest_bs = balance_sheet.iloc[:, 0]

                # 流動比率の計算
                current_assets = latest_bs.get("Current Assets")
                current_liabilities = latest_bs.get("Current Liabilities")
                if current_assets and current_liabilities and current_liabilities != 0:
                    metrics.current_ratio = current_assets / current_liabilities

                # 自己資本比率の計算
                total_equity = latest_bs.get("Total Equity Gross Minority Interest")
                total_assets = latest_bs.get("Total Assets")
                if total_equity and total_assets and total_assets != 0:
                    metrics.equity_ratio = total_equity / total_assets

                # 負債比率の計算
                total_debt = latest_bs.get("Total Debt")
                if total_debt and total_assets and total_assets != 0:
                    metrics.debt_ratio = total_debt / total_assets

            # ROAの計算
            if info.get("returnOnAssets"):
                metrics.roa = info.get("returnOnAssets")

            logger.info(f"財務指標計算完了: {symbol}")
            return metrics

        except Exception as e:
            logger.error(f"財務指標計算エラー {symbol}: {str(e)}")
            return None

    def analyze_growth_trend(
        self, symbol: str, years: int = 5
    ) -> Optional[GrowthTrend]:
        """売上・利益の成長トレンド分析"""
        try:
            financials, _ = self._get_financial_data(symbol)

            if financials.empty:
                return None

            # データを年度順に並び替え
            financials = financials.sort_index(axis=1)

            # 最大years年分のデータを取得
            if len(financials.columns) > years:
                financials = financials.iloc[:, -years:]

            # 売上と利益のデータを抽出
            revenue_data = []
            profit_data = []
            year_labels = []

            for col in financials.columns:
                year_labels.append(col.strftime("%Y"))

                # 売上（Total Revenue）
                revenue = financials.loc[
                    financials.index.str.contains("Total Revenue", na=False), col
                ]
                if not revenue.empty:
                    revenue_data.append(float(revenue.iloc[0]))
                else:
                    revenue_data.append(np.nan)

                # 純利益（Net Income）
                profit = financials.loc[
                    financials.index.str.contains("Net Income", na=False), col
                ]
                if not profit.empty:
                    profit_data.append(float(profit.iloc[0]))
                else:
                    profit_data.append(np.nan)

            # CAGRの計算
            revenue_cagr = self._calculate_cagr(revenue_data)
            profit_cagr = self._calculate_cagr(profit_data)

            # 変動性の計算（標準偏差 / 平均）
            volatility = None
            if len(profit_data) > 1:
                profit_clean = [x for x in profit_data if not np.isnan(x)]
                if len(profit_clean) > 1:
                    volatility = np.std(profit_clean) / np.mean(profit_clean)

            trend = GrowthTrend(
                symbol=symbol,
                revenue_trend=revenue_data,
                profit_trend=profit_data,
                years=year_labels,
                revenue_cagr=revenue_cagr,
                profit_cagr=profit_cagr,
                volatility=volatility,
            )

            logger.info(f"成長トレンド分析完了: {symbol}")
            return trend

        except Exception as e:
            logger.error(f"成長トレンド分析エラー {symbol}: {str(e)}")
            return None

    def _calculate_cagr(self, values: List[float]) -> Optional[float]:
        """年平均成長率（CAGR）を計算"""
        try:
            # NaNを除去
            clean_values = [x for x in values if not np.isnan(x) and x > 0]

            if len(clean_values) < 2:
                return None

            start_value = clean_values[0]
            end_value = clean_values[-1]
            years = len(clean_values) - 1

            if start_value <= 0 or end_value <= 0:
                return None

            cagr = ((end_value / start_value) ** (1 / years)) - 1
            return cagr

        except Exception:
            return None

    def compare_with_peers(
        self, target_symbol: str, peer_symbols: List[str]
    ) -> Optional[ComparisonResult]:
        """同業他社との比較分析"""
        try:
            # 全銘柄の財務指標を取得
            all_metrics = {}

            for symbol in [target_symbol] + peer_symbols:
                metrics = self.get_financial_metrics(symbol)
                if metrics:
                    all_metrics[symbol] = metrics

            if len(all_metrics) < 2:
                logger.warning("比較に十分なデータがありません")
                return None

            # 比較用データフレームを作成
            comparison_data = {}
            metrics_names = [
                "per",
                "pbr",
                "roe",
                "dividend_yield",
                "current_ratio",
                "equity_ratio",
            ]

            for metric_name in metrics_names:
                comparison_data[metric_name] = {}
                for symbol, metrics in all_metrics.items():
                    value = getattr(metrics, metric_name)
                    if value is not None:
                        comparison_data[metric_name][symbol] = value

            # ランキングを計算
            rankings = {}
            for metric_name, values in comparison_data.items():
                if values:
                    # ROE、配当利回り、流動比率、自己資本比率は高い方が良い
                    if metric_name in [
                        "roe",
                        "dividend_yield",
                        "current_ratio",
                        "equity_ratio",
                    ]:
                        sorted_items = sorted(
                            values.items(), key=lambda x: x[1], reverse=True
                        )
                    # PER、PBRは低い方が良い（割安）
                    else:
                        sorted_items = sorted(values.items(), key=lambda x: x[1])

                    rankings[metric_name] = {
                        symbol: rank + 1
                        for rank, (symbol, _) in enumerate(sorted_items)
                    }

            # 業界平均を計算
            industry_averages = {}
            for metric_name, values in comparison_data.items():
                if values:
                    industry_averages[metric_name] = np.mean(list(values.values()))

            # ターゲット銘柄のランキング
            target_ranks = {}
            for metric_name, ranks in rankings.items():
                if target_symbol in ranks:
                    target_ranks[metric_name] = ranks[target_symbol]

            result = ComparisonResult(
                target_symbol=target_symbol,
                comparison_symbols=peer_symbols,
                metrics_comparison=comparison_data,
                rank=target_ranks,
                industry_average=industry_averages,
            )

            logger.info(f"同業他社比較完了: {target_symbol}")
            return result

        except Exception as e:
            logger.error(f"同業他社比較エラー: {str(e)}")
            return None

    def calculate_health_score(self, symbol: str) -> Optional[HealthScoreResult]:
        """財務健全性スコアを算出"""
        try:
            metrics = self.get_financial_metrics(symbol)
            if not metrics:
                return None

            scores = {}
            recommendations = []

            # PERスコア（10-20が理想）
            if metrics.per:
                if 10 <= metrics.per <= 20:
                    scores["per"] = 100
                elif 5 <= metrics.per < 10 or 20 < metrics.per <= 30:
                    scores["per"] = 70
                elif metrics.per < 5 or metrics.per > 30:
                    scores["per"] = 30
                    if metrics.per > 30:
                        recommendations.append("PERが高く割高の可能性があります")
                    else:
                        recommendations.append("PERが低すぎる可能性があります")

            # PBRスコア（0.5-2.0が理想）
            if metrics.pbr:
                if 0.5 <= metrics.pbr <= 2.0:
                    scores["pbr"] = 100
                elif 0.3 <= metrics.pbr < 0.5 or 2.0 < metrics.pbr <= 3.0:
                    scores["pbr"] = 70
                elif metrics.pbr < 0.3 or metrics.pbr > 3.0:
                    scores["pbr"] = 30
                    if metrics.pbr > 3.0:
                        recommendations.append("PBRが高く割高の可能性があります")

            # ROEスコア（15%以上が理想）
            if metrics.roe:
                roe_percent = metrics.roe * 100
                if roe_percent >= 15:
                    scores["roe"] = 100
                elif roe_percent >= 10:
                    scores["roe"] = 70
                elif roe_percent >= 5:
                    scores["roe"] = 50
                else:
                    scores["roe"] = 30
                    recommendations.append(
                        "ROEが低く、株主資本の効率性に課題があります"
                    )

            # 流動比率スコア（200%以上が理想）
            if metrics.current_ratio:
                if metrics.current_ratio >= 2.0:
                    scores["liquidity"] = 100
                elif metrics.current_ratio >= 1.5:
                    scores["liquidity"] = 70
                elif metrics.current_ratio >= 1.0:
                    scores["liquidity"] = 50
                else:
                    scores["liquidity"] = 20
                    recommendations.append(
                        "流動比率が低く、短期的な支払能力に注意が必要です"
                    )

            # 自己資本比率スコア（50%以上が理想）
            if metrics.equity_ratio:
                equity_percent = metrics.equity_ratio * 100
                if equity_percent >= 50:
                    scores["stability"] = 100
                elif equity_percent >= 30:
                    scores["stability"] = 70
                elif equity_percent >= 20:
                    scores["stability"] = 50
                else:
                    scores["stability"] = 30
                    recommendations.append(
                        "自己資本比率が低く、財務安定性に課題があります"
                    )

            # 配当利回りスコア（2-5%が理想）
            if metrics.dividend_yield:
                dividend_percent = metrics.dividend_yield * 100
                if 2 <= dividend_percent <= 5:
                    scores["dividend"] = 100
                elif 1 <= dividend_percent < 2 or 5 < dividend_percent <= 8:
                    scores["dividend"] = 70
                elif dividend_percent > 8:
                    scores["dividend"] = 40
                    recommendations.append("配当利回りが高すぎる可能性があります")
                else:
                    scores["dividend"] = 50

            # 総合スコアを計算（重み付き平均）
            weights = {
                "per": 0.2,
                "pbr": 0.15,
                "roe": 0.25,
                "liquidity": 0.15,
                "stability": 0.2,
                "dividend": 0.05,
            }

            total_score = 0
            total_weight = 0

            for metric, score in scores.items():
                if metric in weights:
                    total_score += score * weights[metric]
                    total_weight += weights[metric]

            if total_weight > 0:
                total_score = total_score / total_weight
            else:
                total_score = 0

            # 健全性レベルを決定
            if total_score >= 90:
                health_level = HealthScore.EXCELLENT
            elif total_score >= 75:
                health_level = HealthScore.GOOD
            elif total_score >= 60:
                health_level = HealthScore.AVERAGE
            elif total_score >= 40:
                health_level = HealthScore.POOR
            else:
                health_level = HealthScore.CRITICAL

            result = HealthScoreResult(
                symbol=symbol,
                total_score=total_score,
                score_breakdown=scores,
                health_level=health_level,
                recommendations=recommendations,
            )

            logger.info(
                f"財務健全性スコア算出完了: {symbol} (スコア: {total_score:.1f})"
            )
            return result

        except Exception as e:
            logger.error(f"財務健全性スコア算出エラー {symbol}: {str(e)}")
            return None

    def get_comprehensive_analysis(
        self, symbol: str, peer_symbols: Optional[List[str]] = None
    ) -> Dict[str, any]:
        """総合的なファンダメンタルズ分析"""
        try:
            results = {}

            # 基本財務指標
            results["metrics"] = self.get_financial_metrics(symbol)

            # 成長トレンド分析
            results["growth_trend"] = self.analyze_growth_trend(symbol)

            # 財務健全性スコア
            results["health_score"] = self.calculate_health_score(symbol)

            # 同業他社比較（提供された場合）
            if peer_symbols:
                results["peer_comparison"] = self.compare_with_peers(
                    symbol, peer_symbols
                )

            logger.info(f"総合ファンダメンタルズ分析完了: {symbol}")
            return results

        except Exception as e:
            logger.error(f"総合分析エラー {symbol}: {str(e)}")
            return {}
