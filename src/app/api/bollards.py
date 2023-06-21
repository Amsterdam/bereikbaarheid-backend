from marshmallow import (
    Schema,
    fields,
    validate,
    validates_schema,
    ValidationError,
)
from webargs.flaskparser import use_args

from .validation import bbox_adam, days_of_the_week_abbreviated
from . import api
from ..db import get_db, query_db


class BollardsValidationSchema(Schema):
    dayOfTheWeek = fields.String(
        required=False,
        validate=validate.OneOf(days_of_the_week_abbreviated),
    )

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

    timeFrom = fields.Time(
        format="%H:%M",
        required=False,
    )

    timeTo = fields.Time(
        format="%H:%M",
        required=False,
    )

    @validates_schema
    def validate_dates(self, data, **kwargs):
        if "timeTo" not in data or "timeFrom" not in data:
            return

        if data["timeTo"] < data["timeFrom"]:
            raise ValidationError("timeTo must be later than timeFrom")

    @validates_schema
    def validate_field_dependencies(self, data, **kwargs):
        dependent_fields = {
            "dayOfTheWeek": ["timeTo", "timeFrom"],
            "timeFrom": ["dayOfTheWeek", "timeTo"],
            "timeTo": ["dayOfTheWeek", "timeFrom"],
        }

        for field in dependent_fields:
            if field in data:
                missing_fields = [
                    f for f in dependent_fields[field] if f not in data
                ]

                if missing_fields:
                    raise ValidationError(
                        f"Missing fields: {', '.join(missing_fields)}"
                    )


@api.get("/bollards/")
@use_args(BollardsValidationSchema(), location="query")
def bollards(args):
    result = query_db_bollards(
        args["dayOfTheWeek"] if "dayOfTheWeek" in args else None,
        args["lat"],
        args["lon"],
        args["timeFrom"] if "timeFrom" in args else None,
        args["timeTo"] if "timeTo" in args else None,
    )

    # https://datatracker.ietf.org/doc/html/rfc7946#section-3.3
    return {
        "type": "FeatureCollection",
        "features": [i[0] for i in result] if result else [],
    }


def query_db_bollards(day_of_the_week, lat, lon, time_from, time_to):
    """
    The query calculates a route to the provided lat/lon and returns
    the encountered bollards. If no bollards are found, nothing is returned.

    It works as follows:
    - Based on the provided day of the week, start and end time,
      the network cost is recalculated:
      - cost is multiplied by 10000 if:
        - road section is linked to a bollard
        - AND the given day, start and end time do not match with the times
          when the bollard is retracted / removed
      - cost is multiplied by 10000 * 10000 if:
        - road section is linked to a bollard
        - AND the given day, start and end time do not match with the times
          when the bollard is retracted / removed
        - AND road section is not accessible for vehicles
      - cost is multiplied by 2 * 10000 * 10000 if:
        - road section is not accessible for vehicles
      - for all other cases, the normal cost calculation (length/speed) applies
    - By recalculating the cost - as described above - the routing algorithm
      will try to find a route without bollards. It will only use routes
      with bollard(s) if all other options are exhausted.
    - The provided lat/lon is used to search for the closest target node
    - The closest target node is used for calculating routes

    :param day_of_the_week: e.g "di"
    :type day_of_the_week: string or None
    :param time_from: e.g "08:00:00"
    :type time_from: string or None
    :param time_to: e.g "16:00:00"
    :type time_to: string or None
    :param lat: the latitude of the location
    :type lat: float
    :param lon: the longitude of the location
    :type lon: float
    :return: object - bollards encountered while routing to a lat/lon
             on a given day, start and end time.
    """
    db_query = """
        with bollards as (
            select pp.*
            from pgr_dijkstra(
                %(pgr_dijkstra_cost_query)s,
                902205,
                (
                    select target
                    from bereikbaarheid.out_vma_directed a
                    where cost > 0 or car_network is false
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
            ) as routing

            left join bereikbaarheid.out_vma_directed g
            on g.id = routing.edge

            left join bereikbaarheid.bd_verkeerspalen pp
            on abs(routing.edge) = pp.linknr
            where paalnummer is not null
            and (
                (
                    %(day_of_the_week)s <> ANY(dagen)
                    or %(day_of_the_week)s is null
                )
                and (%(time_from)s <= begin_tijd or %(time_from)s is null)
                and (%(time_to)s <= eind_tijd or %(time_to)s is null)
            )

            order by seq
        )

        select json_build_object(
            'geometry', ST_Transform(bollards.geometry, 4326)::json,
            'properties', json_build_object(
                'id', bollards.paalnummer,
                'type', bollards.type,
                'location', bollards.standplaats,
                'days', bollards.dagen,
                'start_time', bollards.begin_tijd,
                'end_time', bollards.eind_tijd,
                'entry_system', bollards.toegangssysteem
            ),
            'type', 'Feature'
        )
        from bollards

        -- the "or parameter_name is null" makes sure the bollards are
        -- returned when the optional parameters are not present
        where (
                %(day_of_the_week)s <> ANY(bollards.dagen)
                or %(day_of_the_week)s is null
            )
            and (%(time_from)s <= bollards.begin_tijd or %(time_from)s is null)
            and (%(time_to)s <= bollards.eind_tijd or %(time_to)s is null)
    """

    query_params = {
        "day_of_the_week": day_of_the_week,
        "pgr_dijkstra_cost_query": prepare_pgr_dijkstra_cost_query(
            day_of_the_week, time_from, time_to
        ),
        "lat": lat,
        "lon": lon,
        "time_from": time_from,
        "time_to": time_to,
    }

    try:
        return query_db(db_query, query_params)

    except Exception:
        print("Error while retrieving bollards")


def prepare_pgr_dijkstra_cost_query(day_of_the_week, time_from, time_to):
    """
    Helper function for the query_db_bollards function
    Prepares a database query for use in the pgr_dijkstraCost db function

    This preparation is needed because the pgr_dijkstraCost db function uses
    psycopg placeholders. When defining this query inline - in the db_query
    variable of the query_db_bollards function above - the %(time_to)s and
    %(time_from)s placeholders cause a SQL syntax error (because the date's
    are single-quoted within a single quoted statement). Therefore this query
    is prepared first, and returned for use as a query parameter in the
    query_db_bollards function.

    :param day_of_the_week: string - e.g "di"
    :param time_from: string - e.g "08:00:00"
    :param time_to: string - e.g "16:00:00"
    :return: prepared db query for use in the pgr_dijkstraCost db function
    """

    pgr_dijkstra_cost_query = """
        select v.id,
            v.source,
            v.target,
            v.car_network,
            v.geom,

            case
                -- cars are allowed AND bollard is blocked
                when car_network = true
                    and (
                        %(day_of_the_week)s <> ANY(dagen)
                        or %(time_from)s <= begin_tijd
                        or %(time_to)s >= eind_tijd
                    )
                    then cost * 10000

                -- cars are not allowed AND bollard is blocked
                when car_network = false
                    and (
                        %(day_of_the_week)s <> ANY(dagen)
                        or %(time_from)s <= begin_tijd
                        or %(time_to)s >= eind_tijd
                    )
                    then 10000 * 10000 * 2

                -- cars are allowed AND bollard is open
                when car_network = true and p.paalnummer is not null
                    then cost * 10000

                -- cars are not allowed AND bollard is open
                when car_network = false and p.paalnummer is not null
                    then 10000 * 10000

                -- cars are not allowed, road section cost is -1
                when car_network = false
                    then 10000 * 10000

                -- cars are allowed AND bollard is open
                else cost
            end as cost,

            p.paalnummer,
            p.dagen,
            p.begin_tijd,
            p.eind_tijd,
            p.geometry

            from bereikbaarheid.out_vma_directed v

            left join bereikbaarheid.bd_verkeerspalen p
            on abs(v.id) = abs(p.linknr)
            where car_network = true
            or abs(id) in (
                select linknr from bereikbaarheid.bd_venstertijdwegen
            )
        """

    pgr_dijkstra_cost_query_params = {
        "day_of_the_week": day_of_the_week,
        "time_from": time_from,
        "time_to": time_to,
    }

    cursor = get_db().cursor()

    return cursor.mogrify(
        pgr_dijkstra_cost_query, pgr_dijkstra_cost_query_params
    ).decode("utf-8")
