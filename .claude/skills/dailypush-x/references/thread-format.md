# Thread format and house style

## Shape (3-5 tweets)

| Tweet | Job |
|---|---|
| 1 — Hook | A specific claim with the topic named in the first 10 words. No link, no "thread", no "🧵". It must make sense if it is the only tweet someone sees. |
| 2 to N-1 — Body | One idea per tweet: a story beat, a number, a step, or an example. Each tweet reads on its own. |
| N — Close | The takeaway in one sentence, then the link on its own line. Slot A: "Full essay: <title>" + Medium URL. Slot B: credit the source by name + its URL. |

Total is 3 to 5 tweets including the close.

## Limits

- 280 characters per tweet, counted the way X counts: any URL is 23 characters, emoji and CJK characters count as 2.
- No hashtags, emojis, numbering ("1/", "(2/5)"), em dashes, or @mentions of people who have not opted in.
- Links only in the last tweet.

## Default voice (used when there is no `voice.md`)

- Plain, first person, sure of itself. Short paragraphs, not one sentence per line.
- Name specific things: products, numbers, dates, companies.
- Ends on the point. No "Agree?", "Thoughts?", "Let that sink in".
- Forbidden: "It's not X, it's Y", "Here's the thing", "game-changer", "unlock", "delve", "In today's fast-paced world", self-answered questions ("The result? ...").

## Image house style

One image, on the hook tweet. The link card fills the close tweet.

Drawn as SVG by Claude and rendered with `scripts/render_svg.js`:

- `viewBox="0 0 1600 900"`, background rect `#F5F1EA` (off-white).
- Two colours only: deep navy `#1B2A41` for shapes and outlines, warm coral `#FF6B5A` for the one thing the eye should land on. Opacity steps of navy are fine.
- Flat shapes, rounded corners, stroke width 4-9, generous negative space.
- One concrete metaphor from the thread (an object or a before/after split). Reuse shapes with `<defs>` and `<use>`.
- No `<text>`, no letters or digits drawn as shapes, no logos, no real people. The renderer refuses SVGs with `<text>`.

Examples: day 1 slot A (crossed-out wireframes vs screens on a conveyor belt), day 1 slot B (a stopwatch slice draining into a pile of drafts to fix).
