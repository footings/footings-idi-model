import click


@click.group()
def cli():
    """CLI tool to run footings IDI model."""
    pass


@cli.command()
@cli.option("--all", default=False, help="Run all scenarios.")
@cli.argument("extract_base")
@cli.argument("extract_riders")
@cli.argument("valuation_dt")
@cli.argument("assumption_set")
@cli.argument("scenarios", nargs=-1)
def run_active_life_valuation(
    all, extract_base, extract_riders, valuation_dt, assumption_set, scenarios
):
    """Run valuation model."""
    return valuation_dt


@cli.command()
@cli.option("--all", default=False, help="Run all scenarios.")
@cli.argument("extract_base")
@cli.argument("extract_riders")
@cli.argument("valuation_dt")
@cli.argument("assumption_set")
@cli.argument("scenarios", nargs=-1)
def run_active_life_projection(
    all, extract_base, extract_riders, valuation_dt, assumption_set, scenarios
):
    """Run projection model."""
    return valuation_dt


@cli.command()
@cli.option("--all", default=False, help="Run all scenarios.")
@cli.argument("extract_base")
@cli.argument("extract_riders")
@cli.argument("valuation_dt")
@cli.argument("assumption_set")
@cli.argument("scenarios", nargs=-1)
def run_disabled_life_valuation(
    all, extract_base, extract_riders, valuation_dt, assumption_set, scenarios
):
    """Run valuation model."""
    return valuation_dt


@cli.command()
@cli.option("--all", default=False, help="Run all scenarios.")
@cli.argument("extract_base")
@cli.argument("extract_riders")
@cli.argument("valuation_dt")
@cli.argument("assumption_set")
@cli.argument("scenarios", nargs=-1)
def run_disabled_life_projection(
    all, extract_base, extract_riders, valuation_dt, assumption_set, scenarios
):
    """Run projection model."""
    return valuation_dt


if __name__ == "__main__":
    cli()
