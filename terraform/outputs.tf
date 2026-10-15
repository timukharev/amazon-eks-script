output "cluster_name" { value = module.eks.cluster_name }
output "cluster_endpoint" { value = module.eks.cluster_endpoint }
output "node_security_group_id" { value = module.eks.node_security_group_id }
output "karpenter_node_role_name" { value = module.karpenter.node_iam_role_name }
output "karpenter_interruption_queue" { value = module.karpenter.queue_name }

output "karpenter_controller_settings" {
  description = "Controller chart settings derived from provisioned resources; store generated output outside Git."
  value = {
    settings = {
      clusterName       = module.eks.cluster_name
      clusterEndpoint   = module.eks.cluster_endpoint
      interruptionQueue = module.karpenter.queue_name
    }
  }
}
