# Team organisation and retrospective

## Who did what

TODO — one line per person and per area (model, view, controller,
packaging, documentation). Commit history is evidence, but write the
summary here too.

## How decisions were made

TODO — e.g. short design discussions before each phase, choices recorded
in `decisions.md`, disagreements settled by prototyping.

## Blocking points

* Model and view were developed in parallel against a fake model. That
  kept both moving, but the two sides drifted apart (coordinate
  convention, HUD data path) and integration cost a full pass.
  Lesson: write the protocol down *first*, and make the fake model
  emit exactly the events the real one emits.
* TODO — others.

## What we would do differently

all and nothing.
