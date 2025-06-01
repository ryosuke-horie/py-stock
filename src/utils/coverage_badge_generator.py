#!/usr/bin/env python3
"""
テストカバレッジバッジ生成機能

このモジュールは、プロジェクトのテストカバレッジ結果を基に
SVGバッジを生成し、READMEファイルで表示可能にする機能を提供する。
"""

import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Dict, Any
import urllib.parse


class CoverageBadgeGenerator:
    """テストカバレッジバッジ生成クラス"""

    def __init__(self, project_root: str = "."):
        """
        初期化

        Args:
            project_root: プロジェクトルートディレクトリのパス
        """
        self.project_root = Path(project_root)
        self.coverage_xml = self.project_root / "coverage.xml"
        self.badges_dir = self.project_root / "badges"
        self.badges_dir.mkdir(exist_ok=True)

    def get_coverage_percentage(self) -> Optional[float]:
        """
        カバレッジXMLファイルからカバレッジ率を取得する

        Returns:
            カバレッジ率（0-100）、取得できない場合はNone
        """
        if not self.coverage_xml.exists():
            return None

        try:
            tree = ET.parse(self.coverage_xml)
            root = tree.getroot()
            line_rate = float(root.get("line-rate", 0))
            return line_rate * 100
        except (ET.ParseError, ValueError, TypeError):
            return None

    def run_coverage_test(self) -> Optional[float]:
        """
        カバレッジテストを実行してカバレッジ率を取得する

        Returns:
            カバレッジ率（0-100）、実行に失敗した場合はNone
        """
        try:
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "pytest",
                    "--cov=src",
                    "--cov-report=xml",
                    "--cov-report=term",
                    "-q",  # 静音モード
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5分のタイムアウト
            )

            if result.returncode == 0:
                return self.get_coverage_percentage()
            else:
                print(f"カバレッジテスト実行エラー: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            print("カバレッジテスト実行がタイムアウトしました")
            return None
        except Exception as e:
            print(f"カバレッジテスト実行中にエラーが発生しました: {e}")
            return None

    def get_badge_color(self, coverage: float) -> str:
        """
        カバレッジ率に基づいてバッジの色を決定する

        Args:
            coverage: カバレッジ率（0-100）

        Returns:
            バッジの色（16進数カラーコード）
        """
        if coverage >= 90:
            return "brightgreen"  # 緑
        elif coverage >= 80:
            return "green"  # 明るい緑
        elif coverage >= 70:
            return "yellowgreen"  # 黄緑
        elif coverage >= 60:
            return "yellow"  # 黄色
        elif coverage >= 50:
            return "orange"  # オレンジ
        else:
            return "red"  # 赤

    def generate_svg_badge(
        self, coverage: float, subject: str = "coverage"
    ) -> str:
        """
        SVGバッジを生成する

        Args:
            coverage: カバレッジ率（0-100）
            subject: バッジの左側のテキスト

        Returns:
            SVGバッジのXML文字列
        """
        color = self.get_badge_color(coverage)
        status = f"{coverage:.1f}%"

        # テキストの幅を計算（近似値）
        subject_width = len(subject) * 6 + 10
        status_width = len(status) * 6 + 10
        total_width = subject_width + status_width

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{total_width}" height="20">
    <linearGradient id="b" x2="0" y2="100%">
        <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
        <stop offset="1" stop-opacity=".1"/>
    </linearGradient>
    <clipPath id="a">
        <rect width="{total_width}" height="20" rx="3" fill="#fff"/>
    </clipPath>
    <g clip-path="url(#a)">
        <path fill="#555" d="M0 0h{subject_width}v20H0z"/>
        <path fill="#{self._get_color_hex(color)}" d="M{subject_width} 0h{status_width}v20H{subject_width}z"/>
        <path fill="url(#b)" d="M0 0h{total_width}v20H0z"/>
    </g>
    <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="110">
        <text x="{subject_width // 2 + 1}" y="15" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="{(subject_width - 10) * 10}">{subject}</text>
        <text x="{subject_width // 2}" y="14" transform="scale(.1)" textLength="{(subject_width - 10) * 10}">{subject}</text>
        <text x="{subject_width + status_width // 2 + 1}" y="15" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="{(status_width - 10) * 10}">{status}</text>
        <text x="{subject_width + status_width // 2}" y="14" transform="scale(.1)" textLength="{(status_width - 10) * 10}">{status}</text>
    </g>
</svg>'''
        return svg

    def _get_color_hex(self, color_name: str) -> str:
        """
        色名を16進数カラーコードに変換する

        Args:
            color_name: 色名

        Returns:
            16進数カラーコード（#なし）
        """
        color_map = {
            "brightgreen": "4c1",
            "green": "97CA00",
            "yellowgreen": "a4a61d",
            "yellow": "dfb317",
            "orange": "fe7d37",
            "red": "e05d44",
        }
        return color_map.get(color_name, "lightgrey")

    def save_badge(self, coverage: float, filename: str = "coverage.svg") -> Path:
        """
        SVGバッジをファイルに保存する

        Args:
            coverage: カバレッジ率（0-100）
            filename: 保存するファイル名

        Returns:
            保存されたファイルのパス
        """
        svg_content = self.generate_svg_badge(coverage)
        badge_path = self.badges_dir / filename

        with open(badge_path, "w", encoding="utf-8") as f:
            f.write(svg_content)

        return badge_path

    def generate_markdown_badge(
        self, coverage: float, link_url: str = None
    ) -> str:
        """
        MarkdownでのバッジコードHTMLを生成する

        Args:
            coverage: カバレッジ率（0-100）
            link_url: バッジクリック時のリンク先URL

        Returns:
            Markdown形式のバッジコード
        """
        badge_url = f"badges/coverage.svg"
        alt_text = f"Coverage {coverage:.1f}%"

        if link_url:
            return f"[![{alt_text}]({badge_url})]({link_url})"
        else:
            return f"![{alt_text}]({badge_url})"

    def generate_shields_io_badge_url(self, coverage: float) -> str:
        """
        Shields.ioサービスを使ったバッジURLを生成する

        Args:
            coverage: カバレッジ率（0-100）

        Returns:
            Shields.ioバッジURL
        """
        color = self.get_badge_color(coverage)
        coverage_text = f"{coverage:.1f}%"
        encoded_text = urllib.parse.quote(coverage_text)

        return f"https://img.shields.io/badge/coverage-{encoded_text}-{color}"

    def update_readme_with_badge(
        self, coverage: float, readme_path: str = None
    ) -> bool:
        """
        READMEファイルにカバレッジバッジを追加または更新する

        Args:
            coverage: カバレッジ率（0-100）
            readme_path: READMEファイルのパス（Noneの場合はプロジェクトルートのREADME.md）

        Returns:
            更新が成功した場合True、失敗した場合False
        """
        if readme_path is None:
            readme_path = self.project_root / "README.md"
        else:
            readme_path = Path(readme_path)

        if not readme_path.exists():
            print(f"READMEファイルが見つかりません: {readme_path}")
            return False

        try:
            # 現在のREADME内容を読み込み
            with open(readme_path, "r", encoding="utf-8") as f:
                content = f.read()

            # バッジコードを生成
            shields_badge = self.generate_shields_io_badge_url(coverage)
            badge_markdown = f"![Coverage](https://img.shields.io/badge/coverage-{coverage:.1f}%25-{self.get_badge_color(coverage)})"

            # 既存のカバレッジバッジを探して置換、なければタイトルの後に追加
            coverage_badge_pattern = r"!\[Coverage\]\(https://img\.shields\.io/badge/coverage-[^)]+\)"

            if "![Coverage]" in content:
                # 既存のバッジを更新
                import re

                content = re.sub(coverage_badge_pattern, badge_markdown, content)
            else:
                # 新しいバッジを追加（タイトルの後に）
                lines = content.split("\\n")
                if lines and lines[0].startswith("# "):
                    # タイトルの後に空行とバッジを挿入
                    lines.insert(1, "")
                    lines.insert(2, badge_markdown)
                    lines.insert(3, "")
                    content = "\\n".join(lines)
                else:
                    # タイトルがない場合は先頭に追加
                    content = f"{badge_markdown}\\n\\n{content}"

            # ファイルに書き戻し
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(content)

            return True

        except Exception as e:
            print(f"README更新エラー: {e}")
            return False

    def generate_badge_info(self) -> Dict[str, Any]:
        """
        カバレッジ情報とバッジ情報を生成する

        Returns:
            カバレッジとバッジ情報を含む辞書
        """
        # 最新のカバレッジを取得
        coverage = self.run_coverage_test()
        if coverage is None:
            coverage = self.get_coverage_percentage()

        if coverage is None:
            return {
                "success": False,
                "error": "カバレッジ情報を取得できませんでした",
            }

        # ローカルSVGバッジを保存
        badge_path = self.save_badge(coverage)

        # バッジ情報を返す
        return {
            "success": True,
            "coverage": coverage,
            "color": self.get_badge_color(coverage),
            "local_badge_path": str(badge_path),
            "shields_io_url": self.generate_shields_io_badge_url(coverage),
            "markdown_local": self.generate_markdown_badge(coverage),
            "markdown_shields": f"![Coverage](https://img.shields.io/badge/coverage-{coverage:.1f}%25-{self.get_badge_color(coverage)})",
        }


def main():
    """メイン関数"""
    import sys

    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        project_root = "."

    generator = CoverageBadgeGenerator(project_root)

    print("🎯 カバレッジバッジ生成を開始します...")

    # カバレッジ情報を取得
    badge_info = generator.generate_badge_info()

    if not badge_info["success"]:
        print(f"❌ {badge_info['error']}")
        return

    coverage = badge_info["coverage"]
    print(f"✅ カバレッジ: {coverage:.1f}%")
    print(f"✅ ローカルバッジ: {badge_info['local_badge_path']}")
    print(f"✅ Shields.io URL: {badge_info['shields_io_url']}")

    # READMEを更新
    if generator.update_readme_with_badge(coverage):
        print("✅ README.mdにバッジを追加しました")
    else:
        print("❌ README.mdの更新に失敗しました")

    print("\\n📋 利用可能なバッジコード:")
    print(f"Markdown (Shields.io): {badge_info['markdown_shields']}")
    print(f"Markdown (ローカル): {badge_info['markdown_local']}")


if __name__ == "__main__":
    main()