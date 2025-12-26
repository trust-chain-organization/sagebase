"""計測機能を持つLLMサービスラッパー."""

from typing import Any

from langchain.schema import BaseMessage

from src.common.instrumentation import MetricsContext, measure_time
from src.common.logging import get_logger
from src.common.metrics import CommonMetrics, create_histogram
from src.services.llm_service import LLMService


logger = get_logger(__name__)


class InstrumentedLLMService:
    """LLMサービスに計測機能を追加するラッパークラス."""

    def __init__(self, llm_service: LLMService):
        """初期化.

        Args:
            llm_service: ラップするLLMサービスインスタンス
        """
        self._llm_service = llm_service
        self._setup_metrics()

    def _setup_metrics(self):
        """メトリクスの初期化."""
        self.api_calls = CommonMetrics.llm_api_calls_total()
        self.api_duration = CommonMetrics.llm_api_duration()
        self.tokens_used = CommonMetrics.llm_tokens_used()

        # モデル別のメトリクス
        self.model_latency = create_histogram(
            "llm_model_latency_milliseconds",
            "LLM model latency by model name",
            "ms",
        )

        # トークン使用量のヒストグラム
        self.token_histogram = create_histogram(
            "llm_tokens_per_request",
            "Token usage distribution per request",
            "tokens",
        )

    @measure_time(
        metric_name="llm_api_call",
        log_slow_operations=5.0,
    )
    def invoke(
        self,
        messages: list[BaseMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        """LLM APIを呼び出し（計測付き）.

        Args:
            messages: メッセージリスト
            temperature: 温度パラメータ
            max_tokens: 最大トークン数
            **kwargs: その他のパラメータ

        Returns:
            生成されたテキスト
        """
        model_name = getattr(self._llm_service, "model_name", "unknown")

        with MetricsContext(
            operation="llm_invoke",
            labels={
                "model": model_name,
                "temperature": str(temperature or self._llm_service.temperature),
            },
        ):
            # API呼び出し回数をカウント
            self.api_calls.add(
                1,
                attributes={
                    "model": model_name,
                    "operation": "invoke",
                },
            )

            # 実際のAPI呼び出し
            import time

            start_time = time.time()

            try:
                # LLMServiceには直接のinvokeメソッドがないため、
                # メッセージを文字列に変換してpromptとして実行
                # Convert messages to prompt text
                prompt_parts: list[str] = []
                for msg in messages:
                    if hasattr(msg, "content"):
                        content = msg.content  # type: ignore
                        if isinstance(content, str):
                            prompt_parts.append(content)
                        else:
                            prompt_parts.append(str(content))  # type: ignore
                    else:
                        prompt_parts.append(str(msg))
                prompt_text = "\n".join(prompt_parts)

                chain = self._llm_service.create_simple_chain(
                    prompt_template=prompt_text, use_passthrough=False
                )
                result = self._llm_service.invoke_with_retry(chain, {})
                result = str(result.content if hasattr(result, "content") else result)

                # 成功時のメトリクス記録
                elapsed_ms = (time.time() - start_time) * 1000
                self.api_duration.record(
                    elapsed_ms,
                    attributes={
                        "model": model_name,
                        "status": "success",
                    },
                )
                self.model_latency.record(elapsed_ms, attributes={"model": model_name})

                # トークン使用量の推定（文字数ベース）
                # 実際のトークン数はLLMのレスポンスから取得すべきだが、
                # 簡易的に文字数の1/4として推定
                estimated_tokens = len(str(messages)) // 4 + len(result) // 4
                self.tokens_used.add(
                    estimated_tokens,
                    attributes={
                        "model": model_name,
                        "type": "estimated",
                    },
                )
                self.token_histogram.record(
                    estimated_tokens, attributes={"model": model_name}
                )

                logger.info(
                    "LLM API call completed",
                    model=model_name,
                    duration_ms=elapsed_ms,
                    estimated_tokens=estimated_tokens,
                    response_length=len(result),
                )

                return result

            except Exception as e:
                # エラー時のメトリクス記録
                elapsed_ms = (time.time() - start_time) * 1000
                self.api_duration.record(
                    elapsed_ms,
                    attributes={
                        "model": model_name,
                        "status": "error",
                        "error_type": type(e).__name__,
                    },
                )

                logger.error(
                    "LLM API call failed",
                    model=model_name,
                    duration_ms=elapsed_ms,
                    error=str(e),
                    exc_info=True,
                )

                raise

    def generate_from_template(
        self,
        template_name: str,
        context: dict[str, Any],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        """テンプレートからテキスト生成（計測付き）.

        Args:
            template_name: テンプレート名
            context: テンプレートに渡すコンテキスト
            temperature: 温度パラメータ
            max_tokens: 最大トークン数
            **kwargs: その他のパラメータ

        Returns:
            生成されたテキスト
        """
        model_name = getattr(self._llm_service, "model_name", "unknown")

        with MetricsContext(
            operation="llm_generate_from_template",
            labels={
                "model": model_name,
                "template": template_name,
            },
        ):
            # API呼び出し回数をカウント
            self.api_calls.add(
                1,
                attributes={
                    "model": model_name,
                    "operation": "generate_from_template",
                    "template": template_name,
                },
            )

            # generate_from_templateはLLMServiceに存在しないため、
            # invoke_promptを使用
            result = self._llm_service.invoke_prompt(
                prompt_key=template_name, variables=context
            )
            return str(result.content if hasattr(result, "content") else result)

    def __getattr__(self, name: str) -> Any:
        """その他のメソッドは元のサービスに委譲."""
        return getattr(self._llm_service, name)
