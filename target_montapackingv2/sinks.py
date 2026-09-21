"""Montapackingv2 target sink class, which handles writing streams."""

import json
import re

from hotglue_etl_exceptions import InvalidPayloadError
from target_montapackingv2.client import MontapackingSink

class InboundForecastSink(MontapackingSink):

    endpoint = "inboundforecast/group"
    name = "BuyOrders"

    def preprocess_record(self, record: dict, context: dict) -> None:
        line_items = self.parse_json(record.get("line_items", []))
        delivery_date = self.convert_datetime(record.get("created_at"))
        transaction_date = self.convert_datetime(record.get("transaction_date"))

        lines = [
            {
                "DeliveryDate": delivery_date,
                "Sku": i.get("sku"),
                "Quantity": i.get("quantity"),
                "Batch": i.get("batch")
            }
            for i in line_items
        ]

        mapping = {
            "Reference": str(record.get("id")),
            "SupplierCode": record.get("customer_id"),
            "InboundForecasts": lines,
            "Created": transaction_date,  # seems like Montapacking API ignores this field
            "DeliveryDate": delivery_date,
        }

        return mapping
    
    def upsert_record(self, record: dict, context: dict):
        reference = record.get("Reference")
        attempt = 1
        while True:
            self.logger.debug(
                "BuyOrder reference=%s attempt=%s POST %s payload=%s",
                reference, attempt, self.endpoint, json.dumps(record, default=str),
            )
            try:
                buy_order_response = self.request_api(
                    "POST", endpoint=self.endpoint, request_data=record
                )
                self.logger.debug(
                    "BuyOrder reference=%s attempt=%s response status=%s body=%s",
                    reference, attempt, buy_order_response.status_code, buy_order_response.text,
                )
                break
            except InvalidPayloadError as error:
                self.logger.debug(
                    "BuyOrder reference=%s attempt=%s invalid-payload response=%s",
                    reference, attempt, error,
                )
                if self.config.get("export_remove_line_and_resend") is not True:
                    self.logger.warning(
                        "BuyOrder reference=%s attempt=%s not retrying: export_remove_line_and_resend is not true",
                        reference, attempt,
                    )
                    raise

                invalid_skus = re.findall(
                    r"SKU:\s*(\S+)\s+\[2;\s*No products found", str(error)
                )
                remaining_lines = [
                    line
                    for line in record["InboundForecasts"]
                    if str(line["Sku"]) not in invalid_skus
                ]
                if not remaining_lines:
                    self.logger.warning(
                        "BuyOrder reference=%s attempt=%s not retrying: removing invalid SKUs would leave no lines",
                        reference, attempt,
                    )
                    raise
                if remaining_lines == record["InboundForecasts"]:
                    self.logger.warning(
                        "BuyOrder reference=%s attempt=%s not retrying: no matching invalid-SKU lines",
                        reference, attempt,
                    )
                    raise

                self.logger.warning(
                    "BuyOrder reference=%s attempt=%s retrying as attempt=%s: removed_skus=%s lines=%s->%s",
                    reference, attempt, attempt + 1,
                    [line["Sku"] for line in record["InboundForecasts"] if str(line["Sku"]) in invalid_skus],
                    len(record["InboundForecasts"]), len(remaining_lines),
                )
                record["InboundForecasts"] = remaining_lines
                attempt += 1
            except Exception as error:
                self.logger.error(
                    "BuyOrder reference=%s attempt=%s failed; no invalid-SKU retry: %s",
                    reference, attempt, error,
                )
                raise
        buy_order_remoteId = buy_order_response.json()["UniqueId"]
        # input_id = record.get("id")
        self.logger.info(
            "BuyOrder reference=%s created successfully with UniqueId %s after %s attempt(s)",
            reference, buy_order_remoteId, attempt,
        )
        
        return buy_order_remoteId, True, {}


class UpdateInventory(MontapackingSink):

    name = "UpdateInventory"
    endpoint = "UpdateInventory"

    def preprocess_record(self, record: dict, context: dict) -> None:
        pass
    
    def upsert_record(self, record: dict, context: dict) -> None:
        pass
