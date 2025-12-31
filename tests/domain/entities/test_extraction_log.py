"""抽出ログエンティティのテスト。"""

from tests.fixtures.entity_factories import create_extraction_log

from src.domain.entities.extraction_log import EntityType, ExtractionLog


class TestExtractionLog:
    """ExtractionLogエンティティのテストケース。"""

    def test_create_entity(self):
        """抽出ログエンティティを作成できる。"""
        entity = ExtractionLog(
            entity_type=EntityType.POLITICIAN,
            entity_id=123,
            pipeline_version="gemini-2.0-flash-v1",
            extracted_data={"name": "テスト太郎", "party": "テスト党"},
            confidence_score=0.95,
            extraction_metadata={
                "model_name": "gemini-2.0-flash",
                "token_count_input": 100,
                "token_count_output": 50,
                "processing_time_ms": 1500,
            },
        )

        assert entity.entity_type == EntityType.POLITICIAN
        assert entity.entity_id == 123
        assert entity.pipeline_version == "gemini-2.0-flash-v1"
        assert entity.extracted_data == {"name": "テスト太郎", "party": "テスト党"}
        assert entity.confidence_score == 0.95
        assert entity.extraction_metadata["model_name"] == "gemini-2.0-flash"
        assert entity.extraction_metadata["token_count_input"] == 100
        assert entity.extraction_metadata["token_count_output"] == 50
        assert entity.extraction_metadata["processing_time_ms"] == 1500

    def test_create_entity_minimal(self):
        """最小限のパラメータで抽出ログエンティティを作成できる。"""
        entity = ExtractionLog(
            entity_type=EntityType.SPEAKER,
            entity_id=456,
            pipeline_version="gemini-1.5-flash-v1",
            extracted_data={"speaker_name": "発言者A"},
        )

        assert entity.entity_type == EntityType.SPEAKER
        assert entity.entity_id == 456
        assert entity.pipeline_version == "gemini-1.5-flash-v1"
        assert entity.extracted_data == {"speaker_name": "発言者A"}
        assert entity.confidence_score is None
        assert entity.extraction_metadata == {}

    def test_property_model_name(self):
        """メタデータからモデル名を取得できる。"""
        entity = ExtractionLog(
            entity_type=EntityType.STATEMENT,
            entity_id=789,
            pipeline_version="gemini-2.0-flash-v1",
            extracted_data={"statement": "テスト発言"},
            extraction_metadata={"model_name": "gemini-2.0-flash"},
        )

        assert entity.model_name == "gemini-2.0-flash"

    def test_property_model_name_none(self):
        """モデル名がメタデータにない場合はNoneを返す。"""
        entity = ExtractionLog(
            entity_type=EntityType.STATEMENT,
            entity_id=789,
            pipeline_version="gemini-2.0-flash-v1",
            extracted_data={"statement": "テスト発言"},
        )

        assert entity.model_name is None

    def test_property_token_count_input(self):
        """メタデータから入力トークン数を取得できる。"""
        entity = ExtractionLog(
            entity_type=EntityType.CONFERENCE_MEMBER,
            entity_id=101,
            pipeline_version="gemini-2.0-flash-v1",
            extracted_data={"member_name": "委員A"},
            extraction_metadata={"token_count_input": 200},
        )

        assert entity.token_count_input == 200

    def test_property_token_count_output(self):
        """メタデータから出力トークン数を取得できる。"""
        entity = ExtractionLog(
            entity_type=EntityType.PARLIAMENTARY_GROUP_MEMBER,
            entity_id=202,
            pipeline_version="gemini-2.0-flash-v1",
            extracted_data={"group_member": "議員B"},
            extraction_metadata={"token_count_output": 150},
        )

        assert entity.token_count_output == 150

    def test_property_processing_time_ms(self):
        """メタデータから処理時間を取得できる。"""
        entity = ExtractionLog(
            entity_type=EntityType.POLITICIAN,
            entity_id=303,
            pipeline_version="gemini-2.0-flash-v1",
            extracted_data={"name": "政治家C"},
            extraction_metadata={"processing_time_ms": 2000},
        )

        assert entity.processing_time_ms == 2000

    def test_str_representation(self):
        """文字列表現が正しい。"""
        entity = ExtractionLog(
            entity_type=EntityType.SPEAKER,
            entity_id=456,
            pipeline_version="gemini-2.0-flash-v1",
            extracted_data={"speaker": "発言者D"},
        )

        result = str(entity)
        assert "speaker" in result
        assert "456" in result
        assert "gemini-2.0-flash-v1" in result

    def test_repr_representation(self):
        """repr表現が正しい。"""
        entity = ExtractionLog(
            entity_type=EntityType.STATEMENT,
            entity_id=789,
            pipeline_version="gemini-2.0-flash-v1",
            extracted_data={"statement": "発言内容"},
            confidence_score=0.88,
            id=999,
        )

        result = repr(entity)
        assert "ExtractionLog" in result
        assert "id=999" in result
        assert "entity_type=EntityType.STATEMENT" in result
        assert "entity_id=789" in result
        assert "pipeline_version=gemini-2.0-flash-v1" in result
        assert "confidence_score=0.88" in result

    def test_all_entity_types(self):
        """全てのエンティティタイプが使用できる。"""
        entity_types = [
            EntityType.STATEMENT,
            EntityType.POLITICIAN,
            EntityType.SPEAKER,
            EntityType.CONFERENCE_MEMBER,
            EntityType.PARLIAMENTARY_GROUP_MEMBER,
        ]

        for entity_type in entity_types:
            entity = ExtractionLog(
                entity_type=entity_type,
                entity_id=1,
                pipeline_version="test-v1",
                extracted_data={"test": "data"},
            )
            assert entity.entity_type == entity_type

    def test_confidence_score_range(self):
        """信頼度スコアが正しく設定される。"""
        # 最小値
        entity_min = ExtractionLog(
            entity_type=EntityType.POLITICIAN,
            entity_id=1,
            pipeline_version="test-v1",
            extracted_data={"test": "data"},
            confidence_score=0.0,
        )
        assert entity_min.confidence_score == 0.0

        # 最大値
        entity_max = ExtractionLog(
            entity_type=EntityType.POLITICIAN,
            entity_id=2,
            pipeline_version="test-v1",
            extracted_data={"test": "data"},
            confidence_score=1.0,
        )
        assert entity_max.confidence_score == 1.0

        # 中間値
        entity_mid = ExtractionLog(
            entity_type=EntityType.POLITICIAN,
            entity_id=3,
            pipeline_version="test-v1",
            extracted_data={"test": "data"},
            confidence_score=0.75,
        )
        assert entity_mid.confidence_score == 0.75

    def test_confidence_score_allows_out_of_range_values(self):
        """信頼度スコアは0-1の範囲外の値も許容する。

        LLMからの生の値を保持するため、範囲外の値でもエラーにならない。
        バリデーションは上位層（ユースケース等）で行う設計。
        """
        # 負の値
        entity_negative = ExtractionLog(
            entity_type=EntityType.POLITICIAN,
            entity_id=1,
            pipeline_version="test-v1",
            extracted_data={"test": "data"},
            confidence_score=-0.5,
        )
        assert entity_negative.confidence_score == -0.5

        # 1.0を超える値
        entity_over = ExtractionLog(
            entity_type=EntityType.POLITICIAN,
            entity_id=2,
            pipeline_version="test-v1",
            extracted_data={"test": "data"},
            confidence_score=1.5,
        )
        assert entity_over.confidence_score == 1.5

    def test_empty_extracted_data(self):
        """空のextracted_dataでエンティティを作成できる。"""
        entity = ExtractionLog(
            entity_type=EntityType.STATEMENT,
            entity_id=1,
            pipeline_version="test-v1",
            extracted_data={},
        )
        assert entity.extracted_data == {}

    def test_inheritance_from_base_entity(self):
        """BaseEntityの継承が正しく機能する。"""
        entity1 = ExtractionLog(
            entity_type=EntityType.POLITICIAN,
            entity_id=1,
            pipeline_version="test-v1",
            extracted_data={},
            id=42,
        )
        entity2 = ExtractionLog(
            entity_type=EntityType.SPEAKER,  # 異なるタイプ
            entity_id=999,  # 異なるentity_id
            pipeline_version="different-v1",
            extracted_data={"different": "data"},
            id=42,  # 同じid
        )
        # BaseEntityの__eq__はidのみで比較
        assert entity1 == entity2
        assert hash(entity1) == hash(entity2)

    def test_created_at_updated_at_from_base_entity(self):
        """BaseEntityからcreated_at/updated_atを継承している。"""
        entity = ExtractionLog(
            entity_type=EntityType.POLITICIAN,
            entity_id=1,
            pipeline_version="test-v1",
            extracted_data={},
        )
        assert hasattr(entity, "created_at")
        assert hasattr(entity, "updated_at")
        assert entity.created_at is None  # 初期値
        assert entity.updated_at is None  # 初期値

    def test_create_with_factory(self):
        """ファクトリ関数でエンティティを作成できる。"""
        entity = create_extraction_log()
        assert entity.entity_type == EntityType.POLITICIAN
        assert entity.entity_id == 123
        assert entity.pipeline_version == "gemini-2.0-flash-v1"
        assert entity.extracted_data == {"name": "テスト太郎"}

    def test_create_with_factory_override(self):
        """ファクトリ関数でパラメータを上書きできる。"""
        entity = create_extraction_log(
            entity_type=EntityType.SPEAKER,
            entity_id=999,
            confidence_score=0.85,
        )
        assert entity.entity_type == EntityType.SPEAKER
        assert entity.entity_id == 999
        assert entity.confidence_score == 0.85
