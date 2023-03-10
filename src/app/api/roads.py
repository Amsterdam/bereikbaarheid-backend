from flask import jsonify
from marshmallow import Schema, fields, validate, validates
from webargs.flaskparser import use_args
from . import api
from .validation import vehicle, allowed_vehicle_types
from . import vehicleTypes
from ..db import query_db


class ProhibitoryRoadsValidationSchema(Schema):
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


@api.route("/roads/prohibitory")
@use_args(ProhibitoryRoadsValidationSchema(), location="query")
def roads_prohibitory(args):
    return jsonify(
        query_db_prohibitory_roads(
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
        )
    )


def query_db_prohibitory_roads(
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
):
    """
    Fetches prohibitory roads from database
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
    :return: object - prohibitory roads based on vehicle properties
    """

    # default response
    # https://datatracker.ietf.org/doc/html/rfc7946#section-3.3
    response = {"type": "FeatureCollection", "features": []}

    db_query = """
        select json_build_object(
            'type','Feature',
            'properties',json_build_object(
            'bereikbaar_status_code', bereikbaar_status_code,
            'id',id),
            'geometry', geom::json
        )
        from (
            select v.id,
            case
                when v.bereikbaar_status_code = 333 then 333
                when v.milieuzone = true and v.zone_7_5 = true
                    and v.bereikbaar_status_code = 222
                    and %(permit_zone_milieu)s = true
                    and %(permit_zone_7_5)s = true
                    then 11111
                when v.milieuzone = true and v.zone_7_5 = true
                    and v.bereikbaar_status_code <> 222
                    and %(permit_zone_milieu)s = true
                    and %(permit_zone_7_5)s = true
                    then 11110
                when v.milieuzone = true and v.zone_7_5 = false
                    and v.bereikbaar_status_code <> 222
                    and %(permit_zone_milieu)s = true
                    then 11100
                when v.milieuzone = true and v.zone_7_5 = false
                    and v.bereikbaar_status_code = 222
                    and %(permit_zone_milieu)s = true
                    or v.milieuzone = true and v.zone_7_5 = true
                    and v.bereikbaar_status_code = 222
                    and %(permit_zone_milieu)s = true
                    and %(permit_zone_7_5)s = false
                    then 11101
                when v.milieuzone = false and v.zone_7_5 = true
                    and v.bereikbaar_status_code = 222
                    and %(permit_zone_7_5)s = true
                    or v.milieuzone = true and v.zone_7_5 = true
                    and v.bereikbaar_status_code = 222
                    and %(permit_zone_milieu)s = false
                    and %(permit_zone_7_5)s = true
                    then 11011
                when v.milieuzone = false and v.zone_7_5 = true
                    and v.bereikbaar_status_code <> 222
                    and %(permit_zone_7_5)s = true
                    then 11010
                when v.milieuzone = false and v.zone_7_5 = false
                    and v.bereikbaar_status_code = 222
                    or v.milieuzone = true and v.zone_7_5 = true
                    and v.bereikbaar_status_code = 222
                    and %(permit_zone_milieu)s = false
                    and %(permit_zone_7_5)s = false
                    or (
                        v.milieuzone = true and v.zone_7_5 = false
                        and v.bereikbaar_status_code = 222
                        and %(permit_zone_milieu)s = false
                    )
                    then 11001
                else 999
            end as bereikbaar_status_code,
            v.geom from (
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
                    ST_AsGeoJSON(g.geom4326) as geom,
                    g.zone_7_5,
                    g.milieuzone,
                    g.binnen_amsterdam
                from bereikbaarheid.out_vma_directed n
                left join (
                    SELECT start_vid as source,
                    end_vid as target,
                    agg_cost FROM pgr_dijkstraCost('
                        select id, source, target, cost
                        from bereikbaarheid.out_vma_directed
                        where cost > 0
                        and (
                            (( -.01 + %(lengte)s ) < c17 or c17 is null)
                            and (( -.01 + %(breedte)s ) < c18 or c18 is null)
                            and (( -.01 +%(hoogte)s ) < c19 or c19 is null)
                            and (( -1 + %(aslast)s ) < c20 or c20 is null)
                            and (( -1 + %(gewicht)s ) < c21 or c21 is null)
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
                            )
                        )',
                        902205,
                        array(
                            select node
                            from bereikbaarheid.out_vma_node
                        )
                    )
                ) as routing on n.source = routing.target

                left join bereikbaarheid.out_vma_directed g
                    on abs(n.id) = g.id
                    where abs(n.id) in (
                        select id from bereikbaarheid.out_vma_directed
                        where id > 0
                    )
                    and n.cost > 0

                group by abs(n.id), g.geom4326, g.zone_7_5, g.milieuzone,g.binnen_amsterdam
                order by abs(n.id)
            ) v
            where v.bereikbaar_status_code <> 999
            and v.binnen_amsterdam is true
        ) m """

    query_params = {
        "bus": vehicleTypes.vehicle_is_bus(vehicle_type),
        "bedrijfsauto": vehicleTypes.vehicle_is_company_car(vehicle_type),
        "aanhanger": vehicle_has_trailer,
        "lengte": vehicle_length,
        "breedte": vehicle_width,
        "hoogte": vehicle_height,
        "aslast": vehicle_axle_weight,
        "gewicht": vehicle_total_weight,
        "max_massa": vehicle_max_allowed_weight,
        "permit_zone_milieu": permit_low_emission_zone,
        "permit_zone_7_5": permit_zzv,
    }

    try:
        result = query_db(db_query, query_params)

        if result:
            response["features"] = [i[0] for i in result]

    except Exception:
        print("Error while retrieving prohibitory roads")

    return response
