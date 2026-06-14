# Kanban Studio

Une application de gestion de projets full-stack construite comme projet de cours Udemy. Le backend FastAPI sert un frontend Next.js compilé en statique depuis un seul conteneur Docker. Une barre latérale de chat IA permet aux utilisateurs de demander à un LLM de mettre à jour le tableau Kanban.

## Architecture

```
pm/
├── backend/          # Application FastAPI (Python)
│   ├── main.py       # Toutes les routes API et la logique BDD
│   └── data/         # Base de données SQLite (kanban.db, ignorée par git)
├── frontend/         # Application Next.js
│   ├── src/
│   │   ├── app/      # Routeur Next.js (page.tsx = connexion + racine du tableau)
│   │   ├── components/  # KanbanBoard, KanbanColumn, KanbanCard, ChatSidebar
│   │   └── lib/      # kanban.ts (types/helpers), api.ts (helper URL)
│   └── out/          # Export statique (généré par next build, copié dans backend/static)
├── scripts/          # start.sh / stop.sh (build + lancement Docker)
└── .env              # OPENROUTER_API_KEY (ne jamais committer)
```

Le backend sert le frontend compilé à `/` via `StaticFiles`. Toutes les routes API sont sous `/api/`.

## Lancement en local

**Configuration initiale :**
```bash
uv sync   # crée .venv et installe toutes les dépendances
```

**Développement (rechargement à chaud, deux terminaux) :**
```bash
# Terminal 1 — backend (depuis la racine du projet)
uv run uvicorn backend.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev
```
Le frontend proxifie les appels API vers `http://localhost:8000` via `NEXT_PUBLIC_API_BASE_URL`.

**Production (Docker) :**
```bash
scripts/start.sh   # compile le frontend, le copie dans backend/static, build + lance Docker
scripts/stop.sh    # arrête et supprime le conteneur
```
Accéder à http://localhost:8000

## Authentification

Identifiants de démonstration codés en dur : **user** / **password**. Définit un cookie httpOnly `pm_mvp_auth=true`. Toutes les routes `/api/board` et `/api/ai/*` nécessitent ce cookie.

## IA

Utilise OpenRouter à `https://openrouter.ai/api/v1` avec le modèle `openai/gpt-oss-120b`. Le endpoint `/api/ai/chat` envoie le JSON complet du tableau + la question de l'utilisateur au modèle et attend une réponse JSON `{ reply, board_update }`. Si `board_update` est non nul, il est validé selon le schéma `BoardData` et sauvegardé.

Définir `OPENROUTER_API_KEY` dans `.env` à la racine du projet.

## Tests

```bash
# Tests unitaires frontend (Vitest)
cd frontend && npm test

# Tests e2e frontend (Playwright)
cd frontend && npm run test:e2e

# Tests backend (pytest) — depuis la racine du projet
uv run python -m pytest backend/tests/
```

## Stack technique

| Couche | Stack |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind v4, @dnd-kit |
| Backend | Python 3.14, FastAPI, Pydantic, SQLite |
| IA | OpenRouter (`openai/gpt-oss-120b`) via le SDK `openai` |
| Infra | Docker (conteneur unique), uv (gestionnaire de paquets Python, local + Docker) |

## Palette de couleurs

- Jaune accent `#ecad0a` — lignes d'accent, mises en valeur
- Bleu principal `#209dd7` — liens, sections clés
- Violet secondaire `#753991` — boutons de soumission, actions importantes
- Bleu marine foncé `#032147` — titres principaux
- Gris texte `#888888` — texte d'accompagnement, étiquettes

## Standards de codage

- Pas de sur-ingénierie. Pas de programmation défensive inutile. Pas de fonctionnalités superflues.
- Pas d'emojis.
- Garder les README et la documentation minimaux.
- En cas de problème, identifier la cause racine avec des preuves avant de corriger.
