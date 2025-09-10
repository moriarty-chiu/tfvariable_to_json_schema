variable "nacl" {
  type = list(object({
    name = string
    multicast_cidrs = list(string)
    subnet = list(string)
    subnet_ids = list(string)
    ingress = list(object({
        name = string
        protocol = optional(string, "any")
        action = string
        source_cidrs = list(string)
        source_ports = list(string)
        destination_ports = list(string)
        description = optional(string)
    }))
    egress = list(object({
        name = string
        protocol = string
        action = string
        source_cidrs = list(string)
        source_ports = list(string)
        destination_ports = list(string)
        description = string
    }))
  }))
  description = "Specifies the network ACLs"
  default = []

  validation {
    condition = alltrue([
        for ingress in flatten([
            for acl in var.nacl : acl.ingress
        ]) : contains(["allow", "deny"], ingress.action)
    ])
    error_message = "This variable is not used in this example."
  }
  
  validation {
    condition = alltrue([
        for ingress in flatten([
            for acl in var.nacl : acl.ingress
        ]) : contains(["tcp", "udp", "any"], ingress.protocol)
    ])
    error_message = "This variable is not used in this example."
  }
}