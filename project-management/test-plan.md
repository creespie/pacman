# Acceptance test plan

Automated tests: `make test` (28 tests, `tests/`). They cover the
configuration loader, the highscore table, the model (events, movement,
walls, timer, cheats, progression) and the session (screen flow).

Manual checks, to run before the defence:

| # | feature | how | expected | status |
|---|---------|-----|----------|--------|
| 1 | Launch | `python3 pac-man.py config.json` | main menu | TODO |
| 2 | Wrong number of arguments | `python3 pac-man.py` | one error line + usage, exit 1 | TODO |
| 3 | Not a JSON file | `python3 pac-man.py README.md` | clear error, no traceback | TODO |
| 4 | Missing file | `python3 pac-man.py nope.json` | `file not found`, exit 1 | TODO |
| 5 | Broken config | invalid types and unknown keys | warnings, game still starts | TODO |
| 6 | Movement | arrows and WASD | Pac-Man turns at intersections, never enters a wall | TODO |
| 7 | Pacgums | eat a few | score rises by 10 each, dots disappear | TODO |
| 8 | Super-pacgum | eat one in a corner | ghosts turn blue and flee; eating one gives 200 | TODO |
| 9 | Eaten ghost | eat a frightened ghost | it vanishes, comes back at its corner after ~7 s | TODO |
| 10 | Life lost | get caught | flash, respawn in the middle, HUD lives -1 | TODO |
| 11 | Timer | wait 90 s | a life is lost, level restarts | TODO |
| 12 | Level change | clear a level (cheat `5`) | new maze, score and lives kept | TODO |
| 13 | Victory | clear every level | victory screen, name prompt | TODO |
| 14 | Game over | lose every life | game over screen, name prompt | TODO |
| 15 | Highscores | save a name | appears in the menu and in the highscore screen, survives a restart | TODO |
| 16 | Name rules | type `Jean-Mi!!!!!!!!!!!!` | only letters/digits/spaces, 10 characters | TODO |
| 17 | Pause | `ESC` during a game | game freezes, menu appears, resume works | TODO |
| 18 | Back to menu | pause -> return to main menu | main menu, new game starts fresh | TODO |
| 19 | Cheats | `C` then `1`..`5` | HUD shows the active cheats, each one works | TODO |
| 20 | Window close | click the X | the process exits cleanly | TODO |
| 21 | Packaged build | `make package`, run from `dist/` | identical behaviour | TODO |

## Bugs found and fixed

| bug | found | fix |
|-----|-------|-----|
| The view added half a cell to positions that were already cell centres: everything was drawn one half-cell down and right, and food erased the wrong cell | integration of view and model | single coordinate convention documented in `protocol/events.py`, `+0.5` removed from the view |
| `__main__` imported a `ConsoleView` that did not exist: the game could not be launched at all | first end-to-end run | real wiring, plus a console view that actually exists |
| Lives, level and remaining time were pushed into the view with a method call instead of events | review of the MVC split | `LivesChanged`, `LevelStarted`, `TimeChanged` |
| Fixed alignment epsilon made ghosts miss intersections on slow frames | ghosts getting stuck | tolerance relative to the distance covered in one frame, snap on turn |
| Pac-Man kept pushing into a wall after a blocked turn | play-testing | requested direction kept and applied when the corridor opens |
| Text came out with red and blue swapped (a yellow title looked cyan) | first run on a real screen | `mlx_string_put` gets the colour without swizzling while the swapchain is BGRA; `to_string_color` in `canvas.py` swaps it, behind a single documented flag |
| The HUD was drawn half under the bottom edge of the window | first run on a real screen | the font atlas draws a line in `[y + 15, y + 33]`, not at `y`; `TEXT_HEIGHT` now says what a line costs and the HUD reserves it |
| Centred text was off-centre and the longest lines ran past the window | first run on a real screen | the font is 10 px per character, not the 6 px that had been assumed; measured from the atlas (1140 px / 95 glyphs - 2) |
| The pause menu was unreadable over the maze | first run on a real screen | a plain panel is painted behind it |
| Text flickered continuously on the menus, the pause screen and the HUD | play-testing | MiniLibX presents as soon as 64 blits are queued, and one character is one blit, so a text-heavy frame was torn in two. `present()` now flushes with `mlx_do_sync` at the frame boundary, and static screens are repainted only when an event changed them. Proved by capturing the same screen six times in a row: six identical images, where it used to give six different ones |
