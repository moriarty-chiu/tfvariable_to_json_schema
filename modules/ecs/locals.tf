locals {
  config = jsondecode((file("${remote_address}/config.json")))

  ecs_catalog = {
    ecs_small = {
      image_name = "ubuntu:latest"
      flavor_name = "c1.medium"
    }
  }
}