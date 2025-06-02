"""
単体テスト固有のpytest設定とフィクスチャ
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


@pytest.fixture
def technical_indicators(sample_ohlcv_data):
    """TechnicalIndicatorsインスタンスを提供"""
    from src.technical_analysis.indicators import TechnicalIndicators
    return TechnicalIndicators(sample_ohlcv_data)


@pytest.fixture
def signal_generator():
    """SignalGeneratorインスタンスを提供"""
    from src.technical_analysis.signal_generator import SignalGenerator
    return SignalGenerator()


@pytest.fixture
def risk_manager():
    """RiskManagerインスタンスを提供"""
    from src.risk_management.risk_manager import RiskManager
    return RiskManager()


@pytest.fixture
def market_environment():
    """MarketEnvironmentインスタンスを提供"""
    from src.technical_analysis.market_environment import MarketEnvironment
    return MarketEnvironment()


@pytest.fixture
def mock_yfinance_data():
    """yfinanceのモックデータを提供"""
    return {
        'Open': [100.0, 102.0, 101.0, 103.0, 105.0],
        'High': [105.0, 107.0, 106.0, 108.0, 110.0],
        'Low': [98.0, 100.0, 99.0, 101.0, 103.0],
        'Close': [102.0, 101.0, 103.0, 105.0, 107.0],
        'Volume': [1000, 1100, 1200, 1050, 1300]
    }