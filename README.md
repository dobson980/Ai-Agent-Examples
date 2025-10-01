<div align="center">

# 🧠 AI Agent Examples

Minimal, readable Python examples demonstrating different OpenAI Chat Completions agent patterns: basic text generation, structured output enforcement, and function (tool) calling with a conversational loop.

</div>

## ✨ Agents Included

| Agent | File | Highlights |
|-------|------|-----------|
| Haiku Generator | `src/agents/basic.py` | Smallest example; shows prompt + token usage logging. |
| Compliance Alert Extractor | `src/agents/structured.py` | Pydantic `response_format` parsing into a typed model. |
| Weather Tool Chat | `src/agents/tools.py` | Multi-turn function calling, city name to temperature in °F, cumulative token accounting. |

## 🚀 Quick Start

```bash
git clone <your-fork-or-this-repo-url>
cd Ai-Agent-Examples
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # (create your .env if example provided; otherwise create manually)
```

Create a `.env` file with your OpenAI key:

```bash
echo "OPENAI_API_KEY=sk-REPLACE_ME" > .env
```

> The repo's `.gitignore` already ignores `.env`, virtual environments, and Python build artifacts.

## 📦 Dependencies

Core libraries (from `requirements.txt`):

```
openai>=1.0.0
pydantic>=2.0.0
python-dotenv>=1.0.0
```

Optional (already in stdlib or pulled indirectly):
* `requests` (used in the weather tool; install manually if not present)

Install (ensuring venv is active):

```bash
pip install -r requirements.txt
pip install requests  # only if missing
```

## 🔐 Environment Variables

| Name | Required | Purpose |
|------|----------|---------|
| `OPENAI_API_KEY` | Yes | Authentication for OpenAI API calls. |

Load automatically via `python-dotenv` when scripts start.

## 🛠 Running Each Agent

Ensure your virtual environment is activated and `.env` present.

### 1. Haiku Generator
```bash
python -m src.agents.basic
```
Outputs a haiku + token usage summary.

### 2. Compliance Alert Extractor
```bash
python -m src.agents.structured
```
Parses a device/compliance incident snippet into a strongly typed Pydantic model and prints pretty JSON + token usage.

### 3. Weather Tool Chat (Function Calling)
```bash
python -m src.agents.tools
```
Then interact:
```
City> San Diego
City> Paris, France
City> /exit
```
Shows per-turn token usage (`[usage:first]`, `[usage:second]`) and a final aggregate summary. Commands: `/help`, `/exit`, `exit`, `quit`, `:q` or blank line.

## 🧩 How the Tool Calling Flow Works

1. First call: model returns a `tool_calls` entry indicating it wants `get_weather_by_city` with arguments.
2. Local code runs the public geocoding + weather APIs, trims output to essentials (temperature in °F).
3. Second call: sends back an assistant stub + tool role message containing JSON result.
4. Model responds with a concise natural-language summary.
5. Code aggregates tokens across turns.

## 🗂 Project Structure (excerpt)

```
src/
	agents/
		basic.py        # Haiku generation
		structured.py   # Structured Pydantic response
		tools.py        # Conversational weather tool agent
requirements.txt
.gitignore
README.md
```

## 🧪 Testing Ideas (Not Included Yet)

Potential lightweight tests you could add:
* Mock OpenAI responses to validate parsing.
* Mock HTTP (requests) for the weather tool (e.g. with `responses`).
* Schema regression test for `ComplianceAlert` model.

## 📈 Token Usage Notes

* Tools agent logs both first (tool call) and second (summary) turn tokens.
* Structured agent shows reasoning tokens if the model returns them.
* Consider trimming tool JSON further or caching city lookups if cost matters.

## 🔄 Python Version & SSL Warning

If you see `NotOpenSSLWarning` (LibreSSL vs OpenSSL) on macOS system Python, consider upgrading:
```bash
brew install python@3.11
```
Then recreate the virtual environment with the newer interpreter.

## ❓ Troubleshooting

| Issue | Fix |
|-------|-----|
| `OPENAI_API_KEY not set` | Create `.env` with the key or export it before running. |
| 400 Missing tools[0].function | Ensure `tools` list uses correct `{"type":"function","function":{...}}` shape. |
| Function object not JSON serializable | Only send schema/metadata to API, never Python callables. |
| Blank tool result | Public API rate or network issue; retry. |

## 🛡 License

MIT — see `LICENSE`.

## 🤝 Contributing

Small focused PRs welcome (docs, tests, more agent patterns). Keep examples concise.

---
Feel free to open an issue if you’d like additional agent patterns (retrieval, streaming, image + text, etc.).