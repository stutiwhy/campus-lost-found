campus-lost-found

A web app for reporting and tracking lost and found items on a college campus. Students can post what they lost or found, search and filter existing reports, and mark items as resolved once they are returned. It is containerized with Docker and built, tested and deployed automatically by a Jenkins freestyle job that polls GitHub.

stack

flask, python, sqlite, bootstrap 5, gunicorn, docker, docker compose, jenkins (freestyle), pytest, selenium

deployment

app: http://localhost:5000

infrastructure:

* docker container (gunicorn, non-root user, built-in healthcheck)
* named docker volume for the sqlite database
* jenkins freestyle job with github source and scm polling

features

* report an item as lost or found
* searchable and filterable dashboard (text, type, category, status)
* detailed item page
* one-click mark as resolved
* live stats for total, open and resolved reports
* server-side validation of all fields, categories and lengths
* health endpoint for monitoring and deployment checks
* responsive ui built with bootstrap

categories

Electronics, ID Cards, Books, Bags, Clothing, Accessories, Other

project structure

app

* app.py: flask routes, validation and sqlite access.
* templates: base layout, dashboard, report form, item detail and 404 page.
* static: custom styles on top of bootstrap.

routes

* /: dashboard with search and filters
* /report: submit a lost or found report
* /item/<id>: item details
* /resolve/<id>: mark an item as resolved (POST)
* /health: returns app and database status as json

database

* items: id, name, category, description, location, report_type (Lost or Found), status (Open or Resolved), created_at

Sqlite runs in wal mode so multiple gunicorn workers can read while one writes. The database file lives in the docker volume so reports survive redeploys.

testing

* unit tests (pytest): validation, saving, search, filters, resolving, 404s, health check and html escaping
* browser test (selenium + firefox): reports an item, searches for it, resolves it and filters resolved items through the real ui

docker

* Dockerfile: multi-stage build with base, test and runtime targets. Tests tools are never shipped in the deployed image.
* docker-compose.yml: deployment stack with the app, port 5000 and the persistent volume.
* docker-compose.ci.yml: throwaway test stack with the app, a firefox selenium container and the test runner.

ci/cd pipeline

Jenkins freestyle job, triggered by poll scm (H/2 * * * *) against the github repo.

* ci/test.bat: builds the images and runs unit and selenium tests inside containers, writes test-results/junit.xml
* ci/deploy.bat: rebuilds the image and restarts the live container, waiting for it to become healthy
* ci/verify.bat: calls /health inside the deployed container

A failing test stops the build before anything is deployed. Full job configuration is in JENKINS_SETUP.md.

run locally

Without docker:

* pip install -r requirements-dev.txt
* python app.py
* python -m pytest test_app.py

With docker:

* set SECRET_KEY=any-long-random-string
* docker compose up -d --build --wait
* open http://localhost:5000

Run the full test suite in containers:

* docker compose -f docker-compose.ci.yml up --build --abort-on-container-exit --exit-code-from tests
* docker compose -f docker-compose.ci.yml down -v

configuration

* SECRET_KEY: flask session signing key (required for docker compose deployment)
* DATABASE_PATH: sqlite file location (defaults to /data/lost_found.db in the container)
* PORT: port used when running python app.py (defaults to 5000)

known limitations

* no login, so anyone can mark any item as resolved
* no csrf protection on forms
* no image uploads or pagination yet

o/p demo ss
 <img src="op-1.png"> <img src="op-2.png"> <img src="op-3.png"> <img src="op-4.png">