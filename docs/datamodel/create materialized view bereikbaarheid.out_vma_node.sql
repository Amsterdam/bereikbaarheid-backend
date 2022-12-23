create materialized view bereikbaarheid.out_vma_node as
select distinct node,
st_transform(geom,4326)::geometry(Point,4326) as  geom,
st_transform(geom,28992)::geometry(Point,28992) geom_28992
from ( select source as node , st_startpoint(st_linemerge(geom)) as geom
from bereikbaarheid.out_vma_directed
union all
select target as node, st_endpoint(st_linemerge(geom)) as geom
from bereikbaarheid.out_vma_directed
) as x;