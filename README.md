# Claude Artifacts

Things I first built as Claude artifacts and skills, turned into small, tested Python projects. One piece ships at a time, and each project folder runs on its own.

## Projects

| Project | What it does | Status |
|---|---|---|
| [ppt-transition](projects/ppt-transition) | A Claude skill and engine that add PowerPoint Morph transitions to a finished deck, component by component | Paused |
| [ppt-designer](projects/ppt-designer) | A Claude skill for designing and critiquing slide decks, with tools that check density and titles slide by slide | Paused |
| [medium-threads](projects/medium-threads) | The steps behind my Medium → X threads automation: pick the next essay in tier order, clean the drafted tweets, build a postable thread that fits X's length count and remember what was posted | In progress |

## How this repo is organised

- [`BACKLOG.md`](BACKLOG.md) lists what is planned, grouped into small projects.
- [`LOG.md`](LOG.md) lists what shipped and when.
- Each project has its own README with an example of running it, and its tests sit beside the code.

## Running a project's tests

```bash
cd projects/<project-name>
pip install -r requirements.txt
pytest
```
