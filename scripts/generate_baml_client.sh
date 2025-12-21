#!/bin/bash
# BAMLクライアント再生成スクリプト

set -e

echo "🔄 Generating BAML client from baml_src/*.baml files..."

uv run python -c "import sys; sys.argv = ['baml', 'generate', '--from', 'baml_src']; from baml_py import invoke_runtime_cli; invoke_runtime_cli()"

echo "✅ BAML client generated successfully!"
echo ""
echo "Generated files:"
ls -lh baml_client/*.py | awk '{print "  - " $9 " (" $5 ")"}'
echo ""
echo "To verify:"
echo "  grep -n 'MatchSpeaker\\|MatchPolitician' baml_client/async_client.py"
