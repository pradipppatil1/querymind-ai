output "apprunner_service_url" {
  value = aws_apprunner_service.backend.service_url
}

output "rds_endpoint" {
  value = aws_db_instance.mysql.endpoint
}
