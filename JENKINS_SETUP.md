# Jenkins Freestyle setup

## Prerequisites (Windows Jenkins host)
- Docker Desktop installed and running (Compose v2: `docker compose version`).
- Jenkins plugins: **Git**, **JUnit**, **Credentials Binding**, **Timestamper** (optional).
- The Jenkins service must run as a user that can reach Docker. The default
  `LocalSystem` account usually cannot talk to Docker Desktop: Services ->
  Jenkins -> Log On -> use your Windows user, then restart the service.

## One-time data migration
The old container ran as root, so the existing `lost_found_data` volume is
root-owned. The new image runs as UID 10001. Fix once:

    docker run --rm -v lost_found_data:/data alpine chown -R 10001:10001 /data

## Create the job
New Item -> name `campus-lost-found` -> **Freestyle project**.

**General**: tick *Discard old builds* (keep ~10).

**Source Code Management -> Git**
- Repository URL: your GitHub repo (add a PAT credential if private)
- Branch Specifier: `*/main`

**Build Triggers -> Poll SCM**: `H/2 * * * *`
(polls GitHub every ~2 min; builds only when there are new commits)

**Build Environment**
- *Use secret text(s)*: Variable `SECRET_KEY`, credential = a Secret text you
  create (any long random string). Needed by docker-compose.yml.
- *Add timestamps to the Console Output* (optional)

**Build Steps** (all "Execute Windows batch command", in this order)
1. `ci\test.bat`    - builds images, runs 15 unit tests + Selenium in Firefox containers
2. `ci\deploy.bat`  - `docker compose up -d --build --wait` (only reached if step 1 passed)
3. `ci\verify.bat`  - calls /health inside the deployed container

**Post-build Actions**
- *Publish JUnit test result report*: `test-results/junit.xml`
- *Archive the artifacts*: `test-results/**` (optional; includes app.log)

Save -> Build Now. Then push a commit and watch the poll trigger a build.
App is at http://localhost:5000.

## Notes
- A failing build step stops the job, so a broken commit is never deployed.
- If `selenium/standalone-firefox:4.38.0` can't be pulled, pick an existing tag
  from hub.docker.com/r/selenium/standalone-firefox and keep it close to the
  `selenium` version in requirements-dev.txt.
