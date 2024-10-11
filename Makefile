
build-LDSLambdaFunction:
	#mkdir -p $(ARTIFACTS_DIR)/job_server
	cp deployment/lambda_handler.py $(ARTIFACTS_DIR)
	cp -r job_server $(ARTIFACTS_DIR)/job_server
	cp requirements.txt $(ARTIFACTS_DIR)/requirements.txt
	python -m pip install -r requirements.txt -t $(ARTIFACTS_DIR)
	rm -rf $(ARTIFACTS_DIR)/bin
