# Claude Artifacts

Things I first built as Claude artifacts, turned into small tested projects. One piece ships at a time, and each project folder runs on its own.

## Projects

| Project | What it does | Status |
|---|---|---|
| [case-comp-deck-designer](projects/case-comp-deck-designer) | A Claude skill for case-competition decks, with a tool that measures a deck's density slide by slide | In progress |

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
