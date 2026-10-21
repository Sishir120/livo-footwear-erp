from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, Boolean, UniqueConstraint, Index, Date, BigInteger, CheckConstraint
from sqlalchemy.orm import relationship
from app.db.session import Base

class Client(Base):
    __tablename__ = "clients"
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_company_client_code"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    contact_person = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(String(255), nullable=True)
    pan_number = Column(String(15), nullable=True)
    credit_limit = Column(Numeric, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class SalesOrder(Base):
    __tablename__ = "sales_orders"
    __table_args__ = (
        UniqueConstraint("company_id", "order_number", name="uq_company_sales_order_number"),
        Index("ix_sales_orders_client", "company_id", "client_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    order_number = Column(String(50), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    order_date_ad = Column(String(10), nullable=False, index=True)
    order_date_bs = Column(String(10), nullable=False)
    dispatch_date_ad = Column(Date, nullable=True)
    dispatch_date_bs = Column(String(10), nullable=True)
    status = Column(String(50), default="DELIVERED")  # DRAFT, CONFIRMED, DISPATCHED, DELIVERED, CANCELLED
    total_amount = Column(Numeric, nullable=False, default=0.0)
    received_amount = Column(Numeric, nullable=False, default=0.0)
    receivable_amount = Column(Numeric, nullable=False, default=0.0)
    delivered = Column(Boolean, default=True)
    
    # Deferred Dispatch Metadata
    dispatched_at = Column(DateTime(timezone=True), nullable=True)
    dispatched_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    dispatch_notes = Column(String(255), nullable=True)
    carrier_name = Column(String(128), nullable=True)
    vehicle_number = Column(String(64), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    client = relationship("Client")
    dispatched_by = relationship("User", foreign_keys=[dispatched_by_id])
    items = relationship("SalesItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order", cascade="all, delete-orphan")

    @property
    def taxable_amount_paisa(self) -> int:
        if "taxable_amount_paisa" in self.__dict__:
            return self.__dict__["taxable_amount_paisa"]
        if self.items:
            return sum(it.total_price_paisa for it in self.items)
        tot = self.total_amount if self.total_amount is not None else 0
        return int(round(float(tot) * 100))

    @taxable_amount_paisa.setter
    def taxable_amount_paisa(self, value: int):
        self.__dict__["taxable_amount_paisa"] = int(value)

    @property
    def vat_rate(self) -> float:
        return 13.0

    @property
    def vat_amount_paisa(self) -> int:
        if "vat_amount_paisa" in self.__dict__:
            return self.__dict__["vat_amount_paisa"]
        return int(round(self.taxable_amount_paisa * 0.13))

    @vat_amount_paisa.setter
    def vat_amount_paisa(self, value: int):
        self.__dict__["vat_amount_paisa"] = int(value)

    @property
    def total_amount_paisa(self) -> int:
        if "total_amount_paisa" in self.__dict__:
            return self.__dict__["total_amount_paisa"]
        tot = self.total_amount if self.total_amount is not None else 0
        return int(round(float(tot) * 100))

    @total_amount_paisa.setter
    def total_amount_paisa(self, value: int):
        self.__dict__["total_amount_paisa"] = int(value)

class SalesItem(Base):
    __tablename__ = "sales_items"
    __table_args__ = (
        Index("ix_sales_items_order", "company_id", "sales_order_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Numeric, nullable=False)
    unit_price = Column(Numeric, nullable=False)
    total_price = Column(Numeric, nullable=False)

    order = relationship("SalesOrder", back_populates="items")
    product = relationship("Product")

    @property
    def unit_price_paisa(self) -> int:
        if "unit_price_paisa" in self.__dict__:
            return self.__dict__["unit_price_paisa"]
        val = self.unit_price if self.unit_price is not None else 0
        return int(round(float(val) * 100))

    @unit_price_paisa.setter
    def unit_price_paisa(self, value: int):
        self.__dict__["unit_price_paisa"] = int(value)

    @property
    def total_price_paisa(self) -> int:
        if "total_price_paisa" in self.__dict__:
            return self.__dict__["total_price_paisa"]
        val = self.total_price if self.total_price is not None else 0
        return int(round(float(val) * 100))

    @total_price_paisa.setter
    def total_price_paisa(self, value: int):
        self.__dict__["total_price_paisa"] = int(value)

from sqlalchemy import event

@event.listens_for(SalesItem, "init")
@event.listens_for(SalesItem, "load")
def _populate_sales_item_paisa(target, *args, **kwargs):
    u = target.unit_price if target.unit_price is not None else 0
    t = target.total_price if target.total_price is not None else 0
    target.__dict__["unit_price_paisa"] = int(round(float(u) * 100))
    target.__dict__["total_price_paisa"] = int(round(float(t) * 100))

@event.listens_for(SalesOrder, "init")
@event.listens_for(SalesOrder, "load")
def _populate_sales_order_paisa(target, *args, **kwargs):
    tot = target.total_amount if target.total_amount is not None else 0
    target.__dict__["total_amount_paisa"] = int(round(float(tot) * 100))
    target.__dict__["vat_rate"] = 13.0


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    amount = Column(Numeric, nullable=False)
    payment_date_ad = Column(String(10), nullable=False, index=True)
    payment_date_bs = Column(String(10), nullable=False)
    payment_method = Column(String(50), nullable=False, default="cash")  # cash, bank, online, cheque
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    order = relationship("SalesOrder", back_populates="payments")
    client = relationship("Client")

class SalesExpense(Base):
    __tablename__ = "sales_expenses"
    __table_args__ = (
        CheckConstraint("amount_paisa > 0", name="chk_sales_expense_amount_positive"),
        CheckConstraint(
            "category IN ('DELIVERY_FREIGHT', 'PACKING_MATERIALS', 'SALES_COMMISSION', 'LOADING_UNLOADING', 'PROMOTIONAL_SAMPLE', 'OTHER')",
            name="chk_sales_expense_category"
        ),
        CheckConstraint("payment_method IN ('CASH', 'BANK')", name="chk_sales_expense_payment_method"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    expense_date_ad = Column(Date, nullable=False)
    expense_date_bs = Column(String(10), nullable=False)
    particular = Column(String(255), nullable=False)
    category = Column(String(32), nullable=False)
    amount_paisa = Column(BigInteger, nullable=False)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=True, index=True)
    payment_method = Column(String(32), nullable=False, default="CASH")
    remarks = Column(String(255), nullable=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    sales_order = relationship("SalesOrder")
    actor = relationship("User", foreign_keys=[actor_id])


class FactoryExpense(Base):
    """
    General Factory Operating Expense ledger per client requirement REQ-15.
    Tracks rent, electricity, generator fuel, machine maintenance, office supplies, teas/refreshments, etc.
    """
    __tablename__ = "factory_expenses"
    __table_args__ = (
        CheckConstraint("amount_paisa > 0", name="chk_factory_expense_amount_positive"),
        CheckConstraint("payment_method IN ('CASH', 'BANK')", name="chk_factory_expense_payment_method"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    expense_date_ad = Column(Date, nullable=False)
    expense_date_bs = Column(String(10), nullable=False)
    particular = Column(String(255), nullable=False)
    category = Column(String(32), nullable=False)  # RENT, ELECTRICITY, GENERATOR_FUEL, MACHINE_MAINTENANCE, OFFICE_SUPPLIES, TEA_REFRESHMENT, FACTORY_LABOR, OTHER
    amount_paisa = Column(BigInteger, nullable=False)
    payment_method = Column(String(32), nullable=False, default="CASH")
    remarks = Column(String(255), nullable=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    actor = relationship("User", foreign_keys=[actor_id])

