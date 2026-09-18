output "front_door" {
  description = "The control plane. With the default internal-load-balancer ingress this is reachable from inside the VPC or through a load balancer you put in front; it is not public."
  value       = google_cloud_run_v2_service.stack.uri
}

output "migrate_command" {
  description = "Run this before the first deploy and after every image bump — see compute.tf for why migrations are not in the service's startup path."
  value       = "gcloud run jobs execute ${google_cloud_run_v2_job.migrate.name} --region ${var.region} --wait"
}

output "artifacts_env" {
  description = "Points `pf artifacts` at this deployment's bucket over the GCS XML API. The HMAC pair is sensitive and comes from `tofu output -raw artifacts_key_id` / `artifacts_secret`."
  value = {
    PF_ARTIFACTS_ENDPOINT = "https://storage.googleapis.com"
    PF_ARTIFACTS_REGION   = var.region
    PF_ARTIFACTS_BUCKET   = google_storage_bucket.artifacts.name
  }
}

output "artifacts_key_id" {
  description = "HMAC access key id for the artefact bucket."
  value       = google_storage_hmac_key.artifacts.access_id
  sensitive   = true
}

output "artifacts_secret" {
  description = "HMAC secret for the artefact bucket."
  value       = google_storage_hmac_key.artifacts.secret
  sensitive   = true
}

output "database_host" {
  description = "Cloud SQL private IP. Reachable over the peered range only."
  value       = google_sql_database_instance.main.private_ip_address
}

output "search_host" {
  description = "Internal IP of the search node. No external address; reach it with `gcloud compute ssh --tunnel-through-iap`."
  value       = google_compute_instance.search.network_interface[0].network_ip
}
