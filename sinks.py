"""Montapackingv2 target sink class, which handles writing streams."""

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
        buy_order_response = self.request_api(
            "POST", endpoint=self.endpoint, request_data=record
        )
        buy_order_remoteId = buy_order_response.json()["UniqueId"]
        # input_id = record.get("id")
        self.logger.info(f"BuyOrder created succesfully with UniqueId {buy_order_remoteId}")
        
        return buy_order_remoteId, True, {}


class UpdateInventory(MontapackingSink):

    name = "UpdateInventory"
    endpoint = "UpdateInventory"

    def preprocess_record(self, record: dict, context: dict) -> None:
        pass
    
    def upsert_record(self, record: dict, context: dict) -> None:
        pass
