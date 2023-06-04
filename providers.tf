terraform {
  backend "gcs" {
    bucket = "${var.gcp_project_id}-tf-state"
    prefix = "env/${var.environment}"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.67.0"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}