from flask import current_app, g
import psycopg2


def get_db():
    """Connect to the application's configured database. The connection
    is unique for each request and will be reused if this is called again.
    """
    if "db" not in g:
        g.db = psycopg2.connect(
            database=current_app.config["DB_NAME"],
            user=current_app.config["DB_USER"],
            password=current_app.config["DB_PWD"],
            host=current_app.config["DB_HOST"],
            port=current_app.config["DB_PORT"],
            sslmode=current_app.config["DB_SSL"],
        )

    return g.db


def close_db(e=None):
    """
    If this request connected to the database, close the connection.
    """
    db = g.pop("db", None)

    if db is not None:
        db.close()


def query_db(query, query_params, fetch_one=False):
    """
    Query the database
    :param query: the SQL query
    :param query_params: a dict with named arguments
    :param fetch_one: if one result should be fetched, defaults to False
    :return: the query results

    Debug queries with:
        print(cursor.mogrify(query, query_params).decode("utf-8"))
    """
    try:
        cursor = get_db().cursor()
        cursor.execute(query, query_params)

        if fetch_one:
            return cursor.fetchone()

        return cursor.fetchall()

    except (Exception, psycopg2.DatabaseError) as error:
        print("Error: no connection or error in query: ", error)
        # re-raise exception so API endpoint using this can add HTTP messages
        raise Exception


def init_app(app):
    """Register database functions with the Flask app. This is called by
    the application factory.
    """
    app.teardown_appcontext(close_db)
