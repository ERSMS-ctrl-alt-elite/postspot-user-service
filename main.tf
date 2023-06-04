/* -------------------------------------------------------------------------- */
/*                          Define Cloud Run service                          */
/* -------------------------------------------------------------------------- */
resource "google_cloud_run_v2_service" "default" {
  name     = "user-service"
  location = "europe-central2"
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      image = "europe-central2-docker.pkg.dev/postspot-388715/postspot/user-service:latest"
    }
  }
}

/* -------------------------------------------------------------------------- */
/*                  Allow public access for Cloud Run service                 */
/* -------------------------------------------------------------------------- */
data "google_iam_policy" "noauth" {
  binding {
    role = "roles/run.invoker"
    members = [
      "allUsers",
    ]
  }
}

resource "google_cloud_run_service_iam_policy" "noauth" {
  location = google_cloud_run_v2_service.default.location
  project  = google_cloud_run_v2_service.default.project
  service  = google_cloud_run_v2_service.default.name

  policy_data = data.google_iam_policy.noauth.policy_data
}