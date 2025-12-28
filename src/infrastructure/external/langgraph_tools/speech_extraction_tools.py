"""LangGraph tools for speech extraction from minutes.

このモジュールは、議事録からの発言抽出に使用するLangGraphツールを提供します。
発言抽出サブグラフで使用される境界検出・検証ツールを含みます。
"""

import logging
import re

from typing import Any

from langchain_core.tools import tool

from baml_client.async_client import b


logger = logging.getLogger(__name__)


def create_speech_extraction_tools() -> list[Any]:
    """Create LangGraph tools for speech extraction.

    発言抽出サブグラフで使用するツールのリストを作成します。
    境界検出の精度を向上させるため、以下の3つのツールを提供します：
    1. validate_boundary_candidate: 境界候補の妥当性を検証
    2. analyze_context: 境界周辺のコンテキストを分析
    3. verify_boundary: 最終的な境界検証を実行

    Returns:
        List of LangGraph tools
    """

    @tool
    async def validate_boundary_candidate(
        minutes_text: str,
        boundary_position: int,
        context_window: int = 100,
    ) -> dict[str, Any]:
        """Validate a boundary candidate position.

        指定された境界候補位置の妥当性を検証します。
        境界候補の前後のコンテキストを抽出し、BAMLを使用して
        境界検出を再実行することで、候補の信頼度を評価します。

        Args:
            minutes_text: 議事録テキスト全体
            boundary_position: 境界候補の位置（文字インデックス、0-based）
            context_window: 境界前後から抽出するコンテキストのサイズ（文字数）
                           デフォルトは100文字

        Returns:
            Dictionary with:
            - is_valid: 境界候補が妥当かどうか（bool）
            - confidence: 信頼度（0.0-1.0の範囲）
            - boundary_type: 境界の種類（separator_line, speech_start,
              time_marker, none）
            - reason: 判定理由の説明
            - context_before: 境界前のコンテキスト
            - context_after: 境界後のコンテキスト
            - error: エラーメッセージ（エラー時のみ）

        Example:
            >>> result = await validate_boundary_candidate(
            ...     minutes_text="議事録全文...",
            ...     boundary_position=500
            ... )
            >>> print(result["is_valid"])
            True
            >>> print(result["confidence"])
            0.85
        """
        try:
            # 入力バリデーション
            if not minutes_text:
                return {
                    "is_valid": False,
                    "confidence": 0.0,
                    "boundary_type": "none",
                    "reason": "議事録テキストが空です",
                    "context_before": "",
                    "context_after": "",
                    "error": "Empty minutes text",
                }

            if boundary_position < 0 or boundary_position >= len(minutes_text):
                return {
                    "is_valid": False,
                    "confidence": 0.0,
                    "boundary_type": "none",
                    "reason": "境界位置が議事録の範囲外です",
                    "context_before": "",
                    "context_after": "",
                    "error": f"Boundary position {boundary_position} out of range",
                }

            # 境界前後のコンテキストを抽出
            start_pos = max(0, boundary_position - context_window)
            end_pos = min(len(minutes_text), boundary_position + context_window)

            context_before = minutes_text[start_pos:boundary_position]
            context_after = minutes_text[boundary_position:end_pos]

            # 境界候補周辺のテキストを構築（｜境界｜でマーク）
            boundary_text_with_marker = f"{context_before}｜境界｜{context_after}"

            # BAMLを使用して境界検出を実行
            boundary_result = await b.DetectBoundary(boundary_text_with_marker)

            # 結果を評価
            is_valid = (
                boundary_result.boundary_found and boundary_result.confidence >= 0.5
            )

            return {
                "is_valid": is_valid,
                "confidence": boundary_result.confidence,
                "boundary_type": boundary_result.boundary_type,
                "reason": boundary_result.reason,
                "context_before": context_before,
                "context_after": context_after,
            }

        except Exception as e:
            logger.error(
                f"Error validating boundary candidate at "
                f"position {boundary_position}: {e}",
                exc_info=True,
            )
            return {
                "is_valid": False,
                "confidence": 0.0,
                "boundary_type": "none",
                "reason": f"検証中にエラーが発生しました: {str(e)}",
                "context_before": "",
                "context_after": "",
                "error": str(e),
            }

    @tool
    async def analyze_context(
        minutes_text: str,
        boundary_position: int,
        window_size: int = 200,
    ) -> dict[str, Any]:
        """Analyze context around a boundary position.

        境界位置の周辺コンテキストを分析し、境界を示唆する
        パターンや特徴を検出します。

        Args:
            minutes_text: 議事録テキスト全体
            boundary_position: 境界位置（文字インデックス、0-based）
            window_size: 分析するウィンドウサイズ（文字数）
                        デフォルトは200文字

        Returns:
            Dictionary with:
            - context_before: 境界前のコンテキスト
            - context_after: 境界後のコンテキスト
            - has_attendee_list: 出席者リストパターンが検出されたか
            - has_speech_markers: 発言開始マーカーが検出されたか
            - has_separator_line: 区切り線が検出されたか
            - has_time_markers: 時刻表記が検出されたか
            - boundary_indicators: 検出されたインディケーターのリスト
            - error: エラーメッセージ（エラー時のみ）

        Example:
            >>> result = await analyze_context(
            ...     minutes_text="議事録全文...",
            ...     boundary_position=500
            ... )
            >>> print(result["has_speech_markers"])
            True
            >>> print(result["boundary_indicators"])
            ["speech_marker", "separator_line"]
        """
        try:
            # 入力バリデーション
            if not minutes_text:
                return {
                    "context_before": "",
                    "context_after": "",
                    "has_attendee_list": False,
                    "has_speech_markers": False,
                    "has_separator_line": False,
                    "has_time_markers": False,
                    "boundary_indicators": [],
                    "error": "Empty minutes text",
                }

            if boundary_position < 0 or boundary_position >= len(minutes_text):
                return {
                    "context_before": "",
                    "context_after": "",
                    "has_attendee_list": False,
                    "has_speech_markers": False,
                    "has_separator_line": False,
                    "has_time_markers": False,
                    "boundary_indicators": [],
                    "error": f"Boundary position {boundary_position} out of range",
                }

            # コンテキスト抽出
            start_pos = max(0, boundary_position - window_size)
            end_pos = min(len(minutes_text), boundary_position + window_size)

            context_before = minutes_text[start_pos:boundary_position]
            context_after = minutes_text[boundary_position:end_pos]

            # パターン検出
            boundary_indicators = []

            # 1. 出席者リストパターン検出
            # 「出席」「氏名」「役職」などのキーワード + 人名リスト
            attendee_patterns = [
                r"出席.*?[:：]",
                r"氏名.*?[:：]",
                r"役職.*?[:：]",
                r"委員.*?[:：]",
                r"議員.*?[:：]",
            ]
            has_attendee_list = any(
                re.search(pattern, context_before, re.MULTILINE)
                for pattern in attendee_patterns
            )
            if has_attendee_list:
                boundary_indicators.append("attendee_list")

            # 2. 発言開始マーカー検出
            # ○、◆、●などの記号 + 人名/役職
            speech_marker_patterns = [
                r"[○◆●▼]",
                r"^[　\s]*○",
                r"^[　\s]*◆",
            ]
            has_speech_markers = any(
                re.search(pattern, context_after, re.MULTILINE)
                for pattern in speech_marker_patterns
            )
            if has_speech_markers:
                boundary_indicators.append("speech_marker")

            # 3. 区切り線検出
            # ---、===、━━━などの区切り線
            separator_patterns = [
                r"[-─]{3,}",
                r"[=]{3,}",
                r"[━]{3,}",
                r"[―]{3,}",
            ]
            has_separator_line = any(
                re.search(pattern, context_before[-50:], re.MULTILINE)
                or re.search(pattern, context_after[:50], re.MULTILINE)
                for pattern in separator_patterns
            )
            if has_separator_line:
                boundary_indicators.append("separator_line")

            # 4. 時刻表記検出
            # 午前10時、10:00などの時刻表記
            time_patterns = [
                r"午[前後]\d{1,2}時",
                r"\d{1,2}[:：]\d{2}",
                r"\d{1,2}時\d{1,2}分",
            ]
            has_time_markers = any(
                re.search(pattern, context_after[:100]) for pattern in time_patterns
            )
            if has_time_markers:
                boundary_indicators.append("time_marker")

            return {
                "context_before": context_before,
                "context_after": context_after,
                "has_attendee_list": has_attendee_list,
                "has_speech_markers": has_speech_markers,
                "has_separator_line": has_separator_line,
                "has_time_markers": has_time_markers,
                "boundary_indicators": boundary_indicators,
            }

        except Exception as e:
            logger.error(
                f"Error analyzing context at position {boundary_position}: {e}",
                exc_info=True,
            )
            return {
                "context_before": "",
                "context_after": "",
                "has_attendee_list": False,
                "has_speech_markers": False,
                "has_separator_line": False,
                "has_time_markers": False,
                "boundary_indicators": [],
                "error": str(e),
            }

    @tool
    async def verify_boundary(
        minutes_text: str,
        boundary_position: int,
        validation_result: dict[str, Any] | None = None,
        context_analysis: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform final boundary verification.

        境界の最終検証を実行します。
        validation_resultとcontext_analysisを統合し、
        総合的な境界の妥当性を判定します。

        Args:
            minutes_text: 議事録テキスト全体
            boundary_position: 境界位置（文字インデックス、0-based）
            validation_result: validate_boundary_candidateの結果（オプション）
                              指定しない場合は内部で呼び出されます
            context_analysis: analyze_contextの結果（オプション）
                             指定しない場合は内部で呼び出されます

        Returns:
            Dictionary with:
            - is_boundary: 境界として確定したかどうか
            - final_confidence: 最終信頼度（0.0-1.0の範囲）
            - boundary_type: 境界の種類
            - verification_details: 検証の詳細情報（dict）
            - recommendation: 推奨アクション
            - error: エラーメッセージ（エラー時のみ）

        Example:
            >>> result = await verify_boundary(
            ...     minutes_text="議事録全文...",
            ...     boundary_position=500
            ... )
            >>> print(result["is_boundary"])
            True
            >>> print(result["final_confidence"])
            0.82
            >>> print(result["recommendation"])
            "境界として使用可能です"
        """
        try:
            # validation_resultが提供されていない場合は実行
            if validation_result is None:
                validation_result = await validate_boundary_candidate.ainvoke(
                    {
                        "minutes_text": minutes_text,
                        "boundary_position": boundary_position,
                    }
                )

            # context_analysisが提供されていない場合は実行
            if context_analysis is None:
                context_analysis = await analyze_context.ainvoke(
                    {
                        "minutes_text": minutes_text,
                        "boundary_position": boundary_position,
                    }
                )

            # エラーチェック
            if validation_result is not None and "error" in validation_result:
                return {
                    "is_boundary": False,
                    "final_confidence": 0.0,
                    "boundary_type": "none",
                    "verification_details": {
                        "validation_error": validation_result["error"]
                    },
                    "recommendation": "境界検証に失敗しました",
                    "error": validation_result["error"],
                }

            if context_analysis is not None and "error" in context_analysis:
                return {
                    "is_boundary": False,
                    "final_confidence": 0.0,
                    "boundary_type": "none",
                    "verification_details": {
                        "context_analysis_error": context_analysis["error"]
                    },
                    "recommendation": "コンテキスト分析に失敗しました",
                    "error": context_analysis["error"],
                }

            # この時点でvalidation_resultとcontext_analysisは確実にNoneではない
            assert validation_result is not None, "validation_result should not be None"
            assert context_analysis is not None, "context_analysis should not be None"

            # 信頼度の計算
            base_confidence = validation_result.get("confidence", 0.0)

            # コンテキスト分析によるブースト
            confidence_boost = 0.0
            indicators = context_analysis.get("boundary_indicators", [])

            # インディケーターごとにブースト加算
            # 発言マーカー: +0.1
            if "speech_marker" in indicators:
                confidence_boost += 0.1
            # 出席者リスト: +0.15
            if "attendee_list" in indicators:
                confidence_boost += 0.15
            # 区切り線: +0.05
            if "separator_line" in indicators:
                confidence_boost += 0.05
            # 時刻マーカー: +0.05
            if "time_marker" in indicators:
                confidence_boost += 0.05

            # 最終信頼度（最大1.0）
            final_confidence = min(1.0, base_confidence + confidence_boost)

            # 境界タイプの決定
            boundary_type = validation_result.get("boundary_type", "none")
            if boundary_type == "none" and len(indicators) > 0:
                # コンテキスト分析で境界の種類を推測
                if "separator_line" in indicators:
                    boundary_type = "separator_line"
                elif "speech_marker" in indicators:
                    boundary_type = "speech_start"
                elif "time_marker" in indicators:
                    boundary_type = "time_marker"

            # 信頼度閾値（0.7）で境界判定
            is_boundary = final_confidence >= 0.7

            # 推奨アクション
            if is_boundary:
                if final_confidence >= 0.9:
                    recommendation = "高信頼度の境界です。安全に使用できます"
                elif final_confidence >= 0.7:
                    recommendation = "境界として使用可能です"
                else:
                    recommendation = "境界として使用可能ですが、注意が必要です"
            else:
                if final_confidence >= 0.5:
                    recommendation = (
                        "信頼度が低いため、別の境界候補を探すことを推奨します"
                    )
                else:
                    recommendation = "境界として不適切です。別の位置を検討してください"

            # 検証詳細
            verification_details = {
                "base_confidence": base_confidence,
                "confidence_boost": confidence_boost,
                "indicators_detected": len(indicators),
                "indicator_types": indicators,
                "has_attendee_list": context_analysis.get("has_attendee_list", False),
                "has_speech_markers": context_analysis.get("has_speech_markers", False),
                "has_separator_line": context_analysis.get("has_separator_line", False),
                "has_time_markers": context_analysis.get("has_time_markers", False),
                "validation_reason": validation_result.get("reason", ""),
            }

            return {
                "is_boundary": is_boundary,
                "final_confidence": final_confidence,
                "boundary_type": boundary_type,
                "verification_details": verification_details,
                "recommendation": recommendation,
            }

        except Exception as e:
            logger.error(
                f"Error verifying boundary at position {boundary_position}: {e}",
                exc_info=True,
            )
            return {
                "is_boundary": False,
                "final_confidence": 0.0,
                "boundary_type": "none",
                "verification_details": {},
                "recommendation": "境界検証中にエラーが発生しました",
                "error": str(e),
            }

    return [validate_boundary_candidate, analyze_context, verify_boundary]
