# テストカバレッジ分析レポート

生成日時: 2025-05-31 12:55:39

## 📊 サマリー

- **全体カバレッジ**: 70.80%
- **ブランチカバレッジ**: 61.98%
- **総テストファイル数**: 31

## 🎯 推奨事項

- 🟢 簡単改善対象: 28ファイル - 80%以上のカバレッジを100%に向上
- 🟡 中程度改善対象: 7ファイル - エラーハンドリングやエッジケースのテスト追加
- 📚 examplesディレクトリ: 7ファイル (平均19.7%) - デモ・教育用コードのため低カバレッジは許容
- 📝 テストファイル不足: 7ファイル - 新規テストファイル作成が必要

## 📈 難易度別分析

### 🟢 簡単改善対象 (80%以上)

| ファイル | カバレッジ | 総行数 | 未カバー行数 |
|----------|------------|--------|--------------|
| technical_analysis/fundamental_analysis.py | 83.4% | 308 | 51 |
| risk_management/portfolio_analyzer.py | 86.0% | 299 | 42 |
| technical_analysis/investment_story_generator.py | 86.2% | 240 | 33 |
| technical_analysis/support_resistance.py | 87.5% | 329 | 41 |
| technical_analysis/market_environment.py | 88.2% | 229 | 27 |
| technical_analysis/fundamental_visualization.py | 89.4% | 160 | 17 |
| performance_tracking/pattern_analyzer.py | 89.5% | 266 | 28 |
| data_collector/stock_data_collector.py | 89.7% | 136 | 14 |
| technical_analysis/signal_generator.py | 89.8% | 420 | 43 |
| tax_calculation/profit_loss_simulator.py | 90.5% | 190 | 18 |
| ... | ... | ... | ... |
| (他18ファイル) | | | |

### 🟡 中程度改善対象 (60-79%)

| ファイル | カバレッジ | 総行数 | 未カバー行数 |
|----------|------------|--------|--------------|
| performance_tracking/performance_tracker.py | 70.6% | 228 | 67 |
| performance_tracking/tendency_analyzer.py | 72.4% | 536 | 148 |
| data_collector/watchlist_storage.py | 73.7% | 217 | 57 |
| config/settings.py | 76.9% | 182 | 42 |
| performance_tracking/improvement_suggestions.py | 77.4% | 230 | 52 |
| data_collector/backup_manager.py | 78.6% | 229 | 49 |
| risk_management/risk_manager.py | 79.0% | 229 | 48 |

### 📚 examplesディレクトリ (特殊)

| ファイル | カバレッジ | 総行数 | 未カバー行数 |
|----------|------------|--------|--------------|
| examples/intelligent_alert_demo.py | 0.0% | 108 | 108 |
| examples/signal_generator_demo.py | 5.3% | 360 | 341 |
| examples/technical_analysis_demo.py | 5.7% | 296 | 279 |
| examples/support_resistance_demo.py | 6.3% | 269 | 252 |
| examples/risk_management_demo.py | 8.7% | 195 | 178 |
| examples/basic_usage.py | 11.6% | 121 | 107 |
| examples/__init__.py | 100.0% | 0 | 0 |

## 📝 テストファイル不足

以下のソースファイルに対応するテストファイルが存在しません:

- `examples/basic_usage.py` → `tests/unit/test_basic_usage.py`
- `examples/intelligent_alert_demo.py` → `tests/unit/test_intelligent_alert_demo.py`
- `examples/risk_management_demo.py` → `tests/unit/test_risk_management_demo.py`
- `examples/support_resistance_demo.py` → `tests/unit/test_support_resistance_demo.py`
- `examples/technical_analysis_demo.py` → `tests/unit/test_technical_analysis_demo.py`
- `examples/signal_generator_demo.py` → `tests/unit/test_signal_generator_demo.py`
- `technical_analysis/indicators.py` → `tests/unit/test_indicators.py`
