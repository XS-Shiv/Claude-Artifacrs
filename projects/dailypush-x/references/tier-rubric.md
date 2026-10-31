# Medium tier rubric

Used to build or refresh the Medium library. Read each article in full, score it, and keep only S and A tier articles in the library. B and C articles are not stored anywhere.

## Score each article 1-5 on five criteria

| Criterion | 5 means | 1 means |
|---|---|---|
| **Argument** | One sharp, arguable claim the reader has not heard put this way | A topic with no position |
| **Specifics** | Concrete examples, products, numbers or a personal story carry the claim | Abstractions only |
| **Fit** | Squarely product management, design or AI (or the user's other stated pillars) | Off the user's pillars |
| **Shelf life** | Still true and interesting in a year | Tied to news that has passed |
| **Thread-ability** | 5+ self-contained atoms (claims, examples, lines) that each work as a tweet | One idea that cannot be split |

## Tiers (total out of 25)

| Tier | Total | Rule |
|---|---|---|
| S | 22-25 | And no criterion below 4 |
| A | 18-21 | And no criterion below 3 |
| B | 13-17 | Not stored |
| C | 12 or less | Not stored |

## Where the articles come from

1. RSS feed `https://medium.com/feed/@shivanandisshukla` (latest 10 only, with full text).
2. Older articles: the profile page `https://medium.com/@shivanandisshukla` scraped with Firecrawl or Apify, or a Medium export (Settings → Download your information) the user uploads.
3. If medium.com cannot be reached from the session, ask the user to paste titles and links, or to allow medium.com in the environment's network settings. Never rate an article from its title alone.

## Library entry format

One line per S or A article, in the library page:

```
| queue | tier | title | url | pillar | why it works | last_posted |
```

`pillar` is `design/AI` or `web3`. `why it works` names the hook and the strongest line, quoted where possible. `last_posted` starts empty.
