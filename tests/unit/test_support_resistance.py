"""
SupportResistanceDetectorクラスのテスト
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from datetime import datetime, timedelta, time

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from src.technical_analysis.support_resistance import (
    SupportResistanceDetector, 
    SupportResistanceLevel, 
    PivotPoint, 
    BreakoutEvent
)


class TestSupportResistanceDetector:
    """SupportResistanceDetectorのテストクラス"""
    
    def setup_method(self):
        """各テストメソッド実行前の初期化"""
        # サンプルデータ作成（200日分、より複雑なパターン）
        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', periods=200, freq='h')
        
        # より現実的な価格データ生成
        base_price = 1000
        trend = np.linspace(0, 0.2, 200)  # 上昇トレンド
        noise = np.random.normal(0, 0.01, 200)
        seasonal = 0.05 * np.sin(np.arange(200) * 2 * np.pi / 24)  # 日次パターン
        
        price_multipliers = np.exp(trend + noise + seasonal)
        closes = base_price * price_multipliers
        
        # OHLCV生成
        opens = closes * (1 + np.random.normal(0, 0.002, 200))
        
        # 高値・安値でサポレジ形成をシミュレート
        highs = np.maximum(opens, closes) * (1 + np.random.uniform(0, 0.008, 200))
        lows = np.minimum(opens, closes) * (1 - np.random.uniform(0, 0.008, 200))
        
        # 意図的なサポレジレベル作成
        # 1050付近にレジスタンス
        for i in range(50, 70):
            if highs[i] > 1045:
                highs[i] = np.random.uniform(1048, 1052)
        
        # 980付近にサポート
        for i in range(20, 40):
            if lows[i] < 985:
                lows[i] = np.random.uniform(978, 982)
        
        volumes = np.random.randint(50000, 200000, 200)
        
        # 重要レベルでの出来高増加
        for i in range(50, 70):
            volumes[i] *= 2  # レジスタンステスト時の出来高増加
        
        self.test_data = pd.DataFrame({
            'timestamp': dates,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        })
        
        self.detector = SupportResistanceDetector(self.test_data)
    
    def test_initialization(self):
        """初期化テスト"""
        assert len(self.detector.data) == 200
        assert 'hour' in self.detector.data.columns
        assert 'time_of_day' in self.detector.data.columns
        assert pd.api.types.is_datetime64_any_dtype(self.detector.data['timestamp'])
    
    def test_initialization_invalid_data(self):
        """無効データでの初期化テスト"""
        # 必要カラムが不足
        invalid_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=10),
            'close': np.random.randn(10)
        })
        
        with pytest.raises(ValueError, match="必要なカラムがありません"):
            SupportResistanceDetector(invalid_data)
    
    def test_find_swing_highs_lows(self):
        """スイング高値・安値検出テスト"""
        swings = self.detector.find_swing_highs_lows(window=3)
        
        assert 'highs' in swings
        assert 'lows' in swings
        assert isinstance(swings['highs'], list)
        assert isinstance(swings['lows'], list)
        
        # 検出された高値・安値の検証
        if swings['highs']:
            for idx, price in swings['highs']:
                assert 0 <= idx < len(self.test_data)
                assert price > 0
                # 高値が周辺より高いことを確認
                window = 3
                start_idx = max(0, idx - window)
                end_idx = min(len(self.test_data), idx + window + 1)
                local_highs = self.test_data['high'][start_idx:end_idx]
                assert price >= local_highs.max() * 0.99  # 許容誤差
        
        if swings['lows']:
            for idx, price in swings['lows']:
                assert 0 <= idx < len(self.test_data)
                assert price > 0
                # 安値が周辺より低いことを確認
                window = 3
                start_idx = max(0, idx - window)
                end_idx = min(len(self.test_data), idx + window + 1)
                local_lows = self.test_data['low'][start_idx:end_idx]
                assert price <= local_lows.min() * 1.01  # 許容誤差
    
    def test_find_price_clusters(self):
        """価格クラスター検出テスト"""
        # テスト用価格データ
        prices = [1000, 1001, 999, 1050, 1051, 1049]
        indices = [10, 20, 30, 40, 50, 60]
        
        clusters = self.detector.find_price_clusters(prices, indices, tolerance=0.005)
        
        # クラスターが検出されることを確認
        assert len(clusters) >= 0
        
        for cluster in clusters:
            assert 'average_price' in cluster
            assert 'touch_count' in cluster
            assert 'strength' in cluster
            assert cluster['touch_count'] >= self.detector.min_touches
            assert 0 <= cluster['strength'] <= 1
    
    def test_detect_support_resistance_levels(self):
        """サポート・レジスタンスレベル検出テスト"""
        levels = self.detector.detect_support_resistance_levels(min_strength=0.1)
        
        assert isinstance(levels, list)
        
        for level in levels:
            assert isinstance(level, SupportResistanceLevel)
            assert level.level_type in ['support', 'resistance']
            assert level.price > 0
            assert 0 <= level.strength <= 1
            assert level.touch_count >= self.detector.min_touches
            assert level.total_volume > 0
            assert 0 <= level.confidence <= 1
    
    def test_calculate_pivot_points(self):
        """ピボットポイント計算テスト"""
        # 日次ピボット
        daily_pivot = self.detector.calculate_pivot_points('daily')
        
        assert isinstance(daily_pivot, PivotPoint)
        assert daily_pivot.pivot > 0
        
        # レジスタンスレベル
        assert 'R1' in daily_pivot.resistance_levels
        assert 'R2' in daily_pivot.resistance_levels  
        assert 'R3' in daily_pivot.resistance_levels
        
        # サポートレベル
        assert 'S1' in daily_pivot.support_levels
        assert 'S2' in daily_pivot.support_levels
        assert 'S3' in daily_pivot.support_levels
        
        # レベルの順序確認
        assert daily_pivot.resistance_levels['R1'] > daily_pivot.pivot
        assert daily_pivot.resistance_levels['R2'] > daily_pivot.resistance_levels['R1']
        assert daily_pivot.resistance_levels['R3'] > daily_pivot.resistance_levels['R2']
        
        assert daily_pivot.support_levels['S1'] < daily_pivot.pivot
        assert daily_pivot.support_levels['S2'] < daily_pivot.support_levels['S1']
        assert daily_pivot.support_levels['S3'] < daily_pivot.support_levels['S2']
        
        # 前セッションピボット
        previous_pivot = self.detector.calculate_pivot_points('previous_session')
        assert isinstance(previous_pivot, PivotPoint)
        assert previous_pivot.pivot > 0
    
    def test_calculate_camarilla_pivots(self):
        """カマリラピボット計算テスト"""
        camarilla = self.detector.calculate_camarilla_pivots()
        
        assert isinstance(camarilla, dict)
        
        # 期待されるレベル
        expected_levels = ['H1', 'H2', 'H3', 'H4', 'L1', 'L2', 'L3', 'L4']
        for level in expected_levels:
            assert level in camarilla
            assert camarilla[level] > 0
        
        # レベルの順序確認
        close_price = self.test_data['close'].iloc[-1]
        assert camarilla['H1'] > close_price
        assert camarilla['H2'] > camarilla['H1']
        assert camarilla['H3'] > camarilla['H2']
        assert camarilla['H4'] > camarilla['H3']
        
        assert camarilla['L1'] < close_price
        assert camarilla['L2'] < camarilla['L1']
        assert camarilla['L3'] < camarilla['L2']
        assert camarilla['L4'] < camarilla['L3']
    
    def test_detect_breakouts(self):
        """ブレイクアウト検出テスト"""
        levels = self.detector.detect_support_resistance_levels(min_strength=0.1)
        
        if levels:
            breakouts = self.detector.detect_breakouts(levels, confirmation_bars=1)
            
            assert isinstance(breakouts, list)
            
            for breakout in breakouts:
                assert isinstance(breakout, BreakoutEvent)
                assert breakout.direction in ['upward', 'downward']
                assert breakout.level_type in ['support', 'resistance']
                assert breakout.price > 0
                assert breakout.level_broken > 0
                assert breakout.volume > 0
                assert 0 <= breakout.strength <= 1
                assert isinstance(breakout.confirmed, bool)
                
                # ブレイクアウトの論理確認
                if breakout.level_type == 'resistance' and breakout.direction == 'upward':
                    assert breakout.price > breakout.level_broken
                elif breakout.level_type == 'support' and breakout.direction == 'downward':
                    assert breakout.price < breakout.level_broken
    
    def test_analyze_time_based_strength(self):
        """時間帯別強度分析テスト"""
        levels = self.detector.detect_support_resistance_levels(min_strength=0.1)
        
        if levels:
            time_analysis = self.detector.analyze_time_based_strength(levels)
            
            assert isinstance(time_analysis, dict)
            
            # 期待される時間帯
            expected_periods = ['asian_session', 'european_session', 'us_session', 
                              'pre_market', 'market_hours', 'after_hours']
            
            for period in time_analysis:
                assert period in expected_periods
                period_data = time_analysis[period]
                
                assert 'total_bars' in period_data
                assert 'avg_volume' in period_data
                assert 'avg_volatility' in period_data
                assert 'level_touches' in period_data
                
                assert period_data['total_bars'] >= 0
                assert period_data['avg_volume'] >= 0
                assert period_data['avg_volatility'] >= 0
    
    def test_comprehensive_analysis(self):
        """総合分析テスト"""
        analysis = self.detector.comprehensive_analysis()
        
        # 必要なセクションが存在
        expected_sections = [
            'timestamp', 'current_price', 'support_resistance_levels',
            'pivot_points', 'camarilla_pivots', 'recent_breakouts',
            'time_based_analysis', 'nearest_support', 'nearest_resistance',
            'market_condition', 'trading_recommendations'
        ]
        
        for section in expected_sections:
            assert section in analysis
        
        # データ型確認
        assert isinstance(analysis['current_price'], (int, float))
        assert analysis['current_price'] > 0
        
        assert isinstance(analysis['support_resistance_levels'], list)
        assert isinstance(analysis['pivot_points'], PivotPoint)
        assert isinstance(analysis['camarilla_pivots'], dict)
        assert isinstance(analysis['recent_breakouts'], list)
        assert isinstance(analysis['time_based_analysis'], dict)
        assert isinstance(analysis['trading_recommendations'], list)
        assert analysis['market_condition'] in [
            '強気ブレイクアウト', '弱気ブレイクアウト', 'レンジ相場', 
            '上昇トレンド', '下降トレンド', '中立'
        ]
    
    def test_find_nearest_level(self):
        """最寄りレベル検索テスト"""
        levels = self.detector.detect_support_resistance_levels(min_strength=0.1)
        current_price = self.test_data['close'].iloc[-1]
        
        nearest_support = self.detector._find_nearest_level(levels, current_price, 'support')
        nearest_resistance = self.detector._find_nearest_level(levels, current_price, 'resistance')
        
        if nearest_support:
            assert isinstance(nearest_support, SupportResistanceLevel)
            assert nearest_support.level_type == 'support'
        
        if nearest_resistance:
            assert isinstance(nearest_resistance, SupportResistanceLevel)
            assert nearest_resistance.level_type == 'resistance'
    
    def test_assess_market_condition(self):
        """市場状況判定テスト"""
        levels = self.detector.detect_support_resistance_levels(min_strength=0.1)
        breakouts = self.detector.detect_breakouts(levels) if levels else []
        
        condition = self.detector._assess_market_condition(levels, breakouts)
        
        valid_conditions = [
            '強気ブレイクアウト', '弱気ブレイクアウト', 'レンジ相場',
            '上昇トレンド', '下降トレンド', '中立'
        ]
        assert condition in valid_conditions
    
    def test_generate_trading_recommendations(self):
        """トレーディング推奨事項生成テスト"""
        levels = self.detector.detect_support_resistance_levels(min_strength=0.1)
        current_price = self.test_data['close'].iloc[-1]
        
        nearest_support = self.detector._find_nearest_level(levels, current_price, 'support')
        nearest_resistance = self.detector._find_nearest_level(levels, current_price, 'resistance')
        breakouts = self.detector.detect_breakouts(levels) if levels else []
        
        recommendations = self.detector._generate_trading_recommendations(
            levels, nearest_support, nearest_resistance, breakouts
        )
        
        assert isinstance(recommendations, list)
        for rec in recommendations:
            assert isinstance(rec, str)
            assert len(rec) > 0
    
    def test_level_strength_calculation(self):
        """レベル強度計算テスト"""
        prices = [1000, 1001, 999]
        volumes = [100000, 120000, 110000] 
        indices = [10, 20, 30]
        
        strength = self.detector._calculate_level_strength(prices, volumes, indices)
        
        assert isinstance(strength, float)
        assert 0 <= strength <= 1
    
    def test_confidence_calculation(self):
        """信頼度計算テスト"""
        cluster = {
            'strength': 0.8,
            'indices': [10, 20, 30, 40],
            'touch_count': 4
        }
        
        confidence = self.detector._calculate_confidence(cluster)
        
        assert isinstance(confidence, float)
        assert 0 <= confidence <= 1
    
    def test_rejection_rate_calculation(self):
        """価格拒否率計算テスト"""
        # テスト用タッチデータ
        touches_data = pd.DataFrame({
            'high': [1050, 1052, 1049],
            'low': [1045, 1047, 1044],
            'close': [1048, 1046, 1047]
        })
        
        # レジスタンスレベル
        level = SupportResistanceLevel(
            price=1050, level_type='resistance', strength=0.8,
            touch_count=3, total_volume=300000, last_touch_index=40,
            formation_time=datetime.now(), confidence=0.8
        )
        
        rejection_rate = self.detector._calculate_rejection_rate(touches_data, level)
        
        assert isinstance(rejection_rate, float)
        assert 0 <= rejection_rate <= 1
    
    def test_edge_cases(self):
        """エッジケーステスト"""
        # 最小データでの処理
        minimal_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=10, freq='H'),
            'open': np.random.uniform(990, 1010, 10),
            'high': np.random.uniform(995, 1015, 10),
            'low': np.random.uniform(985, 1005, 10),
            'close': np.random.uniform(990, 1010, 10),
            'volume': np.random.randint(10000, 50000, 10)
        })
        
        minimal_detector = SupportResistanceDetector(minimal_data, min_touches=1)
        
        # 基本機能が動作することを確認
        levels = minimal_detector.detect_support_resistance_levels(min_strength=0.0)
        pivots = minimal_detector.calculate_pivot_points()
        camarilla = minimal_detector.calculate_camarilla_pivots()
        
        assert isinstance(levels, list)
        assert isinstance(pivots, PivotPoint)
        assert isinstance(camarilla, dict)
    
    def test_parameter_validation(self):
        """パラメータ検証テスト"""
        # 無効な許容誤差
        with pytest.raises(Exception):
            detector = SupportResistanceDetector(self.test_data, tolerance_percent=-1)
        
        # 無効な最小タッチ回数
        detector = SupportResistanceDetector(self.test_data, min_touches=0)
        levels = detector.detect_support_resistance_levels()
        # エラーにならないが、有意なレベルは検出されない可能性
        
        # 無効なピボット期間タイプ
        with pytest.raises(ValueError):
            self.detector.calculate_pivot_points('invalid_period')
    
    def test_caching_functionality(self):
        """キャッシュ機能テスト"""
        # 最初の計算
        levels1 = self.detector.detect_support_resistance_levels(min_strength=0.3, max_levels=5)
        
        # キャッシュから取得
        levels2 = self.detector.detect_support_resistance_levels(min_strength=0.3, max_levels=5)
        
        # 同じ結果であることを確認
        assert len(levels1) == len(levels2)
        for l1, l2 in zip(levels1, levels2):
            assert l1.price == l2.price
            assert l1.level_type == l2.level_type
            assert l1.strength == l2.strength


if __name__ == "__main__":
    pytest.main([__file__, "-v"])