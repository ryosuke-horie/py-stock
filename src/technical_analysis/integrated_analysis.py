"""
統合分析モジュール

テクニカル分析、ファンダメンタルズ分析、投資ストーリー生成を統合し、
包括的な投資レポートを生成する
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd
from loguru import logger

from .fundamental_analysis import FundamentalAnalyzer
from .investment_story_generator import (
    InvestmentStoryGenerator,
    InvestmentReport,
    TechnicalAnalysisData,
)
from ..data_collector.stock_data_collector import StockDataCollector


class IntegratedAnalyzer:
    """統合分析メインクラス"""

    def __init__(self):
        """初期化"""
        self.fundamental_analyzer = FundamentalAnalyzer()
        self.story_generator = InvestmentStoryGenerator()
        self.data_collector = StockDataCollector()

    def generate_complete_analysis(
        self,
        symbol: str,
        include_peers: bool = True,
        peer_symbols: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """完全な統合分析レポートを生成"""
        try:
            logger.info(f"統合分析開始: {symbol}")

            # 1. ファンダメンタルズ分析
            fundamental_results = self._perform_fundamental_analysis(
                symbol, include_peers, peer_symbols
            )

            # 2. テクニカル分析（簡易版）
            technical_data = self._perform_basic_technical_analysis(symbol)

            # 3. 投資ストーリー生成
            investment_report = self._generate_investment_story(
                symbol, fundamental_results, technical_data
            )

            # 4. 統合結果の構築
            complete_analysis = {
                "symbol": symbol,
                "analysis_date": datetime.now(),
                "fundamental_analysis": fundamental_results,
                "technical_analysis": technical_data,
                "investment_report": investment_report,
                "summary": self._create_analysis_summary(
                    symbol, fundamental_results, technical_data, investment_report
                ),
            }

            logger.info(f"統合分析完了: {symbol}")
            return complete_analysis

        except Exception as e:
            logger.error(f"統合分析エラー {symbol}: {str(e)}")
            return self._create_error_analysis(symbol, str(e))

    def _perform_fundamental_analysis(
        self, symbol: str, include_peers: bool, peer_symbols: Optional[List[str]]
    ) -> Dict[str, Any]:
        """ファンダメンタルズ分析の実行"""
        try:
            # 基本財務指標
            metrics = self.fundamental_analyzer.get_financial_metrics(symbol)

            # 成長トレンド分析
            growth_trend = self.fundamental_analyzer.analyze_growth_trend(symbol)

            # 財務健全性スコア
            health_score = self.fundamental_analyzer.calculate_health_score(symbol)

            # 同業他社比較（オプション）
            comparison = None
            if include_peers and peer_symbols:
                comparison = self.fundamental_analyzer.compare_with_peers(
                    symbol, peer_symbols
                )

            return {
                "metrics": metrics,
                "growth_trend": growth_trend,
                "health_score": health_score,
                "peer_comparison": comparison,
                "status": "success",
            }

        except Exception as e:
            logger.error(f"ファンダメンタルズ分析エラー {symbol}: {str(e)}")
            return {
                "metrics": None,
                "growth_trend": None,
                "health_score": None,
                "peer_comparison": None,
                "status": "error",
                "error_message": str(e),
            }

    def _perform_basic_technical_analysis(
        self, symbol: str
    ) -> Optional[TechnicalAnalysisData]:
        """基本的なテクニカル分析の実行"""
        try:
            # 株価データを取得
            stock_data = self.data_collector.get_stock_data(
                symbol, interval="1d", period="3mo"
            )

            if stock_data is None or stock_data.empty:
                logger.warning(f"株価データが取得できません: {symbol}")
                return None

            # 基本的なテクニカル指標を計算
            closes = stock_data["close"]
            current_price = closes.iloc[-1]

            # トレンド判定（20日移動平均との比較）
            if len(closes) >= 20:
                ma20 = closes.rolling(20).mean().iloc[-1]
                if current_price > ma20 * 1.02:
                    trend = "上昇"
                elif current_price < ma20 * 0.98:
                    trend = "下降"
                else:
                    trend = "横ばい"
            else:
                trend = "横ばい"

            # モメンタム判定（5日と20日の移動平均比較）
            if len(closes) >= 20:
                ma5 = closes.rolling(5).mean().iloc[-1]
                ma20 = closes.rolling(20).mean().iloc[-1]
                if ma5 > ma20 * 1.01:
                    momentum = "強い"
                elif ma5 < ma20 * 0.99:
                    momentum = "弱い"
                else:
                    momentum = "普通"
            else:
                momentum = "普通"

            # サポート・レジスタンスレベル（簡易版）
            high_prices = stock_data["high"]
            low_prices = stock_data["low"]

            support_level = low_prices.tail(20).min()
            resistance_level = high_prices.tail(20).max()

            # シグナル判定
            if trend == "上昇" and momentum == "強い":
                signal = "買い"
            elif trend == "下降" and momentum == "弱い":
                signal = "売り"
            else:
                signal = "中立"

            return TechnicalAnalysisData(
                trend=trend,
                momentum=momentum,
                support_level=support_level,
                resistance_level=resistance_level,
                signal=signal,
            )

        except Exception as e:
            logger.error(f"テクニカル分析エラー {symbol}: {str(e)}")
            return TechnicalAnalysisData(trend="不明", momentum="普通", signal="中立")

    def _generate_investment_story(
        self,
        symbol: str,
        fundamental_results: Dict[str, Any],
        technical_data: Optional[TechnicalAnalysisData],
    ) -> Optional[InvestmentReport]:
        """投資ストーリーの生成"""
        try:
            metrics = fundamental_results.get("metrics")
            growth_trend = fundamental_results.get("growth_trend")
            health_score = fundamental_results.get("health_score")
            comparison = fundamental_results.get("peer_comparison")

            current_price = None
            if metrics and metrics.price:
                current_price = metrics.price

            return self.story_generator.generate_comprehensive_report(
                symbol=symbol,
                financial_metrics=metrics,
                growth_trend=growth_trend,
                health_score=health_score,
                comparison=comparison,
                technical_data=technical_data,
                current_price=current_price,
            )

        except Exception as e:
            logger.error(f"投資ストーリー生成エラー {symbol}: {str(e)}")
            return None

    def _create_analysis_summary(
        self,
        symbol: str,
        fundamental_results: Dict[str, Any],
        technical_data: Optional[TechnicalAnalysisData],
        investment_report: Optional[InvestmentReport],
    ) -> Dict[str, Any]:
        """分析サマリーの作成"""

        summary = {
            "symbol": symbol,
            "overall_score": 0.0,
            "recommendation": "様子見",
            "key_strengths": [],
            "key_concerns": [],
            "next_actions": [],
        }

        # ファンダメンタルズ評価
        fundamental_score = 0.0
        if fundamental_results.get("status") == "success":
            health_score = fundamental_results.get("health_score")
            if health_score:
                fundamental_score = health_score.total_score

                if health_score.total_score >= 80:
                    summary["key_strengths"].append("優秀な財務健全性")
                elif health_score.total_score >= 60:
                    summary["key_strengths"].append("良好な財務状況")
                else:
                    summary["key_concerns"].append("財務状況の改善が必要")

            # 成長性評価
            growth_trend = fundamental_results.get("growth_trend")
            if growth_trend and growth_trend.revenue_cagr:
                if growth_trend.revenue_cagr > 0.1:
                    summary["key_strengths"].append("高い成長性")
                elif growth_trend.revenue_cagr < 0:
                    summary["key_concerns"].append("売上成長の鈍化")

        # テクニカル評価
        technical_score = 50.0  # デフォルト
        if technical_data:
            if technical_data.signal == "買い":
                technical_score = 80.0
                summary["key_strengths"].append("良好なテクニカルシグナル")
            elif technical_data.signal == "売り":
                technical_score = 20.0
                summary["key_concerns"].append("弱いテクニカルシグナル")

        # 総合スコア計算
        summary["overall_score"] = fundamental_score * 0.7 + technical_score * 0.3

        # 推奨判断
        if summary["overall_score"] >= 75:
            summary["recommendation"] = "買い推奨"
            summary["next_actions"] = [
                "ポジションサイズを決定して投資実行",
                "四半期決算の動向を監視",
                "利益確定の目標価格を設定",
            ]
        elif summary["overall_score"] >= 60:
            summary["recommendation"] = "条件付き買い"
            summary["next_actions"] = [
                "追加分析での確認後に投資検討",
                "リスク管理の徹底",
                "市場環境の変化を注視",
            ]
        elif summary["overall_score"] >= 40:
            summary["recommendation"] = "保有・様子見"
            summary["next_actions"] = [
                "既存ポジションは維持",
                "業績改善の兆候を監視",
                "市場トレンドの確認",
            ]
        else:
            summary["recommendation"] = "売り検討"
            summary["next_actions"] = [
                "ポジション削減を検討",
                "損切りラインの見直し",
                "代替投資先の検討",
            ]

        return summary

    def _create_error_analysis(self, symbol: str, error_message: str) -> Dict[str, Any]:
        """エラー時のデフォルト分析結果"""
        return {
            "symbol": symbol,
            "analysis_date": datetime.now(),
            "status": "error",
            "error_message": error_message,
            "fundamental_analysis": {"status": "error", "error_message": error_message},
            "technical_analysis": None,
            "investment_report": None,
            "summary": {
                "symbol": symbol,
                "overall_score": 0.0,
                "recommendation": "データ不足により判断不可",
                "key_strengths": [],
                "key_concerns": ["分析データの取得に失敗"],
                "next_actions": ["データ取得後の再分析を実施"],
            },
        }

    def generate_comparison_report(
        self, symbols: List[str], include_technical: bool = True
    ) -> Dict[str, Any]:
        """複数銘柄の比較レポートを生成"""
        try:
            logger.info(f"比較分析開始: {symbols}")

            comparison_results = {}

            for symbol in symbols:
                logger.info(f"分析中: {symbol}")
                analysis = self.generate_complete_analysis(symbol, include_peers=False)
                comparison_results[symbol] = analysis

            # 比較サマリーの作成
            comparison_summary = self._create_comparison_summary(comparison_results)

            result = {
                "comparison_type": "multi_symbol",
                "symbols": symbols,
                "analysis_date": datetime.now(),
                "individual_analyses": comparison_results,
                "comparison_summary": comparison_summary,
            }

            logger.info(f"比較分析完了: {symbols}")
            return result

        except Exception as e:
            logger.error(f"比較分析エラー: {str(e)}")
            return {
                "comparison_type": "multi_symbol",
                "symbols": symbols,
                "analysis_date": datetime.now(),
                "status": "error",
                "error_message": str(e),
            }

    def _create_comparison_summary(
        self, comparison_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """比較サマリーの作成"""

        summary = {
            "ranking": [],
            "best_value": None,
            "best_growth": None,
            "best_quality": None,
            "recommendations": [],
        }

        valid_results = {
            symbol: result
            for symbol, result in comparison_results.items()
            if result.get("summary", {}).get("overall_score", 0) > 0
        }

        if not valid_results:
            return summary

        # 総合スコアランキング
        ranking = sorted(
            valid_results.items(),
            key=lambda x: x[1].get("summary", {}).get("overall_score", 0),
            reverse=True,
        )

        summary["ranking"] = [
            {
                "symbol": symbol,
                "score": result.get("summary", {}).get("overall_score", 0),
                "recommendation": result.get("summary", {}).get(
                    "recommendation", "不明"
                ),
            }
            for symbol, result in ranking
        ]

        # カテゴリ別ベスト
        for symbol, result in valid_results.items():
            fundamental = result.get("fundamental_analysis", {})
            health_score = fundamental.get("health_score")
            growth_trend = fundamental.get("growth_trend")

            # バリュー投資向け（財務健全性重視）
            if health_score and health_score.total_score >= 80:
                if summary["best_quality"] is None:
                    summary["best_quality"] = symbol

            # 成長投資向け（成長率重視）
            if (
                growth_trend
                and growth_trend.revenue_cagr
                and growth_trend.revenue_cagr > 0.1
            ):
                if summary["best_growth"] is None:
                    summary["best_growth"] = symbol

            # バリュー投資向け（PERの低さ重視）
            metrics = fundamental.get("metrics")
            if metrics and metrics.per and metrics.per < 15:
                if summary["best_value"] is None:
                    summary["best_value"] = symbol

        # 推奨事項
        if len(ranking) > 0:
            top_symbol = ranking[0][0]
            summary["recommendations"].append(
                f"総合評価では{top_symbol}が最も魅力的な投資機会です"
            )

        if summary["best_growth"] and summary["best_growth"] != (
            ranking[0][0] if ranking else None
        ):
            summary["recommendations"].append(
                f"成長性を重視する場合は{summary['best_growth']}も検討に値します"
            )

        if summary["best_quality"]:
            summary["recommendations"].append(
                f"安定性を重視する場合は{summary['best_quality']}が適しています"
            )

        return summary
