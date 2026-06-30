# SignalGraph

SignalGraph は、海外の最新トレンドシグナルを収集し、日本市場向けの事業機会に
翻訳するための小さな CLI / MCP ツールです。

構成は薄い Python パッケージです。

- Pydantic Graph で調査フローを管理
- Codex SDK で複数トラックを並列調査
- Pydantic モデルで signal schema を固定
- Markdown または JSON で brief を出力
- MCP tool としても公開

## 使い方

```bash
uv run signalgraph scan "AI agent developer tools" --language ja
```

JSON 出力:

```bash
uv run signalgraph scan "healthcare AI" --format json
```

MCP server:

```bash
uv run signalgraph-mcp
```

## Codex 認証

SignalGraph は Codex SDK を使います。認証はユーザーが設定済みの Codex login /
OAuth 認証に依存し、API key を直接扱いません。
