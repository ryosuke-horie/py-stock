"""
ポートフォリオリスク分析システム

ポートフォリオ全体のリスク評価、相関分析、最適化提案を提供する。
現代ポートフォリオ理論とモンテカルロシミュレーションを用いた包括的な分析機能。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from scipy import optimize
from scipy.stats import norm
import warnings

from .risk_manager import RiskManager, Position

logger = logging.getLogger(__name__)
warnings.filterwarnings('ignore', category=RuntimeWarning)


@dataclass
class PortfolioHolding:
    """ポートフォリオ保有銘柄情報"""
    symbol: str
    quantity: float
    current_price: float
    market_value: float
    weight: float  # ポートフォリオ内の重み（%）
    
    @classmethod
    def from_position(cls, position: Position, portfolio_value: float):
        """Positionオブジェクトから作成"""
        market_value = position.current_price * position.quantity
        weight = (market_value / portfolio_value) * 100 if portfolio_value > 0 else 0
        
        return cls(
            symbol=position.symbol,
            quantity=position.quantity,
            current_price=position.current_price or 0,
            market_value=market_value,
            weight=weight
        )


@dataclass
class RiskMetrics:
    """リスク指標"""
    portfolio_var_95: float  # 95%信頼度VaR
    portfolio_var_99: float  # 99%信頼度VaR
    portfolio_cvar_95: float  # 95%信頼度CVaR (Expected Shortfall)
    portfolio_volatility: float  # ポートフォリオボラティリティ
    sharpe_ratio: float  # シャープレシオ
    max_drawdown: float  # 最大ドローダウン
    diversification_ratio: float  # 分散効果


@dataclass
class CorrelationAnalysis:
    """相関分析結果"""
    correlation_matrix: pd.DataFrame
    average_correlation: float
    max_correlation: float
    min_correlation: float
    high_correlation_pairs: List[Tuple[str, str, float]]  # 相関係数0.7以上のペア


@dataclass
class OptimizationResult:
    """最適化結果"""
    optimal_weights: Dict[str, float]
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    optimization_type: str  # 'min_variance', 'max_sharpe', 'target_return'


class PortfolioAnalyzer:
    """ポートフォリオリスク分析クラス"""
    
    def __init__(self, risk_manager: RiskManager = None):
        """
        初期化
        
        Args:
            risk_manager: RiskManagerインスタンス（オプション）
        """
        self.risk_manager = risk_manager
        self.price_history: Dict[str, pd.DataFrame] = {}
        self.returns_cache: Optional[pd.DataFrame] = None
        self.cache_timestamp: Optional[datetime] = None
        
    def set_price_history(self, price_data: Dict[str, pd.DataFrame]):
        """
        価格履歴データを設定
        
        Args:
            price_data: {symbol: DataFrame} 銘柄別価格データ
        """
        self.price_history = price_data
        self.returns_cache = None  # キャッシュをクリア
        logger.info(f"Price history set for {len(price_data)} symbols")
    
    def _calculate_returns(self, periods: int = 252) -> pd.DataFrame:
        """
        リターンを計算（キャッシュ機能付き）
        
        Args:
            periods: 計算期間（日数）
            
        Returns:
            リターンデータフレーム
        """
        current_time = datetime.now()
        
        # キャッシュが有効かチェック（5分以内）
        if (self.returns_cache is not None and 
            self.cache_timestamp is not None and 
            (current_time - self.cache_timestamp).seconds < 300):
            return self.returns_cache
        
        returns_data = {}
        
        for symbol, price_df in self.price_history.items():
            if len(price_df) < periods:
                logger.warning(f"Insufficient data for {symbol}: {len(price_df)} < {periods}")
                continue
            
            # 直近のデータを使用
            recent_data = price_df.tail(periods)
            if 'Close' in recent_data.columns:
                daily_returns = recent_data['Close'].pct_change().dropna()
            elif 'close' in recent_data.columns:
                daily_returns = recent_data['close'].pct_change().dropna()
            else:
                logger.warning(f"No price column found for {symbol}")
                continue
            
            returns_data[symbol] = daily_returns
        
        if not returns_data:
            logger.error("No valid return data calculated")
            return pd.DataFrame()
        
        # データフレーム作成
        self.returns_cache = pd.DataFrame(returns_data).dropna()
        self.cache_timestamp = current_time
        
        logger.info(f"Calculated returns for {len(returns_data)} symbols over {len(self.returns_cache)} periods")
        return self.returns_cache
    
    def get_portfolio_holdings(self) -> List[PortfolioHolding]:
        """
        現在のポートフォリオ保有銘柄を取得
        
        Returns:
            ポートフォリオ保有銘柄リスト
        """
        if not self.risk_manager or not self.risk_manager.positions:
            return []
        
        # 総ポートフォリオ価値計算
        total_value = sum(
            (pos.current_price or 0) * pos.quantity 
            for pos in self.risk_manager.positions.values()
        )
        
        holdings = []
        for position in self.risk_manager.positions.values():
            if position.current_price is not None:
                holding = PortfolioHolding.from_position(position, total_value)
                holdings.append(holding)
        
        return holdings
    
    def calculate_portfolio_var(self, confidence_level: float = 0.95, 
                              holding_period: int = 1) -> Dict[str, float]:
        """
        ポートフォリオVaR（Value at Risk）を計算
        
        Args:
            confidence_level: 信頼度（0.95 = 95%）
            holding_period: 保有期間（日数）
            
        Returns:
            VaR計算結果
        """
        try:
            holdings = self.get_portfolio_holdings()
            if not holdings:
                return {"var": 0.0, "cvar": 0.0, "portfolio_value": 0.0}
            
            returns_df = self._calculate_returns()
            if returns_df.empty:
                return {"var": 0.0, "cvar": 0.0, "portfolio_value": 0.0}
            
            # ポートフォリオの重みベクトル作成
            symbols = [h.symbol for h in holdings]
            weights = np.array([h.weight / 100 for h in holdings])
            
            # 保有銘柄のリターンのみ抽出
            portfolio_symbols = [s for s in symbols if s in returns_df.columns]
            if not portfolio_symbols:
                return {"var": 0.0, "cvar": 0.0, "portfolio_value": 0.0}
            
            returns_subset = returns_df[portfolio_symbols]
            weights_subset = weights[:len(portfolio_symbols)]
            weights_subset = weights_subset / weights_subset.sum()  # 正規化
            
            # ポートフォリオリターン計算
            portfolio_returns = (returns_subset * weights_subset).sum(axis=1)
            
            # ポートフォリオ価値
            portfolio_value = sum(h.market_value for h in holdings)
            
            # VaR計算（ヒストリカル法）
            var_percentile = (1 - confidence_level) * 100
            var_return = np.percentile(portfolio_returns, var_percentile)
            var_amount = abs(var_return * portfolio_value * np.sqrt(holding_period))
            
            # CVaR（Expected Shortfall）計算
            tail_returns = portfolio_returns[portfolio_returns <= var_return]
            if len(tail_returns) > 0:
                cvar_return = tail_returns.mean()
                cvar_amount = abs(cvar_return * portfolio_value * np.sqrt(holding_period))
            else:
                cvar_amount = var_amount
            
            # パラメトリック法によるVaR（参考値）
            portfolio_vol = portfolio_returns.std() * np.sqrt(252)  # 年率化
            parametric_var = norm.ppf(1 - confidence_level) * portfolio_vol * portfolio_value * np.sqrt(holding_period / 252)
            
            return {
                "var_historical": var_amount,
                "cvar": cvar_amount,
                "var_parametric": abs(parametric_var),
                "portfolio_value": portfolio_value,
                "portfolio_volatility": portfolio_vol,
                "confidence_level": confidence_level,
                "holding_period": holding_period
            }
            
        except Exception as e:
            logger.error(f"Error calculating portfolio VaR: {e}")
            return {"var": 0.0, "cvar": 0.0, "portfolio_value": 0.0}
    
    def analyze_correlations(self) -> CorrelationAnalysis:
        """
        銘柄間相関分析
        
        Returns:
            相関分析結果
        """
        try:
            returns_df = self._calculate_returns()
            if returns_df.empty or len(returns_df.columns) < 2:
                return CorrelationAnalysis(
                    correlation_matrix=pd.DataFrame(),
                    average_correlation=0.0,
                    max_correlation=0.0,
                    min_correlation=0.0,
                    high_correlation_pairs=[]
                )
            
            # 相関行列計算
            correlation_matrix = returns_df.corr()
            
            # 対角成分（自己相関）を除外
            corr_values = correlation_matrix.values
            mask = np.triu(np.ones_like(corr_values, dtype=bool), k=1)
            upper_triangle = corr_values[mask]
            
            # 統計計算
            avg_correlation = np.mean(upper_triangle)
            max_correlation = np.max(upper_triangle)
            min_correlation = np.min(upper_triangle)
            
            # 高相関ペアの抽出（相関係数0.7以上）
            high_corr_pairs = []
            symbols = correlation_matrix.columns.tolist()
            
            for i in range(len(symbols)):
                for j in range(i + 1, len(symbols)):
                    corr_value = correlation_matrix.iloc[i, j]
                    if abs(corr_value) >= 0.7:
                        high_corr_pairs.append((symbols[i], symbols[j], corr_value))
            
            # 相関の高い順にソート
            high_corr_pairs.sort(key=lambda x: abs(x[2]), reverse=True)
            
            return CorrelationAnalysis(
                correlation_matrix=correlation_matrix,
                average_correlation=avg_correlation,
                max_correlation=max_correlation,
                min_correlation=min_correlation,
                high_correlation_pairs=high_corr_pairs[:10]  # 上位10ペア
            )
            
        except Exception as e:
            logger.error(f"Error analyzing correlations: {e}")
            return CorrelationAnalysis(
                correlation_matrix=pd.DataFrame(),
                average_correlation=0.0,
                max_correlation=0.0,
                min_correlation=0.0,
                high_correlation_pairs=[]
            )
    
    def calculate_risk_metrics(self) -> RiskMetrics:
        """
        包括的リスク指標の計算
        
        Returns:
            リスク指標
        """
        try:
            # VaR計算
            var_95 = self.calculate_portfolio_var(0.95)
            var_99 = self.calculate_portfolio_var(0.99)
            
            returns_df = self._calculate_returns()
            if returns_df.empty:
                return RiskMetrics(0, 0, 0, 0, 0, 0, 0)
            
            holdings = self.get_portfolio_holdings()
            if not holdings:
                return RiskMetrics(0, 0, 0, 0, 0, 0, 0)
            
            # ポートフォリオリターン計算
            symbols = [h.symbol for h in holdings if h.symbol in returns_df.columns]
            if not symbols:
                return RiskMetrics(0, 0, 0, 0, 0, 0, 0)
            
            weights = np.array([h.weight / 100 for h in holdings if h.symbol in symbols])
            weights = weights / weights.sum()  # 正規化
            
            portfolio_returns = (returns_df[symbols] * weights).sum(axis=1)
            
            # ボラティリティ（年率化）
            portfolio_vol = portfolio_returns.std() * np.sqrt(252)
            
            # シャープレシオ（リスクフリーレート0%と仮定）
            annual_return = portfolio_returns.mean() * 252
            sharpe_ratio = annual_return / portfolio_vol if portfolio_vol > 0 else 0
            
            # 最大ドローダウン計算
            cumulative_returns = (1 + portfolio_returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = abs(drawdown.min())
            
            # 分散効果計算
            individual_vols = returns_df[symbols].std() * np.sqrt(252)
            weighted_avg_vol = (individual_vols * weights).sum()
            diversification_ratio = weighted_avg_vol / portfolio_vol if portfolio_vol > 0 else 1
            
            return RiskMetrics(
                portfolio_var_95=var_95.get("var_historical", 0),
                portfolio_var_99=var_99.get("var_historical", 0),
                portfolio_cvar_95=var_95.get("cvar", 0),
                portfolio_volatility=portfolio_vol,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                diversification_ratio=diversification_ratio
            )
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
            return RiskMetrics(0, 0, 0, 0, 0, 0, 0)
    
    def optimize_portfolio(self, optimization_type: str = "max_sharpe", 
                          target_return: float = None) -> OptimizationResult:
        """
        ポートフォリオ最適化
        
        Args:
            optimization_type: 最適化タイプ ('min_variance', 'max_sharpe', 'target_return')
            target_return: 目標リターン（optimization_type='target_return'時に使用）
            
        Returns:
            最適化結果
        """
        try:
            returns_df = self._calculate_returns()
            if returns_df.empty or len(returns_df.columns) < 2:
                return OptimizationResult({}, 0, 0, 0, optimization_type)
            
            # リターンと共分散行列計算
            mean_returns = returns_df.mean() * 252  # 年率化
            cov_matrix = returns_df.cov() * 252  # 年率化
            
            n_assets = len(mean_returns)
            
            # 制約条件：重みの合計=1、各重み>=0
            constraints = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]
            bounds = tuple((0, 1) for _ in range(n_assets))
            
            # 初期値：等重み
            x0 = np.array([1/n_assets] * n_assets)
            
            if optimization_type == "min_variance":
                # 最小分散ポートフォリオ
                def objective(weights):
                    return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
                
            elif optimization_type == "max_sharpe":
                # 最大シャープレシオポートフォリオ
                def objective(weights):
                    portfolio_return = np.sum(mean_returns * weights)
                    portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
                    return -portfolio_return / portfolio_vol if portfolio_vol > 0 else 0
                
            elif optimization_type == "target_return":
                # 目標リターン制約付き最小分散
                if target_return is None:
                    target_return = mean_returns.mean()
                
                constraints.append({
                    'type': 'eq', 
                    'fun': lambda x: np.sum(mean_returns * x) - target_return
                })
                
                def objective(weights):
                    return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            
            else:
                raise ValueError(f"Unknown optimization type: {optimization_type}")
            
            # 最適化実行
            result = optimize.minimize(
                objective, x0, method='SLSQP', 
                bounds=bounds, constraints=constraints,
                options={'maxiter': 1000}
            )
            
            if not result.success:
                logger.warning(f"Optimization failed: {result.message}")
                return OptimizationResult({}, 0, 0, 0, optimization_type)
            
            # 結果計算
            optimal_weights = dict(zip(mean_returns.index, result.x))
            expected_return = np.sum(mean_returns * result.x)
            expected_vol = np.sqrt(np.dot(result.x.T, np.dot(cov_matrix, result.x)))
            sharpe_ratio = expected_return / expected_vol if expected_vol > 0 else 0
            
            return OptimizationResult(
                optimal_weights=optimal_weights,
                expected_return=expected_return,
                expected_volatility=expected_vol,
                sharpe_ratio=sharpe_ratio,
                optimization_type=optimization_type
            )
            
        except Exception as e:
            logger.error(f"Error optimizing portfolio: {e}")
            return OptimizationResult({}, 0, 0, 0, optimization_type)
    
    def monte_carlo_stress_test(self, num_simulations: int = 10000, 
                               time_horizon: int = 252) -> Dict[str, float]:
        """
        モンテカルロシミュレーションによるストレステスト
        
        Args:
            num_simulations: シミュレーション回数
            time_horizon: 時間軸（日数）
            
        Returns:
            ストレステスト結果
        """
        try:
            holdings = self.get_portfolio_holdings()
            returns_df = self._calculate_returns()
            
            if not holdings or returns_df.empty:
                return {"var_95": 0, "var_99": 0, "expected_loss": 0, "worst_case": 0}
            
            # ポートフォリオの重みとリターン
            symbols = [h.symbol for h in holdings if h.symbol in returns_df.columns]
            if not symbols:
                return {"var_95": 0, "var_99": 0, "expected_loss": 0, "worst_case": 0}
            
            weights = np.array([h.weight / 100 for h in holdings if h.symbol in symbols])
            weights = weights / weights.sum()
            
            returns_subset = returns_df[symbols]
            mean_returns = returns_subset.mean()
            cov_matrix = returns_subset.cov()
            
            # ポートフォリオ価値
            portfolio_value = sum(h.market_value for h in holdings)
            
            # モンテカルロシミュレーション
            simulated_returns = []
            
            for _ in range(num_simulations):
                # 多変量正規分布からリターンをサンプリング
                random_returns = np.random.multivariate_normal(
                    mean_returns, cov_matrix, time_horizon
                )
                
                # ポートフォリオリターン計算
                portfolio_daily_returns = np.dot(random_returns, weights)
                
                # 累積リターン
                cumulative_return = np.prod(1 + portfolio_daily_returns) - 1
                simulated_returns.append(cumulative_return)
            
            simulated_returns = np.array(simulated_returns)
            
            # 損失の計算（負のリターン）
            losses = -simulated_returns * portfolio_value
            
            # VaR計算
            var_95 = np.percentile(losses, 95)
            var_99 = np.percentile(losses, 99)
            
            # 損失がある場合のみ平均を計算
            positive_losses = losses[losses > 0]
            expected_loss = np.mean(positive_losses) if len(positive_losses) > 0 else 0
            worst_case = np.max(losses)
            
            # 負の値のパーセンタイル
            negative_returns = simulated_returns[simulated_returns < 0]
            prob_loss = len(negative_returns) / len(simulated_returns) * 100
            
            return {
                "var_95": max(0, var_95),
                "var_99": max(0, var_99),
                "expected_loss": max(0, expected_loss),
                "worst_case": max(0, worst_case),
                "probability_of_loss": prob_loss,
                "simulations": num_simulations,
                "time_horizon": time_horizon,
                "portfolio_value": portfolio_value
            }
            
        except Exception as e:
            logger.error(f"Error in Monte Carlo stress test: {e}")
            return {"var_95": 0, "var_99": 0, "expected_loss": 0, "worst_case": 0}
    
    def generate_efficient_frontier(self, num_points: int = 50) -> Dict[str, List[float]]:
        """
        効率的フロンティアの生成
        
        Args:
            num_points: プロット点数
            
        Returns:
            効率的フロンティアデータ
        """
        try:
            returns_df = self._calculate_returns()
            if returns_df.empty or len(returns_df.columns) < 2:
                return {"returns": [], "volatilities": [], "sharpe_ratios": []}
            
            mean_returns = returns_df.mean() * 252
            cov_matrix = returns_df.cov() * 252
            
            # リターンの範囲設定
            min_ret = mean_returns.min()
            max_ret = mean_returns.max()
            target_returns = np.linspace(min_ret, max_ret, num_points)
            
            efficient_portfolios = []
            
            for target_ret in target_returns:
                try:
                    result = self.optimize_portfolio("target_return", target_ret)
                    if result.optimal_weights:
                        efficient_portfolios.append({
                            "return": result.expected_return,
                            "volatility": result.expected_volatility,
                            "sharpe_ratio": result.sharpe_ratio
                        })
                except:
                    continue
            
            if not efficient_portfolios:
                return {"returns": [], "volatilities": [], "sharpe_ratios": []}
            
            return {
                "returns": [p["return"] for p in efficient_portfolios],
                "volatilities": [p["volatility"] for p in efficient_portfolios],
                "sharpe_ratios": [p["sharpe_ratio"] for p in efficient_portfolios]
            }
            
        except Exception as e:
            logger.error(f"Error generating efficient frontier: {e}")
            return {"returns": [], "volatilities": [], "sharpe_ratios": []}
    
    def get_portfolio_analysis_summary(self) -> Dict:
        """
        ポートフォリオ分析の総合サマリー
        
        Returns:
            分析サマリー
        """
        try:
            holdings = self.get_portfolio_holdings()
            risk_metrics = self.calculate_risk_metrics()
            correlation_analysis = self.analyze_correlations()
            var_results = self.calculate_portfolio_var()
            stress_test = self.monte_carlo_stress_test()
            
            return {
                "portfolio_overview": {
                    "total_value": sum(h.market_value for h in holdings),
                    "num_holdings": len(holdings),
                    "holdings": [
                        {
                            "symbol": h.symbol,
                            "weight": h.weight,
                            "market_value": h.market_value,
                            "current_price": h.current_price
                        }
                        for h in holdings
                    ]
                },
                "risk_metrics": {
                    "var_95": risk_metrics.portfolio_var_95,
                    "var_99": risk_metrics.portfolio_var_99,
                    "cvar_95": risk_metrics.portfolio_cvar_95,
                    "volatility": risk_metrics.portfolio_volatility,
                    "sharpe_ratio": risk_metrics.sharpe_ratio,
                    "max_drawdown": risk_metrics.max_drawdown,
                    "diversification_ratio": risk_metrics.diversification_ratio
                },
                "correlation_analysis": {
                    "average_correlation": correlation_analysis.average_correlation,
                    "max_correlation": correlation_analysis.max_correlation,
                    "high_correlation_pairs": correlation_analysis.high_correlation_pairs[:5]
                },
                "stress_test": {
                    "monte_carlo_var_95": stress_test.get("var_95", 0),
                    "monte_carlo_var_99": stress_test.get("var_99", 0),
                    "worst_case_loss": stress_test.get("worst_case", 0),
                    "probability_of_loss": stress_test.get("probability_of_loss", 0)
                },
                "optimization_suggestions": self._generate_optimization_suggestions(
                    risk_metrics, correlation_analysis
                )
            }
            
        except Exception as e:
            logger.error(f"Error generating portfolio analysis summary: {e}")
            return {}
    
    def _generate_optimization_suggestions(self, risk_metrics: RiskMetrics, 
                                         correlation_analysis: CorrelationAnalysis) -> List[str]:
        """最適化提案の生成"""
        suggestions = []
        
        # シャープレシオが低い場合
        if risk_metrics.sharpe_ratio < 0.5:
            suggestions.append("シャープレシオが低いため、リスクリターン効率の改善を検討してください")
        
        # 分散効果が低い場合
        if risk_metrics.diversification_ratio < 1.2:
            suggestions.append("分散効果が限定的です。異なるセクターや資産クラスへの分散を検討してください")
        
        # 高相関ペアが多い場合
        if len(correlation_analysis.high_correlation_pairs) > 3:
            suggestions.append("高い相関を持つ銘柄ペアが多数あります。ポートフォリオの分散を見直してください")
        
        # 高ボラティリティの場合
        if risk_metrics.portfolio_volatility > 0.3:
            suggestions.append("ポートフォリオのボラティリティが高いため、より安定的な銘柄の組み入れを検討してください")
        
        # 最大ドローダウンが大きい場合
        if risk_metrics.max_drawdown > 0.2:
            suggestions.append("最大ドローダウンが大きいため、リスク管理の強化を検討してください")
        
        if not suggestions:
            suggestions.append("現在のポートフォリオは適切にリスク管理されています")
        
        return suggestions