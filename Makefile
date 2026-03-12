.PHONY: clean codex run

clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

codex:
	npm install @openai/codex --save-dev
	rm package.json package-lock.json
	npx codex

run:
	python3 -m docker_check_updates