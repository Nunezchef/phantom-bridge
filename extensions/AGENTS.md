# EXTENSIONS MODULE

## OVERVIEW
A0 extension hooks — numeric prefix filenames control load order. Injects bridge awareness into A0's system prompt, patches browser profile sharing, and provides tool documentation.

## STRUCTURE
```
extensions/
├── system_prompt/
│   └── _45_browser_bridge.py    # Load order 45 — injects bridge context into A0's system prompt
├── python/
│   └── message_loop_start/
│       └── _30_browser_bridge_profile.py  # Load order 30 — monkeypatches browser_agent.State
├── prompts/
│   ├── agent.system.tool.browser_bridge.md    # Tool usage docs for A0
│   ├── agent.system.tool.bridge_auth.md
│   ├── agent.system.tool.bridge_health.md
│   ├── agent.system.tool.bridge_record.md
│   ├── agent.system.tool.bridge_replay.md
│   └── agent.system.tool.bridge_sitemap.md
└── webui/
    ├── modal-shell-end/           # Injects bridge modal into A0's UI
    └── chat-input-bottom-actions-end/  # Injects bridge button into chat bar
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Profile sharing (CRITICAL) | `python/message_loop_start/_30_browser_bridge_profile.py` | Monkeypatches `State.get_user_data_dir()` |
| System prompt injection | `system_prompt/_45_browser_bridge.py` | Adds bridge awareness to A0 |
| Tool documentation | `prompts/` | One `.md` per tool — consumed by A0 |
| UI injection | `webui/` | Modal + chat bar button injection |

## CONVENTIONS
- **Load order:** Numeric prefix `_30_`, `_45_` in filenames — lower number = earlier execution
- **Profile patch:** `_30_` runs first to ensure profile dir is set before A0's browser agent starts
- **Prompt injection:** `_45_` runs after profile patch — adds bridge context to system prompt
- **Prompt files:** Named `agent.system.tool.<tool_name>.md` — A0 auto-discovers these
- **WebUI hooks:** Directory names indicate injection points in A0's template (e.g., `modal-shell-end`)

## ANTI-PATTERNS
- **NEVER** change numeric prefixes without understanding load order dependencies
- **DO NOT** replace A0's system prompt — only append/additive injection
- **DO NOT** remove the `__del__` patch in `_30_browser_bridge_profile.py` — prevents profile deletion

## NOTES
- The profile patch is the most critical integration — without it, A0's browser agent uses an ephemeral profile
- System prompt injection is additive: reads existing prompt, appends bridge context
- WebUI extensions use A0's template injection system — directory name = injection target
