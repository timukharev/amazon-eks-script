# Existing EC2 data tier

The source plan retains three PostgreSQL nodes, three MongoDB nodes, and three ELK nodes on EC2. This repository does not recreate them, import state, select a new HA manager, shard PostgreSQL, or automate resizing.

## PostgreSQL rightsizing procedure

1. Record current instance/EBS sizes, HA roles and manager, backups, and rollback options privately. Establish measured CPU, working set/cache, I/O, replication lag, connections, and peak capacity for every possible primary.
2. Test restored, isolated copies and verify backups/restore against agreed RPO/RTO. The exact commands depend on the existing HA tooling and cannot be inferred from the plan.
3. Keep database rightsizing in a separate window after application migration stabilizes. Change one replica at a time, verify health/replication, perform a controlled switchover, then handle the former primary according to the established HA runbook.
4. Keep a reviewed return path to previous EC2/EBS sizes and settings. Stop on violated thresholds; do not treat lower CPU averages as proof that cache/I/O capacity can shrink.
5. Record database savings separately from application hosting; do not add overlapping percentages to the total-bill result.

MongoDB changes require a separate study. ELK storage/retention/index/shard changes require their own capacity and recovery review. The application migration does not imply either change was implemented.

Production connects through explicitly approved network and database permissions. Preprod and testing need separate data, endpoints, users, and secrets; tests must not reach production directly or through a test application's dependencies. No production address or credential is included in this repository.

## Live acceptance evidence

Keep restore/failover results, baseline/peak latency, replication behavior, approved maintenance windows, access-denial tests, and rollback evidence in private operational records. The public runbook is a procedure, not evidence of successful execution.
