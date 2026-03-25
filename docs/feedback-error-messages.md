---
name: feedback-error-messages
description: User wants clear, specific error messages in code - not generic swallowed exceptions
type: feedback
---

Always surface specific error messages in extraction and API code. Don't swallow exceptions silently or show generic "extraction failed" messages. Show the actual error (e.g., "API credits exhausted", "connection refused") so the user can act on it.

**Why:** User was repeatedly blocked by unhelpful "KeyError" messages that hid the real issue (API credits exhausted, .format() bug). Clear error messages would have saved significant debugging time.

**How to apply:** In any try/except block, always print the actual exception message. For API calls specifically, catch and display HTTP status codes and response bodies.
