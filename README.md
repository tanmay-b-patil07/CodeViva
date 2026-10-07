# Code Comprehension Platform

A platform for assessing student code comprehension through automated analysis and AI-generated questions.

## Project Structure

See the scaffold structure for the complete organization of the codebase.

## Getting Started

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Configure your .env file
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
cp .env.example .env.local
# Configure your .env.local file
npm run dev
```

## Team Ownership

- **Member 1**: Backend platform (API, models, routers, services)
- **Member 2**: Analysis engine (code facts, runner, tracer, questions)
- **Member 3**: AI integration (question generation, evaluation, scoring)
- **Member 4**: Frontend (Next.js UI, student/teacher portals)

## Documentation

See the `docs/` directory for detailed documentation on architecture, API, and components.
