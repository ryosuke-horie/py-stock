"""
インテリジェントアラートシステムのデモンストレーション
市場状況に応じた動的アラート管理の実例
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.technical_analysis.intelligent_alert_system import (
    IntelligentAlertSystem,
    AlertPriority,
    MarketCondition
)
from src.data_collector.stock_data_collector import StockDataCollector
from src.technical_analysis.indicators import TechnicalIndicators
from src.technical_analysis.market_environment import MarketEnvironmentAnalyzer


def demo_intelligent_alerts():
    """インテリジェントアラートシステムのデモ"""
    print("=== インテリジェントアラートシステムデモ ===\n")
    
    # システム初期化
    alert_system = IntelligentAlertSystem()
    data_collector = StockDataCollector()
    indicators = None  # データ取得後に初期化
    
    # デモ用銘柄
    symbol = "7203.T"  # トヨタ自動車
    
    print(f"分析対象銘柄: {symbol}\n")
    
    # 1. 市場データ取得
    print("1. 市場データ取得中...")
    data = data_collector.get_stock_data(symbol, period="1mo")
    
    if data is None or data.empty:
        print("データ取得に失敗しました。デモデータを使用します。")
        data = create_demo_data()
    else:
        print(f"  - データ期間: {data.index[0]} 〜 {data.index[-1]}")
        print(f"  - データ数: {len(data)} レコード\n")
    
    # データ取得後にTechnicalIndicatorsを初期化
    indicators = TechnicalIndicators(data)
    
    # 2. 市場状況分析
    print("2. 市場状況分析...")
    market_condition = alert_system.analyze_market_condition(data, symbol)
    print(f"  - 現在の市場状況: {market_condition.value}")
    print(f"  - 説明: {get_market_condition_description(market_condition)}\n")
    
    # 3. 複合アラート作成
    print("3. 複合アラートの作成...")
    
    # ブレイクアウトアラート
    breakout_conditions = [
        {
            'type': 'price_change_pct',
            'threshold': 2.0,  # 2%以上の価格上昇
            'operator': 'greater',
            'weight': 1.5
        },
        {
            'type': 'volume_ratio',
            'threshold': 2.5,  # 平均出来高の2.5倍
            'operator': 'greater',
            'weight': 1.2
        },
        {
            'type': 'rsi',
            'threshold': 60.0,  # RSI 60以上
            'operator': 'greater',
            'weight': 1.0
        },
        {
            'type': 'macd_signal',
            'threshold': 0.0,  # MACDがシグナルを上回る
            'operator': 'greater',
            'weight': 0.8
        }
    ]
    
    breakout_alert_id = alert_system.create_composite_alert(
        symbol=symbol,
        conditions=breakout_conditions,
        min_conditions=3,  # 最低3条件
        priority_rules={
            1: 'low',
            2: 'medium',
            3: 'high',
            4: 'critical'
        }
    )
    print(f"  - ブレイクアウトアラート作成: {breakout_alert_id}")
    
    # リスクアラート
    risk_conditions = [
        {
            'type': 'volatility',
            'threshold': 3.0,  # ボラティリティ3%以上
            'operator': 'greater',
            'weight': 1.5
        },
        {
            'type': 'rsi',
            'threshold': 80.0,  # RSI 80以上（買われすぎ）
            'operator': 'greater',
            'weight': 1.0
        },
        {
            'type': 'price_drop_pct',
            'threshold': -1.5,  # 1.5%以上の下落
            'operator': 'less',
            'weight': 1.2
        }
    ]
    
    risk_alert_id = alert_system.create_composite_alert(
        symbol=symbol,
        conditions=risk_conditions,
        min_conditions=2,
        priority_rules={
            1: 'medium',
            2: 'high',
            3: 'critical'
        }
    )
    print(f"  - リスクアラート作成: {risk_alert_id}\n")
    
    # 4. 動的閾値調整
    print("4. 市場状況に応じた動的閾値調整...")
    alert_system.adjust_thresholds(symbol, market_condition)
    
    # 調整後の閾値を表示
    for alert_id, alert in alert_system.alerts.items():
        print(f"\n  アラート: {alert_id[:20]}...")
        for condition in alert.conditions[:2]:  # 最初の2条件のみ表示
            print(f"    - {condition.condition_type}:")
            print(f"      基準値: {condition.threshold.base_value:.2f}")
            print(f"      調整後: {condition.threshold.current_value:.2f}")
            print(f"      調整係数: {condition.threshold.adjustment_factor:.2f}")
    
    # 5. アラート評価
    print("\n5. 現在の市場データでアラート評価...")
    
    # テクニカル指標計算
    indicators_df = indicators.calculate_all_indicators(data)
    
    # 最新データでアラート評価
    latest_data = indicators_df.iloc[-1]
    
    # 市場データとテクニカルデータを準備
    market_data = {
        'price': latest_data['Close'],
        'volume': latest_data['Volume'],
        'price_change_pct': ((latest_data['Close'] - indicators_df['Close'].iloc[-2]) / 
                            indicators_df['Close'].iloc[-2] * 100),
        'volume_ratio': latest_data['Volume'] / indicators_df['Volume'].rolling(20).mean().iloc[-1]
    }
    
    technical_data = {
        'rsi': latest_data['RSI'],
        'macd': latest_data['MACD'],
        'macd_signal': latest_data['MACD'] - latest_data['MACD_Signal'],
        'volatility': indicators_df['Close'].pct_change().rolling(20).std().iloc[-1] * 100
    }
    
    # 各アラートを評価
    for alert_id in [breakout_alert_id, risk_alert_id]:
        result = alert_system.evaluate_alert(
            alert_id,
            market_data,
            technical_data
        )
        
        if result:
            print(f"\n  ⚠️ アラート発火: {alert_id[:20]}...")
            print(f"    優先度: {result['priority'].value}")
            print(f"    満たされた条件: {len(result['conditions_met'])}/{result['total_conditions']}")
            for cond in result['conditions_met']:
                print(f"    - {cond['type']}: {cond['value']:.2f} (閾値: {cond['threshold']:.2f})")
            
            # ノイズフィルタリング適用
            filtered_result = alert_system.process_alert(result)
            if filtered_result:
                print("    ✅ ノイズフィルタリング通過")
                
                # 通知方法の決定
                notification_methods = alert_system.get_notification_method(result['priority'])
                print(f"    通知方法: {', '.join(notification_methods)}")
            else:
                print("    ❌ ノイズフィルタリングで除外")
        else:
            print(f"\n  アラート未発火: {alert_id[:20]}...")
    
    # 6. アラートサマリー
    print("\n6. アクティブアラートサマリー")
    summary = alert_system.get_active_alerts_summary()
    
    print(f"  - 総アクティブアラート数: {summary['total_active']}")
    print(f"  - 銘柄別: {summary['by_symbol']}")
    print(f"  - 最近1時間の発火数:")
    for priority, count in summary['by_priority'].items():
        if count > 0:
            print(f"    {priority}: {count}件")
    
    print("\n=== デモ完了 ===")


def create_demo_data():
    """デモ用データの作成"""
    dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
    
    # ランダムウォークで価格データ生成
    price = 2000
    prices = []
    volumes = []
    
    for _ in range(30):
        # 価格変動（±2%）
        change = np.random.normal(0, 0.02)
        price = price * (1 + change)
        prices.append(price)
        
        # 出来高（基準値の50%〜150%）
        volume = np.random.uniform(1000000, 3000000)
        volumes.append(volume)
    
    return pd.DataFrame({
        'Open': [p * 0.99 for p in prices],
        'High': [p * 1.01 for p in prices],
        'Low': [p * 0.98 for p in prices],
        'Close': prices,
        'Volume': volumes
    }, index=dates)


def get_market_condition_description(condition: MarketCondition) -> str:
    """市場状況の説明を取得"""
    descriptions = {
        MarketCondition.EXTREME_VOLATILITY: "極端な価格変動が発生。リスク管理を強化し、ポジションサイズを縮小することを推奨。",
        MarketCondition.HIGH_VOLATILITY: "通常より高い変動性。慎重な取引を心がけ、ストップロスを設定。",
        MarketCondition.NORMAL: "標準的な市場環境。通常の取引戦略を適用可能。",
        MarketCondition.LOW_VOLATILITY: "変動性が低い状態。ブレイクアウトの可能性に注意。",
        MarketCondition.CONSOLIDATION: "レンジ相場。サポート・レジスタンスレベルでの取引が有効。"
    }
    return descriptions.get(condition, "不明な市場状況")


def demo_noise_filtering():
    """ノイズフィルタリングのデモ"""
    print("\n=== ノイズフィルタリングデモ ===\n")
    
    alert_system = IntelligentAlertSystem()
    
    # 同じアラートを短期間に複数回発火させる
    base_alert = {
        'alert_id': 'test_alert_001',
        'symbol': 'TEST',
        'timestamp': datetime.now(),
        'conditions_met': [{'type': 'price', 'value': 110.0, 'threshold': 100.0}],
        'total_conditions': 1,
        'priority': AlertPriority.MEDIUM,
        'market_condition': MarketCondition.NORMAL
    }
    
    print("同じアラートを5分以内に3回発火:")
    
    for i in range(3):
        alert = base_alert.copy()
        alert['timestamp'] = datetime.now() + timedelta(seconds=i * 60)  # 1分間隔
        
        should_notify = alert_system.apply_noise_filter(alert)
        print(f"  {i+1}回目 ({alert['timestamp'].strftime('%H:%M:%S')}): "
              f"{'✅ 通知' if should_notify else '❌ フィルタリング'}")
        
        if should_notify:
            alert_system.alert_history.append(alert)
    
    print("\n異なる優先度でのフィルタリング:")
    
    for priority in [AlertPriority.CRITICAL, AlertPriority.LOW]:
        alert = base_alert.copy()
        alert['priority'] = priority
        alert['timestamp'] = datetime.now() + timedelta(seconds=180)
        
        should_notify = alert_system.apply_noise_filter(alert)
        print(f"  優先度 {priority.value}: "
              f"{'✅ 通知' if should_notify else '❌ フィルタリング'}")


if __name__ == "__main__":
    # メインデモ実行
    demo_intelligent_alerts()
    
    # ノイズフィルタリングデモ
    demo_noise_filtering()