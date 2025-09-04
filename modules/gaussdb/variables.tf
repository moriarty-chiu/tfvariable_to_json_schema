variable "gaussdb" {
  type = list(object({
    database_name = string
    schemas = map(object({
        owner = string
    }))
  }))
}