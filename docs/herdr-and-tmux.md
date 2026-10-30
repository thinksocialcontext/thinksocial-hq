# Running the agents side by side: herdr or tmux

ThinkSocial HQ runs seven Claude Code agents at once: `hq`, `clients`, `inventory`, `team`, `growth`, `growth-research` and `ops` (the map is `docs/layout.md`). Something has to hold seven terminals and let HQ read and type into the others. The kit supports two options and one script, `scripts/hq`, that works the same on both.

## herdr (recommended)

[herdr](https://herdr.dev) is a terminal workspace manager built for coding agents. It knows when an agent is working, idle, or waiting on a question, and it has commands for reading and prompting agents. It is open source under the Apache 2.0 licence. `./setup.sh` offers to install it from the official installer:

```
curl -fsSL https://herdr.dev/install.sh | sh
herdr integration install claude     # lets herdr see Claude Code's state
```

Then open a terminal, run `herdr`, and inside it run `scripts/hq start`. You get one workspace per space, each rooted at its folder: HQ (the repository root), Clients (`clients/`), Inventory (`inventory/`), Team (`team/`), Growth (`growth/`, with a second tab Research in `growth/research/`) and Ops (`ops/`). Running it again only adds what is missing.

## tmux (fallback, always works)

tmux comes with Ubuntu. If herdr is not installed, `scripts/hq` uses tmux automatically:

```
scripts/hq start      # creates the tmux session "thinksocial-hq", one window per agent, named like the agent
scripts/hq attach     # look at it; Ctrl+b then 0 to 6 switches agents, Ctrl+b then d leaves it running
```

On tmux, agent state is a best guess: `working` if the screen is changing, `blocked` if a question or permission dialog is showing, `idle` otherwise.

To force one or the other: `HQ_BACKEND=tmux scripts/hq start`.

## The verbs

| Command | Does |
| --- | --- |
| `scripts/hq start` | open every workspace and agent (safe to run twice) |
| `scripts/hq list` | each agent and its state |
| `scripts/hq read inventory 80` | the last 80 lines of the inventory agent's screen |
| `scripts/hq prompt clients "..."` | type a task and press Enter (refuses if a dialog or unsent text is showing) |
| `scripts/hq wait clients 600` | wait up to 600 seconds for clients to finish or ask something |
| `scripts/hq layout` | each agent, its folder and its workspace label |
| `scripts/hq attach` / `stop` | tmux only |
