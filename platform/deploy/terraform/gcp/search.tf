# OpenMetadata's search index, on one VM.
#
# ## Why this is not a managed service
#
# GCP has no first-party managed Elasticsearch or OpenSearch. The alternatives
# were:
#
#   Elastic Cloud on GCP   a marketplace subscription and a second vendor
#                          relationship, for one index of ~1200 tables
#   GKE Autopilot          a cluster, its upgrades and its bill, to run one pod
#   one VM                 this
#
# For a single-node search index behind a single-task control plane, the VM is
# the honest answer: the other two buy high availability that the stack in front
# of them does not have. Move to Elastic Cloud when the control plane itself
# stops being one container, not before.
#
# ## What this is not
#
# Not highly available, not backed up, and not authenticated —
# `xpack.security.enabled` is off, exactly as in `compose.yaml`. The firewall
# rule in network.tf is the entire access control, which is why it is scoped to
# the subnet and tagged rather than open.
#
# None of that is a gap to fix later: the index is *derived*. It is rebuilt from
# Postgres with `PF_OM_REINDEX=recreate`, so losing this disk costs a reindex
# and no data. Backing it up would be backing up a cache.

resource "google_compute_disk" "search" {
  name = "${local.name}-search"
  type = "pd-ssd"
  zone = var.zone
  size = var.search_disk_size

  lifecycle {
    # The disk outliving a VM replacement is the point: a machine-type change
    # should not cost a reindex.
    prevent_destroy = true
  }
}

resource "google_service_account" "search" {
  account_id   = "${local.name}-search"
  display_name = "Search node"
}

resource "google_compute_instance" "search" {
  name         = "${local.name}-search"
  machine_type = var.search_machine_type
  zone         = var.zone
  tags         = ["${local.name}-search"]

  boot_disk {
    initialize_params {
      # Container-Optimized OS: it runs a container from metadata and has no
      # package manager to drift.
      image = "cos-cloud/cos-stable"
      size  = 20
      type  = "pd-balanced"
    }
  }

  attached_disk {
    source      = google_compute_disk.search.id
    device_name = "search-data"
  }

  network_interface {
    network    = google_compute_network.main.id
    subnetwork = google_compute_subnetwork.main.id
    # No access_config block, so no external IP. Egress is through Cloud NAT;
    # reach it with `gcloud compute ssh --tunnel-through-iap`.
  }

  service_account {
    email  = google_service_account.search.email
    scopes = ["cloud-platform"]
  }

  metadata = {
    # Formats the data disk on first boot only — `mkfs.ext4 -F` would reformat
    # on every boot and silently discard the index. `-n` checks for an existing
    # filesystem and does nothing if one is there.
    startup-script = <<-EOT
      #!/bin/bash
      set -euo pipefail
      DISK=/dev/disk/by-id/google-search-data
      MOUNT=/mnt/disks/search

      mkdir -p "$MOUNT"
      if ! blkid "$DISK" >/dev/null 2>&1; then
        mkfs.ext4 -m 0 -E lazy_itable_init=0,lazy_journal_init=0,discard "$DISK"
      fi
      mountpoint -q "$MOUNT" || mount -o discard,defaults "$DISK" "$MOUNT"
      # Elasticsearch runs as uid 1000 in its image and will not start if it
      # cannot write here.
      chown -R 1000:1000 "$MOUNT"

      # mmapfs wants more than the COS default, and Elasticsearch refuses to
      # start below 262144 rather than degrading.
      sysctl -w vm.max_map_count=262144

      docker rm -f search >/dev/null 2>&1 || true
      docker run -d --name search --restart always \
        -p 9200:9200 \
        -e discovery.type=single-node \
        -e xpack.security.enabled=false \
        -e ES_JAVA_OPTS="${var.search_heap}" \
        -v "$MOUNT":/usr/share/elasticsearch/data \
        ${var.search_image}
    EOT
  }

  allow_stopping_for_update = true
}
