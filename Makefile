
build-LDSLambdaFunction:
	#mkdir -p $(ARTIFACTS_DIR)/job_server
	cp deployment/lambda_handler.py $(ARTIFACTS_DIR)
	cp -r job_server $(ARTIFACTS_DIR)/job_server
	cp requirements.txt $(ARTIFACTS_DIR)/requirements.txt
	python -m pip install -r requirements.txt -t $(ARTIFACTS_DIR)
	rm -rf $(ARTIFACTS_DIR)/bin

falcon-egl-index:
	python3 scripts/build_falcon_egl_index.py
.PHONY: falcon-egl-index

sync-local-db:
	python3 -m job_server.sync_from_s3
.PHONY: sync-local-db
