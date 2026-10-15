# Migration runbook

This is a reusable operator checklist, not evidence of a migration executed by this template.

1. **Baseline:** inventory services, dependencies, ECS desired/min/max settings, CPU/RAM percentiles, latency, errors, queue depth, DB connections, discounts, and a clearly scoped AWS cost baseline. Agree SLOs, owner, cutover authority, and rollback thresholds before moving traffic.
2. **Compare options:** model optimized Fargate, ECS on EC2, and EKS with the same workload/availability assumptions. Include cluster fees, system overhead, reserves, networking, storage, labor, upgrade support, and temporary dual-running. Attribute database rightsizing separately.
3. **Prepare EKS:** confirm system bootstrap, controllers, capacity bounds, IAM, namespace isolation, secret management, application dependencies, and observability. Calculate and protect capacity for peak load after each possible AZ failure. Do not substitute three available AZs for an actual reserve.
4. **Preprod proof:** run a representative API and worker with isolated data; verify scale-out/in, consolidation, rollout surge, negative network tests, test-pool isolation, and chosen failure scenarios. Measure startup and warm-up; add scheduling of minimum capacity before predictable peaks if required.
5. **Prepare each wave:** fix image/configuration versions, maintain API/database compatibility, keep ECS deployment capacity ready, rehearse traffic reversal, and define queue-drain/idempotency rules. Avoid concurrent database downsizing or irreversible schema changes.
6. **Cut over:** move agreed traffic increments using the application's reviewed ALB/DNS/routing mechanism. Observe SLOs and dependencies through the peak and the agreed stability window. Transition workers separately so messages are not processed twice.
7. **Rollback on threshold breach:** halt promotion; route back to the ready ECS deployment; stop/drain EKS workers; confirm errors, queues, DB health, and correct routing. Record what happened and preserve diagnostic evidence privately. Exact traffic commands are environment-specific and deliberately absent.
8. **Retire and optimize:** remove old resources only after acceptance and the rollback window. Tune requests and replicas, then node consolidation, while retaining protected failure capacity. Handle PostgreSQL rightsizing in its own tested window; retain rollback and backup/restore procedures.
9. **Measure:** compare agreed periods using consistent net/amortized/unblended cost, workload, and discount treatment. Include shared overhead and retained resources. The cost tool can check arithmetic and window lengths; workload comparability requires human review.

No source-project zero-downtime, specific rollback time, SLO attainment, or exact project duration is claimed here. No command in this repository switches production traffic.
