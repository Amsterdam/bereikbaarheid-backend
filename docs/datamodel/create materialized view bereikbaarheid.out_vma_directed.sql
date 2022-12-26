create materialized view bereikbaarheid.out_vma_directed as
select
netwerk.linknr as id,
netwerk.name,
netwerk.source,
netwerk.target,
ST_LineMerge(netwerk.geom)::geometry(LineString,28992) as geom,
ST_LineMerge(st_transform(geom,4326))::geometry(LineString,4326) as geom4326,
ST_LineMerge(ST_SnapToGrid(st_transform(ST_SimplifyPreserveTopology(geom,3),4326),0.00001))::geometry(LineString,4326)  as geom4326simply,
netwerk.cost,
netwerk.binnen_amsterdam,
netwerk.milieuzone,
netwerk.zone_zwaar_verkeer_detail,
case when netwerk.zone_zwaar_verkeer_detail in ('binnen','binnen - breed opgezette wegen') then true else false end as zone_7_5,
netwerk.frc,
case when bordc07.c07 =1 then true when bordc07.c07 = 0 then false else false end as c07,
case when bordc07a.c07a =1 then true when bordc07a.c07a = 0 then false else false end as c07a,
case when bordc01.c01 =1 then true when bordc01.c01 = 0 then false else false end as c01,
case when bordc10.c10 =1 then true when bordc10.c10 = 0 then false else false end as c10,
borden17_21.c17,
borden17_21.c18,
borden17_21.c19,
borden17_21.c20,
case
when borden17_21.c21 is null and l.lastbeperking_in_kg is not null then l.lastbeperking_in_kg
when l.lastbeperking_in_kg <  borden17_21.c21 then l.lastbeperking_in_kg
else borden17_21.c21 end as c21,
borden17_21.c21 as c21_borden,
l.lastbeperking_in_kg
from
(	select linknr,
	name,
	source,
	target,
	geom,
	cost,
	binnen_amsterdam,
	milieuzone,
	zone_zwaar_verkeer_detail,
	frc
	from  bereikbaarheid.vma_undirected
	union all
	select linknr*-1 as linknr,
	name,
	target,
	source,
	st_reverse(geom),
	reverse_cost,
	binnen_amsterdam,
	milieuzone,
	zone_zwaar_verkeer_detail,
	frc
	from  bereikbaarheid.vma_undirected
) 	as netwerk
left join	(	select  vb.link_gevalideerd as linknr_vma,
				min(case when vb.rvv_modelnummer = 'C17' then vb.tekst_waarde else NULL end) as c17,
				min(case when vb.rvv_modelnummer = 'C18' then vb.tekst_waarde else NULL end) as c18,
				min(case when vb.rvv_modelnummer = 'C19' then vb.tekst_waarde else NULL end) as c19,
				min(case when vb.rvv_modelnummer = 'C20' then vb.tekst_waarde else NULL end) as c20,
				min(case when vb.rvv_modelnummer = 'C21' or vb.rvv_modelnummer = 'C21_ZB' then vb.tekst_waarde else NULL end) as c21
				from  bereikbaarheid.bd_verkeersborden vb
				where  vb.link_gevalideerd  <> 0
				and geldigheid in ('verbod')
				and verkeersbesluit<>'stcrt-2021-24726'
				group by  vb.link_gevalideerd
			) 	as borden17_21
on 			netwerk.linknr=borden17_21.linknr_vma
left join (select linknr, min(lastbeperking_in_kg) as lastbeperking_in_kg  from bereikbaarheid.lastbeperking_in_zzv_zonder_vb group by linknr) l
on abs(netwerk.linknr)=l.linknr
left join 	(select distinct link_gevalideerd, 1 as c07 from bereikbaarheid.bd_verkeersborden vb where rvv_modelnummer='C07' and geldigheid in ('verbod') or rvv_modelnummer='C07ZB' and geldigheid in ('verbod') or rvv_modelnummer='C07B' and geldigheid in ('verbod') )
			as bordc07
on 			netwerk.linknr=bordc07.link_gevalideerd
left join 	(select distinct link_gevalideerd, 1 as c01 from bereikbaarheid.bd_verkeersborden vb where rvv_modelnummer='C01' and geldigheid in ('verbod') )
			as bordc01
on 			netwerk.linknr=bordc01.link_gevalideerd
left join 	(select distinct link_gevalideerd, 1 as c07a from bereikbaarheid.bd_verkeersborden vb where rvv_modelnummer='C07A' and geldigheid in ('verbod') or rvv_modelnummer='C07B' and geldigheid in ('verbod')  )
			as bordc07a
on 			netwerk.linknr=bordc07a.link_gevalideerd
 left join 	(select distinct link_gevalideerd, 1 as c10 from bereikbaarheid.bd_verkeersborden vb where rvv_modelnummer='C10' and geldigheid in ('verbod') )
 			as bordc10
 on 			netwerk.linknr=bordc10.link_gevalideerd;