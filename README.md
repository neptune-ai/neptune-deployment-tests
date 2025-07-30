# Neptune Deployment Tests

Tests worth running to confirm successful setup of a self-hosted neptune instance.

Tests are divided into basic & performance tests:
- basic tests are short and require minimal human intervention, we recommend running them after each deployment and upgrade
- performance tests run for much longer (typically hours) and can be used to spot performance regressions at scale

Both kinds of tests require some minimal manual actions to validate the results, and are intended to be completed as a kind of "checklist".

## Quick start

### 1. Clone this repo and set up python virtual env with all dependencies:

```bash
python3 -m venv .env
source .env/bin/activate
pip install -r requirements.txt
export PYTHONPATH=`pwd`
```

## 2. Set up your environment

Rename `secrets.yml.example` to `secrets.yml`.

Log into your neptune workspace in the web app, and:
- create a new project for the tests in your organization workspace & copy paste its full path (including workspace name, such as `my-workspace/deployment-tests`) into `secrets.yml`
- copy paste your neptune api token to `secrets.yml`
- finally, set your neptune URL in `secrets.yml` if you're not using 

## 3. Run the basic tests

Run the command to run all basic tests:
```
python basic_tests.py
```

The script will prompt you for some manual verification actions to perform.

