.PHONY: build deploy

build:
	uv export --format requirements-txt --no-hashes --no-annotate --no-dev > app/requirements.txt
	sam build --use-container --docker-network host --parallel --cached

deploy: build
	. .envrc && \
	sam deploy --confirm-changeset --parameter-overrides \
		"GoogleClientId=$$GOOGLE_CLIENT_ID" \
		"GoogleClientSecret=$$GOOGLE_CLIENT_SECRET" \
		"SecretKey=$$SECRET_KEY"

plan: build
	. .envrc && \
	sam deploy --no-execute-changeset --parameter-overrides \
		"GoogleClientId=$$GOOGLE_CLIENT_ID" \
		"GoogleClientSecret=$$GOOGLE_CLIENT_SECRET" \
		"SecretKey=$$SECRET_KEY"
