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
        with load_unload as (
            select abs(bd.linknr) as linknr_abs,
            case
                when vma.linknr > 0
                    and degrees(
                        st_azimuth(st_startpoint(st_linemerge(vma.geom)),
                        st_endpoint(st_linemerge(vma.geom)))
                    ) < 45
                    then 'noord'

                when vma.linknr > 0
                    and degrees(
                        st_azimuth(st_startpoint(st_linemerge(vma.geom)),
                        st_endpoint(st_linemerge(vma.geom)))
                    ) < 45 + 90
                    then 'oost'

                when vma.linknr > 0
                    and degrees(
                        st_azimuth(st_startpoint(st_linemerge(vma.geom)),
                        st_endpoint(st_linemerge(vma.geom)))
                    ) < 45 + 180
                    then 'zuid'

                when vma.linknr > 0
                    and degrees(
                        st_azimuth(st_startpoint(st_linemerge(vma.geom)),
                        st_endpoint(st_linemerge(vma.geom)))
                    ) < 45 + 270
                    then 'west'

                when vma.linknr > 0 then 'noord'

                when vma.linknr < 0
                    and degrees(
                        st_azimuth(st_startpoint(st_linemerge(vma.geom)),
                        st_endpoint(st_linemerge(st_reverse(vma.geom))))
                    ) < 45
                    then 'noord'

                when vma.linknr < 0
                    and degrees(
                        st_azimuth(st_startpoint(st_linemerge(vma.geom)),
                        st_endpoint(st_linemerge(st_reverse(vma.geom))))
                    ) < 45 + 90
                    then 'oost'

                when vma.linknr < 0
                    and degrees(
                        st_azimuth(st_startpoint(st_linemerge(vma.geom)),
                        st_endpoint(st_linemerge(st_reverse(vma.geom))))
                    ) < 45 + 180
                    then 'zuid'

                when vma.linknr < 0
                    and degrees(
                        st_azimuth(st_startpoint(st_linemerge(vma.geom)),
                        st_endpoint(st_linemerge(st_reverse(vma.geom))))
                    ) < 45 + 270
                    then 'west'

                else  'noord'

            end as richting,

            bd.linknr,
            bd.e_type,
            bd.laden_lossen,
            bd.dagen,
            bd.begin_tijd,
            bd.eind_tijd,
            vma.car_network,
            vma.geom,
            vma.name

            from bereikbaarheid.bd_venstertijdwegen bd

            left join bereikbaarheid.vma_latest_undirected vma
                on abs(bd.linknr) = vma.linknr

            order by bd.linknr
        )

        select json_build_object(
            'geometry', ST_Transform(load_unload.geom, 4326)::json,
            'properties', json_build_object(
                'id', load_unload.linknr_abs,
                'street_name', load_unload.name,
                'load_unload', json_agg(json_build_object(
                    'road_section_id', load_unload.linknr,
                    'direction', load_unload.richting,
                    'additional_info', load_unload.laden_lossen,
                    'days', load_unload.dagen,
                    'start_time', load_unload.begin_tijd,
                    'end_time', load_unload.eind_tijd
                ) order by load_unload.eind_tijd asc)
            ),
            'type', 'Feature'
        )
        from load_unload

        where load_unload.geom is not null
        group by load_unload.geom, load_unload.linknr_abs, load_unload.name
        order by load_unload.linknr_abs
    """

    try:
        return query_db(db_query, {})

    except Exception:
        print("Error while retrieving road sections with load-unload data")
