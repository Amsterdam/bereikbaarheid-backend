from flask import jsonify
from marshmallow import Schema, fields, validate, validates
from webargs.flaskparser import use_args
from . import api
from .validation import vehicle, allowed_vehicle_types
from . import vehicleTypes
from ..db import query_db


class TrafficSignsValidationSchema(Schema):
    trafficSignCategories = fields.List(
        fields.String(
            required=True,
            validate=validate.OneOf(
                [
                    "prohibition",
                    "prohibition with exception",
                    "prohibition ahead",
                ]
            ),
        ),
        required=True,
        validate=validate.Length(min=1),
    )

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


@api.route("/traffic-signs")
@use_args(TrafficSignsValidationSchema(), location="query")
def traffic_signs(args):
    return jsonify(
        query_db_traffic_signs(
            args["trafficSignCategories"],
            args["vehicleAxleWeight"],
            args["vehicleHasTrailer"],
            args["vehicleHeight"],
            args["vehicleLength"],
            args["vehicleMaxAllowedWeight"],
            args["vehicleTotalWeight"],
            args["vehicleType"],
            args["vehicleWidth"],
        )
    )


def query_db_traffic_signs(
    traffic_sign_categories,
    vehicle_axle_weight,
    vehicle_has_trailer,
    vehicle_height,
    vehicle_length,
    vehicle_max_allowed_weight,
    vehicle_total_weight,
    vehicle_type,
    vehicle_width,
):
    """
    Fetches traffic signs from database
    :param traffic_sign_categories: one or more of the following categories:
        'prohibition', 'prohibition with exception', 'prohibition ahead',
    :param vehicle_type: string - one of the RDW vehicle types
    :param vehicle_length: float - length of the vehicle
    :param vehicle_width: float - width of the vehicle
    :param vehicle_has_trailer: 'true' or 'false' - if vehicle has a trailer
    :param vehicle_height: float - height of the vehicle
    :param vehicle_axle_weight: int - axle weight of the vehicle
    :param vehicle_total_weight: int - total weight of the vehicle
    :param vehicle_max_allowed_weight: int - max allowed weight of the vehicle
    :return: object - traffic signs based on vehicle properties and expert mode
    """

    # default response
    # https://datatracker.ietf.org/doc/html/rfc7946#section-3.3
    response = {"type": "FeatureCollection", "features": []}

    # Map traffic sign category URL parameter to values used in database
    # allows us to change category names without having to change the API
    categories_mapping = {
        "prohibition": "verbod",
        "prohibition with exception": "verbod, met uitzondering",
        "prohibition ahead": "vooraankondiging verbod",
    }
    sign_categories = [
        categories_mapping[cat] for cat in traffic_sign_categories
    ]

    db_query = """
        select json_build_object(
            'type','Feature',
            'properties', json_build_object(
                'additional_info', onderbord_tekst,
                'category', geldigheid,
                'id', bord_id,
                'label', tekst,
                'label_as_value', tekst_waarde,
                'link_to_panoramic_image', panorama,
                'network_link_id', link_gevalideerd,
                'street_name', straatnaam,
                'traffic_decree_id', verkeersbesluit,
                'type', rvv_modelnummer,
                'view_direction_in_degrees', kijkrichting
            ),
            'geometry', geom::json )
        from (
            select m.bord_id,
            m.rvv_modelnummer,
            m.tekst_waarde,
            m.tekst,
            m.kijkrichting,
            m.link_gevalideerd,
            m.onderbord_tekst,
            m.verkeersbesluit,
            m.geldigheid,
            m.panorama,
            ST_AsGeoJSON(
                st_transform(ST_SetSRID(st_makepoint(rd_x,rd_y),28992),4326)
            ) as geom,
            x.name as straatnaam
            from bereikbaarheid.borden_mapping m
            left join bereikbaarheid.netwerk2020_bebording x
            on m.link_gevalideerd = x.id
            where m.link_gevalideerd <> 0
            and LOWER(m.geldigheid) in %(traffic_sign_categories)s
            and (
                m.rvv_modelnummer = 'C01'
                or (
                    (m.rvv_modelnummer = 'C07' or m.rvv_modelnummer = 'C07ZB')
                    and
                    (%(bedrijfsauto)s is true and %(max_massa)s > 3500)
                )
                or (m.rvv_modelnummer = 'C07A' and %(bus)s is true)
                or (m.rvv_modelnummer = 'C10' and %(aanhanger)s is true)
                or (
                    m.rvv_modelnummer = 'C07B'
                    and (
                        (%(bedrijfsauto)s is true and %(max_massa)s > 3500)
                        or
                        %(bus)s is true
                    )
                )
                or (m.rvv_modelnummer = 'C17' and %(lengte)s > m.tekst_waarde)
                or (m.rvv_modelnummer = 'C18' and %(breedte)s > m.tekst_waarde)
                or (m.rvv_modelnummer = 'C19' and %(hoogte)s > m.tekst_waarde)
                or (m.rvv_modelnummer = 'C20' and %(aslast)s > m.tekst_waarde)
                or (
                    (m.rvv_modelnummer = 'C21' or m.rvv_modelnummer = 'C21_ZB')
                    and
                    %(gewicht)s > m.tekst_waarde
                )
            )
        ) v
    """

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
        "traffic_sign_categories": tuple(sign_categories),
    }

    try:
        result = query_db(db_query, query_params)

        if result:
            response["features"] = [i[0] for i in result]

    except Exception:
        print("Error while retrieving traffic signs")

    return response
