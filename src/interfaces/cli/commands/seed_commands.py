"""SEEDファイル生成関連のCLIコマンド"""

from pathlib import Path

import click

from click import Command

from src.infrastructure.exceptions import (
    DatabaseError,
    PermissionError,
)
from src.interfaces.cli.base import BaseCommand
from src.seed_generator import generate_all_seeds


class SeedCommands(BaseCommand):
    """SEEDファイル生成関連のコマンド"""

    @staticmethod
    @click.command("generate-seeds")
    @click.option(
        "--output-dir",
        default="database/",
        help="SEEDファイルの出力ディレクトリ（デフォルト: database/）",
    )
    def generate_seeds(output_dir: str) -> None:
        """データベースから現在のデータを元にSEEDファイルを生成する

        現在のデータベースに登録されている以下のデータからSEEDファイルを生成します：
        - governing_bodies (開催主体)
        - conferences (会議体)
        - political_parties (政党)

        生成されるファイル名にはサフィックス '_generated' が付きます。
        """
        try:
            # 出力ディレクトリの確認
            output_path = Path(output_dir)
            if not output_path.exists():
                output_path.mkdir(parents=True)
                click.echo(f"出力ディレクトリを作成しました: {output_dir}")

            click.echo("SEEDファイルの生成を開始します...")
            generate_all_seeds(output_dir)
            click.echo(click.style("✅ SEEDファイルの生成が完了しました", fg="green"))

            # 生成されたファイルのリスト
            generated_files = [
                f"{output_dir}/seed_governing_bodies_generated.sql",
                f"{output_dir}/seed_conferences_generated.sql",
                f"{output_dir}/seed_political_parties_generated.sql",
            ]

            click.echo("\n生成されたファイル:")
            for file in generated_files:
                click.echo(f"  - {file}")

            click.echo(
                "\n💡 ヒント: 生成されたファイルをレビューして、"
                "必要に応じて既存のSEEDファイルと置き換えてください。"
            )

        except (DatabaseError, FileNotFoundError, PermissionError):
            # These exceptions will be properly handled by the error handler
            raise
        except Exception as e:
            # Wrap unexpected exceptions
            raise DatabaseError(
                f"SEEDファイル生成中に予期しないエラーが発生しました: {str(e)}",
                {"output_dir": output_dir},
            ) from e


def get_seed_commands() -> list[Command]:
    """SEEDコマンドのリストを返す"""
    return [
        SeedCommands.generate_seeds,
    ]
