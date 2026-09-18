# The VPC. Public subnets carry the load balancer and the NAT gateway; the task,
# the database and the search domain sit in private subnets and reach the
# internet outbound only.
#
# Written as native resources rather than terraform-aws-modules/vpc so this root
# module has no registry dependency: one `tofu init` against the AWS provider is
# the whole bootstrap, and nothing here changes shape when a community module
# releases a major.

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  name = "${var.name_prefix}-${var.env}"
  azs  = slice(data.aws_availability_zones.available.names, 0, var.az_count)
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = local.name }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = local.name }
}

resource "aws_subnet" "public" {
  count = var.az_count

  vpc_id                  = aws_vpc.main.id
  availability_zone       = local.azs[count.index]
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  map_public_ip_on_launch = true

  tags = { Name = "${local.name}-public-${local.azs[count.index]}" }
}

resource "aws_subnet" "private" {
  count = var.az_count

  vpc_id            = aws_vpc.main.id
  availability_zone = local.azs[count.index]
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 100)

  tags = { Name = "${local.name}-private-${local.azs[count.index]}" }
}

# One NAT gateway, not one per AZ. A second costs the same as a small database
# and buys AZ-failure tolerance for *outbound* traffic only — which for a
# control plane that is already single-task is not the weakest link.
resource "aws_eip" "nat" {
  domain = "vpc"
  tags   = { Name = "${local.name}-nat" }
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id
  depends_on    = [aws_internet_gateway.main]

  tags = { Name = local.name }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = { Name = "${local.name}-public" }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }

  tags = { Name = "${local.name}-private" }
}

resource "aws_route_table_association" "public" {
  count          = var.az_count
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count          = var.az_count
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# ---------------------------------------------------------------- groups --
resource "aws_security_group" "alb" {
  name        = "${local.name}-alb"
  description = "Front door. Only what var.ingress_cidrs names."
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "front door"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = var.ingress_cidrs
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name}-alb" }
}

resource "aws_security_group" "task" {
  name        = "${local.name}-task"
  description = "The stack task. Reachable only from the load balancer."
  vpc_id      = aws_vpc.main.id

  # 8585 and 3000 are deliberately not here. Locally they are published so the
  # ingestion CLI and `dagster` clients can bypass nginx; in the cloud that
  # would be two more unauthenticated ways in, and the front door already
  # proxies both.
  ingress {
    description     = "front door only"
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name}-task" }
}

resource "aws_security_group" "data" {
  name        = "${local.name}-data"
  description = "Postgres and OpenSearch. Reachable only from the task."
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "postgres"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.task.id]
  }

  ingress {
    description     = "opensearch"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.task.id]
  }

  tags = { Name = "${local.name}-data" }
}
