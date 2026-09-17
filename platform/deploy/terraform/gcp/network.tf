locals {
  name = "${var.name_prefix}-${var.env}"

  apis = [
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "compute.googleapis.com",
    "servicenetworking.googleapis.com",
    "artifactregistry.googleapis.com",
  ]
}

resource "google_project_service" "main" {
  for_each = var.enable_apis ? toset(local.apis) : toset([])

  service = each.value
  # Leaving an API enabled on destroy is the safe default: another stack in the
  # same project may depend on it, and disabling one is not a local decision.
  disable_on_destroy = false
}

resource "google_compute_network" "main" {
  name                    = local.name
  auto_create_subnetworks = false
  depends_on              = [google_project_service.main]
}

resource "google_compute_subnetwork" "main" {
  name          = local.name
  network       = google_compute_network.main.id
  region        = var.region
  ip_cidr_range = var.subnet_cidr

  # Cloud Run direct VPC egress allocates from this subnet, and so does the
  # search VM. Private Google Access lets both reach Google APIs without a
  # public address — without it, Secret Manager calls from the VM fail.
  private_ip_google_access = true
}

# Cloud SQL with a private IP needs a peered range reserved to the service
# producer network. This is the pair of resources that makes `ipv4_enabled =
# false` possible; without them the instance can only be reached over the
# public internet with an authorised-networks list.
resource "google_compute_global_address" "private_ip" {
  name          = "${local.name}-sql"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.main.id
}

resource "google_service_networking_connection" "main" {
  network                 = google_compute_network.main.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip.name]

  depends_on = [google_project_service.main]
}

# Egress to the internet for the search VM, which has no external address. The
# stack's Cloud Run service reaches Google APIs directly and only needs this for
# anything outside Google — a warehouse endpoint, for instance.
resource "google_compute_router" "main" {
  name    = local.name
  network = google_compute_network.main.id
  region  = var.region
}

resource "google_compute_router_nat" "main" {
  name                               = local.name
  router                             = google_compute_router.main.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# ------------------------------------------------------------- firewall --
# Search is reachable from inside the subnet only. There is no authentication on
# this Elasticsearch — `xpack.security.enabled` is off, matching the compose
# stack — so subnet-scoped is doing the whole job and must not be widened.
resource "google_compute_firewall" "search" {
  name      = "${local.name}-search"
  network   = google_compute_network.main.name
  direction = "INGRESS"

  source_ranges = [var.subnet_cidr]
  target_tags   = ["${local.name}-search"]

  allow {
    protocol = "tcp"
    ports    = ["9200"]
  }
}

# IAP's range, for `gcloud compute ssh --tunnel-through-iap` onto a VM with no
# external address. Debugging a search node otherwise means giving it one.
resource "google_compute_firewall" "iap_ssh" {
  name      = "${local.name}-iap-ssh"
  network   = google_compute_network.main.name
  direction = "INGRESS"

  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["${local.name}-search"]

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}
