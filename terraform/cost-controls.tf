resource "aws_budgets_budget" "account_monthly" {
  count        = var.cost_budget == null ? 0 : 1
  name         = "${var.name}-account-cost"
  budget_type  = "COST"
  limit_amount = tostring(var.cost_budget.monthly_limit_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator       = "GREATER_THAN"
    threshold                 = 80
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_sns_topic_arns = [var.cost_budget.sns_topic_arn]
  }
}
