# Deploy to the lab VM, same convention as the calendar's repo: rsync the
# working tree (never .git, never docs) and rebuild. The .env lives only on
# the host and rsync without --delete never touches it.

DIR = /srv/lab/groceries

.PHONY: deploy up down logs status demo demo-reset

# --- try it locally -------------------------------------------------------
# `cp .env.example .env`, then `make demo`: the stack comes up on
# http://127.0.0.1:3030 with a plausible list already on the board.

demo:
	docker compose up -d --build
	@echo "waiting for the database…"
	@until docker compose exec -T db pg_isready -U groceries >/dev/null 2>&1; do sleep 1; done
	@sleep 2
	docker compose exec -T db psql -q -U groceries -d groceries < demo/seed.sql
	@echo "seeded. http://127.0.0.1:3030"

demo-reset:
	docker compose exec -T db psql -q -U groceries -d groceries \
	  -c "truncate entries, category_defaults, items restart identity cascade;"
	docker compose exec -T db psql -q -U groceries -d groceries < demo/seed.sql
	@echo "reseeded. http://127.0.0.1:3030"

# --- the household instance ------------------------------------------------

deploy:
	rsync -a --exclude .git --exclude .gitignore --exclude Makefile \
	      --exclude README.md --exclude STATUS.md --exclude LICENSE \
	      --exclude .env.example --exclude demo --exclude docs ./ lab:$(DIR)/
	ssh lab 'cd $(DIR) && docker compose up -d --build'

up:
	ssh lab 'cd $(DIR) && docker compose up -d'

down:
	ssh lab 'cd $(DIR) && docker compose down'

logs:
	ssh lab 'cd $(DIR) && docker compose logs --tail=100 -f'

status:
	ssh lab 'cd $(DIR) && docker compose ps'
