# Research tools and sources

## Which tool for which job

| Job | First choice | Fallback |
|---|---|---|
| Find recent stories and data on a topic | Exa search (last 7 days, `category: news` or `research paper`) | WebSearch |
| Find articles similar to a Medium essay (fresh angle) | Exa "find similar" on the essay URL | WebSearch on the essay's main claim |
| Read a page in full | Firecrawl scrape (markdown) | WebFetch |
| Pull recent posts from subreddits | Apify `fatihtahta/reddit-scraper-search-fast` via `call-actor` with `{"subredditName": "UXDesign", "subredditSort": "top", "subredditTimeframe": "week", "maxPosts": 10, "scrapeComments": false}` and `callOptions.maxTotalChargeUsd: 0.1`, then `get-actor-run` (waitSecs 45) and `get-dataset-items` with `fields: "title,score,num_comments,url,created_utc"` | WebSearch on `site:reddit.com/r/<sub>` |
| Pull recent posts from X accounts | Apify `search-actors` for "Twitter" and pick a well-rated tweet scraper; cap spend with `maxTotalChargeUsd` | Skip; note it in `brief.md` |

Record in `brief.md` which tool produced each source.

## Sources for slot B

Edit this list to match the user's niche.

**Product management:** Lenny's Newsletter, Reforge blog, Mind the Product, Shreyas Doshi, Marty Cagan (SVPG), John Cutler.

**Design:** Nielsen Norman Group, Figma blog, Smashing Magazine, UX Collective, Julie Zhuo, Luke Wroblewski.

**AI:** Anthropic news, OpenAI blog, Google DeepMind blog, Simon Willison's weblog, Latent Space, Ben's Bites, Hacker News front page.

**Communities (via Apify or the fallback):** r/ProductManagement, r/UXDesign, r/userexperience, r/LocalLLaMA, r/MachineLearning.

## Search queries to start from

- `product management AI agents` (last 7 days)
- `design systems AI` / `UX research AI tools` (last 7 days)
- `<model or product launched this week> product design implications`
- For slot A: the article's main claim, phrased as a question
