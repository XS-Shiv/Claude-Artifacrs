---
name: dailypush-x
description: Generate one day's X (Twitter) threads, two a day of 3-5 tweets each, into a day-N folder. Slot A threads one of the user's S or A tier Medium articles; slot B threads current product management, design or AI news. Each piece goes through brainstorm (Exa, Firecrawl, Apify, Medium library), draft (marketing skills) and audit before it is marked ready. Use for /dailypush-x, "today's tweets", "make day N", or the daily X content run.
---

# dailypush-x

Make the day's two X threads, check them, and leave them in `day-N/` ready for approval and posting. This skill never posts to X itself. The n8n workflow "dailypush-x: Post to X" posts audited threads from the queue at 14:00 and 20:00 IST (see Step 5), so the audit is the last check before a thread goes out.

## Setup and inputs

**Content root.** Use the folder the user names. Otherwise use `x-content/` at the root of the XS-Shiv/Claude-Artifacrs checkout, on branch `dailypush-x` (the public branch the n8n workflow reads through raw.githubusercontent.com). Everything below is relative to the content root.

**The Medium library lives in Notion Memory**, so it survives across sessions. It holds only the S and A tier essays (11 S, 43 A out of 113, rated 2026-10-25), in a ranked posting queue.

- Page: "Medium S/A articles", https://app.notion.com/p/408b760b3c5081169057f6f4079c4fda (a Work memory). Fetch it by that URL. If the fetch fails, find it with Notion memory search for "Medium S/A articles". Read `notion://docs/memory` once per session before the first memory write.
- Columns: `queue | tier | title | url | pillar | why it works | last_posted`. `pillar` is `design/AI` or `web3`. The full rating of all 113 essays, B and C included, is the artifact https://claude.ai/artifact/RQRdnXit63m3hiLm1NJq1m.
- If the Notion connector is not connected, use `medium-library.md` in the content root instead, in the same format.
- If neither exists, build it first (Step 0).

**Files in the content root (create if missing):**

| File | What it holds | If missing |
|---|---|---|
| `voice.md` | The user's voice rules | Look for `.agents/product-marketing.md` or `.claude/product-marketing.md` first. If neither exists, use the defaults in `references/thread-format.md` and say so in `summary.md`. |
| `posted.json` | Every thread already made: date, slot, topic, source URL | Start an empty list `[]` |
| `queue.json` | What the n8n poster reads: one entry per READY thread (`id`, `day`, `slot`, `dir`, `status`, `created`, `title`) | Start an empty list `[]` |

**Which day.** If the user names a day ("day 4"), use it. Otherwise N = highest existing `day-N` + 1. If `day-N/` already exists, do not overwrite it. Ask before replacing anything.

**The two slots:**

| Slot | Source | Default time |
|---|---|---|
| A — `piece-1-medium` | The next essay in the Medium library's queue | Morning |
| B — `piece-2-industry` | One current story or idea from product management, design or AI | Evening |

Keep posting times at least 60 minutes apart (author-diversity decay on X), and at times the user can reply in the first 30 minutes.

## Output layout

```
day-N/
  brief.md                 date, slot times, brainstorm notes and sources for both pieces
  piece-1-medium/
    thread.md              the thread as it will read, with character counts
    thread.json            {"title", "link", "tweets": [...]} (same shape medium-threads/thread.py reads)
    image-prompts.md       the image's metaphor, which tweet it goes on, and the house style
    images/hook.svg        the illustration, drawn as SVG
    images/hook.png        the 1600x900 render the poster attaches to tweet 1
    audit.md               the checklist with PASS/FAIL per line and the final status
  piece-2-industry/
    (same files)
  summary.md               both pieces, their status, and anything the user must do
```

## Step 0: Build or refresh the Medium library

Run this when the library does not exist, when the user asks to re-rate, or when the RSS feed has an article newer than the library's "Last rated" date.

1. Collect articles as described in `references/tier-rubric.md`. Read each one in full.
2. Score each on the rubric and assign S, A, B or C. Show the user the full scored table, B and C included, before saving.
3. Save only S and A rows to the library (Notion memory page from `references/medium-library-template.md`, or `medium-library.md`). Number the queue S first, then A, alternating design/AI and Web3 rows where possible. Append new essays after the last queue number rather than renumbering, so rows already posted keep their place. Keep existing `last_posted` values. Drop rows that fall below A on a re-rate.
4. If no article can be read (for example medium.com is blocked), stop and ask the user for the article links or to allow medium.com. Never fill the library with guessed tiers.

## Step 1: Brainstorm

Do this separately for each piece. Write the notes into `brief.md`.

**Tools.** Use the Exa, Firecrawl and Apify connectors (tool names `mcp__Exa__*`, `mcp__Firecrawl__*`, `mcp__Apify__*`; load them with ToolSearch). If one is missing, use WebSearch and WebFetch for that job instead and write "fallback: <tool>" in `brief.md`. Never stop the run because a connector is missing. `references/sources.md` lists which tool does which job, the Apify actor to use, and the source list.

**Slot A (Medium):**
1. Read the Medium library and `posted.json`. Take the row with the lowest `queue` number whose `last_posted` is empty and whose URL is not in `posted.json`. The queue already puts S before A and alternates design/AI with Web3, so do not reorder it. If the user names an essay, use that one instead. Once every row has a `last_posted`, start again from the oldest `last_posted` that is at least 90 days ago; if none is, tell the user the queue is used up and suggest a re-rate (Step 0).
2. Fetch the full article (Firecrawl scrape, else WebFetch on the URL). If medium.com cannot be reached from the session, stop slot A and tell the user to allow medium.com in the environment's network settings or paste the essay text. Never draft a Medium thread from the title and the "why it works" line alone.
3. Pull 5-8 "content atoms": a claim, a story, a number, a framework, a contrarian line. Quote them with the paragraph they came from.
4. Use Exa to find one fresh angle: a recent news item, data point or post that makes the article timely now. Note it with its URL.
5. Pick one angle for the thread and say why in one line.

**Slot B (industry):**
1. Use Exa (search, last 7 days) and Apify (X or Reddit scrape of the accounts and subreddits in `references/sources.md`) to collect 8-12 candidate stories in product management, design and AI.
2. Drop any whose topic or URL is already in `posted.json`, or that overlaps today's slot A angle.
3. Score each 1-5 on: relevance to the user's pillars, freshness, whether the user has a real point of view on it, and "would someone DM this to a friend". Keep the top one.
4. Read the primary source in full (Firecrawl, else WebFetch). Never thread from a headline or a secondary summary alone.
5. Write the user's take in one sentence. If there is no take beyond "this happened", pick the next story.

## Step 2: Draft

Load these skills and use them as instructed. If one is not installed, follow `references/thread-format.md` alone.

| Skill | Use it for |
|---|---|
| `social` | Thread structure, hook formulas, its "No AI Tells" list, and `references/x-algorithm.md` (hook and topic in the first 8-10 words, write for the DM share and the follow) |
| `content-strategy` | Map the piece to one content pillar and note it in `brief.md` |
| `marketing-psychology` | Choose one principle for the hook (curiosity gap, specificity, loss framing) and name it in `brief.md` |
| `copywriting` | Its AI-tells reference while writing each tweet |
| `image` | Choosing the image's visual metaphor |

Write each thread to `references/thread-format.md`: 3-5 tweets, the last one carrying the single link, the voice from `voice.md`. Write 3 hook options, keep the strongest, and list the other two under "Alternates" in `thread.md`.

**Images.** Draw one image per thread yourself, no image API. Pick one concrete visual metaphor from the thread, write it as a flat SVG in the house style (`references/thread-format.md`, viewBox `0 0 1600 900`, no `<text>`), save it as `images/hook.svg`, then render it:

```bash
NODE_PATH=$(npm root -g) node <skill-dir>/scripts/render_svg.js images/hook.svg images/hook.png
```

Open the PNG with Read and look at it. Fix overlaps, clipped shapes or anything that reads as letters, and render again. Note the metaphor in `image-prompts.md`.

## Step 3: Audit

Run every check in `references/audit-checklist.md` on each piece and write the results to `audit.md`. Run `scripts/check_thread.py <piece>/thread.json` for the mechanical checks and paste its output in.

- Every check PASS → status **READY**.
- Any FAIL → fix the thread, then audit again from the top. Allow two revision rounds.
- Still failing after two rounds → status **NEEDS-REVIEW**, with the failing lines and why at the top of `audit.md`.

Also load `copy-editing` (or `humanizer`) for the AI-tells pass, and `copywriting-kit:copy-proof-check` when installed to check every claim against the sources saved in `brief.md`.

## Step 4: Record

1. Append both pieces to `posted.json` with status `drafted`, plus date, slot, topic, source URL and day folder. The posting workflow changes `drafted` to `posted` and adds the tweet id.
2. For slot A, set the essay's `last_posted` to today's date in the Medium library. In Notion, use a targeted `update_content` on that one row (match the row's `| <queue> | <tier> | <title> |` start through its trailing empty cell) and leave everything else on the page as it is.
3. Append each READY piece to `queue.json`: `{"id": "day-N-A", "day": "day-N", "slot": "A", "dir": "x-content/day-N/piece-1-medium", "status": "READY", "created": "<today>", "title": "<thread title>"}` (slot B uses `piece-2-industry`). Leave NEEDS-REVIEW pieces out of the queue.
4. Write `summary.md`: each piece's hook tweet, status, slot time, image status, and what the user must do (approve, fix, or fill tiers).
5. Commit `x-content/` and push to `dailypush-x` (`git push -u origin dailypush-x`), so the n8n poster can read it. Never push this content to `main`.

## Step 5: Hand off

Stop at READY. Tell the user the day folder path and each piece's status in a few lines. Never post to X or call X yourself. The n8n workflow "dailypush-x: Post to X" runs at 14:00 (slot A) and 20:00 (slot B) IST, takes the oldest READY queue entry for that slot that is not in its `x_threads_posted` log, and posts it with its image. Because anything in `queue.json` will be posted, only a piece whose audit is fully PASS may go in.

## Rules that never bend

- Every fact, number and quote in a tweet traces to a URL in `brief.md`. Industry threads credit the source in the link tweet.
- No copying more than one short quoted line from someone else's work. Summarise in the user's words and add their take.
- No hashtags, emojis, numbering ("1/5"), em dashes or links in any tweet but the last.
- One run makes one day. Never write into an older `day-N` folder unless the user asks.
