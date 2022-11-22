from flask import jsonify
from marshmallow import Schema, fields, validate
from webargs.flaskparser import use_args
from . import api
from .validation import bbox_adam
from ..db import query_db


class IsochronesValidationSchema(Schema):
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


@api.route("/roads/isochrones")
@use_args(IsochronesValidationSchema(), location="query")
def isochrones(args):
    return jsonify(query_db_isochrones(args["lat"], args["lon"]))


def query_db_isochrones(lat, lon):
    """
    Queries database for isochrones based on location
    :param lat: float - the latitude of the location
    :param lon: float - the longitude of the location
    :return: object - isochrones based on location
    """

    # default response
    # https://datatracker.ietf.org/doc/html/rfc7946#section-3.3
    response = {"type": "FeatureCollection", "features": []}

    db_query = """
        select json_build_object(
            'type','Feature',
            'properties',json_build_object(
            'id', abs(sub.id),
            'totalcost', min(totalcost)::int) ,
            'geometry', geom::json
        )
        from (
            select id,
            (0.5 * cost+source.agg_cost) * 3600 as totalcost
            from netwerk.netwerk2020_bebording bebording

            left join (
                SELECT end_vid, agg_cost
                FROM pgr_dijkstraCost('
                    select id, source ,target, cost
                    from netwerk.netwerk2020_bebording',
                    (
                        select x.node
                        from (
                            select node, geom
                            from bereikbaarheid.netwerk2020_bebording_node
                        ) as x
                        order by st_distance(
                            x.geom,
                            st_setsrid(ST_MakePoint(%(lon)s, %(lat)s), 4326)
                        ) asc
                        limit 1
                    ),
                    array(
                        select node
                        from bereikbaarheid.netwerk2020_bebording_node
                    )
                )
            ) as source
            on source.end_vid =  bebording.source
            where cost > 0
        ) as sub

        left join netwerk.netwerk2020_bebording a
            on a.id=sub.id
            where abs(a.id) in (
                select linknr from vma400.vma400_20210622_tiles
                where zone_amsterdam is true
            )

        group by a.geom, abs(sub.id)"""

    query_params = {"lat": lat, "lon": lon}

    try:
        result = query_db(db_query, query_params)

        if result:
            response["features"] = [i[0] for i in result]

    except Exception:
        print("Error while retrieving isochrones")

    return response
