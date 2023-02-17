from datetime import datetime, time
from marshmallow import Schema, fields, validates_schema, ValidationError
import pytz
from webargs.flaskparser import use_args
from . import api
from ..db import query_db, get_db

tz_amsterdam = pytz.timezone("Europe/Amsterdam")


class RoadObstructionsValidationSchema(Schema):
    date = fields.Date(
        format="%Y-%m-%d",
        load_default=lambda: datetime.today().astimezone(tz_amsterdam),
        required=False,
    )

    timeFrom = fields.Time(
        format="%H:%M",
        load_default=time.min,
        required=False,
    )

    timeTo = fields.Time(
        format="%H:%M",
        load_default=time.max,
        required=False,
    )

    @validates_schema
    def validate_dates(self, data, **kwargs):
        if data["timeTo"] < data["timeFrom"]:
            raise ValidationError("TimeTo must be later than timeFrom")


@api.get("/road-obstructions/")
@use_args(RoadObstructionsValidationSchema(), location="query")
def road_obstructions(args):
    time_from = datetime.combine(args["date"], args["timeFrom"])
    time_to = datetime.combine(args["date"], args["timeTo"])

    result = query_db_road_obstructions(time_from, time_to)

    # https://datatracker.ietf.org/doc/html/rfc7946#section-3.3
    return {
        "type": "FeatureCollection",
        "features": [i[0] for i in result] if result else [],
    }


def query_db_road_obstructions(time_from, time_to):
    """
    Queries database for road obstructions for a specific date
    :param time_from: string - e.g "2022-05-29 08:00:00"
    :param time_to: string - e.g "2022-05-29 16:00:00"
    :return: object - road elements with obstructions
    """
    db_query = """
        select json_build_object(
            'geometry', ST_Transform(t1.geom, 4326)::json,
            'properties', json_build_object(
                'road_element_id', t1.linknr,
                'road_element_street_name', t1.name,
                'road_element_accessibility_code', t2."bereikbaar_status_code",
                'obstructions', case
                    when t2."bereikbaar_status_code" = 222 then '[]'
                    else json_agg(json_build_object(
                        'activity', t2."werkzaamheden",
                        'reference', t2."kenmerk",
                        'url', t2."url",
                        'start_date', t2.start_date,
                        'end_date', t2.end_date
                    ) order by t2.end_date asc)
                    end
            ),
            'type', 'Feature'
        )
        from bereikbaarheid.out_vma_undirected t1

        right join (
            select v.id,
                v.bereikbaar_status_code,
                v.geom,
                url, kenmerk, werkzaamheden,
                opmerking, start_date, end_date
            from (
                -- BLOCK 1: SELECT
                -- selects linknumber, geom, bereikbaar_status_code
                -- and stremming-information
                select abs(netwerk.id) as id,
                    netwerk.name,
                    max(
                        case
                            when strem.start_date is not NUll then 333	-- If the link has a startdate, there are werkzaamheden. So it is directly unreachable. # noqa: E501
                            when routing.agg_cost is null then 222		-- When the aggregating cost is zero the source node of the road is unreachable. # noqa: E501
                            else 999
                        end
                    ) as bereikbaar_status_code,
                    g.geom as geom,
                    strem.start_date as start_date,
                    strem.end_date as end_date,
                    strem.url as url,
                    strem.kenmerk as kenmerk,
                    strem.werkzaamheden as werkzaamheden,
                    strem.opmerking as opmerking
                from bereikbaarheid.out_vma_directed netwerk

                -- BLOCK 2: FROM, routing
                -- finds agg_cost to all nodes
                left join (
                    SELECT start_vid as source, end_vid as target, agg_cost
                    FROM pgr_dijkstraCost(
                        %(pgr_dijkstra_cost_query)s,
                        683623,
                        array(
                            select node
                            from bereikbaarheid.out_vma_node
                        ),
                        directed := true -- because all the roads have been doubled to form an undirected network. # noqa: E501
                    )
                ) as routing
                on netwerk.source = routing.target -- Is the source of the link reachable? # noqa: E501

                -- BLOCK 3; FROM,
                -- Joins with stremmingen to find all direct unreachable links
                left join (
                    select vma_linknr, start_date, end_date, url,
                        kenmerk, werkzaamheden, opmerking
                    from bereikbaarheid.bd_stremmingen
                ) as strem
                on abs(netwerk.id) = strem.vma_linknr

                -- BLOCK 4; FROM, Joins with the geom.
                left join bereikbaarheid.out_vma_directed g
                    on abs(netwerk.id) = g.id

                -- BLOCK 5: WHERE.
                where
                    abs(netwerk.id) in (
                        select id from bereikbaarheid.out_vma_directed
                        where binnen_amsterdam is true and id > 0
                        and id > 0
                    )
                    and netwerk.cost > 0
                    and (
                        (
                            strem.start_date <= %(time_to)s
                            and strem.end_date >= %(time_from)s
                        )
                        or strem.start_date is null
                    )

                group by abs(netwerk.id), netwerk.name, g.geom,
                    strem.start_date, strem.end_date, strem.url, strem.kenmerk,
                    strem.werkzaamheden, strem.opmerking
                order by abs(netwerk.id)
            ) v

            where v.bereikbaar_status_code <> 999 -- Where the status is not equal to 999 (so the road is unreachable)

        ) t2

        on t1.linknr = t2.id
        group by t1.geom, t1.linknr, t1.name, t2.bereikbaar_status_code
        order by t1.linknr
    """

    query_params = {
        "pgr_dijkstra_cost_query": prepare_pgr_dijkstra_cost_query(
            time_from, time_to
        ),
        "time_from": time_from,
        "time_to": time_to,
    }

    try:
        return query_db(db_query, query_params)

    except Exception:
        print("Error while retrieving road obstructions")


def prepare_pgr_dijkstra_cost_query(time_from, time_to):
    """
    Helper function for the query_db_road_obstructions function
    Prepares a database query for use in the pgr_dijkstraCost db function

    This preparation is needed because the pgr_dijkstraCost db function uses
    psycopg placeholders. When defining this query inline - in the db_query
    variable of the query_db_road_obstructions function above - the
    %(time_to)s and %(time_from)s placeholders cause a SQL syntax error
    (because the date's are single-quoted within a single quoted statement).
    Therefore this query is prepared first, and returned for use as a
    query parameter in the query_db_road_obstructions function.

    :param time_from: string - e.g "2022-05-29 08:00:00"
    :param time_to: string - e.g "2022-05-29 16:00:00"
    :return: prepared db query for use in the pgr_dijkstraCost db function
    """

    pgr_dijkstra_cost_query = """
            select total_network.*
            from (
                select nw.id, nw.source, nw.target, nw.cost
                from bereikbaarheid.out_vma_directed nw

                ) total_network
            where cost > 0
            and
            abs(id) not in (
                select t1.vma_linknr
                from bereikbaarheid.bd_stremmingen as t1
                where start_date <= %(time_to)s
                and end_date >= %(time_from)s
            )
        """

    pgr_dijkstra_cost_query_params = {
        "time_from": time_from,
        "time_to": time_to,
    }

    cursor = get_db().cursor()

    return cursor.mogrify(
        pgr_dijkstra_cost_query, pgr_dijkstra_cost_query_params
    ).decode("utf-8")
