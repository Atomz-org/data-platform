# Postgres, the bucket and the secret. Search is in search.tf, because on GCP it
# is a VM rather than a managed service and that deserves its own file and its
# own explanation.

# ------------------------------------------------------------- postgres --
resource "random_password" "db" {
  length           = 32
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "google_sql_database_instance" "main" {
  name             = local.name
  database_version = "POSTGRES_16"
  region           = var.region

  # On by default here, unlike the usual example. This instance holds
  # OpenMetadata's catalogue and Dagster's entire run history; a `tofu destroy`
  # that takes it silently is not a recoverable mistake.
  deletion_protection = true

  settings {
    tier              = var.db_tier
    disk_size         = var.db_disk_size
    disk_type         = "PD_SSD"
    disk_autoresize   = true
    availability_type = "ZONAL"

    ip_configuration {
      # Private only. The stack reaches it over the peered range.
      ipv4_enabled    = false
      private_network = google_compute_network.main.id
      ssl_mode        = "ENCRYPTED_ONLY"
    }

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "03:00"
    }

    maintenance_window {
      day          = 7
      hour         = 4
      update_track = "stable"
    }
  }

  depends_on = [google_service_networking_connection.main]
}

resource "google_sql_database" "main" {
  name     = "openmetadata_db"
  instance = google_sql_database_instance.main.name
}

# One user. The `public` / `dagster` schema split inside the database is done by
# `pf stack db-init` — it is application layout and belongs to the application.
resource "google_sql_user" "main" {
  name     = "pfadmin"
  instance = google_sql_database_instance.main.name
  password = random_password.db.result
}

# --------------------------------------------------------------- bucket --
resource "google_storage_bucket" "artifacts" {
  name     = "${local.name}-artifacts-${var.project_id}"
  location = var.region

  # Uniform access, not per-object ACLs: `pf.artifacts` never sets an ACL and
  # object-level permissions are how a bucket ends up world-readable.
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      days_since_noncurrent_time = 90
    }
    action {
      type = "Delete"
    }
  }

  lifecycle_rule {
    condition {
      age = 7
    }
    action {
      type = "AbortIncompleteMultipartUpload"
    }
  }
}

# `pf.artifacts` speaks S3, and GCS answers S3 on its XML API — but only with an
# HMAC key pair, not with a service-account JSON. This is that pair. It is the
# single least obvious thing about running this platform on GCP: every other GCP
# integration wants the JSON key, and the JSON key does not work here.
resource "google_service_account" "artifacts" {
  account_id   = "${local.name}-artifacts"
  display_name = "Artefact store HMAC identity"
}

resource "google_storage_hmac_key" "artifacts" {
  service_account_email = google_service_account.artifacts.email
}

resource "google_storage_bucket_iam_member" "artifacts_hmac" {
  bucket = google_storage_bucket.artifacts.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.artifacts.email}"
}

# --------------------------------------------------------------- secrets --
# One secret per environment variable, which is where this diverges from the AWS
# module's single JSON blob. ECS can inject one key out of a JSON secret with a
# `valueFrom` suffix; Cloud Run's `secret_key_ref` injects the whole value and
# has no equivalent, so a JSON blob here would arrive as a literal `{"..."}` in
# the variable. Splitting them is the only shape that works, not a preference.
locals {
  stack_secrets = merge(var.warehouse_env, {
    PF_STACK_PG_USER               = google_sql_user.main.name
    PF_STACK_PG_PASSWORD           = random_password.db.result
    PF_STACK_PG_ADMIN_USER         = google_sql_user.main.name
    PF_STACK_PG_ADMIN_PASSWORD     = random_password.db.result
    PF_ARTIFACTS_ACCESS_KEY_ID     = google_storage_hmac_key.artifacts.access_id
    PF_ARTIFACTS_SECRET_ACCESS_KEY = google_storage_hmac_key.artifacts.secret
  })
}

resource "google_secret_manager_secret" "stack" {
  for_each = local.stack_secrets

  secret_id = "${local.name}-${each.key}"

  replication {
    auto {}
  }

  depends_on = [google_project_service.main]
}

resource "google_secret_manager_secret_version" "stack" {
  for_each = local.stack_secrets

  secret      = google_secret_manager_secret.stack[each.key].id
  secret_data = each.value
}
