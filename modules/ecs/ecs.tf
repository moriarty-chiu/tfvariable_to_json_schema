module "ecs" {
  source = "${remote_address}/terraform-ecs.git?ref=v2.0.0"

  for_each = { for idx, config in local.config.ecs : (lookup(config, "id", idx)) => config}
  hostname = each.value.hostname
  image_name = local.ecs_catalog[each.value.ecs_size].image_name
  availability_zone = each.value.az
  flavor_name = local.ecs_catalog[each.value.ecs_size].flavor_name
  subnet = each.value.subnet
  application_disk = merge(
    {
      "/dev/vdb" = {
        size = each.value.default_disk
      }
    },
    each.value.additional_disks
  )
}