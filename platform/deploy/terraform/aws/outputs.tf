output "front_door" {
  description = "The control plane. Same paths as the local stack: / is OpenMetadata, /dagster/ is Dagster, /recce/<project> is that project's review."
  value       = "http://${aws_lb.front.dns_name}:8080"
}

output "artifacts_env" {
  description = "Export these to point `pf artifacts` at this deployment's bucket. The credential pair comes from your own IAM user or role — in the task it comes from the task role instead."
  value = {
    PF_ARTIFACTS_ENDPOINT = "https://s3.${var.region}.amazonaws.com"
    PF_ARTIFACTS_REGION   = var.region
    PF_ARTIFACTS_BUCKET   = aws_s3_bucket.artifacts.id
  }
}

output "database_host" {
  description = "Postgres endpoint. Private — reachable from the task security group only."
  value       = aws_db_instance.main.address
}

output "search_endpoint" {
  value       = aws_opensearch_domain.main.endpoint
  description = "OpenSearch domain endpoint, HTTPS on 443."
}

output "secret_arn" {
  description = "Where warehouse credentials live. Rotate by writing a new version; the task picks it up on next start."
  value       = aws_secretsmanager_secret.stack.arn
}

output "log_group" {
  value = aws_cloudwatch_log_group.stack.name
}
