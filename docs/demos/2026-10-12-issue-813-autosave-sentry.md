# A chapter that could not be saved is reported (#813)

*2026-10-12T20:20:46Z by Showboat 0.6.1*
<!-- showboat-id: 08604686-0145-41ea-afe1-d21ce26882c8 -->

When a chapter fails to save, the editor says so and keeps the text in a local backup. Nobody else was told: the failure went to the browser console. This demo runs the real backend and the real frontend from main and from this branch, with the frontend's Sentry pointed at a stand-in on this machine, opens a chapter in a real Chromium, stops the backend and types a sentence. Autosave then fails every three seconds for twelve seconds.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo813/env.sh; echo "main:   $(git -C $MAIN log --oneline -1 | cut -c1-7)"; echo "branch: $(git -C $WT rev-parse --abbrev-ref HEAD)"; echo "the sentence typed: $TYPED"
```

```output
main:   0afaf98
branch: feature/issue-813-autosave-sentry
the sentence typed: MANUSCRIPT the keeper climbed the stairs
```

Before. The writer is told and the text is kept, as it should be. Sentry is told nothing.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo813/env.sh; backend; frontend $MAIN; bash $D/browser-probe.sh; stop
```

```output
the backend is stopped; the writer types a sentence and autosave tries for 12 seconds
the page says: Failed to auto-save. Content backed up locally.
local backup:  holds the sentence: true
reports the browser posted to Sentry: 0
the sentence is in what was posted: False
```

After. The same for the writer. Sentry gets one report for the run of failures, tagged so it can be found, and the sentence is not in it. Autosave tried several times in those twelve seconds; a report for each would be one every three seconds from every open editor for as long as the backend is away.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo813/env.sh; backend; frontend $WT; bash $D/browser-probe.sh; stop
```

```output
the backend is stopped; the writer types a sentence and autosave tries for 12 seconds
the page says: Failed to auto-save. Content backed up locally.
local backup:  holds the sentence: true
reports the browser posted to Sentry: 1
  TypeError: Failed to fetch (localhost:8113) | tags: {'feature': 'autosave', 'operation': 'auto-save'}
the sentence is in what was posted: False
```

The same behaviour as tests: an autosave, a save the writer asked for, a backup that could not be written, a backup that could not be restored, leaving a chapter with an unsaved edit, and a conflict, which is not a failure and is not reported.

```bash
cd /home/frankbria/projects/worktrees/issue-813-autosave-sentry/frontend && npx jest src/components/chapters/__tests__/ChapterEditor.reporting.test.tsx 2>&1 | grep -E '^Tests:' | sed -E 's/ +/ /g'
```

```output
Tests: 9 passed, 9 total
```
