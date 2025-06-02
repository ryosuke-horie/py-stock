"""
インテリジェントアラートコンポーネントのテスト
TechnicalIndicators初期化エラーの修正をテスト
"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))


class TestIntelligentAlertComponent:
    """IntelligentAlertComponentのテスト"""
    
    @patch('dashboard.components.intelligent_alerts.st')
    @patch('dashboard.components.intelligent_alerts.StockDataCollector')
    @patch('dashboard.components.intelligent_alerts.MarketEnvironmentAnalyzer')
    @patch('dashboard.components.intelligent_alerts.IntelligentAlertSystem')
    def test_component_initialization_without_error(self, mock_alert_system, mock_market_analyzer, mock_data_collector, mock_st):
        """コンポーネントがエラーなく初期化されることをテスト"""
        from dashboard.components.intelligent_alerts import IntelligentAlertComponent
        
        # モックの設定
        mock_st.session_state = {}
        mock_data_collector.return_value = Mock()
        mock_market_analyzer.return_value = Mock()
        mock_alert_system.return_value = Mock()
        
        # 初期化時にエラーが発生しないことを確認
        try:
            component = IntelligentAlertComponent()
            assert component is not None
            assert component.indicators is None  # dataなしでは初期化されない
            assert component.data_collector is not None
            assert component.market_analyzer is not None
        except TypeError as e:
            # TechnicalIndicatorsの初期化エラーが発生しないことを確認
            assert "missing 1 required positional argument: 'data'" not in str(e)
            pytest.fail(f"Unexpected initialization error: {e}")
    
    @patch('dashboard.components.intelligent_alerts.st')
    @patch('dashboard.components.intelligent_alerts.StockDataCollector')
    @patch('dashboard.components.intelligent_alerts.MarketEnvironmentAnalyzer')
    @patch('dashboard.components.intelligent_alerts.IntelligentAlertSystem')
    def test_technical_indicators_not_initialized_without_data(self, mock_alert_system, mock_market_analyzer, mock_data_collector, mock_st):
        """データなしではTechnicalIndicatorsが初期化されないことをテスト"""
        from dashboard.components.intelligent_alerts import IntelligentAlertComponent
        
        # モックの設定
        mock_st.session_state = {}
        mock_data_collector.return_value = Mock()
        mock_market_analyzer.return_value = Mock()
        mock_alert_system.return_value = Mock()
        
        component = IntelligentAlertComponent()
        
        # TechnicalIndicatorsがNoneであることを確認
        assert component.indicators is None
    
    @patch('dashboard.components.intelligent_alerts.st')
    def test_component_with_missing_imports(self, mock_st):
        """必要なモジュールのインポートに失敗した場合の処理をテスト"""
        # モックの設定
        mock_st.session_state = {}
        
        # インポートエラーをシミュレート
        with patch('dashboard.components.intelligent_alerts.IntelligentAlertSystem', None):
            from dashboard.components.intelligent_alerts import IntelligentAlertComponent
            
            component = IntelligentAlertComponent()
            assert component.data_collector is None
            assert component.indicators is None
            assert component.market_analyzer is None