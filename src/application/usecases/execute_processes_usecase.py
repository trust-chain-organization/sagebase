"""Use case for executing various processes."""

from dataclasses import dataclass
from typing import Any

from src.common.logging import get_logger


logger = get_logger(__name__)


@dataclass
class ProcessExecutionInputDto:
    """Input DTO for process execution."""

    process_type: str
    command: str
    parameters: dict[str, Any] | None = None


@dataclass
class ProcessExecutionOutputDto:
    """Output DTO for process execution."""

    success: bool
    output: str | None = None
    error_message: str | None = None


class ExecuteProcessesUseCase:
    """Use case for executing various processes."""

    def __init__(self):
        """Initialize the use case."""
        pass

    def execute_process(
        self, input_dto: ProcessExecutionInputDto
    ) -> ProcessExecutionOutputDto:
        """Execute a process."""
        try:
            # For now, return a placeholder
            # In a real implementation, this would execute the actual process
            return ProcessExecutionOutputDto(
                success=True,
                output=(
                    f"Process {input_dto.process_type} would be executed "
                    f"with command: {input_dto.command}"
                ),
            )
        except Exception as e:
            logger.error(f"Failed to execute process: {e}")
            return ProcessExecutionOutputDto(success=False, error_message=str(e))

    def get_available_processes(self) -> dict[str, list[dict[str, str]]]:
        """Get available processes grouped by category."""
        return {
            "議事録処理": [
                {
                    "name": "議事録分割処理",
                    "command": (
                        "docker compose -f docker/docker-compose.yml "
                        "exec sagebase uv run python -m src.process_minutes"
                    ),
                    "description": "PDFまたはテキストから議事録を分割して発言を抽出",
                },
                {
                    "name": "発言者抽出",
                    "command": (
                        "docker compose -f docker/docker-compose.yml "
                        "exec sagebase uv run sagebase extract-speakers"
                    ),
                    "description": "議事録から発言者情報を抽出",
                },
                {
                    "name": "発言者マッチング（LLM）",
                    "command": (
                        "docker compose -f docker/docker-compose.yml "
                        "exec sagebase uv run sagebase update-speakers --use-llm"
                    ),
                    "description": "LLMを使用して発言者と政治家をマッチング",
                },
            ],
            "政治家情報": [
                {
                    "name": "政党議員スクレイピング",
                    "command": (
                        "docker compose -f docker/docker-compose.yml "
                        "exec sagebase uv run sagebase scrape-politicians --all-parties"
                    ),
                    "description": "全政党の議員情報をWebサイトから取得",
                },
            ],
            "会議体メンバー": [
                {
                    "name": "会議体メンバー抽出",
                    "command": (
                        "docker compose -f docker/docker-compose.yml "
                        "exec sagebase uv run sagebase "
                        "extract-conference-members --force"
                    ),
                    "description": "会議体メンバーをURLから抽出",
                },
                {
                    "name": "メンバーマッチング",
                    "command": (
                        "docker compose -f docker/docker-compose.yml "
                        "exec sagebase uv run sagebase match-conference-members"
                    ),
                    "description": "抽出したメンバーと政治家をマッチング",
                },
                {
                    "name": "所属関係作成",
                    "command": (
                        "docker compose -f docker/docker-compose.yml "
                        "exec sagebase uv run sagebase create-affiliations"
                    ),
                    "description": "マッチング結果から所属関係を作成",
                },
            ],
            "スクレイピング": [
                {
                    "name": "議事録スクレイピング（京都）",
                    "command": (
                        "docker compose -f docker/docker-compose.yml "
                        "exec sagebase uv run sagebase batch-scrape --tenant kyoto"
                    ),
                    "description": "京都市議会の議事録を一括取得",
                },
                {
                    "name": "議事録スクレイピング（大阪）",
                    "command": (
                        "docker compose -f docker/docker-compose.yml "
                        "exec sagebase uv run sagebase batch-scrape --tenant osaka"
                    ),
                    "description": "大阪市議会の議事録を一括取得",
                },
            ],
            "その他": [
                {
                    "name": "カバレッジ統計",
                    "command": (
                        "docker compose -f docker/docker-compose.yml "
                        "exec sagebase uv run sagebase coverage"
                    ),
                    "description": "開催主体のカバレッジ統計を表示",
                },
                {
                    "name": "データベースバックアップ",
                    "command": (
                        "docker compose -f docker/docker-compose.yml "
                        "exec sagebase uv run sagebase database backup"
                    ),
                    "description": "データベースをバックアップ",
                },
            ],
        }
