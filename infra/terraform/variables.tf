variable "aws_region" {
  description = "AWS deployment region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment name (dev, staging, prod)"
  type        = string
  default     = "production"
}

variable "app_name" {
  description = "Application name identifier"
  type        = string
  default     = "ekia"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "db_instance_class" {
  description = "RDS instance class for PostgreSQL + pgvector"
  type        = string
  default     = "db.t4g.medium"
}

variable "db_allocated_storage" {
  description = "Allocated storage in GB for RDS"
  type        = number
  default     = 50
}

variable "backend_cpu" {
  description = "Fargate CPU units for FastAPI backend (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "backend_memory" {
  description = "Fargate memory for FastAPI backend in MB"
  type        = number
  default     = 2048
}

variable "frontend_cpu" {
  description = "Fargate CPU units for Next.js frontend"
  type        = number
  default     = 512
}

variable "frontend_memory" {
  description = "Fargate memory for Next.js frontend in MB"
  type        = number
  default     = 1024
}
