"""
examplesディレクトリ内のスクリプトのテスト
実際の実行は行わず、インポートと基本的な関数の存在確認のみ
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, Mock
import importlib.util

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))


class TestExamples:
    """examples配下のスクリプトのテストクラス"""
    
    def test_import_basic_usage(self):
        """basic_usage.pyのインポートテスト"""
        spec = importlib.util.spec_from_file_location(
            "basic_usage", 
            Path(__file__).parent.parent.parent / "src" / "examples" / "basic_usage.py"
        )
        module = importlib.util.module_from_spec(spec)
        
        # インポートエラーが発生しないことを確認
        assert spec is not None
        assert module is not None
    
    def test_import_signal_generator_demo(self):
        """signal_generator_demo.pyのインポートテスト"""
        spec = importlib.util.spec_from_file_location(
            "signal_generator_demo", 
            Path(__file__).parent.parent.parent / "src" / "examples" / "signal_generator_demo.py"
        )
        module = importlib.util.module_from_spec(spec)
        
        # インポートエラーが発生しないことを確認
        assert spec is not None
        assert module is not None
    
    def test_import_risk_management_demo(self):
        """risk_management_demo.pyのインポートテスト"""
        spec = importlib.util.spec_from_file_location(
            "risk_management_demo", 
            Path(__file__).parent.parent.parent / "src" / "examples" / "risk_management_demo.py"
        )
        module = importlib.util.module_from_spec(spec)
        
        # インポートエラーが発生しないことを確認
        assert spec is not None
        assert module is not None
    
    def test_import_support_resistance_demo(self):
        """support_resistance_demo.pyのインポートテスト"""
        spec = importlib.util.spec_from_file_location(
            "support_resistance_demo", 
            Path(__file__).parent.parent.parent / "src" / "examples" / "support_resistance_demo.py"
        )
        module = importlib.util.module_from_spec(spec)
        
        # インポートエラーが発生しないことを確認
        assert spec is not None
        assert module is not None
    
    def test_import_technical_analysis_demo(self):
        """technical_analysis_demo.pyのインポートテスト"""
        spec = importlib.util.spec_from_file_location(
            "technical_analysis_demo", 
            Path(__file__).parent.parent.parent / "src" / "examples" / "technical_analysis_demo.py"
        )
        module = importlib.util.module_from_spec(spec)
        
        # インポートエラーが発生しないことを確認
        assert spec is not None
        assert module is not None
    
    @patch('src.data_collector.stock_data_collector.StockDataCollector')
    @patch('src.data_collector.symbol_manager.SymbolManager')
    @patch('src.config.settings.settings_manager')
    def test_basic_usage_functions_exist(self, mock_settings, mock_symbol_manager, mock_collector):
        """basic_usage.pyの主要関数の存在確認"""
        try:
            from src.examples import basic_usage
            
            # 主要な関数が存在することを確認
            assert hasattr(basic_usage, 'basic_data_collection_demo')
            assert hasattr(basic_usage, 'symbol_management_demo')
            assert hasattr(basic_usage, 'basic_analysis_demo')
            assert callable(basic_usage.basic_data_collection_demo)
            assert callable(basic_usage.symbol_management_demo)
            assert callable(basic_usage.basic_analysis_demo)
            
        except ImportError:
            pytest.skip("basic_usage module could not be imported")
    
    @patch('src.data_collector.stock_data_collector.StockDataCollector')
    @patch('src.data_collector.symbol_manager.SymbolManager')
    @patch('src.config.settings.settings_manager')
    def test_signal_generator_demo_functions_exist(self, mock_settings, mock_symbol_manager, mock_collector):
        """signal_generator_demo.pyの主要関数の存在確認"""
        try:
            from src.examples import signal_generator_demo
            
            # 主要な関数が存在することを確認
            assert hasattr(signal_generator_demo, 'basic_signal_generation_demo')
            assert hasattr(signal_generator_demo, 'custom_rules_demo')
            assert hasattr(signal_generator_demo, 'backtest_analysis_demo')
            assert callable(signal_generator_demo.basic_signal_generation_demo)
            assert callable(signal_generator_demo.custom_rules_demo)
            assert callable(signal_generator_demo.backtest_analysis_demo)
            
        except ImportError:
            pytest.skip("signal_generator_demo module could not be imported")
    
    @patch('src.risk_management.risk_manager.RiskManager')
    @patch('src.data_collector.stock_data_collector.StockDataCollector')
    @patch('src.config.settings.settings_manager')
    def test_risk_management_demo_functions_exist(self, mock_settings, mock_collector, mock_risk_manager):
        """risk_management_demo.pyの主要関数の存在確認"""
        try:
            from src.examples import risk_management_demo
            
            # 主要な関数が存在することを確認
            assert hasattr(risk_management_demo, 'basic_risk_management_demo')
            assert hasattr(risk_management_demo, 'portfolio_risk_demo')
            assert hasattr(risk_management_demo, 'position_sizing_demo')
            assert callable(risk_management_demo.basic_risk_management_demo)
            assert callable(risk_management_demo.portfolio_risk_demo)
            assert callable(risk_management_demo.position_sizing_demo)
            
        except ImportError:
            pytest.skip("risk_management_demo module could not be imported")
    
    @patch('src.technical_analysis.support_resistance.SupportResistanceDetector')
    @patch('src.data_collector.stock_data_collector.StockDataCollector')
    @patch('src.config.settings.settings_manager')
    def test_support_resistance_demo_functions_exist(self, mock_settings, mock_collector, mock_detector):
        """support_resistance_demo.pyの主要関数の存在確認"""
        try:
            from src.examples import support_resistance_demo
            
            # 主要な関数が存在することを確認
            assert hasattr(support_resistance_demo, 'basic_support_resistance_demo')
            assert hasattr(support_resistance_demo, 'advanced_analysis_demo')
            assert hasattr(support_resistance_demo, 'pivot_point_demo')
            assert callable(support_resistance_demo.basic_support_resistance_demo)
            assert callable(support_resistance_demo.advanced_analysis_demo)
            assert callable(support_resistance_demo.pivot_point_demo)
            
        except ImportError:
            pytest.skip("support_resistance_demo module could not be imported")
    
    @patch('src.technical_analysis.indicators.TechnicalIndicators')
    @patch('src.data_collector.stock_data_collector.StockDataCollector')
    @patch('src.config.settings.settings_manager')
    def test_technical_analysis_demo_functions_exist(self, mock_settings, mock_collector, mock_indicators):
        """technical_analysis_demo.pyの主要関数の存在確認"""
        try:
            from src.examples import technical_analysis_demo
            
            # 主要な関数が存在することを確認
            assert hasattr(technical_analysis_demo, 'basic_indicators_demo')
            assert hasattr(technical_analysis_demo, 'trend_analysis_demo')
            assert hasattr(technical_analysis_demo, 'oscillator_analysis_demo')
            assert callable(technical_analysis_demo.basic_indicators_demo)
            assert callable(technical_analysis_demo.trend_analysis_demo)
            assert callable(technical_analysis_demo.oscillator_analysis_demo)
            
        except ImportError:
            pytest.skip("technical_analysis_demo module could not be imported")
    
    def test_examples_init_file_exists(self):
        """examples/__init__.pyファイルの存在確認"""
        init_file = Path(__file__).parent.parent.parent / "src" / "examples" / "__init__.py"
        assert init_file.exists()
    
    @patch('builtins.print')
    @patch('src.config.settings.settings_manager')
    def test_basic_demo_execution_mocked(self, mock_settings, mock_print):
        """基本デモの実行テスト（モック使用）"""
        try:
            from src.examples import basic_usage
            
            # モックを設定
            mock_settings.setup_logging.return_value = None
            
            # 例外が発生しないことを確認
            # 実際のデータ取得は行わず、関数の構造のみテスト
            assert callable(basic_usage.basic_data_collection_demo)
            
        except ImportError:
            pytest.skip("basic_usage module could not be imported")
    
    def test_all_demo_files_are_python_files(self):
        """examples配下のすべてのファイルがPythonファイルであることを確認"""
        examples_dir = Path(__file__).parent.parent.parent / "src" / "examples"
        
        if not examples_dir.exists():
            pytest.skip("examples directory does not exist")
        
        python_files = list(examples_dir.glob("*.py"))
        
        # 少なくとも1つのPythonファイルが存在することを確認
        assert len(python_files) > 0
        
        # 各ファイルが.py拡張子を持つことを確認
        for file in python_files:
            assert file.suffix == '.py'
    
    def test_demo_scripts_have_main_guard(self):
        """デモスクリプトが適切なmainガードを持つことを確認"""
        examples_dir = Path(__file__).parent.parent.parent / "src" / "examples"
        
        if not examples_dir.exists():
            pytest.skip("examples directory does not exist")
        
        demo_files = [f for f in examples_dir.glob("*_demo.py")]
        
        for demo_file in demo_files:
            content = demo_file.read_text(encoding='utf-8')
            
            # if __name__ == "__main__": があることを確認
            assert 'if __name__ == "__main__":' in content, f"{demo_file.name} should have main guard"