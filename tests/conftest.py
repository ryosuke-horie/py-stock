"""
プロジェクト全体の共通pytest設定とフィクスチャ
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import sys

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def test_data_dir():
    """テストデータディレクトリへのパスを提供"""
    return Path(__file__).parent / "data"


@pytest.fixture
def temp_workspace(tmp_path):
    """一時的な作業ディレクトリを提供"""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def sample_stock_data():
    """サンプルの株価データを提供するフィクスチャ"""
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
    
    # 価格データ生成（リアルな株価パターン）
    base_price = 1000
    returns = np.random.normal(0.001, 0.02, 100)  # 日次リターン
    
    prices = [base_price]
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # OHLCV生成
    closes = np.array(prices)
    opens = closes * (1 + np.random.normal(0, 0.005, 100))
    highs = np.maximum(opens, closes) * (1 + np.random.uniform(0, 0.01, 100))
    lows = np.minimum(opens, closes) * (1 - np.random.uniform(0, 0.01, 100))
    volumes = np.random.randint(100000, 1000000, 100)
    
    return pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    })


@pytest.fixture
def empty_stock_data():
    """空の株価データフレームを提供するフィクスチャ"""
    return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])


@pytest.fixture
def minimal_stock_data():
    """最小限の株価データを提供するフィクスチャ"""
    dates = pd.date_range(start='2024-01-01', periods=5, freq='D')
    return pd.DataFrame({
        'timestamp': dates,
        'open': [100, 102, 101, 103, 105],
        'high': [105, 107, 106, 108, 110],
        'low': [98, 100, 99, 101, 103],
        'close': [102, 101, 103, 105, 107],
        'volume': [1000, 1100, 1200, 1050, 1300]
    })


# カバレッジ測定のためのマーカー設定
def pytest_configure(config):
    """pytest設定の初期化"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )