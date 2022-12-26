from marshmallow import Schema, fields
from webargs.flaskparser import use_args
from . import api
from ..db import query_db


class RoadElementsValidationSchema(Schema):
    id = fields.Int(required=True)


@api.get("/road-elements/<id>")
@use_args(RoadElementsValidationSchema(), location="view_args")
def road_elements(args, **kwargs):
    result = query_db_road_elements(args["id"])

    # https://datatracker.ietf.org/doc/html/rfc7946#section-3.3
    return {
        "type": "FeatureCollection",
        "features": [result[0]] if result else [],
    }


def query_db_road_elements(road_element_id):
    """
    Queries database for road elements based on id
    :param road_element_id: int - the id of the road element
    :return: object - road element with relationships
    """
    db_query = """
        select json_build_object(
            'geometry', ST_Transform(t1.geom, 4326)::json,
            'properties', json_build_object(
                'id', t1.linknr,
                'length_in_m', t1.lengte::int,
                'max_speed_in_km', t1.wettelijke_snelheid_actueel,
                'street_name', t1.name,
                'traffic_counts', case
                    when count(t2) = 0 then '[]'
                    else json_agg(json_build_object(
                        'direction_1', t2."Richtingen_1",
                        'direction_2', t2."Richtingen_2",
                        'known_interruptions', t2.storing,
                        'langzaam_verkeer', t2."Langzaam_verkeer"::boolean,
                        'link_to_file', t2.url,
                        'location_name', t2."Telpuntnaam",
                        'measures_between', t2."Tussen",
                        'method', t2."Meetmethode",
                        'remarks', t2."Bijzonderheden",
                        'snelverkeer', t2.snel_verkeer::boolean,
                        'traffic_type', t2."Type_verkeer",
                        'year', t2.jaar
                    ) order by t2.jaar desc)
                    end,
                'traffic_obstructions', case
                    when count(t3) = 0 then '[]'
                    else json_agg(json_build_object(
                        'activity', t3."werkzaamheden",
                        'reference', t3."kenmerk",
                        'url', t3."url",
                        'start_date', t3.start_date,
                        'end_date', t3.end_date
                    ) order by t3.start_date desc)
                    end
            ),
            'type', 'Feature'
        )
        from bereikbaarheid.out_vma_undirected t1

        left join bereikbaarheid.bd_verkeerstellingen t2
            on t1.linknr = t2.vma_linknr

        left join bereikbaarheid.bd_stremmingen t3
            on t1.linknr = t3.vma_linknr
            and now() < t3.end_date

        where t1.linknr = %(road_element_id)s
        group by t1.geom, t1.linknr, t1.name,
            t1.wettelijke_snelheid_actueel, t1.lengte
    """

    query_params = {"road_element_id": road_element_id}

    try:
        return query_db(db_query, query_params, True)

    except Exception:
        print("Error while retrieving road element")
