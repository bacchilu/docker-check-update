.PHONY: clean codex

clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

codex:
	npm install @openai/codex --save-dev
	rm package.json package-lock.json
	npx codex