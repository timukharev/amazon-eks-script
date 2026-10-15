# Security and public-content boundary

The template and diagram contain synthetic resource names and generic architectural patterns. No private repository files, Git history, client identities, credentials, account numbers, internal endpoints, bills, state, or database material were imported. The public case study contains user-authorized summary facts, including the self-reported cost outcome.

## Runtime limitations

- Kubernetes namespaces share a control plane and worker nodes may share a kernel. This is a trusted-team reference, not hostile multi-tenancy isolation.
- Chart node selectors, capacity selectors, and taints constrain these examples. They do not stop someone who can change a Pod spec from choosing other pools. The optional admission manifest provides namespace/pool/priority/toleration checks, but its CEL still requires live API-server acceptance testing. Enforce host/privilege restrictions through Pod Security, and complete RBAC, bindings, secret/IAM access, and negative tests before expanding access.
- Restricted Pod Security prevents many host/privilege settings in the sample namespaces. IAM/Pod Identity, production secrets, database permissions, and production security-group rules remain operator responsibilities. Nonproduction must use its own data and credentials.
- Default-deny and DNS policies require an enforcing CNI. Standard mode has a startup allowance window; strict mode requires all system dependency policies first. Policy behavior, API access, DNS, health checks, and negative paths need live testing.
- The sample application's service is internal and no ingress permission is supplied. Add precise ingress rules; do not turn a test into an unrestricted production endpoint.
- Karpenter can consolidate unused capacity and create billable EC2 resources. Limits/disruption budgets are not a proven failure reserve, a hard currency budget, or a defense against every forced termination. Spot has no availability guarantee and is used only for isolated tests here.
- A manually supplied load-test URL does not prove safety. Use dedicated runner placement, network isolation, separate data, and restricted identities; no production credentials should be available to the test job.
- EKS admin access is intentionally powerful and must be restricted. Node IAM policy, CNI permission separation, encryption, audit retention, registry trust, dependency/image updates, and state encryption/locking need operator review for each environment.

## Publication review

Review tracked files, Git diff/history, SVG strings, and image content. Scan for credentials, tokens, personal information, private domains/IPs, account identifiers, and encoded material. Ignore rules cannot remove secrets already committed. Never publish private tfvars, state, plans, rendered environment-specific capacity files, or real billing inputs. Revoke any exposed credential before cleaning history.

GitHub's secret-scan workflow runs only after publication. A local scan and manual review must precede the first commit. Local tests do not validate a live EKS cluster or guarantee absence of every secret.
