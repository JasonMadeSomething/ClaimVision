# Root Makefile for ClaimVision project

TF_DIR=terraform
TF_OUTPUT_FILE=terraform_outputs.json

.PHONY: all plan apply terraform_outputs cognito_deploy samconfig sam_build sam_deploy deploy clean

all: deploy

plan:
	cd $(TF_DIR) && terraform init && terraform plan -out=tfplan

apply:
	cd $(TF_DIR) && terraform apply -auto-approve tfplan

terraform_outputs:
	cd $(TF_DIR) && terraform output -json > ../$(TF_OUTPUT_FILE)

cognito_deploy:
	sam deploy \
		--stack-name ClaimVision-cognito-dev \
		--template-file cognito-template.yaml \
		--capabilities CAPABILITY_IAM
	sleep 5

samconfig:
	python3 scripts/generate_samconfig.py

sam_build:
	sam build

sam_deploy:
	sam deploy --no-confirm-changeset --config-file samconfig.toml

deploy: plan apply terraform_outputs cognito_deploy samconfig sam_build sam_deploy

clean:
	rm -f tfplan
	rm -f $(TF_OUTPUT_FILE)
	rm -f samconfig.toml
