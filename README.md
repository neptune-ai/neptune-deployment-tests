# Neptune Deployment Tests

Tests worth running to confirm successful setup of a self-hosted neptune instance.

Tests are divided into:
1. `basic_test.py` that only checks minimal logging functionality & can be parametrized by number of metrics & steps logged
2. `feature_tests.py` with comprehensive checks for most logging & retrieval features (recommended for deployment validation)
3. `performance_tests.py` measuring logging throughput & retrieval performance (not implemneted yet)

Some (<10%) of the tests will prompt you for maual validation actions, to be completed as a kind of post-deployment "checklist".

## Quick start

Dependencies:

1. Create a project called `deployment-tests` in your workspace using neptune web app
2. Clone this repository & set up necessary environment variables:
    - `export NEPTUNE_API_TOKEN=my-api-token`, using your user token copied from your neptune web app
    - `export NEPTUNE_PROJECT=my-workspace/deployment-tests`, using workspace & project name from step 1

We recommend running the scripts using `uv`, which supports [inline script metadata with package dependencies](https://docs.astral.sh/uv/guides/scripts/#declaring-script-dependencies):

```bash
uv run basic_test.py
uv run feature_tests.py # this one will prompt you for 2-3 manual validation actions in the web app
```

You can re-try specifc tests using filtering:
```bash
uv run feature_tests.py -f fetcher # only runs tests that contain "fetcher" in their funciton name - no manual actions required
```

Alternatively, you can use `pip` & `virtualenv`:
```bash
python3 -m venv .env
source .env/bin/activate
pip install -r requirements.txt
```

And then run the tests using:

```bash
python basic_test.py
python feature_tests.py
```

To make test output less verbose, set [`NEPTUNE_LOGGER_LEVEL` environment variable](https://docs.neptune.ai/environment_variables/neptune_scale/#neptune_logger_level) to `warning`.
