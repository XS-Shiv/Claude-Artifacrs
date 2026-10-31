# Audit checklist

Write each line into `audit.md` as `PASS` or `FAIL — <reason>`. One FAIL blocks READY.

## Mechanical (from `scripts/check_thread.py`)

1. 3 to 5 tweets.
2. Every tweet at or under 280 characters, counted the X way (URLs = 23, emoji and wide characters = 2).
3. Exactly one link, in the last tweet only.
4. No hashtags, emojis, numbering or em dashes.
5. No empty or duplicate tweets.

## Content

6. **Hook:** the topic is named in the first 10 words and the claim is specific (a name, number or concrete situation).
7. **Stands alone:** the hook tweet makes sense with no other context.
8. **One idea per tweet:** each body tweet carries a single point and reads on its own.
9. **Take:** the thread holds a real opinion or lesson, not just a summary. For slot B, the user's take is in the thread.
10. **Share test:** a reader in product management, design or AI would plausibly DM it to a colleague. One line on why.

## Truth and sources

11. Every fact, number, quote and name traces to a URL in `brief.md`. List each claim and its source.
12. No more than one short quoted line from someone else's work. Industry pieces credit the source in the last tweet.
13. Dates are right. "Today", "this week" and "just launched" match the source date.
14. Slot A: the thread says nothing the Medium article does not support.

## Voice and AI tells

15. Matches `voice.md` (or the default voice).
16. None of: "It's not X, it's Y", negation lists, self-answered questions, colon reveals, stock phrases, broetry, engagement bait, manufactured vulnerability, emoji bullets.
17. Reads aloud without stumbling.

## Safety and fit

18. Nothing that could read as defamatory, as financial or medical advice, or as mocking a named person.
19. No overlap with anything in `posted.json` in the last 30 days, and the two pieces today cover different topics.
20. Image: `images/hook.png` exists at 1600x900, was looked at after rendering, has no text, logos or real people, and matches tweet 1.

## Final status

`READY`, or `NEEDS-REVIEW — <failing check numbers and why>`.
