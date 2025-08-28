variable "ecs" {
  type = list(object({
    hostname = string
    ecs_size = string 
    az = string
    subnet = string
    default_disk = optional(number, 150)
    additional_disks = optional(map(object({
      size = number 
    })), {})
  }))
  description = "Specify the ECS instances to be created"
  default = []
  validation {
    condition = alltrue([
      for ecs_instance in var.ecs :
      contains(["ecs_small", "ecs_medium", "ecs_large"], ecs_instance.ecs_size)
    ])
    error_message = "Invalid ecs_size. Valid options are ecs_small, ecs_medium, ecs_large"
  }
  validation {
    condition = alltrue([
      for ecs_instance in var.ecs :
      contains(["app", "db", "dmz"], ecs_instance.subnet)
    ])
    error_message = "Invalid subnet. Valid options are app, db, dmz"
  }
}