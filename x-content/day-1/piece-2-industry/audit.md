# Audit: slot B (NN/g survey)

**Final status: READY** (one revision: tweet 2 reworded to match the source quote exactly)

## Mechanical (`check_thread.py thread.json`)

```
  tweet 1: 223 chars
  tweet 2: 258 chars
  tweet 3: 261 chars
  tweet 4: 260 chars
PASS — 3 to 5 tweets
PASS — every tweet <= 280 (X counting)
PASS — one link, last tweet only
PASS — no hashtags, emojis, numbering or em dashes
PASS — no empty or duplicate tweets
```

1-5. PASS (above).

## Content

6. **Hook:** PASS. "NN/g", "521 UX practitioners" and "AI" are in the first 10 words; two concrete numbers.
7. **Stands alone:** PASS. Tweet 1 states the finding and the tension on its own.
8. **One idea per tweet:** PASS. 1 the gap, 2 why, 3 where the time goes, 4 what to measure instead.
9. **Take:** PASS. Judge AI at the system level (good work reaching users), not by individual speed. Proposed for Shivanand to confirm.
10. **Share test:** PASS. A design lead would send this to a manager pushing AI usage targets.

## Truth and sources (all from the NN/g article, read in full with Firecrawl)

11. **Every claim traces to the source:** PASS.
    - 521 UX practitioners; task time 4.2 out of 5 → "AI Was Used Least When Users Were Involved".
    - sentiment 3.57, barely above neutral → "Respondents Were Only Moderately Positive About AI".
    - top complaint unreliable output and verification → coded reasons chart (40 comments, the most common).
    - mandates, tracked usage → "Many respondents said that their organizations mandated AI and tracked their usage".
    - prototypes a product manager made; expected to be as fast as AI → respondent quote "trying to quickly fix completely unusable prototypes made by a product manager. And I'm expected to come up with a solution just as quickly as AI does."
    - quoted line in tweet 3 → Conclusion, word for word.
    - time saved absorbed by more output or cleanup → Conclusion.
    - measure whether work reaches users faster and better; people whose work got better reinvested the time → Conclusion.
12. **Quoting others:** PASS. One short quoted line (tweet 3), credited; the rest is paraphrase. Authors and NN/g credited in the link tweet.
13. **Dates:** PASS. No time words; the article is dated 2026-10-23.
14. **Source supports everything:** PASS.

## Voice and AI tells

15. **Voice:** PASS with a note. Default voice; first person only in tweet 3.
16. **AI tells:** PASS. No "not X, it's Y", no self-answered questions (an earlier draft had "How they feel? 3.57", removed). One fragment (end of tweet 1). No engagement bait.
17. **Reads aloud:** PASS.

## Safety and fit

18. **Safety:** PASS. Respondent quotes stay anonymous, as in the source. PMs are described doing what the source says, without blame.
19. **Overlap:** PASS. Slot A is about where design happens; slot B is about how AI productivity is measured. Both touch AI and design, so post them on different halves of the day as planned.
20. **Image:** PASS. No text, logos or people; matches tweet 1.

## Research log

- Exa: found the NN/g original (nngroup.com, 2026-10-23) plus 10 candidate stories from Oct 24-31.
- Apify (`fatihtahta/reddit-scraper-search-fast`, r/UXDesign top of the week): top post "Golden days of ux is over.." (332 upvotes, 245 comments) shows the same mood. Context only, not quoted.
- Firecrawl: full NN/g article.
