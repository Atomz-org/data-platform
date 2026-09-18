# The control plane: one Cloud Run service, and one Cloud Run job in front of it.
#
# ## Why the migrations are a separate job
#
# OpenMetadata runs schema migrations at start, and on a cold database they take
# minutes. Cloud Run's startup probe budget does not stretch that far, so a
# service that migrates on boot fails its probe, gets killed, restarts, begins
# the migration again, and presents as a crash loop that looks like a broken
# image. The AWS module solves this with a 600-second health-check grace period;
# Cloud Run has no equivalent, so the migration moves out of the request path
# entirely and the service starts with `PF_OM_MIGRATE=0`.
#
# Run it on first deploy and on every version bump, before the service rolls:
#
#   gcloud run jobs execute <name>-migrate --region <region> --wait
#
# ## Why min = max = 1
#
# The stack is one container running OpenMetadata, Dagster's webserver, its code
# servers and nginx. Two instances would be two Dagster daemons sharing one run
# storage schema, racing to launch the same schedules. Scaling this is a
# decomposition project, not a number change.

resource "google_service_account" "stack" {
  account_id   = "${local.name}-stack"
  display_name = "Control plane"
}

resource "google_project_iam_member" "stack_sql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.stack.email}"
}

resource "google_storage_bucket_iam_member" "stack_artifacts" {
  bucket = google_storage_bucket.artifacts.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.stack.email}"
}

resource "google_secret_manager_secret_iam_member" "stack" {
  for_each = local.stack_secrets

  secret_id = google_secret_manager_secret.stack[each.key].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.stack.email}"
}

locals {
  stack_env = {
    PF_REPO      = var.repo_path
    DAGSTER_HOME = "${var.repo_path}/.dagster-stack"

    PF_STACK_PG_HOST   = google_sql_database_instance.main.private_ip_address
    PF_STACK_PG_PORT   = "5432"
    PF_STACK_PG_DB     = google_sql_database.main.name
    PF_STACK_PG_SCHEMA = "dagster"

    OPENMETADATA_HOST_PORT = "http://127.0.0.1:8585"

    # GCS answers S3 on its XML API. The endpoint is the global one; the region
    # still has to be real, because SigV4 signs it.
    PF_ARTIFACTS_ENDPOINT = "https://storage.googleapis.com"
    PF_ARTIFACTS_REGION   = var.region
    PF_ARTIFACTS_BUCKET   = google_storage_bucket.artifacts.name

    SEARCH_TYPE   = "elasticsearch"
    SEARCH_HOST   = google_compute_instance.search.network_interface[0].network_ip
    SEARCH_PORT   = "9200"
    SEARCH_SCHEME = "http"
  }
}

resource "google_cloud_run_v2_job" "migrate" {
  name     = "${local.name}-migrate"
  location = var.region

  deletion_protection = false

  template {
    template {
      service_account = google_service_account.stack.email
      max_retries     = 1
      # Migrations are the long pole. An hour is generous rather than expected.
      timeout = "3600s"

      vpc_access {
        network_interfaces {
          network    = google_compute_network.main.id
          subnetwork = google_compute_subnetwork.main.id
        }
        egress = "PRIVATE_RANGES_ONLY"
      }

      containers {
        image = var.stack_image
        # The entrypoint's own migration prologue, then exit — same code in the
        # same order as a normal start, rather than a second copy of the
        # sequence here that would drift from the script.
        args = ["--migrate-only"]

        resources {
          limits = {
            cpu    = "2"
            memory = "4Gi"
          }
        }

        dynamic "env" {
          for_each = local.stack_env
          content {
            name  = env.key
            value = env.value
          }
        }

        env {
          name  = "PF_OM_MIGRATE"
          value = "1"
        }

        dynamic "env" {
          for_each = local.stack_secrets
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = google_secret_manager_secret.stack[env.key].secret_id
                version = "latest"
              }
            }
          }
        }
      }
    }
  }

  depends_on = [google_secret_manager_secret_version.stack]
}

resource "google_cloud_run_v2_service" "stack" {
  name     = local.name
  location = var.region
  ingress  = var.ingress

  deletion_protection = false

  template {
    service_account = google_service_account.stack.email
    # The catalogue serves large lineage payloads; the default 300s is short for
    # a first-load of a big project.
    timeout = "3600s"

    scaling {
      min_instance_count = 1
      max_instance_count = 1
    }

    vpc_access {
      network_interfaces {
        network    = google_compute_network.main.id
        subnetwork = google_compute_subnetwork.main.id
      }
      # Private ranges only: Cloud SQL and the search VM go through the VPC,
      # everything else takes Google's default egress. ALL_TRAFFIC would push
      # warehouse traffic through Cloud NAT for no benefit and a per-GB charge.
      egress = "PRIVATE_RANGES_ONLY"
    }

    containers {
      image = var.stack_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = var.service_cpu
          memory = var.service_memory
        }
        # Dagster's daemon and its schedules run between requests. With CPU
        # throttled to request handling they simply stop, and nothing reports it.
        cpu_idle          = false
        startup_cpu_boost = true
      }

      dynamic "env" {
        for_each = local.stack_env
        content {
          name  = env.key
          value = env.value
        }
      }

      # Migrations belong to the job above. Leaving this at 1 reintroduces the
      # crash loop this file's header describes.
      env {
        name  = "PF_OM_MIGRATE"
        value = "0"
      }

      dynamic "env" {
        for_each = local.stack_secrets
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.stack[env.key].secret_id
              version = "latest"
            }
          }
        }
      }

      startup_probe {
        # Even without migrations, OpenMetadata and eight code servers take
        # time. 40 × 15s is ten minutes before Cloud Run gives up.
        initial_delay_seconds = 30
        period_seconds        = 15
        timeout_seconds       = 10
        failure_threshold     = 40

        tcp_socket {
          port = 8080
        }
      }

      liveness_probe {
        initial_delay_seconds = 60
        period_seconds        = 30
        timeout_seconds       = 10
        failure_threshold     = 5

        http_get {
          path = "/"
          port = 8080
        }
      }
    }
  }

  depends_on = [google_secret_manager_secret_version.stack]
}

# Who may reach it. `allUsers` is behind a variable that defaults to false: the
# control plane has no authentication of its own and Dagster's UI launches runs.
resource "google_cloud_run_v2_service_iam_member" "public" {
  count = var.allow_unauthenticated ? 1 : 0

  name     = google_cloud_run_v2_service.stack.name
  location = google_cloud_run_v2_service.stack.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "invokers" {
  for_each = var.allow_unauthenticated ? toset([]) : toset(var.invoker_members)

  name     = google_cloud_run_v2_service.stack.name
  location = google_cloud_run_v2_service.stack.location
  role     = "roles/run.invoker"
  member   = each.value
}
