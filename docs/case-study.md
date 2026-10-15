# ECS Fargate to Amazon EKS

## Challenge

Production and preprod ran continuously on ECS Fargate, with a daily peak of roughly five hours. The project sought lower overall AWS spending through capacity management, while planning for availability and controlled rollback.

## Work completed

The application platform moved to EKS across three Availability Zones. Karpenter manages application EC2 capacity, and HPA/KEDA scales replicas. Production and preprod share On-Demand capacity with namespace, resource, access, and network controls. System services run on dedicated On-Demand nodes. Irregular load tests use a separate Spot pool and isolated applications and data.

Terraform, Helm, and GitLab CI/CD support the delivery workflow. The migration followed a preprod proof of concept, phased production rollout, and rollback procedures. PostgreSQL, MongoDB, and ELK remain on EC2; PostgreSQL rightsizing was a separate optimization step.

## Result and evidence boundary

The freelancer confirms approximately **32% lower total AWS spending**, measured over a **90-day period**, from the combined migration and optimization work. No component-level attribution, actual bill amounts, exact comparison dates, workload normalization, or independently reviewed billing exports are available. This result is self-reported and does not predict savings from this template.

## Public reconstruction

This repository recreates selected implementation patterns using synthetic configuration. The diagram represents the broader source project. Terraform, render scripts, manifests, and tests were prepared for this public template; they are not the private production source or evidence of a live deployment.
