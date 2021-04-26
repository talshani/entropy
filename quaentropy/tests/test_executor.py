import os
from datetime import datetime

import pytest

from quaentropy.api.data_writer import RawResultData, Plot, PlotDataType
from quaentropy.api.execution import EntropyContext
from quaentropy.api.plot import BokehCirclePlotGenerator, BokehLinePlotGenerator
from quaentropy.instruments.lab_topology import LabResources, ExperimentResources
from quaentropy.results_backend.sqlalchemy.connector import (
    SqlalchemySqlitePandasConnector,
)
from quaentropy.results_backend.sqlalchemy.db import SqlAlchemyDB
from quaentropy.script_experiment import ScriptExperiment, script_experiment
from quaentropy.tests.mock_instruments import MockScope


def do_something():
    rest = 5
    print(f"a resting for {rest}")
    return rest


def do_something2():
    rest = 3
    print(f"b resting for {rest}")
    return rest


def an_experiment(experiment: EntropyContext):
    scope = experiment.get_resource("scope_1")
    print(scope.extra)
    a1 = do_something()
    scope.get_trig()
    for i in range(30):
        experiment.add_result(
            RawResultData("a_result", a1 + i + datetime.now().microsecond)
        )
        b1 = do_something2()
        experiment.add_result(
            RawResultData("b_result", b1 + i + datetime.now().microsecond)
        )
    micro = datetime.now().microsecond
    experiment.add_result(
        RawResultData(
            "plot",
            [
                [
                    1 * micro,
                    2 * micro,
                    3 * micro,
                    4 * micro,
                    5 * micro,
                    6 * micro,
                    7 * micro,
                    8 * micro,
                ],
                [0, 1, 2, 3, 4, 5, 6, 7],
            ],
        )
    )


def an_experiment_with_plot(experiment: EntropyContext):
    scope = experiment.get_resource("scope_1")
    a1 = do_something()
    scope.get_trig()
    for i in range(30):
        experiment.add_result(
            RawResultData("a_result", a1 + i + datetime.now().microsecond)
        )
        b1 = do_something2()
        experiment.add_result(
            RawResultData("b_result", b1 + i + datetime.now().microsecond)
        )
    micro = datetime.now().microsecond
    experiment.add_plot(
        Plot(
            label="plot",
            story="created this plot in experiment",
            data=[
                [
                    1 * micro,
                    2 * micro,
                    3 * micro,
                    4 * micro,
                    5 * micro,
                    6 * micro,
                    7 * micro,
                    8 * micro,
                ],
                [0, 1, 2, 3, 4, 5, 6, 7],
            ],
            data_type=PlotDataType.py_2d,
            bokeh_generator=BokehCirclePlotGenerator(),
        )
    )

    experiment.add_plot(
        Plot(
            label="another plot",
            story="just showing off now",
            data=[
                [1, 2, 3, 4, 5, 6, 7, 8],
                [4, 5, 6, 7, 0, 1, 2, 3],
            ],
            data_type=PlotDataType.np_2d,
            bokeh_generator=BokehLinePlotGenerator(),
        )
    )


def test_running_no_db_no_runner():
    experiment = ScriptExperiment(None, do_something, "no_db").run()
    reader = experiment.results_reader()
    print(reader.get_experiment_info())


def test_running_no_db():
    resources = ExperimentResources()
    resources.add_temp_resource("scope_1", MockScope("1.1.1.1", ""))
    runner = ScriptExperiment(resources, an_experiment, "no_db").run()
    reader = runner.results_reader()
    print(reader.get_experiment_info())
    print(reader.get_results("a_result"))


@pytest.mark.repeat(3)
def test_running_db():
    try:
        resources = ExperimentResources()
        resources.add_temp_resource("scope_1", MockScope("1.1.1.1", ""))
        db = SqlalchemySqlitePandasConnector("my_db.db")

        definition = ScriptExperiment(resources, an_experiment, "with_db")

        experiment_runner = definition.run(db)
        reader = experiment_runner.results_reader()
        print(reader.get_experiment_info())
        print(reader.get_experiment_info().script.print_all())

        db = SqlalchemySqlitePandasConnector("my_db.db")
        definition = ScriptExperiment(resources, an_experiment_with_plot, "with_db")
        definition.run(db)
    finally:
        os.remove("my_db.db")


def test_running_db_and_topology():
    try:
        # setup lab environment one time
        db = SqlAlchemyDB("db_and_topo.db")
        lab = LabResources(db)
        lab.register_resource(
            "scope_1",
            MockScope,
            args=["1.1.1.1"],
            experiment_args=["blah"],
        )
        lab.register_resource_if_not_exist(
            "scope_1", MockScope, args=["1.1.1.1"], experiment_args=["blah"]
        )
        # lab.update_resource("scope_1", "scope_1", "1.1.1.1", experiment_args=["blah"])
        # lab.remove_resource("scope_1")
        lab.list_resources()
        print(lab.get_resource_info("scope_1"))

        # setup experiment
        resources = ExperimentResources(db)
        resources.import_lab_resource(
            "scope_1",
            experiment_args=["blah1"],
        )
        resources.add_temp_resource("temp_scope", MockScope("2.2.2.2", "blah"))

        # revert resource to snapshot if needed
        lab.get_resource("scope_1", experiment_args=["blah1"])
        lab.save_snapshot("scope_1", "snapshot_name")
        snap = lab.get_snapshot("scope_1", "snapshot_name")
        scope = resources.get_resource("scope_1")
        scope.revert_to_snapshot(snap)  # if implemented

        # add resource in a specific snapshot
        # resources.import_lab_resource(
        #     "scope_1", snapshot_name="snapshot_name", experiment_args=["blah2"]
        # )

        # define experiment
        definition = ScriptExperiment(resources, an_experiment, "with_db")
        experiment_runner = definition.run(db)
        reader = experiment_runner.results_reader()
        print(reader.get_experiment_info())
        print(reader.get_experiment_info().script.print_all())

        # setup experiment
        resources = ExperimentResources(db)
        resources.import_lab_resource("scope_1", experiment_args=["blah2"])
        # define experiment
        definition = ScriptExperiment(resources, an_experiment, "with_db")
        experiment_runner = definition.run(db)
        reader = experiment_runner.results_reader()
        print(reader.get_experiment_info())
        print(reader.get_experiment_info().script.print_all())

        # setup experiment
        resources = ExperimentResources(db)
        resources.import_lab_resource("scope_1", experiment_args=["blah3"])
        # define experiment
        definition = ScriptExperiment(resources, an_experiment, "with_db")
        experiment_runner = definition.run(db)
        reader = experiment_runner.results_reader()
        print(reader.get_experiment_info())
        print(reader.get_experiment_info().script.print_all())

    finally:
        os.remove("db_and_topo.db")
        pass


def test_running_db_and_topology_with_kwargs():
    try:
        # setup lab environment one time
        db = SqlAlchemyDB("db_and_topo.db")
        lab = LabResources(db)
        lab.register_resource(
            "scope_1",
            MockScope,
            kwargs={"address": "1.1.1.1"},
            experiment_kwargs={"extra": "blah"},
        )

        resources = ExperimentResources(db)
        resources.import_lab_resource(
            "scope_1",
            experiment_kwargs={"extra": "blah1"},
        )

        # define experiment
        definition = ScriptExperiment(resources, an_experiment, "with_db")
        experiment_runner = definition.run(db)
        reader = experiment_runner.results_reader()
        print(reader.get_experiment_info())
        print(reader.get_experiment_info().script.print_all())

        # setup experiment
        resources = ExperimentResources(db)
        resources.import_lab_resource(
            "scope_1",
            experiment_kwargs={"extra": "blah2"},
        )
        # define experiment
        definition = ScriptExperiment(resources, an_experiment, "with_db")
        experiment_runner = definition.run(db)
        reader = experiment_runner.results_reader()
        print(reader.get_experiment_info())
        print(reader.get_experiment_info().script.print_all())
    finally:
        os.remove("db_and_topo.db")
        pass


def test_executor_decorator():
    resources = ExperimentResources()
    resources.add_temp_resource("scope_1", MockScope("1.1.1.1", ""))
    resources.add_temp_resource("scope_2", MockScope("1.1.1.1", ""))
    db = SqlalchemySqlitePandasConnector()

    @script_experiment("the best", resources, db)
    def experiment(experiment_runner: EntropyContext):
        scope = experiment_runner.get_resource("scope_1")
        a1 = do_something()
        scope.get_trig()
        experiment_runner.add_result(RawResultData("a_result", a1))
        a2 = do_something()
        if a2 > 4:
            a2 = do_something()
        experiment_runner.add_result(RawResultData("a2", a2))
        b1 = do_something2()
        experiment_runner.add_result(RawResultData("b_result", b1))