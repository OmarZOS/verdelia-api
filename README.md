
## Document storage server
## Table of Contents

- Table of Contents
  - Description
  - Folder hierarchy
  - Deploying
    - Docker
    - Development
  - Progress

### Description


### Folder hierarchy

        ├── core
        |  # base component for the server
        ├── features
        |  # each set of features is implemented in a folder
        └── storage
            ├── storage_service
            | # an abstraction for storage engines
            └── wrappers
            | # the implementation to handle 3rd party storage.

### Deploying

#### Docker

You can use docker-compose to build and deploy the containers:

    sudo docker compose up -d

#### Development
Connect to the container 

    sudo docker exec -it verdelia-db mysql -u dev_user verdelia -p

Create a user that can access from anywhere:

    CREATE USER 'dev_user'@'%' IDENTIFIED BY 'dev_password';
    GRANT ALL PRIVILEGES ON *.* TO 'dev_user'@'%';
    FLUSH PRIVILEGES;
    exit;

To generate the `models.py` file, you can execute the following instruction:

    docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' verdelia-db

    sqlacodegen --outfile=api_server/core/models.py   mysql+pymysql://dev_user:dev_password@[$MYSQL_HOST]/verdelia

For the spatial data: 

    from geoalchemy2 import Geometry
    location_position = Column(Geometry('POINT'))  # ✅ Correct way:

    class Location(Base):
    __tablename__ = 'location'
    __table_args__ = (
        ForeignKeyConstraint(['location_address_id'], ['address.id_address'], name='fk_location_1'),
        Index('fk_location_1_idx', 'location_address_id'),
        Index('spatial', 'location_position')
    )

    id_location = Column(Integer, primary_key=True)
    location_position = Column(Geometry('POINT', srid=4326), nullable=False)
    position_wkt = column_property(func.ST_AsText(location_position)) 
    location_name = Column(String(45))
    location_address_id = Column(Integer)
    # Computed column to always get the WKT representation
    location_address = relationship('Address', back_populates='location')
    person = relationship('Person', back_populates='person_location')
    product_provider = relationship('ProductProvider', back_populates='product_provider_location')

For the business logic:

    Placed Order → ordered_items → Product → Provider
        ↓
        → Invoice → Payment


    Cart → (ordered_items OR ordered_services) → Provider
        ↓
        → Placed Order (optional?) → Invoice → Payment

    -- Two competing payment tables
    payment → invoice (full payment)
    deposit → cart OR invoice (partial payments)

    -- Receipt can reference payment OR cart directly
    receipt → payment_id
    receipt → cart_ref

    ordered_item → order_ref (placed_order)  -- Path A
    ordered_item → cart_ref                  -- Path B
    ordered_service → cart_ref               -- Only path

    1. ordered_item → product → provider
    2. cart → product_provider (direct)
    3. ordered_service → provided_service → provider



    @startuml

    [*] --> paid : creates a cart and its payment 

    [*] --> unpaid : creates a cart, might create invoice or a receipt 

    unpaid -> paid : creates a payment or a full deposit




    unpaid --> deposited : creates a deposit and a receipt
    deposited:  might be associated with a receipt

    deposited --> paid : creates a deposit

    paid --> [*]
    paid : by a single payment
    paid : by multiple deposits


    @enduml



### Progress
    
- Serving feature. ![x](https://us-central1-progress-markdown.cloudfunctions.net/progress/90)
  - Product.
    - Ordering Products.
    - Polling to monitor `quantity` changes.
  - Category.
  - Supplier.
  - App user.
- Auth server. ![x](https://us-central1-progress-markdown.cloudfunctions.net/progress/60)
  - App user creation.
  - Logging in feature.
  - Changing password.
  - ssl certificate (locally generated).
- [x] 3rd Party storage solutions. ![](https://us-central1-progress-markdown.cloudfunctions.net/progress/80)
  - [x] SQL based storage.
  - [x] SQLITE based authentication.
- [x] File server. ![](https://us-central1-progress-markdown.cloudfunctions.net/progress/95)
- [x] Containerisation. ![](https://us-central1-progress-markdown.cloudfunctions.net/progress/90)
  - [x] Automation of deployment. (docker-compose)
  - [x] Smaller footprint.



<!-- >## NOTES: -->
>  
> 