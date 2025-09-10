variable "cce" {
  type = list(object({
    az = string
    cce_size = string 
    num_of_nodes = optional(number, 0)
    subnet_id = string
  }))

  validation {
    condition = alltrue([
      for cce_instance in var.cce :
      contains(["cce_small", "cce_medium", "cce_large"], cce_instance.cce_size)
    ])
    error_message = "Invalid ecs_size. Valid options are cce_small, cce_medium, cce_large"
  }

  validation {
    condition = alltrue([
      for cce_instance in var.ecs :
      contains(["az1", "az2"], cce_instance.az)
    ])
    error_message = "Invalid az. Valid options are az1, az2"
  }

  validation {
    condition = alltrue([
      for cce_instance in var.ecs :
      contains(["app", "db", "dmz"], cce_instance.subnet_id)
    ])
    error_message = "Invalid subnet. Valid options are app, db, dmz"
  }
}