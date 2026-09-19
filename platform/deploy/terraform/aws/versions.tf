# Pinned to majors, not to exact versions. A root module that pins an exact
# provider stops receiving security fixes the day it is written, and the pin is
# always discovered during an incident.
terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Platform  = "data-platform"
      Component = "control-plane"
      ManagedBy = "opentofu"
      Env       = var.env
    }
  }
}
