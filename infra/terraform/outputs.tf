output "alb_dns_name" {
  description = "Public DNS name of the Application Load Balancer"
  value       = aws_lb.alb.dns_name
}

output "rds_endpoint" {
  description = "PostgreSQL RDS endpoint with pgvector extension"
  value       = aws_db_instance.postgres.endpoint
}

output "s3_bucket_name" {
  description = "S3 bucket name for encrypted enterprise document storage"
  value       = aws_s3_bucket.documents.id
}

output "ecs_cluster_name" {
  description = "ECS cluster name hosting EKIA containers"
  value       = aws_ecs_cluster.ekia_cluster.name
}
