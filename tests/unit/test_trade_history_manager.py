"""
投資履歴記録・管理機能のユニットテスト
"""

import pytest
import tempfile
import os
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import patch
import pandas as pd

from src.performance_tracking.trade_history_manager import (
    TradeHistoryManager, TradeRecord, TradeDirection, TradeStatus
)


class TestTradeRecord:
    """TradeRecordクラスのテスト"""
    
    def test_trade_record_creation(self):
        """TradeRecord作成テスト"""
        trade = TradeRecord(
            trade_id="TEST_001",
            symbol="7203.T",
            direction=TradeDirection.LONG,
            entry_time=datetime(2024, 1, 15, 9, 0),
            entry_price=1000.0,
            quantity=100
        )
        
        assert trade.trade_id == "TEST_001"
        assert trade.symbol == "7203.T"
        assert trade.direction == TradeDirection.LONG
        assert trade.status == TradeStatus.OPEN
        assert trade.realized_pnl is None
    
    def test_trade_record_to_dict(self):
        """TradeRecord辞書変換テスト"""
        trade = TradeRecord(
            trade_id="TEST_001",
            symbol="7203.T",
            direction=TradeDirection.LONG,
            entry_time=datetime(2024, 1, 15, 9, 0),
            entry_price=1000.0,
            quantity=100,
            tags=["tech", "automotive"]
        )
        
        trade_dict = trade.to_dict()
        
        assert isinstance(trade_dict, dict)
        assert trade_dict["trade_id"] == "TEST_001"
        assert trade_dict["direction"] == "long"
        assert trade_dict["status"] == "open"
        assert "2024-01-15T09:00:00" in trade_dict["entry_time"]
        assert '"tech"' in trade_dict["tags"]
    
    def test_trade_record_from_dict(self):
        """TradeRecord辞書から復元テスト"""
        data = {
            "trade_id": "TEST_001",
            "symbol": "7203.T",
            "direction": "long",
            "entry_time": "2024-01-15T09:00:00",
            "entry_price": 1000.0,
            "quantity": 100,
            "status": "open",
            "tags": '["tech", "automotive"]'
        }
        
        trade = TradeRecord.from_dict(data)
        
        assert trade.trade_id == "TEST_001"
        assert trade.direction == TradeDirection.LONG
        assert trade.status == TradeStatus.OPEN
        assert isinstance(trade.entry_time, datetime)
        assert trade.tags == ["tech", "automotive"]
    
    def test_trade_record_from_dict_null_tags(self):
        """TradeRecord辞書から復元テスト（tagsがnull）"""
        data = {
            "trade_id": "TEST_001",
            "symbol": "7203.T",
            "direction": "long",
            "entry_time": "2024-01-15T09:00:00",
            "entry_price": 1000.0,
            "quantity": 100,
            "status": "open",
            "tags": "null"
        }
        
        trade = TradeRecord.from_dict(data)
        assert trade.tags is None


class TestTradeHistoryManager:
    """TradeHistoryManagerクラスのテスト"""
    
    @pytest.fixture
    def temp_db_path(self):
        """テンポラリDBファイルパス"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            yield f.name
        os.unlink(f.name)
    
    @pytest.fixture
    def manager(self, temp_db_path):
        """テスト用TradeHistoryManager"""
        return TradeHistoryManager(temp_db_path)
    
    @pytest.fixture
    def sample_trade(self):
        """サンプル取引"""
        return TradeRecord(
            trade_id="TEST_001",
            symbol="7203.T",
            direction=TradeDirection.LONG,
            entry_time=datetime(2024, 1, 15, 9, 0),
            entry_price=1000.0,
            quantity=100,
            strategy_name="Test Strategy",
            signal_strength=80.0,
            market_condition="Bull Market"
        )
    
    def test_initialization(self, manager, temp_db_path):
        """初期化テスト"""
        assert manager.db_path.name == os.path.basename(temp_db_path)
        assert os.path.exists(temp_db_path)
        
        # データベーステーブルが作成されていることを確認
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='trade_history'"
            )
            assert cursor.fetchone() is not None
    
    def test_add_trade_success(self, manager, sample_trade):
        """取引追加成功テスト"""
        success = manager.add_trade(sample_trade)
        assert success is True
        
        # データベースに保存されていることを確認
        retrieved_trade = manager.get_trade(sample_trade.trade_id)
        assert retrieved_trade is not None
        assert retrieved_trade.trade_id == sample_trade.trade_id
        assert retrieved_trade.symbol == sample_trade.symbol
        assert retrieved_trade.direction == sample_trade.direction
    
    def test_add_trade_replace_existing(self, manager, sample_trade):
        """既存取引の置き換えテスト"""
        # 最初の追加
        manager.add_trade(sample_trade)
        
        # 同じIDで異なるデータを追加
        sample_trade.entry_price = 1100.0
        success = manager.add_trade(sample_trade)
        assert success is True
        
        # 更新されていることを確認
        retrieved_trade = manager.get_trade(sample_trade.trade_id)
        assert retrieved_trade.entry_price == 1100.0
    
    def test_get_trade_not_found(self, manager):
        """存在しない取引取得テスト"""
        trade = manager.get_trade("NONEXISTENT")
        assert trade is None
    
    def test_update_trade_success(self, manager, sample_trade):
        """取引更新成功テスト"""
        # 取引を追加
        manager.add_trade(sample_trade)
        
        # 更新
        sample_trade.notes = "Updated notes"
        sample_trade.market_condition = "Bear Market"
        success = manager.update_trade(sample_trade)
        assert success is True
        
        # 更新されていることを確認
        retrieved_trade = manager.get_trade(sample_trade.trade_id)
        assert retrieved_trade.notes == "Updated notes"
        assert retrieved_trade.market_condition == "Bear Market"
    
    def test_close_trade_success(self, manager, sample_trade):
        """取引決済成功テスト"""
        # オープン取引を追加
        manager.add_trade(sample_trade)
        
        # 決済
        success = manager.close_trade(
            trade_id=sample_trade.trade_id,
            exit_price=1200.0,
            exit_reason="Take Profit",
            exit_commission=100.0
        )
        assert success is True
        
        # 決済情報が正しく設定されていることを確認
        closed_trade = manager.get_trade(sample_trade.trade_id)
        assert closed_trade.status == TradeStatus.CLOSED
        assert closed_trade.exit_price == 1200.0
        assert closed_trade.exit_reason == "Take Profit"
        assert closed_trade.exit_commission == 100.0
        assert abs(closed_trade.realized_pnl - 19900.0) < 0.01  # (1200-1000)*100 - 100
        assert abs(closed_trade.realized_pnl_pct - 19.9) < 0.01  # 19900/(1000*100)*100
    
    def test_close_trade_short_position(self, manager):
        """ショートポジション決済テスト"""
        short_trade = TradeRecord(
            trade_id="SHORT_001",
            symbol="7203.T",
            direction=TradeDirection.SHORT,
            entry_time=datetime(2024, 1, 15, 9, 0),
            entry_price=1000.0,
            quantity=100
        )
        manager.add_trade(short_trade)
        
        # 利益決済（価格下落）
        success = manager.close_trade("SHORT_001", 900.0, "Take Profit")
        assert success is True
        
        closed_trade = manager.get_trade("SHORT_001")
        assert abs(closed_trade.realized_pnl - 10000.0) < 0.01  # (1000-900)*100
    
    def test_close_trade_not_found(self, manager):
        """存在しない取引の決済テスト"""
        success = manager.close_trade("NONEXISTENT", 1000.0, "Test")
        assert success is False
    
    def test_close_already_closed_trade(self, manager, sample_trade):
        """既に決済済みの取引の決済テスト"""
        manager.add_trade(sample_trade)
        
        # 最初の決済
        manager.close_trade(sample_trade.trade_id, 1100.0, "First close")
        
        # 二回目の決済（失敗するべき）
        success = manager.close_trade(sample_trade.trade_id, 1200.0, "Second close")
        assert success is False
    
    def test_get_trades_basic(self, manager):
        """基本的な取引リスト取得テスト"""
        # 複数の取引を追加
        trades = []
        for i in range(3):
            trade = TradeRecord(
                trade_id=f"TEST_{i:03d}",
                symbol=f"TEST{i}",
                direction=TradeDirection.LONG,
                entry_time=datetime(2024, 1, 15 + i, 9, 0),
                entry_price=1000.0 + i * 100,
                quantity=100
            )
            manager.add_trade(trade)
            trades.append(trade)
        
        # 全取引取得
        all_trades = manager.get_trades()
        assert len(all_trades) == 3
        
        # 降順ソートされていることを確認
        assert all_trades[0].entry_time >= all_trades[1].entry_time
    
    def test_get_trades_with_filters(self, manager):
        """フィルタ付き取引リスト取得テスト"""
        # 異なる銘柄・ステータスの取引を追加
        trades_data = [
            ("AAPL", TradeStatus.OPEN),
            ("AAPL", TradeStatus.CLOSED),
            ("GOOGL", TradeStatus.OPEN),
            ("GOOGL", TradeStatus.CLOSED),
        ]
        
        for i, (symbol, status) in enumerate(trades_data):
            trade = TradeRecord(
                trade_id=f"TEST_{i:03d}",
                symbol=symbol,
                direction=TradeDirection.LONG,
                entry_time=datetime(2024, 1, 15 + i, 9, 0),
                entry_price=1000.0,
                quantity=100,
                status=status
            )
            manager.add_trade(trade)
        
        # 銘柄フィルタ
        aapl_trades = manager.get_trades(symbol="AAPL")
        assert len(aapl_trades) == 2
        assert all(t.symbol == "AAPL" for t in aapl_trades)
        
        # ステータスフィルタ
        open_trades = manager.get_trades(status=TradeStatus.OPEN)
        assert len(open_trades) == 2
        assert all(t.status == TradeStatus.OPEN for t in open_trades)
        
        # 組み合わせフィルタ
        aapl_open = manager.get_trades(symbol="AAPL", status=TradeStatus.OPEN)
        assert len(aapl_open) == 1
        assert aapl_open[0].symbol == "AAPL"
        assert aapl_open[0].status == TradeStatus.OPEN
    
    def test_get_trades_with_date_filter(self, manager):
        """日付フィルタ付き取引取得テスト"""
        base_date = datetime(2024, 1, 15, 9, 0)
        
        # 異なる日付の取引を追加
        for i in range(5):
            trade = TradeRecord(
                trade_id=f"TEST_{i:03d}",
                symbol="TEST",
                direction=TradeDirection.LONG,
                entry_time=base_date + timedelta(days=i),
                entry_price=1000.0,
                quantity=100
            )
            manager.add_trade(trade)
        
        # 日付範囲フィルタ
        start_date = base_date + timedelta(days=1)
        end_date = base_date + timedelta(days=3)
        
        filtered_trades = manager.get_trades(start_date=start_date, end_date=end_date)
        assert len(filtered_trades) == 3  # 1, 2, 3日目
    
    def test_get_trades_with_limit(self, manager):
        """制限付き取引取得テスト"""
        # 多数の取引を追加
        for i in range(10):
            trade = TradeRecord(
                trade_id=f"TEST_{i:03d}",
                symbol="TEST",
                direction=TradeDirection.LONG,
                entry_time=datetime(2024, 1, 15 + i, 9, 0),
                entry_price=1000.0,
                quantity=100
            )
            manager.add_trade(trade)
        
        # 制限付き取得
        limited_trades = manager.get_trades(limit=5)
        assert len(limited_trades) == 5
    
    def test_get_open_trades(self, manager):
        """オープン取引取得テスト"""
        # オープンとクローズの取引を混ぜて追加
        for i in range(4):
            trade = TradeRecord(
                trade_id=f"TEST_{i:03d}",
                symbol="TEST",
                direction=TradeDirection.LONG,
                entry_time=datetime(2024, 1, 15 + i, 9, 0),
                entry_price=1000.0,
                quantity=100,
                status=TradeStatus.OPEN if i % 2 == 0 else TradeStatus.CLOSED
            )
            manager.add_trade(trade)
        
        open_trades = manager.get_open_trades()
        assert len(open_trades) == 2
        assert all(t.status == TradeStatus.OPEN for t in open_trades)
    
    def test_get_closed_trades(self, manager):
        """クローズ取引取得テスト"""
        # オープンとクローズの取引を混ぜて追加
        for i in range(4):
            trade = TradeRecord(
                trade_id=f"TEST_{i:03d}",
                symbol="TEST",
                direction=TradeDirection.LONG,
                entry_time=datetime(2024, 1, 15 + i, 9, 0),
                entry_price=1000.0,
                quantity=100,
                status=TradeStatus.OPEN if i % 2 == 0 else TradeStatus.CLOSED
            )
            manager.add_trade(trade)
        
        closed_trades = manager.get_closed_trades()
        assert len(closed_trades) == 2
        assert all(t.status == TradeStatus.CLOSED for t in closed_trades)
    
    def test_get_trades_dataframe(self, manager):
        """DataFrame形式での取引取得テスト"""
        # 取引を追加
        trade = TradeRecord(
            trade_id="TEST_001",
            symbol="7203.T",
            direction=TradeDirection.LONG,
            entry_time=datetime(2024, 1, 15, 9, 0),
            entry_price=1000.0,
            quantity=100
        )
        manager.add_trade(trade)
        
        df = manager.get_trades_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert "trade_id" in df.columns
        assert "symbol" in df.columns
        assert pd.api.types.is_datetime64_any_dtype(df["entry_time"])
    
    def test_get_trades_dataframe_empty(self, manager):
        """空のDataFrame取得テスト"""
        df = manager.get_trades_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
    
    def test_calculate_basic_stats_no_data(self, manager):
        """統計計算（データなし）テスト"""
        stats = manager.calculate_basic_stats()
        assert stats == {}
    
    def test_calculate_basic_stats_with_data(self, manager):
        """統計計算（データあり）テスト"""
        # 勝ち取引と負け取引を追加
        win_trade = TradeRecord(
            trade_id="WIN_001",
            symbol="TEST",
            direction=TradeDirection.LONG,
            entry_time=datetime(2024, 1, 15, 9, 0),
            entry_price=1000.0,
            quantity=100,
            exit_time=datetime(2024, 1, 15, 10, 0),
            exit_price=1100.0,
            realized_pnl=10000.0,
            realized_pnl_pct=10.0,
            status=TradeStatus.CLOSED
        )
        
        loss_trade = TradeRecord(
            trade_id="LOSS_001",
            symbol="TEST",
            direction=TradeDirection.LONG,
            entry_time=datetime(2024, 1, 16, 9, 0),
            entry_price=1000.0,
            quantity=100,
            exit_time=datetime(2024, 1, 16, 10, 0),
            exit_price=900.0,
            realized_pnl=-10000.0,
            realized_pnl_pct=-10.0,
            status=TradeStatus.CLOSED
        )
        
        manager.add_trade(win_trade)
        manager.add_trade(loss_trade)
        
        stats = manager.calculate_basic_stats()
        
        assert stats['total_trades'] == 2
        assert stats['winning_trades'] == 1
        assert stats['losing_trades'] == 1
        assert abs(stats['win_rate'] - 0.5) < 0.01
        assert abs(stats['total_pnl'] - 0.0) < 0.01
        assert abs(stats['average_pnl'] - 0.0) < 0.01
        assert abs(stats['average_win'] - 10000.0) < 0.01
        assert abs(stats['average_loss'] - (-10000.0)) < 0.01
        assert abs(stats['profit_factor'] - 1.0) < 0.01
        assert abs(stats['average_hold_time_hours'] - 1.0) < 0.01
    
    def test_delete_trade_success(self, manager, sample_trade):
        """取引削除成功テスト"""
        manager.add_trade(sample_trade)
        
        # 取引が存在することを確認
        assert manager.get_trade(sample_trade.trade_id) is not None
        
        # 削除
        success = manager.delete_trade(sample_trade.trade_id)
        assert success is True
        
        # 削除されていることを確認
        assert manager.get_trade(sample_trade.trade_id) is None
    
    def test_backup_database(self, manager, temp_db_path):
        """データベースバックアップテスト"""
        backup_path = temp_db_path.replace('.db', '_backup.db')
        
        success = manager.backup_database(backup_path)
        assert success is True
        assert os.path.exists(backup_path)
        
        # バックアップファイルがSQLiteデータベースであることを確認
        with sqlite3.connect(backup_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='trade_history'"
            )
            assert cursor.fetchone() is not None
        
        # クリーンアップ
        os.unlink(backup_path)
    
    def test_backup_database_default_path(self, manager):
        """デフォルトパスでのバックアップテスト"""
        success = manager.backup_database()
        assert success is True
        
        # デフォルトパスのバックアップファイルが作成されていることを確認
        backup_files = list(manager.db_path.parent.glob("trade_history_backup_*.db"))
        assert len(backup_files) > 0
        
        # クリーンアップ
        for backup_file in backup_files:
            os.unlink(backup_file)


class TestComplexTradeScenarios:
    """複雑な取引シナリオのテスト"""
    
    @pytest.fixture
    def temp_db_path(self):
        """テンポラリDBファイルパス"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            yield f.name
        os.unlink(f.name)
    
    @pytest.fixture
    def manager(self, temp_db_path):
        """テスト用TradeHistoryManager"""
        return TradeHistoryManager(temp_db_path)
    
    def test_complex_trading_workflow(self, manager):
        """複雑な取引ワークフローテスト"""
        # 複数銘柄、複数戦略の取引シナリオ
        base_time = datetime(2024, 1, 15, 9, 0)
        
        trades_data = [
            # デイトレード戦略
            ("7203.T", "Day Trading", 1000.0, 1050.0, 1),
            ("6758.T", "Day Trading", 2000.0, 1950.0, 1),
            
            # スイング取引戦略
            ("4755.T", "Swing Trading", 1500.0, 1650.0, 5),
            ("9984.T", "Swing Trading", 8000.0, 7800.0, 5),
            
            # 長期投資戦略
            ("6861.T", "Long Term", 3000.0, 3300.0, 30),
        ]
        
        trade_ids = []
        for i, (symbol, strategy, entry, exit, hold_days) in enumerate(trades_data):
            # エントリー
            trade = TradeRecord(
                trade_id=f"COMPLEX_{i:03d}",
                symbol=symbol,
                direction=TradeDirection.LONG,
                entry_time=base_time + timedelta(days=i),
                entry_price=entry,
                quantity=100,
                strategy_name=strategy
            )
            manager.add_trade(trade)
            trade_ids.append(trade.trade_id)
            
            # 決済
            manager.close_trade(
                trade.trade_id,
                exit,
                f"{strategy} Exit",
                exit_commission=entry * 0.001  # 0.1%手数料
            )
        
        # 統計確認
        stats = manager.calculate_basic_stats()
        assert stats['total_trades'] == 5
        assert stats['winning_trades'] == 3  # Toyota, SoftBank, Keyence
        assert stats['losing_trades'] == 2   # Sony, SoftBank Group
        assert stats['win_rate'] == 0.6
        
        # 戦略別分析
        day_trading_trades = manager.get_trades(strategy="Day Trading")
        assert len(day_trading_trades) == 2
        
        swing_trades = manager.get_trades(strategy="Swing Trading")
        assert len(swing_trades) == 2
        
        long_term_trades = manager.get_trades(strategy="Long Term")
        assert len(long_term_trades) == 1
    
    def test_position_sizing_and_risk_management(self, manager):
        """ポジションサイジングとリスク管理テスト"""
        base_time = datetime(2024, 1, 15, 9, 0)
        
        # リスク管理パラメータを持つ取引
        risk_trades = [
            {
                "trade_id": "RISK_001",
                "symbol": "7203.T",
                "entry_price": 1000.0,
                "quantity": 100,
                "stop_loss": 950.0,
                "take_profit": 1100.0,
                "max_loss_pct": 5.0
            },
            {
                "trade_id": "RISK_002",
                "symbol": "6758.T",
                "entry_price": 2000.0,
                "quantity": 50,
                "stop_loss": 1800.0,
                "take_profit": 2200.0,
                "max_loss_pct": 10.0
            }
        ]
        
        for trade_data in risk_trades:
            trade = TradeRecord(
                trade_id=trade_data["trade_id"],
                symbol=trade_data["symbol"],
                direction=TradeDirection.LONG,
                entry_time=base_time,
                entry_price=trade_data["entry_price"],
                quantity=trade_data["quantity"],
                stop_loss=trade_data["stop_loss"],
                take_profit=trade_data["take_profit"],
                max_loss_pct=trade_data["max_loss_pct"]
            )
            manager.add_trade(trade)
        
        # リスク管理情報が正しく保存されていることを確認
        risk_001 = manager.get_trade("RISK_001")
        assert risk_001.stop_loss == 950.0
        assert risk_001.take_profit == 1100.0
        assert risk_001.max_loss_pct == 5.0
        
        risk_002 = manager.get_trade("RISK_002")
        assert risk_002.stop_loss == 1800.0
        assert risk_002.take_profit == 2200.0
        assert risk_002.max_loss_pct == 10.0
    
    def test_market_condition_tracking(self, manager):
        """市場環境追跡テスト"""
        base_time = datetime(2024, 1, 15, 9, 0)
        
        market_scenarios = [
            ("Bull Market", 0.8, 1.5),   # 強気市場
            ("Bear Market", 0.3, 0.8),   # 弱気市場
            ("Sideways", 0.5, 1.2),      # レンジ相場
            ("Volatile", 0.6, 2.5)       # ボラティル市場
        ]
        
        for i, (market, confidence, volatility) in enumerate(market_scenarios):
            trade = TradeRecord(
                trade_id=f"MARKET_{i:03d}",
                symbol="TEST",
                direction=TradeDirection.LONG,
                entry_time=base_time + timedelta(days=i),
                entry_price=1000.0,
                quantity=100,
                market_condition=market,
                signal_confidence=confidence,
                volatility=volatility
            )
            manager.add_trade(trade)
        
        # 市場環境別の取引数確認
        all_trades = manager.get_trades()
        market_conditions = [t.market_condition for t in all_trades]
        
        assert "Bull Market" in market_conditions
        assert "Bear Market" in market_conditions
        assert "Sideways" in market_conditions
        assert "Volatile" in market_conditions


if __name__ == "__main__":
    pytest.main([__file__])