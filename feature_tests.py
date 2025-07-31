# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "neptune-scale",
#   "neptune-fetcher",
#   "requests",
#   "typer",
# ]
# ///

from pathlib import Path
from datetime import datetime
import math
import os
import tempfile
import numpy as np
from functools import wraps
import base64
import json

import typer
import requests
from neptune_scale import Run
from neptune_scale.types import Histogram
import neptune_fetcher.alpha.runs as npt_runs

tests_available = 0
tests = []
tests_run = 0
tests_passed = 0

app = typer.Typer()


def check_environment_variables():
    """Check that required Neptune environment variables are set."""
    if not os.getenv("NEPTUNE_API_TOKEN"):
        typer.echo("Error: NEPTUNE_API_TOKEN environment variable is not set", err=True)
        raise typer.Exit(1)
    
    if not os.getenv("NEPTUNE_PROJECT"):
        typer.echo(
            "Error: NEPTUNE_PROJECT environment variable is not set - set it using:\nexport NEPTUNE_PROJECT=my-team/deployment-tests",
            err=True
        )
        raise typer.Exit(1)


def test(func):
    global tests, tests_available
    tests_available += 1

    @wraps(func)
    def wrapper(*args, ):
        global tests_run, tests_passed
        try:
            print("")
            print(func.__name__)
            print("")
            tests_run += 1
            func(*args, )
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


def manual_confirm(message: str):
    print("")
    print("[MANUAL CONFIRMATION REQUIRED]")
    print(message)
    print("Is this correct? (Y/n)")
    if input().lower() == "n":
        raise KeyboardInterrupt


def url_friendly_datetime():
    """Generate URL-friendly datetime string with dash separators."""
    return datetime.now().strftime("%Y-%m-%d-%H-%M-%S")


@test
def test_neptune_is_reachable():
    # Decode NEPTUNE_API_TOKEN to get the api_url
    api_token = os.environ["NEPTUNE_API_TOKEN"]
    data = json.loads(base64.b64decode(api_token).decode("utf-8"))
    neptune_url = data["api_url"]
    
    response = requests.get(f"{neptune_url}/api/backend/status")
    response.raise_for_status()

    assert response.status_code == 200, f"{response.status_code=} (expected 200)"


@test
def test_log_configs_manual():
    run_id = f"test_log_configs_manual-{url_friendly_datetime()}"
    run = Run(
        run_id=run_id,
        experiment_name=run_id,
        enable_console_capture=False,
    )
    configs = {"integer": 1, "float": 2.5, "boolean": True, "string": "test", "datetime": datetime.now()}
    run.log_configs(data=configs)
    run.close(timeout=60.0)

    message = "\n".join([
        f"Configs: {configs}",
        "Confirm configs are visible in the web app by visiting:",
        run.get_run_url()
    ])
    manual_confirm(message)


@test
def test_log_metrics_manual():
    run_id = f"test_log_metrics_manual-{url_friendly_datetime()}"
    run = Run(
        run_id=run_id,
        experiment_name=run_id,
        enable_console_capture=False,
    )
    for step in range(1, 100_000):
        run.log_metrics(
            data={"step": step, "value": math.log(step)},
            step=step
        )
    run.close(timeout=60.0)

    message = "\n".join([
        "Metrics: step, value",
        "Confirm metrics above are visible in the web app by visiting:",
        run.get_run_url()
    ])
    manual_confirm(message)


@test
def test_configs_metrics_fetcher():
    run_id = f"test_configs_metrics_fetcher-{url_friendly_datetime()}"
    run = Run(
        run_id=run_id,
        experiment_name=run_id,
        enable_console_capture=False,
    )
    
    # Log configs
    expected_configs = {
        "configs/integer": 1,
        "configs/float": 2.5,
        "configs/boolean": True,
        "configs/string": "test",
        "configs/datetime": datetime.now(),
    }
    run.log_configs(data=expected_configs)
    
    # Log metrics
    expected_steps = list(range(1, 100))
    for step in expected_steps:
        run.log_metrics(
            data={"metrics/step": step, "metrics/value": math.log(step)},
            step=step
        )
    run.close(timeout=60.0)
    
    configs_df = npt_runs.fetch_runs_table(
        runs=[run_id],
        attributes=["configs/integer", "configs/float", "configs/boolean", "configs/string", "configs/datetime"],
    )
    metrics_df = npt_runs.fetch_metrics(
        runs=[run_id],
        attributes=["metrics/step", "metrics/value"],
    )
    
    # Validate configs
    assert len(configs_df) == 1, f"{len(configs_df)=} (expected 1)"
    fetched_row = configs_df.iloc[0]
    
    assert fetched_row["configs/integer"].item() == expected_configs["configs/integer"], f"{fetched_row['configs/integer'].item()=} (expected {expected_configs['configs/integer']})"
    assert fetched_row["configs/float"].item() == expected_configs["configs/float"], f"{fetched_row['configs/float'].item()=} (expected {expected_configs['configs/float']})"
    assert fetched_row["configs/boolean"].item() == expected_configs["configs/boolean"], f"{fetched_row['configs/boolean'].item()=} (expected {expected_configs['configs/boolean']})" 
    assert fetched_row["configs/string"].item() == expected_configs["configs/string"], f"{fetched_row['configs/string'].item()=} (expected {expected_configs['configs/string']})"
    
    # Validate metrics
    assert len(metrics_df) == len(expected_steps), f"{len(metrics_df)=} (expected {len(expected_steps)})"
    fetched_steps = sorted(metrics_df['metrics/step'].unique())
    assert fetched_steps == expected_steps, f"{fetched_steps=} (expected {expected_steps})"
    
    # Validate a few sample metric values
    for step in [1, 10, 50, 99]:
        step_row = metrics_df[metrics_df['metrics/step'] == step]
        assert len(step_row) == 1, f"{len(step_row)=} (expected 1)"
        
        fetched_step_value = step_row.iloc[0]['metrics/step'].item()
        fetched_value = step_row.iloc[0]['metrics/value'].item()
        expected_value = math.log(step)
        
        assert fetched_step_value == step, f"{fetched_step_value=} (expected {step})"
        assert abs(fetched_value - expected_value) < 1e-10, f"{fetched_value=:.2f} (expected {expected_value=:.2f})"


@test
def test_log_strings_fetcher():
    run_id = f"test_log_strings_fetcher-{url_friendly_datetime()}"
    run = Run(
        run_id=run_id,
        experiment_name=run_id,
        enable_console_capture=True,
    )
    
    expected_steps = list(range(1, 10))
    expected_messages = {}
    
    for step in expected_steps:
        message = f"we are at step {step}"
        print(f"logging {step=}")
        run.log_string_series(data={"message": message}, step=step)
        expected_messages[step] = message
        
    run.close(timeout=60.0)
    
    # Fetch string series data
    series_df = npt_runs.fetch_series(
        runs=[run_id],
        attributes=["message", "runtime/stdout"],
    )
    
    # Reset index to make step a regular column
    series_df_reset = series_df.reset_index()
    
    # Validate message string series - filter for rows with non-NaN message values
    message_data = series_df_reset[series_df_reset['message'].notna()]
    
    # Check that we have the expected number of message entries
    assert len(message_data) == len(expected_steps), f"{len(message_data)=} (expected {len(expected_steps)})"
    
    # Validate each logged message
    for step in expected_steps:
        step_data = message_data[message_data['step'] == step]
        assert len(step_data) == 1, f"Expected exactly 1 row for step {step}, got {len(step_data)}"
        
        fetched_message = step_data.iloc[0]['message']
        expected_message = expected_messages[step]
        assert fetched_message == expected_message, f"{fetched_message=} (expected {expected_message})"
    
    # Validate that runtime/stdout data exists (console capture should have generated some output)
    stdout_data = series_df_reset[series_df_reset['runtime/stdout'].notna()]
    assert len(stdout_data) > 0, "Expected runtime/stdout data from console capture, but none found"


@test
def test_log_files_fetcher():
    run_id = f"test_log_files_fetcher-{url_friendly_datetime()}"
    
    # Use the current Python file as test content
    current_file = Path(__file__)
    expected_content = current_file.read_text()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        run = Run(
            run_id=run_id,
            experiment_name=run_id,
            enable_console_capture=False,
        )
        run.assign_files(files={"test_script": current_file})
        run.close(timeout=60.0)
        
        download_dir = Path(temp_dir)
        npt_runs.download_files(
            runs=[run_id],
            attributes=["test_script"],
            destination=str(download_dir)
        )

        # Look for the downloaded file - it will be named by the attribute name "test_script"
        downloaded_file_path = download_dir / "test_script"
        
        # If not found directly, search for it recursively
        if not downloaded_file_path.exists():
            all_files = list(download_dir.rglob("*"))
            file_candidates = [f for f in all_files if f.is_file() and f.name == "test_script"]
            assert len(file_candidates) > 0, f"test_script file not found, available files: {[f.name for f in all_files]}"
            downloaded_file_path = file_candidates[0]
        
        downloaded_content = downloaded_file_path.read_text()
        assert downloaded_content == expected_content, "Downloaded file content doesn't match original"




@test
def test_log_histograms_only():
    run_id = f"test_log_histograms_only-{url_friendly_datetime()}"
    run = Run(
        run_id=run_id,
        experiment_name=run_id,
        enable_console_capture=False,
    )
    
    # Log histogram series for different distributions
    for step in range(1, 20):
        # Generate sample data for histograms
        normal_data = np.random.normal(0, 1, 1000)
        uniform_data = np.random.uniform(-2, 2, 500)
        exponential_data = np.random.exponential(2, 800)
        activations_data = np.random.normal(step * 0.1, 0.5, 100)
        gradients_data = np.random.normal(0, 0.01, 200)
        
        # Convert numpy arrays to Neptune Histogram objects
        normal_counts, normal_bins = np.histogram(normal_data, bins=30)
        uniform_counts, uniform_bins = np.histogram(uniform_data, bins=25)
        exponential_counts, exponential_bins = np.histogram(exponential_data, bins=35)
        activations_counts, activations_bins = np.histogram(activations_data, bins=20)
        gradients_counts, gradients_bins = np.histogram(gradients_data, bins=25)
        
        # Log histograms with different distributions
        run.log_histograms(
            histograms={
                "distributions/normal": Histogram(bin_edges=normal_bins, counts=normal_counts),
                "distributions/uniform": Histogram(bin_edges=uniform_bins, counts=uniform_counts),
                "distributions/exponential": Histogram(bin_edges=exponential_bins, counts=exponential_counts),
                "activations/layer1": Histogram(bin_edges=activations_bins, counts=activations_counts),
                "gradients/weights": Histogram(bin_edges=gradients_bins, counts=gradients_counts),
            },
            step=step
        )
    
    run.close(timeout=60.0)

@test
def test_fork_experiment_only():
    parent_run_id = f"test_fork_experiment_only-{url_friendly_datetime()}-parent"
    
    # Create original experiment run
    original_run = Run(
        experiment_name=parent_run_id,
        run_id=parent_run_id,
        enable_console_capture=False,
    )
    
    # Log some initial data to the original experiment
    original_run.log_configs({
        "model_type": "transformer",
        "learning_rate": 0.001,
        "batch_size": 32,
        "optimizer": "adam"
    })
    
    for step in range(1, 10_000):
        original_run.log_metrics(
            data={
                "train/loss": 2.0 - (step * 0.03),
                "train/accuracy": min(0.95, step * 0.02),
                "val/loss": 2.1 - (step * 0.025),
            },
            step=step
        )
    
    original_run.close(timeout=60.0)
    
    # Fork from the original experiment
    forked_run = Run(
        experiment_name=parent_run_id.replace("-parent", "-child"),
        run_id=parent_run_id.replace("-parent", "-child"),
        fork_run_id=parent_run_id,
        fork_step=7_500,
        enable_console_capture=False,
    )
    
    # Continue logging from the fork point
    forked_run.log_configs({
        "fork_reason": "hyperparameter_tuning",
        "learning_rate": 0.0005,  # Changed learning rate
        "warmup_steps": 100,
    })
    
    for step in range(7_500, 15_000):
        forked_run.log_metrics(
            data={
                "train/loss": 1.5 - ((step - 50) * 0.02),
                "train/accuracy": min(0.98, 0.5 + (step - 50) * 0.01),
                "val/loss": 1.6 - ((step - 50) * 0.018),
            },
            step=step
        )
    
    forked_run.close(timeout=60.0)

@test
def test_resume_run_only():
    run_id = f"test_resume_run_only-{url_friendly_datetime()}"
    
    # Create initial run and log some data
    initial_run = Run(
        run_id=run_id,
        experiment_name=run_id,
        enable_console_capture=False,
    )
    
    # Log initial configs and metrics
    initial_run.log_configs({
        "model": "resnet50",
        "epochs": 100,
        "initial_lr": 0.01,
        "dataset": "imagenet"
    })
    
    # Log first phase of training (steps 1-30)
    for step in range(1, 31):
        initial_run.log_metrics(
            data={
                "train/loss": 3.0 - (step * 0.05),
                "train/accuracy": min(0.85, step * 0.025),
                "val/loss": 3.2 - (step * 0.04),
                "val/accuracy": min(0.80, step * 0.02),
                "learning_rate": 0.01 * (0.95 ** (step // 10))
            },
            step=step
        )
    
    # Simulate interruption by closing the run
    initial_run.close(timeout=60.0)
    
    # Resume the same run
    resumed_run = Run(
        run_id=run_id,
        experiment_name=run_id,
        resume=True,
        enable_console_capture=False,
    )
    
    # Update configs for resumed training
    resumed_run.log_configs({
        "resumed": True,
        "resume_step": 30,
        "adjusted_lr": 0.005,
    })
    
    # Continue training from step 31
    for step in range(31, 61):
        resumed_run.log_metrics(
            data={
                "train/loss": 1.5 - ((step - 30) * 0.02),
                "train/accuracy": min(0.95, 0.75 + (step - 30) * 0.006),
                "val/loss": 1.7 - ((step - 30) * 0.018),
                "val/accuracy": min(0.92, 0.70 + (step - 30) * 0.005),
                "learning_rate": 0.005 * (0.98 ** ((step - 30) // 10))
            },
            step=step
        )
    
    resumed_run.close(timeout=60.0)


@app.command()
def main(
    filter: str = typer.Option(None, "--filter", "-f", help="Only run tests containing this substring"),
):
    """Run Neptune feature tests with environment variables."""
    check_environment_variables()

    if filter:
        filtered_tests = [fn for fn in tests if filter.strip() in fn.__name__]
        print(f"Running {len(filtered_tests)} out of {tests_available} available tests...")
    else:
        filtered_tests = tests
        print(f"Running {tests_available} tests...")

    for fn in filtered_tests:
        fn()

    print("--------------------------------")
    print(f"Tests executed: {tests_run}/{tests_available}")
    print(f"Tests passed: {tests_passed}/{tests_run}")
    print("--------------------------------")


if __name__ == "__main__":
    app()
