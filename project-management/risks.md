# Risk analysis

| risk | impact | likelihood | mitigation | status |
|------|--------|-----------|------------|--------|
| The assigned A-Maze-ing package changes or is reinstalled with a different behaviour | blocking: no levels | medium | all of it is behind `model/maze.py`; failures are caught and sent back to the main menu | handled |
| The generator produces a maze with no corridor at the expected spawn | crash or unplayable level | low | `_nearest_walkable_center` searches outward from the target cell | handled |
| MiniLibX unavailable (no display, missing X11 headers) | game cannot start | medium | `make_canvas` returns `None`, the program exits with a clear message; a console view keeps the model testable | handled |
| Configuration edited during the defence with wrong values | crash in front of the reviewer | high | every value clamped, unknown keys ignored, no traceback | handled |
| Frame drops making entities skip intersections or walls | broken collisions | medium | frame-relative alignment tolerance, delta capped at 100 ms, positions snapped on turns | handled |
| Corrupted highscore file | crash at start-up | medium | defensive load, invalid entries dropped | handled |
| Packaging on a different distribution than the reviewer's | the itch.io build does not run | medium | build on the target distribution, document it in the README | TODO: verify on the review machine |
| Team member unavailable near the deadline | scope not finished | TODO | TODO | TODO |
