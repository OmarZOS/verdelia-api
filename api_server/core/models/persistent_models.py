"""
This file is destined to keep the sensitive models away from 
sqlacodegen's instruction of 





"""



from sqlalchemy import Table,BigInteger, PrimaryKeyConstraint,TIMESTAMP,DECIMAL,JSON,  DateTime, Enum, Float, ForeignKeyConstraint, Index, Integer, String, Text, text,Column, Date, DateTime, Float, Index, Integer, LargeBinary, String, Text,  select, func
from sqlalchemy.orm import column_property

from sqlalchemy.sql.sqltypes import NullType

from geoalchemy2 import Geometry
from sqlalchemy.orm import column_property
from sqlalchemy.sql import func

from sqlalchemy import Column, Date, DateTime, Float, ForeignKeyConstraint, Index, Integer, String, Text
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.sql.sqltypes import NullType

from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()
metadata = Base.metadata





class Location(Base):
    """
        The Location model represents a geospatial point associated with an address and several domain entities (persons, providers, orders, and images).
    It stores a geographic POINT using SRID 4326 for spatial operations and indexing.

Developers must be careful when using location_position directly.
This field is a raw spatial Geometry object; attempting to serialize or inspect it without conversion may raise exceptions depending on the database driver.
To avoid issues, always use position_wkt, which exposes the geometry in a safe, readable WKT (Well-Known Text) format.
    """
    __tablename__ = 'location'
    __table_args__ = (
        ForeignKeyConstraint(['location_address_id'], ['address.id_address'], name='fk_location_1'),
        Index('fk_location_1_idx', 'location_address_id'),
        Index('spatial', 'location_position')
    )

    id_location = Column(Integer, primary_key=True)
    location_position = Column(Geometry('POINT', srid=4326))
    position_wkt = column_property(
        func.ST_AsText(location_position)
    )
    location_name = Column(String(45))
    location_address_id = Column(Integer)
    location_postal_code = Column(Integer)
    
    location_address = relationship('Address', back_populates='location')
    location_image = relationship('LocationImage', back_populates='location')
    person = relationship('Person', back_populates='person_location')
    placed_order = relationship('PlacedOrder', back_populates='location')
    product_provider = relationship('ProductProvider', back_populates='product_provider_location')

class BusinessOperation(Base):
    """
    Business Operations View Model - Updated Version

    This model maps to the enhanced `business_operation` database view that 
    consolidates all business transactions with comprehensive tracking.

    The view now provides:
    • Complete financial transaction history across all operation types
    • Full document tracking (invoices, receipts, deposits)
    • Detailed payment status categorization
    • Operation type classification (products, services, mixed)
    • Timestamp tracking for all operations

    New Fields:
    • invoice_id - Direct reference to invoice table
    • receipt_id - Direct reference to receipt table  
    • document_type - Type of financial document created
    • operation_type - Classification of the business operation
    • operation_date - When the operation occurred

    Used for:
    • Financial reporting and analytics
    • Document reconciliation and audit trails
    • Business intelligence dashboards
    • Payment tracking across all transaction types
    • Performance monitoring by operation type

    Note: This is a read-only view model. Direct modifications are not supported.
    """
    __tablename__ = 'business_operation'
    
    # Supplier/Provider Information
    supplier_id = Column(Integer, primary_key=True)
    
    # Transaction References
    order_id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, primary_key=True)
    
    # Participant Information
    client_id = Column(Integer, primary_key=True)  # Renamed from 'client' to 'client_id'
    seller_id = Column(Integer, primary_key=True)
    
    # Financial Information
    total_amount = Column(Float)
    balance_due = Column(Float)
    
    # Document Tracking
    invoice_id = Column(Integer, primary_key=True)
    invoice_status = Column(String(50))
    receipt_id = Column(Integer, primary_key=True)
    
    # Payment Information
    total_paid = Column(DECIMAL(37, 4))
    total_deposited = Column(DECIMAL(37, 4))
    
    # Status and Classification
    payment_status = Column(String(27))
    document_type = Column(String(19))
    operation_type = Column(String(23))
    source_table = Column(String(13))
    
    # Temporal Information
    operation_date = Column(TIMESTAMP)    

class FinancialDocument(Base):
    __tablename__ = 'financial_documents_status'
    
    # Primary key columns - note: you have server_default='0' for document_id
    document_type = Column(String(12), primary_key=True)  # 'deposit', 'invoice', 'pending_cart'
    document_id = Column(Integer, primary_key=True, server_default=text("'0'"))  # Note the server_default
    
    # Other columns - note type differences (BigInteger vs Integer)
    document_number = Column(String(100))
    source_id = Column(Integer)
    source_type = Column(String(14))
    supplier_id = Column(BigInteger)  # Changed from Integer to BigInteger
    customer_id = Column(BigInteger)  # Changed from Integer to BigInteger
    customer_type = Column(String(7))
    customer_person_id = Column(BigInteger)  # Changed from Integer to BigInteger
    seller_id = Column(BigInteger)  # Changed from Integer to BigInteger
    
    # Decimal columns with server defaults
    document_amount = Column(DECIMAL(15, 4))
    issue_date = Column(Date)
    due_date = Column(Date)
    total_paid = Column(DECIMAL(37, 4), server_default=text("'0.0000'"))
    total_deposited = Column(DECIMAL(37, 4), server_default=text("'0.0000'"))
    additional_fees = Column(DECIMAL(37, 4), server_default=text("'0.0000'"))
    outstanding_balance = Column(DECIMAL(39, 4))
    
    # Status columns
    document_status = Column(String(50))
    payment_status = Column(String(19))  # Changed from 21 to 19
    
    # Days columns - changed from Integer to BigInteger
    days_issued = Column(BigInteger)
    days_overdue = Column(BigInteger)
    
    # Timestamp columns
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
    # Define composite primary key

    
    













