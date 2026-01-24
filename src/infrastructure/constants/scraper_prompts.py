"""Constants for scraper prompts."""

PROPOSAL_EXTRACTION_PROMPT = (
    "以下の政府・議会のウェブページから議案情報を抽出してください。\n"
    "\n"
    "URL: {url}\n"
    "\n"
    "ページ内容:\n"
    "{text_content}\n"
    "\n"
    "以下の情報を抽出してください"
    "（見つからない場合は空文字列を返してください）：\n"
    "- title: 議案名・法案名（タイトル）\n"
    "\n"
    "JSON形式で返してください。"
)

PROPOSAL_EXTRACTION_SYSTEM_PROMPT = (
    "あなたは日本の政府・議会ウェブサイトから情報を抽出する専門家です。"
)
