PYTHON ?= python3

.PHONY: validate terraform-validate
validate:
	$(PYTHON) -m unittest discover -s tests -v
	@for environment in production preprod testing; do helm lint helm/workload --namespace $$environment -f environments/$$environment.yaml || exit 1; done
	terraform -chdir=terraform fmt -check -recursive

terraform-validate:
	terraform -chdir=terraform init -backend=false -input=false
	terraform -chdir=terraform validate
