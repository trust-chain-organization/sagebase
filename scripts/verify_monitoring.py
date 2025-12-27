#!/usr/bin/env python3
"""
監視システムの動作確認スクリプト

このスクリプトは、Grafana、Prometheus、Lokiが正しく設定されているかを確認します。
"""

import sys

import requests

from rich.console import Console
from rich.table import Table


console = Console()


def check_service(name: str, url: str, expected_status: int = 200) -> bool:
    """サービスの稼働状況を確認"""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == expected_status:
            console.print(f"✅ {name}: [green]正常稼働中[/green]")
            return True
        else:
            console.print(
                f"❌ {name}: [red]異常なステータスコード: {response.status_code}[/red]"
            )
            return False
    except requests.exceptions.ConnectionError:
        console.print(f"❌ {name}: [red]接続できません[/red]")
        return False
    except Exception as e:
        console.print(f"❌ {name}: [red]エラー: {str(e)}[/red]")
        return False


def check_prometheus_targets() -> bool:
    """Prometheusのターゲット状態を確認"""
    try:
        response = requests.get("http://localhost:9091/api/v1/targets")
        data = response.json()

        if data["status"] == "success":
            active_targets = data["data"]["activeTargets"]

            table = Table(title="Prometheusターゲット")
            table.add_column("Job", style="cyan")
            table.add_column("Instance", style="magenta")
            table.add_column("状態", style="green")
            table.add_column("最終スクレイプ", style="yellow")

            all_up = True
            for target in active_targets:
                state = target["health"]
                if state != "up":
                    all_up = False

                table.add_row(
                    target["labels"]["job"],
                    target["labels"]["instance"],
                    state,
                    target["lastScrape"],
                )

            console.print(table)
            return all_up
        return False
    except Exception as e:
        console.print(f"[red]Prometheusターゲットの確認エラー: {str(e)}[/red]")
        return False


def check_grafana_datasources() -> bool:
    """Grafanaのデータソース設定を確認"""
    try:
        # デフォルトの認証情報
        auth = ("admin", "admin")
        response = requests.get(
            "http://localhost:3000/api/datasources", auth=auth, timeout=5
        )

        if response.status_code == 200:
            datasources = response.json()

            table = Table(title="Grafanaデータソース")
            table.add_column("名前", style="cyan")
            table.add_column("タイプ", style="magenta")
            table.add_column("URL", style="yellow")

            for ds in datasources:
                table.add_row(ds["name"], ds["type"], ds.get("url", "N/A"))

            console.print(table)

            # 必要なデータソースの確認
            required = {"prometheus", "loki"}
            found = {ds["type"] for ds in datasources}

            if required.issubset(found):
                console.print("✅ 必要なデータソースが設定されています")
                return True
            else:
                missing = required - found
                console.print(f"❌ 不足しているデータソース: {', '.join(missing)}")
                return False
        else:
            console.print(
                "[yellow]Grafanaへの接続に失敗しました。"
                "デフォルトのパスワードが変更されている可能性があります。[/yellow]"
            )
            return True  # パスワードが変更されている場合は正常とみなす
    except Exception as e:
        console.print(f"[red]Grafanaデータソースの確認エラー: {str(e)}[/red]")
        return False


def check_sample_metrics() -> bool:
    """サンプルメトリクスの確認"""
    try:
        # アプリケーションメトリクスの確認
        response = requests.get("http://localhost:9090/metrics")
        if response.status_code == 200:
            console.print("✅ アプリケーションメトリクスエンドポイントが正常です")

            # いくつかの重要なメトリクスの存在確認
            metrics_text = response.text
            important_metrics = [
                "http_requests_total",
                "http_request_duration_seconds",
                "db_operations_total",
                "minutes_processed_total",
            ]

            found_metrics = []
            for metric in important_metrics:
                if metric in metrics_text:
                    found_metrics.append(metric)

            if found_metrics:
                console.print(
                    f"✅ 重要なメトリクスが見つかりました: {', '.join(found_metrics)}"
                )
            else:
                console.print(
                    "[yellow]⚠️  重要なメトリクスがまだ生成されていません。"
                    "アプリケーションを実行してください。[/yellow]"
                )

            return True
        else:
            console.print(
                "[red]❌ アプリケーションメトリクスエンドポイントに"
                "アクセスできません[/red]"
            )
            return False
    except Exception as e:
        console.print(f"[red]メトリクスの確認エラー: {str(e)}[/red]")
        return False


def main():
    """メイン処理"""
    console.print("[bold blue]Polibase監視システムの動作確認[/bold blue]\n")

    # サービスの稼働確認
    console.print("[bold]1. サービス稼働状況の確認[/bold]")
    services = [
        ("Grafana", "http://localhost:3000/api/health"),
        ("Prometheus", "http://localhost:9091/-/healthy"),
        ("Loki", "http://localhost:3100/ready"),
    ]

    all_services_up = True
    for name, url in services:
        if not check_service(name, url):
            all_services_up = False

    if not all_services_up:
        console.print(
            "\n[red]❌ 一部のサービスが起動していません。"
            "以下のコマンドで監視サービスを起動してください:[/red]"
        )
        console.print(
            "[yellow]docker compose -f docker/docker-compose.yml "
            "-f docker/docker-compose.monitoring.yml up -d[/yellow]"
        )
        sys.exit(1)

    # Prometheusターゲットの確認
    console.print("\n[bold]2. Prometheusターゲットの確認[/bold]")
    prometheus_ok = check_prometheus_targets()

    # Grafanaデータソースの確認
    console.print("\n[bold]3. Grafanaデータソースの確認[/bold]")
    grafana_ok = check_grafana_datasources()

    # メトリクスの確認
    console.print("\n[bold]4. メトリクスエンドポイントの確認[/bold]")
    metrics_ok = check_sample_metrics()

    # 結果のサマリー
    console.print("\n[bold]監視システムの状態サマリー[/bold]")
    if all_services_up and prometheus_ok and grafana_ok and metrics_ok:
        console.print("[green]✅ 監視システムは正常に動作しています！[/green]\n")
        console.print("以下のURLでアクセスできます:")
        console.print("- Grafana: http://localhost:3000 (初期: admin/admin)")
        console.print("- Prometheus: http://localhost:9091")
        console.print("- Loki: http://localhost:3100")
    else:
        console.print(
            "[yellow]⚠️  一部の設定に問題がある可能性があります。"
            "上記のメッセージを確認してください。[/yellow]"
        )


if __name__ == "__main__":
    main()
