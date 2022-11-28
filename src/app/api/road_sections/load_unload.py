from .. import api
from ...db import query_db


@api.get("/road-sections/load-unload/")
def load_unload_data():
    result = query_db_load_unload()

    # https://datatracker.ietf.org/doc/html/rfc7946#section-3.3
    return {
        "type": "FeatureCollection",
        "features": [i[0] for i in result] if result else [],
    }


def query_db_load_unload():
    """
    Queries database for road sections with load unload data
    :return: object - road sections with load unload data
    """
    db_query = """
        select json_build_object(
            'geometry', ST_Transform(t1.geom, 4326)::json,
            'properties', json_build_object(
                'id', t1.linknr,
                'street_name', t1.name,
                'load_unload', json_agg(json_build_object(
                    'category', t2.laden_lossen,
                    'days', t2.dagen,
                    'start_time', t2.begin_tijd,
                    'end_time', t2.eind_tijd
                ) order by t2.eind_tijd asc)
            ),
            'type', 'Feature'
        )
        from bereikbaarheid.vma400_20212201_undirected_test t1

        right join bereikbaarheid.ht_venstertijdwegen t2
            on t1.linknr = t2.linknr

        where t1.geom is not null
        group by t1.geom, t1.linknr, t1.name
        order by t1.linknr
    """

    try:
        return query_db(db_query, {})

    except Exception:
        print("Error while retrieving road sections with load-unload data")
