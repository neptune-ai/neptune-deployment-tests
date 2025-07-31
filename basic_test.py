# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "neptune-scale",
#   "typer",
# ]
# ///


import math
import os
import random
import time

import typer
from neptune_scale import Run

app = typer.Typer()
def populate_run(run, run_id, fields: int, steps: int, tags=None):
    if tags:
        run.add_tags(tags)

    data = {f"config/foo{x + 1}": f"valfoo{x + 1}" for x in range(fields)}
    data |= {f"config/bar{x + 1}": x + 1 for x in range(fields)}
    data |= {f"config/foo{x + 1}-unique-{run_id}": x + 1 for x in range(10)}
    run.log_configs(data)

    step = 0
    for step in range(steps - 1):
        value = math.sin((step + random.random() - 0.5) * 0.1)
        data = {f"metrics/foo{x + 1}": value for x in range(fields)}
        data |= {f"metrics/bar{x + 1}": value for x in range(fields)}
        data |= {f"metrics/bar{x + 1}-unique-{run_id}": value for x in range(10)}
        run.log_metrics(step=step, data=data)

    # Last step will have a predetermined value
    step += 1
    data = {f"metrics/foo{x + 1}": x + 1 for x in range(fields)}
    data |= {f"metrics/bar{x + 1}-unique-{run_id}": x + 1 for x in range(10)}
    data |= {f"metrics/bar{x + 1}": x + 1 for x in range(fields)}

    run.log_metrics(step=step, data=data)


def create_run(index, tags, fields: int, steps: int, experiment_name=None):
    print(f"create_runs({index}, {tags}, {experiment_name})")
    kind = "run" if not experiment_name else "exp"
    run_id = f"id-{kind}-{index}"
    with Run(run_id=run_id, experiment_name=experiment_name) as run:
        print("Populating run", run_id)
        populate_run(run, run_id, fields, steps, tags=tags)


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


@app.command()
def main(
    fields: int = typer.Option(10, "--fields", "-f", help="Number of field kinds to create"),
    steps: int = typer.Option(50_000, "--steps", "-s", help="Number of steps to log")
):
    """Run Neptune scale test with configurable fields and steps."""
    check_environment_variables()
    
    start_time = time.time()
    create_run(int(time.time()), ["test20k"], fields, steps, f"exp20k-{start_time}")
    print("--- %s seconds ---" % (time.time() - start_time))


if __name__ == '__main__':
    app()
