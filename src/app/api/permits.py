from flask import jsonify
from marshmallow import Schema, fields, validate, validates
from webargs.flaskparser import use_args
from . import api
from .validation import bbox_adam, vehicle, allowed_vehicle_types
from . import vehicleTypes
from ..db import query_db


class PermitsValidationSchema(Schema):
    lat = fields.Float(
        required=True,
        validate=[
            validate.Range(
                min=bbox_adam["lat"]["min"], max=bbox_adam["lat"]["max"]
            )
        ],
    )

    lon = fields.Float(
        required=True,
        validate=[
            validate.Range(
                min=bbox_adam["lon"]["min"], max=bbox_adam["lon"]["max"]
            )
        ],
    )

    permitLowEmissionZone = fields.Boolean(required=True)
    permitZzv = fields.Boolean(required=True)

    vehicleAxleWeight = fields.Integer(
        required=True,
        validate=[
            validate.Range(
                min=vehicle["axleWeight"]["min"],
                max=vehicle["axleWeight"]["max"],
            )
        ],
    )

    vehicleHasTrailer = fields.Boolean(required=True)

    vehicleHeight = fields.Float(
        required=True,
        validate=[
            validate.Range(
                min=vehicle["height"]["min"],
                max=vehicle["height"]["max"],
                min_inclusive=False,
            )
        ],
    )

    vehicleLength = fields.Float(
        required=True,
        validate=[
            validate.Range(
                min=vehicle["length"]["min"], max=vehicle["length"]["max"]
            )
        ],
    )

    vehicleMaxAllowedWeight = fields.Integer(
        required=True,
        validate=[
            validate.Range(
                min=vehicle["maxAllowedWeight"]["min"],
                max=vehicle["maxAllowedWeight"]["max"],
            )
        ],
    )

    vehicleTotalWeight = fields.Integer(
        required=True,
        validate=[
            validate.Range(
                min=vehicle["totalWeight"]["min"],
                max=vehicle["totalWeight"]["max"],
            )
        ],
    )

    vehicleType = fields.String(required=True)

    @validates("vehicleType")
    def allowed_vehicle_types(self, value):
        allowed_vehicle_types(value)

    vehicleWidth = fields.Float(
        required=True,
        validate=[
            validate.Range(
                min=vehicle["width"]["min"], max=vehicle["width"]["max"]
            )
        ],
    )


@api.route("/permits")
@use_args(PermitsValidationSchema(), location="query")
def permits(args):
    return jsonify(
        query_db_permits(
            args["vehicleType"],
            args["vehicleLength"],
            args["vehicleWidth"],
            args["vehicleHasTrailer"],
            args["vehicleHeight"],
            args["vehicleAxleWeight"],
            args["vehicleTotalWeight"],
            args["vehicleMaxAllowedWeight"],
            args["permitLowEmissionZone"],
            args["permitZzv"],
            args["lat"],
            args["lon"],
        )
    )


def query_db_permits(
    vehicle_type,
    vehicle_length,
    vehicle_width,
    vehicle_has_trailer,
    vehicle_height,
    vehicle_axle_weight,
    vehicle_total_weight,
    vehicle_max_allowed_weight,
    permit_low_emission_zone,
    permit_zzv,
    lat,
    lon,
):
    """
    Queries database for permits based on location and vehicle properties
    :param vehicle_type: string - one of the RDW vehicle types
    :param vehicle_length: float - length of the vehicle
    :param vehicle_width: float - width of the vehicle
    :param vehicle_has_trailer: 'true' or 'false' - if vehicle has a trailer
    :param vehicle_height: float - height of the vehicle
    :param vehicle_axle_weight: int - axle weight of the vehicle
    :param vehicle_total_weight: int - total weight of the vehicle
    :param vehicle_max_allowed_weight: int - max allowed weight of the vehicle
    :param permit_low_emission_zone: 'true' or 'false'
        if a low emission permit is needed based on vehicle properties
    :param permit_zzv: 'true' or 'false'
        if a heavy goods vehicle permit is needed based on vehicle properties
    :param lat: float - the latitude of the location
    :param lon: float - the longitude of the location
    :return: object - permits based on location and vehicle properties
    """

    # default response
    # https://jsonapi.org/format/
    response = {"data": None, "errors": [], "meta": {}}

    db_query = """
        select json_build_object(
            'id', id,
            'attributes',json_build_object(
                'heavy_goods_vehicle_zone', zone_7_5_boolean::boolean,
                'in_amsterdam', boolean_in_amsterdam::boolean,
                'low_emission_zone', miliezone_boolean::boolean,
                'rvv_permit_needed', rvv_boolean::boolean,
                'time_window', venstertijd,
                'wide_road', zone_7_5_detail::boolean,
                'distance_to_destination_in_m', afstand_in_m::int,
                'geom', geom
            )
        )
        from (
            select v.id,
            case
                when v.milieuzone = false and %(permit_zone_milieu)s = false
                    then 'false'
                when v.milieuzone = true and %(permit_zone_milieu)s = true
                    then 'true'
                when v.milieuzone=true and %(permit_zone_milieu)s = false
                    then 'false'
                when v.milieuzone=false and %(permit_zone_milieu)s = true
                    then 'false'
                else 'onbepaald'
            end as miliezone_boolean,

            case
                when v.zone_7_5 = false and %(permit_zone_7_5)s = false
                    then 'false'
                when v.zone_7_5 = true and %(permit_zone_7_5)s = true
                    then 'true'
                when v.zone_7_5 = true and %(permit_zone_7_5)s = false
                    then 'false'
                when v.zone_7_5 = false and %(permit_zone_7_5)s = true
                    then 'false'
                else 'onbepaald'
            end as zone_7_5_boolean,

            case
                when v.bereikbaar_status_code = 222 then 'true'
                else 'false'
            end as rvv_boolean,

            case
                when v.bereikbaar_status_code = 333 then 'false'
                else 'true'
            end as boolean_in_amsterdam,

            ST_closestpoint(
                v.geom,st_setsrid(ST_MakePoint(%(lon)s, %(lat)s), 4326)
            ) as geom,

            st_length(
                st_transform(
                    st_shortestline(
                        v.geom,
                        st_setsrid(ST_MakePoint(%(lon)s, %(lat)s), 4326)
                    ),
                    28992
                )
            ) as afstand_in_m,

            ven.dagen as venstertijd,

            case
                when tiles.zone_zwaar_verkeer_detail like '%%breed opgezette wegen' then 'true'
                else 'false'
            end as zone_7_5_detail

            from (
                select
                    abs(n.id) as id,
                    max(
                        case
                            when n.cost is NULL then 333
                            when routing.agg_cost is null then 222
                            when n.c07 is true and %(bedrijfsauto)s is true
                                and %(max_massa)s > 3500
                                or n.c07a is true and %(bus)s is true
                                or n.c10 is true and %(aanhanger)s is true
                                or n.c01 is true
                                or n.c17 < %(lengte)s
                                or n.c18 < %(breedte)s
                                or n.c19 < %(hoogte)s
                                or n.c20 < %(aslast)s
                                or n.c21 < %(gewicht)s
                                then 222
                            else 999
                        end
                    ) as bereikbaar_status_code,
                    g.geom4326 as geom,
                    g.zone_7_5,
                    g.milieuzone
                from bereikbaarheid.out_vma_directed n
                left join (
                    SELECT start_vid as source,
                    end_vid as target,
                    agg_cost FROM pgr_dijkstraCost('
                        select id, source, target, cost
                        from bereikbaarheid.out_vma_directed
                        where (%(lengte)s < c17 or c17 is null)
                        and (%(breedte)s < c18 or c18 is null)
                        and (%(hoogte)s < c19 or c19 is null)
                        and (%(aslast)s < c20 or c20 is null)
                        and (%(gewicht)s < c21 or c21 is null)
                        and (c01 is false)
                        and (
                                c07 is false
                                or (c07 is true and %(bedrijfsauto)s is false)
                                or (
                                    c07 is true
                                    and %(bedrijfsauto)s is true
                                    and %(max_massa)s <= 3500
                                )
                            )
                            and (
                                c07a is false
                                or (c07a is true and %(bus)s is false)
                            )
                            and (
                                c10 is false
                                or (c10 is true and %(aanhanger)s is false)

                        )',
                        461470,
                        array(
                            select node
                            from bereikbaarheid.out_vma_node
                        )
                    )
                ) as routing on n.source=routing.target

                left join bereikbaarheid.out_vma_directed g
                    on abs(n.id) = g.id
                    where abs(n.id) in (
                        select id from bereikbaarheid.out_vma_directed
                        where binnen_amsterdam is true and id > 0
                    )
                    and n.cost > 0

                group by abs(n.id), g.geom4326,g.zone_7_5, g.milieuzone
                order by abs(n.id)) v

                left join bereikbaarheid.bd_venstertijdwegen as ven
                on v.id = abs(ven.linknr)

                left join bereikbaarheid.out_vma_undirected as tiles
                    on v.id=tiles.linknr
                    where v.id = (
                        SELECT id
                        from bereikbaarheid.out_vma_directed a
                        where id > 0
                        order by st_length(
                            st_transform(
                                st_shortestline(
                                    st_setsrid(
                                        ST_MakePoint(%(lon)s, %(lat)s),
                                        4326
                                    ),
                                    st_linemerge(a.geom4326)
                                ),
                                28992
                            )
                        ) asc
                        limit 1
                    )
        ) m """

    query_params = {
        "bedrijfsauto": vehicleTypes.vehicle_is_company_car(vehicle_type),
        "bus": vehicleTypes.vehicle_is_bus(vehicle_type),
        "aanhanger": vehicle_has_trailer,
        "lengte": vehicle_length,
        "breedte": vehicle_width,
        "hoogte": vehicle_height,
        "aslast": vehicle_axle_weight,
        "gewicht": vehicle_total_weight,
        "max_massa": vehicle_max_allowed_weight,
        "permit_zone_milieu": permit_low_emission_zone,
        "permit_zone_7_5": permit_zzv,
        "lat": lat,
        "lon": lon,
    }

    try:
        result = query_db(db_query, query_params, True)

        if result:
            response["data"] = result[0]

    except Exception:
        response["errors"].append(
            {
                "status": 500,
                "title": "database error",
                "detail": "no connection or error in query",
            }
        )

    return response
