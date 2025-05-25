"""
risk_management/__init__.pyのテスト
"""

import pytest


def test_import_risk_management():
    """リスク管理モジュールのインポートテスト"""
    from src.risk_management import RiskManager, RiskParameters, Position, StopLossType, PositionSide
    
    # インポートが成功することを確認
    assert RiskManager is not None
    assert RiskParameters is not None
    assert Position is not None
    assert StopLossType is not None
    assert PositionSide is not None


def test_risk_management_all():
    """__all__の内容をテスト"""
    import src.risk_management as rm
    
    expected_all = ["RiskManager", "RiskParameters", "Position", "StopLossType", "PositionSide"]
    assert rm.__all__ == expected_all