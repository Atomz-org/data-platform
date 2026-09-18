# The three stateful things: one Postgres, one search domain, one bucket.
#
# `platform/deploy/compose.yaml` keeps all three out of the stack image on
# purpose — they are stateful, they have their own upgrade cycles, and folding a
# database into an application image is how you lose the database. That reasoning
# survives the move to managed services unchanged; this file is the same split
# expressed in AWS.

# ------------------------------------------------------------- postgres --
# One instance, two schemas: `public` for OpenMetadata, `dagster` for Dagster's
# run and event storage. The schema split is done by `pf stack db-init`, not
# here — it is application layout, and Terraform recreating it would fight the
# application that owns it.
resource "random_password" "db" {
  length = 32
  # RDS rejects `/`, `@`, `"` and space in a master password. Excluding them
  # here rather than discovering it on apply.
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "aws_db_subnet_group" "main" {
  name       = local.name
  subnet_ids = aws_subnet.private[*].id
  tags       = { Name = local.name }
}

resource "aws_db_instance" "main" {
  identifier     = local.name
  engine         = "postgres"
  engine_version = "16"

  instance_class        = var.db_instance_class
  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_allocated_storage * 4
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "openmetadata_db"
  username = "pfadmin"
  password = random_password.db.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.data.id]
  publicly_accessible    = false

  backup_retention_period   = 7
  skip_final_snapshot       = false
  final_snapshot_identifier = "${local.name}-final"
  deletion_protection       = true

  # Minor versions only. A major upgrade meets the old data directory and is a
  # dump-and-restore decision, exactly as the compose comment says.
  auto_minor_version_upgrade  = true
  allow_major_version_upgrade = false

  tags = { Name = local.name }
}

# ---------------------------------------------------------------- search --
# OpenSearch rather than Elasticsearch: OpenMetadata supports both, and this is
# the one AWS runs as a managed service. The compose stack's Elasticsearch pin
# does not transfer — check OpenMetadata's supported search versions before
# moving this, and reindex with PF_OM_REINDEX=recreate on the first run after.
resource "aws_opensearch_domain" "main" {
  domain_name    = local.name
  engine_version = "OpenSearch_2.11"

  cluster_config {
    instance_type          = var.search_instance_type
    instance_count         = var.search_instance_count
    zone_awareness_enabled = var.search_zone_awareness

    dynamic "zone_awareness_config" {
      for_each = var.search_zone_awareness ? [1] : []
      content {
        availability_zone_count = var.az_count
      }
    }
  }

  ebs_options {
    ebs_enabled = true
    volume_size = 20
    volume_type = "gp3"
  }

  vpc_options {
    # One subnet per node when zone awareness is off; AWS requires the counts
    # to line up, and a mismatch fails at apply with a message about subnets
    # rather than about zone awareness.
    subnet_ids         = slice(aws_subnet.private[*].id, 0, var.search_zone_awareness ? var.az_count : 1)
    security_group_ids = [aws_security_group.data.id]
  }

  encrypt_at_rest {
    enabled = true
  }

  node_to_node_encryption {
    enabled = true
  }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }

  tags = { Name = local.name }
}

# ---------------------------------------------------------------- bucket --
# The artefact store. `pf.artifacts` writes keys that mirror the repository, so
# the bucket reads like a checkout — nothing here needs to know that layout.
resource "aws_s3_bucket" "artifacts" {
  bucket = "${local.name}-artifacts"
  tags   = { Name = "${local.name}-artifacts" }
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Versioning is on because the keys are ref-scoped but not immutable: two runs
# on the same branch overwrite one baseline, and recovering the previous one is
# otherwise impossible.
resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Baselines and reviews are worth keeping for as long as the branch that made
# them is open, not forever. Ninety days is a guess that errs long; shorten it
# once you know your own review cadence.
resource "aws_s3_bucket_lifecycle_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    id     = "expire-noncurrent"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 90
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# --------------------------------------------------------------- secrets --
# One secret holding the whole environment block, rather than one per key.
# ECS injects secrets per environment variable, so a secret per credential would
# be N API calls on every task start and N resources to keep in agreement with
# `pf.runtime.targets`.
resource "aws_secretsmanager_secret" "stack" {
  name        = "${local.name}/stack"
  description = "Warehouse and database credentials for the control plane."

  # Zero, not the default seven days. A recreated stack in the same account
  # would otherwise collide with the scheduled-for-deletion secret of the last
  # one and fail on a name that appears not to exist.
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "stack" {
  secret_id = aws_secretsmanager_secret.stack.id

  secret_string = jsonencode(merge(var.warehouse_env, {
    POSTGRES_USER     = aws_db_instance.main.username
    POSTGRES_PASSWORD = random_password.db.result
  }))
}
