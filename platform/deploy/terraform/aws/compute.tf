# One Fargate task behind one ALB.
#
# ## Why one task and not a service with N
#
# The stack image runs OpenMetadata, Dagster's webserver, up to eight Dagster
# code servers, the recce servers and nginx together, and Dagster's code
# locations hold absolute paths into a repository baked into the image. Two
# replicas would be two independent Dagster instances sharing one run-storage
# schema, racing to launch the same schedules. Scaling this is a decomposition
# project, not a `desired_count` change, so the count is pinned at 1 and the
# comment is here rather than in a runbook.

resource "aws_cloudwatch_log_group" "stack" {
  name              = "/aws/ecs/${local.name}"
  retention_in_days = 30
}

resource "aws_ecs_cluster" "main" {
  name = local.name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# ------------------------------------------------------------------- iam --
data "aws_iam_policy_document" "assume_ecs" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# Pulls the image and reads the secret at task start. Distinct from the task
# role below: this one is used by the ECS agent, not by the process, so a
# compromise of the container does not carry it.
resource "aws_iam_role" "execution" {
  name               = "${local.name}-execution"
  assume_role_policy = data.aws_iam_policy_document.assume_ecs.json
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "read_secret" {
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.stack.arn]
  }
}

resource "aws_iam_role_policy" "execution_secret" {
  name   = "read-stack-secret"
  role   = aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.read_secret.json
}

# What the running process may do. Only the artefact bucket — the warehouse is
# reached with its own credentials, and the database with a password, so
# neither belongs in an IAM policy.
resource "aws_iam_role" "task" {
  name               = "${local.name}-task"
  assume_role_policy = data.aws_iam_policy_document.assume_ecs.json
}

data "aws_iam_policy_document" "artifacts" {
  statement {
    actions   = ["s3:ListBucket", "s3:GetBucketLocation"]
    resources = [aws_s3_bucket.artifacts.arn]
  }

  statement {
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.artifacts.arn}/*"]
  }
}

resource "aws_iam_role_policy" "task_artifacts" {
  name   = "artifact-store"
  role   = aws_iam_role.task.id
  policy = data.aws_iam_policy_document.artifacts.json
}

# ------------------------------------------------------------------ task --
locals {
  # `pf.stack.storage` reads exactly these names. PF_STACK_PG_SCHEMA is what
  # keeps Dagster's 22 tables out of OpenMetadata's 176 — the compose file's
  # comment on this is emphatic and it applies identically here.
  stack_env = {
    PF_REPO      = var.repo_path
    DAGSTER_HOME = "${var.repo_path}/.dagster-stack"

    PF_STACK_PG_HOST   = aws_db_instance.main.address
    PF_STACK_PG_PORT   = tostring(aws_db_instance.main.port)
    PF_STACK_PG_DB     = aws_db_instance.main.db_name
    PF_STACK_PG_SCHEMA = "dagster"

    OPENMETADATA_HOST_PORT = "http://127.0.0.1:8585"

    # The artefact store, reached with the task role rather than a key pair.
    # boto3 picks up the Fargate credential endpoint on its own; `Store.from_env`
    # still needs a non-empty pair, so the bucket and region are set here and
    # the key pair comes from the secret. See docs/ARTIFACTS.md.
    PF_ARTIFACTS_BUCKET   = aws_s3_bucket.artifacts.id
    PF_ARTIFACTS_REGION   = var.region
    PF_ARTIFACTS_ENDPOINT = "https://s3.${var.region}.amazonaws.com"

    # OpenMetadata's search. The managed domain speaks HTTPS on 443, unlike the
    # compose stack's plaintext 9200.
    SEARCH_TYPE   = "opensearch"
    SEARCH_HOST   = aws_opensearch_domain.main.endpoint
    SEARCH_PORT   = "443"
    SEARCH_SCHEME = "https"
  }

  # Injected from Secrets Manager by key, so none of these appear in the task
  # definition — which is readable by anyone with ecs:DescribeTaskDefinition.
  stack_secrets = merge(
    { for k in keys(var.warehouse_env) : k => k },
    {
      PF_STACK_PG_USER           = "POSTGRES_USER"
      PF_STACK_PG_PASSWORD       = "POSTGRES_PASSWORD"
      PF_STACK_PG_ADMIN_USER     = "POSTGRES_USER"
      PF_STACK_PG_ADMIN_PASSWORD = "POSTGRES_PASSWORD"
    },
  )
}

resource "aws_ecs_task_definition" "stack" {
  family                   = local.name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([
    {
      name      = "stack"
      image     = var.stack_image
      essential = true

      portMappings = [
        { containerPort = 8080, protocol = "tcp" },
      ]

      environment = [
        for k, v in local.stack_env : { name = k, value = v }
      ]

      secrets = [
        for env_name, json_key in local.stack_secrets : {
          name      = env_name
          valueFrom = "${aws_secretsmanager_secret.stack.arn}:${json_key}::"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.stack.name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "stack"
        }
      }

      # OpenMetadata's migrations run at start and are slow. A health check that
      # gives up before they finish puts the service in a crash loop that looks
      # like a broken image.
      healthCheck = {
        command     = ["CMD-SHELL", "curl -sf http://localhost:8080/ || exit 1"]
        interval    = 30
        timeout     = 10
        retries     = 5
        startPeriod = 600
      }
    }
  ])
}

resource "aws_ecs_service" "stack" {
  name            = local.name
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.stack.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  # The stack is not two-replica safe (see the header). A rolling deploy that
  # briefly runs two would have two Dagster daemons on one schema.
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100

  # Ten minutes, matching the health check's start period. OpenMetadata's
  # migrations are the reason both numbers are large.
  health_check_grace_period_seconds = 600

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.task.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.stack.arn
    container_name   = "stack"
    container_port   = 8080
  }

  depends_on = [aws_lb_listener.front]
}

# ------------------------------------------------------------------- alb --
resource "aws_lb" "front" {
  name               = local.name
  load_balancer_type = "application"
  internal           = false
  subnets            = aws_subnet.public[*].id
  security_groups    = [aws_security_group.alb.id]

  # The control plane has no auth of its own in front of Dagster. Dropping the
  # log is dropping the only record of who reached it.
  enable_deletion_protection = true
}

resource "aws_lb_target_group" "stack" {
  name        = local.name
  port        = 8080
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = aws_vpc.main.id

  health_check {
    path                = "/"
    matcher             = "200-399"
    interval            = 30
    timeout             = 10
    healthy_threshold   = 2
    unhealthy_threshold = 5
  }

  # The catalogue and Dagster both keep session state in cookies; without
  # stickiness a second replica would log people out at random. It is set even
  # though the count is 1, so raising the count is not silently a regression.
  stickiness {
    type            = "lb_cookie"
    enabled         = true
    cookie_duration = 86400
  }
}

# Plain HTTP on 8080, matching the front door's local contract. TLS is the first
# thing to add for anything but a private network: put an ACM certificate on a
# 443 listener and redirect this one. Left out rather than half-done, because a
# certificate needs a domain this module does not own.
resource "aws_lb_listener" "front" {
  load_balancer_arn = aws_lb.front.arn
  port              = 8080
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.stack.arn
  }
}
