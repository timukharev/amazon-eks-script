# Operator setup

## 1. Local checks

Prerequisites: Python 3.11+, Helm 3, and Terraform 1.12+. `make validate` tests cost arithmetic, rejects incomparable inputs, renders each workload environment, checks pool placement and container settings, lints Helm, and checks Terraform formatting. Install the pinned development dependency as shown in the README. `make terraform-validate` requires network access for dependencies but no AWS credentials.

## 2. Infrastructure design

Use a new sandbox account/VPC for evaluation. Supply Terraform inputs through a private, ignored tfvars file or your own configuration system: region, VPC ID, three private subnet IDs in different AZs, operator IAM role, EKS version, and the exact VPC CNI/CoreDNS/kube-proxy/Pod Identity Agent add-on versions. No production identifiers are supplied in this repository.

Private subnets need working routes/endpoints for ECR, S3, STS, EKS, EC2, SQS, Pod Identity, and any registries/controllers used. Terraform checks VPC membership, distinct AZs, and public-IP assignment; it does not prove private routing. The EKS API is private-only, so operator and CI access requires an approved private network path. Review service quotas, address space, IAM permissions, costs, encryption, logging, state storage/locking, and existing resource ownership before an operator plans/applies anything.

The managed system group has illustrative sizes, not a validated capacity model. Check the instance architecture, AMI, add-on compatibility, and EKS support window. Initial network enforcement mode is `standard`; read the strict-mode staging notes in [architecture](architecture.md). Supply partition-appropriate EKS access-policy ARNs if operating outside commercial AWS.

## 3. Karpenter installation

Terraform outputs provide the cluster name/endpoint, node security group, Karpenter node-role name, and interruption queue. Choose and pin a compatible Karpenter controller chart version, use `helm/karpenter/values.yaml` for controller placement/resources and prepare private settings overrides with:

- `settings.clusterName`, `settings.clusterEndpoint`, and `settings.interruptionQueue` from Terraform.
- `serviceAccount.name: karpenter` in `kube-system`, matching the Pod Identity association.
- `nodeSelector: {workload.example.com/pool: system}` and a toleration for `CriticalAddonsOnly=true:NoSchedule`.
- Appropriate replica count, resource requests, and system-node topology rules for the failure model.

Once infrastructure exists, export the derived settings into the ignored build directory:

```sh
mkdir -p build
terraform -chdir=terraform output -json karpenter_controller_settings > build/karpenter-settings.json
```

Pass both `helm/karpenter/values.yaml` and the generated `build/karpenter-settings.json` to the Karpenter controller chart. The first file sets placement/resources; the second supplies the real cluster name, endpoint, and queue without duplicating them manually. This output command only reads state; no provisioning is performed by it.

Install controller and CRDs using the [official setup workflow](https://karpenter.sh/docs/getting-started/getting-started-with-karpenter/) after reviewing compatibility with the pinned IAM module. This repository does not install the controller automatically. The module uses a node IAM role and access entry; `EC2NodeClass` references that role and lets Karpenter create/manage the instance profile. Private clusters without IAM endpoint access need a separately provisioned instance profile and a corresponding NodeClass change, per the [NodeClass documentation](https://karpenter.sh/docs/concepts/nodeclasses/).

Edit `config/capacity.yaml` for EC2 instance types, aggregate limits, expiration, and consolidation. The allowlists are illustrative; confirm regional availability and AMI/architecture compatibility. The renderer accepts `--config` for an alternate file and requires On-Demand applications and Spot tests. Render your capacity resources offline using `python3 scripts/render_capacity.py --help`. Pass the real node role, three subnet IDs, node security group, three AZs, and an explicit EKS-optimized AL2023 amd64 AMI ID compatible with the selected Kubernetes version. Redirect stdout into an ignored `build/` file. Inspect the rendered JSON, then have an operator perform a server-side dry run and apply it. CPU/memory pool limits are illustrative aggregate guardrails, not hard dollar limits or guaranteed instantaneous ceilings.

## 4. Workload and access setup

Review `k8s/environments.json`. Applying it creates production/preprod/testing namespaces, restricted Pod Security labels, quotas, LimitRanges, priorities, default-deny policies, and DNS egress. It grants no database access and exposes no public endpoint. Keep namespace and scheduling administration outside developer roles. Implement RBAC and admission controls before allowing untrusted users to submit workloads; namespace/pool selection in a chart is not an authorization boundary.

Install Metrics Server for CPU HPA, or disable HPA deliberately. Resolve the synthetic application image to a reviewed immutable digest before a real deployment. Render the chart with a namespace matching the chosen environment:

```sh
helm template sample helm/workload --namespace preprod -f environments/preprod.yaml
```

Environment files define illustrative production HPA (3–12 replicas, 60% CPU), preprod HPA (1–4 replicas, 70%), and testing (two fixed replicas, HPA disabled). The HPA template is `helm/workload/templates/hpa.yaml`; base workload requests/limits remain in `helm/workload/values.yaml`. PriorityClasses are `production` and `nonproduction`; check for existing cluster-scoped objects with those names before applying. The sample only serves a static page. Add narrowly scoped network rules for approved clients and dependencies; default-deny intentionally blocks ordinary ingress. The Helm sample's PDB and resource sizes are illustrative. Validate probes, writable paths, scaling, DNS, placement, and service connectivity in a sandbox before substituting real services. Deployment replicas are controlled by HPA when enabled; transient startup behavior still needs validation.

## 5. Manual testing

`k8s/load-test-job.yaml` provides an alternative manually launched Kubernetes k6 Job with explicit testing-pool and Spot selectors, matching toleration, bounded resources, and `nonproduction` priority. It does not fall back to On-Demand. Before launch, an operator must create `load-test-script` in `testing` from `ci/load-test.js` and `load-test-target` containing an approved isolated endpoint in its `url` key. Create narrow test egress and target ingress rules; the namespace defaults otherwise block HTTP traffic. The Job has no production credentials, runs once without automatic retries, and has a 120-second deadline with a one-hour cleanup TTL. This configuration is statically checked, not runtime-tested on an EKS cluster.


`ci/gitlab-ci.yml` is an include template with render checks and an explicitly manual, protected-web-pipeline load-test job. It uses a caller-managed runner; the file does not place the GitLab job onto Spot. Configure a dedicated Kubernetes runner in `testing`, enforcing the testing pool/Spot selector, taint toleration, namespace controls, network policy, and isolated test data. Only then is the runner itself part of the source architecture's Spot test model.

Use an operator-approved isolated `LOAD_TEST_URL`. The included two-user, 30-second k6 job is a small example, not a validated benchmark. A URL string cannot prove isolation; enforce network/RBAC/credentials so it cannot reach production or transitively access production data. Do not expose a public test endpoint merely to run this example.

## 6. Costs and cleanup

The cost script consumes locally supplied aggregates; it never contacts AWS. It requires equal-duration, non-overlapping windows, one declared billing basis, scope, and comparability notes. It reports arithmetic only. `samples/costs.json` intentionally uses a fictional 25% application-hosting reduction, not the source project's 32% total-bill result. Keep real cost exports and identifiers outside Git.

Cloud resources accrue charges, including the cluster, system nodes, application/test nodes, volumes, traffic, and retained logs. Teardown is manual: drain/remove workloads and Karpenter capacity before removing controller/node classes/IAM/cluster resources. Confirm deletion of EC2, EBS, load balancers, queues, and other billable dependencies before considering the sandbox closed. No cleanup command is run by local validation.

## Plan-alignment additions

Review `docs/implementation-map.md` for a requirement-by-requirement distinction between runnable configuration, optional examples, gaps, and operator procedures. It includes strict networking, retained EC2 databases, production data access, spare-capacity protection, budgets, and actual failure tests.

System managed groups are now scoped to each of the three subnet/AZ pairs. `system_node_capacity` still expresses total min/desired/max, and each total must be a multiple of three. One third is assigned to each group. This does not establish enough capacity for a system-component or production failure scenario.

To inspect optional scheduled scaling offline:

```sh
helm template sample helm/workload --namespace production -f environments/production.yaml --set scheduledScaling.enabled=true
```

This renders a KEDA ScaledObject instead of the standalone HPA. The confirmed window is 17:00–22:00 America/New_York, adjusting for daylight saving. The six-replica target is illustrative, not a user-provided capacity requirement. Install compatible KEDA and metrics components and validate this mode before use; chart switching/ownership migration on an existing live release needs a reviewed rollout. Warm-up must start earlier than 17:00 only after measured startup requirements determine the lead time. Scheduled scaling and existing CPU HPA must not concurrently own the same Deployment.

`k8s/admission.yaml` is an optional native ValidatingAdmissionPolicy/Binding for production/preprod/testing Pods. Use a compatible API server and review `status.typeChecking`, admission diagnostics, positive cases, wrong-pool cases, broader-toleration cases, and controller-generated pods in a sandbox before enabling it. It has not been compiled/evaluated by a live server here. It must not be installed into a namespace with incompatible existing pods. It intentionally does not grant a reserve-buffer exception. Restricted Pod Security remains necessary. The read-only Roles in the environment bundle are unbound until actual user/group identities are mapped; runtime service accounts have no added API or AWS permissions.

`k8s/monitoring-alerts.yaml` requires an installed Prometheus Operator, kube-state-metrics, container metrics, and matching Prometheus rule selection. It supplies three illustrative alerts, not the full SLO/database/cost monitoring plan. Rule selection, metric labels, PromQL behavior, and notification routing need live validation. The monitoring namespace alone installs no exporters, monitoring stack, or access permissions.

`python3 scripts/check_capacity.py samples/capacity.json` checks each possible AZ loss for CPU, RAM, pod slots, and pod IPs in synthetic baseline/peak scenarios. A failure returns exit code 1; malformed inputs return exit code 2. Supplied usable capacities must already subtract OS/DaemonSet/other overhead. Replace fixtures with privately measured values. This arithmetic does not protect spare nodes from Karpenter consolidation or validate application scheduling and dependencies.

`cost_budget` is null by default. Supply an actual monthly USD amount and existing SNS topic ARN to enable `terraform/cost-controls.tf`; it configures total-account cost monitoring with an illustrative 80% actual-spend notification threshold. It is not an enforceable spend cap. The SNS topic must be in the budget account. Its policy, subscription recipients, KMS permissions if applicable, and delivery testing are operator-owned; see [AWS budget notification setup](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-sns-policy.html). No anomaly monitor/subscription is provisioned. `ci/gitlab-ci.yml` now exports k6 aggregate summaries into GitLab artifacts with an illustrative seven-day retention; the standalone Kubernetes Job still needs an external report sink for durable retention before its TTL expires.
