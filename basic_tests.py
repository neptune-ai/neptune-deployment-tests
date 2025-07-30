import requests
from pathlib import Path
import yaml
from datetime import datetime
import math

from neptune_scale import Run

tests_available = 0
tests = []
tests_run = 0
tests_passed = 0


def test(func):
    global tests, tests_available
    tests_available += 1

    def wrapper(*args, **kwargs):
        global tests_run, tests_passed
        try:
            print("")
            print(func.__name__)
            print("")
            tests_run += 1
            func(*args, **kwargs)
            tests_passed += 1
            print(f"{func.__name__} passed")
        except Exception as e:
            print(f"{func.__name__} failed")
            print(e)
            print("Do you wish to continue tests? (Y/n)")
            if input().lower() == "n":
                raise e from e
    
    tests.append(wrapper)
    return wrapper


@test
def test_neptune_is_reachable(neptune_url: str, **kwargs):
    response = requests.get(f"{neptune_url}/api/backend/status")
    response.raise_for_status()

    assert response.status_code == 200, f"{response.status_code=} (expected 200)"


@test
def test_log_configs(neptune_api_token: str, neptune_project: str, **kwargs):
    run = Run(
        run_id=f"test-log-configs-{datetime.now().isoformat()}",
        api_token=neptune_api_token,
        project=neptune_project,
        enable_console_capture=False,
    )
    configs = {"integer": 1, "float": 2.5, "boolean": True, "string": "test", "datetime": datetime.now()}
    run.log_configs(data=configs)
    run.close()

    print(f"Configs: {configs}")
    print("Confirm configs are visible in the web app by visiting:")
    print(run.get_run_url())
    print("Are configs visible? (Y/n)")
    if input().lower() == "n":
        raise KeyboardInterrupt


@test
def test_log_metrics(neptune_api_token: str, neptune_project: str, **kwargs):
    run = Run(
        run_id=f"test-log-metrics-{datetime.now().isoformat()}",
        api_token=neptune_api_token,
        project=neptune_project,
        enable_console_capture=False,
    )
    for step in range(1, 100):
        run.log_metrics(
            data={"step": step, "value": math.log(step)},
            step=step
        )
    run.close()

    print("Metrics: step, value")
    print("Confirm metrics above are visible in the web app by visiting:")
    print(run.get_run_url())
    print("Are the metrics visible? (Y/n)")
    if input().lower() == "n":
        raise KeyboardInterrupt


@test
def test_log_strings(neptune_api_token: str, neptune_project: str, **kwargs):
    run = Run(
        run_id=f"test-log-strings-{datetime.now().isoformat()}",
        api_token=neptune_api_token,
        project=neptune_project,
        enable_console_capture=True,
    )
    for step in range(1, 10):
        print(f"logging {step=}")
        run.log_string_series(data={"message": f"we are at step {step}"}, step=step)
    run.close()

    print("String series: message, runtime/stdout")
    print("Confirm string series above are visible in the web app by visiting:")
    print(run.get_run_url())
    print("Are the string series visible? (Y/n)")
    if input().lower() == "n":
        raise KeyboardInterrupt


@test
def test_log_files(neptune_api_token: str, neptune_project: str, **kwargs):
    run = Run(
        run_id=f"test-log-files-{datetime.now().isoformat()}",
        api_token=neptune_api_token,
        project=neptune_project,
        enable_console_capture=False,
    )
    run.assign_files(files={"this_script": Path(__file__)})
    for step in range(1, 10):
        run.log_files(files={"this_script_series": Path(__file__)}, step=step)
    run.close()

    print("Files: this_script, this_script_series")
    print("Confirm files above are visible in the web app by visiting:")
    print(run.get_run_url())
    print("Are the files visible? (Y/n)")
    if input().lower() == "n":
        raise KeyboardInterrupt


# @test
# def test_log_histograms(neptune_api_token: str, neptune_project: str, **kwargs):
#     pass # TODO

# @test
# def test_fork_experiment(neptune_api_token: str, neptune_project: str, **kwargs):
#     pass # TODO

# @test
# def test_resume_run(neptune_api_token: str, neptune_project: str, **kwargs):
#     pass # TODO


if __name__ == "__main__":
    with open(Path(__file__).parent / "secrets.yml", "r") as f:
        secrets = yaml.safe_load(f)

    print(f"Running {tests_available} tests...")
    for fn in tests:
        fn(**secrets)

    print(f"Tests passed: {tests_passed}/{tests_run}")
