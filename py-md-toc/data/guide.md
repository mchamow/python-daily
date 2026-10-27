---
title: Brewbot user guide
---

# Brewbot

Brewbot times your pour-over so you don't have to count in your head.

<!-- toc -->
- [Install](#install)
- [Usage](#usage)
  - [Old flags](#old-flags)
<!-- /toc -->

## Installation

Run `pip install brewbot`, then read [Configuration](#configuration) and
[the V60 recipe](#brewing-a-v60-).

## Usage

### Brewing a V60 ☕

```bash
# this comment is not a heading
brew v60 --dose 15g
```

### `brew --ratio` & friends

The ratio is water to coffee, so `--ratio 16` means 1:16.

### Example

~~~markdown
## Neither is this, even inside a fence that mentions ```
[a link in code](#not-checked)
~~~

## Configuration

Environment variables
---------------------

`BREWBOT_UNITS` is `metric` or `imperial`.

### Example

### `List<Recipe>` in the API

## FAQ

### Why is it called _Brewbot_?

### Q&A for C# / TypeScript folks

### Example

## Troubleshooting ##

If the scale doesn't connect, redo the [install steps](#instalation) and compare with the
[configuration example](#example-1).
