# medium-threads

The code behind my Medium → X threads automation. It started as an n8n workflow that, once a day, takes the newest Medium essay not yet tweeted, has a model draft a five-tweet thread in my voice, and posts it to X with a last tweet linking the essay. The steps that do not need a model are being moved here as small, tested Python, one step at a time.

| File | What it does |
|---|---|
| `next_essay.py` | Picks the one essay to thread this run: the newest feed item whose guid is not in the posted log |
| `feed_item.py` | Turns a Medium RSS item into clean essay text: HTML stripped to paragraphs, entities decoded, images and the "originally published" footer dropped, tracking query removed from the link |
| `thread.py` | Cleans drafted tweets into a thread that is safe to post: strips links, drops empty tweets, keeps at most six, cuts each to 280 characters at a word boundary and adds the link tweet |

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

[5/5] 116 chars
Full essay: Are Tooltips UX or Confessions?
https://medium.com/coinmonks/are-tooltips-ux-or-confessions-a012d600d0c5
```

`--json` prints the thread as a JSON list instead, ready to post tweet by tweet. Links inside drafted tweets are removed, because the essay link has its own tweet at the end. A tweet over 280 characters is cut back to its last space and ends in an ellipsis, unless that space falls in the first 70% of the limit, in which case it is cut mid-word. A draft with fewer than three usable tweets exits with status 1 so nothing half-finished gets posted; a file that is not a draft exits with status 2.

Lengths are counted in Unicode code points, the same way the workflow counts them. X itself counts links as 23 characters and some scripts and emoji as two; that is on the backlog.

## Tests

```bash
pip install -r requirements.txt
pytest
```
