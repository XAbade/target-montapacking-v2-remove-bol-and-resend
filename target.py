"""Montapackingv2 target class."""
from target_montapackingv2.sinks import (
    InboundForecastSink,
    UpdateInventory
)
from hotglue_singer_sdk.helpers.capabilities import AlertingLevel
from hotglue_singer_sdk.target_sdk.target import TargetHotglue

class TargetMontapacking(TargetHotglue):
    SINK_TYPES = [InboundForecastSink, UpdateInventory]
    MAX_PARALLELISM = 10
    name = "target-montapackingv2"
    alerting_level = AlertingLevel.WARNING


if __name__ == "__main__":
    TargetMontapacking.cli()

