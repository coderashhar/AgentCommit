# AgentCommit — Manual Test Checklist

## Authentication
- [ ] Visit the app unauthenticated → redirected to landing page
- [ ] Click "Sign in with GitHub" → GitHub OAuth flow → lands on `/dashboard`
- [ ] Refresh the dashboard while signed in → stays authenticated, no flicker
- [ ] Sign out → redirected to landing page, `/dashboard` no longer accessible

## Profile Analysis
- [ ] Dashboard loads → profile analysis runs automatically → shows languages, experience level, summary
- [ ] Analysis result is cached → revisit dashboard, result appears instantly (no spinner)

## Repo Recommendations
- [ ] Repos appear after profile analysis → each card shows stars, language, match reason
- [ ] All repos match experience tier (beginner shouldn't show microsoft/vscode-level repos)
- [ ] Click a repo card → opens GitHub in a new tab

## Issue Discovery
- [ ] Issues appear below repos → labelled "good first issue" or "help wanted"
- [ ] Issues are unassigned and open
- [ ] Click an issue card → navigates to `/issue/owner/repo/number`

## Saved Issues (M2)
- [ ] Click the bookmark icon on an issue card → icon fills/changes state
- [ ] Refresh the page → bookmarked issues remain bookmarked
- [ ] Click bookmark again → removes the bookmark, persists after refresh
- [ ] Bookmark the same issue twice → no duplicate (idempotent)

## Issue Detail Page
- [ ] Navigate to `/issue/owner/repo/number` → explanation loads with difficulty, estimated time, concepts
- [ ] "View on GitHub" link → correct issue URL opens in new tab
- [ ] Bad URL (e.g. `/issue/bad`) → "Issue not found" message, no crash
- [ ] "Try again" button on error → retries the explanation fetch

## Implementation Planner (M4)
- [ ] On issue detail → click "Generate Implementation Plan" → spinner appears, then plan renders
- [ ] Plan shows: numbered steps, file paths as code chips, complexity badge, risks, edge cases, testing strategy
- [ ] Click the plan header → collapses/expands the card
- [ ] Re-open the same issue → plan loads instantly from cache (no spinner)

## Mentor Agent (M5)
- [ ] On issue detail → click "Ask the Mentor" → chat panel expands
- [ ] Type a question → Enter sends it → mentor responds in 2-5 sentences
- [ ] Send a follow-up referring to the first answer → mentor retains context
- [ ] Shift+Enter → inserts a newline instead of sending
- [ ] Long message (near 2000 chars) → sends successfully
- [ ] Close and reopen the mentor panel → previous messages are gone (UI-only state, expected)

## Commit Message Generator (M6)
- [ ] On issue detail → click "Generate Commit Message" → navigates to `/commit` with repo + issue pre-filled
- [ ] Enter a change description → click generate → conventional commit appears
- [ ] Subject line is ≤72 chars, imperative mood
- [ ] "Copy" button on full message → pastes correctly into a text editor
- [ ] Copy on an alternative subject line → works independently
- [ ] Leave diff blank → still generates (description-only mode)
- [ ] Paste a real `git diff` → subject and type are more precise
- [ ] Navigate to `/commit` directly from navbar → blank form, fully functional
- [ ] Generate without repo filled in → button stays disabled

## Error & Edge Cases
- [ ] Kill the backend → frontend shows error state with "Try again" button, not a blank screen
- [ ] Issue that doesn't exist (e.g. `/issue/owner/repo/99999`) → explanation fails gracefully, fallback shown
- [ ] Very fast network → no race conditions between profile → repos → issues loading sequence
