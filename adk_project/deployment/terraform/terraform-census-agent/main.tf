variable "project_id" {
    description = "The ID of the Google Cloud Project"
    type = string
    default = "christine-dev"
}

variable "agent_sa_id" {
    description = "The desired unique ID for the service account used by agent engine"
    type = string
    default = "bq-agent"
}

variable "test_census_agent_sa_id" {
    description = "The desired unique ID for the service account used by agent engine"
    type = string
    default = "test-census-agent"
}


terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
      version = "7.11.0"
    }
  }
}


provider "google" {
    project = var.project_id
    region = "us-central1"
}


resource "google_service_account" "agent_executor_sa" {
    account_id = var.agent_sa_id
    display_name = "Agent Executor - BigQuery/Vertex AI Access"
    project = var.project_id
}


resource "google_project_iam_member" "bq_job_user" {
    project = var.project_id
    role = "roles/bigquery.jobUser"
    member = "serviceAccount:${google_service_account.agent_executor_sa.email}"
    depends_on = [google_service_account.agent_executor_sa]
}

resource "google_project_iam_member" "bq_data_viewer" {
    project = var.project_id
    role = "roles/bigquery.dataViewer"
    member = "serviceAccount:${google_service_account.agent_executor_sa.email}"
    depends_on = [google_service_account.agent_executor_sa]
}

resource "google_project_iam_member" "vertex_ai_user" {
    project = var.project_id
    role = "roles/aiplatform.user"
    member = "serviceAccount:${google_service_account.agent_executor_sa.email}"
    depends_on = [google_service_account.agent_executor_sa]
}


output "service_account_email" {
    description = "The email of the created Service Account"
    value = google_service_account.agent_executor_sa.email
}



## provision a new test service account for census query agent

resource "google_service_account" "test_census_agent_executor_sa" {
    account_id = var.test_census_agent_sa_id
    display_name = "Test Census Agent Executor - BigQuery/Vertex AI Access"
    project = var.project_id
}


resource "google_project_iam_member" "bq_job_user_2" {
    project = var.project_id
    role = "roles/bigquery.jobUser"
    member = "serviceAccount:${google_service_account.test_census_agent_executor_sa.email}"
    depends_on = [google_service_account.test_census_agent_executor_sa]
}

resource "google_project_iam_member" "bq_data_viewer_2" {
    project = var.project_id
    role = "roles/bigquery.dataViewer"
    member = "serviceAccount:${google_service_account.test_census_agent_executor_sa.email}"
    depends_on = [google_service_account.test_census_agent_executor_sa]
}

resource "google_project_iam_member" "vertex_ai_user_2" {
    project = var.project_id
    role = "roles/aiplatform.user"
    member = "serviceAccount:${google_service_account.test_census_agent_executor_sa.email}"
    depends_on = [google_service_account.test_census_agent_executor_sa]
}


output "test_census_agent_service_account_email" {
    description = "The email of the created test census agent Service Account"
    value = google_service_account.test_census_agent_executor_sa.email
}