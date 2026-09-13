.PHONY: help install sample-data taxonomy grounding index eval serve frontend dev

help:
	@echo "Available commands:"
	@echo "  make install       Install python requirements"
	@echo "  make sample-data   Filter brand threads from raw CSV"
	@echo "  make taxonomy      Build intent clusters and taxonomy"
	@echo "  make grounding     Filter resolved threads grounding corpus"
	@echo "  make index         Build ChromaDB vector index"
	@echo "  make eval          Run evaluation harness on golden set"
	@echo "  make serve         Start FastAPI backend server"
	@echo "  make frontend      Start Vite frontend development server"
	@echo "  make dev           Run both backend and frontend"

install:
	pip install -r requirements.txt

sample-data:
	python scripts/01_sample_data.py

taxonomy:
	python scripts/02_build_taxonomy.py

grounding:
	python scripts/03_build_grounding_corpus.py

index:
	python scripts/04_build_index.py

eval:
	python scripts/06_run_eval.py

serve:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev
