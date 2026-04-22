"""
Pydantic models for WareFlow P1 API.

Defines request/response schemas consumed by FastAPI endpoints
and by Person 4's frontend.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class OrderRequest(BaseModel):
    """Incoming order placement request.

    Attributes:
        order_id: Unique order identifier (e.g. "ORD-001").
        customer_coords: [latitude, longitude] of the customer.
        items: List of item names in the order.
    """
    order_id: str = Field(..., description="Unique order identifier", examples=["ORD-001"])
    customer_coords: List[float] = Field(
        ...,
        min_length=2,
        max_length=2,
        description="[latitude, longitude] of the customer",
        examples=[[27.2, 79.0]],
    )
    items: List[str] = Field(
        ...,
        min_length=1,
        description="List of item names in the order",
        examples=[["laptop", "charger"]],
    )


class OrderResponse(BaseModel):
    """Response after successful order placement.

    This shape is what Person 4's order confirmation card reads.

    Attributes:
        warehouse: Assigned warehouse ID ("lucknow" or "delhi").
        eta: Estimated time of arrival as a string.
        queue_position: Position in the assigned warehouse's queue.
    """
    warehouse: str
    eta: str
    queue_position: int


class HealthResponse(BaseModel):
    """Health check response — Person 4 polls this on startup.

    Attributes:
        status: Overall health status.
        firebase_connected: Whether Firebase Admin SDK is initialised.
        model_loaded: Whether warehouse_selector.pkl is loaded.
        model_path: Path to the model file (for debugging).
    """
    status: str
    firebase_connected: bool
    model_loaded: bool
    model_path: Optional[str] = None


class ErrorResponse(BaseModel):
    """Generic error response.

    Attributes:
        error: Human-readable error message.
        detail: Optional technical detail.
    """
    error: str
    detail: Optional[str] = None
