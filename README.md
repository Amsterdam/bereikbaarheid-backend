# Backend
Deze folder bevat de Bereikbaarheid API zoals zichtbaar op https://api.data.amsterdam.nl/bereikbaarheid/v1/ .

## Mappen & bestanden
Deze folder is als volgt ingedeeld:

* `requirements` bevat de Python applicatie requirements.
* `src` bevat een Flask applicatie met 1) de API (`src/app/api`) en 2) een status endpoint (`src/app/status`).
* `Dockerfile` bevat config voor de Docker omgeving.
* `Dockerfile_python_deps`; gebruikt voor onderhoud aan Python dependencies, zie hieronder voor meer info.
* `.flake8`; Flake8 linting config, zie het [Contributing document](./CONTRIBUTING.md) voor meer info.
* `pyproject.toml`; Black formatting config, zie het [Contributing document](./CONTRIBUTING.md) voor meer info.
* `start_app.sh`; Docker entry point, deze start de Flask applicatie.

## Getting Started
Om lokaal te kunnen ontwikkelen wordt gebruik gemaakt van Docker-compose. 

- Setup a PostgreSQL database with PostGIS 3.1.x and pgRouting 3.0.x extensions enabled.
- Download a copy of the database and import it locally
- Copy `.env.example` and rename to `.env`. A `.env` file is needed to run the Docker container.
- Complete the missing environment variables in `.env`.
- Run the docker container: `docker-compose up --build`.

De backend is beschikbaar op `localhost:8000`. De `src` folder wordt gedeeld met de container, dus lokale wijzigingen zijn zichtbaar in je browser na het verversen van de pagina.

## Contributing
You would like to contribute? Great! All input, feedback and improvements are very welcome. Whether it is reporting a problem, suggesting a change, asking a question, improving the docs or code. Please have a look at the [Contributing document](./CONTRIBUTING.md).

## Maintenance
Please see [the maintenance documentation](./docs/maintenance.md) for info about how to update Python dependencies.
