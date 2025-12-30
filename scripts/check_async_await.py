#!/usr/bin/env python3
"""
非同期関数内でのawait忘れを検出するスクリプト

Usage:
    python scripts/check_async_await.py <file1.py> <file2.py> ...

このスクリプトは、Python の AST (Abstract Syntax Tree) を使用して、
非同期関数内で RepositoryAdapter のメソッド呼び出しが await されているかを
チェックします。

Issue #839: async/await バグの再発防止
"""

import argparse
import ast
import sys

from pathlib import Path


class AsyncAwaitChecker(ast.NodeVisitor):
    """非同期関数内でのRepositoryAdapterメソッド呼び出しをチェック

    このクラスは AST を走査し、以下をチェックします：
    1. 非同期関数内での関数呼び出し
    2. RepositoryAdapter のメソッド呼び出しが await されているか
    3. よく使われるリポジトリメソッドの await 忘れ
    """

    def __init__(self, filename: str):
        self.filename = filename
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.in_async_function = False
        self.current_function_name = ""

        # よく使われる非同期メソッド
        self.async_methods = {
            # Repository メソッド
            "get_by_id",
            "get_all",
            "create",
            "update",
            "delete",
            "get_by_meeting",
            "get_by_minutes",
            "get_by_conference",
            "get_by_party",
            "get_by_parliamentary_group",
            "get_by_politician",
            "get_by_speaker",
            "bulk_create",
            "bulk_update",
            "bulk_delete",
            # その他の非同期メソッド
            "fetch_html",
            "extract_members",
            "match_speaker_to_politician",
            "generate",
            "generate_structured",
        }

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """非同期関数の定義をチェック"""
        old_in_async = self.in_async_function
        old_function_name = self.current_function_name

        self.in_async_function = True
        self.current_function_name = node.name

        self.generic_visit(node)

        self.in_async_function = old_in_async
        self.current_function_name = old_function_name

    def visit_Call(self, node: ast.Call) -> None:
        """関数呼び出しをチェック"""
        if self.in_async_function:
            # メソッド呼び出しをチェック（e.g., repo.get_by_id()）
            if isinstance(node.func, ast.Attribute):
                method_name = node.func.attr

                # 非同期メソッドの可能性がある
                if method_name in self.async_methods:
                    # このノードが await されているかチェック
                    if not self._is_in_await_context(node):
                        line_no = node.lineno
                        msg = (
                            f"{self.filename}:{line_no}: "
                            f"関数 '{self.current_function_name}' 内: "
                            f"'{method_name}()' には 'await' が必要かも"
                        )
                        self.warnings.append(msg)

        self.generic_visit(node)

    def _is_in_await_context(self, node: ast.AST) -> bool:
        """ノードが await コンテキスト内にあるかチェック（簡易版）

        注: この実装は簡易版で、完全な検出はできません。
        より正確な検出には、親ノードの追跡が必要です。
        現在は Pyright による型チェックが主要な防御線となります。
        """
        # 簡易実装：常に False を返す
        # 実際の await 検出は Pyright に任せる
        # このスクリプトは警告のみを出力
        return False

    def get_errors(self) -> list[str]:
        """エラーメッセージのリストを取得"""
        return self.errors

    def get_warnings(self) -> list[str]:
        """警告メッセージのリストを取得"""
        return self.warnings


def check_file(filepath: Path) -> tuple[list[str], list[str]]:
    """ファイル内の await 忘れをチェック

    Args:
        filepath: チェックするファイルのパス

    Returns:
        (エラーリスト, 警告リスト) のタプル
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            source = f.read()

        # AST を解析
        tree = ast.parse(source, filename=str(filepath))

        # チェッカーを実行
        checker = AsyncAwaitChecker(str(filepath))
        checker.visit(tree)

        return checker.get_errors(), checker.get_warnings()

    except SyntaxError as e:
        return ([f"{filepath}: 構文エラー: {e}"], [])

    except Exception as e:
        return ([f"{filepath}: エラー: {e}"], [])


def main() -> int:
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="非同期関数内での await 忘れをチェック"
    )
    parser.add_argument(
        "files",
        nargs="+",
        type=Path,
        help="チェックする Python ファイル",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="警告もエラーとして扱う",
    )

    args = parser.parse_args()

    all_errors: list[str] = []
    all_warnings: list[str] = []

    # 各ファイルをチェック
    for filepath in args.files:
        if filepath.suffix == ".py":
            errors, warnings = check_file(filepath)
            all_errors.extend(errors)
            all_warnings.extend(warnings)

    # 結果を表示
    if all_errors:
        print("❌ エラーが見つかりました:")
        for error in all_errors:
            print(f"  {error}")

    if all_warnings:
        print("\n⚠️  警告が見つかりました:")
        for warning in all_warnings:
            print(f"  {warning}")

    # 終了コードを返す
    if all_errors:
        return 1

    if args.strict and all_warnings:
        return 1

    if not all_errors and not all_warnings:
        print("✅ await 関連の問題は見つかりませんでした")

    return 0


if __name__ == "__main__":
    sys.exit(main())
