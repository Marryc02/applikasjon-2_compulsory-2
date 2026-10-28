# Event categories

This file is the single source of truth for categories. The pipeline reads the
category IDs from the list below (the text in backticks). The classifier may
only return IDs from this list. To add or rename a category, edit this file only.

Rules:
- An event gets 1–3 categories. Pick the most specific ones that fit.
- If nothing fits, return an empty list. The event then goes to human review.
- Classify by what participants *do*, not where it happens
  (a concert in a sports hall is `music`, not `sports`).

## Categories

- `music`: concerts, open mic, band nights, DJ events, choir, music workshops where people listen or play.
- `sports`: matches (as spectator or player), training sessions open to newcomers, climbing, skating, swimming, martial arts.
- `gaming`: video games, e-sports, LAN parties, board games, card games, tabletop role-playing.
- `arts_culture`: theatre, dance, art exhibitions, drawing, crafts, writing, photography, stand-up.
- `film`: film screenings, cinema events, film-making workshops.
- `outdoors`: hikes, trips, fishing, skiing, outdoor activities in nature.
- `food`: cooking, shared meals, baking, food festivals.
- `learning`: workshops, courses, talks, homework help, language cafés.
- `social`: drop-in meeting places, youth clubs, quiz nights, meetups whose main purpose is meeting people.

## Edge-case decisions

- E-sports tournament → `gaming` (not `sports`).
- Quiz night → `social`.
- "Pizza and board games" → `gaming`, `food`, `social`.
- Language café → `learning`, `social`.
