# medium-threads

The code behind my Medium → X threads automation. It started as an n8n workflow that, once a day, takes the newest Medium essay not yet tweeted, has a model draft a five-tweet thread in my voice, and posts it to X with a last tweet linking the essay. The steps that do not need a model are being moved here as small, tested Python, one step at a time.

| File | What it does |
|---|---|
| `next_essay.py` | Picks the one essay to thread this run: the newest feed item whose guid is not in the posted log |
| `tier_order.py` | Orders the queue from the tier list: S and A essays only, design/AI and Web3 topics alternating |
| `posted_log.py` | Keeps the posted log: guid, title, link, root tweet id and time for each threaded essay, written atomically and refusing duplicates |
| `feed_item.py` | Turns a Medium RSS item into clean essay text: HTML stripped to paragraphs, entities decoded, images and the "originally published" footer dropped, tracking query removed from the link |
| `x_length.py` | Counts a tweet's length the way X does: links as 23, wide scripts and "…" as 2, a whole emoji sequence as 2 |
| `thread.py` | Cleans drafted tweets into a thread that is safe to post: strips links, drops empty tweets, keeps at most six, cuts each to 280 as X counts length at a word boundary and adds the link tweet |

## Picking the next essay

```bash
python next_essay.py examples/feed_three.xml --posted examples/posted.json
```

```
Gas Fees Are a Design Problem
https://medium.com/@sample/gas-fees-are-a-design-problem-1c2d3e4f5061
2026-10-24
```

Items are sorted newest first by `<pubDate>`, compared as instants across time zones; an item with no readable date sorts last. The posted log is a JSON list of guids or of objects with a `guid` key, and a missing log means nothing is posted yet. `--json` prints the essay with its `text`. When every essay is posted it exits with status 1; an unreadable feed or malformed log exits with status 2.

## Posting order from the tier list

```bash
python tier_order.py examples/tiers.json --posted examples/posted.json
```

```
 1. S  web3       Gas Fees Are a Design Problem
 2. A  design-ai  Empty States Are Onboarding
 3. A  web3       Wallets Should Feel Like Inboxes
 4. A  design-ai  Prompts Are the New Forms
```

The tier list is a JSON list of `{"guid", "title", "tier", "topic"}`: tier is S, A, B or C and topic is `design-ai` or `web3` (`design`, `ai` and `design/ai` are read as `design-ai`). Only S and A essays are queued, S before A within a topic and ties in list order. Topics alternate, starting with the one the last posted essay was not, so two Web3 threads never go out back to back; with nothing posted yet it leads with the topic of the first S essay. When one topic runs out the other follows. `--next` prints only the next essay and `--json` prints JSON. It exits with status 1 when every S and A essay is posted, and 2 on an unreadable or invalid tier list (unknown tier or topic, a guid listed twice).

## Recording a posted thread

```bash
python posted_log.py add posted.json --guid https://medium.com/p/1c2d3e4f5061 \
  --title "Gas Fees Are a Design Problem" \
  --link https://medium.com/@sample/gas-fees-are-a-design-problem-1c2d3e4f5061 \
  --tweet-id 1850000000000000001
python posted_log.py list posted.json
```

```
logged https://medium.com/p/1c2d3e4f5061 (2 posted)
2026-10-28   1850000000000000001  Gas Fees Are a Design Problem
-                     -  Are Tooltips UX or Confessions?
```

The log is the same file `next_essay.py --posted` reads. Each record gets a UTC `posted_at`; the tweet id must be digits. Adding a guid that is already logged exits with status 1 and leaves the file untouched, so a re-run cannot post an essay twice. Older logs of bare guid strings are read and written back as objects. The file is written to a temp file and swapped in, so a crash mid-write keeps the previous log. Bad input or a malformed log exits with status 2.

## Cleaning an essay from the feed

```bash
python feed_item.py examples/feed.xml
```

```
Are Tooltips UX or Confessions?
https://medium.com/coinmonks/are-tooltips-ux-or-confessions-a012d600d0c5

Every tooltip is a small admission

The screen didn’t explain itself, so a little box has to.
...
```

`--index N` picks another item (0 is the first) and `--json` prints `guid`, `title`, `link` and `text` as JSON. A feed that cannot be read, an item with no title or link, or an index past the end exits with status 2.

## Building a thread from a draft

A draft is the model's output plus the essay's title and link:

```json
{"title": "Are Tooltips UX or Confessions?", "link": "https://medium.com/...", "tweets": ["...", "..."]}
```

```bash
python thread.py examples/draft.json
```

```
[1/5] 74 chars
Every tooltip is a small admission that the screen did not explain itself.

...

[5/5] 67 chars
Full essay: Are Tooltips UX or Confessions?
https://medium.com/coinmonks/are-tooltips-ux-or-confessions-a012d600d0c5
```

`--json` prints the thread as a JSON list instead, ready to post tweet by tweet. Links inside drafted tweets are removed, because the essay link has its own tweet at the end. A tweet over 280 is cut back to its last space and ends in an ellipsis, unless that space falls in the first 70% of the limit, in which case it is cut mid-word. A draft with fewer than three usable tweets exits with status 1 so nothing half-finished gets posted; a file that is not a draft exits with status 2.

Lengths are counted the way X counts them, with `x_length.py`, and the cut never splits a link or an emoji.

## Counting length the way X does

```bash
python x_length.py "Hello 👋🏽 世界 https://example.com/long"
```

```
37/280
```

It follows twitter-text's v3 weights: text is NFC-normalised, a link counts as 23 however long it is, Latin and other scripts below U+1100 and the common punctuation ranges (spaces, dashes, curly quotes) count as 1, and everything else counts as 2, including CJK, Hangul and the "…" that `thread.py` adds when it cuts. An emoji counts as 2 however many code points build it: skin tones, ZWJ sequences, flags and keycaps. It exits with status 1 when the text is over 280.

## Tests

```bash
pip install -r requirements.txt
pytest
```
