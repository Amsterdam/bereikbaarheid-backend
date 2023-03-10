create materialized view bereikbaarheid.out_vma_undirected as
select v.linknr::int,
v.name,
v.anode::int as source,
v.bnode::int as target,
v.geom,
wegtype_ab,
wegtype_ba,
st_length(v.geom) as lengte,
case 	when v.speedab is null then -1
		when v.speedab = 0 then -1
		else st_length(v.geom)/(v.speedab/(10000/3600)) end as cost,
case 	when v.speedba is null then -1
		when v.speedba = 0 then -1
		else st_length(v.geom)/(v.speedba/(10000/3600)) end as reverse_cost,

case 	when v.speedab is null and  v.speedba is null then false
		when v.speedab = 0   and v.speedba = 0  then false
		when v.speedab is null and  v.speedba = 0 then false
		when v.speedab = 0   and v.speedba is null  then false
		else true end as car_network,
b.binnen_amsterdam ,
b.binnen_polygoon_awb ,
b.milieuzone ,
b.zone_zwaar_verkeer_bus ,
b.zone_zwaar_verkeer_non_bus ,
b.zone_zwaar_verkeer_detail ,
b.tunnelcategorie_gevaarlijke_stoffen ,
b.tunnelnamen ,
b.route_gevaarlijke_stoffen,
b.beleidsnet_auto ,
b.beleidsnet_ov ,
b.beleidsnet_fiets,
b.beleidsnet_lopen ,
b.hoofdroute_taxi ,
b.touringcar_aanbevolen_routes,
b.wettelijke_snelheid_actueel ,
b.wettelijke_snelheid_wens ,
b.wegcategorie_actueel ,
b.wegcategorie_wens ,
b.frc ,
'4.50' as vma_netwerk_versie
from  bereikbaarheid.bd_vma_latest  v
left join bereikbaarheid.bd_gebieden p
on st_dwithin(p.geom,v.geom,50)=true
left join bereikbaarheid.bd_vma_beleidsmatige_verrijking b
on v.linknr = b.linknr
where	(st_intersects(p.geom,v.geom)=true  and wegtypeab not in  ('voedingslink','BTM','loop en fietsveer','trein','loopverbinding_halte','tram','loopverbinding_knoop')  )
or 		(st_intersects(p.geom,v.geom)=true  and wegtypeba not in  ('voedingslink','BTM','loop en fietsveer','trein','loopverbinding_halte','tram','loopverbinding_knoop')  ) ;

