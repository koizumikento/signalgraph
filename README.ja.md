# SignalGraph

SignalGraph は、海外のトレンドシグナルを監視し、日本市場向けの事業機会に
翻訳するための小さな CLI / MCP ツールです。

[English README](README.md)

Pydantic Graph と Codex SDK の薄いフロー層として設計しています。

- `uvx` でローカル実行
- 同じフローを MCP tool として公開
- Pydantic モデルで signal contract を固定
- Codex SDK で複数の調査トラックを並列実行
- Markdown または JSON の brief を出力

## インストール

```bash
uvx signalgraph --help
```

ローカル開発中:

```bash
uv run signalgraph --help
```

80% カバレッジゲートを含む検証:

```bash
uv run --extra dev pytest
uv run --extra dev ruff check .
```

## 使い方

トレンドスキャンを実行:

```bash
signalgraph scan "AI agent developer tools"
```

brief をファイルに書き出す:

```bash
signalgraph scan "AI agent developer tools" --out weekly-brief.md
```

日本語で出力:

```bash
signalgraph scan "AI agent developer tools" --language ja
```

JSON 出力:

```bash
signalgraph scan "AI agent developer tools" --format json
```

Web検索と並列数を制御:

```bash
signalgraph scan "healthcare AI" --web-search live --max-parallel 3
```

Codex runtime config を上書き:

```bash
signalgraph scan "AI agents" --codex-config stream_idle_timeout_ms=900000
```

SignalGraph は Codex に既定の 10 分 stream idle timeout を渡します。

```bash
stream_idle_timeout_ms=600000
```

MCP server として実行:

```bash
signalgraph-mcp
```

MCP server は `scan_trends` を公開します。

## 調査トラック

既定のスキャンは5つのトラックで実行します。

- `products`: 海外ローンチ、Product Hunt 的なプロダクトシグナル、スタートアップツール
- `oss`: GitHub / OSS プロジェクト、devtools、実装モメンタム
- `research`: 論文、技術ブレイクスルー、ベンチマーク変化
- `community`: Hacker News、Reddit、開発者・利用者の議論や不満
- `funding`: VC、アクセラレータ、スタートアップ資金調達シグナル

各トラックは構造化された `TrendSignal` レコードを返します。グラフはそれらを
検証、重複排除、スコアリングし、簡潔な brief としてレンダリングします。

各トラックは単なる短いプロンプトではなく、research contract として定義します。
research contract には、情報源の優先順位、採用条件、棄却条件、スコアリング
観点、日本市場向けの翻訳ガイダンス、最大finding数を含めます。これにより、
並列で動く Codex research thread が無制約な検索プロンプトになることを防ぎます。

## Codex 認証

SignalGraph は Codex SDK を使います。そのため、ユーザーが設定済みの Codex
login または認証設定に依存します。SignalGraph は API key を直接管理しません。

## 仕様

初期設計は [docs/SPEC.md](docs/SPEC.md) を参照してください。
