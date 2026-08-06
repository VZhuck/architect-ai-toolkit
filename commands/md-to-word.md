---
description: "Convert a folder of rule-compliant markdown SAD section files into a single Word document via the md-to-word skill."
argument-hint: "[sourceFolder] [--template <path>] [--output <path>]"
---

# /md-to-word

Parse `$ARGUMENTS`:
1. Extract `--template <path>` if present (the value is the next token).
2. Extract `--output <path>` if present (the value is the next token).
3. Whatever single token remains, if any, is `sourceFolder`. If nothing remains, `sourceFolder` defaults to `sad`.

Examples:
```
/md-to-word                                   # sourceFolder=sad, no explicit template/output
/md-to-word sad
/md-to-word sad --template docs/template.docx
/md-to-word sad --output dist/sad.docx
/md-to-word --template docs/template.docx --output dist/sad.docx
```

Invoke the `md-to-word` skill with the resolved `sourceFolder`, `--template` (or none, if omitted — the skill itself falls back to `.env`'s `SAD_TEMPLATE`), and `--output` (or none, if omitted — the skill defaults to `ai-workflow/md-to-word/<sourceFolder-name>.docx`). This command does not read `.env` directly; the skill's script resolves that fallback. Relay the final output `.docx` path back to the user.
