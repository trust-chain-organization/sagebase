#!/bin/bash
# Cloud Runサービスのロールバックスクリプト

set -e

# カラー出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 使用方法を表示
show_usage() {
    echo -e "${GREEN}=== Cloud Run Rollback Script ===${NC}"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -l, --list              リビジョン一覧を表示"
    echo "  -r, --revision REVISION 指定したリビジョンにロールバック"
    echo "  -p, --previous          直前のリビジョンにロールバック（デフォルト）"
    echo "  -t, --traffic PERCENT   トラフィック分割（0-100）"
    echo "  -h, --help              このヘルプを表示"
    echo ""
    echo "Environment Variables:"
    echo "  PROJECT_ID              GCPプロジェクトID（必須）"
    echo "  REGION                  デプロイリージョン（デフォルト: asia-northeast1）"
    echo "  SERVICE_NAME            サービス名（デフォルト: sagebase-streamlit）"
    echo ""
    echo "Examples:"
    echo "  # リビジョン一覧を表示"
    echo "  PROJECT_ID=my-project $0 --list"
    echo ""
    echo "  # 直前のリビジョンにロールバック"
    echo "  PROJECT_ID=my-project $0 --previous"
    echo ""
    echo "  # 特定のリビジョンにロールバック"
    echo "  PROJECT_ID=my-project $0 --revision sagebase-streamlit-00005-abc"
    echo ""
    echo "  # トラフィックを50%に分割してロールバック"
    echo "  PROJECT_ID=my-project $0 --revision sagebase-streamlit-00005-abc --traffic 50"
    exit 0
}

# 環境変数の確認
check_env_var() {
    if [ -z "${!1}" ]; then
        echo -e "${RED}Error: $1 is not set${NC}"
        echo "Please set $1 environment variable"
        echo "Run '$0 --help' for usage information"
        exit 1
    fi
}

# リビジョン一覧を表示
list_revisions() {
    echo -e "${GREEN}Fetching revisions for service: ${SERVICE_NAME}${NC}"
    echo ""

    # リビジョン一覧を取得
    REVISIONS=$(gcloud run revisions list \
        --service="$SERVICE_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="table(
            metadata.name:label='REVISION',
            status.conditions[0].lastTransitionTime.date('%Y-%m-%d %H:%M:%S'):label='DEPLOYED',
            status.conditions[0].status:label='READY',
            spec.containers[0].image.basename():label='IMAGE',
            status.traffic:label='TRAFFIC'
        )")

    echo "$REVISIONS"
    echo ""

    # 現在のリビジョンを取得
    CURRENT_REVISION=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="value(status.latestReadyRevisionName)")

    echo -e "${YELLOW}Current active revision: ${CURRENT_REVISION}${NC}"
}

# 直前のリビジョンにロールバック
rollback_to_previous() {
    echo -e "${GREEN}Finding previous revision...${NC}"

    # すべてのリビジョンを取得（デプロイ日時の降順）
    ALL_REVISIONS=$(gcloud run revisions list \
        --service="$SERVICE_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="value(metadata.name)" \
        --sort-by="~metadata.creationTimestamp")

    # 現在のリビジョンを取得
    CURRENT_REVISION=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="value(status.latestReadyRevisionName)")

    echo -e "${YELLOW}Current revision: ${CURRENT_REVISION}${NC}"

    # 直前のリビジョンを見つける
    PREVIOUS_REVISION=""
    FOUND_CURRENT=false

    while IFS= read -r revision; do
        if [ "$FOUND_CURRENT" = true ]; then
            PREVIOUS_REVISION="$revision"
            break
        fi
        if [ "$revision" = "$CURRENT_REVISION" ]; then
            FOUND_CURRENT=true
        fi
    done <<< "$ALL_REVISIONS"

    if [ -z "$PREVIOUS_REVISION" ]; then
        echo -e "${RED}Error: No previous revision found${NC}"
        exit 1
    fi

    echo -e "${GREEN}Previous revision found: ${PREVIOUS_REVISION}${NC}"
    rollback_to_revision "$PREVIOUS_REVISION"
}

# 特定のリビジョンにロールバック
rollback_to_revision() {
    TARGET_REVISION=$1

    echo -e "${YELLOW}Rolling back to revision: ${TARGET_REVISION}${NC}"

    # リビジョンの存在確認
    if ! gcloud run revisions describe "$TARGET_REVISION" \
        --region="$REGION" \
        --project="$PROJECT_ID" > /dev/null 2>&1; then
        echo -e "${RED}Error: Revision ${TARGET_REVISION} not found${NC}"
        exit 1
    fi

    # リビジョンの詳細を表示
    echo -e "${BLUE}Revision details:${NC}"
    gcloud run revisions describe "$TARGET_REVISION" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="table(
            metadata.name:label='REVISION',
            status.conditions[0].lastTransitionTime.date('%Y-%m-%d %H:%M:%S'):label='DEPLOYED',
            spec.containers[0].image.basename():label='IMAGE'
        )"

    echo ""
    echo -e "${YELLOW}WARNING: This will update the service to use revision ${TARGET_REVISION}${NC}"
    read -p "Do you want to continue? (y/N): " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Rollback cancelled${NC}"
        exit 0
    fi

    # トラフィック設定
    TRAFFIC_ARG="--to-revisions=${TARGET_REVISION}=100"
    if [ -n "$TRAFFIC_PERCENT" ]; then
        REMAINING_TRAFFIC=$((100 - TRAFFIC_PERCENT))
        CURRENT_REVISION=$(gcloud run services describe "$SERVICE_NAME" \
            --region="$REGION" \
            --project="$PROJECT_ID" \
            --format="value(status.latestReadyRevisionName)")
        TRAFFIC_ARG="--to-revisions=${TARGET_REVISION}=${TRAFFIC_PERCENT},${CURRENT_REVISION}=${REMAINING_TRAFFIC}"
        echo -e "${YELLOW}Traffic split: ${TARGET_REVISION}=${TRAFFIC_PERCENT}%, ${CURRENT_REVISION}=${REMAINING_TRAFFIC}%${NC}"
    fi

    # ロールバック実行
    echo -e "${GREEN}Executing rollback...${NC}"
    gcloud run services update-traffic "$SERVICE_NAME" \
        $TRAFFIC_ARG \
        --region="$REGION" \
        --project="$PROJECT_ID"

    # 結果確認
    echo ""
    echo -e "${GREEN}=== Rollback Successful! ===${NC}"

    SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="value(status.url)")

    echo -e "Service URL: ${YELLOW}${SERVICE_URL}${NC}"
    echo ""
    echo -e "${GREEN}Current traffic distribution:${NC}"
    gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="table(status.traffic[].revisionName:label='REVISION',status.traffic[].percent:label='TRAFFIC %')"

    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Verify the service: curl ${SERVICE_URL}"
    echo "2. Monitor logs: gcloud run logs tail ${SERVICE_NAME} --region=${REGION} --project=${PROJECT_ID}"
    echo "3. If issues persist, rollback further or redeploy"
}

# デフォルト値設定
REGION="${REGION:-asia-northeast1}"
SERVICE_NAME="${SERVICE_NAME:-sagebase-streamlit}"
ACTION="previous"
TARGET_REVISION=""
TRAFFIC_PERCENT=""

# 引数のパース
while [[ $# -gt 0 ]]; do
    case $1 in
        -l|--list)
            ACTION="list"
            shift
            ;;
        -r|--revision)
            ACTION="revision"
            TARGET_REVISION="$2"
            shift 2
            ;;
        -p|--previous)
            ACTION="previous"
            shift
            ;;
        -t|--traffic)
            TRAFFIC_PERCENT="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_usage
            ;;
    esac
done

# 必須環境変数の確認
check_env_var "PROJECT_ID"

echo -e "${GREEN}=== Cloud Run Rollback Script ===${NC}"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Service Name: $SERVICE_NAME"
echo ""

# GCPプロジェクトの設定
gcloud config set project "$PROJECT_ID" --quiet

# アクション実行
case $ACTION in
    list)
        list_revisions
        ;;
    revision)
        if [ -z "$TARGET_REVISION" ]; then
            echo -e "${RED}Error: Revision name is required${NC}"
            show_usage
        fi
        rollback_to_revision "$TARGET_REVISION"
        ;;
    previous)
        rollback_to_previous
        ;;
esac
