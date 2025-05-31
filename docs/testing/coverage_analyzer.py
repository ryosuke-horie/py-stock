#!/usr/bin/env python3
"""
テストカバレッジ分析スクリプト

このスクリプトは、pytestとcoverageライブラリを使用してプロジェクトのテストカバレッジを分析し、
機能別のカバレッジ状況と難易度を上げている要因を特定する。
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any
import xml.etree.ElementTree as ET


class CoverageAnalyzer:
    """テストカバレッジ分析クラス"""

    def __init__(self, project_root: str = "."):
        """
        初期化

        Args:
            project_root: プロジェクトルートディレクトリのパス
        """
        self.project_root = Path(project_root)
        self.src_dir = self.project_root / "src"
        self.test_dir = self.project_root / "tests"
        self.htmlcov_dir = self.project_root / "htmlcov"
        self.coverage_xml = self.project_root / "coverage.xml"

    def run_coverage_analysis(self) -> Dict[str, Any]:
        """
        カバレッジテストを実行し、結果を分析する

        Returns:
            分析結果辞書
        """
        print("📊 カバレッジテストを実行中...")

        # カバレッジテストを実行
        result = subprocess.run(
            [
                "uv",
                "run",
                "pytest",
                "--cov=src",
                "--cov-report=html",
                "--cov-report=xml",
                "--cov-report=term",
            ],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"❌ カバレッジテスト実行エラー: {result.stderr}")
            return {}

        print("✅ カバレッジテスト完了")

        # XML結果を解析
        return self.parse_coverage_xml()

    def parse_coverage_xml(self) -> Dict[str, Any]:
        """
        coverage.xmlファイルを解析する

        Returns:
            解析結果辞書
        """
        if not self.coverage_xml.exists():
            print("❌ coverage.xml が見つかりません")
            return {}

        tree = ET.parse(self.coverage_xml)
        root = tree.getroot()

        coverage_data = {
            "overall_coverage": float(root.get("line-rate", 0)) * 100,
            "branch_coverage": float(root.get("branch-rate", 0)) * 100,
            "packages": {},
            "files": {},
        }

        # パッケージ別データを収集
        for package in root.findall(".//package"):
            package_name = package.get("name", "")
            line_rate = float(package.get("line-rate", 0))
            branch_rate = float(package.get("branch-rate", 0))

            coverage_data["packages"][package_name] = {
                "line_coverage": line_rate * 100,
                "branch_coverage": branch_rate * 100,
                "files": [],
            }

            # ファイル別データを収集
            for class_elem in package.findall(".//class"):
                filename = class_elem.get("filename", "")
                line_rate = float(class_elem.get("line-rate", 0))
                branch_rate = float(class_elem.get("branch-rate", 0))

                # 行数とmissing行数を計算
                lines_covered = 0
                lines_total = 0
                missing_lines = []

                for line in class_elem.findall(".//line"):
                    lines_total += 1
                    if line.get("hits", "0") != "0":
                        lines_covered += 1
                    else:
                        missing_lines.append(int(line.get("number", 0)))

                file_data = {
                    "filename": filename,
                    "line_coverage": line_rate * 100,
                    "branch_coverage": branch_rate * 100,
                    "lines_total": lines_total,
                    "lines_covered": lines_covered,
                    "lines_missing": len(missing_lines),
                    "missing_lines": missing_lines[:10],  # 最初の10行のみ表示
                }

                coverage_data["files"][filename] = file_data
                coverage_data["packages"][package_name]["files"].append(file_data)

        return coverage_data

    def categorize_by_difficulty(
        self, coverage_data: Dict[str, Any]
    ) -> Dict[str, List[Dict]]:
        """
        カバレッジ向上の難易度別にファイルを分類する

        Args:
            coverage_data: カバレッジデータ

        Returns:
            難易度別分類
        """
        categories = {
            "easy": [],  # 80%以上のカバレッジ - 簡単に100%に持っていける
            "medium": [],  # 60-79%のカバレッジ - 中程度の難易度
            "hard": [],  # 40-59%のカバレッジ - 困難
            "very_hard": [],  # 40%未満のカバレッジ - 非常に困難
            "examples": [],  # examplesディレクトリの特殊処理
        }

        for filename, file_data in coverage_data["files"].items():
            coverage = file_data["line_coverage"]

            # examplesディレクトリは別枠で処理
            if "examples/" in filename:
                categories["examples"].append(file_data)
            elif coverage >= 80:
                categories["easy"].append(file_data)
            elif coverage >= 60:
                categories["medium"].append(file_data)
            elif coverage >= 40:
                categories["hard"].append(file_data)
            else:
                categories["very_hard"].append(file_data)

        # 各カテゴリをカバレッジ順でソート
        for category in categories:
            categories[category].sort(key=lambda x: x["line_coverage"])

        return categories

    def analyze_test_patterns(self) -> Dict[str, Any]:
        """
        テストパターンを分析し、改善提案を生成する

        Returns:
            テストパターン分析結果
        """
        test_files = list(self.test_dir.rglob("test_*.py"))

        analysis = {
            "total_test_files": len(test_files),
            "test_file_coverage": {},
            "missing_test_files": [],
            "test_suggestions": [],
        }

        # srcディレクトリのPythonファイルを列挙
        src_files = list(self.src_dir.rglob("*.py"))
        src_files = [f for f in src_files if "__init__.py" not in f.name]

        # 各srcファイルに対応するテストファイルの存在確認
        for src_file in src_files:
            rel_path = src_file.relative_to(self.src_dir)
            expected_test_file = self.test_dir / "unit" / f"test_{rel_path.name}"

            if not expected_test_file.exists():
                analysis["missing_test_files"].append(str(rel_path))

        return analysis

    def generate_recommendations(
        self,
        coverage_data: Dict[str, Any],
        categories: Dict[str, List[Dict]],
        test_analysis: Dict[str, Any],
    ) -> List[str]:
        """
        カバレッジ向上のための推奨事項を生成する

        Args:
            coverage_data: カバレッジデータ
            categories: 難易度別分類
            test_analysis: テストパターン分析

        Returns:
            推奨事項リスト
        """
        recommendations = []

        # 全体的な状況
        overall = coverage_data["overall_coverage"]
        if overall < 70:
            recommendations.append(
                f"🎯 全体カバレッジ {overall:.1f}% - 70%以上を目標に改善が必要"
            )

        # 優先度の高い改善項目
        if categories["easy"]:
            count = len(categories["easy"])
            recommendations.append(
                f"🟢 簡単改善対象: {count}ファイル - 80%以上のカバレッジを100%に向上"
            )

        if categories["medium"]:
            count = len(categories["medium"])
            recommendations.append(
                f"🟡 中程度改善対象: {count}ファイル - エラーハンドリングやエッジケースのテスト追加"
            )

        if categories["hard"]:
            count = len(categories["hard"])
            recommendations.append(
                f"🟠 困難改善対象: {count}ファイル - 設計見直しやモック活用を検討"
            )

        if categories["very_hard"]:
            count = len(categories["very_hard"])
            recommendations.append(
                f"🔴 非常に困難: {count}ファイル - リファクタリングやアーキテクチャ見直しが必要"
            )

        # examplesディレクトリの特殊な状況
        if categories["examples"]:
            count = len(categories["examples"])
            avg_coverage = (
                sum(f["line_coverage"] for f in categories["examples"]) / count
            )
            recommendations.append(
                f"📚 examplesディレクトリ: {count}ファイル (平均{avg_coverage:.1f}%) - デモ・教育用コードのため低カバレッジは許容"
            )

        # テストファイル不足
        if test_analysis["missing_test_files"]:
            count = len(test_analysis["missing_test_files"])
            recommendations.append(
                f"📝 テストファイル不足: {count}ファイル - 新規テストファイル作成が必要"
            )

        return recommendations

    def generate_detailed_report(
        self,
        coverage_data: Dict[str, Any],
        categories: Dict[str, List[Dict]],
        test_analysis: Dict[str, Any],
        recommendations: List[str],
    ) -> str:
        """
        詳細なレポートを生成する

        Args:
            coverage_data: カバレッジデータ
            categories: 難易度別分類
            test_analysis: テストパターン分析
            recommendations: 推奨事項

        Returns:
            詳細レポート文字列
        """
        report = []
        report.append("# テストカバレッジ分析レポート")
        report.append("")
        import datetime
        report.append(
            f"生成日時: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        report.append("")

        # サマリー
        report.append("## 📊 サマリー")
        report.append("")
        report.append(f"- **全体カバレッジ**: {coverage_data['overall_coverage']:.2f}%")
        report.append(
            f"- **ブランチカバレッジ**: {coverage_data['branch_coverage']:.2f}%"
        )
        report.append(f"- **総テストファイル数**: {test_analysis['total_test_files']}")
        report.append("")

        # 推奨事項
        report.append("## 🎯 推奨事項")
        report.append("")
        for rec in recommendations:
            report.append(f"- {rec}")
        report.append("")

        # 難易度別分析
        report.append("## 📈 難易度別分析")
        report.append("")

        for difficulty, files in categories.items():
            if not files:
                continue

            if difficulty == "easy":
                report.append("### 🟢 簡単改善対象 (80%以上)")
            elif difficulty == "medium":
                report.append("### 🟡 中程度改善対象 (60-79%)")
            elif difficulty == "hard":
                report.append("### 🟠 困難改善対象 (40-59%)")
            elif difficulty == "very_hard":
                report.append("### 🔴 非常に困難 (40%未満)")
            elif difficulty == "examples":
                report.append("### 📚 examplesディレクトリ (特殊)")

            report.append("")
            report.append("| ファイル | カバレッジ | 総行数 | 未カバー行数 |")
            report.append("|----------|------------|--------|--------------|")

            for file_data in files[:10]:  # 最大10ファイルまで表示
                filename = file_data["filename"].replace("src/", "")
                coverage = file_data["line_coverage"]
                total_lines = file_data["lines_total"]
                missing_lines = file_data["lines_missing"]

                report.append(
                    f"| {filename} | {coverage:.1f}% | {total_lines} | {missing_lines} |"
                )

            if len(files) > 10:
                report.append(f"| ... | ... | ... | ... |")
                report.append(f"| (他{len(files) - 10}ファイル) | | | |")

            report.append("")

        # テストファイル不足
        if test_analysis["missing_test_files"]:
            report.append("## 📝 テストファイル不足")
            report.append("")
            report.append("以下のソースファイルに対応するテストファイルが存在しません:")
            report.append("")
            for missing_file in test_analysis["missing_test_files"][:20]:
                report.append(
                    f"- `{missing_file}` → `tests/unit/test_{Path(missing_file).name}`"
                )

            if len(test_analysis["missing_test_files"]) > 20:
                remaining = len(test_analysis["missing_test_files"]) - 20
                report.append(f"- ... (他{remaining}ファイル)")
            report.append("")

        return "\n".join(report)

    def run_analysis(self) -> None:
        """
        カバレッジ分析を実行し、レポートを生成する
        """
        print("🚀 テストカバレッジ分析を開始します...")
        print()

        # カバレッジ分析実行
        coverage_data = self.run_coverage_analysis()
        if not coverage_data:
            print("❌ カバレッジ分析に失敗しました")
            return

        # 難易度別分類
        categories = self.categorize_by_difficulty(coverage_data)

        # テストパターン分析
        test_analysis = self.analyze_test_patterns()

        # 推奨事項生成
        recommendations = self.generate_recommendations(
            coverage_data, categories, test_analysis
        )

        # 詳細レポート生成
        detailed_report = self.generate_detailed_report(
            coverage_data, categories, test_analysis, recommendations
        )

        # レポート保存
        report_path = (
            self.project_root / "docs" / "testing" / "coverage_analysis_report.md"
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(detailed_report)

        print(f"✅ 詳細レポートを保存しました: {report_path}")

        # 分析データをJSONで保存
        json_path = self.project_root / "docs" / "testing" / "coverage_data.json"
        analysis_data = {
            "coverage_data": coverage_data,
            "categories": categories,
            "test_analysis": test_analysis,
            "recommendations": recommendations,
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)

        print(f"✅ 分析データを保存しました: {json_path}")

        # サマリー表示
        print()
        print("📊 分析サマリー:")
        print(f"   全体カバレッジ: {coverage_data['overall_coverage']:.2f}%")
        print(f"   簡単改善対象: {len(categories['easy'])}ファイル")
        print(f"   中程度改善対象: {len(categories['medium'])}ファイル")
        print(f"   困難改善対象: {len(categories['hard'])}ファイル")
        print(f"   非常に困難: {len(categories['very_hard'])}ファイル")
        print(f"   examplesディレクトリ: {len(categories['examples'])}ファイル")
        print()


def main():
    """メイン関数"""
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        project_root = "."

    analyzer = CoverageAnalyzer(project_root)
    analyzer.run_analysis()


if __name__ == "__main__":
    main()
