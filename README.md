# 100 Days of Python

A .NET / TypeScript developer learning Python by building one small, complete app a day,
in the spirit of "100 Days of React".

Every day is a self-contained [uv](https://docs.astral.sh/uv/) project for Python 3.14, with its
own dependencies, sample data and tests. The `README.md` in each day's folder is that day's lesson:
it shows real output, tours the interesting code, maps it to C# / TypeScript, lists the traps,
and ends with three challenges.

- [Curriculum](CURRICULUM.md): all 100 days, in 10 phases from the standard library to
  full-stack capstones
- [Progress](PROGRESS.md): what's done so far

## Run any day

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```bash
cd 001-word-frequency      # any day's folder
uv run <command>           # the exact command is at the top of that day's README
uv run pytest              # its tests
```

uv installs the right Python version and the day's dependencies on first run. Nothing is
installed globally, and days never share an environment.

## How it's made

Each day is generated with [Claude Code](https://claude.com/claude-code) using a custom
`/python-daily` command. It picks the next day from the curriculum, builds the app, checks that
the demo, tests, ruff and mypy (strict) all pass, writes the lesson README, and commits the day
here.
