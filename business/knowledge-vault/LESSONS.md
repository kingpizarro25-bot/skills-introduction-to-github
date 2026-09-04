# Lessons

What happened, the root cause, and what changes because of it. A lesson without a
change is a diary entry.

Format:

```
## <yyyy-mm-dd> — <lesson in one line>
**What happened**
**Root cause** (the actual cause, not the symptom)
**What changes** (the specific rule, agent constraint, or procedure that changed)
**Where that change lives** (file path)
```

---

*No entries yet. First real project failure goes here.*

## 2026-09-04 — Five sessions, five branches, nothing merged

**What happened** While merging the agent structure to `main`, four other unmerged
branches surfaced, each built by a different session between 2026-08-20 and 2026-08-24:
an AI orchestrator (52 files), a biomedical discovery platform (36), a Python runtime
(18), and a revenue plan (2). No session could see any other session's work. One of them,
`pizarro-multi-ai-orchestrator`, is an AI-coordination system — the same category of
thing as Pizarro Studios OS, built three weeks earlier.

**Root cause** Work was done on branches and left unmerged, in a repository whose default
branch was an unrelated tutorial. There was no shared source of truth, so every session
started from nothing and rebuilt its own version of reality. This is not a memory problem
and would not have been fixed by a better prompt — the state simply was not written
anywhere the next session would look.

**What changes**
1. The system now lives on the default branch, so opening the repository shows it.
2. Mission Control's inventory step is not optional: check `projects/` and
   `UNREGISTERED-WORK.md` before commissioning anything. Duplicate work is a stated
   failure condition, and it has now actually occurred once.
3. Work that is not merged is not visible, and work that is not visible does not exist to
   the next session. Push to a shared branch or it is lost.

**Where that change lives** `projects/UNREGISTERED-WORK.md`,
`.claude/agents/mission-control.md` (inventory responsibility), `CLAUDE.md` (system rules).
