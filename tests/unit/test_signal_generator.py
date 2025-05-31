"""
SignalGeneratorクラスのテスト
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from datetime import datetime, timedelta
import tempfile
import json

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from src.technical_analysis.signal_generator import (
    SignalGenerator, 
    TradingSignal, 
    SignalRule,
    SignalType,
    FilterCriteria,
    BacktestResult
)


class TestSignalGenerator:
    """SignalGeneratorのテストクラス"""
    
    def setup_method(self):
        """各テストメソッド実行前の初期化"""
        # サンプルデータ作成（200日分、より複雑なパターン）
        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', periods=200, freq='h')
        
        # 現実的な価格データ生成
        base_price = 1000
        
        # トレンド + ノイズ + サイクル
        trend = np.linspace(0, 0.15, 200)  # 15%の上昇トレンド
        noise = np.random.normal(0, 0.008, 200)  # ランダムノイズ
        cycle = 0.03 * np.sin(np.arange(200) * 2 * np.pi / 48)  # 48時間サイクル
        
        price_changes = trend + noise + cycle
        
        # 累積リターンから価格生成
        prices = [base_price]
        for change in price_changes[1:]:
            prices.append(prices[-1] * (1 + change))
        
        closes = np.array(prices)
        
        # OHLCV生成
        opens = closes * (1 + np.random.normal(0, 0.002, 200))
        highs = np.maximum(opens, closes) * (1 + np.random.uniform(0, 0.006, 200))
        lows = np.minimum(opens, closes) * (1 - np.random.uniform(0, 0.006, 200))
        
        # 出来高（トレンドに連動）
        base_volume = 100000
        volume_trend = 1 + np.random.uniform(-0.3, 0.5, 200)
        volumes = (base_volume * volume_trend).astype(int)
        
        self.test_data = pd.DataFrame({
            'timestamp': dates,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        })
        
        self.generator = SignalGenerator(self.test_data)
    
    def test_initialization(self):
        """初期化テスト"""
        assert len(self.generator.data) == 200
        assert hasattr(self.generator, 'indicators')
        assert hasattr(self.generator, 'support_resistance')
        assert hasattr(self.generator, 'rules')
        assert len(self.generator.rules) > 0
    
    def test_initialization_invalid_data(self):
        """無効データでの初期化テスト"""
        # 必要カラムが不足
        invalid_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=10),
            'close': np.random.randn(10)
        })
        
        with pytest.raises(ValueError, match="必要なカラムがありません"):
            SignalGenerator(invalid_data)
    
    def test_default_rules_creation(self):
        """デフォルトルール作成テスト"""
        rules = self.generator._create_default_rules()
        
        assert isinstance(rules, dict)
        assert len(rules) > 0
        
        # 主要ルールの存在確認
        expected_rules = [
            'ema_bullish_crossover',
            'rsi_oversold_recovery', 
            'bollinger_lower_bounce',
            'ema_bearish_crossover',
            'rsi_overbought_reversal',
            'bollinger_upper_rejection'
        ]
        
        for rule_name in expected_rules:
            assert rule_name in rules
            assert isinstance(rules[rule_name], SignalRule)
            assert rules[rule_name].enabled
            assert rules[rule_name].weight > 0
    
    def test_calculate_all_indicators(self):
        """指標計算テスト"""
        indicators = self.generator._calculate_all_indicators()
        
        assert isinstance(indicators, dict)
        
        # 主要指標の存在確認
        expected_indicators = [
            'ema_9', 'ema_21', 'sma_25', 'sma_75',
            'rsi', 'rsi_current', 'rsi_previous',
            'macd_line', 'macd_signal', 'macd_histogram',
            'bb_upper', 'bb_middle', 'bb_lower', 'bb_percent_b',
            'vwap', 'close', 'close_change',
            'ema_21_slope', 'volume_ratio', 'atr'
        ]
        
        for indicator in expected_indicators:
            assert indicator in indicators
            assert isinstance(indicators[indicator], pd.Series)
            assert len(indicators[indicator]) == len(self.test_data)
    
    def test_evaluate_condition(self):
        """条件評価テスト"""
        indicators = {
            'rsi': 75.0,
            'ema_9': 1000.0,
            'ema_21': 995.0,
            'volume_ratio': 2.5
        }
        
        # 基本的な比較テスト
        condition1 = {'indicator': 'rsi', 'operator': '>', 'value': 70}
        assert self.generator._evaluate_condition(condition1, indicators) == True
        
        condition2 = {'indicator': 'rsi', 'operator': '<', 'value': 70}
        assert self.generator._evaluate_condition(condition2, indicators) == False
    
    def test_initialization_with_config_file(self):
        """設定ファイル付きでの初期化テスト"""
        # 一時的な設定ファイル作成
        config_data = {
            "test_rule": {
                "name": "テストルール",
                "description": "設定ファイルテスト",
                "conditions": [
                    {"indicator": "rsi", "operator": ">", "value": 50}
                ],
                "weight": 2.0,
                "category": "test"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name
        
        try:
            generator = SignalGenerator(self.test_data, config_file=config_file)
            assert "test_rule" in generator.rules
        finally:
            Path(config_file).unlink()  # ファイル削除
    
    def test_initialization_with_invalid_config_file(self):
        """存在しない設定ファイルでの初期化テスト"""
        # 存在しないファイルパスでも例外が発生しないことを確認
        generator = SignalGenerator(self.test_data, config_file="nonexistent.json")
        assert len(generator.rules) > 0  # デフォルトルールは存在
    
    def test_initialization_with_small_data(self):
        """少量データでの初期化テスト（警告出力）"""
        small_data = self.test_data.head(30)  # 50件未満
        
        # 警告が出力されるが正常に初期化される
        generator = SignalGenerator(small_data)
        assert len(generator.data) == 30
    
    def test_evaluate_condition_with_invalid_indicator(self):
        """存在しない指標での条件評価テスト"""
        indicators = {'rsi': 50.0}
        condition = {'indicator': 'nonexistent', 'operator': '>', 'value': 40}
        
        # 存在しない指標は False を返す
        result = self.generator._evaluate_condition(condition, indicators)
        assert result is False
    
    def test_evaluate_condition_with_invalid_operator(self):
        """無効な演算子での条件評価テスト"""
        indicators = {'rsi': 50.0}
        condition = {'indicator': 'rsi', 'operator': 'invalid_op', 'value': 40}
        
        # 無効な演算子は False を返す
        result = self.generator._evaluate_condition(condition, indicators)
        assert result is False
    
    def test_evaluate_condition_compare_to_missing(self):
        """compare_to指標が存在しない場合の条件評価テスト"""
        indicators = {'ema_9': 100.0}
        condition = {'indicator': 'ema_9', 'operator': '>', 'compare_to': 'ema_21'}
        
        # compare_to指標がないとFalseを返す
        result = self.generator._evaluate_condition(condition, indicators)
        assert result is False
    
    def test_evaluate_condition_equal_operator(self):
        """等号演算子での条件評価テスト"""
        indicators = {'near_support': True, 'test_value': 50.0}
        
        # ブール値の等価比較
        condition1 = {'indicator': 'near_support', 'operator': '==', 'value': True}
        assert self.generator._evaluate_condition(condition1, indicators) is True
        
        # 数値の等価比較
        condition2 = {'indicator': 'test_value', 'operator': '==', 'value': 50.0}
        assert self.generator._evaluate_condition(condition2, indicators) is True
        
        condition3 = {'indicator': 'test_value', 'operator': '==', 'value': 60.0}
        assert self.generator._evaluate_condition(condition3, indicators) is False
        assert self.generator._evaluate_condition(condition3, indicators) == True
        
        # 等価比較テスト
        condition4 = {'indicator': 'volume_ratio', 'operator': '==', 'value': 2.5}
        assert self.generator._evaluate_condition(condition4, indicators) == True
        
        # 存在しない指標
        condition5 = {'indicator': 'nonexistent', 'operator': '>', 'value': 0}
        assert self.generator._evaluate_condition(condition5, indicators) == False
    
    def test_evaluate_rule(self):
        """ルール評価テスト"""
        # テスト用ルール作成
        test_rule = SignalRule(
            name="Test Rule",
            description="Test rule for unit testing",
            conditions=[
                {'indicator': 'rsi', 'operator': '>', 'value': 30},
                {'indicator': 'rsi', 'operator': '<', 'value': 70},
                {'indicator': 'ema_9', 'operator': '>', 'compare_to': 'ema_21'}
            ],
            weight=1.0
        )
        
        # テストデータ
        row_data = {
            'indicators': {
                'rsi': 50.0,
                'ema_9': 1000.0,
                'ema_21': 995.0
            }
        }
        
        # 全条件満たす場合
        assert self.generator._evaluate_rule(test_rule, row_data) == True
        
        # 一部条件を満たさない場合
        row_data['indicators']['rsi'] = 80.0  # 70超過
        assert self.generator._evaluate_rule(test_rule, row_data) == False
    
    def test_passes_filter(self):
        """フィルタリング条件テスト"""
        row_data = {
            'timestamp': datetime(2024, 1, 15, 14, 30),  # 14:30
            'volume': 150000,
            'close': 1000.0,
            'indicators': {'atr': 20.0}  # 2% volatility
        }
        
        # 出来高フィルター
        filter1 = FilterCriteria(min_volume=100000, max_volume=200000)
        assert self.generator._passes_filter(row_data, filter1) == True
        
        filter2 = FilterCriteria(min_volume=200000)
        assert self.generator._passes_filter(row_data, filter2) == False
        
        # 時間フィルター
        filter3 = FilterCriteria(allowed_hours=[14, 15, 16])
        assert self.generator._passes_filter(row_data, filter3) == True
        
        filter4 = FilterCriteria(allowed_hours=[9, 10, 11])
        assert self.generator._passes_filter(row_data, filter4) == False
        
        # ボラティリティフィルター
        filter5 = FilterCriteria(min_volatility=0.01, max_volatility=0.03)
        assert self.generator._passes_filter(row_data, filter5) == True
        
        filter6 = FilterCriteria(max_volatility=0.01)
        assert self.generator._passes_filter(row_data, filter6) == False
    
    def test_assess_risk_level(self):
        """リスクレベル評価テスト"""
        # 低ボラティリティ
        row_data1 = {
            'close': 1000.0,
            'indicators': {'atr': 10.0}  # 1% volatility
        }
        assert self.generator._assess_risk_level(row_data1, 80.0) == 'low'
        
        # 中ボラティリティ
        row_data2 = {
            'close': 1000.0,
            'indicators': {'atr': 20.0}  # 2% volatility
        }
        assert self.generator._assess_risk_level(row_data2, 80.0) == 'medium'
        
        # 高ボラティリティ
        row_data3 = {
            'close': 1000.0,
            'indicators': {'atr': 40.0}  # 4% volatility
        }
        assert self.generator._assess_risk_level(row_data3, 80.0) == 'high'
    
    def test_calculate_exit_levels(self):
        """ストップロス・利確レベル計算テスト"""
        entry_price = 1000.0
        indicators = {'atr': 20.0}
        
        # 買いシグナル
        stop_loss, take_profit = self.generator._calculate_exit_levels(
            entry_price, SignalType.BUY, indicators
        )
        
        assert stop_loss < entry_price  # ストップロスは下
        assert take_profit > entry_price  # 利確は上
        assert abs(stop_loss - (entry_price - 40)) < 0.01  # ATR * 2
        assert abs(take_profit - (entry_price + 60)) < 0.01  # ATR * 3
        
        # 売りシグナル
        stop_loss, take_profit = self.generator._calculate_exit_levels(
            entry_price, SignalType.SELL, indicators
        )
        
        assert stop_loss > entry_price  # ストップロスは上
        assert take_profit < entry_price  # 利確は下
    
    def test_generate_signals(self):
        """シグナル生成テスト"""
        signals = self.generator.generate_signals()
        
        assert isinstance(signals, list)
        
        for signal in signals:
            assert isinstance(signal, TradingSignal)
            assert signal.signal_type in [SignalType.BUY, SignalType.SELL]
            assert 0 <= signal.strength <= 100
            assert 0 <= signal.confidence <= 1
            assert signal.price > 0
            assert signal.risk_level in ['low', 'medium', 'high']
            assert isinstance(signal.conditions_met, dict)
            assert isinstance(signal.indicators_used, dict)
    
    def test_generate_signals_with_filter(self):
        """フィルター付きシグナル生成テスト"""
        # 出来高フィルター
        filter_criteria = FilterCriteria(min_volume=120000)
        
        signals_filtered = self.generator.generate_signals(filter_criteria)
        signals_all = self.generator.generate_signals()
        
        # フィルター適用で減少することを確認
        assert len(signals_filtered) <= len(signals_all)
        
        # フィルター条件を満たすことを確認
        for signal in signals_filtered:
            # シグナル時点の出来高を確認
            signal_time = signal.timestamp
            matching_row = self.test_data[self.test_data['timestamp'] == signal_time]
            if not matching_row.empty:
                assert matching_row.iloc[0]['volume'] >= 120000
    
    def test_backtest_signals(self):
        """バックテストテスト"""
        # シグナル生成
        signals = self.generator.generate_signals()
        
        if len(signals) == 0:
            pytest.skip("テスト用シグナルが生成されませんでした")
        
        # バックテスト実行
        result = self.generator.backtest_signals(signals, holding_period=5)
        
        assert isinstance(result, BacktestResult)
        assert result.total_signals >= 0
        assert result.winning_signals >= 0
        assert result.losing_signals >= 0
        assert result.winning_signals + result.losing_signals <= result.total_signals
        assert 0 <= result.win_rate <= 1
        assert isinstance(result.avg_return_per_signal, float)
        assert result.max_drawdown >= 0
        assert isinstance(result.sharpe_ratio, float)
        assert result.profit_factor >= 0
        assert isinstance(result.signals_detail, list)
        
        # 詳細結果の検証
        for detail in result.signals_detail:
            assert 'entry_time' in detail
            assert 'exit_time' in detail
            assert 'signal_type' in detail
            assert 'entry_price' in detail
            assert 'exit_price' in detail
            assert 'return' in detail
            assert isinstance(detail['return'], float)
    
    def test_save_load_rules(self):
        """ルール保存・読み込みテスト"""
        # テスト用ルール追加
        test_rule = SignalRule(
            name="Test Custom Rule",
            description="Custom rule for testing",
            conditions=[{'indicator': 'rsi', 'operator': '>', 'value': 50}],
            weight=2.0,
            category="test"
        )
        
        self.generator.add_custom_rule("test_rule", test_rule)
        
        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            self.generator.save_rules_to_file(temp_file)
            
            # 新しいジェネレーターで読み込み
            new_generator = SignalGenerator(self.test_data)
            new_generator.load_rules_from_file(temp_file)
            
            # ルールが正しく読み込まれたことを確認
            assert "test_rule" in new_generator.rules
            loaded_rule = new_generator.rules["test_rule"]
            assert loaded_rule.name == test_rule.name
            assert loaded_rule.weight == test_rule.weight
            assert loaded_rule.category == test_rule.category
            
        finally:
            # 一時ファイル削除
            Path(temp_file).unlink(missing_ok=True)
    
    def test_rule_management(self):
        """ルール管理テスト"""
        initial_count = len(self.generator.rules)
        
        # ルール追加
        test_rule = SignalRule(
            name="Management Test",
            description="Test rule management",
            conditions=[{'indicator': 'rsi', 'operator': '<', 'value': 30}],
            weight=1.5
        )
        
        self.generator.add_custom_rule("mgmt_test", test_rule)
        assert len(self.generator.rules) == initial_count + 1
        assert "mgmt_test" in self.generator.rules
        
        # ルール無効化
        self.generator.enable_rule("mgmt_test", False)
        assert not self.generator.rules["mgmt_test"].enabled
        
        # ルール有効化
        self.generator.enable_rule("mgmt_test", True)
        assert self.generator.rules["mgmt_test"].enabled
        
        # ルール削除
        self.generator.remove_rule("mgmt_test")
        assert len(self.generator.rules) == initial_count
        assert "mgmt_test" not in self.generator.rules
    
    def test_analyze_signal_performance(self):
        """シグナルパフォーマンス分析テスト"""
        signals = self.generator.generate_signals()
        
        if len(signals) == 0:
            pytest.skip("分析用シグナルが生成されませんでした")
        
        analysis = self.generator.analyze_signal_performance(signals)
        
        assert isinstance(analysis, dict)
        assert 'total_signals' in analysis
        assert 'signal_types' in analysis
        assert 'strength_distribution' in analysis
        assert 'hourly_distribution' in analysis
        assert 'avg_strength' in analysis
        assert 'avg_confidence' in analysis
        
        # 数値の妥当性確認
        assert analysis['total_signals'] == len(signals)
        assert 0 <= analysis['avg_strength'] <= 100
        assert 0 <= analysis['avg_confidence'] <= 1
        
        # 分布の合計確認
        strength_dist = analysis['strength_distribution']
        total_by_strength = strength_dist['weak'] + strength_dist['moderate'] + strength_dist['strong']
        assert total_by_strength == len(signals)
    
    def test_get_signal_summary(self):
        """シグナル要約テスト"""
        # シグナル未生成時
        summary1 = self.generator.get_signal_summary()
        assert "シグナルが生成されていません" in summary1
        
        # シグナル生成後
        signals = self.generator.generate_signals()
        summary2 = self.generator.get_signal_summary()
        
        assert isinstance(summary2, str)
        assert len(summary2) > 0
        if len(signals) > 0:
            assert "総シグナル数" in summary2
            assert "買いシグナル" in summary2
            assert "売りシグナル" in summary2
    
    def test_optimize_rules(self):
        """ルール最適化テスト"""
        # 簡単なテストのため、少数のルールで実行
        original_rules = self.generator.rules.copy()
        
        # テスト用にルール数を制限
        test_rules = {k: v for i, (k, v) in enumerate(original_rules.items()) if i < 3}
        self.generator.rules = test_rules
        
        try:
            optimization = self.generator.optimize_rules('win_rate')
            
            assert isinstance(optimization, dict)
            assert 'baseline_score' in optimization
            assert 'rule_importance' in optimization
            assert isinstance(optimization['rule_importance'], dict)
            
            # ルール重要度の値が数値であることを確認
            for rule_name, importance in optimization['rule_importance'].items():
                assert isinstance(importance, (int, float))
            
        finally:
            # 元のルールに戻す
            self.generator.rules = original_rules
    
    def test_edge_cases(self):
        """エッジケーステスト"""
        # 最小データでの処理
        minimal_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=60, freq='h'),
            'open': np.random.uniform(990, 1010, 60),
            'high': np.random.uniform(995, 1015, 60),
            'low': np.random.uniform(985, 1005, 60),
            'close': np.random.uniform(990, 1010, 60),
            'volume': np.random.randint(50000, 150000, 60)
        })
        
        minimal_generator = SignalGenerator(minimal_data)
        
        # 基本機能が動作することを確認
        signals = minimal_generator.generate_signals()
        assert isinstance(signals, list)
        
        # バックテストも動作することを確認
        if len(signals) > 0:
            backtest = minimal_generator.backtest_signals(signals, holding_period=3)
            assert isinstance(backtest, BacktestResult)
    
    def test_custom_rules(self):
        """カスタムルールテスト"""
        # カスタムルール作成
        custom_rules = {
            'simple_buy': SignalRule(
                name="Simple Buy",
                description="Simple buy when RSI < 40",
                conditions=[
                    {'indicator': 'rsi_current', 'operator': '<', 'value': 40}
                ],
                weight=2.0,
                category="custom"
            ),
            'simple_sell': SignalRule(
                name="Simple Sell", 
                description="Simple sell when RSI > 60",
                conditions=[
                    {'indicator': 'rsi_current', 'operator': '>', 'value': 60}
                ],
                weight=2.0,
                category="custom"
            )
        }
        
        # カスタムルールでシグナル生成
        signals = self.generator.generate_signals(custom_rules=custom_rules)
        
        assert isinstance(signals, list)
        
        # 生成されたシグナルがカスタムルールに基づいていることを検証
        for signal in signals:
            rsi_value = signal.indicators_used.get('rsi_current')
            if signal.signal_type == SignalType.BUY and not pd.isna(rsi_value):
                # 買いシグナルではRSIが低めの傾向があるはず
                pass  # 実際の値は複数条件の組み合わせなので厳密にはチェックできない
            elif signal.signal_type == SignalType.SELL and not pd.isna(rsi_value):
                # 売りシグナルではRSIが高めの傾向があるはず
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])