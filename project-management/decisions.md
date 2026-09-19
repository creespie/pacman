# Analysis and technical choices

## MVC with an observer, rather than a view reading the model

The view could have read the model directly every frame. We chose an
event stream instead: the model exposes what *changed*, not what *is*.

* the model has no reference to any view and no import of MLX;
* the same events feed the graphical view and a console view, which is
  how we test the game without a display;
* events are plain dataclasses of primitive fields, so they could be
  serialized (network play) without touching the model.

Cost: an event has to exist for anything the HUD shows. That is why
`LivesChanged`, `LevelStarted` and `TimeChanged` exist — an earlier
version pushed those values into the view through a method call, which
broke the rule and got removed.

## One coordinate convention

Positions are points in cell units; the cell is `(int(x), int(y))` and
its centre is `(col + 0.5, row + 0.5)`. The model sends centres and the
view multiplies by the cell size. Writing this down in
`protocol/events.py` closed a bug where both sides added the half cell.

## Turning only on cell centres, with a frame-relative tolerance

Grid games need entities aligned on the grid. "Close enough to a centre"
is half of the distance covered during the current frame, not a fixed
epsilon: with a fixed one, a slow frame makes an entity jump over the
intersection and a ghost ends up stuck against a wall.

## Tolerant configuration

The subject asks for clamping, so the loader has no fatal path for
values: it warns and continues. Only an unreadable or unparsable file
stops the program, with one readable line.

## JSON highscores

Simple, inspectable during the review, cheap to rewrite whole. Every
read is defensive because the file is user-editable by design.

## Repainting only what changed

The obvious loop redraws everything sixty times a second. That is right
for a running game and wrong for a menu: MiniLibX draws text one
character at a time, on top of the frame that has just erased it, and
flushes to the screen every 64 blits, so a static menu flickered
permanently. The view therefore keeps a dirty flag, set by any incoming
event and by the expose hook. The game screen ignores it, since
something moves on every frame.

## Session separate from the game

Screen flow (menu, pause, highscores, name entry) lives in
`controller/session.py`, not in the model: a Pac-Man game does not need
to know that menus exist. The session observes the model, forwards its
events to the views, and reacts to `GameOver` / `GameWon`.