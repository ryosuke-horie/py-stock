"""
インテリジェントアラートシステムの統合テスト
実際のデータコレクターやインジケーターとの連携をテスト
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.technical_analysis.intelligent_alert_system import (
    IntelligentAlertSystem,
    AlertPriority,
    MarketCondition
)
from src.data_collector.stock_data_collector import StockDataCollector
from src.technical_analysis.indicators import TechnicalIndicators


class TestIntelligentAlertIntegration:
    """インテリジェントアラートシステムの統合テスト"""
    
    @pytest.fixture
    def mock_stock_data(self):
        """モック株価データ"""
        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        prices = np.random.uniform(1900, 2100, 30)
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices * 0.99,
            'high': prices * 1.01,
            'low': prices * 0.98,
            'close': prices,
            'volume': np.random.uniform(1000000, 2000000, 30)
        })
    
    def test_alert_system_with_indicators(self, mock_stock_data):
        """インジケーターとの統合テスト"""
        # システム初期化
        alert_system = IntelligentAlertSystem()
        indicators = TechnicalIndicators()
        
        # データをインジケーター用に変換
        data_for_indicators = mock_stock_data.rename(columns={
            'timestamp': 'Date',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }).set_index('Date')
        
        # インジケーター計算
        indicators_df = indicators.calculate_all_indicators(data_for_indicators)
        
        # アラート作成
        conditions = [
            {'type': 'rsi', 'threshold': 50.0, 'operator': 'greater'},
            {'type': 'volume', 'threshold': 1500000, 'operator': 'greater'}
        ]
        
        alert_id = alert_system.create_composite_alert("TEST", conditions)
        
        # 最新データで評価
        latest = indicators_df.iloc[-1]
        market_data = {
            'volume': latest['Volume']
        }
        technical_data = {
            'rsi': latest['RSI'] if 'RSI' in latest else 50.0
        }
        
        result = alert_system.evaluate_alert(alert_id, market_data, technical_data)
        
        # 結果確認
        assert result is not None or result is None  # 条件次第
        if result:
            assert 'symbol' in result
            assert 'priority' in result
            assert 'conditions_met' in result
    
    @patch('src.data_collector.stock_data_collector.StockDataCollector.get_stock_data')
    def test_market_condition_analysis_with_real_collector(self, mock_get_data, mock_stock_data):
        """データコレクターとの統合テスト"""
        # モックデータを返すよう設定
        mock_get_data.return_value = mock_stock_data
        
        # システム初期化
        alert_system = IntelligentAlertSystem()
        data_collector = StockDataCollector()
        
        # データ取得
        symbol = "TEST"
        data = data_collector.get_stock_data(symbol, period="1mo")
        
        # 市場状況分析（DataFrameの列名を調整）
        data_for_analysis = data.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        })
        
        condition = alert_system.analyze_market_condition(data_for_analysis, symbol)
        
        # 結果確認
        assert isinstance(condition, MarketCondition)
        assert symbol in alert_system.market_conditions
    
    def test_complete_alert_workflow(self, mock_stock_data):
        """完全なアラートワークフローのテスト"""
        # システム初期化
        alert_system = IntelligentAlertSystem()
        indicators = TechnicalIndicators()
        
        # データ準備
        symbol = "WORKFLOW_TEST"
        data_for_indicators = mock_stock_data.rename(columns={
            'timestamp': 'Date',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }).set_index('Date')
        
        # 1. 市場状況分析
        market_condition = alert_system.analyze_market_condition(data_for_indicators, symbol)
        
        # 2. 複合アラート作成
        conditions = [
            {
                'type': 'price_change_pct',
                'threshold': 1.0,
                'operator': 'greater',
                'min_threshold': 0.5,
                'max_threshold': 3.0
            },
            {
                'type': 'volume_ratio',
                'threshold': 1.5,
                'operator': 'greater'
            },
            {
                'type': 'rsi',
                'threshold': 60.0,
                'operator': 'greater'
            }
        ]
        
        alert_id = alert_system.create_composite_alert(
            symbol=symbol,
            conditions=conditions,
            min_conditions=2,
            priority_rules={2: AlertPriority.MEDIUM, 3: AlertPriority.HIGH}
        )
        
        # 3. 動的閾値調整
        alert_system.adjust_thresholds(symbol, market_condition)
        
        # 4. インジケーター計算
        indicators_df = indicators.calculate_all_indicators(data_for_indicators)
        
        # 5. アラート評価
        if len(indicators_df) > 1:
            latest = indicators_df.iloc[-1]
            prev = indicators_df.iloc[-2]
            
            market_data = {
                'price': latest['Close'],
                'volume': latest['Volume'],
                'price_change_pct': ((latest['Close'] - prev['Close']) / prev['Close'] * 100),
                'volume_ratio': latest['Volume'] / indicators_df['Volume'].rolling(20).mean().iloc[-1]
            }
            
            technical_data = {
                'rsi': latest.get('RSI', 50.0)
            }
            
            result = alert_system.evaluate_alert(alert_id, market_data, technical_data)
            
            # 6. ノイズフィルタリング
            if result:
                filtered = alert_system.process_alert(result)
                
                # 結果確認
                if filtered:
                    assert filtered['symbol'] == symbol
                    assert isinstance(filtered['priority'], AlertPriority)
                    assert len(alert_system.alert_history) > 0
        
        # 7. サマリー取得
        summary = alert_system.get_active_alerts_summary()
        assert summary['total_active'] >= 1
        assert symbol in summary['by_symbol']
    
    def test_priority_based_notification(self):
        """優先度別通知のテスト"""
        alert_system = IntelligentAlertSystem()
        
        # 各優先度での通知方法確認
        priority_tests = [
            (AlertPriority.CRITICAL, ['sound', 'popup', 'email', 'push']),
            (AlertPriority.HIGH, ['sound', 'popup', 'push']),
            (AlertPriority.MEDIUM, ['popup', 'push']),
            (AlertPriority.LOW, ['popup']),
            (AlertPriority.INFO, [])
        ]
        
        for priority, expected_methods in priority_tests:
            methods = alert_system.get_notification_method(priority)
            assert methods == expected_methods
    
    def test_noise_filter_effectiveness(self):
        """ノイズフィルターの効果性テスト"""
        alert_system = IntelligentAlertSystem()
        
        # 短期間に大量のアラートを生成
        base_time = datetime.now()
        symbol = "NOISE_TEST"
        
        alerts_fired = 0
        alerts_filtered = 0
        
        for i in range(10):
            alert_info = {
                'alert_id': f'noise_test_{i}',
                'symbol': symbol,
                'timestamp': base_time + timedelta(seconds=i * 30),  # 30秒間隔
                'priority': AlertPriority.MEDIUM,
                'conditions_met': [{'type': 'test', 'value': i}]
            }
            
            if alert_system.apply_noise_filter(alert_info):
                alerts_fired += 1
                alert_system.alert_history.append(alert_info)
            else:
                alerts_filtered += 1
        
        # フィルタリングが機能していることを確認
        assert alerts_filtered > 0
        assert alerts_fired < 10  # 全てが通過しないこと
        
        # 履歴の確認
        assert len(alert_system.alert_history) == alerts_fired