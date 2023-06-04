resource "google_cloud_run_v2_service" "default" {
  name     = "user-service"
  location = "europe-central2"
  ingress = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      image = "europe-central2-docker.pkg.dev/postspot-388715/postspot/user-service:latest"
    }
  }
}