#!/usr/bin/env python3
"""
カバレッジバッジ更新スクリプト

このスクリプトはテストカバレッジを実行し、結果をバッジとしてREADMEに追加する。
CI/CDパイプラインでの使用や、開発者が手動でバッジを更新する際に使用する。
"""

import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.coverage_badge_generator import CoverageBadgeGenerator


def main():
    """メイン関数"""
    print("🎯 カバレッジバッジ更新スクリプトを開始します...")
    print()

    # プロジェクトルートでバッジジェネレータを初期化
    generator = CoverageBadgeGenerator(str(project_root))

    # カバレッジテストを実行してバッジ情報を生成
    print("📊 カバレッジテストを実行中...")
    badge_info = generator.generate_badge_info()

    if not badge_info["success"]:
        print(f"❌ エラー: {badge_info['error']}")
        sys.exit(1)

    coverage = badge_info["coverage"]
    color = badge_info["color"]

    print(f"✅ カバレッジテスト完了")
    print(f"   カバレッジ率: {coverage:.1f}%")
    print(f"   バッジ色: {color}")
    print()

    # ローカルSVGバッジを保存
    print("💾 ローカルSVGバッジを保存中...")
    print(f"   保存先: {badge_info['local_badge_path']}")

    # READMEファイルを更新
    print("📝 README.mdを更新中...")
    readme_path = project_root / "README.md"

    if generator.update_readme_with_badge(coverage, readme_path):
        print("✅ README.mdにカバレッジバッジを追加/更新しました")
    else:
        print("❌ README.mdの更新に失敗しました")
        sys.exit(1)

    print()
    print("🎉 カバレッジバッジ更新が完了しました！")
    print()
    print("📋 バッジ情報:")
    print(f"   Shields.io URL: {badge_info['shields_io_url']}")
    print(f"   Markdown: {badge_info['markdown_shields']}")
    print()

    # カバレッジしきい値チェック
    threshold = 68.0  # pyproject.tomlのfail_underに合わせる
    if coverage < threshold:
        print(f"⚠️  警告: カバレッジ率 {coverage:.1f}% がしきい値 {threshold}% を下回っています")
    else:
        print(f"🎯 カバレッジ率 {coverage:.1f}% がしきい値 {threshold}% を満たしています")


if __name__ == "__main__":
    main()