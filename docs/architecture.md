# Architecture and implementation boundary

```text
Existing ECS Fargate                         EKS cluster
  production                    dedicated system On-Demand nodes
  preprod          ──────────>   shared application On-Demand nodes
                  phased        isolated testing Spot nodes
                  cutover

Application data remains on EC2: PostgreSQL / MongoDB / ELK
```

Application NodePools constrain capacity type, zones, Linux/amd64, and allowed instance types from `config/capacity.yaml`. The chart selects its pool and capacity type explicitly and tolerates only its matching pool taint. Spot exhaustion leaves test workloads pending; there is no On-Demand fallback in this chart. Labels and taints are scheduling controls; operators must enforce who can create/patch workloads and modify their scheduling properties.

The Terraform module creates the system node group and Karpenter identity/queue resources. The Karpenter controller is installed separately into `kube-system` and must select the system nodes and tolerate `CriticalAddonsOnly=true:NoSchedule`. This breaks its dependency on the nodes it provisions. System nodes use one managed group per AZ/subnet, with total node-count inputs split equally across the three groups. This fixes placement granularity; sufficient failure capacity still requires measured sizing and live tests.

Terraform modules are split into `eks.tf` and `karpenter.tf`; `compute.tf` holds system node group settings. Karpenter dynamically creates application/test EC2 instances; existing database instances remain outside Terraform here.

The chart defaults to CPU HPA. Optional scheduled mode uses one KEDA ScaledObject with cron and CPU triggers, suppressing the standalone HPA. Production values contain the user-confirmed 17:00–22:00 America/New_York window; scheduled mode remains disabled until selected. KEDA and Metrics Server are external prerequisites. Six peak replicas are illustrative. The configured window has no measured pre-warm lead; adjust after startup measurements rather than assuming one.

## Capacity and availability

For each baseline, peak, and rollout scenario, verify CPU, RAM, pod/IP limits, service placement, and dependencies after losing each AZ. At even distribution, the theoretical lower bound is total usable production capacity of at least 1.5 times production demand; packing, overhead, rollout surge, and real topology constraints require additional analysis.

The dynamic NodePools here do not reserve this capacity. Consolidation can remove spare nodes. Implement and test an explicit reserve before treating the template as production-ready. The chart uses best-effort AZ spread (`ScheduleAnyway`) for demonstration; it does not prove AZ resilience. A PDB controls voluntary disruption, not an AZ outage or every forced node termination.

## Networking

The foundation enables VPC CNI NetworkPolicy support. It initially uses standard enforcement mode to allow system bootstrap. The namespace manifests deny application ingress/egress, then allow DNS only. Add narrow application/ingress, AWS API, and data-tier rules based on actual dependency flows. Test startup, rescheduling, and negative paths. System policies for CoreDNS, Karpenter, Pod Identity, and their dependencies must be installed and verified before changing to strict mode; strict is cluster-wide and initially denies new pod traffic. Do not enable strict blindly on an existing cluster.

## Versions

Terraform EKS module is pinned to 21.3.1; providers are locked by `.terraform.lock.hcl` after initialization. Module version is a tested configuration choice, not a claim to be the newest version. EKS and add-on versions, AMI ID, and controller chart version must be selected explicitly by the operator for compatibility. Runtime components have not been deployed or integration-tested by this repository's local checks.
