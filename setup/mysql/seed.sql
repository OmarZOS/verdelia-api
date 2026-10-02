-- First, let's fix the foreign key issues by ensuring proper data flow

-- Insert app_user_type first (this is referenced by app_user)




-- Insert product_category (referenced by product)
INSERT INTO `verdelia`.`product_category` (`product_category_icon`) VALUES
('Baked Goods'),
('Spreads'),
('Cereals'),
('Pasta'),
('Snacks'),
('Beverages'),
('Desserts'),
('Frozen Foods'),
('Flours & Baking Ingredients'),
('Canned & Packaged Goods ');

-- Insert product_provider_type (referenced by product_provider)
INSERT INTO `verdelia`.`product_provider_type` (`product_provider_type_icon_url`) VALUES
('Restaurant'),
('Bakery'),
('Factory'),
('Supermarket'),
("Grocery Store"),
("Distributor");

-- Insert recipe_category (just for completeness)
INSERT INTO `verdelia`.`recipe_category` (`recipe_category_icon_url`) VALUES
("Appetizers & Snacks"),
("Soups & Stews"),
("Salads"),
("Main Courses"),
("Side Dishes"),
("Pasta & Noodles"),
("Casseroles"),
("Breakfast & Brunch"),
("Breads & Baking"),
("Desserts"),
("Drinks & Beverages"),
("Sauces & Condiments"),
("International Cuisine"),
("Healthy & Special Diets"),
("Holiday & Seasonal"),
("Kids & Family"),
("Slow Cooker & Instant Pot"),
("Quick & Easy"),
("One-Pan Recipes"),
("Grilling & BBQ");

-- Insert provider_details first (before product_provider)
INSERT INTO `verdelia`.`provider_details` (`provider_name`, `provider_contact_info`) VALUES
('Magasin habibou sans gluten', 'Facebook: https://www.facebook.com/profile.php?id=100063549909208'),
('Uno', 'Facebook: https://www.facebook.com/UNO.Hypermarche/, Instagram: https://www.instagram.com/uno_hypermarche/'),
('Superette université', 'N/A'),
('Corridors Shopping', 'N/A'),
('Caramel sans gluten', 'N/A');

select * from provider_details;


-- Insert product_provider with valid type IDs (1-6)
INSERT INTO `verdelia`.`product_provider` (`product_provider_details_id`, `product_provider_type_id`) VALUES
(1, 2),  -- Provider 1: Magasin habibou (Bakery)
(2, 4),  -- Provider 2: Uno (Supermarket)
(3, 4),  -- Provider 3: Superette université (Supermarket)
(4, 1),  -- Provider 4: Corridors Shopping (Restaurant)
(5, 4),  -- Provider 5: Caramel sans gluten (Supermarket)
(1, 2),  -- Provider 6: Another entry for Magasin habibou
(2, 4);  -- Provider 7: Another entry for Uno

-- Insert person_details first (before person)
INSERT INTO `verdelia`.`person_details` 
    (person_first_name, person_last_name, person_birth_date, person_gender, person_country_code) 
VALUES 
    ('Some', 'One', '2003-01-01', 'Male', '213');

-- Insert person with valid blood_type_id (1-8)
INSERT INTO `verdelia`.`person` 
    (person_details_id, person_blood_type) 
VALUES 
    (1, "B+"); 

-- Insert app_user with valid app_user_type_id (1-4) and person_id (1)
INSERT INTO `verdelia`.`app_user` 
    (app_user_name, app_user_password, app_user_person_id, app_user_type) 
VALUES 
    ('SomeOne', 'password', 1, "ADMIN"),
    ('ProviderAdmin', 'password', 1, "provider"),  -- Supplier user
    ('SellerUser', 'password', 1, "customer");     -- Seller user

-- Insert products with valid product_provider_id (1-7) and product_category_id (1-10)
-- Note: product_owner should reference valid app_user.id_app_user
INSERT INTO `verdelia`.`product` 
(`product_owner`,`product_name`, `product_brand`,`product_description`, `product_provider_id`, `product_category_id`, `product_barcode`, `product_price`, `product_quantity`,`last_updated`,`created`) VALUES
-- Products for provider 2
(2,'Grano''Sac Raisin Cacahuetes', 'Grano''Sac','Delicious gluten-free baked goods made with raisins and peanuts.', 2, 1, '1234567890123', 5.99, 100, CURDATE(), CURDATE()),
(2,'Butter Biscuits LEGER', 'LEGER','Light and crispy gluten-free butter biscuits.', 2, 1, '1234567890124', 4.49, 150, CURDATE(), CURDATE()),

-- Products for provider 3
(2,'Cookies', 'Home Bakery','Indulgent gluten-free cookies baked to perfection.', 3, 1, '1234567890125', 3.99, 200, CURDATE(), CURDATE()),
(2,'Gullon Cookies', 'Gullon','Classic gluten-free cookies from Gullon.', 3, 1, '1234567890126', 6.29, 120, CURDATE(), CURDATE()),

-- Products for provider 4
(2,'Date Butter', 'NutriLife','A rich and creamy date butter.', 4, 2, '1234567890127', 7.99, 80, CURDATE(), CURDATE()),

-- Products for provider 5
(2,'CARAIBE Crème à Tartiner', 'CARAIBE','Decadent chocolate spread from CARAIBE.', 5, 2, '1234567890128', 8.49, 100, CURDATE(), CURDATE()),

-- Products for provider 6
(2,'JUMPY Beurre De Cacahuète', 'JUMPY','Smooth and creamy peanut butter spread.', 6, 2, '1234567890129', 5.79, 90, CURDATE(), CURDATE()),

-- Products for provider 7
(2,'Semoule de pain', 'BioCereal','Organic gluten-free semolina.', 7, 3, '1234567890130', 3.99, 120, CURDATE(), CURDATE());


-- -----------------------------------------------------
-- Dummy Data for product
-- -----------------------------------------------------
INSERT INTO `product` (
    `product_owner`,
    `product_name`,
    `product_brand`,
    `product_description`,
    `product_provider_id`,
    `product_category_id`,
    `product_barcode`,
    `product_price`,
    `product_quantity`,
    `product_quantifier`,
    `product_origin_id`,
    `last_updated`,
    `created`
) VALUES
-- =====================================================
-- PROVIDER 1 - General Medical Supplies
-- =====================================================
(1, 'Surgical Face Mask (50pcs)', 'MediSafe', 'Disposable 3-ply surgical masks with high filtration efficiency', 1, 8, '1234567890001', 12.99, 500, 'box', NULL, NOW(), NOW()),
(1, 'Latex Examination Gloves (100pcs)', 'SafeHands', 'Powder-free latex examination gloves, size M', 1, 8, '1234567890002', 15.50, 300, 'box', NULL, NOW(), NOW()),
(1, 'Digital Thermometer', 'TempSure', 'Fast reading digital thermometer for accurate temperature measurement', 1, 9, '1234567890003', 24.99, 80, 'piece', NULL, NOW(), NOW()),
(1, 'Blood Pressure Monitor', 'CardioChek', 'Digital blood pressure monitor with large display', 1, 9, '1234567890004', 49.95, 45, 'piece', NULL, NOW(), NOW()),
(1, 'First Aid Kit', 'MediSafe', 'Comprehensive first aid kit for home and travel', 1, 8, '1234567890005', 29.99, 60, 'kit', NULL, NOW(), NOW()),
(1, 'Hand Sanitizer 500ml', 'CleanWell', 'Alcohol-based hand sanitizer with moisturizer', 1, 8, '1234567890006', 6.99, 200, 'bottle', NULL, NOW(), NOW()),
(1, 'Disposable Syringes (10pcs)', 'MediSafe', 'Sterile disposable syringes, 5ml', 1, 8, '1234567890007', 8.50, 150, 'pack', NULL, NOW(), NOW()),
(1, 'Wound Dressing Pack', 'HealFast', 'Sterile wound dressing with bandages and antiseptic wipes', 1, 8, '1234567890008', 14.99, 100, 'pack', NULL, NOW(), NOW()),

-- =====================================================
-- PROVIDER 2 - Bakery & Pastry Products
-- =====================================================
(2, 'Grano''Sac Raisin Cacahuetes', 'Grano''Sac', 'Delicious gluten-free baked goods made with raisins and peanuts', 2, 1, '1234567890009', 5.99, 100, 'pack', NULL, NOW(), NOW()),
(2, 'Butter Biscuits LEGER', 'LEGER', 'Light and crispy gluten-free butter biscuits', 2, 1, '1234567890010', 4.49, 150, 'pack', NULL, NOW(), NOW()),
(2, 'Chocolate Chip Cookies', 'LEGER', 'Soft-baked gluten-free chocolate chip cookies', 2, 1, '1234567890011', 4.99, 120, 'pack', NULL, NOW(), NOW()),
(2, 'Almond Biscotti', 'Grano''Sac', 'Crunchy Italian-style biscotti with almonds', 2, 1, '1234567890012', 5.49, 90, 'pack', NULL, NOW(), NOW()),
(2, 'Gluten-Free Bread Loaf', 'LEGER', 'Freshly baked gluten-free bread loaf', 2, 1, '1234567890013', 6.99, 80, 'loaf', NULL, NOW(), NOW()),
(2, 'Oatmeal Cookies', 'Grano''Sac', 'Wholesome oatmeal cookies with raisins', 2, 1, '1234567890014', 3.99, 130, 'pack', NULL, NOW(), NOW()),
(2, 'Cinnamon Rolls (6pcs)', 'LEGER', 'Gluten-free cinnamon rolls with cream cheese frosting', 2, 1, '1234567890015', 7.49, 60, 'pack', NULL, NOW(), NOW()),

-- =====================================================
-- PROVIDER 3 - Gluten-Free Snacks
-- =====================================================
(2, 'Cookies - Assorted', 'Home Bakery', 'Indulgent gluten-free cookies baked to perfection', 3, 1, '1234567890016', 3.99, 200, 'pack', NULL, NOW(), NOW()),
(2, 'Gullon Cookies - Chocolate Chip', 'Gullon', 'Classic gluten-free chocolate chip cookies', 3, 1, '1234567890017', 6.29, 120, 'pack', NULL, NOW(), NOW()),
(2, 'Gullon Cookies - Digestive', 'Gullon', 'Gluten-free digestive biscuits', 3, 1, '1234567890018', 5.79, 110, 'pack', NULL, NOW(), NOW()),
(2, 'Rice Cakes (12pcs)', 'Home Bakery', 'Light and crispy gluten-free rice cakes', 3, 1, '1234567890019', 3.49, 150, 'pack', NULL, NOW(), NOW()),
(2, 'Granola Bars - 6pcs', 'Home Bakery', 'Healthy gluten-free granola bars with nuts and honey', 3, 1, '1234567890020', 4.29, 140, 'pack', NULL, NOW(), NOW()),
(2, 'Crispy Crackers', 'Gullon', 'Gluten-free savory crackers', 3, 1, '1234567890021', 4.99, 130, 'pack', NULL, NOW(), NOW()),
(2, 'Fruit Snacks (12pcs)', 'Home Bakery', 'Gluten-free fruit snacks made with real fruit juice', 3, 1, '1234567890022', 3.79, 160, 'pack', NULL, NOW(), NOW()),

-- =====================================================
-- PROVIDER 4 - Health & Wellness Products
-- =====================================================
(2, 'Date Butter - 250g', 'NutriLife', 'Rich and creamy date butter made from premium dates', 4, 2, '1234567890023', 7.99, 80, 'jar', NULL, NOW(), NOW()),
(2, 'Almond Butter - 300g', 'NutriLife', '100% natural roasted almond butter', 4, 2, '1234567890024', 8.99, 70, 'jar', NULL, NOW(), NOW()),
(2, 'Pure Honey - 500g', 'NutriLife', 'Raw, unprocessed honey from organic farms', 4, 2, '1234567890025', 9.99, 90, 'bottle', NULL, NOW(), NOW()),
(2, 'Chia Seeds - 400g', 'NutriLife', 'Organic chia seeds rich in omega-3', 4, 2, '1234567890026', 6.49, 100, 'pack', NULL, NOW(), NOW()),
(2, 'Quinoa - 500g', 'NutriLife', 'Organic quinoa, high in protein', 4, 2, '1234567890027', 7.49, 85, 'pack', NULL, NOW(), NOW()),
(2, 'Protein Bar - 12pcs', 'NutriLife', 'High-protein bars for post-workout recovery', 4, 2, '1234567890028', 19.99, 50, 'box', NULL, NOW(), NOW()),
(2, 'Green Superfood Powder', 'NutriLife', 'Organic green superfood blend with spirulina and wheatgrass', 4, 2, '1234567890029', 24.99, 40, 'can', NULL, NOW(), NOW()),

-- =====================================================
-- PROVIDER 5 - Spreads & Condiments
-- =====================================================
(2, 'CARAIBE Crème à Tartiner - 300g', 'CARAIBE', 'Decadent chocolate spread with hazelnuts', 5, 2, '1234567890030', 8.49, 100, 'jar', NULL, NOW(), NOW()),
(2, 'CARAIBE Caramel Spread', 'CARAIBE', 'Smooth caramel spread with sea salt', 5, 2, '1234567890031', 7.99, 90, 'jar', NULL, NOW(), NOW()),
(2, 'CARAIBE Coconut Spread', 'CARAIBE', 'Creamy coconut spread with lime zest', 5, 2, '1234567890032', 7.49, 85, 'jar', NULL, NOW(), NOW()),
(2, 'Organic Strawberry Jam - 250g', 'CARAIBE', 'Organic strawberry jam with no added sugar', 5, 2, '1234567890033', 5.99, 110, 'jar', NULL, NOW(), NOW()),
(2, 'Blueberry Preserve - 250g', 'CARAIBE', 'Wild blueberry preserve with natural sweetness', 5, 2, '1234567890034', 6.49, 100, 'jar', NULL, NOW(), NOW()),
(2, 'Maple Syrup - 250ml', 'CARAIBE', 'Pure organic maple syrup from Canada', 5, 2, '1234567890035', 11.99, 60, 'bottle', NULL, NOW(), NOW()),

-- =====================================================
-- PROVIDER 6 - Nut Butters & Spreads
-- =====================================================
(2, 'JUMPY Beurre De Cacahuète - 400g', 'JUMPY', 'Smooth and creamy peanut butter spread', 6, 2, '1234567890036', 5.79, 90, 'jar', NULL, NOW(), NOW()),
(2, 'JUMPY Crunchy Peanut Butter', 'JUMPY', 'Crunchy peanut butter with peanut pieces', 6, 2, '1234567890037', 5.99, 85, 'jar', NULL, NOW(), NOW()),
(2, 'JUMPY Almond & Cashew Butter', 'JUMPY', 'Blend of roasted almonds and cashews', 6, 2, '1234567890038', 8.99, 70, 'jar', NULL, NOW(), NOW()),
(2, 'JUMPY Hazelnut Spread', 'JUMPY', 'Rich hazelnut spread with cocoa', 6, 2, '1234567890039', 6.99, 80, 'jar', NULL, NOW(), NOW()),
(2, 'JUMPY Sunflower Seed Butter', 'JUMPY', 'Nut-free sunflower seed butter', 6, 2, '1234567890040', 7.49, 75, 'jar', NULL, NOW(), NOW()),
(2, 'JUMPY Pumpkin Seed Butter', 'JUMPY', 'Roasted pumpkin seed butter', 6, 2, '1234567890041', 8.49, 65, 'jar', NULL, NOW(), NOW()),

-- =====================================================
-- PROVIDER 7 - Grains & Cereals
-- =====================================================
(2, 'Semoule de pain - Bio', 'BioCereal', 'Organic gluten-free bread semolina', 7, 3, '1234567890042', 3.99, 120, 'pack', NULL, NOW(), NOW()),
(2, 'Gluten-Free Oatmeal - 500g', 'BioCereal', 'Organic gluten-free rolled oats', 7, 3, '1234567890043', 4.99, 100, 'pack', NULL, NOW(), NOW()),
(2, 'Rice Pasta - 400g', 'BioCereal', 'Organic gluten-free rice pasta', 7, 3, '1234567890044', 5.49, 95, 'pack', NULL, NOW(), NOW()),
(2, 'Corn Flour - 1kg', 'BioCereal', 'Fine organic corn flour for baking', 7, 3, '1234567890045', 4.29, 110, 'pack', NULL, NOW(), NOW()),
(2, 'Buckwheat Flour - 500g', 'BioCereal', 'Organic buckwheat flour, gluten-free', 7, 3, '1234567890046', 5.99, 90, 'pack', NULL, NOW(), NOW()),
(2, 'Millet Flakes - 300g', 'BioCereal', 'Organic millet flakes for breakfast cereals', 7, 3, '1234567890047', 4.49, 100, 'pack', NULL, NOW(), NOW()),
(2, 'Quinoa Flour - 500g', 'BioCereal', 'Organic quinoa flour rich in protein', 7, 3, '1234567890048', 6.49, 85, 'pack', NULL, NOW(), NOW()),
(2, 'Gluten-Free Muesli - 400g', 'BioCereal', 'Organic muesli with dried fruits and nuts', 7, 3, '1234567890049', 5.79, 95, 'pack', NULL, NOW(), NOW());


-- Insert provided_service_category first
INSERT INTO `verdelia`.`provided_service_category` (
  `provided_service_category_name`,
  `provided_service_category_icon_url`,
  `provided_service_category_avg_duration`,
  `provided_service_category_description`
) VALUES
('Blood Testing', 'https://example.com/icons/blood-test.svg', 30.00, 'Complete blood count, cholesterol, glucose, and other blood tests'),
('Diagnostic Imaging', 'https://example.com/icons/xray.svg', 45.00, 'X-rays, MRIs, CT scans, and ultrasound services'),
('Vaccination', 'https://example.com/icons/vaccine.svg', 15.00, 'Routine immunizations and travel vaccinations'),
('Health Check-up', 'https://example.com/icons/stethoscope.svg', 60.00, 'Comprehensive annual physical examinations'),
('Dental Care', 'https://example.com/icons/dental.svg', 40.00, 'Teeth cleaning, fillings, and basic dental procedures'),
('Pathology Tests', 'https://example.com/icons/microscope.svg', 120.00, 'Tissue biopsy analysis and histopathology'),
('Urine Analysis', 'https://example.com/icons/urine-test.svg', 20.00, 'Complete urinalysis and culture tests'),
('Allergy Testing', 'https://example.com/icons/allergy.svg', 90.00, 'Skin prick tests and allergen screening'),
('Genetic Testing', 'https://example.com/icons/dna.svg', 180.00, 'DNA analysis and genetic screening services'),
('Physiotherapy', 'https://example.com/icons/physical-therapy.svg', 50.00, 'Rehabilitation and physical therapy sessions'),
('Nutrition Counseling', 'https://example.com/icons/nutrition.svg', 45.00, 'Diet planning and nutritional guidance'),
('Mental Health Counseling', 'https://example.com/icons/mental-health.svg', 60.00, 'Therapy and psychological counseling sessions'),
('Acupuncture', 'https://example.com/icons/acupuncture.svg', 40.00, 'Traditional acupuncture therapy sessions'),
('Prenatal Care', 'https://example.com/icons/pregnancy.svg', 30.00, 'Pregnancy monitoring and prenatal check-ups'),
('Pediatric Care', 'https://example.com/icons/baby-care.svg', 25.00, 'Child healthcare and development monitoring'),
('Geriatric Care', 'https://example.com/icons/elderly-care.svg', 40.00, 'Elderly health monitoring and management'),
('Sports Medicine', 'https://example.com/icons/sports-medicine.svg', 50.00, 'Injury assessment and sports-related healthcare'),
('First Aid Training', 'https://example.com/icons/first-aid.svg', 240.00, 'CPR and emergency first aid certification'),
('Minor Surgery', 'https://example.com/icons/surgery.svg', 75.00, 'Outpatient minor surgical procedures'),
('Wound Care', 'https://example.com/icons/wound-care.svg', 25.00, 'Dressing changes and wound management'),
('IV Therapy', 'https://example.com/icons/iv-therapy.svg', 35.00, 'Intravenous hydration and vitamin therapy');

-- Insert provided_services with valid category_id (1-21) and product_provider_id (2-7)
-- Note: provided_service_product_provider_id should reference existing product_provider.id_product_provider
INSERT INTO `verdelia`.`provided_service` (
  `provided_service_name`,
  `provided_service_description`,
  `provided_service_category_id`,
  `provided_service_product_provider_id`,
  `provided_service_base_price`,
  `provided_service_final_price`,
  `provided_service_actual_duration`,
  `provided_service_is_active`,
  `provided_service_pricing_config`
) VALUES
-- Services for provider 2 (Blood Testing)
('Complete Blood Count (CBC)', 'Measures different components of blood', 1, 2, 25.0000, 20.0000, 25.00, 1, '{"discount_percent": 20}'),
('Lipid Profile Test', 'Measures cholesterol and triglyceride levels', 1, 2, 35.0000, 28.0000, 30.00, 1, '{"discount_percent": 20}'),
('Blood Glucose Test', 'Measures sugar levels for diabetes screening', 1, 2, 15.0000, 12.0000, 15.00, 1, '{"discount_percent": 20}'),

-- Services for provider 3 (Diagnostic Imaging)
('Chest X-Ray', 'Standard chest radiograph assessment', 2, 3, 80.0000, 65.0000, 20.00, 1, '{"insurance_coverage": 80}'),
('Abdominal Ultrasound', 'Imaging of abdominal organs', 2, 3, 120.0000, 95.0000, 45.00, 1, '{"insurance_coverage": 75}'),
('MRI Scan - Brain', 'Magnetic resonance imaging of the brain', 2, 3, 450.0000, 360.0000, 60.00, 1, '{"insurance_coverage": 70}'),

-- Services for provider 4 (Vaccination)
('Flu Vaccine', 'Annual influenza vaccination', 3, 4, 40.0000, 25.0000, 10.00, 1, '{"seasonal": true}'),
('COVID-19 Booster', 'Latest COVID-19 vaccine booster shot', 3, 4, 0.0000, 0.0000, 15.00, 1, '{"government_funded": true}'),
('Travel Vaccination Package', 'Vaccinations for international travel', 3, 4, 150.0000, 120.0000, 45.00, 1, '{"consultation_included": true}'),

-- Services for provider 5 (Health Check-up)
('Executive Health Screening', 'Comprehensive full-body check-up', 4, 5, 500.0000, 400.0000, 180.00, 1, '{"includes": ["blood_tests", "ecg"]}'),
('Basic Annual Check-up', 'Routine annual physical examination', 4, 5, 100.0000, 80.0000, 60.00, 1, '{"age_group": "adult"}'),
('Senior Citizen Health Package', 'Specialized check-up for elderly', 4, 5, 250.0000, 200.0000, 90.00, 1, '{"specialist_consultation": true}'),

-- Services for provider 6 (Dental Care)
('Teeth Cleaning & Polishing', 'Professional dental cleaning and scaling', 5, 6, 80.0000, 65.0000, 40.00, 1, '{"recommended_frequency": "6 months"}'),
('Dental Filling', 'Tooth cavity filling (per tooth)', 5, 6, 120.0000, 100.0000, 45.00, 1, '{"material_options": ["composite"]}'),
('Dental X-Ray', 'Intraoral dental imaging', 5, 6, 50.0000, 40.0000, 15.00, 1, '{"digital_imaging": true}'),

-- Services for provider 7 (Pathology Tests)
('Biopsy Analysis', 'Microscopic examination of tissue sample', 6, 7, 200.0000, 160.0000, 120.00, 1, '{"sample_type": "tissue"}'),
('Pap Smear Test', 'Cervical cancer screening test', 6, 7, 60.0000, 45.0000, 30.00, 1, '{"recommended_age": "21-65"}');

-- Insert service_staff_requirement with valid service_id (1-17)
INSERT INTO `verdelia`.`service_staff_requirement` (
  `service_staff_requirement_service_id`,
  `service_staff_requirement_min_count`,
  `service_staff_requirement_max_count`,
  `service_staff_requirement_hourly_rate`,
  `service_staff_requirement_allocated_hours`,
  `service_staff_requirement_notes`
) VALUES
-- Service 1 requirements
(1, 1, 2, 35.0000, 0.75, 'Certified phlebotomist'),
(1, 1, 1, 20.0000, 0.50, 'Prepare samples'),

-- Service 2 requirements
(2, 1, 1, 35.0000, 1.00, 'Fasting blood specialist'),
(2, 1, 1, 30.0000, 0.25, 'Patient preparation'),

-- Service 3 requirements
(3, 1, 1, 25.0000, 0.50, 'Glucose testing specialist'),
(3, 1, 1, 18.0000, 0.25, 'Patient check-in'),

-- Service 4 requirements
(4, 1, 2, 32.0000, 1.00, 'Liver function specialist'),
(4, 1, 1, 80.0000, 0.25, 'Results interpretation'),

-- Service 5 requirements
(5, 1, 1, 38.0000, 1.00, 'Thyroid testing specialist'),
(5, 1, 1, 100.0000, 0.50, 'Consultation and prescription'),

-- Service 6 requirements
(6, 1, 1, 40.0000, 0.75, 'Certified X-ray technician'),
(6, 1, 1, 120.0000, 0.25, 'Image interpretation'),

-- Service 7 requirements
(7, 1, 1, 45.0000, 1.25, 'Registered sonographer'),
(7, 1, 1, 120.0000, 0.50, 'Results interpretation'),

-- Service 8 requirements
(8, 1, 2, 55.0000, 2.00, 'Certified MRI specialist'),
(8, 1, 1, 150.0000, 1.00, 'Neuroradiology specialist'),

-- Service 9 requirements
(9, 1, 2, 50.0000, 1.00, 'CT scan specialist'),
(9, 1, 1, 45.0000, 0.25, 'Safety protocol'),

-- Service 10 requirements
(10, 1, 2, 32.0000, 0.50, 'Vaccination administration'),
(10, 1, 1, 45.0000, 0.25, 'Vaccine preparation'),

-- Service 11 requirements
(11, 1, 3, 35.0000, 0.50, 'COVID-19 specialist'),
(11, 1, 2, 22.0000, 0.50, 'Appointment scheduling'),

-- Service 12 requirements
(12, 1, 1, 60.0000, 1.50, 'International expert'),
(12, 1, 1, 55.0000, 0.75, 'Travel health assessment'),

-- Service 13 requirements
(13, 1, 1, 35.0000, 0.50, 'Adolescent vaccinations'),
(13, 1, 1, 95.0000, 0.25, 'HPV vaccine prescription'),

-- Service 14 requirements
(14, 1, 1, 150.0000, 3.00, 'Executive health specialist'),
(14, 1, 1, 180.0000, 0.50, 'Heart health consultation'),
(14,  2, 3, 32.0000, 4.00, 'Assist with tests'),

-- Service 15 requirements
(15, 1, 1, 120.0000, 1.50, 'Annual physical'),
(15, 1, 1, 25.0000, 1.00, 'Vital signs'),

-- Service 16 requirements
(16, 1, 1, 40.0000, 1.00, 'Teeth cleaning'),
(16, 1, 1, 80.0000, 0.50, 'Dental examination'),

-- Service 17 requirements
(17, 1, 1, 100.0000, 2.00, 'Biopsy analysis'),
(17, 1, 2, 35.0000, 1.50, 'Sample processing');

-- Insert service_resource_requirement with valid service_id (1-17) and product_ref (1-7)
INSERT INTO `verdelia`.`service_resource_requirement` (
  `service_resource_requirement_service_id`,
  `service_resource_requirement_name`,
  `service_resource_requirement_type`,
  `service_resource_requirement_quantity`,
  `service_resource_requirement_cost_per_unit`,
  `service_resource_requirement_is_consumable`,
  `service_resource_requirement_notes`,
  `service_resource_requirement_product_ref`
) VALUES
-- Service 1 resources
(1, 'Blood Collection Tube', 'Medical Supply', 3, 1.5000, 1, 'Vacutainer tubes', 1),
(1, 'Sterile Needle', 'Medical Supply', 1, 0.7500, 1, '21G safety needle', 1),
(1, 'Alcohol Swab', 'Medical Supply', 2, 0.2500, 1, 'Sterile preparation', NULL),

-- Service 2 resources
(2, 'Fasting Blood Test Kit', 'Test Kit', 1, 8.0000, 1, 'Lipid profile kit', 2),
(2, 'Centrifuge Tube', 'Lab Equipment', 1, 2.0000, 1, 'Sample separation', NULL),

-- Service 3 resources
(3, 'Glucose Test Strip', 'Medical Supply', 1, 3.5000, 1, 'Single-use strip', 1),
(3, 'Lancet Device', 'Medical Device', 1, 5.0000, 0, 'Finger prick device', 3),
(3, 'Control Solution', 'Chemical', 1, 4.0000, 1, 'Quality control', NULL),

-- Service 4 resources
(4, 'X-Ray Film', 'Imaging Supply', 1, 8.0000, 1, 'Digital imaging plate', 4),
(4, 'Lead Apron', 'Safety Equipment', 2, 45.0000, 0, 'Radiation protection', 3),
(4, 'Contrast Media', 'Chemical', 1, 35.0000, 1, 'Enhanced images', NULL),

-- Service 5 resources
(5, 'Ultrasound Gel', 'Medical Supply', 1, 5.0000, 1, 'Conduction gel', 1),
(5, 'Probe Cover', 'Medical Supply', 1, 1.2500, 1, 'Single-use protection', 1),
(5, 'Thermal Paper', 'Office Supply', 1, 2.0000, 1, 'Image printing', NULL),

-- Service 6 resources
(6, 'MRI Contrast Agent', 'Pharmaceutical', 1, 85.0000, 1, 'Gadolinium contrast', 2),
(6, 'Ear Protection', 'Safety Equipment', 1, 3.0000, 1, 'Noise reduction', NULL),

-- Service 7 resources
(7, 'Influenza Vaccine', 'Pharmaceutical', 1, 18.0000, 1, 'Quadrivalent flu vaccine', 2),
(7, 'Syringe with Needle', 'Medical Supply', 1, 0.8500, 1, '1ml safety syringe', 1),
(7, 'Sharps Container', 'Safety Equipment', 1, 3.5000, 0, 'Biohazard disposal', 3),

-- Service 8 resources
(8, 'COVID-19 Vaccine', 'Pharmaceutical', 1, 0.0000, 1, 'Government supplied', NULL),
(8, 'PPE Kit', 'Safety Equipment', 1, 4.5000, 1, 'Personal protection', 1),
(8, 'Vaccination Certificate', 'Document', 1, 1.0000, 1, 'Official proof', NULL),

-- Service 9 resources
(9, 'Travel Vaccine Package', 'Pharmaceutical', 3, 40.0000, 1, 'Multiple vaccines', 2),
(9, 'International Certificate', 'Document', 1, 5.0000, 1, 'Yellow fever certificate', NULL),

-- Service 10 resources
(10, 'ECG Electrodes', 'Medical Supply', 10, 1.2000, 1, 'Disposable ECG leads', 1),
(10, 'Spirometer Mouthpiece', 'Medical Supply', 1, 3.5000, 1, 'Lung function test', 1),
(10, 'Blood Pressure Cuff', 'Medical Device', 1, 25.0000, 0, 'Digital monitor', 3),

-- Service 11 resources
(11, 'Stethoscope', 'Medical Device', 1, 35.0000, 0, 'Clinical examination', 3),
(11, 'Otoscope Set', 'Medical Device', 1, 85.0000, 0, 'Ear examination', 3),
(11, 'Reflex Hammer', 'Medical Device', 1, 8.5000, 0, 'Neurological assessment', 3),

-- Service 12 resources
(12, 'Bone Density Phantom', 'Lab Equipment', 1, 150.0000, 0, 'DEXA calibration', NULL),
(12, 'Fall Risk Kit', 'Assessment Tool', 1, 45.0000, 0, 'Balance assessment', 3),
(12, 'Medication Software', 'Software', 1, 25.0000, 0, 'Annual subscription', NULL),

-- Service 13 resources
(13, 'Dental Prophy Paste', 'Dental Supply', 1, 4.5000, 1, 'Tooth polishing', 1),
(13, 'Disposable Prophy Angle', 'Dental Supply', 1, 2.7500, 1, 'Polishing attachment', 1),
(13, 'Dental Floss', 'Dental Supply', 1, 0.5000, 1, 'Patient education', NULL),

-- Service 14 resources
(14, 'Dental Composite', 'Dental Supply', 1, 15.0000, 1, 'Tooth-colored filling', 1),
(14, 'Curing Light', 'Dental Equipment', 1, 250.0000, 0, 'LED hardening light', 4),
(14, 'Dental Dam', 'Dental Supply', 1, 3.5000, 1, 'Isolation sheet', 1),

-- Service 15 resources
(15, 'Digital Sensor Cover', 'Dental Supply', 1, 1.2500, 1, 'Sterile barrier', 1),
(15, 'Bitewing Tabs', 'Dental Supply', 2, 0.7500, 1, 'X-ray positioning', NULL),
(15, 'Lead Thyroid Collar', 'Safety Equipment', 1, 12.0000, 0, 'Radiation protection', 3),

-- Service 16 resources
(16, 'Biopsy Cassette', 'Lab Supply', 1, 2.5000, 1, 'Tissue processing', NULL),
(16, 'Histology Slides', 'Lab Supply', 10, 0.8000, 1, 'Glass slides', 1),
(16, 'Staining Reagents', 'Chemical', 1, 25.0000, 1, 'H&E staining', 2),

-- Service 17 resources
(17, 'Pap Smear Kit', 'Test Kit', 1, 8.5000, 1, 'Collection set', 2),
(17, 'Cytology Fixative', 'Chemical', 1, 6.0000, 1, 'Preservative', NULL),
(17, 'Microscope Slides', 'Lab Supply', 5, 1.0000, 1, 'Examination slides', 1);

-- -- Insert carts with valid references
-- INSERT INTO `verdelia`.`cart` (
--   `cart_product_provider_id`,
--   `cart_selling_user`,
--   `cart_status`,
--   `cart_total_amount`,
--   `cart_notes`,
--   `cart_person_ref`
-- ) VALUES
-- -- Provider 2: Open carts (provider_id=2, selling_user=1, person_ref=1)
-- (2, 1, 'open', 85.5000, 'Lab tests pending selection', 1),
-- (2, 1, 'open', 120.0000, 'Follow-up tests needed', 1),

-- -- Provider 2: Pending/processing carts
-- (2, 1, 'pending', 220.7500, 'Waiting for insurance approval', 1),
-- (2, 1, 'pending', 95.2500, 'Payment processing', 1),

-- -- Provider 2: Completed carts
-- (2, 1, 'completed', 65.0000, 'Annual blood work completed on 2024-01-15', 1),
-- (2, 1, 'completed', 180.5000, 'Comprehensive health screening package', 1),
-- (2, 1, 'completed', 45.7500, 'Flu vaccination and basic checkup', 1),

-- -- Provider 3: Various status carts
-- (3, 1, 'open', 350.0000, 'MRI scan consultation', 1),
-- (3, 1, 'pending', 420.5000, 'CT scan scheduled for next week', 1),
-- (3, 1, 'completed', 280.0000, 'Ultrasound completed last month', 1),
-- (3, 1, 'completed', 150.0000, 'X-ray services - sports injury', 1),

-- -- Provider 4: Carts for different services
-- (4, 1, 'open', 600.0000, 'Executive health package under consideration', 1),
-- (4, 1, 'pending', 450.0000, 'Physiotherapy session package - awaiting confirmation', 1),
-- (4, 1, 'completed', 380.0000, 'Sports medicine consultation completed', 1),
-- (4, 1, 'canceled', 220.0000, 'Patient rescheduled acupuncture sessions', 1),

-- -- Provider 5: Vaccination and wellness carts
-- (5, 1, 'open', 0.0000, 'COVID-19 booster - free service', 1),
-- (5, 1, 'pending', 200.0000, 'HPV vaccination series - first dose administered', 1),
-- (5, 1, 'completed', 85.0000, 'Nutrition counseling - initial session', 1),
-- (5, 1, 'completed', 75.0000, 'Electro-acupuncture therapy completed', 1),

-- -- Provider 6: Travel and specialized services
-- (6, 1, 'open', 320.0000, 'Travel vaccination package for Europe trip', 1),
-- (6, 1, 'pending', 130.0000, 'Couples counseling - session package', 1),
-- (6, 1, 'completed', 79.0000, 'Ancestry DNA test results received', 1),
-- (6, 1, 'completed', 200.0000, 'Senior citizen health assessment completed', 1),

-- -- Provider 7: Various medical services
-- (7, 1, 'open', 95.0000, 'Dental cleaning appointment cart', 1),
-- (7, 1, 'pending', 165.0000, 'Dental filling procedure scheduled', 1),
-- (7, 1, 'completed', 40.0000, 'Dental X-ray completed', 1),
-- (7, 1, 'canceled', 100.0000, 'Patient opted for different provider', 1),

-- -- Additional carts with different statuses
-- (3, 1, 'open', 0.0000, 'Consultation cart - no services added yet', 1),
-- (4, 1, 'pending', 750.0000, 'Comprehensive diagnostic package - awaiting lab results', 1),
-- (5, 1, 'completed', 120.0000, 'Travel medicine consultation for Asia trip', 1),
-- (6, 1, 'open', 45.0000, 'Basic urinalysis test selection', 1),
-- (7, 1, 'pending', 300.0000, 'Dental crown procedure - mold taken', 1);

-- -- More varied cart examples
-- INSERT INTO `verdelia`.`cart` (
--   `cart_product_provider_id`,
--   `cart_selling_user`,
--   `cart_status`,
--   `cart_total_amount`,
--   `cart_notes`,
--   `cart_person_ref`
-- ) VALUES
-- (2, 1, 'completed', 560.0000, 'Full body checkup with specialist consultations', 1),
-- (3, 1, 'completed', 680.0000, 'MRI and CT scan package for neurological assessment', 1),
-- (4, 1, 'pending', 900.0000, 'Executive health screening with cardiology consult', 1),
-- (5, 1, 'canceled', 150.0000, 'Canceled due to schedule conflict', 1),
-- (6, 1, 'open', 250.0000, 'Genetic counseling and testing consideration', 1),
-- (7, 1, 'completed', 480.0000, 'Complete dental work including cleaning, filling, and X-ray', 1),
-- (2, 1, 'open', 35.0000, 'Single cholesterol test selection', 1),
-- (3, 1, 'pending', 1500.0000, 'Advanced imaging package - payment plan requested', 1),
-- (4, 1, 'completed', 320.0000, 'Physiotherapy sessions for back pain - completed course', 1),
-- (5, 1, 'open', 0.0000, 'Flu shot reminder cart', 1);

-- -- Insert ordered_services with valid cart_id (1-42) and service_id (1-17)
-- INSERT INTO `verdelia`.`ordered_service` (
--   `ordered_service_cart_id`,
--   `ordered_service_service_id`,
--   `ordered_service_quantity`,
--   `ordered_service_unit_price`,
--   `ordered_service_total_price`,
--   `ordered_service_notes`
-- ) VALUES
-- -- Cart 1-5: Blood Testing Services (services 1-3)
-- (1, 1, 1, 20.0000, 20.0000, 'Complete Blood Count test'),
-- (1, 2, 1, 28.0000, 28.0000, 'Lipid Profile with fasting'),
-- (1, 3, 1, 12.0000, 12.0000, 'Random blood glucose test'),

-- (2, 4, 1, 36.0000, 36.0000, 'Liver function test follow-up'),
-- (2, 5, 1, 48.0000, 48.0000, 'Thyroid panel re-check'),

-- (3, 1, 2, 20.0000, 40.0000, 'CBC for family - 2 persons'),
-- (3, 2, 2, 28.0000, 56.0000, 'Lipid tests for couple'),
-- (3, 3, 1, 12.0000, 12.0000, 'Single glucose test'),

-- (4, 4, 1, 36.0000, 36.0000, 'Annual liver function'),
-- (4, 5, 1, 48.0000, 48.0000, 'Thyroid monitoring'),

-- (5, 1, 1, 20.0000, 20.0000, 'Routine CBC'),
-- (5, 3, 1, 12.0000, 12.0000, 'Diabetes screening'),

-- -- Cart 6-10: Imaging Services (services 6-9)
-- (6, 6, 1, 65.0000, 65.0000, 'Chest X-ray for cough'),
-- (6, 7, 1, 95.0000, 95.0000, 'Abdominal ultrasound'),

-- (7, 8, 1, 360.0000, 360.0000, 'Brain MRI for headaches'),
-- (7, 9, 1, 240.0000, 240.0000, 'Follow-up CT scan'),

-- (8, 6, 1, 65.0000, 65.0000, 'Pre-employment chest X-ray'),
-- (8, 7, 1, 95.0000, 95.0000, 'Gallbladder ultrasound'),

-- (9, 8, 1, 360.0000, 360.0000, 'Neurological assessment MRI'),
-- (10, 9, 1, 240.0000, 240.0000, 'Chest CT for lung nodule'),

-- -- Cart 11-15: Vaccination Services (services 10-13)
-- (11, 10, 1, 25.0000, 25.0000, 'Annual flu shot'),
-- (11, 11, 1, 0.0000, 0.0000, 'COVID-19 booster'),

-- (12, 12, 1, 120.0000, 120.0000, 'Travel vaccination package'),
-- (12, 13, 1, 180.0000, 180.0000, 'HPV vaccine first dose'),

-- (13, 10, 2, 25.0000, 50.0000, 'Flu shots for couple'),
-- (13, 11, 2, 0.0000, 0.0000, 'COVID boosters for family'),

-- (14, 12, 1, 120.0000, 120.0000, 'Business travel vaccinations'),
-- (15, 13, 3, 180.0000, 540.0000, 'HPV vaccine for all 3 doses'),

-- -- Cart 16-20: Health Check-ups (services 14-15)
-- (16, 14, 1, 400.0000, 400.0000, 'Executive health screening'),
-- (16, 15, 1, 80.0000, 80.0000, 'Basic physical added'),

-- (17, 15, 1, 80.0000, 80.0000, 'Annual physical exam'),
-- (18, 14, 1, 400.0000, 400.0000, 'Corporate executive checkup'),

-- (19, 15, 2, 80.0000, 160.0000, 'Family physical exams'),

-- -- Cart 21-25: Dental Care (services 16-17)
-- (21, 16, 1, 65.0000, 65.0000, 'Teeth cleaning'),
-- (22, 17, 2, 100.0000, 200.0000, 'Two fillings needed'),
-- (22, 16, 1, 65.0000, 65.0000, 'Cleaning before fillings'),

-- (24, 16, 1, 65.0000, 65.0000, '6-month cleaning'),
-- (25, 17, 1, 100.0000, 100.0000, 'Single cavity filling'),

-- -- Cart 26-30: Pathology Tests (service 17)
-- (26, 17, 1, 160.0000, 160.0000, 'Skin biopsy analysis'),

-- -- Cart 31-35: Mixed Services
-- (31, 1, 1, 120.0000, 120.0000, 'Allergy skin testing'),
-- (32, 2, 1, 300.0000, 300.0000, 'Genetic carrier screening'),

-- (33, 3, 1, 75.0000, 75.0000, 'Initial physiotherapy assessment'),
-- (34, 4, 1, 85.0000, 85.0000, 'Nutrition consultation'),
-- (35, 5, 4, 100.0000, 400.0000, '4 therapy sessions package'),

-- -- Cart 36-42: Mixed Services
-- (36, 6, 2, 70.0000, 140.0000, '2 acupuncture sessions'),
-- (37, 7, 1, 100.0000, 100.0000, 'First trimester ultrasound'),

-- (38, 8, 1, 65.0000, 65.0000, 'Well-baby checkup'),
-- (39, 9, 1, 130.0000, 130.0000, 'Geriatric health assessment'),

-- (40, 10, 1, 100.0000, 100.0000, 'Sports injury evaluation'),
-- (41, 11, 1, 20.0000, 20.0000, 'Single test cart'),
-- (41, 10, 1, 25.0000, 25.0000, 'Flu shot only'),

-- (42, 16, 1, 65.0000, 65.0000, 'Dental cleaning'),
-- (42, 10, 1, 25.0000, 25.0000, 'Plus flu vaccination');

-- -- Insert ordered_items with valid product_id (1-7) and cart_ref (1-42)
-- INSERT INTO `verdelia`.`ordered_item` (
--   `ordered_product_id`,
--   `ordered_quantity`,
--   `applied_vat`,
--   `unit_price`,
--   `product_discount`,
--   `ordered_item_cart_ref`
-- ) VALUES
-- -- Cart 1: Blood test supplies (product IDs 1-4)
-- (1, 5, 8.0, 1.5000, 0.0, 1),    -- Blood Collection Tubes
-- (1, 10, 8.0, 0.7500, 10.0, 1),   -- Sterile Needles
-- (1, 20, 8.0, 0.2500, 0.0, 1),    -- Alcohol Swabs
-- (2, 1, 8.0, 8.0000, 15.0, 1),    -- Fasting Blood Test Kit

-- -- Cart 2: More lab supplies
-- (2, 2, 8.0, 12.0000, 5.0, 2),    -- Liver Function Reagents
-- (2, 1, 8.0, 25.0000, 10.0, 2),   -- Thyroid Assay Kit
-- (1, 3, 8.0, 0.5000, 0.0, 2),     -- Bandages

-- -- Cart 3: Imaging supplies
-- (4, 2, 18.0, 8.0000, 0.0, 3),    -- X-Ray Films
-- (3, 2, 18.0, 45.0000, 15.0, 3),  -- Lead Aprons
-- (2, 1, 18.0, 35.0000, 10.0, 3),  -- Contrast Media

-- -- Cart 4: Ultrasound supplies
-- (1, 3, 18.0, 5.0000, 5.0, 4),    -- Ultrasound Gel
-- (1, 5, 18.0, 1.2500, 0.0, 4),    -- Probe Covers

-- -- Cart 5: MRI supplies
-- (2, 1, 18.0, 85.0000, 20.0, 5),  -- MRI Contrast Agent
-- (3, 1, 18.0, 12.0000, 5.0, 5),   -- MRI Safe IV Set

-- -- Cart 6: Vaccination supplies
-- (2, 10, 5.0, 18.0000, 25.0, 6),  -- Flu Vaccines
-- (1, 12, 5.0, 0.8500, 10.0, 6),   -- Syringes with Needles
-- (3, 2, 5.0, 3.5000, 0.0, 6),     -- Sharps Containers

-- -- Cart 7: COVID vaccination supplies
-- (1, 25, 0.0, 4.5000, 0.0, 7),    -- PPE Kits

-- -- Cart 8: Travel vaccination package
-- (2, 5, 5.0, 40.0000, 15.0, 8),   -- Travel Vaccines

-- -- Cart 9: Dental supplies
-- (1, 10, 18.0, 4.5000, 10.0, 9),  -- Dental Prophy Paste
-- (1, 15, 18.0, 2.7500, 5.0, 9),   -- Disposable Prophy Angles
-- (1, 20, 18.0, 0.5000, 0.0, 9),   -- Dental Floss

-- -- Cart 10: Dental filling materials
-- (1, 5, 18.0, 15.0000, 15.0, 10), -- Dental Composite
-- (1, 10, 18.0, 3.5000, 5.0, 10),  -- Dental Dam
-- (4, 1, 18.0, 250.0000, 20.0, 10), -- Curing Light

-- -- Cart 11: X-ray dental supplies
-- (1, 20, 18.0, 1.2500, 5.0, 11),  -- Digital Sensor Covers
-- (3, 2, 18.0, 12.0000, 10.0, 11), -- Lead Thyroid Collars

-- -- Cart 12: Pathology lab supplies
-- (2, 5, 8.0, 25.0000, 15.0, 12),  -- Staining Reagents
-- (1, 50, 8.0, 0.8000, 20.0, 12),  -- Histology Slides

-- -- Cart 13: Urine test supplies
-- (1, 25, 8.0, 0.8500, 10.0, 13),  -- Urine Collection Cups
-- (2, 30, 8.0, 2.2500, 15.0, 13),  -- Urine Test Strips
-- (2, 10, 8.0, 4.5000, 20.0, 13),  -- Culture Media Plates

-- -- Cart 14: Allergy testing supplies
-- (2, 50, 8.0, 0.9500, 25.0, 14),  -- Allergen Extracts
-- (1, 60, 8.0, 0.1500, 30.0, 14),  -- Skin Test Lancets

-- -- Cart 15: Genetic testing supplies
-- (2, 3, 8.0, 350.0000, 20.0, 15), -- Carrier Screening Kits
-- (3, 1, 8.0, 25.0000, 10.0, 15),  -- Software Subscription

-- -- Cart 16: Physiotherapy equipment
-- (3, 2, 18.0, 25.0000, 15.0, 16), -- Blood Pressure Cuffs
-- (3, 1, 18.0, 35.0000, 10.0, 16), -- Stethoscopes
-- (3, 1, 18.0, 85.0000, 20.0, 16), -- Otoscope/Ophthalmoscope Set

-- -- Cart 17: Sports medicine equipment
-- (3, 1, 18.0, 45.0000, 15.0, 17), -- Fall Risk Assessment Kit
-- (3, 2, 18.0, 8.5000, 10.0, 17),  -- Reflex Hammers
-- (4, 1, 18.0, 150.0000, 25.0, 17), -- Bone Density Calibration

-- -- Cart 18: Single product orders
-- (1, 100, 8.0, 0.2500, 40.0, 18),  -- Bulk Alcohol Swabs
-- (2, 1, 18.0, 65.0000, 0.0, 19),   -- Single CT Contrast
-- (3, 3, 18.0, 12.0000, 10.0, 20),  -- Multiple IV Sets
-- (4, 2, 18.0, 8.0000, 5.0, 21),    -- X-Ray Films
-- (1, 50, 5.0, 0.8500, 30.0, 22),   -- Bulk Syringes

-- -- Cart 19-25: Mixed medical supplies
-- (2, 4, 8.0, 12.0000, 15.0, 23),   -- Liver Reagents
-- (1, 30, 8.0, 1.5000, 20.0, 24),   -- Blood Tubes
-- (3, 1, 18.0, 35.0000, 10.0, 25),  -- Stethoscope
-- (2, 2, 18.0, 85.0000, 25.0, 26),  -- MRI Contrast
-- (1, 15, 18.0, 4.5000, 15.0, 27),  -- Dental Paste
-- (2, 8, 5.0, 18.0000, 30.0, 28),   -- Flu Vaccines
-- (1, 40, 8.0, 0.8500, 35.0, 29),   -- Urine Cups

-- -- Cart 30-35: Business/wholesale orders
-- (1, 500, 8.0, 0.7500, 50.0, 30),  -- Wholesale Needles
-- (2, 100, 8.0, 2.2500, 40.0, 31),  -- Bulk Test Strips
-- (3, 25, 18.0, 3.5000, 35.0, 32),  -- Sharps Containers
-- (1, 200, 18.0, 5.0000, 30.0, 34), -- Ultrasound Gel
-- (2, 20, 18.0, 35.0000, 25.0, 35), -- Contrast Media

-- -- Cart 36-42: Final mixed carts
-- (1, 10, 8.0, 1.5000, 10.0, 36),   -- Blood Tubes
-- (2, 5, 8.0, 8.0000, 15.0, 37),    -- Test Kits
-- (3, 2, 18.0, 45.0000, 20.0, 38),  -- Lead Aprons
-- (1, 25, 5.0, 0.8500, 25.0, 40),   -- Syringes
-- (2, 1, 18.0, 250.0000, 30.0, 41), -- Curing Light
-- (3, 1, 8.0, 25.0000, 15.0, 42);   -- Software

-- -- Insert more varied orders
-- INSERT INTO `verdelia`.`ordered_item` (
--   `ordered_product_id`,
--   `ordered_quantity`,
--   `applied_vat`,
--   `unit_price`,
--   `product_discount`,
--   `ordered_item_cart_ref`
-- ) VALUES
-- -- Zero VAT items (medical essentials)
-- (1, 15, 0.0, 1.5000, 0.0, 1),
-- (2, 3, 0.0, 8.0000, 10.0, 2),

-- -- High VAT items (non-essential medical equipment)
-- (4, 1, 23.0, 250.0000, 15.0, 3),
-- (3, 2, 23.0, 85.0000, 20.0, 4),

-- -- Small orders for individual patients
-- (1, 5, 8.0, 0.2500, 0.0, 7),
-- (2, 1, 8.0, 25.0000, 5.0, 8),
-- (3, 1, 18.0, 35.0000, 10.0, 9),

-- -- Mixed VAT cart
-- (1, 10, 8.0, 1.5000, 10.0, 10),
-- (2, 2, 18.0, 35.0000, 15.0, 10),
-- (3, 1, 23.0, 85.0000, 20.0, 10),

-- -- Emergency order (no discount)
-- (1, 50, 8.0, 1.5000, 0.0, 11),
-- (2, 10, 8.0, 12.0000, 0.0, 11),

-- -- Seasonal sale items
-- (1, 20, 8.0, 4.5000, 50.0, 12),
-- (2, 5, 8.0, 18.0000, 40.0, 12),
-- (3, 3, 18.0, 12.0000, 30.0, 12);

-- -- Insert invoices with valid cart_id (1-42)
-- -- INSERT INTO `verdelia`.`invoice` (
-- --   `invoice_cart_id`,
-- --   `invoice_number`,
-- --   `invoice_total_amount`,
-- --   `invoice_status`,
-- --   `invoice_issue_date`,
-- --   `invoice_due_date`,
-- --   `invoice_notes`
-- -- ) VALUES
-- -- -- Cart 1-10: Various invoices
-- -- (1, 'INV-2024-001', 85.5000, 'paid', '2024-01-15', '2024-02-15', 'Complete blood work invoice'),
-- -- (2, 'INV-2024-002', 120.0000, 'paid', '2024-01-16', '2024-02-16', 'Follow-up tests invoice'),
-- -- (3, 'INV-2024-003', 220.7500, 'paid', '2024-01-17', '2024-02-17', 'Family tests package'),
-- -- (4, 'INV-2024-004', 95.2500, 'paid', '2024-01-18', '2024-02-18', 'Annual screening tests'),
-- -- (5, 'INV-2024-005', 65.0000, 'paid', '2024-01-19', '2024-02-19', 'Basic CBC screening'),
-- -- (6, 'INV-2024-006', 180.5000, 'paid', '2024-01-20', '2024-02-20', 'Chest X-ray and ultrasound'),
-- -- (7, 'INV-2024-007', 420.5000, 'paid', '2024-01-21', '2024-02-21', 'MRI and CT scan package'),
-- -- (8, 'INV-2024-008', 150.0000, 'paid', '2024-01-22', '2024-02-22', 'Pre-employment tests'),
-- -- (9, 'INV-2024-009', 280.0000, 'paid', '2024-01-23', '2024-02-23', 'Neurological MRI'),
-- -- (10, 'INV-2024-010', 240.0000, 'paid', '2024-01-24', '2024-02-24', 'CT scan follow-up'),

-- -- -- Cart 11-20: More invoices
-- -- (11, 'INV-2024-011', 25.0000, 'paid', '2024-01-25', '2024-02-25', 'Annual flu vaccination'),
-- -- (12, 'INV-2024-012', 300.0000, 'paid', '2024-01-26', '2024-02-26', 'Travel vaccination'),
-- -- (13, 'INV-2024-013', 50.0000, 'paid', '2024-01-27', '2024-02-27', 'Family flu shots'),
-- -- (14, 'INV-2024-014', 120.0000, 'paid', '2024-01-28', '2024-02-28', 'Business travel'),
-- -- (15, 'INV-2024-015', 540.0000, 'paid', '2024-01-29', '2024-02-29', 'HPV vaccine series'),
-- -- (16, 'INV-2024-016', 480.0000, 'paid', '2024-01-30', '2024-03-01', 'Executive health'),
-- -- (17, 'INV-2024-017', 280.0000, 'unpaid', '2024-02-01', '2024-03-01', 'Annual physical'),
-- -- (18, 'INV-2024-018', 400.0000, 'paid', '2024-02-02', '2024-03-02', 'Corporate checkup'),
-- -- (19, 'INV-2024-019', 160.0000, 'unpaid', '2024-02-03', '2024-03-03', 'Family exams'),
-- -- (20, 'INV-2024-020', 200.0000, 'paid', '2024-02-04', '2024-03-04', 'Geriatric assessment'),

-- -- -- Cart 21-30: More invoices
-- -- (21, 'INV-2024-021', 105.0000, 'paid', '2024-02-05', '2024-03-05', 'Dental cleaning'),
-- -- (22, 'INV-2024-022', 265.0000, 'paid', '2024-02-06', '2024-03-06', 'Dental fillings'),
-- -- (23, 'INV-2024-023', 40.0000, 'paid', '2024-02-07', '2024-03-07', 'Dental X-rays'),
-- -- (24, 'INV-2024-024', 65.0000, 'paid', '2024-02-08', '2024-03-08', '6-month cleaning'),
-- -- (25, 'INV-2024-025', 100.0000, 'unpaid', '2024-02-09', '2024-03-09', 'Single filling'),
-- -- (26, 'INV-2024-026', 205.0000, 'paid', '2024-02-10', '2024-03-10', 'Biopsy tests'),
-- -- (27, 'INV-2024-027', 160.0000, 'paid', '2024-02-11', '2024-03-11', 'Mole biopsy'),
-- -- (28, 'INV-2024-028', 45.0000, 'paid', '2024-02-12', '2024-03-12', 'Gynecological screening'),
-- -- (29, 'INV-2024-029', 56.0000, 'paid', '2024-02-13', '2024-03-13', 'UTI tests'),
-- -- (30, 'INV-2024-030', 20.0000, 'unpaid', '2024-02-14', '2024-03-14', 'Drug screening'),

-- -- -- Cart 31-42: More invoices
-- -- (31, 'INV-2024-031', 270.0000, 'paid', '2024-02-15', '2024-03-15', 'Allergy testing'),
-- -- (32, 'INV-2024-032', 379.0000, 'paid', '2024-02-16', '2024-03-16', 'Genetic testing'),
-- -- (33, 'INV-2024-033', 255.0000, 'unpaid', '2024-02-17', '2024-03-17', 'Physiotherapy'),
-- -- (34, 'INV-2024-034', 585.0000, 'paid', '2024-02-18', '2024-03-18', 'Weight management'),
-- -- (35, 'INV-2024-035', 530.0000, 'unpaid', '2024-02-19', '2024-03-19', 'Therapy package'),
-- -- (36, 'INV-2024-036', 215.0000, 'paid', '2024-02-20', '2024-03-20', 'Acupuncture'),
-- -- (37, 'INV-2024-037', 280.0000, 'paid', '2024-02-21', '2024-03-21', 'Prenatal care'),
-- -- (38, 'INV-2024-038', 165.0000, 'paid', '2024-02-22', '2024-03-22', 'Pediatric care'),
-- -- (39, 'INV-2024-039', 215.0000, 'unpaid', '2024-02-23', '2024-03-23', 'Geriatric care'),
-- -- (40, 'INV-2024-040', 230.0000, 'paid', '2024-02-24', '2024-03-24', 'Sports medicine'),
-- -- (41, 'INV-2024-041', 45.0000, 'paid', '2024-02-25', '2024-03-25', 'Single tests'),
-- -- (42, 'INV-2024-042', 130.0000, 'canceled', '2024-02-26', '2024-03-26', 'Dental + flu');

-- -- -- Insert more invoices
-- -- INSERT INTO `verdelia`.`invoice` (
-- --   `invoice_cart_id`,
-- --   `invoice_number`,
-- --   `invoice_total_amount`,
-- --   `invoice_status`,
-- --   `invoice_issue_date`,
-- --   `invoice_due_date`,
-- --   `invoice_notes`
-- -- ) VALUES
-- -- -- Past due invoices
-- -- (17, 'INV-2024-043', 280.0000, 'unpaid', '2024-01-15', '2024-02-15', 'PAST DUE - Annual physical'),
-- -- (19, 'INV-2024-044', 160.0000, 'unpaid', '2024-01-20', '2024-02-20', 'PAST DUE - Family exams'),
-- -- (25, 'INV-2024-045', 100.0000, 'unpaid', '2024-01-25', '2024-02-25', 'PAST DUE - Dental filling'),

-- -- -- Bulk/wholesale invoices
-- -- (5, 'INV-2024-048', 650.0000, 'paid', '2024-02-01', '2024-03-01', 'Corporate bulk order'),
-- -- (11, 'INV-2024-049', 250.0000, 'paid', '2024-02-05', '2024-03-05', 'Company flu program'),

-- -- -- Recent invoices
-- -- (17, 'INV-2024-054', 280.0000, 'unpaid', CURDATE(), DATE_ADD(CURDATE(), INTERVAL 30 DAY), 'Current month invoice'),
-- -- (25, 'INV-2024-055', 100.0000, 'unpaid', CURDATE(), DATE_ADD(CURDATE(), INTERVAL 30 DAY), 'Current dental work');

-- -- -- Insert payments with valid invoice_id (1-60)
-- -- INSERT INTO `verdelia`.`payment` (
-- --   `payment_invoice_id`,
-- --   `payment_amount`,
-- --   `payment_method`,
-- --   `payment_status`,
-- --   `payment_reference`,
-- --   `payment_notes`
-- -- ) VALUES
-- -- -- Full payments for invoices 1-10
-- -- (1, 85.5000, 'card', 'completed', 'TXN-00123456', 'Credit card payment'),
-- -- (2, 120.0000, 'bank', 'completed', 'BANK-78901234', 'Bank transfer'),
-- -- (3, 220.7500, 'card', 'completed', 'TXN-56789012', 'Debit card payment');


-- -- INSERT INTO `verdelia`.`cart` (
-- --   `cart_product_provider_id`,
-- --   `cart_selling_user`,
-- --   `cart_status`,
-- --   `cart_total_amount`,
-- --   `cart_notes`,
-- --   `cart_person_ref`
-- -- ) VALUES
-- -- -- Provider 2: Open carts
-- -- (2, 2, 'open', 85.5000, 'Lab tests pending selection', 2),
-- -- (2, 2, 'open', 120.0000, 'Follow-up tests needed', 2),

-- -- -- Provider 2: Pending/processing carts
-- -- (2, 2, 'pending', 220.7500, 'Waiting for insurance approval', 2),
-- -- (2, 2, 'pending', 95.2500, 'Payment processing', 2),

-- -- -- Provider 2: Completed carts
-- -- (2, 2, 'completed', 65.0000, 'Annual blood work completed on 2024-01-15', 2),
-- -- (2, 2, 'completed', 180.5000, 'Comprehensive health screening package', 2),
-- -- (2, 2, 'completed', 45.7500, 'Flu vaccination and basic checkup', 2),

-- -- -- Provider 3: Various status carts
-- -- (3, 2, 'open', 350.0000, 'MRI scan consultation', 2),
-- -- (3, 2, 'pending', 420.5000, 'CT scan scheduled for next week', 2),
-- -- (3, 2, 'completed', 280.0000, 'Ultrasound completed last month', 2),
-- -- (3, 2, 'completed', 150.0000, 'X-ray services - sports injury', 2),

-- -- -- Provider 4: Carts for different services
-- -- (4, 2, 'open', 600.0000, 'Executive health package under consideration', 2),
-- -- (4, 2, 'pending', 450.0000, 'Physiotherapy session package - awaiting confirmation', 2),
-- -- (4, 2, 'completed', 380.0000, 'Sports medicine consultation completed', 2),
-- -- (4, 2, 'canceled', 220.0000, 'Patient rescheduled acupuncture sessions', 2),

-- -- -- Provider 5: Vaccination and wellness carts
-- -- (5, 2, 'open', 0.0000, 'COVID-19 booster - free service', 2),
-- -- (5, 2, 'pending', 200.0000, 'HPV vaccination series - first dose administered', 2),
-- -- (5, 2, 'completed', 85.0000, 'Nutrition counseling - initial session', 2),
-- -- (5, 2, 'completed', 75.0000, 'Electro-acupuncture therapy completed', 2),

-- -- -- Provider 6: Travel and specialized services
-- -- (6, 2, 'open', 320.0000, 'Travel vaccination package for Europe trip', 2),
-- -- (6, 2, 'pending', 130.0000, 'Couples counseling - session package', 2),
-- -- (6, 2, 'completed', 79.0000, 'Ancestry DNA test results received', 2),
-- -- (6, 2, 'completed', 200.0000, 'Senior citizen health assessment completed', 2),

-- -- -- Provider 7: Various medical services
-- (7, 2, 'open', 95.0000, 'Dental cleaning appointment cart', 2),
-- (7, 2, 'pending', 165.0000, 'Dental filling procedure scheduled', 2),
-- (7, 2, 'completed', 40.0000, 'Dental X-ray completed', 2),
-- (7, 2, 'canceled', 100.0000, 'Patient opted for different provider', 2),

-- -- Additional carts with different statuses
-- (3, 2, 'open', 0.0000, 'Consultation cart - no services added yet', 2),
-- (4, 2, 'pending', 750.0000, 'Comprehensive diagnostic package - awaiting lab results', 2),
-- (5, 2, 'completed', 120.0000, 'Travel medicine consultation for Asia trip', 2),
-- (6, 2, 'open', 45.0000, 'Basic urinalysis test selection', 2),
-- (7, 2, 'pending', 300.0000, 'Dental crown procedure - mold taken', 2);

-- -- More varied cart examples
-- INSERT INTO `verdelia`.`cart` (
--   `cart_product_provider_id`,
--   `cart_selling_user`,
--   `cart_status`,
--   `cart_total_amount`,
--   `cart_notes`,
--   `cart_person_ref`
-- ) VALUES
-- (2, 2, 'completed', 560.0000, 'Full body checkup with specialist consultations', 2),
-- (3, 2, 'completed', 680.0000, 'MRI and CT scan package for neurological assessment', 2),
-- (4, 2, 'pending', 900.0000, 'Executive health screening with cardiology consult', 2),
-- (5, 2, 'canceled', 150.0000, 'Canceled due to schedule conflict', 2),
-- (6, 2, 'open', 250.0000, 'Genetic counseling and testing consideration', 2),
-- (7, 2, 'completed', 480.0000, 'Complete dental work including cleaning, filling, and X-ray', 2),
-- (2, 2, 'open', 35.0000, 'Single cholesterol test selection', 2),
-- (3, 2, 'pending', 1500.0000, 'Advanced imaging package - payment plan requested', 2),
-- (4, 2, 'completed', 320.0000, 'Physiotherapy sessions for back pain - completed course', 2),
-- (5, 2, 'open', 0.0000, 'Flu shot reminder cart', 2);

-- Insert dummy data for ordered_service table
-- INSERT INTO `verdelia`.`ordered_service` (
--   `ordered_service_cart_id`,
--   `ordered_service_service_id`,
--   `ordered_service_quantity`,
--   `ordered_service_unit_price`,
--   `ordered_service_total_price`,
--   `ordered_service_notes`
-- ) VALUES
-- -- Cart 1-5: Blood Testing Services
-- (1, 44, 1, 20.0000, 20.0000, 'Complete Blood Count test'),
-- (1, 45, 1, 28.0000, 28.0000, 'Lipid Profile with fasting'),
-- (1, 46, 1, 12.0000, 12.0000, 'Random blood glucose test'),

-- (2, 47, 1, 36.0000, 36.0000, 'Liver function test follow-up'),
-- (2, 48, 1, 48.0000, 48.0000, 'Thyroid panel re-check'),

-- (3, 44, 2, 20.0000, 40.0000, 'CBC for family - 2 persons'),
-- (3, 45, 2, 28.0000, 56.0000, 'Lipid tests for couple'),
-- (3, 46, 1, 12.0000, 12.0000, 'Single glucose test'),

-- (4, 47, 1, 36.0000, 36.0000, 'Annual liver function'),
-- (4, 48, 1, 48.0000, 48.0000, 'Thyroid monitoring'),

-- (5, 44, 1, 20.0000, 20.0000, 'Routine CBC'),
-- (5, 46, 1, 12.0000, 12.0000, 'Diabetes screening'),

-- -- Cart 6-10: Imaging Services
-- (6, 49, 1, 65.0000, 65.0000, 'Chest X-ray for cough'),
-- (6, 50, 1, 95.0000, 95.0000, 'Abdominal ultrasound'),

-- (7, 51, 1, 360.0000, 360.0000, 'Brain MRI for headaches'),
-- (7, 52, 1, 240.0000, 240.0000, 'Follow-up CT scan'),

-- (8, 49, 1, 65.0000, 65.0000, 'Pre-employment chest X-ray'),
-- (8, 50, 1, 95.0000, 95.0000, 'Gallbladder ultrasound'),

-- (9, 51, 1, 360.0000, 360.0000, 'Neurological assessment MRI'),

-- (10, 52, 1, 240.0000, 240.0000, 'Chest CT for lung nodule'),

-- -- Cart 11-15: Vaccination Services
-- (11, 53, 1, 25.0000, 25.0000, 'Annual flu shot'),
-- (11, 54, 1, 0.0000, 0.0000, 'COVID-19 booster'),

-- (12, 55, 1, 120.0000, 120.0000, 'Travel vaccination package'),
-- (12, 56, 1, 180.0000, 180.0000, 'HPV vaccine first dose'),

-- (13, 53, 2, 25.0000, 50.0000, 'Flu shots for couple'),
-- (13, 54, 2, 0.0000, 0.0000, 'COVID boosters for family'),

-- (14, 55, 1, 120.0000, 120.0000, 'Business travel vaccinations'),

-- (15, 56, 3, 180.0000, 540.0000, 'HPV vaccine for all 3 doses'),

-- -- Cart 16-20: Health Check-ups
-- (16, 57, 1, 400.0000, 400.0000, 'Executive health screening'),
-- (16, 58, 1, 80.0000, 80.0000, 'Basic physical added'),

-- (17, 58, 1, 80.0000, 80.0000, 'Annual physical exam'),
-- (17, 59, 1, 200.0000, 200.0000, 'Elderly parent check-up'),

-- (18, 57, 1, 400.0000, 400.0000, 'Corporate executive checkup'),

-- (19, 58, 2, 80.0000, 160.0000, 'Family physical exams'),

-- (20, 59, 1, 200.0000, 200.0000, 'Geriatric assessment'),

-- -- Cart 21-25: Dental Care
-- (21, 60, 1, 65.0000, 65.0000, 'Teeth cleaning'),
-- (21, 62, 1, 40.0000, 40.0000, 'Dental X-rays'),

-- (22, 61, 2, 100.0000, 200.0000, 'Two fillings needed'),
-- (22, 60, 1, 65.0000, 65.0000, 'Cleaning before fillings'),

-- (23, 62, 1, 40.0000, 40.0000, 'Routine dental X-rays'),

-- (24, 60, 1, 65.0000, 65.0000, '6-month cleaning'),

-- (25, 61, 1, 100.0000, 100.0000, 'Single cavity filling'),

-- -- Cart 26-30: Pathology & Lab Tests
-- (26, 63, 1, 160.0000, 160.0000, 'Skin biopsy analysis'),
-- (26, 64, 1, 45.0000, 45.0000, 'Routine pap smear'),

-- (27, 63, 1, 160.0000, 160.0000, 'Mole biopsy'),

-- (28, 64, 1, 45.0000, 45.0000, 'Annual gynecological screening'),

-- (29, 65, 1, 20.0000, 20.0000, 'Urinalysis for UTI'),
-- (29, 66, 1, 36.0000, 36.0000, 'Urine culture'),

-- (30, 65, 1, 20.0000, 20.0000, 'Pre-employment drug screen'),

-- -- Cart 31-35: Specialized Services
-- (31, 67, 1, 120.0000, 120.0000, 'Allergy skin testing'),
-- (31, 68, 1, 150.0000, 150.0000, 'Food allergy panel'),

-- (32, 69, 1, 300.0000, 300.0000, 'Genetic carrier screening'),
-- (32, 70, 1, 79.0000, 79.0000, 'Ancestry DNA test'),

-- (33, 71, 1, 75.0000, 75.0000, 'Initial physiotherapy assessment'),
-- (33, 72, 3, 60.0000, 180.0000, '3 massage therapy sessions'),

-- (34, 73, 1, 85.0000, 85.0000, 'Nutrition consultation'),
-- (34, 74, 1, 500.0000, 500.0000, 'Weight management program'),

-- (35, 75, 4, 100.0000, 400.0000, '4 therapy sessions package'),
-- (35, 76, 1, 130.0000, 130.0000, 'Couples counseling'),

-- -- Cart 36-42: Mixed Services
-- (36, 77, 2, 70.0000, 140.0000, '2 acupuncture sessions'),
-- (36, 78, 1, 75.0000, 75.0000, 'Electro-acupuncture'),

-- (37, 79, 1, 100.0000, 100.0000, 'First trimester ultrasound'),
-- (37, 80, 1, 180.0000, 180.0000, 'Prenatal blood work'),

-- (38, 81, 1, 65.0000, 65.0000, 'Well-baby checkup'),
-- (38, 82, 1, 100.0000, 100.0000, 'Child development assessment'),

-- (39, 83, 1, 130.0000, 130.0000, 'Geriatric health assessment'),
-- (39, 84, 1, 85.0000, 85.0000, 'Fall risk evaluation'),

-- (40, 85, 1, 100.0000, 100.0000, 'Sports injury evaluation'),
-- (40, 86, 1, 130.0000, 130.0000, 'Athletic performance consultation'),

-- (41, 44, 1, 20.0000, 20.0000, 'Single test cart'),
-- (41, 53, 1, 25.0000, 25.0000, 'Flu shot only'),

-- (42, 60, 1, 65.0000, 65.0000, 'Dental cleaning'),
-- (42, 62, 1, 40.0000, 40.0000, 'With X-rays'),
-- (42, 53, 1, 25.0000, 25.0000, 'Plus flu vaccination');




-- Insert dummy data for ordered_item table
-- INSERT INTO `verdelia`.`ordered_item` (
--   `ordered_product_id`,
--   `ordered_quantity`,
--   `applied_vat`,
--   `unit_price`,
--   `product_discount`,
--   `ordered_item_cart_ref`
-- ) VALUES
-- -- Cart 1: Blood test supplies (product IDs 8-11)
-- (8, 5, 8.0, 1.5000, 0.0, 1),    -- Blood Collection Tubes
-- (8, 10, 8.0, 0.7500, 10.0, 1),   -- Sterile Needles
-- (8, 20, 8.0, 0.2500, 0.0, 1),    -- Alcohol Swabs
-- (9, 1, 8.0, 8.0000, 15.0, 1),    -- Fasting Blood Test Kit

-- -- Cart 2: More lab supplies
-- (9, 2, 8.0, 12.0000, 5.0, 2),    -- Liver Function Reagents
-- (9, 1, 8.0, 25.0000, 10.0, 2),   -- Thyroid Assay Kit
-- (8, 3, 8.0, 0.5000, 0.0, 2),     -- Bandages

-- -- Cart 3: Imaging supplies
-- (11, 2, 18.0, 8.0000, 0.0, 3),   -- X-Ray Films
-- (10, 2, 18.0, 45.0000, 15.0, 3), -- Lead Aprons
-- (9, 1, 18.0, 35.0000, 10.0, 3),  -- Contrast Media

-- -- Cart 4: Ultrasound supplies
-- (8, 3, 18.0, 5.0000, 5.0, 4),    -- Ultrasound Gel
-- (8, 5, 18.0, 1.2500, 0.0, 4),    -- Probe Covers
-- (11, 1, 18.0, 2.0000, 0.0, 4),   -- Thermal Paper

-- -- Cart 5: MRI supplies
-- (9, 1, 18.0, 85.0000, 20.0, 5),  -- MRI Contrast Agent
-- (10, 1, 18.0, 12.0000, 5.0, 5),  -- MRI Safe IV Set
-- (NULL, 2, 18.0, 3.0000, 0.0, 5), -- Ear Protection (no product ref)

-- -- Cart 6: Vaccination supplies
-- (9, 10, 5.0, 18.0000, 25.0, 6),  -- Flu Vaccines
-- (8, 12, 5.0, 0.8500, 10.0, 6),   -- Syringes with Needles
-- (10, 2, 5.0, 3.5000, 0.0, 6),    -- Sharps Containers

-- -- Cart 7: COVID vaccination supplies
-- (8, 25, 0.0, 4.5000, 0.0, 7),    -- PPE Kits (no VAT for medical emergency)
-- (NULL, 50, 0.0, 1.0000, 0.0, 7), -- Vaccination Certificates

-- -- Cart 8: Travel vaccination package
-- (9, 5, 5.0, 40.0000, 15.0, 8),   -- Travel Vaccines
-- (NULL, 2, 5.0, 5.0000, 0.0, 8),  -- International Certificates
-- (NULL, 5, 5.0, 2.5000, 20.0, 8), -- Travel Health Guides

-- -- Cart 9: Dental supplies
-- (8, 10, 18.0, 4.5000, 10.0, 9),  -- Dental Prophy Paste
-- (8, 15, 18.0, 2.7500, 5.0, 9),   -- Disposable Prophy Angles
-- (8, 20, 18.0, 0.5000, 0.0, 9),   -- Dental Floss

-- -- Cart 10: Dental filling materials
-- (8, 5, 18.0, 15.0000, 15.0, 10), -- Dental Composite
-- (8, 10, 18.0, 3.5000, 5.0, 10),  -- Dental Dam
-- (11, 1, 18.0, 250.0000, 20.0, 10), -- Curing Light (equipment)

-- -- Cart 11: X-ray dental supplies
-- (8, 20, 18.0, 1.2500, 5.0, 11),  -- Digital Sensor Covers
-- (10, 2, 18.0, 12.0000, 10.0, 11), -- Lead Thyroid Collars
-- (NULL, 10, 18.0, 0.7500, 0.0, 11), -- Bitewing Tabs

-- -- Cart 12: Pathology lab supplies
-- (9, 5, 8.0, 25.0000, 15.0, 12),  -- Staining Reagents
-- (8, 50, 8.0, 0.8000, 20.0, 12),  -- Histology Slides
-- (NULL, 20, 8.0, 2.5000, 5.0, 12), -- Biopsy Cassettes

-- -- Cart 13: Urine test supplies
-- (8, 25, 8.0, 0.8500, 10.0, 13),  -- Urine Collection Cups
-- (9, 30, 8.0, 2.2500, 15.0, 13),  -- Urine Test Strips
-- (9, 10, 8.0, 4.5000, 20.0, 13),  -- Culture Media Plates

-- -- Cart 14: Allergy testing supplies
-- (9, 50, 8.0, 0.9500, 25.0, 14),  -- Allergen Extracts
-- (8, 60, 8.0, 0.1500, 30.0, 14),  -- Skin Test Lancets
-- (NULL, 5, 8.0, 3.5000, 0.0, 14), -- Measuring Rulers

-- -- Cart 15: Genetic testing supplies
-- (9, 3, 8.0, 350.0000, 20.0, 15), -- Carrier Screening Kits
-- (NULL, 2, 8.0, 99.0000, 25.0, 15), -- Ancestry DNA Kits
-- (10, 1, 8.0, 25.0000, 10.0, 15), -- Software Subscription

-- -- Cart 16: Physiotherapy equipment
-- (10, 2, 18.0, 25.0000, 15.0, 16), -- Blood Pressure Cuffs
-- (10, 1, 18.0, 35.0000, 10.0, 16), -- Stethoscopes
-- (10, 1, 18.0, 85.0000, 20.0, 16), -- Otoscope/Ophthalmoscope Set

-- -- Cart 17: Sports medicine equipment
-- (10, 1, 18.0, 45.0000, 15.0, 17), -- Fall Risk Assessment Kit
-- (10, 2, 18.0, 8.5000, 10.0, 17),  -- Reflex Hammers
-- (11, 1, 18.0, 150.0000, 25.0, 17), -- Bone Density Calibration

-- -- Cart 18: Single product orders
-- (8, 100, 8.0, 0.2500, 40.0, 18),  -- Bulk Alcohol Swabs
-- (9, 1, 18.0, 65.0000, 0.0, 19),   -- Single CT Contrast
-- (10, 3, 18.0, 12.0000, 10.0, 20), -- Multiple IV Sets
-- (11, 2, 18.0, 8.0000, 5.0, 21),   -- X-Ray Films
-- (8, 50, 5.0, 0.8500, 30.0, 22),   -- Bulk Syringes

-- -- Cart 19-25: Mixed medical supplies
-- (9, 4, 8.0, 12.0000, 15.0, 23),   -- Liver Reagents
-- (8, 30, 8.0, 1.5000, 20.0, 24),   -- Blood Tubes
-- (10, 1, 18.0, 35.0000, 10.0, 25), -- Stethoscope
-- (9, 2, 18.0, 85.0000, 25.0, 26),  -- MRI Contrast
-- (8, 15, 18.0, 4.5000, 15.0, 27),  -- Dental Paste
-- (9, 8, 5.0, 18.0000, 30.0, 28),   -- Flu Vaccines
-- (8, 40, 8.0, 0.8500, 35.0, 29),   -- Urine Cups

-- -- Cart 30-35: Business/wholesale orders
-- (8, 500, 8.0, 0.7500, 50.0, 30),  -- Wholesale Needles
-- (9, 100, 8.0, 2.2500, 40.0, 31),  -- Bulk Test Strips
-- (10, 25, 18.0, 3.5000, 35.0, 32), -- Sharps Containers
-- (11, 50, 18.0, 1.2500, 45.0, 33), -- Sensor Covers
-- (8, 200, 18.0, 5.0000, 30.0, 34), -- Ultrasound Gel
-- (9, 20, 18.0, 35.0000, 25.0, 35), -- Contrast Media

-- -- Cart 36-42: Final mixed carts
-- (8, 10, 8.0, 1.5000, 10.0, 36),   -- Blood Tubes
-- (9, 5, 8.0, 8.0000, 15.0, 37),    -- Test Kits
-- (10, 2, 18.0, 45.0000, 20.0, 38), -- Lead Aprons
-- (11, 3, 18.0, 2.0000, 0.0, 39),   -- Thermal Paper
-- (8, 25, 5.0, 0.8500, 25.0, 40),   -- Syringes
-- (9, 1, 18.0, 250.0000, 30.0, 41), -- Curing Light
-- (10, 1, 8.0, 25.0000, 15.0, 42);  -- Software



-- More varied orders with different scenarios
-- INSERT INTO `verdelia`.`ordered_item` (
--   `ordered_product_id`,
--   `ordered_quantity`,
--   `applied_vat`,
--   `unit_price`,
--   `product_discount`,
--   `ordered_item_cart_ref`
-- ) VALUES
-- -- Zero VAT items (medical essentials)
-- (8, 15, 0.0, 1.5000, 0.0, 1),
-- (9, 3, 0.0, 8.0000, 10.0, 2),

-- -- High VAT items (non-essential medical equipment)
-- (11, 1, 23.0, 250.0000, 15.0, 3),
-- (10, 2, 23.0, 85.0000, 20.0, 4),

-- -- Bulk orders with tiered discounts
-- (8, 1000, 8.0, 0.7500, 60.0, 5),
-- (9, 500, 8.0, 2.2500, 55.0, 6),

-- -- Small orders for individual patients
-- (8, 5, 8.0, 0.2500, 0.0, 7),
-- (9, 1, 8.0, 25.0000, 5.0, 8),
-- (10, 1, 18.0, 35.0000, 10.0, 9),

-- -- Mixed VAT cart
-- (8, 10, 8.0, 1.5000, 10.0, 10),
-- (9, 2, 18.0, 35.0000, 15.0, 10),
-- (10, 1, 23.0, 85.0000, 20.0, 10),

-- -- Emergency order (no discount)
-- (8, 50, 8.0, 1.5000, 0.0, 11),
-- (9, 10, 8.0, 12.0000, 0.0, 11),

-- -- Seasonal sale items
-- (8, 20, 8.0, 4.5000, 50.0, 12),
-- (9, 5, 8.0, 18.0000, 40.0, 12),
-- (10, 3, 18.0, 12.0000, 30.0, 12);


-- -- Insert dummy data for ordered_item table referencing placed_order (IDs 38-74)
-- INSERT INTO `verdelia`.`ordered_item` (
--   `ordered_product_id`,
--   `ordered_quantity`,
--   `applied_vat`,
--   `order_ref`,
--   `unit_price`,
--   `product_discount`,
--   `ordered_item_cart_ref`
-- ) VALUES
-- -- Order 38: Blood test supplies order
-- (8, 10, 8.0, 38, 1.5000, 10.0, NULL),    -- Blood Collection Tubes
-- (8, 20, 8.0, 38, 0.7500, 15.0, NULL),    -- Sterile Needles
-- (8, 30, 8.0, 38, 0.2500, 0.0, NULL),     -- Alcohol Swabs
-- (9, 5, 8.0, 38, 8.0000, 20.0, NULL),     -- Fasting Blood Test Kits

-- -- Order 39: Imaging supplies order
-- (11, 5, 18.0, 39, 8.0000, 5.0, NULL),    -- X-Ray Films
-- (10, 2, 18.0, 39, 45.0000, 15.0, NULL),  -- Lead Aprons
-- (9, 3, 18.0, 39, 35.0000, 10.0, NULL),   -- Contrast Media

-- -- Order 40: Vaccination supplies
-- (9, 25, 5.0, 40, 18.0000, 25.0, NULL),   -- Flu Vaccines
-- (8, 30, 5.0, 40, 0.8500, 20.0, NULL),    -- Syringes with Needles
-- (10, 5, 5.0, 40, 3.5000, 10.0, NULL),    -- Sharps Containers

-- -- Order 41: Dental supplies package
-- (8, 25, 18.0, 41, 4.5000, 15.0, NULL),   -- Dental Prophy Paste
-- (8, 30, 18.0, 41, 2.7500, 10.0, NULL),   -- Disposable Prophy Angles
-- (8, 50, 18.0, 41, 0.5000, 5.0, NULL),    -- Dental Floss

-- -- Order 42: Dental equipment order
-- (8, 10, 18.0, 42, 15.0000, 20.0, NULL),  -- Dental Composite
-- (11, 1, 18.0, 42, 250.0000, 25.0, NULL), -- Curing Light
-- (10, 2, 18.0, 42, 12.0000, 15.0, NULL),  -- Lead Thyroid Collars

-- -- Order 43: Lab pathology supplies
-- (9, 10, 8.0, 43, 25.0000, 20.0, NULL),   -- Staining Reagents
-- (8, 100, 8.0, 43, 0.8000, 30.0, NULL),   -- Histology Slides
-- (NULL, 30, 8.0, 43, 2.5000, 10.0, NULL), -- Biopsy Cassettes

-- -- Order 44: Urine test supplies bulk
-- (8, 50, 8.0, 44, 0.8500, 25.0, NULL),    -- Urine Collection Cups
-- (9, 50, 8.0, 44, 2.2500, 20.0, NULL),    -- Urine Test Strips
-- (9, 20, 8.0, 44, 4.5000, 15.0, NULL),    -- Culture Media Plates

-- -- Order 45: Allergy testing supplies
-- (9, 100, 8.0, 45, 0.9500, 30.0, NULL),   -- Allergen Extracts
-- (8, 120, 8.0, 45, 0.1500, 35.0, NULL),   -- Skin Test Lancets
-- (NULL, 10, 8.0, 45, 3.5000, 0.0, NULL),  -- Measuring Rulers

-- -- Order 46: Genetic testing order
-- (9, 5, 8.0, 46, 350.0000, 25.0, NULL),   -- Carrier Screening Kits
-- (NULL, 3, 8.0, 46, 99.0000, 30.0, NULL), -- Ancestry DNA Kits
-- (10, 1, 8.0, 46, 25.0000, 15.0, NULL),   -- Software Subscription

-- -- Order 47: Physiotherapy equipment
-- (10, 3, 18.0, 47, 25.0000, 20.0, NULL),  -- Blood Pressure Cuffs
-- (10, 2, 18.0, 47, 35.0000, 15.0, NULL),  -- Stethoscopes
-- (10, 1, 18.0, 47, 85.0000, 25.0, NULL),  -- Otoscope/Ophthalmoscope Set

-- -- Order 48: Sports medicine equipment
-- (10, 2, 18.0, 48, 45.0000, 20.0, NULL),  -- Fall Risk Assessment Kits
-- (10, 5, 18.0, 48, 8.5000, 15.0, NULL),   -- Reflex Hammers
-- (11, 1, 18.0, 48, 150.0000, 30.0, NULL), -- Bone Density Calibration

-- -- Order 49: COVID supplies (zero VAT)
-- (8, 100, 0.0, 49, 4.5000, 0.0, NULL),    -- PPE Kits
-- (NULL, 200, 0.0, 49, 1.0000, 0.0, NULL), -- Vaccination Certificates
-- (8, 50, 0.0, 49, 0.8500, 0.0, NULL),     -- Syringes

-- -- Order 50: Travel medicine package
-- (9, 10, 5.0, 50, 40.0000, 20.0, NULL),   -- Travel Vaccines
-- (NULL, 5, 5.0, 50, 5.0000, 10.0, NULL),  -- International Certificates
-- (NULL, 10, 5.0, 50, 2.5000, 15.0, NULL), -- Travel Health Guides

-- -- Order 51: Single product bulk order
-- (8, 500, 8.0, 51, 0.7500, 50.0, NULL),   -- Sterile Needles (bulk)

-- -- Order 52: Mixed medical supplies
-- (9, 8, 8.0, 52, 12.0000, 20.0, NULL),    -- Liver Function Reagents
-- (8, 50, 8.0, 52, 1.5000, 25.0, NULL),    -- Blood Collection Tubes
-- (9, 3, 18.0, 52, 85.0000, 30.0, NULL),   -- MRI Contrast Agent

-- -- Order 53: Dental X-ray supplies
-- (8, 40, 18.0, 53, 1.2500, 20.0, NULL),   -- Digital Sensor Covers
-- (10, 3, 18.0, 53, 12.0000, 15.0, NULL),  -- Lead Thyroid Collars
-- (NULL, 20, 18.0, 53, 0.7500, 10.0, NULL),-- Bitewing Tabs

-- -- Order 54: Emergency order (no discounts)
-- (8, 25, 8.0, 54, 1.5000, 0.0, NULL),     -- Blood Tubes
-- (9, 5, 8.0, 54, 12.0000, 0.0, NULL),     -- Liver Reagents
-- (8, 10, 8.0, 54, 0.2500, 0.0, NULL),     -- Alcohol Swabs

-- -- Order 55: Seasonal flu prevention
-- (9, 50, 5.0, 55, 18.0000, 35.0, NULL),   -- Flu Vaccines
-- (8, 60, 5.0, 55, 0.8500, 30.0, NULL),    -- Syringes
-- (10, 8, 5.0, 55, 3.5000, 20.0, NULL),    -- Sharps Containers

-- -- Order 56: Hospital equipment order
-- (11, 3, 23.0, 56, 250.0000, 40.0, NULL), -- Curing Lights
-- (10, 5, 23.0, 56, 85.0000, 35.0, NULL),  -- Otoscope Sets
-- (11, 2, 23.0, 56, 150.0000, 30.0, NULL), -- Bone Density Equipment

-- -- Order 57: Small clinic order
-- (8, 15, 8.0, 57, 4.5000, 10.0, NULL),    -- Dental Paste
-- (9, 5, 8.0, 57, 8.0000, 15.0, NULL),     -- Test Kits
-- (8, 20, 8.0, 57, 0.5000, 5.0, NULL),     -- Dental Floss

-- -- Order 58: Wholesale needles
-- (8, 1000, 8.0, 58, 0.7500, 60.0, NULL),  -- Sterile Needles (wholesale)

-- -- Order 59: Test strips bulk
-- (9, 200, 8.0, 59, 2.2500, 55.0, NULL),   -- Urine Test Strips

-- -- Order 60: Mixed VAT order
-- (8, 20, 8.0, 60, 1.5000, 15.0, NULL),    -- Blood Tubes (8% VAT)
-- (9, 5, 18.0, 60, 35.0000, 20.0, NULL),   -- Contrast Media (18% VAT)
-- (11, 1, 23.0, 60, 250.0000, 25.0, NULL), -- Equipment (23% VAT)

-- -- Order 61: Single item order
-- (10, 1, 18.0, 61, 35.0000, 10.0, NULL),  -- Single Stethoscope

-- -- Order 62: Two items order
-- (8, 10, 8.0, 62, 0.8500, 15.0, NULL),    -- Syringes
-- (9, 2, 8.0, 62, 25.0000, 20.0, NULL),    -- Staining Reagents

-- -- Order 63: Free medical supplies (zero cost)
-- (8, 50, 0.0, 63, 0.0000, 100.0, NULL),   -- Donated supplies
-- (9, 10, 0.0, 63, 0.0000, 100.0, NULL),   -- Donated test kits

-- -- Order 64: High-value equipment
-- (11, 2, 23.0, 64, 1200.0000, 35.0, NULL),-- Advanced Imaging Equipment
-- (10, 3, 23.0, 64, 450.0000, 30.0, NULL), -- Specialized Medical Devices

-- -- Order 65: Regular restocking order
-- (8, 100, 8.0, 65, 1.5000, 25.0, NULL),   -- Blood Tubes
-- (8, 200, 8.0, 65, 0.7500, 30.0, NULL),   -- Needles
-- (8, 300, 8.0, 65, 0.2500, 20.0, NULL),   -- Alcohol Swabs

-- -- Order 66: Lab chemicals order
-- (9, 15, 8.0, 66, 12.0000, 20.0, NULL),   -- Liver Reagents
-- (9, 8, 8.0, 66, 25.0000, 25.0, NULL),    -- Thyroid Kits
-- (9, 20, 8.0, 66, 2.2500, 30.0, NULL),    -- Test Strips

-- -- Order 67: Dental monthly supply
-- (8, 40, 18.0, 67, 4.5000, 20.0, NULL),   -- Dental Paste
-- (8, 60, 18.0, 67, 2.7500, 15.0, NULL),   -- Prophy Angles
-- (8, 80, 18.0, 67, 1.2500, 10.0, NULL),   -- Sensor Covers

-- -- Order 68: Vaccination campaign
-- (9, 200, 5.0, 68, 18.0000, 40.0, NULL),  -- Flu Vaccines
-- (8, 250, 5.0, 68, 0.8500, 35.0, NULL),   -- Syringes
-- (10, 15, 5.0, 68, 3.5000, 25.0, NULL);



-- Insert dummy data for invoice table
-- INSERT INTO `verdelia`.`invoice` (
--   `invoice_cart_id`,
--   `invoice_number`,
--   `invoice_total_amount`,
--   `invoice_status`,
--   `invoice_issue_date`,
--   `invoice_due_date`,
--   `invoice_notes`
-- ) VALUES
-- -- Cart 1: Blood tests (Paid)
-- (1, 'INV-2024-001', 85.5000, 'paid', '2024-01-15', '2024-02-15', 'Complete blood work invoice - includes CBC, Lipid Profile, Glucose Test'),

-- -- Cart 2: Follow-up tests (Paid)
-- (2, 'INV-2024-002', 120.0000, 'paid', '2024-01-16', '2024-02-16', 'Follow-up liver and thyroid function tests'),

-- -- Cart 3: Family blood work (Paid)
-- (3, 'INV-2024-003', 220.7500, 'paid', '2024-01-17', '2024-02-17', 'Family blood tests package - 2 persons'),

-- -- Cart 4: Annual tests (Paid)
-- (4, 'INV-2024-004', 95.2500, 'paid', '2024-01-18', '2024-02-18', 'Annual health screening tests'),

-- -- Cart 5: Basic tests (Paid)
-- (5, 'INV-2024-005', 65.0000, 'paid', '2024-01-19', '2024-02-19', 'Basic CBC and glucose screening'),

-- -- Cart 6: Imaging - X-ray & Ultrasound (Paid)
-- (6, 'INV-2024-006', 180.5000, 'paid', '2024-01-20', '2024-02-20', 'Chest X-ray and abdominal ultrasound'),

-- -- Cart 7: Advanced imaging (Paid)
-- (7, 'INV-2024-007', 420.5000, 'paid', '2024-01-21', '2024-02-21', 'Brain MRI and CT scan package'),

-- -- Cart 8: Pre-employment screening (Paid)
-- (8, 'INV-2024-008', 150.0000, 'paid', '2024-01-22', '2024-02-22', 'Pre-employment medical tests'),

-- -- Cart 9: Neurological assessment (Paid)
-- (9, 'INV-2024-009', 280.0000, 'paid', '2024-01-23', '2024-02-23', 'Neurological MRI scan'),

-- -- Cart 10: Lung assessment (Paid)
-- (10, 'INV-2024-010', 240.0000, 'paid', '2024-01-24', '2024-02-24', 'CT scan for lung nodule follow-up'),

-- -- Cart 11: Vaccinations (Paid)
-- (11, 'INV-2024-011', 25.0000, 'paid', '2024-01-25', '2024-02-25', 'Annual flu vaccination'),

-- -- Cart 12: Travel vaccinations (Paid)
-- (12, 'INV-2024-012', 300.0000, 'paid', '2024-01-26', '2024-02-26', 'Travel vaccination package'),

-- -- Cart 13: Family vaccinations (Paid)
-- (13, 'INV-2024-013', 50.0000, 'paid', '2024-01-27', '2024-02-27', 'Family flu shots'),

-- -- Cart 14: Business travel (Paid)
-- (14, 'INV-2024-014', 120.0000, 'paid', '2024-01-28', '2024-02-28', 'Business travel vaccinations'),

-- -- Cart 15: HPV vaccination (Paid)
-- (15, 'INV-2024-015', 540.0000, 'paid', '2024-01-29', '2024-02-29', 'Complete HPV vaccination series (3 doses)'),

-- -- Cart 16: Executive health (Paid)
-- (16, 'INV-2024-016', 480.0000, 'paid', '2024-01-30', '2024-03-01', 'Executive health screening package'),

-- -- Cart 17: Annual physical (Unpaid)
-- (17, 'INV-2024-017', 280.0000, 'unpaid', '2024-02-01', '2024-03-01', 'Annual physical exam + elderly parent assessment'),

-- -- Cart 18: Corporate executive (Paid)
-- (18, 'INV-2024-018', 400.0000, 'paid', '2024-02-02', '2024-03-02', 'Corporate executive health checkup'),

-- -- Cart 19: Family physicals (Unpaid)
-- (19, 'INV-2024-019', 160.0000, 'unpaid', '2024-02-03', '2024-03-03', 'Family physical examinations (2 persons)'),

-- -- Cart 20: Geriatric assessment (Paid)
-- (20, 'INV-2024-020', 200.0000, 'paid', '2024-02-04', '2024-03-04', 'Geriatric health assessment'),

-- -- Cart 21: Dental cleaning (Paid)
-- (21, 'INV-2024-021', 105.0000, 'paid', '2024-02-05', '2024-03-05', 'Teeth cleaning with X-rays'),

-- -- Cart 22: Dental fillings (Paid)
-- (22, 'INV-2024-022', 265.0000, 'paid', '2024-02-06', '2024-03-06', 'Two dental fillings with cleaning'),

-- -- Cart 23: Routine dental X-rays (Paid)
-- (23, 'INV-2024-023', 40.0000, 'paid', '2024-02-07', '2024-03-07', 'Routine dental X-rays'),

-- -- Cart 24: 6-month cleaning (Paid)
-- (24, 'INV-2024-024', 65.0000, 'paid', '2024-02-08', '2024-03-08', '6-month dental cleaning'),

-- -- Cart 25: Single filling (Unpaid)
-- (25, 'INV-2024-025', 100.0000, 'unpaid', '2024-02-09', '2024-03-09', 'Single cavity filling'),

-- -- Cart 26: Pathology tests (Paid)
-- (26, 'INV-2024-026', 205.0000, 'paid', '2024-02-10', '2024-03-10', 'Skin biopsy and pap smear tests'),

-- -- Cart 27: Mole biopsy (Paid)
-- (27, 'INV-2024-027', 160.0000, 'paid', '2024-02-11', '2024-03-11', 'Mole biopsy analysis'),

-- -- Cart 28: Gynecological screening (Paid)
-- (28, 'INV-2024-028', 45.0000, 'paid', '2024-02-12', '2024-03-12', 'Annual gynecological pap smear'),

-- -- Cart 29: UTI tests (Paid)
-- (29, 'INV-2024-029', 56.0000, 'paid', '2024-02-13', '2024-03-13', 'Urinalysis and urine culture for UTI'),

-- -- Cart 30: Drug screening (Unpaid)
-- (30, 'INV-2024-030', 20.0000, 'unpaid', '2024-02-14', '2024-03-14', 'Pre-employment drug screening'),

-- -- Cart 31: Allergy testing (Paid)
-- (31, 'INV-2024-031', 270.0000, 'paid', '2024-02-15', '2024-03-15', 'Allergy skin testing and food panel'),

-- -- Cart 32: Genetic testing (Paid)
-- (32, 'INV-2024-032', 379.0000, 'paid', '2024-02-16', '2024-03-16', 'Genetic carrier screening and ancestry test'),

-- -- Cart 33: Physiotherapy (Unpaid)
-- (33, 'INV-2024-033', 255.0000, 'unpaid', '2024-02-17', '2024-03-17', 'Physiotherapy assessment + 3 massage sessions'),

-- -- Cart 34: Nutrition & weight (Paid)
-- (34, 'INV-2024-034', 585.0000, 'paid', '2024-02-18', '2024-03-18', 'Nutrition consultation + weight management program'),

-- -- Cart 35: Therapy package (Unpaid)
-- (35, 'INV-2024-035', 530.0000, 'unpaid', '2024-02-19', '2024-03-19', '4 therapy sessions + couples counseling'),

-- -- Cart 36: Acupuncture (Paid)
-- (36, 'INV-2024-036', 215.0000, 'paid', '2024-02-20', '2024-03-20', '2 acupuncture sessions + electro-acupuncture'),

-- -- Cart 37: Prenatal care (Paid)
-- (37, 'INV-2024-037', 280.0000, 'paid', '2024-02-21', '2024-03-21', 'First trimester ultrasound + prenatal blood work'),

-- -- Cart 38: Pediatric care (Paid)
-- (38, 'INV-2024-038', 165.0000, 'paid', '2024-02-22', '2024-03-22', 'Well-baby checkup + child development assessment'),

-- -- Cart 39: Geriatric care (Unpaid)
-- (39, 'INV-2024-039', 215.0000, 'unpaid', '2024-02-23', '2024-03-23', 'Geriatric assessment + fall risk evaluation'),

-- -- Cart 40: Sports medicine (Paid)
-- (40, 'INV-2024-040', 230.0000, 'paid', '2024-02-24', '2024-03-24', 'Sports injury evaluation + performance consultation'),

-- -- Cart 41: Single tests (Paid)
-- (41, 'INV-2024-041', 45.0000, 'paid', '2024-02-25', '2024-03-25', 'Single blood test + flu shot'),

-- -- Cart 42: Dental + flu (Canceled)
-- (42, 'INV-2024-042', 130.0000, 'canceled', '2024-02-26', '2024-03-26', 'Dental cleaning with X-rays + flu vaccination - Patient canceled');


-- More invoices for comprehensive coverage
-- INSERT INTO `verdelia`.`invoice` (
--   `invoice_cart_id`,
--   `invoice_number`,
--   `invoice_total_amount`,
--   `invoice_status`,
--   `invoice_issue_date`,
--   `invoice_due_date`,
--   `invoice_notes`
-- ) VALUES
-- -- Past due invoices
-- (17, 'INV-2024-043', 280.0000, 'unpaid', '2024-01-15', '2024-02-15', 'PAST DUE - Annual physical exam'),
-- (19, 'INV-2024-044', 160.0000, 'unpaid', '2024-01-20', '2024-02-20', 'PAST DUE - Family physical exams'),
-- (25, 'INV-2024-045', 100.0000, 'unpaid', '2024-01-25', '2024-02-25', 'PAST DUE - Dental filling'),

-- -- Partially paid invoices (treated as unpaid since status is binary)
-- (30, 'INV-2024-046', 20.0000, 'unpaid', '2024-02-10', '2024-03-10', 'Partially paid - balance due $5.00'),
-- (33, 'INV-2024-047', 255.0000, 'unpaid', '2024-02-12', '2024-03-12', 'Payment plan arranged - first payment received'),

-- -- Bulk/wholesale invoices
-- (5, 'INV-2024-048', 650.0000, 'paid', '2024-02-01', '2024-03-01', 'Corporate bulk order - 10 employee screenings'),
-- (11, 'INV-2024-049', 250.0000, 'paid', '2024-02-05', '2024-03-05', 'Company flu vaccination program - 10 employees'),

-- -- Insurance pending invoices
-- (35, 'INV-2024-050', 530.0000, 'unpaid', '2024-02-15', '2024-03-15', 'Awaiting insurance approval'),
-- (39, 'INV-2024-051', 215.0000, 'unpaid', '2024-02-18', '2024-03-18', 'Insurance claim submitted'),

-- -- Zero amount invoices (free services)
-- (11, 'INV-2024-052', 0.0000, 'paid', '2024-02-20', '2024-03-20', 'Free COVID-19 vaccination - government funded'),

-- -- Refunded invoices (canceled status)
-- (42, 'INV-2024-053', 130.0000, 'canceled', '2024-02-22', '2024-03-22', 'Refund issued - patient switched providers'),

-- -- Recent invoices (current month)
-- (17, 'INV-2024-054', 280.0000, 'unpaid', CURDATE(), DATE_ADD(CURDATE(), INTERVAL 30 DAY), 'Current month invoice - sent today'),
-- (25, 'INV-2024-055', 100.0000, 'unpaid', CURDATE(), DATE_ADD(CURDATE(), INTERVAL 30 DAY), 'Current dental work invoice'),

-- -- Overdue invoices (more than 30 days past due)
-- (30, 'INV-2024-056', 20.0000, 'unpaid', '2023-12-15', '2024-01-15', 'OVERDUE - 60+ days past due'),
-- (33, 'INV-2024-057', 255.0000, 'unpaid', '2023-12-20', '2024-01-20', 'OVERDUE - Collections notified'),

-- -- Quarterly invoices
-- (16, 'INV-2024-058', 1440.0000, 'paid', '2024-01-01', '2024-01-31', 'Q1 Corporate executive health package - 3 employees'),
-- (16, 'INV-2024-059', 1440.0000, 'paid', '2024-04-01', '2024-04-30', 'Q2 Corporate executive health package'),
-- (16, 'INV-2024-060', 1440.0000, 'unpaid', '2024-07-01', '2024-07-31', 'Q3 Corporate executive health package - pending');

-- First, create payments (some with invoice references)
-- INSERT INTO `verdelia`.`payment` (
--   `payment_invoice_id`,
--   `payment_amount`,
--   `payment_method`,
--   `payment_status`,
--   `payment_reference`,
--   `payment_notes`
-- ) VALUES
-- -- Full payments for invoices
-- (1, 85.5000, 'card', 'completed', 'TXN-00123456', 'Credit card payment - Visa ending 4321'),
-- (2, 120.0000, 'bank', 'completed', 'BANK-78901234', 'Bank transfer - Ref: INV-2024-002'),
-- (3, 220.7500, 'card', 'completed', 'TXN-56789012', 'Debit card payment - Mastercard'),
-- (4, 95.2500, 'mobile', 'completed', 'MOB-34567890', 'Mobile payment via Apple Pay'),
-- (5, 65.0000, 'cash', 'completed', 'CASH-001', 'Cash payment at counter'),
-- (6, 180.5000, 'card', 'completed', 'TXN-90123456', 'Credit card payment - Amex'),
-- (7, 420.5000, 'bank', 'completed', 'BANK-12345678', 'Corporate bank transfer'),
-- (8, 150.0000, 'card', 'completed', 'TXN-23456789', 'Debit card - company account'),
-- (9, 280.0000, 'bank', 'completed', 'BANK-87654321', 'Insurance direct deposit'),
-- (10, 240.0000, 'card', 'completed', 'TXN-34567890', 'Health savings account card'),

-- -- Partial payments (for unpaid invoices)
-- (17, 140.0000, 'card', 'completed', 'TXN-45678901', 'Partial payment - 50% of total'),
-- (19, 80.0000, 'cash', 'completed', 'CASH-002', 'Partial cash payment - family discount'),
-- (25, 50.0000, 'bank', 'completed', 'BANK-23456789', 'Deposit for dental work'),

-- -- Payments for other invoices
-- (11, 25.0000, 'card', 'completed', 'TXN-56789012', 'Flu shot payment'),
-- (12, 300.0000, 'bank', 'completed', 'BANK-34567890', 'Travel clinic payment'),
-- (13, 50.0000, 'mobile', 'completed', 'MOB-45678901', 'Family vaccination mobile payment'),
-- (14, 120.0000, 'card', 'completed', 'TXN-67890123', 'Business expense card'),
-- (15, 180.0000, 'bank', 'completed', 'BANK-45678901', 'First dose HPV vaccine payment'),
-- (16, 480.0000, 'bank', 'completed', 'BANK-56789012', 'Corporate executive package'),

-- -- More payments with different statuses
-- (20, 200.0000, 'card', 'completed', 'TXN-78901234', 'Geriatric assessment - senior discount applied'),
-- (21, 105.0000, 'cash', 'completed', 'CASH-003', 'Dental cleaning payment'),
-- (22, 265.0000, 'card', 'completed', 'TXN-89012345', 'Dental fillings - insurance co-pay'),
-- (23, 40.0000, 'mobile', 'completed', 'MOB-56789012', 'Dental X-ray mobile payment'),
-- (24, 65.0000, 'card', 'completed', 'TXN-90123456', 'Regular cleaning payment'),

-- -- Failed/refunded payments
-- (42, 130.0000, 'card', 'refunded', 'TXN-REF-12345', 'Refund processed - patient canceled'),
-- (NULL, 45.0000, 'card', 'failed', 'TXN-FAIL-001', 'Payment declined - insufficient funds'),
-- (NULL, 100.0000, 'bank', 'pending', 'BANK-PEND-001', 'Bank transfer initiated - pending confirmation'),

-- -- Payments without invoice reference (direct cart payments)
-- (NULL, 75.0000, 'cash', 'completed', 'CASH-004', 'Direct payment for consultation'),
-- (NULL, 120.0000, 'card', 'completed', 'TXN-01234567', 'Direct card payment for tests'),
-- (NULL, 200.0000, 'bank', 'completed', 'BANK-67890123', 'Direct bank transfer for services');

-- -- Now create receipts (some with payment references, some without)
-- INSERT INTO `verdelia`.`receipt` (
--   `receipt_payment_id`,
--   `receipt_number`,
--   `receipt_amount`,
--   `receipt_notes`,
--   `receipt_cart_ref`
-- ) VALUES
-- -- Receipts with payment references (full payments)
-- (1, 'RCPT-2024-001', 85.5000, 'Receipt for blood work payment - Card TXN-00123456', 1),
-- (2, 'RCPT-2024-002', 120.0000, 'Receipt for follow-up tests - Bank transfer', 2),
-- (3, 'RCPT-2024-003', 220.7500, 'Family blood tests receipt - Paid in full', 3),
-- (4, 'RCPT-2024-004', 95.2500, 'Annual screening receipt - Mobile payment', 4),
-- (5, 'RCPT-2024-005', 65.0000, 'Basic tests receipt - Cash payment', 5),

-- -- Receipts for partial payments
-- (11, 'RCPT-2024-011', 140.0000, 'Partial payment receipt - Balance due: $140.00', 17),
-- (12, 'RCPT-2024-012', 80.0000, 'Family discount applied - Balance: $80.00', 19),
-- (13, 'RCPT-2024-013', 50.0000, 'Dental deposit receipt - Balance due: $50.00', 25),

-- -- Receipts without payment references (cash receipts)
-- (NULL, 'RCPT-2024-021', 180.5000, 'Cash receipt for imaging services - No payment record', 6),
-- (NULL, 'RCPT-2024-022', 420.5000, 'Receipt for advanced imaging - Paid by check', 7),
-- (NULL, 'RCPT-2024-023', 150.0000, 'Pre-employment screening receipt', 8),

-- -- More receipts with payments
-- (6, 'RCPT-2024-024', 180.5000, 'Imaging services - Card payment', 6),
-- (7, 'RCPT-2024-025', 420.5000, 'Advanced imaging - Corporate payment', 7),
-- (8, 'RCPT-2024-026', 150.0000, 'Pre-employment screening - Company card', 8),

-- -- Receipts for other services
-- (9, 'RCPT-2024-027', 280.0000, 'MRI scan receipt - Insurance covered', 9),
-- (10, 'RCPT-2024-028', 240.0000, 'CT scan receipt - HSA payment', 10),
-- (14, 'RCPT-2024-029', 120.0000, 'Travel clinic receipt - Business expense', 14),

-- -- Refund receipt
-- (22, 'RCPT-2024-030', 130.0000, 'REFUND RECEIPT - Services canceled', 42),

-- -- Direct cart receipts (no payment reference)
-- (NULL, 'RCPT-2024-031', 25.0000, 'Flu shot receipt - Paid at clinic', 11),
-- (NULL, 'RCPT-2024-032', 300.0000, 'Travel vaccinations receipt', 12),
-- (NULL, 'RCPT-2024-033', 50.0000, 'Family vaccinations receipt', 13);


-- -- Now create deposits (some with receipts, some without)
-- INSERT INTO `verdelia`.`deposit` (
--   `deposit_cart_id`,
--   `deposit_invoice_id`,
--   `deposit_amount`,
--   `deposit_method`,
--   `deposit_reference`,
--   `deposit_notes`,
--   `deposit_receipt_id`
-- ) VALUES

-- -- Deposits with receipts (full payment scenario)
-- (1, 1, 85.5000, 'card', 'DEP-TXN-001', 'Full deposit for blood work', 1),
-- (2, 2, 120.0000, 'bank', 'DEP-BANK-001', 'Full deposit for follow-up tests', 2),
-- (3, 3, 220.7500, 'card', 'DEP-TXN-002', 'Full deposit for family tests', 3),
-- -- Partial deposits (for unpaid invoices)
-- (17, 17, 140.0000, 'card', 'DEP-TXN-003', '50% deposit for annual physical', 11),
-- (19, 19, 80.0000, 'cash', 'DEP-CASH-001', '50% deposit for family exams', 12),
-- (25, 25, 50.0000, 'bank', 'DEP-BANK-002', '50% deposit for dental work', 13),





-- -- Deposits without receipts
-- (6, 6, 90.2500, 'cash', 'DEP-CASH-002', '50% deposit for imaging services', NULL),
-- (7, 7, 210.2500, 'bank', 'DEP-BANK-003', '50% deposit for advanced imaging', NULL),
-- (33, 33, 127.5000, 'card', 'DEP-TXN-004', '50% deposit for physiotherapy', NULL),

-- -- Deposits for future services (no invoice yet)
-- (35, NULL, 265.0000, 'card', 'DEP-TXN-005', 'Advance deposit for therapy package', NULL),
-- (39, NULL, 107.5000, 'cash', 'DEP-CASH-003', 'Deposit for geriatric assessment', NULL),

-- -- Multiple deposits for same cart/invoice
-- (16, 16, 240.0000, 'bank', 'DEP-BANK-004', 'First deposit for executive package', NULL),
-- (16, 16, 240.0000, 'bank', 'DEP-BANK-005', 'Second deposit for executive package', NULL);


-- -- Deposit with receipt but no invoice (direct service booking)
-- (22, NULL, 132.5000, 'card', 'DEP-TXN-006', 'Deposit for dental fillings', 21),
-- (21, NULL, 135.0000, 'bank', 'DEP-BANK-006', 'Deposit for allergy testing', NULL),

-- -- Small deposits
-- (11, 11, 12.5000, 'cash', 'DEP-CASH-004', 'Token deposit for flu shot', NULL),
-- (23, 23, 20.0000, 'mobile', 'DEP-MOB-001', 'Deposit for dental X-rays', NULL),

-- -- Large/corporate deposits
-- (16, 16, 480.0000, 'bank', 'DEP-BANK-007', 'Corporate bulk deposit - 10 employees', NULL),
-- (34, 34, 292.5000, 'bank', 'DEP-BANK-008', '50% deposit for weight management program', NULL),

-- -- Refunded deposit
-- (42, 42, 130.0000, 'card', 'DEP-REF-001', 'DEPOSIT REFUNDED - Services canceled', 20),

-- -- Recent deposits
-- (17, 17, 70.0000, 'card', 'DEP-TXN-007', 'Additional deposit for balance', NULL),
-- (25, 25, 25.0000, 'cash', 'DEP-CASH-005', 'Additional dental deposit', NULL),

-- -- Deposit without cart reference
-- (NULL, 20, 100.0000, 'bank', 'DEP-BANK-009', 'Deposit against invoice - cart not specified', NULL),
-- (NULL, 21, 52.5000, 'card', 'DEP-TXN-008', 'Partial deposit - cart unknown', NULL);

-- select * from app_user;
desc app_user ;
insert into app_user (id_app_user,
app_user_name,
app_user_password,
app_user_type,
app_user_preferences,
app_user_image_url,
app_user_last_active,
app_user_last_updated,
app_user_creation)
values
(4, 'admin', '77b23d5396b51608e7189cf8895bd283c88639db5ed6211fa8bfbaecf477409f',  "admin",NULL , NULL , '2025-12-10 08:01:27', '2025-12-10 08:01:27', '2025-12-10 08:01:27' );


INSERT INTO `verdelia`.`management_rule` (
  `rule_ref_org`,
  `rule_ref_provider`,
  `rule_ref_user`,
  `management_rule_code`,
  `management_rule_status`,
  `management_rule_expiry`
) VALUES
-- Provider 1: Magasin habibou sans gluten (Bakery)
(NULL, 1, 4, 63, 'PENDING', DATE_ADD(NOW(), INTERVAL 30 DAY)),

-- Provider 2: Uno (Supermarket)
(NULL, 2, 4, 63, 'ACTIVE', DATE_ADD(NOW(), INTERVAL 60 DAY)),

-- Provider 3: Superette université (Supermarket)
(NULL, 3, 4, 63, 'PENDING', DATE_ADD(NOW(), INTERVAL 45 DAY)),

-- Provider 4: Corridors Shopping (Restaurant)
(NULL, 4, 4, 63, 'REJECTED', DATE_ADD(NOW(), INTERVAL 90 DAY)),

-- Provider 5: Caramel sans gluten (Supermarket)
(NULL, 5, 4, 63, 'SUSPENDED', DATE_ADD(NOW(), INTERVAL 15 DAY)),

-- Provider 6: Magasin habibou sans gluten (Bakery - duplicate name but different ID)
(NULL, 6, 4, 63, 'ACTIVE', DATE_ADD(NOW(), INTERVAL 180 DAY)),

-- Provider 7: Uno (Supermarket - duplicate name but different ID)
(NULL, 7, 4, 63, 'OBSOLETE', DATE_ADD(NOW(), INTERVAL 7 DAY));

-- Optional: Insert more variations with different statuses for testing
INSERT INTO `verdelia`.`management_rule` (
  `rule_ref_org`,
  `rule_ref_provider`,
  `rule_ref_user`,
  `management_rule_code`,
  `management_rule_status`,
  `management_rule_expiry`
) VALUES
-- Additional rules with different expiry dates
(NULL, 1, 4, 63, 'ACTIVE', DATE_ADD(NOW(), INTERVAL 365 DAY)),  -- 1 year expiry
(NULL, 2, 4, 63, 'PENDING', NULL),  -- No expiry date
(NULL, 3, 4, 63, 'ACTIVE', DATE_ADD(NOW(), INTERVAL -7 DAY)),  -- Already expired
(NULL, 4, 4, 63, 'SUSPENDED', DATE_ADD(NOW(), INTERVAL 30 DAY)),

-- Same provider, different rule codes for user 4
(NULL, 2, 4, 64, 'ACTIVE', DATE_ADD(NOW(), INTERVAL 90 DAY)),  -- Different rule code
(NULL, 2, 4, 65, 'PENDING', DATE_ADD(NOW(), INTERVAL 30 DAY)),  -- Another rule code

-- Same provider and rule code, different users (if you want to test with other users)
(NULL, 2, 1, 63, 'ACTIVE', DATE_ADD(NOW(), INTERVAL 60 DAY)),  -- User ID 1
(NULL, 2, 2, 63, 'ACTIVE', DATE_ADD(NOW(), INTERVAL 60 DAY)),  -- User ID 2
(NULL, 2, 3, 63, 'ACTIVE', DATE_ADD(NOW(), INTERVAL 60 DAY));  -- User ID 3



INSERT INTO `verdelia`.`ingredient` (ingredient_name) VALUES 
('Wheat'), 
('Barley'), 
('Rye'), 
('Oats');
INSERT INTO `verdelia`.`ingredient` (ingredient_name) VALUES 
('Corn'), 
('Rice'), 
('Soy'), 
('Milk');
INSERT INTO `verdelia`.`ingredient` (ingredient_name) VALUES 
('Egg'), 
('Peanuts'), 
('Tree Nuts'), 
('Fish');
INSERT INTO `verdelia`.`ingredient` (ingredient_name) VALUES 
('Shellfish'), 
('Lentils'), 
('Chickpeas'), 
('Buckwheat');
INSERT INTO `verdelia`.`ingredient` (ingredient_name) VALUES 
('Almond'), 
('Coconut'), 
('Sunflower Seeds');
INSERT INTO `verdelia`.`ingredient` (ingredient_name) VALUES 
('Pumpkin Seeds'), 
('Sesame Seeds'), 
('Potato'), 
('Sweet Potato');
INSERT INTO `verdelia`.`ingredient` (ingredient_name) VALUES 
('Gelatin'), 
('Lupin'), 
('Mustard');
INSERT INTO `verdelia`.`ingredient` (ingredient_name) VALUES 
('Fennel'), 
('Cumin');
INSERT INTO `verdelia`.`ingredient` (ingredient_name) VALUES 
('Ginger');
INSERT INTO `verdelia`.`ingredient` (ingredient_name) VALUES 
('Garlic');
INSERT INTO `verdelia`.`ingredient` (ingredient_name) VALUES 
('Onion');
INSERT INTO `verdelia`.`ingredient` (ingredient_name) VALUES 
('Leek'), 
('Shallot'), 
('Scallion'), 
('Chive'), 
('Parsley');
INSERT INTO `verdelia`.`ingredient` (ingredient_name) VALUES 
('Cilantro'), 
('Basil'), 
('Oregano'), 
('Thyme');
INSERT INTO `verdelia`.`ingredient` (ingredient_name) VALUES 
('Rosemary'), 
('Sage'), 
('Mint'), 
('Lemongrass');
INSERT INTO `verdelia`.`ingredient` (ingredient_name) VALUES 
('Lavender'), 
('Paprika'), 
('Chili Pepper'), 
('Black Pepper');
INSERT INTO `verdelia`.`ingredient` (ingredient_name) VALUES 
('White Pepper'), 
('Green Pepper'), 
('Red Pepper'), 
('Cinnamon'), 
('Allspice');
INSERT INTO `verdelia`.`ingredient` (ingredient_name) VALUES 
('Butter'), 
('Margarine'), 
('Vegetable Oil'), 
('Baking Powder');
INSERT INTO `verdelia`.`ingredient` (ingredient_name) VALUES 
('Baking Soda'), 
('Cornstarch'), 
('All-Purpose Flour');
INSERT INTO `verdelia`.`ingredient` (ingredient_name) VALUES  
('Pastry Flour'), 
('Self-Rising Flour'); 


update management_rule set management_rule_code = 16383 where id_management_rule >0;

select * from product_provider, provider_details where  idprovider_details_id=product_provider_details_id;

select * from product_provider ;



-- Person Details (base information for individuals)
INSERT INTO person_details (person_first_name, person_last_name, person_birth_date, person_gender, person_country_code, person_phone) VALUES
('Ahmed', 'Benali', '1985-03-15', 'MALE', '213', '+213551234567'),
('Fatima', 'Zohra', '1990-07-22', 'FEMALE', '213', '+213552345678'),
('Mohamed', 'Khelifa', '1978-11-08', 'MALE', '213', '+213553456789'),
('Nadia', 'Bensalem', '1995-01-30', 'FEMALE', '213', '+213554567890'),
('Karim', 'Mansouri', '1982-09-12', 'MALE', '213', '+213555678901'),
('Samira', 'Hadj', '1988-04-25', 'FEMALE', '213', '+213556789012'),
('Yacine', 'Meziane', '1992-12-03', 'MALE', '213', '+213557890123'),
('Leila', 'Boukadoum', '1980-06-18', 'FEMALE', '213', '+213558901234'),
('Rachid', 'Ferhat', '1975-10-10', 'MALE', '213', '+213559012345'),
('Amira', 'Saidi', '1998-08-07', 'FEMALE', '213', '+213560123456'),
('Hakim', 'Bouaziz', '1987-02-28', 'MALE', '213', '+213561234567'),
('Sofia', 'Khemiri', '1993-05-14', 'FEMALE', '213', '+213562345678'),
('Youcef', 'Lounis', '1970-11-20', 'MALE', '213', '+213563456789'),
('Meriem', 'Taleb', '1984-09-03', 'FEMALE', '213', '+213564567890'),
('Ali', 'Boukhelifa', '1991-07-19', 'MALE', '213', '+213565678901'),
('Djamila', 'Ouahab', '1976-12-25', 'FEMALE', '213', '+213566789012'),
('Nassim', 'Cherif', '1983-03-08', 'MALE', '213', '+213567890123'),
('Karima', 'Benaissa', '1989-06-30', 'FEMALE', '213', '+213568901234'),
('Slimane', 'Kaddour', '1972-08-15', 'MALE', '213', '+213569012345'),
('Zahra', 'Moussaoui', '1996-01-12', 'FEMALE', '213', '+213570123456'),
('Abdelkader', 'Benslimane', '1981-10-05', 'MALE', '213', '+213571234567'),
('Noura', 'Dahmani', '1986-04-22', 'FEMALE', '213', '+213572345678'),
('Fares', 'Boutaleb', '1994-11-11', 'MALE', '213', '+213573456789'),
('Hania', 'Zeroual', '1997-02-14', 'FEMALE', '213', '+213574567890'),
('Walid', 'Gherbi', '1979-05-28', 'MALE', '213', '+213575678901');

-- Persons (linking person_details to other entities)
-- Assuming person_details inserted with IDs from 1 to 25
INSERT INTO person (person_details_id, person_blood_type, person_location_id) VALUES
(1, "A+", NULL),   -- Ahmed Benali, A+
(2, "O+", NULL),   -- Fatima Zohra, O+
(3, "B+", NULL),   -- Mohamed Khelifa, B+
(4, "A+", NULL),   -- Nadia Bensalem, A+
(5, "AB+", NULL),   -- Karim Mansouri, AB+
(6, "O+", NULL),   -- Samira Hadj, O+
(7, "A+", NULL),   -- Yacine Meziane, A+
(8, "B+", NULL),   -- Leila Boukadoum, B+
(9, "AB+", NULL),   -- Rachid Ferhat, AB+
(10, "O+", NULL),  -- Amira Saidi, O+
(11, "A+", NULL),  -- Hakim Bouaziz, A+
(12, "B+", NULL),  -- Sofia Khemiri, B+
(13, "O+", NULL),  -- Youcef Lounis, O+
(14, "AB+", NULL),  -- Meriem Taleb, AB+
(15, "A+", NULL),  -- Ali Boukhelifa, A+
(16, "O+", NULL),  -- Djamila Ouahab, O+
(17, "B+", NULL),  -- Nassim Cherif, B+
(18, "A+", NULL),  -- Karima Benaissa, A+
(19, "AB+", NULL),  -- Slimane Kaddour, AB+
(20, "O+", NULL),  -- Zahra Moussaoui, O+
(21, "A+", NULL),  -- Abdelkader Benslimane, A+
(22, "B+", NULL),  -- Noura Dahmani, B+
(23, "O+", NULL),  -- Fares Boutaleb, O+
(24, "AB+", NULL),  -- Hania Zeroual, AB+
(25, "A+", NULL);  -- Walid Gherbi, A+


-- App Users (1-10: Regular Users, 11-15: Managers, 16-20: Admins)
INSERT INTO app_user (
    app_user_name, 
    app_user_password, 
    app_user_person_id, 
    app_user_type, 
    app_user_preferences, 
    app_user_image_url, 
    app_user_email, 
    app_user_wallet_id
) VALUES
-- Regular Users (type_id = 1)
('ahmed.benali', 'hashed_password_1', 1, "admin", '{"theme": "light", "language": "fr"}', 'https://randomuser.me/api/portraits/men/1.jpg', 'ahmed.benali@example.com', NULL),
('fatima.zohra', 'hashed_password_2', 2, "admin", '{"theme": "dark", "language": "ar"}', 'https://randomuser.me/api/portraits/women/1.jpg', 'fatima.zohra@example.com', NULL),
('mohamed.khelifa', 'hashed_password_3', 3, "admin", '{"theme": "light", "language": "en"}', 'https://randomuser.me/api/portraits/men/2.jpg', 'mohamed.khelifa@example.com', NULL),
('nadia.bensalem', 'hashed_password_4', 4, "admin", '{"theme": "dark", "language": "fr"}', 'https://randomuser.me/api/portraits/women/2.jpg', 'nadia.bensalem@example.com', NULL),
('karim.mansouri', 'hashed_password_5', 5, "admin", '{"theme": "light", "language": "ar"}', 'https://randomuser.me/api/portraits/men/3.jpg', 'karim.mansouri@example.com', NULL),
('samira.hadj', 'hashed_password_6', 6, "admin", '{"theme": "dark", "language": "en"}', 'https://randomuser.me/api/portraits/women/3.jpg', 'samira.hadj@example.com', NULL),
('yacine.meziane', 'hashed_password_7', 7, "admin", '{"theme": "light", "language": "fr"}', 'https://randomuser.me/api/portraits/men/4.jpg', 'yacine.meziane@example.com', NULL),
('leila.boukadoum', 'hashed_password_8', 8, "admin", '{"theme": "dark", "language": "ar"}', 'https://randomuser.me/api/portraits/women/4.jpg', 'leila.boukadoum@example.com', NULL),
('rachid.ferhat', 'hashed_password_9', 9, "admin", '{"theme": "light", "language": "en"}', 'https://randomuser.me/api/portraits/men/5.jpg', 'rachid.ferhat@example.com', NULL),
('amira.saidi', 'hashed_password_10', 10, "admin", '{"theme": "dark", "language": "fr"}', 'https://randomuser.me/api/portraits/women/5.jpg', 'amira.saidi@example.com', NULL),

-- Managers (type_id = 2)
('hakim.bouaziz', 'hashed_password_11', 11, "admin", '{"theme": "light", "language": "en", "dashboard": "admin"}', 'https://randomuser.me/api/portraits/men/6.jpg', 'hakim.bouaziz@management.com', NULL),
('sofia.khemiri', 'hashed_password_12', 12, "admin", '{"theme": "dark", "language": "fr", "dashboard": "admin"}', 'https://randomuser.me/api/portraits/women/6.jpg', 'sofia.khemiri@management.com', NULL),
('youcef.lounis', 'hashed_password_13', 13, "admin", '{"theme": "light", "language": "ar", "dashboard": "admin"}', 'https://randomuser.me/api/portraits/men/7.jpg', 'youcef.lounis@management.com', NULL),
('meriem.taleb', 'hashed_password_14', 14, "admin", '{"theme": "dark", "language": "en", "dashboard": "admin"}', 'https://randomuser.me/api/portraits/women/7.jpg', 'meriem.taleb@management.com', NULL),
('ali.boukhelifa', 'hashed_password_15', 15, "admin", '{"theme": "light", "language": "fr", "dashboard": "admin"}', 'https://randomuser.me/api/portraits/men/8.jpg', 'ali.boukhelifa@management.com', NULL),

-- Admins (type_id = 3)
('djamila.ouahab', 'hashed_password_16', 16, "admin", '{"theme": "dark", "language": "ar", "dashboard": "admin", "super_admin": true}', 'https://randomuser.me/api/portraits/women/8.jpg', 'djamila.ouahab@admin.com', NULL),
('nassim.cherif', 'hashed_password_17', 17, "admin", '{"theme": "light", "language": "en", "dashboard": "admin", "super_admin": true}', 'https://randomuser.me/api/portraits/men/9.jpg', 'nassim.cherif@admin.com', NULL),
('karima.benaissa', 'hashed_password_18', 18, "admin", '{"theme": "dark", "language": "fr", "dashboard": "admin", "super_admin": true}', 'https://randomuser.me/api/portraits/women/9.jpg', 'karima.benaissa@admin.com', NULL),
('slimane.kaddour', 'hashed_password_19', 19, "admin", '{"theme": "light", "language": "ar", "dashboard": "admin", "super_admin": true}', 'https://randomuser.me/api/portraits/men/10.jpg', 'slimane.kaddour@admin.com', NULL),
('zahra.moussaoui', 'hashed_password_20', 20, "admin", '{"theme": "dark", "language": "en", "dashboard": "admin", "super_admin": true}', 'https://randomuser.me/api/portraits/women/10.jpg', 'zahra.moussaoui@admin.com', NULL),

-- Additional regular users
('abdelkader.benslimane', 'hashed_password_21', 21, "admin", '{"theme": "light", "language": "fr"}', 'https://randomuser.me/api/portraits/men/11.jpg', 'abdelkader.benslimane@example.com', NULL),
('noura.dahmani', 'hashed_password_22', 22, "admin", '{"theme": "dark", "language": "ar"}', 'https://randomuser.me/api/portraits/women/11.jpg', 'noura.dahmani@example.com', NULL),
('fares.boutaleb', 'hashed_password_23', 23, "admin", '{"theme": "light", "language": "en"}', 'https://randomuser.me/api/portraits/men/12.jpg', 'fares.boutaleb@example.com', NULL),
('hania.zeroual', 'hashed_password_24', 24, "admin", '{"theme": "dark", "language": "fr"}', 'https://randomuser.me/api/portraits/women/12.jpg', 'hania.zeroual@example.com', NULL),
('walid.gherbi', 'hashed_password_25', 25, "admin", '{"theme": "light", "language": "ar"}', 'https://randomuser.me/api/portraits/men/13.jpg', 'walid.gherbi@example.com', NULL);



-- Notifications for user #4 (assuming user exists with id_app_user = 4)

-- Organizations for suppliers
INSERT INTO provider_organisation (
    provider_organisation_name, 
    provider_organisation_desc
) VALUES
('Verdelia International', 'Leading provider of gluten-free products and specialty food items across North Africa. Committed to quality and innovation in celiac-friendly nutrition.'),
('MediFarm Algérie', 'Agricultural cooperative specializing in organic grains, legumes, and traditional Algerian produce. Focus on sustainable farming and fair trade practices.'),
('Sahara Fresh Distribution', 'Major distributor of fresh produce, dairy products, and packaged goods serving retail chains across Algeria. Fast delivery and competitive pricing.'),
('El Djazair Food Industries', 'Food manufacturing company producing traditional Algerian pastries, couscous, and preserved goods. Family-owned since 1985.'),
('Atlas Mountains Organic', 'Specialized in organic and natural food products sourced from the Atlas Mountains region. Focus on honey, dried fruits, and aromatic herbs.');


-- Invitation Notifications for Organizations and Suppliers
INSERT INTO notification (notification_code, notification_params, notification_user_ref, notification_created_at, notification_read_at) VALUES

-- Organization Invitations (referencing the 5 organizations)
('ROLE_INVITATION', '{"entity_id": 1, "entity_name": "Verdelia International", "entity_type": "organization", "role_name": "Store Manager", "invited_by": "Admin User", "invitation_date": "2024-06-01T10:30:00", "management_rule_id": 101}', 4, '2024-06-01 10:30:00', NULL),
('ROLE_INVITATION', '{"entity_id": 2, "entity_name": "MediFarm Algérie", "entity_type": "organization", "role_name": "Product Manager", "invited_by": "Sarah Johnson", "invitation_date": "2024-06-05T14:15:00", "management_rule_id": 102}', 4, '2024-06-05 14:15:00', '2024-06-06 09:20:00'),
('ROLE_INVITATION', '{"entity_id": 3, "entity_name": "Sahara Fresh Distribution", "entity_type": "organization", "role_name": "Inventory Manager", "invited_by": "Michael Brown", "invitation_date": "2024-06-10T09:45:00", "management_rule_id": 103}', 4, '2024-06-10 09:45:00', NULL),
('ROLE_INVITATION', '{"entity_id": 4, "entity_name": "El Djazair Food Industries", "entity_type": "organization", "role_name": "Quality Control Manager", "invited_by": "Ahmed Benali", "invitation_date": "2024-06-12T11:00:00", "management_rule_id": 104}', 4, '2024-06-12 11:00:00', NULL),
('ROLE_INVITATION', '{"entity_id": 5, "entity_name": "Atlas Mountains Organic", "entity_type": "organization", "role_name": "Procurement Specialist", "invited_by": "Fatima Zohra", "invitation_date": "2024-06-15T13:30:00", "management_rule_id": 105}', 4, '2024-06-15 13:30:00', NULL),

-- Supplier Invitations (referencing 7 suppliers)
('ROLE_INVITATION', '{"entity_id": 1, "entity_name": "Verdelia North Algeria", "entity_type": "supplier", "role_name": "Supplier Admin", "invited_by": "Admin User", "invitation_date": "2024-06-02T09:00:00", "management_rule_id": 201}', 4, '2024-06-02 09:00:00', '2024-06-02 10:30:00'),
('ROLE_INVITATION', '{"entity_id": 2, "entity_name": "Verdelia South Region", "entity_type": "supplier", "role_name": "Regional Manager", "invited_by": "Admin User", "invitation_date": "2024-06-03T14:00:00", "management_rule_id": 202}', 4, '2024-06-03 14:00:00', NULL),
('ROLE_INVITATION', '{"entity_id": 3, "entity_name": "MediFarm Central", "entity_type": "supplier", "role_name": "Farm Coordinator", "invited_by": "Sarah Johnson", "invitation_date": "2024-06-07T10:00:00", "management_rule_id": 203}', 4, '2024-06-07 10:00:00', '2024-06-08 08:00:00'),
('ROLE_INVITATION', '{"entity_id": 4, "entity_name": "Sahara Fresh Algiers", "entity_type": "supplier", "role_name": "Logistics Manager", "invited_by": "Michael Brown", "invitation_date": "2024-06-09T15:30:00", "management_rule_id": 204}', 4, '2024-06-09 15:30:00', NULL),
('ROLE_INVITATION', '{"entity_id": 5, "entity_name": "El Djazair Traditional", "entity_type": "supplier", "role_name": "Production Supervisor", "invited_by": "Ahmed Benali", "invitation_date": "2024-06-11T11:00:00", "management_rule_id": 205}', 4, '2024-06-11 11:00:00', '2024-06-12 14:00:00'),
('ROLE_INVITATION', '{"entity_id": 6, "entity_name": "Atlas Honey Products", "entity_type": "supplier", "role_name": "Quality Inspector", "invited_by": "Fatima Zohra", "invitation_date": "2024-06-13T09:00:00", "management_rule_id": 206}', 4, '2024-06-13 09:00:00', NULL),
('ROLE_INVITATION', '{"entity_id": 7, "entity_name": "Sahara Oasis Dates", "entity_type": "supplier", "role_name": "Date Specialist", "invited_by": "Karim Mansouri", "invitation_date": "2024-06-14T14:00:00", "management_rule_id": 207}', 4, '2024-06-14 14:00:00', NULL),

-- System Alert Notifications
('service_reminder', '{"alert_type": "maintenance", "message": "System maintenance scheduled for June 15th at 2 AM", "timestamp": "2024-06-08T16:20:00"}', 4, '2024-06-08 16:20:00', '2024-06-08 17:00:00'),
('service_reminder', '{"alert_type": "security", "message": "New login detected from new device", "timestamp": "2024-06-12T08:15:00"}', 4, '2024-06-12 08:15:00', '2024-06-12 08:30:00'),
('service_reminder', '{"alert_type": "update", "message": "New version 2.0.0 is available", "timestamp": "2024-06-14T11:00:00"}', 4, '2024-06-14 11:00:00', NULL),

-- Reminder Notifications
('event_reminder', '{"reminder_type": "order", "due_date": "2024-06-20", "created_at": "2024-06-13T10:00:00"}', 4, '2024-06-13 10:00:00', NULL),
('event_reminder', '{"reminder_type": "payment", "due_date": "2024-06-25", "created_at": "2024-06-14T09:30:00"}', 4, '2024-06-14 09:30:00', NULL),
('event_reminder', '{"reminder_type": "subscription", "due_date": "2024-07-01", "created_at": "2024-06-15T14:45:00"}', 4, '2024-06-15 14:45:00', '2024-06-16 08:00:00'),

-- Order Status Notifications
('order_shipped', '{"order_id": "ORD-12345", "status": "shipped", "tracking_number": "TRK789012", "updated_at": "2024-06-02T15:30:00"}', 4, '2024-06-02 15:30:00', '2024-06-02 16:00:00'),
('order_delivered', '{"order_id": "ORD-12346", "status": "delivered", "delivered_at": "2024-06-07T12:00:00"}', 4, '2024-06-07 12:00:00', '2024-06-07 13:15:00'),
('order_processing', '{"order_id": "ORD-12347", "status": "processing", "estimated_delivery": "2024-06-22"}', 4, '2024-06-10 11:20:00', NULL),

-- Stock Alert Notifications
('product_stock_low', '{"product_name": "Premium Coffee Beans", "current_stock": 15, "min_threshold": 20, "alert_at": "2024-06-03T08:00:00"}', 4, '2024-06-03 08:00:00', '2024-06-03 09:30:00'),
('product_stock_low', '{"product_name": "Organic Tea", "current_stock": 8, "min_threshold": 10, "alert_at": "2024-06-09T10:15:00"}', 4, '2024-06-09 10:15:00', NULL),
('product_stock_low', '{"product_name": "Gluten-Free Flour", "current_stock": 25, "min_threshold": 30, "alert_at": "2024-06-11T14:30:00"}', 4, '2024-06-11 14:30:00', NULL),

-- Promotional Notifications
('promotional_offer', '{"promo_code": "SUMMER20", "discount": "20%", "expires_at": "2024-07-31", "message": "Summer sale! Get 20% off on all orders"}', 4, '2024-06-01 00:00:00', '2024-06-01 10:00:00'),
('promotional_offer', '{"promo_code": "FREESHIP", "discount": "free shipping", "expires_at": "2024-06-30", "message": "Free shipping on orders over DZD 5000"}', 4, '2024-06-05 09:00:00', NULL),
('promotional_offer', '{"promo_code": "WELCOME10", "discount": "10%", "expires_at": "2024-07-15", "message": "Welcome discount for new customers"}', 4, '2024-06-10 08:00:00', NULL);

-- Summary counts
-- SELECT COUNT(*) FROM notification WHERE notification_user_ref = 4;  -- Should return 18
-- SELECT COUNT(*) FROM notification WHERE notification_user_ref = 4 AND notification_read_at IS NOT NULL;  -- Read count: 6
-- SELECT COUNT(*) FROM notification WHERE notification_user_ref = 4 AND notification_read_at IS NULL;  -- Unread count: 12

-- Management Rules (Role Invitations) for user #4
-- These represent pending invitations for the user to join organizations or suppliers

INSERT INTO `provided_service_category` (
    `provided_service_category_name`,
    `provided_service_category_naming_ref`,
    `provided_service_category_icon_url`,
    `provided_service_category_avg_duration`,
    `provided_service_category_description`,
    `provided_service_category_created_at`,
    `provided_service_category_updated_at`,
    `provided_service_category_deleted_at`
) VALUES
-- Medical & Health Services
('General Medical Consultation', NULL, 'icons/medical/consultation.svg', 30.00, 'General medical consultation and diagnosis for common health issues', NOW(), NOW(), NULL),
('Specialist Consultation', NULL, 'icons/medical/specialist.svg', 45.00, 'Specialized medical consultation with expert doctors', NOW(), NOW(), NULL),
('Emergency Care', NULL, 'icons/medical/emergency.svg', 60.00, 'Emergency medical care and urgent treatment services', NOW(), NOW(), NULL),
('Surgery', NULL, 'icons/medical/surgery.svg', 120.00, 'Surgical procedures and operations', NOW(), NOW(), NULL),
('Dental Services', NULL, 'icons/medical/dental.svg', 45.00, 'Comprehensive dental care including checkups and procedures', NOW(), NOW(), NULL),
('Orthopedic Services', NULL, 'icons/medical/orthopedic.svg', 60.00, 'Bone, joint, and muscle treatment services', NOW(), NOW(), NULL),
('Dermatology', NULL, 'icons/medical/dermatology.svg', 30.00, 'Skin, hair, and nail care services', NOW(), NOW(), NULL),
('Ophthalmology', NULL, 'icons/medical/ophthalmology.svg', 30.00, 'Eye care and vision services', NOW(), NOW(), NULL),
('Cardiology', NULL, 'icons/medical/cardiology.svg', 45.00, 'Heart and cardiovascular services', NOW(), NOW(), NULL),
('Neurology', NULL, 'icons/medical/neurology.svg', 45.00, 'Brain, spine, and nervous system services', NOW(), NOW(), NULL),
('Gynecology & Obstetrics', NULL, 'icons/medical/gynecology.svg', 45.00, 'Women\'s health, pregnancy, and childbirth services', NOW(), NOW(), NULL),
('Pediatrics', NULL, 'icons/medical/pediatrics.svg', 30.00, 'Child health and development services', NOW(), NOW(), NULL),

-- Laboratory & Diagnostic Services
('Laboratory Tests', NULL, 'icons/medical/lab.svg', 15.00, 'Blood tests, urine tests, and other laboratory diagnostics', NOW(), NOW(), NULL),
('Radiology & Imaging', NULL, 'icons/medical/radiology.svg', 30.00, 'X-rays, MRIs, CT scans, and ultrasound services', NOW(), NOW(), NULL),
('Pathology', NULL, 'icons/medical/pathology.svg', 45.00, 'Disease diagnosis through tissue and fluid analysis', NOW(), NOW(), NULL),

-- Therapeutic & Rehabilitative Services
('Physiotherapy', NULL, 'icons/medical/physiotherapy.svg', 45.00, 'Physical therapy and rehabilitation services', NOW(), NOW(), NULL),
('Occupational Therapy', NULL, 'icons/medical/occupational.svg', 45.00, 'Therapy to help patients perform daily activities', NOW(), NOW(), NULL),
('Speech Therapy', NULL, 'icons/medical/speech.svg', 30.00, 'Speech and language therapy services', NOW(), NOW(), NULL),
('Psychological Services', NULL, 'icons/medical/psychology.svg', 50.00, 'Mental health counseling and psychological therapy', NOW(), NOW(), NULL),
('Psychiatry', NULL, 'icons/medical/psychiatry.svg', 45.00, 'Psychiatric evaluation and medication management', NOW(), NOW(), NULL),

-- Wellness & Preventive
('Nutrition & Dietetics', NULL, 'icons/medical/nutrition.svg', 30.00, 'Nutritional counseling and diet planning', NOW(), NOW(), NULL),
('Fitness & Wellness', NULL, 'icons/medical/fitness.svg', 45.00, 'Personal training and wellness programs', NOW(), NOW(), NULL),
('Health Screening', NULL, 'icons/medical/screening.svg', 20.00, 'Preventive health screening and checkups', NOW(), NOW(), NULL),
('Vaccination Services', NULL, 'icons/medical/vaccination.svg', 15.00, 'Immunization and vaccination services', NOW(), NOW(), NULL),

-- Home Care & Support
('Home Healthcare', NULL, 'icons/medical/homecare.svg', 60.00, 'Healthcare services provided at the patient\'s home', NOW(), NOW(), NULL),
('Palliative Care', NULL, 'icons/medical/palliative.svg', 60.00, 'Comfort care for patients with serious illnesses', NOW(), NOW(), NULL),
('Hospice Care', NULL, 'icons/medical/hospice.svg', 60.00, 'End-of-life care and support services', NOW(), NOW(), NULL),

-- Administrative & Other Services
('Medical Records Management', NULL, 'icons/medical/records.svg', 15.00, 'Medical records and health information management', NOW(), NOW(), NULL),
('Pharmacy Services', NULL, 'icons/medical/pharmacy.svg', 10.00, 'Medication dispensing and pharmaceutical services', NOW(), NOW(), NULL),
('Medical Transport', NULL, 'icons/medical/transport.svg', 30.00, 'Ambulance and medical transportation services', NOW(), NOW(), NULL),
('Health Education', NULL, 'icons/medical/education.svg', 45.00, 'Health education and wellness workshops', NOW(), NOW(), NULL);


INSERT INTO `provided_service_category` (
    `provided_service_category_name`,
    `provided_service_category_naming_ref`,
    `provided_service_category_icon_url`,
    `provided_service_category_avg_duration`,
    `provided_service_category_description`,
    `provided_service_category_created_at`,
    `provided_service_category_updated_at`,
    `provided_service_category_deleted_at`
) VALUES
-- Medical & Health Services
('General Medical Consultation', NULL, 'icons/medical/consultation.svg', 30.00, 'General medical consultation and diagnosis for common health issues', NOW(), NOW(), NULL),
('Specialist Consultation', NULL, 'icons/medical/specialist.svg', 45.00, 'Specialized medical consultation with expert doctors', NOW(), NOW(), NULL),
('Emergency Care', NULL, 'icons/medical/emergency.svg', 60.00, 'Emergency medical care and urgent treatment services', NOW(), NOW(), NULL),
('Surgery', NULL, 'icons/medical/surgery.svg', 120.00, 'Surgical procedures and operations', NOW(), NOW(), NULL),
('Dental Services', NULL, 'icons/medical/dental.svg', 45.00, 'Comprehensive dental care including checkups and procedures', NOW(), NOW(), NULL),
('Orthopedic Services', NULL, 'icons/medical/orthopedic.svg', 60.00, 'Bone, joint, and muscle treatment services', NOW(), NOW(), NULL),
('Dermatology', NULL, 'icons/medical/dermatology.svg', 30.00, 'Skin, hair, and nail care services', NOW(), NOW(), NULL),
('Ophthalmology', NULL, 'icons/medical/ophthalmology.svg', 30.00, 'Eye care and vision services', NOW(), NOW(), NULL),
('Cardiology', NULL, 'icons/medical/cardiology.svg', 45.00, 'Heart and cardiovascular services', NOW(), NOW(), NULL),
('Neurology', NULL, 'icons/medical/neurology.svg', 45.00, 'Brain, spine, and nervous system services', NOW(), NOW(), NULL),
('Gynecology & Obstetrics', NULL, 'icons/medical/gynecology.svg', 45.00, 'Women\'s health, pregnancy, and childbirth services', NOW(), NOW(), NULL),
('Pediatrics', NULL, 'icons/medical/pediatrics.svg', 30.00, 'Child health and development services', NOW(), NOW(), NULL),

-- Laboratory & Diagnostic Services
('Laboratory Tests', NULL, 'icons/medical/lab.svg', 15.00, 'Blood tests, urine tests, and other laboratory diagnostics', NOW(), NOW(), NULL),
('Radiology & Imaging', NULL, 'icons/medical/radiology.svg', 30.00, 'X-rays, MRIs, CT scans, and ultrasound services', NOW(), NOW(), NULL),
('Pathology', NULL, 'icons/medical/pathology.svg', 45.00, 'Disease diagnosis through tissue and fluid analysis', NOW(), NOW(), NULL),

-- Therapeutic & Rehabilitative Services
('Physiotherapy', NULL, 'icons/medical/physiotherapy.svg', 45.00, 'Physical therapy and rehabilitation services', NOW(), NOW(), NULL),
('Occupational Therapy', NULL, 'icons/medical/occupational.svg', 45.00, 'Therapy to help patients perform daily activities', NOW(), NOW(), NULL),
('Speech Therapy', NULL, 'icons/medical/speech.svg', 30.00, 'Speech and language therapy services', NOW(), NOW(), NULL),
('Psychological Services', NULL, 'icons/medical/psychology.svg', 50.00, 'Mental health counseling and psychological therapy', NOW(), NOW(), NULL),
('Psychiatry', NULL, 'icons/medical/psychiatry.svg', 45.00, 'Psychiatric evaluation and medication management', NOW(), NOW(), NULL),

-- Wellness & Preventive
('Nutrition & Dietetics', NULL, 'icons/medical/nutrition.svg', 30.00, 'Nutritional counseling and diet planning', NOW(), NOW(), NULL),
('Fitness & Wellness', NULL, 'icons/medical/fitness.svg', 45.00, 'Personal training and wellness programs', NOW(), NOW(), NULL),
('Health Screening', NULL, 'icons/medical/screening.svg', 20.00, 'Preventive health screening and checkups', NOW(), NOW(), NULL),
('Vaccination Services', NULL, 'icons/medical/vaccination.svg', 15.00, 'Immunization and vaccination services', NOW(), NOW(), NULL),

-- Home Care & Support
('Home Healthcare', NULL, 'icons/medical/homecare.svg', 60.00, 'Healthcare services provided at the patient\'s home', NOW(), NOW(), NULL),
('Palliative Care', NULL, 'icons/medical/palliative.svg', 60.00, 'Comfort care for patients with serious illnesses', NOW(), NOW(), NULL),
('Hospice Care', NULL, 'icons/medical/hospice.svg', 60.00, 'End-of-life care and support services', NOW(), NOW(), NULL),

-- Administrative & Other Services
('Medical Records Management', NULL, 'icons/medical/records.svg', 15.00, 'Medical records and health information management', NOW(), NOW(), NULL),
('Pharmacy Services', NULL, 'icons/medical/pharmacy.svg', 10.00, 'Medication dispensing and pharmaceutical services', NOW(), NOW(), NULL),
('Medical Transport', NULL, 'icons/medical/transport.svg', 30.00, 'Ambulance and medical transportation services', NOW(), NOW(), NULL),
('Health Education', NULL, 'icons/medical/education.svg', 45.00, 'Health education and wellness workshops', NOW(), NOW(), NULL);


-- -----------------------------------------------------
-- Dummy Data for provided_service
-- -----------------------------------------------------
INSERT INTO `provided_service` (
    `provided_service_name`,
    `provided_service_description`,
    `provided_service_category_id`,
    `provided_service_product_provider_id`,
    `provided_service_base_price`,
    `provided_service_final_price`,
    `provided_service_actual_duration`,
    `provided_service_is_active`,
    `provided_service_pricing_config`,
    `provided_service_created_at`,
    `provided_service_updated_at`,
    `provided_service_deleted_at`
) VALUES
-- Provider 1 (General Medical Services)
('General Health Checkup', 'Comprehensive health checkup including vital signs, basic lab tests, and general physical examination', 1, 1, 80.00, 75.00, 30.00, 1, '{"discount": 5, "package_price": 75}', NOW(), NOW(), NULL),
('Family Medicine Consultation', 'Primary care consultation for all family members', 1, 1, 60.00, 60.00, 25.00, 1, NULL, NOW(), NOW(), NULL),
('Urgent Care Visit', 'Same-day urgent care for non-emergency conditions', 3, 1, 100.00, 95.00, 30.00, 1, '{"discount": 5}', NOW(), NOW(), NULL),
('Physical Examination', 'Complete physical exam for employment or school', 1, 1, 85.00, 85.00, 40.00, 1, NULL, NOW(), NOW(), NULL),

-- Provider 2 (Specialist Services)
('Cardiology Consultation', 'Cardiac evaluation and consultation', 9, 2, 150.00, 140.00, 45.00, 1, '{"discount": 10}', NOW(), NOW(), NULL),
('ECG/EKG Test', 'Electrocardiogram for heart rhythm assessment', 9, 2, 65.00, 65.00, 20.00, 1, NULL, NOW(), NOW(), NULL),
('Echocardiogram', 'Ultrasound imaging of the heart', 9, 2, 250.00, 235.00, 45.00, 1, '{"discount": 15}', NOW(), NOW(), NULL),
('Cardiac Stress Test', 'Exercise stress test for heart evaluation', 9, 2, 180.00, 170.00, 60.00, 1, '{"discount": 10}', NOW(), NOW(), NULL),

-- Provider 3 (Dental Services)
('General Dental Checkup', 'Comprehensive dental examination and cleaning', 5, 3, 70.00, 70.00, 30.00, 1, NULL, NOW(), NOW(), NULL),
('Teeth Cleaning', 'Professional teeth cleaning and scaling', 5, 3, 50.00, 45.00, 25.00, 1, '{"discount": 5}', NOW(), NOW(), NULL),
('Dental X-ray', 'X-ray imaging for dental diagnosis', 5, 3, 40.00, 40.00, 15.00, 1, NULL, NOW(), NOW(), NULL),
('Root Canal Treatment', 'Endodontic treatment for infected teeth', 5, 3, 350.00, 330.00, 90.00, 1, '{"discount": 20}', NOW(), NOW(), NULL),
('Teeth Whitening', 'Professional teeth whitening service', 5, 3, 120.00, 110.00, 45.00, 1, '{"discount": 10}', NOW(), NOW(), NULL),

-- Provider 4 (Dermatology)
('Dermatology Consultation', 'Skin, hair, and nail evaluation', 7, 4, 100.00, 95.00, 30.00, 1, '{"discount": 5}', NOW(), NOW(), NULL),
('Acne Treatment', 'Customized acne treatment program', 7, 4, 150.00, 140.00, 45.00, 1, '{"discount": 10}', NOW(), NOW(), NULL),
('Skin Biopsy', 'Skin tissue biopsy for diagnosis', 7, 4, 200.00, 190.00, 30.00, 1, '{"discount": 10}', NOW(), NOW(), NULL),
('Laser Skin Treatment', 'Laser treatment for skin conditions', 7, 4, 300.00, 275.00, 45.00, 1, '{"discount": 25}', NOW(), NOW(), NULL),
('Chemical Peel', 'Skin rejuvenation with chemical peel', 7, 4, 180.00, 170.00, 30.00, 1, '{"discount": 10}', NOW(), NOW(), NULL),

-- Provider 5 (Laboratory & Imaging)
('Blood Tests', 'Complete blood count and basic chemistry panel', 13, 5, 45.00, 45.00, 15.00, 1, NULL, NOW(), NOW(), NULL),
('Urine Analysis', 'Urine test for various health indicators', 13, 5, 25.00, 25.00, 10.00, 1, NULL, NOW(), NOW(), NULL),
('X-Ray Imaging', 'General X-ray imaging service', 14, 5, 75.00, 70.00, 20.00, 1, '{"discount": 5}', NOW(), NOW(), NULL),
('Ultrasound Scan', 'Ultrasound diagnostic imaging', 14, 5, 120.00, 115.00, 30.00, 1, '{"discount": 5}', NOW(), NOW(), NULL),
('CT Scan', 'Computerized tomography scan', 14, 5, 350.00, 330.00, 30.00, 1, '{"discount": 20}', NOW(), NOW(), NULL),

-- Provider 6 (Physiotherapy)
('Physiotherapy Assessment', 'Initial physiotherapy evaluation', 16, 6, 80.00, 75.00, 45.00, 1, '{"discount": 5}', NOW(), NOW(), NULL),
('Physical Therapy Session', 'Regular physiotherapy treatment session', 16, 6, 60.00, 55.00, 45.00, 1, '{"discount": 5}', NOW(), NOW(), NULL),
('Sports Injury Rehabilitation', 'Specialized rehabilitation for sports injuries', 16, 6, 90.00, 85.00, 60.00, 1, '{"discount": 5}', NOW(), NOW(), NULL),
('Massage Therapy', 'Therapeutic massage for pain relief', 16, 6, 70.00, 65.00, 60.00, 1, '{"discount": 5}', NOW(), NOW(), NULL),

-- Provider 7 (Mental Health)
('Psychological Assessment', 'Comprehensive psychological evaluation', 19, 7, 120.00, 115.00, 50.00, 1, '{"discount": 5}', NOW(), NOW(), NULL),
('Cognitive Behavioral Therapy', 'CBT session for mental health', 19, 7, 100.00, 95.00, 50.00, 1, '{"discount": 5}', NOW(), NOW(), NULL),
('Psychiatric Consultation', 'Psychiatric evaluation and medication management', 19, 7, 150.00, 140.00, 45.00, 1, '{"discount": 10}', NOW(), NOW(), NULL),
('Counseling Session', 'General counseling and therapy', 19, 7, 80.00, 75.00, 45.00, 1, '{"discount": 5}', NOW(), NOW(), NULL),

-- More Services for Provider 1
('Vaccination Service', 'Immunization and vaccination administration', 24, 1, 50.00, 50.00, 15.00, 1, NULL, NOW(), NOW(), NULL),
('Travel Medicine Consultation', 'Pre-travel health consultation and advice', 1, 1, 70.00, 65.00, 30.00, 1, '{"discount": 5}', NOW(), NOW(), NULL),
('Home Visit Consultation', 'Medical consultation at patient\'s home', 25, 1, 120.00, 115.00, 45.00, 1, '{"discount": 5}', NOW(), NOW(), NULL),

-- More Services for Provider 2
('Holter Monitor', '24-hour heart rhythm monitoring', 9, 2, 200.00, 190.00, 30.00, 1, '{"discount": 10}', NOW(), NOW(), NULL),
('Blood Pressure Monitoring', '24-hour ambulatory blood pressure monitoring', 9, 2, 150.00, 145.00, 30.00, 1, '{"discount": 5}', NOW(), NOW(), NULL),

-- More Services for Provider 3
('Dental Crown', 'Dental crown fitting and installation', 5, 3, 400.00, 375.00, 90.00, 1, '{"discount": 25}', NOW(), NOW(), NULL),
('Dental Implant', 'Dental implant surgery', 5, 3, 800.00, 750.00, 120.00, 1, '{"discount": 50}', NOW(), NOW(), NULL),
('Braces Consultation', 'Orthodontic consultation for braces', 5, 3, 100.00, 95.00, 30.00, 1, '{"discount": 5}', NOW(), NOW(), NULL),

-- More Services for Provider 4
('Botox Treatment', 'Botox injection for wrinkles and conditions', 7, 4, 250.00, 235.00, 30.00, 1, '{"discount": 15}', NOW(), NOW(), NULL),
('Dermatology Surgery', 'Surgical skin procedures and excisions', 7, 4, 500.00, 475.00, 60.00, 1, '{"discount": 25}', NOW(), NOW(), NULL),

-- More Services for Provider 5
('MRI Scan', 'Magnetic resonance imaging', 14, 5, 500.00, 475.00, 45.00, 1, '{"discount": 25}', NOW(), NOW(), NULL),
('Blood Donation Services', 'Blood donation and testing', 13, 5, 0.00, 0.00, 30.00, 1, '{"free_service": true}', NOW(), NOW(), NULL),

-- More Services for Provider 6
('Post-Surgery Rehabilitation', 'Rehabilitation after surgery', 16, 6, 100.00, 95.00, 60.00, 1, '{"discount": 5}', NOW(), NOW(), NULL),
('Geriatric Physiotherapy', 'Physiotherapy for elderly patients', 16, 6, 80.00, 75.00, 45.00, 1, '{"discount": 5}', NOW(), NOW(), NULL),

-- More Services for Provider 7
('Group Therapy', 'Group counseling sessions', 19, 7, 50.00, 45.00, 60.00, 1, '{"discount": 5}', NOW(), NOW(), NULL),
('Family Therapy', 'Family counseling and therapy', 19, 7, 120.00, 115.00, 60.00, 1, '{"discount": 5}', NOW(), NOW(), NULL),
('Online Therapy Session', 'Virtual/online therapy consultation', 19, 7, 80.00, 75.00, 45.00, 1, '{"discount": 5}', NOW(), NOW(), NULL);



-- -----------------------------------------------------
-- Dummy Data for staff_role
-- -----------------------------------------------------
INSERT INTO `staff_role` (
    `staff_role_service_category_ref`,
    `staff_role_naming_ref`,
    `staff_role_icon_url`,
    `staff_role_name`
) VALUES
-- Medical Doctors (Reference General Medical Consultation)
(1, NULL, 'icons/staff/doctor.svg', 'General Practitioner'),
(1, NULL, 'icons/staff/doctor.svg', 'Family Physician'),
(2, NULL, 'icons/staff/specialist.svg', 'Specialist Doctor'),
(2, NULL, 'icons/staff/surgeon.svg', 'Consultant'),

-- Surgeons (Reference Surgery)
(4, NULL, 'icons/staff/surgeon.svg', 'General Surgeon'),
(4, NULL, 'icons/staff/surgeon.svg', 'Cardiothoracic Surgeon'),
(4, NULL, 'icons/staff/surgeon.svg', 'Neurosurgeon'),
(4, NULL, 'icons/staff/surgeon.svg', 'Orthopedic Surgeon'),
(4, NULL, 'icons/staff/surgeon.svg', 'Plastic Surgeon'),

-- Dental Staff (Reference Dental Services)
(5, NULL, 'icons/staff/dentist.svg', 'General Dentist'),
(5, NULL, 'icons/staff/dentist.svg', 'Orthodontist'),
(5, NULL, 'icons/staff/dentist.svg', 'Oral Surgeon'),
(5, NULL, 'icons/staff/dental_hygienist.svg', 'Dental Hygienist'),
(5, NULL, 'icons/staff/dental_assistant.svg', 'Dental Assistant'),

-- Orthopedic Staff (Reference Orthopedic Services)
(6, NULL, 'icons/staff/orthopedic.svg', 'Orthopedic Surgeon'),
(6, NULL, 'icons/staff/orthopedic.svg', 'Sports Medicine Specialist'),
(6, NULL, 'icons/staff/physical_therapist.svg', 'Physical Therapist'),

-- Dermatology Staff (Reference Dermatology)
(7, NULL, 'icons/staff/dermatologist.svg', 'Dermatologist'),
(7, NULL, 'icons/staff/dermatologist.svg', 'Cosmetic Dermatologist'),

-- Ophthalmology Staff (Reference Ophthalmology)
(8, NULL, 'icons/staff/ophthalmologist.svg', 'Ophthalmologist'),
(8, NULL, 'icons/staff/optometrist.svg', 'Optometrist'),

-- Cardiology Staff (Reference Cardiology)
(9, NULL, 'icons/staff/cardiologist.svg', 'Interventional Cardiologist'),
(9, NULL, 'icons/staff/cardiologist.svg', 'Cardiac Surgeon'),
(9, NULL, 'icons/staff/cardiologist.svg', 'Cardiovascular Technician'),

-- Neurology Staff (Reference Neurology)
(10, NULL, 'icons/staff/neurologist.svg', 'Neurologist'),
(10, NULL, 'icons/staff/neurologist.svg', 'Neurosurgeon'),

-- Gynecology Staff (Reference Gynecology & Obstetrics)
(11, NULL, 'icons/staff/gynecologist.svg', 'Gynecologist'),
(11, NULL, 'icons/staff/gynecologist.svg', 'Obstetrician'),
(11, NULL, 'icons/staff/midwife.svg', 'Midwife'),

-- Pediatric Staff (Reference Pediatrics)
(12, NULL, 'icons/staff/pediatrician.svg', 'Pediatrician'),
(12, NULL, 'icons/staff/pediatrician.svg', 'Neonatologist'),

-- Laboratory Staff (Reference Laboratory Tests)
(13, NULL, 'icons/staff/lab_technician.svg', 'Lab Technician'),
(13, NULL, 'icons/staff/pathologist.svg', 'Pathologist'),

-- Radiology Staff (Reference Radiology & Imaging)
(14, NULL, 'icons/staff/radiologist.svg', 'Radiologist'),
(14, NULL, 'icons/staff/radiology_technician.svg', 'Radiology Technician'),
(14, NULL, 'icons/staff/ultrasound_technician.svg', 'Ultrasound Technician'),

-- Physical Therapy Staff (Reference Physiotherapy)
(16, NULL, 'icons/staff/physical_therapist.svg', 'Physical Therapist'),
(16, NULL, 'icons/staff/physical_therapist.svg', 'Physical Therapy Assistant'),

-- Mental Health Staff (Reference Psychological Services)
(19, NULL, 'icons/staff/psychologist.svg', 'Clinical Psychologist'),
(19, NULL, 'icons/staff/psychiatrist.svg', 'Psychiatrist'),

-- Support Staff (General)
(1, NULL, 'icons/staff/nurse.svg', 'Registered Nurse'),
(1, NULL, 'icons/staff/nurse.svg', 'Licensed Practical Nurse'),
(1, NULL, 'icons/staff/nurse.svg', 'Nurse Practitioner'),
(1, NULL, 'icons/staff/medical_assistant.svg', 'Medical Assistant'),
(1, NULL, 'icons/staff/pharmacist.svg', 'Pharmacist'),
(1, NULL, 'icons/staff/pharmacist.svg', 'Pharmacy Technician'),
(1, NULL, 'icons/staff/administrator.svg', 'Medical Administrator'),
(1, NULL, 'icons/staff/receptionist.svg', 'Medical Receptionist'),

-- Emergency & Critical Care Staff (Reference Emergency Care)
(3, NULL, 'icons/staff/emergency_doctor.svg', 'Emergency Physician'),
(3, NULL, 'icons/staff/paramedic.svg', 'Paramedic'),
(3, NULL, 'icons/staff/emergency_nurse.svg', 'Emergency Nurse'),
(3, NULL, 'icons/staff/critical_care_nurse.svg', 'Critical Care Nurse'),

-- Nutrition Staff (Reference Nutrition & Dietetics)
(21, NULL, 'icons/staff/nutritionist.svg', 'Clinical Nutritionist'),
(21, NULL, 'icons/staff/dietitian.svg', 'Registered Dietitian'),

-- Healthcare Support
(1, NULL, 'icons/staff/caregiver.svg', 'Caregiver'),
(1, NULL, 'icons/staff/home_health_aide.svg', 'Home Health Aide'),
(1, NULL, 'icons/staff/medical_social_worker.svg', 'Medical Social Worker'),
(1, NULL, 'icons/staff/health_coach.svg', 'Health Coach');




-- -----------------------------------------------------
-- Dummy Data for service_staff_requirement
-- -----------------------------------------------------
INSERT INTO `service_staff_requirement` (
    `service_staff_requirement_service_id`,
    `service_staff_requirement_role`,
    `service_staff_requirement_min_count`,
    `service_staff_requirement_max_count`,
    `service_staff_requirement_hourly_rate`,
    `service_staff_requirement_allocated_hours`,
    `service_staff_requirement_notes`,
    `service_staff_requirement_created_at`,
    `service_staff_requirement_updated_at`
) VALUES
-- Provider 1 Services (General Medical)
(1, 1, 1, 1, 50.00, 1.00, 'General Practitioner for health checkup', NOW(), NOW()),
(1, 25, 1, 1, 30.00, 1.00, 'Nurse assistant for checkup', NOW(), NOW()),
(2, 2, 1, 1, 55.00, 1.00, 'Family Physician consultation', NOW(), NOW()),
(3, 52, 1, 1, 60.00, 1.00, 'Emergency Physician for urgent care', NOW(), NOW()),
(3, 54, 1, 1, 35.00, 1.00, 'Emergency Nurse support', NOW(), NOW()),
(4, 1, 1, 1, 50.00, 1.50, 'Physical examination by GP', NOW(), NOW()),
(4, 25, 1, 1, 30.00, 1.00, 'Nurse for exam preparation', NOW(), NOW()),

-- Provider 2 Services (Cardiology)
(5, 21, 1, 1, 80.00, 1.00, 'Cardiologist consultation', NOW(), NOW()),
(5, 25, 1, 1, 35.00, 1.00, 'Nurse assistant', NOW(), NOW()),
(6, 23, 1, 1, 45.00, 0.50, 'Cardiovascular Technician for ECG', NOW(), NOW()),
(7, 21, 1, 1, 85.00, 1.00, 'Interventional Cardiologist for echo', NOW(), NOW()),
(7, 23, 1, 1, 45.00, 0.75, 'Echocardiogram technician', NOW(), NOW()),
(8, 21, 1, 1, 80.00, 1.50, 'Cardiologist for stress test', NOW(), NOW()),
(8, 53, 1, 1, 40.00, 1.00, 'Critical Care Nurse monitoring', NOW(), NOW()),
(31, 21, 1, 1, 75.00, 0.50, 'Holter monitor setup by cardiologist', NOW(), NOW()),
(31, 23, 1, 1, 40.00, 0.50, 'Technician for monitor setup', NOW(), NOW()),
(32, 21, 1, 1, 75.00, 0.50, 'Blood pressure monitor setup', NOW(), NOW()),

-- Provider 3 Services (Dental)
(9, 10, 1, 1, 65.00, 1.00, 'General Dentist for checkup', NOW(), NOW()),
(9, 13, 1, 1, 30.00, 1.00, 'Dental Hygienist support', NOW(), NOW()),
(10, 13, 1, 1, 35.00, 1.00, 'Dental Hygienist for cleaning', NOW(), NOW()),
(10, 25, 1, 1, 25.00, 0.50, 'Assistant for cleaning', NOW(), NOW()),
(11, 25, 1, 1, 25.00, 0.50, 'Technician for X-ray', NOW(), NOW()),
(12, 11, 1, 1, 90.00, 2.00, 'Endodontist for root canal', NOW(), NOW()),
(12, 14, 1, 1, 35.00, 2.00, 'Dental Assistant for root canal', NOW(), NOW()),
(13, 10, 1, 1, 65.00, 1.00, 'Dentist for whitening', NOW(), NOW()),
(13, 13, 1, 1, 30.00, 0.75, 'Hygienist support for whitening', NOW(), NOW()),
(33, 10, 1, 1, 70.00, 2.00, 'Dentist for crown fitting', NOW(), NOW()),
(33, 14, 1, 1, 30.00, 2.00, 'Assistant for crown procedure', NOW(), NOW()),
(34, 11, 1, 1, 100.00, 3.00, 'Oral Surgeon for implant', NOW(), NOW()),
(34, 25, 1, 1, 40.00, 3.00, 'Surgical nurse for implant', NOW(), NOW()),
(35, 11, 1, 1, 70.00, 1.00, 'Orthodontist for braces consultation', NOW(), NOW()),

-- Provider 4 Services (Dermatology)
(14, 18, 1, 1, 80.00, 1.00, 'Dermatologist consultation', NOW(), NOW()),
(15, 18, 1, 1, 85.00, 1.50, 'Dermatologist for acne treatment', NOW(), NOW()),
(15, 25, 1, 1, 35.00, 1.00, 'Nurse for treatment assistance', NOW(), NOW()),
(16, 18, 1, 1, 90.00, 1.00, 'Dermatologist for biopsy', NOW(), NOW()),
(16, 25, 1, 1, 35.00, 0.50, 'Nurse for biopsy preparation', NOW(), NOW()),
(17, 19, 1, 1, 95.00, 1.00, 'Cosmetic Dermatologist for laser', NOW(), NOW()),
(17, 25, 1, 1, 40.00, 1.00, 'Nurse for laser treatment', NOW(), NOW()),
(18, 18, 1, 1, 85.00, 1.00, 'Dermatologist for chemical peel', NOW(), NOW()),
(18, 25, 1, 1, 35.00, 1.00, 'Nurse for chemical peel assistance', NOW(), NOW()),
(39, 19, 1, 1, 95.00, 1.00, 'Cosmetic Dermatologist for Botox', NOW(), NOW()),
(39, 25, 1, 1, 40.00, 1.00, 'Nurse for Botox procedure', NOW(), NOW()),
(40, 18, 1, 1, 100.00, 2.00, 'Dermatologist for surgery', NOW(), NOW()),
(40, 54, 1, 1, 45.00, 2.00, 'Surgical nurse for procedure', NOW(), NOW()),

-- Provider 5 Services (Laboratory & Imaging)
(20, 27, 1, 1, 30.00, 0.50, 'Lab Technician for blood tests', NOW(), NOW()),
(21, 27, 1, 1, 25.00, 0.50, 'Lab Technician for urine analysis', NOW(), NOW()),
(22, 28, 1, 1, 45.00, 0.50, 'Radiology Technician for X-ray', NOW(), NOW()),
(23, 30, 1, 1, 50.00, 1.00, 'Ultrasound Technician for scan', NOW(), NOW()),
(24, 28, 1, 1, 55.00, 1.00, 'Radiologist for CT scan', NOW(), NOW()),
(24, 29, 1, 1, 45.00, 1.00, 'Radiology Technician for CT', NOW(), NOW()),
(41, 28, 1, 1, 60.00, 1.50, 'Radiologist for MRI', NOW(), NOW()),
(41, 29, 1, 1, 50.00, 1.50, 'MRI Technician', NOW(), NOW()),
(42, 27, 1, 1, 25.00, 1.00, 'Lab Technician for blood donation', NOW(), NOW()),
(42, 25, 1, 1, 20.00, 1.00, 'Nurse for blood donation', NOW(), NOW()),

-- Provider 6 Services (Physiotherapy)
(26, 16, 1, 1, 60.00, 1.00, 'Physical Therapist assessment', NOW(), NOW()),
(27, 16, 1, 1, 55.00, 1.00, 'Physical Therapist session', NOW(), NOW()),
(27, 17, 1, 1, 35.00, 1.00, 'Physical Therapy Assistant', NOW(), NOW()),
(28, 16, 1, 1, 65.00, 1.50, 'Physical Therapist for sports rehab', NOW(), NOW()),
(29, 16, 1, 1, 55.00, 1.50, 'Physical Therapist for massage', NOW(), NOW()),
(43, 16, 1, 1, 60.00, 2.00, 'Physical Therapist for post-surgery', NOW(), NOW()),
(43, 17, 1, 1, 35.00, 2.00, 'Assistant for post-surgery rehab', NOW(), NOW()),
(44, 16, 1, 1, 60.00, 1.00, 'Geriatric Physiotherapist', NOW(), NOW()),

-- Provider 7 Services (Mental Health)
(30, 32, 1, 1, 80.00, 1.00, 'Clinical Psychologist assessment', NOW(), NOW()),
(31, 31, 1, 1, 75.00, 1.00, 'Therapist for CBT', NOW(), NOW()),
(32, 33, 1, 1, 85.00, 1.00, 'Psychiatrist consultation', NOW(), NOW()),
(32, 25, 1, 1, 40.00, 1.00, 'Nurse for psychiatric support', NOW(), NOW()),
(33, 32, 1, 1, 65.00, 1.00, 'Psychologist for counseling', NOW(), NOW()),
(45, 31, 1, 1, 50.00, 1.50, 'Group therapy session', NOW(), NOW()),
(45, 32, 1, 1, 60.00, 1.50, 'Psychologist for group session', NOW(), NOW()),
(46, 31, 1, 1, 80.00, 1.50, 'Family therapist for counseling', NOW(), NOW()),
(47, 32, 1, 1, 70.00, 1.00, 'Online therapy session', NOW(), NOW());


-- -----------------------------------------------------
-- Dummy Data for service_resource_requirement
-- -----------------------------------------------------
INSERT INTO `service_resource_requirement` (
    `service_resource_requirement_service_id`,
    `service_resource_requirement_name`,
    `service_resource_requirement_type`,
    `service_resource_requirement_quantity`,
    `service_resource_requirement_cost_per_unit`,
    `service_resource_requirement_is_consumable`,
    `service_resource_requirement_notes`,
    `service_resource_requirement_product_ref`,
    `service_resource_requirement_created_at`,
    `service_resource_requirement_updated_at`
) VALUES
-- =====================================================
-- PROVIDER 1 - General Medical Services
-- =====================================================
-- Service 1: General Health Checkup
(1, 'Examination Table Paper Roll', 'Medical Supply', 2, 2.50, 1, 'Disposable paper roll for examination table', NULL, NOW(), NOW()),
(1, 'Disposable Gloves (Pair)', 'Medical Supply', 2, 0.75, 1, 'Latex-free examination gloves', NULL, NOW(), NOW()),
(1, 'Stethoscope', 'Medical Equipment', 1, 45.00, 0, 'Standard diagnostic stethoscope', NULL, NOW(), NOW()),
(1, 'Blood Pressure Cuff', 'Medical Equipment', 1, 30.00, 0, 'Manual blood pressure measurement device', NULL, NOW(), NOW()),
(1, 'Thermometer (Disposable)', 'Medical Supply', 1, 1.25, 1, 'Single-use disposable thermometer', NULL, NOW(), NOW()),
(1, 'Alcohol Swabs (Pack of 10)', 'Medical Supply', 1, 1.50, 1, 'Disposable alcohol wipes for skin preparation', NULL, NOW(), NOW()),

-- Service 2: Family Medicine Consultation
(2, 'Consultation Room Supplies Kit', 'Medical Supply', 1, 5.00, 1, 'Basic supplies for consultation room', NULL, NOW(), NOW()),
(2, 'Medical Record Forms', 'Administrative', 5, 0.50, 1, 'Patient history and consultation forms', NULL, NOW(), NOW()),

-- Service 3: Urgent Care Visit
(3, 'Emergency Care Kit', 'Medical Supply', 1, 15.00, 1, 'Basic emergency care supplies', NULL, NOW(), NOW()),
(3, 'Sterile Gauze Pads (10pcs)', 'Medical Supply', 2, 3.50, 1, 'Sterile gauze for wound care', NULL, NOW(), NOW()),
(3, 'Medical Tape Roll', 'Medical Supply', 1, 2.50, 1, 'Hypoallergenic medical tape', NULL, NOW(), NOW()),

-- Service 4: Physical Examination
(4, 'Examination Gown (Disposable)', 'Medical Supply', 1, 3.00, 1, 'Patient examination gown', NULL, NOW(), NOW()),
(4, 'Pulse Oximeter', 'Medical Equipment', 1, 25.00, 0, 'Oxygen saturation monitor', NULL, NOW(), NOW()),
(4, 'Weight Scale', 'Medical Equipment', 1, 80.00, 0, 'Digital medical weight scale', NULL, NOW(), NOW()),

-- =====================================================
-- PROVIDER 2 - Cardiology Services
-- =====================================================
-- Service 5: Cardiology Consultation
(5, 'ECG Machine', 'Medical Equipment', 1, 350.00, 0, '12-lead electrocardiogram machine', NULL, NOW(), NOW()),
(5, 'ECG Electrodes (Pack of 50)', 'Medical Supply', 1, 15.00, 1, 'Disposable ECG electrodes', NULL, NOW(), NOW()),
(5, 'ECG Paper Roll', 'Medical Supply', 2, 12.50, 1, 'Thermal paper for ECG printing', NULL, NOW(), NOW()),
(5, 'Cardiac Monitor', 'Medical Equipment', 1, 500.00, 0, 'Patient cardiac monitoring system', NULL, NOW(), NOW()),

-- Service 6: ECG/EKG Test
(6, 'ECG Electrodes (Pack of 10)', 'Medical Supply', 1, 3.00, 1, 'Disposable electrodes for ECG', NULL, NOW(), NOW()),
(6, 'ECG Gel', 'Medical Supply', 1, 8.00, 1, 'Conductive gel for ECG', NULL, NOW(), NOW()),
(6, 'ECG Machine', 'Medical Equipment', 1, 350.00, 0, '12-lead electrocardiogram machine', NULL, NOW(), NOW()),

-- Service 7: Echocardiogram
(7, 'Ultrasound Machine', 'Medical Equipment', 1, 3500.00, 0, 'Cardiac ultrasound imaging system', NULL, NOW(), NOW()),
(7, 'Ultrasound Gel', 'Medical Supply', 2, 10.00, 1, 'Conductive ultrasound gel', NULL, NOW(), NOW()),
(7, 'Ultrasound Probe Cover', 'Medical Supply', 1, 2.50, 1, 'Sterile probe covers', NULL, NOW(), NOW()),
(7, 'Image Printer Paper', 'Medical Supply', 1, 15.00, 1, 'High-quality ultrasound image paper', NULL, NOW(), NOW()),

-- Service 8: Cardiac Stress Test
(8, 'Treadmill', 'Medical Equipment', 1, 1200.00, 0, 'Medical-grade exercise treadmill', NULL, NOW(), NOW()),
(8, 'Blood Pressure Cuff (Ambulatory)', 'Medical Equipment', 1, 45.00, 0, 'Continuous BP monitoring cuff', NULL, NOW(), NOW()),
(8, 'EKG Electrodes (Pack of 50)', 'Medical Supply', 1, 18.00, 1, 'Disposable EKG electrodes', NULL, NOW(), NOW()),
(8, 'Oxygen Mask', 'Medical Supply', 1, 5.00, 1, 'Emergency oxygen mask', NULL, NOW(), NOW()),

-- Service 31: Holter Monitor
(31, 'Holter Monitor Device', 'Medical Equipment', 1, 800.00, 0, '24-hour ambulatory ECG recorder', NULL, NOW(), NOW()),
(31, 'Holter Monitor Electrodes', 'Medical Supply', 10, 2.50, 1, 'Adhesive electrodes for Holter', NULL, NOW(), NOW()),
(31, 'Holter Monitor Battery', 'Medical Supply', 2, 15.00, 1, 'Replacement battery for Holter', NULL, NOW(), NOW()),

-- Service 32: Blood Pressure Monitoring
(32, 'Ambulatory BP Monitor', 'Medical Equipment', 1, 450.00, 0, '24-hour blood pressure monitoring device', NULL, NOW(), NOW()),
(32, 'BP Monitor Cuff', 'Medical Supply', 2, 20.00, 1, 'Replacement cuffs for BP monitor', NULL, NOW(), NOW()),
(32, 'BP Monitor Battery', 'Medical Supply', 2, 10.00, 1, 'Replacement batteries', NULL, NOW(), NOW()),

-- =====================================================
-- PROVIDER 3 - Dental Services
-- =====================================================
-- Service 9: General Dental Checkup
(9, 'Dental Mirror', 'Dental Equipment', 1, 8.00, 0, 'Standard dental examination mirror', NULL, NOW(), NOW()),
(9, 'Dental Probe', 'Dental Equipment', 1, 6.00, 0, 'Dental explorer/probe', NULL, NOW(), NOW()),
(9, 'Dental Chair', 'Dental Equipment', 1, 2500.00, 0, 'Electric dental chair', NULL, NOW(), NOW()),
(9, 'Dental Light', 'Dental Equipment', 1, 450.00, 0, 'LED dental operating light', NULL, NOW(), NOW()),
(9, 'Dental X-Ray Sensor', 'Dental Equipment', 1, 600.00, 0, 'Digital X-ray sensor', NULL, NOW(), NOW()),

-- Service 10: Teeth Cleaning
(10, 'Ultrasonic Scaler', 'Dental Equipment', 1, 350.00, 0, 'Ultrasonic dental scaler', NULL, NOW(), NOW()),
(10, 'Dental Polish Prophy Paste', 'Dental Supply', 2, 8.00, 1, 'Prophylaxis polishing paste', NULL, NOW(), NOW()),
(10, 'Dental Floss', 'Dental Supply', 1, 3.00, 1, 'Professional dental floss', NULL, NOW(), NOW()),
(10, 'Disposable Dental Tips', 'Dental Supply', 5, 2.00, 1, 'Single-use dental tips', NULL, NOW(), NOW()),

-- Service 11: Dental X-Ray
(11, 'Dental X-Ray Machine', 'Dental Equipment', 1, 1800.00, 0, 'Digital dental X-ray machine', NULL, NOW(), NOW()),
(11, 'X-Ray Film (Pack of 10)', 'Dental Supply', 1, 12.00, 1, 'Dental X-ray films', NULL, NOW(), NOW()),
(11, 'Lead Apron', 'Dental Equipment', 1, 80.00, 0, 'X-ray protection lead apron', NULL, NOW(), NOW()),

-- Service 12: Root Canal Treatment
(12, 'Root Canal Kit', 'Dental Supply', 1, 45.00, 1, 'Complete endodontic procedure kit', NULL, NOW(), NOW()),
(12, 'Endodontic Files (Assorted)', 'Dental Supply', 5, 12.00, 1, 'Various sizes for root canal', NULL, NOW(), NOW()),
(12, 'Gutta-Percha Points', 'Dental Supply', 20, 1.50, 1, 'Root canal filling material', NULL, NOW(), NOW()),
(12, 'Dental Dam', 'Dental Supply', 1, 8.00, 1, 'Rubber dam for isolation', NULL, NOW(), NOW()),
(12, 'Irrigation Syringe', 'Dental Supply', 2, 5.00, 1, 'Root canal irrigation syringes', NULL, NOW(), NOW()),

-- Service 13: Teeth Whitening
(13, 'Whitening Gel', 'Dental Supply', 4, 15.00, 1, 'Professional teeth whitening gel', NULL, NOW(), NOW()),
(13, 'Whitening Trays', 'Dental Supply', 2, 20.00, 1, 'Customizable whitening trays', NULL, NOW(), NOW()),
(13, 'UV Curing Light', 'Dental Equipment', 1, 200.00, 0, 'LED curing light for whitening', NULL, NOW(), NOW()),
(13, 'Lip Retractor', 'Dental Equipment', 1, 12.00, 0, 'Dental lip retractor', NULL, NOW(), NOW()),

-- Service 33: Dental Crown
(33, 'Crown Preparation Kit', 'Dental Supply', 1, 35.00, 1, 'Kit for crown preparation', NULL, NOW(), NOW()),
(33, 'Dental Impression Material', 'Dental Supply', 2, 18.00, 1, 'Alginate impression material', NULL, NOW(), NOW()),
(33, 'Temporary Crown Material', 'Dental Supply', 1, 25.00, 1, 'Material for temporary crowns', NULL, NOW(), NOW()),
(33, 'Cement for Crowns', 'Dental Supply', 1, 15.00, 1, 'Permanent dental cement', NULL, NOW(), NOW()),

-- Service 34: Dental Implant
(34, 'Surgical Implant Kit', 'Dental Supply', 1, 200.00, 1, 'Complete surgical implant kit', NULL, NOW(), NOW()),
(34, 'Dental Implant', 'Dental Supply', 1, 150.00, 1, 'Titanium dental implant', NULL, NOW(), NOW()),
(34, 'Surgical Drill Set', 'Dental Equipment', 1, 350.00, 0, 'Implant surgical drill set', NULL, NOW(), NOW()),
(34, 'Surgical Sutures', 'Dental Supply', 2, 8.00, 1, 'Non-absorbable sutures', NULL, NOW(), NOW()),
(34, 'Sterile Surgical Gloves', 'Dental Supply', 2, 4.00, 1, 'Sterile surgical gloves', NULL, NOW(), NOW()),

-- Service 35: Braces Consultation
(35, 'Orthodontic Models', 'Dental Supply', 1, 20.00, 1, 'Study models for planning', NULL, NOW(), NOW()),
(35, 'Orthodontic Brackets', 'Dental Supply', 10, 4.00, 1, 'Assorted orthodontic brackets', NULL, NOW(), NOW()),
(35, 'Arch Wires', 'Dental Supply', 2, 12.00, 1, 'Various arch wire sizes', NULL, NOW(), NOW()),
(35, 'Elastic Bands', 'Dental Supply', 20, 0.50, 1, 'Orthodontic elastic bands', NULL, NOW(), NOW()),

-- =====================================================
-- PROVIDER 4 - Dermatology Services
-- =====================================================
-- Service 14: Dermatology Consultation
(14, 'Dermatoscope', 'Medical Equipment', 1, 300.00, 0, 'Dermatoscope for skin examination', NULL, NOW(), NOW()),
(14, 'Woods Lamp', 'Medical Equipment', 1, 120.00, 0, 'UV Wood\'s lamp for skin evaluation', NULL, NOW(), NOW()),

-- Service 15: Acne Treatment
(15, 'Acne Extraction Kit', 'Medical Supply', 1, 25.00, 1, 'Professional acne extraction tools', NULL, NOW(), NOW()),
(15, 'Chemical Peel Solution', 'Medical Supply', 1, 35.00, 1, 'Professional chemical peel solution', NULL, NOW(), NOW()),
(15, 'Post-Treatment Cream', 'Medical Supply', 1, 18.00, 1, 'Soothing post-treatment cream', NULL, NOW(), NOW()),

-- Service 16: Skin Biopsy
(16, 'Biopsy Punch Set', 'Medical Supply', 1, 45.00, 1, 'Disposable biopsy punch tools', NULL, NOW(), NOW()),
(16, 'Local Anesthetic', 'Medical Supply', 1, 12.00, 1, 'Lidocaine injection', NULL, NOW(), NOW()),
(16, 'Suture Kit', 'Medical Supply', 1, 15.00, 1, 'Surgical suture kit', NULL, NOW(), NOW()),
(16, 'Specimen Container', 'Medical Supply', 1, 3.00, 1, 'Formalin specimen container', NULL, NOW(), NOW()),

-- Service 17: Laser Skin Treatment
(17, 'Laser Device', 'Medical Equipment', 1, 5000.00, 0, 'Medical-grade laser treatment device', NULL, NOW(), NOW()),
(17, 'Laser Cooling Gel', 'Medical Supply', 2, 15.00, 1, 'Cooling gel for laser treatment', NULL, NOW(), NOW()),
(17, 'Protective Eye Shields', 'Medical Equipment', 1, 35.00, 0, 'Laser protection goggles', NULL, NOW(), NOW()),
(17, 'Laser Handpiece', 'Medical Equipment', 1, 400.00, 0, 'Replacement laser handpiece', NULL, NOW(), NOW()),

-- Service 18: Chemical Peel
(18, 'Chemical Peel Set', 'Medical Supply', 1, 50.00, 1, 'Complete chemical peel kit', NULL, NOW(), NOW()),
(18, 'Neutralizer Solution', 'Medical Supply', 1, 12.00, 1, 'Chemical peel neutralizer', NULL, NOW(), NOW()),
(18, 'Post-Peel Cream', 'Medical Supply', 1, 20.00, 1, 'Post-treatment cream', NULL, NOW(), NOW()),

-- Service 39: Botox Treatment
(39, 'Botox Injection Kit', 'Medical Supply', 1, 60.00, 1, 'Complete Botox injection kit', NULL, NOW(), NOW()),
(39, 'Botox Solution', 'Medical Supply', 1, 80.00, 1, 'Botox vial', NULL, NOW(), NOW()),
(39, 'Micro Needles', 'Medical Supply', 1, 12.00, 1, 'Fine gauge injection needles', NULL, NOW(), NOW()),
(39, 'Ice Pack', 'Medical Supply', 1, 8.00, 1, 'Pre-treatment ice pack', NULL, NOW(), NOW()),

-- Service 40: Dermatology Surgery
(40, 'Surgical Drape Kit', 'Medical Supply', 1, 12.00, 1, 'Sterile surgical drapes', NULL, NOW(), NOW()),
(40, 'Electrosurgical Unit', 'Medical Equipment', 1, 450.00, 0, 'Electrosurgery device', NULL, NOW(), NOW()),
(40, 'Surgical Blade Set', 'Medical Supply', 1, 18.00, 1, 'Assorted surgical blades', NULL, NOW(), NOW()),
(40, 'Hemostat Forceps', 'Medical Equipment', 2, 25.00, 0, 'Surgical hemostats', NULL, NOW(), NOW()),
(40, 'Suture Scissors', 'Medical Equipment', 1, 20.00, 0, 'Surgical scissors', NULL, NOW(), NOW()),

-- =====================================================
-- PROVIDER 5 - Laboratory & Imaging
-- =====================================================
-- Service 20: Blood Tests
(20, 'Blood Collection Tubes (10pcs)', 'Lab Supply', 5, 2.50, 1, 'Vacutainer tubes for blood collection', NULL, NOW(), NOW()),
(20, 'Needles (Pack of 10)', 'Lab Supply', 2, 3.00, 1, 'Blood collection needles', NULL, NOW(), NOW()),
(20, 'Alcohol Swabs', 'Lab Supply', 10, 0.50, 1, 'Disposable alcohol wipes', NULL, NOW(), NOW()),
(20, 'Tourniquet', 'Lab Supply', 1, 5.00, 1, 'Disposable tourniquet', NULL, NOW(), NOW()),
(20, 'Lab Requisition Forms', 'Administrative', 1, 2.00, 1, 'Laboratory test request forms', NULL, NOW(), NOW()),

-- Service 21: Urine Analysis
(21, 'Urine Collection Cups (10pcs)', 'Lab Supply', 2, 2.00, 1, 'Sterile urine collection cups', NULL, NOW(), NOW()),
(21, 'Urine Test Strips (50pcs)', 'Lab Supply', 1, 15.00, 1, 'Multiparameter urine test strips', NULL, NOW(), NOW()),
(21, 'Microscope Slides', 'Lab Supply', 5, 1.50, 1, 'Glass microscope slides', NULL, NOW(), NOW()),

-- Service 22: X-Ray Imaging
(22, 'X-Ray Cassette', 'Imaging Equipment', 2, 45.00, 0, 'Digital X-ray cassette', NULL, NOW(), NOW()),
(22, 'X-Ray Film', 'Imaging Supply', 10, 8.00, 1, 'X-ray films', NULL, NOW(), NOW()),
(22, 'Lead Apron', 'Imaging Equipment', 1, 80.00, 0, 'Lead apron for patient protection', NULL, NOW(), NOW()),
(22, 'X-Ray Markers', 'Imaging Supply', 1, 15.00, 1, 'Lead markers for X-ray positioning', NULL, NOW(), NOW()),

-- Service 23: Ultrasound Scan
(23, 'Ultrasound Machine', 'Imaging Equipment', 1, 3000.00, 0, 'Diagnostic ultrasound system', NULL, NOW(), NOW()),
(23, 'Ultrasound Gel', 'Imaging Supply', 3, 10.00, 1, 'Conductive ultrasound gel', NULL, NOW(), NOW()),
(23, 'Ultrasound Probe', 'Imaging Equipment', 2, 800.00, 0, 'Interchangeable ultrasound probes', NULL, NOW(), NOW()),
(23, 'Image Printer', 'Imaging Equipment', 1, 400.00, 0, 'Thermal image printer', NULL, NOW(), NOW()),
(23, 'Printer Paper', 'Imaging Supply', 2, 12.00, 1, 'Thermal printer paper', NULL, NOW(), NOW()),

-- Service 24: CT Scan
(24, 'CT Scanner', 'Imaging Equipment', 1, 15000.00, 0, 'Multi-slice CT scanner', NULL, NOW(), NOW()),
(24, 'Contrast Medium', 'Medical Supply', 2, 45.00, 1, 'IV contrast solution for CT', NULL, NOW(), NOW()),
(24, 'IV Catheter Kit', 'Medical Supply', 1, 8.00, 1, 'IV catheter for contrast injection', NULL, NOW(), NOW()),
(24, 'CT Table Pad', 'Imaging Equipment', 1, 120.00, 0, 'CT scanner table pad', NULL, NOW(), NOW()),

-- Service 41: MRI Scan
(41, 'MRI Scanner', 'Imaging Equipment', 1, 25000.00, 0, '1.5T MRI system', NULL, NOW(), NOW()),
(41, 'Gadolinium Contrast', 'Medical Supply', 2, 60.00, 1, 'MRI contrast agent', NULL, NOW(), NOW()),
(41, 'MRI Coil Set', 'Imaging Equipment', 3, 1200.00, 0, 'Various MRI coils', NULL, NOW(), NOW()),
(41, 'Ear Protection', 'Imaging Supply', 2, 25.00, 0, 'MRI-compatible earphones', NULL, NOW(), NOW()),
(41, 'MRI Patient Alarm', 'Imaging Equipment', 1, 80.00, 0, 'Patient emergency alarm system', NULL, NOW(), NOW()),

-- Service 42: Blood Donation Services
(42, 'Blood Collection Bag', 'Lab Supply', 1, 12.00, 1, 'Sterile blood collection bag', NULL, NOW(), NOW()),
(42, 'Blood Typing Kit', 'Lab Supply', 1, 10.00, 1, 'Blood type testing kit', NULL, NOW(), NOW()),
(42, 'Needle (16G)', 'Lab Supply', 1, 2.00, 1, '16-gauge blood collection needle', NULL, NOW(), NOW()),
(42, 'Antiseptic Solution', 'Lab Supply', 1, 5.00, 1, 'Skin antiseptic solution', NULL, NOW(), NOW()),

-- =====================================================
-- PROVIDER 6 - Physiotherapy
-- =====================================================
-- Service 26: Physiotherapy Assessment
(26, 'Goniometer', 'PT Equipment', 1, 15.00, 0, 'Joint angle measurement tool', NULL, NOW(), NOW()),
(26, 'Measuring Tape', 'PT Equipment', 1, 5.00, 0, 'Flexible measuring tape', NULL, NOW(), NOW()),
(26, 'Reflex Hammer', 'PT Equipment', 1, 12.00, 0, 'Neurological reflex hammer', NULL, NOW(), NOW()),
(26, 'Assessment Forms', 'Administrative', 3, 1.00, 1, 'Patient assessment documentation forms', NULL, NOW(), NOW()),

-- Service 27: Physical Therapy Session
(27, 'Therapy Table', 'PT Equipment', 1, 400.00, 0, 'Electric adjustable therapy table', NULL, NOW(), NOW()),
(27, 'Therapy Balls', 'PT Equipment', 2, 25.00, 0, 'Exercise therapy balls', NULL, NOW(), NOW()),
(27, 'Resistance Bands', 'PT Supply', 3, 12.00, 1, 'Various resistance levels', NULL, NOW(), NOW()),
(27, 'Towel Sets', 'PT Supply', 4, 5.00, 1, 'Therapy towels', NULL, NOW(), NOW()),
(27, 'Massage Oil', 'PT Supply', 1, 8.00, 1, 'Therapeutic massage oil', NULL, NOW(), NOW()),

-- Service 28: Sports Injury Rehabilitation
(28, 'Exercise Bike', 'PT Equipment', 1, 600.00, 0, 'Stationary exercise bike', NULL, NOW(), NOW()),
(28, 'Treadmill', 'PT Equipment', 1, 800.00, 0, 'Rehabilitation treadmill', NULL, NOW(), NOW()),
(28, 'Parallel Bars', 'PT Equipment', 1, 450.00, 0, 'Walking parallel bars', NULL, NOW(), NOW()),
(28, 'Weights Set', 'PT Equipment', 1, 100.00, 0, 'Various therapy weights', NULL, NOW(), NOW()),
(28, 'Balance Board', 'PT Equipment', 1, 35.00, 0, 'Balance training board', NULL, NOW(), NOW()),

-- Service 29: Massage Therapy
(29, 'Massage Table', 'PT Equipment', 1, 350.00, 0, 'Professional massage table', NULL, NOW(), NOW()),
(29, 'Massage Oil Set', 'PT Supply', 2, 15.00, 1, 'Various therapeutic oils', NULL, NOW(), NOW()),
(29, 'Hot Stones Set', 'PT Equipment', 1, 40.00, 0, 'Hot stone therapy set', NULL, NOW(), NOW()),
(29, 'Massage Linens', 'PT Supply', 3, 20.00, 1, 'Fresh linens for massage', NULL, NOW(), NOW()),

-- Service 43: Post-Surgery Rehabilitation
(43, 'Cryotherapy Pack', 'PT Equipment', 2, 25.00, 0, 'Ice packs for therapy', NULL, NOW(), NOW()),
(43, 'Heating Pad', 'PT Equipment', 1, 20.00, 0, 'Therapeutic heating pad', NULL, NOW(), NOW()),
(43, 'TENS Unit', 'PT Equipment', 1, 150.00, 0, 'Transcutaneous electrical nerve stimulator', NULL, NOW(), NOW()),
(43, 'Exercise Mat', 'PT Equipment', 1, 30.00, 0, 'Floor exercise mat', NULL, NOW(), NOW()),
(43, 'Pillow Support', 'PT Equipment', 2, 15.00, 0, 'Therapy support pillows', NULL, NOW(), NOW()),

-- Service 44: Geriatric Physiotherapy
(44, 'Walker', 'PT Equipment', 1, 120.00, 0, 'Mobility walker', NULL, NOW(), NOW()),
(44, 'Cane Set', 'PT Equipment', 1, 30.00, 0, 'Adjustable canes', NULL, NOW(), NOW()),
(44, 'Elevation Wedge', 'PT Equipment', 2, 18.00, 0, 'Leg elevation wedge', NULL, NOW(), NOW()),
(44, 'Grab Bars', 'PT Equipment', 1, 25.00, 0, 'Portable grab bars', NULL, NOW(), NOW()),

-- =====================================================
-- PROVIDER 7 - Mental Health Services
-- =====================================================
-- Service 30: Psychological Assessment
(30, 'Assessment Forms', 'Administrative', 5, 2.00, 1, 'Psychological testing forms', NULL, NOW(), NOW()),
(30, 'Cognitive Test Kit', 'Medical Supply', 1, 50.00, 1, 'Cognitive assessment tools', NULL, NOW(), NOW()),
(30, 'Computer with Software', 'Equipment', 1, 800.00, 0, 'Testing computer with software', NULL, NOW(), NOW()),
(30, 'Timer', 'Equipment', 1, 12.00, 0, 'Stopwatch timer', NULL, NOW(), NOW()),

-- Service 31: Cognitive Behavioral Therapy
(31, 'Workbook Materials', 'Administrative', 5, 8.00, 1, 'CBT workbooks and worksheets', NULL, NOW(), NOW()),
(31, 'Therapy Cards', 'Therapy Supply', 1, 15.00, 1, 'CBT and emotion cards', NULL, NOW(), NOW()),
(31, 'Art Therapy Materials', 'Therapy Supply', 1, 20.00, 1, 'Art supplies for therapy', NULL, NOW(), NOW()),

-- Service 32: Psychiatric Consultation
(32, 'Prescription Pad', 'Medical Supply', 1, 5.00, 1, 'Prescription forms', NULL, NOW(), NOW()),
(32, 'Medical Reference Books', 'Equipment', 1, 120.00, 0, 'Psychiatric reference materials', NULL, NOW(), NOW()),
(32, 'Computer for Records', 'Equipment', 1, 600.00, 0, 'Computer for EMR', NULL, NOW(), NOW()),

-- Service 33: Counseling Session
(33, 'Counseling Room Kit', 'Therapy Supply', 1, 10.00, 1, 'Counseling materials', NULL, NOW(), NOW()),
(33, 'Therapy Journals', 'Therapy Supply', 2, 8.00, 1, 'Patient therapy journals', NULL, NOW(), NOW()),
(33, 'Relaxation CD', 'Therapy Supply', 1, 12.00, 1, 'Guided relaxation audio', NULL, NOW(), NOW()),

-- Service 45: Group Therapy
(45, 'Group Room Setup', 'Equipment', 1, 50.00, 0, 'Group therapy room equipment', NULL, NOW(), NOW()),
(45, 'Chairs (10)', 'Equipment', 10, 35.00, 0, 'Comfortable group chairs', NULL, NOW(), NOW()),
(45, 'Whiteboard', 'Equipment', 1, 25.00, 0, 'Whiteboard for group activities', NULL, NOW(), NOW()),
(45, 'Group Worksheets', 'Administrative', 10, 1.00, 1, 'Group therapy worksheets', NULL, NOW(), NOW()),

-- Service 46: Family Therapy
(46, 'Family Therapy Kit', 'Therapy Supply', 1, 25.00, 1, 'Family therapy resources', NULL, NOW(), NOW()),
(46, 'Family Assessment Tools', 'Therapy Supply', 1, 30.00, 1, 'Family evaluation materials', NULL, NOW(), NOW()),
(46, 'Recording Device', 'Equipment', 1, 80.00, 0, 'Audio recording device (consent required)', NULL, NOW(), NOW()),

-- Service 47: Online Therapy Session
(47, 'Webcam', 'Equipment', 1, 50.00, 0, 'HD webcam for virtual sessions', NULL, NOW(), NOW()),
(47, 'Headset', 'Equipment', 1, 40.00, 0, 'Noise-canceling headset', NULL, NOW(), NOW()),
(47, 'Virtual Background', 'Equipment', 1, 15.00, 1, 'Professional virtual background', NULL, NOW(), NOW()),
(47, 'Therapy Software', 'Equipment', 1, 150.00, 0, 'Telehealth therapy platform', NULL, NOW(), NOW());

desc provider_organisation;

select * from notification;
select * from product_provider_type;
desc person_details;
select * from product_provider, provider_details where product_provider.product_provider_details_id = provider_details.idprovider_details_id ;
desc notification;
desc management_rule;
select * from recipe;
select * from notification;
select * from management_rule;
select * from product_provider;
delete from management_rule where id_management_rule = 19;
desc wallet;
desc payment;
desc money_transaction;
desc staff_role;
desc provided_service;
desc provided_service_category;
desc service_staff_requirement;
desc service_resource_requirement;
desc ordered_service;
desc ordered_item;
