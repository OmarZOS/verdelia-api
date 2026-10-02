CREATE DATABASE  IF NOT EXISTS "verdelia" /*!40100 DEFAULT CHARACTER SET utf8mb3 */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `verdelia`;
-- MySQL dump 10.13  Distrib 8.0.36, for Linux (x86_64)
--
-- Host: dbaas-db-10408380-do-user-13698920-0.e.db.ondigitalocean.com    Database: verdelia
-- ------------------------------------------------------
-- Server version	8.0.35

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
SET @MYSQLDUMP_TEMP_LOG_BIN = @@SESSION.SQL_LOG_BIN;
SET @@SESSION.SQL_LOG_BIN= 0;

--
-- GTID state at the beginning of the backup 
--

SET @@GLOBAL.GTID_PURGED=/*!80000 '+'*/ 'aab6d081-fb37-11ef-a370-aebcaae0155a:1-702';

--
-- Table structure for table `address`
--

DROP TABLE IF EXISTS `address`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `address` (
  `id_address` int NOT NULL AUTO_INCREMENT,
  `address_street` varchar(45) DEFAULT NULL,
  `address_city` varchar(45) DEFAULT NULL,
  `address_postal_code` varchar(45) DEFAULT NULL,
  `address_country` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`id_address`)
) ENGINE=InnoDB AUTO_INCREMENT=24 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `app_user`
--

DROP TABLE IF EXISTS `app_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `app_user` (
  `id_app_user` int NOT NULL AUTO_INCREMENT,
  `app_user_name` varchar(100) DEFAULT NULL,
  `app_user_password` varchar(256) DEFAULT NULL,
  `app_user_person_id` int DEFAULT NULL,
  `app_user_type_id` int DEFAULT NULL,
  `app_user_preferences` text,
  `app_user_last_active` datetime DEFAULT NULL,
  `app_user_last_updated` datetime DEFAULT NULL,
  `app_user_creation` datetime DEFAULT NULL,
  `app_user_image_url` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id_app_user`),
  KEY `fk_app_user_3_idx` (`app_user_person_id`),
  KEY `fk_app_user_1_idx` (`app_user_type_id`),
  CONSTRAINT `fk_app_user_1` FOREIGN KEY (`app_user_type_id`) REFERENCES `app_user_type` (`id_app_user_type`),
  CONSTRAINT `fk_app_user_3` FOREIGN KEY (`app_user_person_id`) REFERENCES `person` (`id_person`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `app_user_type`
--

DROP TABLE IF EXISTS `app_user_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `app_user_type` (
  `id_app_user_type` int NOT NULL AUTO_INCREMENT,
  `app_user_type_desc` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`id_app_user_type`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `blood_type`
--

DROP TABLE IF EXISTS `blood_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `blood_type` (
  `id_blood_type` int NOT NULL AUTO_INCREMENT,
  `blood_type_desc` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`id_blood_type`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `comment`
--

DROP TABLE IF EXISTS `comment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `comment` (
  `idcomment` int NOT NULL AUTO_INCREMENT,
  `comment_owner` int DEFAULT NULL,
  `comment_content` text,
  `replying_to` int DEFAULT NULL,
  `comment_timestamp` datetime DEFAULT NULL,
  `comment_visibility` tinyint DEFAULT NULL,
  PRIMARY KEY (`idcomment`),
  KEY `fk_comment_1_idx` (`replying_to`),
  KEY `fk_comment_2_idx` (`comment_owner`),
  CONSTRAINT `fk_comment_1` FOREIGN KEY (`replying_to`) REFERENCES `comment` (`idcomment`),
  CONSTRAINT `fk_comment_2` FOREIGN KEY (`comment_owner`) REFERENCES `app_user` (`id_app_user`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `comment_reaction`
--

DROP TABLE IF EXISTS `comment_reaction`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `comment_reaction` (
  `id_comment_reaction` int NOT NULL AUTO_INCREMENT,
  `comment_reacting_user` int DEFAULT NULL,
  `comment_reaction_ref` int DEFAULT NULL,
  `reacted_on_comment` int DEFAULT NULL,
  PRIMARY KEY (`id_comment_reaction`),
  KEY `fk_product_reaction_1_idx` (`comment_reacting_user`),
  KEY `fk_product_reaction_2_idx` (`comment_reaction_ref`),
  KEY `fk_product_reaction_30_idx` (`reacted_on_comment`),
  CONSTRAINT `fk_product_reaction_11` FOREIGN KEY (`comment_reacting_user`) REFERENCES `app_user` (`id_app_user`),
  CONSTRAINT `fk_product_reaction_21` FOREIGN KEY (`comment_reaction_ref`) REFERENCES `reaction` (`id_reaction`),
  CONSTRAINT `fk_product_reaction_30` FOREIGN KEY (`reacted_on_comment`) REFERENCES `comment` (`idcomment`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `disease_severity`
--

DROP TABLE IF EXISTS `disease_severity`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `disease_severity` (
  `id_disease_severity` int NOT NULL AUTO_INCREMENT,
  `disease_severity_desc` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`id_disease_severity`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ingredient`
--

DROP TABLE IF EXISTS `ingredient`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ingredient` (
  `id_ingredient` int NOT NULL AUTO_INCREMENT,
  `ingredient_name` varchar(45) DEFAULT NULL,
  `ingredient_icon` text,
  PRIMARY KEY (`id_ingredient`)
) ENGINE=InnoDB AUTO_INCREMENT=63 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `location`
--

DROP TABLE IF EXISTS `location`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `location` (
  `id_location` int NOT NULL AUTO_INCREMENT,
  `location_position` point NOT NULL,
  `location_name` varchar(45) DEFAULT NULL,
  `location_address_id` int DEFAULT NULL,
  PRIMARY KEY (`id_location`),
  KEY `fk_location_1_idx` (`location_address_id`),
  SPATIAL KEY `spatial` (`location_position`),
  CONSTRAINT `fk_location_1` FOREIGN KEY (`location_address_id`) REFERENCES `address` (`id_address`)
) ENGINE=InnoDB AUTO_INCREMENT=73 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ordered_item`
--

DROP TABLE IF EXISTS `ordered_item`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ordered_item` (
  `id_ordered_item` int NOT NULL AUTO_INCREMENT,
  `ordered_product_id` int DEFAULT NULL,
  `ordered_quantity` varchar(100) DEFAULT NULL,
  `applied_vat` double DEFAULT NULL,
  `order_ref` int DEFAULT NULL,
  `unit_price` double DEFAULT NULL,
  `product_discount` double DEFAULT NULL,
  PRIMARY KEY (`id_ordered_item`),
  KEY `fk_ordered_item_1_idx` (`ordered_product_id`),
  KEY `fk_ordered_item_3_idx` (`order_ref`),
  CONSTRAINT `fk_ordered_item_1` FOREIGN KEY (`ordered_product_id`) REFERENCES `product` (`id_product`),
  CONSTRAINT `fk_ordered_item_3` FOREIGN KEY (`order_ref`) REFERENCES `placed_order` (`id_placed_order`)
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `patient`
--

DROP TABLE IF EXISTS `patient`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `patient` (
  `id_patient` int NOT NULL AUTO_INCREMENT,
  `patient_person_id` int DEFAULT NULL,
  `patient_disease_severity_id` int DEFAULT NULL,
  PRIMARY KEY (`id_patient`),
  KEY `fk_patient_1_idx` (`patient_person_id`),
  KEY `fk_patient_2_idx` (`patient_disease_severity_id`),
  CONSTRAINT `fk_patient_1` FOREIGN KEY (`patient_person_id`) REFERENCES `person` (`id_person`),
  CONSTRAINT `fk_patient_2` FOREIGN KEY (`patient_disease_severity_id`) REFERENCES `disease_severity` (`id_disease_severity`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `person`
--

DROP TABLE IF EXISTS `person`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `person` (
  `id_person` int NOT NULL AUTO_INCREMENT,
  `person_details_id` int DEFAULT NULL,
  `person_blood_type_id` int DEFAULT NULL,
  `person_location_id` int DEFAULT NULL,
  PRIMARY KEY (`id_person`),
  KEY `fk_person_1_idx` (`person_details_id`),
  KEY `fk_person_2_idx` (`person_blood_type_id`),
  KEY `fk_person_3_idx` (`person_location_id`),
  CONSTRAINT `fk_person_1` FOREIGN KEY (`person_details_id`) REFERENCES `person_details` (`id_person_details`),
  CONSTRAINT `fk_person_2` FOREIGN KEY (`person_blood_type_id`) REFERENCES `blood_type` (`id_blood_type`),
  CONSTRAINT `fk_person_3` FOREIGN KEY (`person_location_id`) REFERENCES `location` (`id_location`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `person_details`
--

DROP TABLE IF EXISTS `person_details`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `person_details` (
  `id_person_details` int NOT NULL AUTO_INCREMENT,
  `person_first_name` varchar(45) DEFAULT NULL,
  `person_last_name` varchar(45) DEFAULT NULL,
  `person_birth_date` date DEFAULT NULL,
  `person_gender` varchar(45) DEFAULT NULL,
  `person_nationality` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`id_person_details`)
) ENGINE=InnoDB AUTO_INCREMENT=19 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `placed_order`
--

DROP TABLE IF EXISTS `placed_order`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `placed_order` (
  `id_placed_order` int NOT NULL AUTO_INCREMENT,
  `ordered_timestamp` datetime DEFAULT NULL,
  `order_discount` double DEFAULT NULL,
  `total_price` double DEFAULT NULL,
  `ordering_user_id` int DEFAULT NULL,
  PRIMARY KEY (`id_placed_order`),
  KEY `fk_placed_order_1_idx` (`ordering_user_id`),
  CONSTRAINT `fk_placed_order_1` FOREIGN KEY (`ordering_user_id`) REFERENCES `app_user` (`id_app_user`)
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `presented_symptom`
--

DROP TABLE IF EXISTS `presented_symptom`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `presented_symptom` (
  `id_presented_symptom` int NOT NULL AUTO_INCREMENT,
  `presented_symptom_ref_symptoms_occurence` int DEFAULT NULL,
  `presented_symptom_ref_symptom` int DEFAULT NULL,
  PRIMARY KEY (`id_presented_symptom`),
  KEY `fk_presented_symptom_1_idx` (`presented_symptom_ref_symptom`),
  KEY `fk_presented_symptom_2_idx` (`presented_symptom_ref_symptoms_occurence`),
  CONSTRAINT `fk_presented_symptom_1` FOREIGN KEY (`presented_symptom_ref_symptom`) REFERENCES `symptom` (`id_symptom`),
  CONSTRAINT `fk_presented_symptom_2` FOREIGN KEY (`presented_symptom_ref_symptoms_occurence`) REFERENCES `symptoms_occurence` (`id_symptoms_occurence`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `product`
--

DROP TABLE IF EXISTS `product`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `product` (
  `id_product` int NOT NULL AUTO_INCREMENT,
  `product_name` varchar(45) DEFAULT NULL,
  `product_brand` varchar(45) DEFAULT NULL,
  `product_provider_id` int DEFAULT NULL,
  `product_category_id` int DEFAULT NULL,
  `product_barcode` varchar(45) DEFAULT NULL,
  `last_updated` datetime DEFAULT NULL,
  `created` datetime DEFAULT NULL,
  `product_description` varchar(300) DEFAULT NULL,
  `product_price` double DEFAULT NULL,
  `product_quantity` int DEFAULT NULL,
  `product_quantifier` varchar(45) DEFAULT NULL,
  `product_owner` int DEFAULT NULL,
  PRIMARY KEY (`id_product`),
  KEY `fk_product_1_idx` (`product_provider_id`),
  KEY `fk_product_2_idx` (`product_category_id`),
  KEY `fk_product_3_idx` (`product_owner`),
  CONSTRAINT `fk_product_1` FOREIGN KEY (`product_provider_id`) REFERENCES `product_provider` (`id_product_provider`),
  CONSTRAINT `fk_product_2` FOREIGN KEY (`product_category_id`) REFERENCES `product_category` (`id_product_category`),
  CONSTRAINT `fk_product_3` FOREIGN KEY (`product_owner`) REFERENCES `app_user` (`id_app_user`)
) ENGINE=InnoDB AUTO_INCREMENT=69 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `product_category`
--

DROP TABLE IF EXISTS `product_category`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `product_category` (
  `id_product_category` int NOT NULL AUTO_INCREMENT,
  `product_category_desc` varchar(45) DEFAULT NULL,
  `product_category_icon` text,
  PRIMARY KEY (`id_product_category`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `product_image`
--

DROP TABLE IF EXISTS `product_image`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `product_image` (
  `id_product_image` int NOT NULL AUTO_INCREMENT,
  `product_image_url` varchar(255) DEFAULT NULL,
  `product_ref_id` int DEFAULT NULL,
  PRIMARY KEY (`id_product_image`),
  KEY `fk_product_image_1_idx` (`product_ref_id`),
  CONSTRAINT `fk_product_image_1` FOREIGN KEY (`product_ref_id`) REFERENCES `product` (`id_product`)
) ENGINE=InnoDB AUTO_INCREMENT=22 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `product_provider`
--

DROP TABLE IF EXISTS `product_provider`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `product_provider` (
  `id_product_provider` int NOT NULL AUTO_INCREMENT,
  `product_provider_details_id` int DEFAULT NULL,
  `product_provider_type_id` int DEFAULT NULL,
  `product_provider_location_id` int DEFAULT NULL,
  `product_provider_org_id` int DEFAULT NULL,
  `product_provider_owner` int DEFAULT NULL,
  PRIMARY KEY (`id_product_provider`),
  KEY `fk_product_provider_3_idx` (`product_provider_details_id`),
  KEY `fk_product_provider_1_idx` (`product_provider_type_id`),
  KEY `fk_product_provider_4_idx` (`product_provider_location_id`),
  KEY `fk_product_provider_2_idx` (`product_provider_org_id`),
  KEY `fk_product_provider_5_idx` (`product_provider_owner`),
  CONSTRAINT `fk_product_provider_1` FOREIGN KEY (`product_provider_type_id`) REFERENCES `product_provider_type` (`id_product_provider_type`),
  CONSTRAINT `fk_product_provider_2` FOREIGN KEY (`product_provider_org_id`) REFERENCES `provider_organisation` (`idprovider_organisation`),
  CONSTRAINT `fk_product_provider_3` FOREIGN KEY (`product_provider_details_id`) REFERENCES `provider_details` (`idprovider_details_id`),
  CONSTRAINT `fk_product_provider_4` FOREIGN KEY (`product_provider_location_id`) REFERENCES `location` (`id_location`),
  CONSTRAINT `fk_product_provider_5` FOREIGN KEY (`product_provider_owner`) REFERENCES `app_user` (`id_app_user`)
) ENGINE=InnoDB AUTO_INCREMENT=57 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `product_provider_type`
--

DROP TABLE IF EXISTS `product_provider_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `product_provider_type` (
  `id_product_provider_type` int NOT NULL AUTO_INCREMENT,
  `product_provider_type_desc` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`id_product_provider_type`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `product_reaction`
--

DROP TABLE IF EXISTS `product_reaction`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `product_reaction` (
  `id_product_reaction` int NOT NULL AUTO_INCREMENT,
  `product_reacting_user` int DEFAULT NULL,
  `product_reaction_ref` int DEFAULT NULL,
  `reacted_on_product` int DEFAULT NULL,
  PRIMARY KEY (`id_product_reaction`),
  KEY `fk_product_reaction_1_idx` (`product_reacting_user`),
  KEY `fk_product_reaction_2_idx` (`product_reaction_ref`),
  KEY `fk_product_reaction_3_idx` (`reacted_on_product`),
  CONSTRAINT `fk_product_reaction_1` FOREIGN KEY (`product_reacting_user`) REFERENCES `app_user` (`id_app_user`),
  CONSTRAINT `fk_product_reaction_2` FOREIGN KEY (`product_reaction_ref`) REFERENCES `reaction` (`id_reaction`),
  CONSTRAINT `fk_product_reaction_3` FOREIGN KEY (`reacted_on_product`) REFERENCES `product` (`id_product`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `provider_details`
--

DROP TABLE IF EXISTS `provider_details`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `provider_details` (
  `idprovider_details_id` int NOT NULL AUTO_INCREMENT,
  `provider_name` varchar(45) DEFAULT NULL,
  `provider_contact_info` text,
  PRIMARY KEY (`idprovider_details_id`)
) ENGINE=InnoDB AUTO_INCREMENT=37 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `provider_organisation`
--

DROP TABLE IF EXISTS `provider_organisation`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `provider_organisation` (
  `idprovider_organisation` int NOT NULL AUTO_INCREMENT,
  `provider_organisation_name` varchar(45) DEFAULT NULL,
  `provider_organisation_desc` varchar(300) DEFAULT NULL,
  PRIMARY KEY (`idprovider_organisation`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `reaction`
--

DROP TABLE IF EXISTS `reaction`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `reaction` (
  `id_reaction` int NOT NULL AUTO_INCREMENT,
  `reaction_type` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`id_reaction`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `recipe`
--

DROP TABLE IF EXISTS `recipe`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `recipe` (
  `id_recipe` int NOT NULL AUTO_INCREMENT,
  `recipe_owner_id` int DEFAULT NULL,
  `recipe_category_id` int DEFAULT NULL,
  `recipe_preparation_time` varchar(45) DEFAULT NULL,
  `recipe_instructions` text,
  `recipe_name` varchar(45) DEFAULT NULL,
  `recipe_description` varchar(300) DEFAULT NULL,
  `recipe_creation` datetime DEFAULT NULL,
  `recipe_last_updated` datetime DEFAULT NULL,
  PRIMARY KEY (`id_recipe`),
  KEY `fk_recipe_1_idx` (`recipe_owner_id`),
  KEY `fk_recipe_2_idx` (`recipe_category_id`),
  CONSTRAINT `fk_recipe_1` FOREIGN KEY (`recipe_owner_id`) REFERENCES `app_user` (`id_app_user`),
  CONSTRAINT `fk_recipe_2` FOREIGN KEY (`recipe_category_id`) REFERENCES `recipe_category` (`id_recipe_category`)
) ENGINE=InnoDB AUTO_INCREMENT=20 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `recipe_category`
--

DROP TABLE IF EXISTS `recipe_category`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `recipe_category` (
  `id_recipe_category` int NOT NULL AUTO_INCREMENT,
  `recipe_category_desc` varchar(45) DEFAULT NULL,
  `recipe_category_icon` text,
  PRIMARY KEY (`id_recipe_category`)
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `recipe_contains_ingredient`
--

DROP TABLE IF EXISTS `recipe_contains_ingredient`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `recipe_contains_ingredient` (
  `idrecipe_contains_ingredient_id` int NOT NULL AUTO_INCREMENT,
  `containing_recipe_id` int DEFAULT NULL,
  `contained_ingredient_id` int DEFAULT NULL,
  `contained_quantity` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`idrecipe_contains_ingredient_id`),
  KEY `fk_recipe_contains_ingredient_1_idx` (`containing_recipe_id`),
  KEY `fk_recipe_contains_ingredient_2_idx` (`contained_ingredient_id`),
  CONSTRAINT `fk_recipe_contains_ingredient_1` FOREIGN KEY (`containing_recipe_id`) REFERENCES `recipe` (`id_recipe`),
  CONSTRAINT `fk_recipe_contains_ingredient_2` FOREIGN KEY (`contained_ingredient_id`) REFERENCES `ingredient` (`id_ingredient`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `recipe_image`
--

DROP TABLE IF EXISTS `recipe_image`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `recipe_image` (
  `id_recipe_image` int NOT NULL AUTO_INCREMENT,
  `recipe_image_url` varchar(255) DEFAULT NULL,
  `recipe_ref_id` int DEFAULT NULL,
  PRIMARY KEY (`id_recipe_image`),
  KEY `fk_recipe_image_1_idx` (`recipe_ref_id`),
  CONSTRAINT `fk_recipe_image_1` FOREIGN KEY (`recipe_ref_id`) REFERENCES `recipe` (`id_recipe`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `recipe_reaction`
--

DROP TABLE IF EXISTS `recipe_reaction`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `recipe_reaction` (
  `id_recipe_reaction` int NOT NULL AUTO_INCREMENT,
  `recipe_reacting_user` int DEFAULT NULL,
  `recipe_reaction_ref` int DEFAULT NULL,
  `reacted_on_recipe` int DEFAULT NULL,
  PRIMARY KEY (`id_recipe_reaction`),
  KEY `fk_product_reaction_1_idx` (`recipe_reacting_user`),
  KEY `fk_product_reaction_2_idx` (`recipe_reaction_ref`),
  KEY `fk_recipe_reaction_1_idx` (`reacted_on_recipe`),
  CONSTRAINT `fk_product_reaction_10` FOREIGN KEY (`recipe_reacting_user`) REFERENCES `app_user` (`id_app_user`),
  CONSTRAINT `fk_product_reaction_20` FOREIGN KEY (`recipe_reaction_ref`) REFERENCES `reaction` (`id_reaction`),
  CONSTRAINT `fk_recipe_reaction_1` FOREIGN KEY (`reacted_on_recipe`) REFERENCES `recipe` (`id_recipe`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `report`
--

DROP TABLE IF EXISTS `report`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `report` (
  `id_report` int NOT NULL AUTO_INCREMENT,
  `report_text` text,
  `report_owner` int DEFAULT NULL,
  PRIMARY KEY (`id_report`),
  KEY `fk_report_1_idx` (`report_owner`),
  CONSTRAINT `fk_report_1` FOREIGN KEY (`report_owner`) REFERENCES `app_user` (`id_app_user`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `serology`
--

DROP TABLE IF EXISTS `serology`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `serology` (
  `id_serology` int NOT NULL AUTO_INCREMENT,
  `indicator_id` int DEFAULT NULL,
  `serology_date` date DEFAULT NULL,
  `patient_id` int DEFAULT NULL,
  `indicator_value` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`id_serology`),
  KEY `fk_diagnosis_1_idx` (`patient_id`),
  KEY `fk_serology_1_idx` (`indicator_id`),
  CONSTRAINT `fk_diagnosis_1` FOREIGN KEY (`patient_id`) REFERENCES `patient` (`id_patient`),
  CONSTRAINT `fk_serology_1` FOREIGN KEY (`indicator_id`) REFERENCES `serology_indicator` (`id_serology_indicator`)
) ENGINE=InnoDB AUTO_INCREMENT=31 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `serology_indicator`
--

DROP TABLE IF EXISTS `serology_indicator`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `serology_indicator` (
  `id_serology_indicator` int NOT NULL AUTO_INCREMENT,
  `serology_indicator_name` varchar(45) DEFAULT NULL,
  `serology_indicator_desc` varchar(300) DEFAULT NULL,
  PRIMARY KEY (`id_serology_indicator`)
) ENGINE=InnoDB AUTO_INCREMENT=27 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `symptom`
--

DROP TABLE IF EXISTS `symptom`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `symptom` (
  `id_symptom` int NOT NULL AUTO_INCREMENT,
  `symptom_name` varchar(45) DEFAULT NULL,
  `symptom_desc` varchar(300) DEFAULT NULL,
  PRIMARY KEY (`id_symptom`)
) ENGINE=InnoDB AUTO_INCREMENT=106 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `symptoms_occurence`
--

DROP TABLE IF EXISTS `symptoms_occurence`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `symptoms_occurence` (
  `id_symptoms_occurence` int NOT NULL AUTO_INCREMENT,
  `symptoms_occurence_submission_time` datetime DEFAULT NULL,
  `symptoms_occurence_reason` varchar(300) DEFAULT NULL,
  `reason_date` datetime DEFAULT NULL,
  `symptoms_occurence_ref_patient` int DEFAULT NULL,
  PRIMARY KEY (`id_symptoms_occurence`),
  KEY `fk_symptoms_causality_1_idx` (`symptoms_occurence_ref_patient`),
  CONSTRAINT `fk_symptoms_causality_1` FOREIGN KEY (`symptoms_occurence_ref_patient`) REFERENCES `patient` (`id_patient`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
SET @@SESSION.SQL_LOG_BIN = @MYSQLDUMP_TEMP_LOG_BIN;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-08-16 19:54:35




INSERT INTO `verdelia`.`app_user_type` ( `app_user_type_desc`) VALUES
( 'Client'),
( 'Admin'),
( 'Cooking chef'),
( 'Supplier');

INSERT INTO `verdelia`.`blood_type` ( `blood_type_desc`) VALUES
('O+'),
('A+'),
('B+'),
('AB+'),
('O-'),
('A-'),
('B-'),
('AB-');

INSERT INTO `verdelia`.`product_category` ( `product_category_desc`) VALUES
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

INSERT INTO `verdelia`.`product_provider_type` ( `product_provider_type_desc`) VALUES
('Restaurant'),
('Bakery'),
('Factory'),
('Supermarket'),
("Grocery Store"),
("Distributor");


INSERT INTO `verdelia`.`recipe_category` ( `recipe_category_desc`) VALUES
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







-- INSERT INTO `verdelia`.`provider_details` (`provider_name`, `provider_contact_info`) VALUES
-- ('Smart Technologies', 'Phone: +213 609 1126074, Email: mjmhqzs@example.com'),
-- ('Eco Systems', 'Phone: +213 606 7668104, Email: fbkulvv@example.com'),
-- ('Smart Corporation', 'Phone: +213 675 9893109, Email: jkjkbvj@example.com'),
-- ('Health Industries', 'Phone: +213 604 3331217, Email: uxsjtfy@example.com'),
-- ('Tech Partners', 'Phone: +213 641 7681417, Email: lksfdtv@example.com'),
-- ('Green Enterprises', 'Phone: +213 627 6240490, Email: lcaleej@example.com'),
-- ('Green Consulting', 'Phone: +213 641 9897301, Email: yfpplzr@example.com'),
-- ('Smart Corporation', 'Phone: +213 611 5823312, Email: kbcxhps@example.com'),
-- ('Eco Partners', 'Phone: +213 640 4406431, Email: jqaeljx@example.com'),
-- ('Innovative Enterprises', 'Phone: +213 600 6854116, Email: aakgoqm@example.com'),
-- ('Global Solutions', 'Phone: +213 661 6236168, Email: unadtjk@example.com'),
-- ('Green Corporation', 'Phone: +213 653 3147806, Email: qrhkloy@example.com'),
-- ('Prime Technologies', 'Phone: +213 608 5803282, Email: mplnqpb@example.com'),
-- ('Innovative Corporation', 'Phone: +213 682 5387637, Email: ongcbmo@example.com'),
-- ('Prime Technologies', 'Phone: +213 635 4163080, Email: yvqcumv@example.com'),
-- ('Global Services', 'Phone: +213 667 6194095, Email: npxexni@example.com'),
-- ('Bright Solutions', 'Phone: +213 609 5237134, Email: rospbtg@example.com'),
-- ('Health Industries', 'Phone: +213 674 4584401, Email: iqqrnoz@example.com'),
-- ('Tech Consulting', 'Phone: +213 639 6918018, Email: mzgzxmy@example.com'),
-- ('Dynamic Technologies', 'Phone: +213 622 5664114, Email: nqhtvuh@example.com'),
-- ('Bright Solutions', 'Phone: +213 655 1527858, Email: eorfakx@example.com'),
-- ('Bright Solutions', 'Phone: +213 688 7400754, Email: vpltnqs@example.com'),
-- ('Prime Consulting', 'Phone: +213 611 3908501, Email: vcfjnyj@example.com'),
-- ('Prime Solutions', 'Phone: +213 690 5009291, Email: emdrlxj@example.com'),
-- ('Smart Technologies', 'Phone: +213 644 9988918, Email: zzpbmpp@example.com'),
-- ('Bright Industries', 'Phone: +213 684 3960601, Email: prieuim@example.com'),
-- ('Global Technologies', 'Phone: +213 638 7617405, Email: mrphlvv@example.com'),
-- ('Eco Consulting', 'Phone: +213 662 6706103, Email: khphupc@example.com'),
-- ('Green Partners', 'Phone: +213 635 9913502, Email: wlfnjcv@example.com'),
-- ('Global Consulting', 'Phone: +213 643 2839789, Email: upgoewx@example.com');




-- INSERT INTO `verdelia`.`location` (`location_position`, `location_name`) VALUES
-- ('31.4704', '10.5995','Algiers'),
-- ('21.9235', '6.6383','Oran'),
-- ('33.3383', '-0.7512','Constantine'),
-- ('30.3659', '11.3850','Annaba'),
-- ('31.2074', '8.0155','Blida'),
-- ('32.3339', '-0.0670','Batna'),
-- ('26.7321', '9.2440','Sétif'),
-- ('33.0055', '-5.9117','Tlemcen'),
-- ('30.2891', '2.5290','Biskra'),
-- ('29.1807', '3.8425','Béjaïa'),
-- ('26.1838', '-7.1486','Tizi Ouzou'),
-- ('32.5957', '-3.5024','Chlef'),
-- ('34.7306', '8.1922','Sidi Bel Abbès'),
-- ('31.0770', '-1.8179','Djelfa'),
-- ('26.7578', '11.0753','Guelma'),
-- ('28.5457', '-5.5282','Mascara'),
-- ('33.0417', '1.0216','Skikda'),
-- ('29.2655', '11.9160','Ouargla'),
-- ('33.7725', '1.0248','Relizane'),
-- ('27.2296', '-7.0964','Tiaret'),
-- ('36.0817', '9.7897','Tindouf'),
-- ('31.9784', '1.2928','Laghouat'),
-- ('30.6563', '2.6474','Tebessa'),
-- ('31.1872', '9.6848','Mostaganem'),
-- ('24.3694', '-8.1194','Bordj Bou Arreridj'),
-- ('19.3143', '2.7007','Boumerdès'),
-- ('26.6551', '-2.8732','Ain Temouchent'),
-- ('33.1827', '4.8710','Médéa'),
-- ('31.6452', '1.0392','El Oued'),
-- ('25.2283', '-0.0806','Khenchela');

-- Insert data into the address table
INSERT INTO `verdelia`.`address` (`address_street`, `address_city`, `address_country`)
VALUES
('Rue Lamameri Ali', 'Bouzareah', 'Algeria'),
('Avenue Houari Boumedien', 'Bordj El Bahri', 'Algeria'),
('Route de Dar El Beida', 'Bab Ezzouar', 'Algeria'),
('N63', 'Mahelma', 'Algeria'),
('Khraicia', 'Khraicia', 'Algeria'),
('Cheraga', 'Chéraga', 'Algeria');


-- Insertions for Amissan -gluten free-
INSERT INTO `verdelia`.`provider_details` (`provider_name`, `provider_contact_info`) VALUES
('Amissan -gluten free-', 'Facebook: https://www.facebook.com/profile.php?id=100063573159141, Phone number: 0781 56 64 26');
INSERT INTO `verdelia`.`location` (`location_position`, `location_name`, `location_address_id`) VALUES
(ST_GeomFromText('POINT(3.00456923564612 36.79664864280521)'), 'Rue Lamameri Ali', 1);
INSERT INTO `verdelia`.`product_provider` (`product_provider_location_id`, `product_provider_details_id`,`product_provider_type_id`) VALUES
(1,1,2);

-- Insertions for Magasin habibou sans gluten
INSERT INTO `verdelia`.`provider_details` (`provider_name`, `provider_contact_info`) VALUES
('Magasin habibou sans gluten', 'Facebook: https://www.facebook.com/profile.php?id=100063549909208');
INSERT INTO `verdelia`.`location` (`location_position`, `location_name`, `location_address_id`) VALUES
(ST_GeomFromText('POINT(3.244388200045344 36.79104995021719)'), 'Avenue Houari Boumedien', 2);
INSERT INTO `verdelia`.`product_provider` (`product_provider_location_id`, `product_provider_details_id`,`product_provider_type_id`) VALUES
(2,2,2);

-- Insertions for Uno
INSERT INTO `verdelia`.`provider_details` (`provider_name`, `provider_contact_info`) VALUES
('Uno', 'Facebook: https://www.facebook.com/UNO.Hypermarche/, Instagram: https://www.instagram.com/uno_hypermarche/');
INSERT INTO `verdelia`.`location` (`location_position`, `location_name`, `location_address_id`) VALUES
(ST_GeomFromText('POINT(3.191942199815943 36.71305045006746)'), 'Route de Dar El Beida', 3);
INSERT INTO `verdelia`.`product_provider` (`product_provider_location_id`, `product_provider_details_id`,`product_provider_type_id`) VALUES
(3,3,4);

-- Insertions for Superette université
INSERT INTO `verdelia`.`provider_details` (`provider_name`, `provider_contact_info`) VALUES
('Superette université', 'N/A');
INSERT INTO `verdelia`.`location` (`location_position`, `location_name`, `location_address_id`) VALUES
(ST_GeomFromText('POINT(2.872905857188605 36.68805559407475)'), 'N63', 4);
INSERT INTO `verdelia`.`product_provider` (`product_provider_location_id`, `product_provider_details_id`,`product_provider_type_id`) VALUES
(4,4,4);

-- Insertions for Corridors Shopping
INSERT INTO `verdelia`.`provider_details` (`provider_name`, `provider_contact_info`) VALUES
('Corridors Shopping', 'N/A');
INSERT INTO `verdelia`.`location` (`location_position`, `location_name`, `location_address_id`) VALUES
(ST_GeomFromText('POINT(2.9833228 36.6683827)'), 'Khraicia', 5);
INSERT INTO `verdelia`.`product_provider` (`product_provider_location_id`, `product_provider_details_id`,`product_provider_type_id`) VALUES
(5,5,1);

-- Insertions for Caramel sans gluten
INSERT INTO `verdelia`.`provider_details` (`provider_name`, `provider_contact_info`) VALUES
('Caramel sans gluten', 'N/A');
INSERT INTO `verdelia`.`location` (`location_position`, `location_name`, `location_address_id`) VALUES
(ST_GeomFromText('POINT(2.9514329 36.75573869999999)'), 'Cheraga', 6);
INSERT INTO `verdelia`.`product_provider` (`product_provider_location_id`, `product_provider_details_id`,`product_provider_type_id`) VALUES
(6,6,4);

INSERT INTO `verdelia`.`provider_details` (`provider_name`, `provider_contact_info`) VALUES
('Dar El Karim', 'Facebook: https://www.facebook.com/darelkari, Phone: 0551 23 45 67'),
('S&R Sans Gluten', 'Facebook: https://www.facebook.com/srglutenfree, Phone: 0562 98 76 54'),
('Caramel Sans Gluten', 'Instagram: @caramel_sans_gluten, Phone: 0771 23 45 67'),
('Neima La Maison du Sans Gluten', 'Facebook: https://www.facebook.com/neima, Phone: 0661 78 90 12'),
('Khayer Superette', 'Facebook: https://www.facebook.com/khayer.superette, Phone: 0798 34 56 78'),
('Promochoc', 'Website: https://www.promochoc.com, Phone: 0541 45 67 89'),
('Bonjour Superette', 'Facebook: https://www.facebook.com/bonjour.superette, Phone: 0654 23 45 67'),
('Boulangerie El Qods', 'Instagram: @boulangerie_el_qods, Phone: 0778 90 12 34'),
('Pâtisserie Bouchaib', 'Facebook: https://www.facebook.com/bouchaib.patisserie, Phone: 0792 34 56 78'),
('Boulangerie Ouadah Anis', 'Website: https://www.ouadahanis.com, Phone: 0665 78 90 12');



-- Insert locations
INSERT INTO `verdelia`.`location` (`location_position`, `location_name`) VALUES
(ST_GeomFromText('POINT(3.001 36.75)'), 'Ouled Fayet, Algiers'),
(ST_GeomFromText('POINT(3.021 36.76)'), 'Bouzareah, Algiers'),
(ST_GeomFromText('POINT(3.033 36.75)'), 'Chéraga, Algiers'),
(ST_GeomFromText('POINT(3.059 36.72)'), 'Bab Ezzouar, Algiers'),
(ST_GeomFromText('POINT(3.048 36.75)'), 'El Mouradia, Algiers'),
(ST_GeomFromText('POINT(3.131 36.72)'), 'El Harrach, Algiers'),
(ST_GeomFromText('POINT(3.276 36.72)'), 'Rouiba, Algiers'),
(ST_GeomFromText('POINT(3.05 36.67)'), 'Djasr Kasentina, Algiers'),
(ST_GeomFromText('POINT(3.055 36.76)'), 'Sidi M’Hamed, Algiers'),
(ST_GeomFromText('POINT(3.058 36.74)'), 'Kouba, Algiers');

-- Insert providers into product_provider table (assuming type 2 = Bakery)
INSERT INTO `verdelia`.`product_provider` (`product_provider_location_id`, `product_provider_details_id`, `product_provider_type_id`) VALUES
(1, 1, 2),
(2, 2, 2),
(3, 3, 2),
(4, 4, 2),
(5, 5, 2),
(6, 6, 2),
(7, 7, 2),
(8, 8, 2),
(9, 9, 2),
(10, 10, 2);



-- Insert providers for Sétif
INSERT INTO `verdelia`.`provider_details` (`provider_name`, `provider_contact_info`) VALUES
('Sétif Sans Gluten', 'Facebook: https://www.facebook.com/setifglutenfree, Phone: 0561 34 56 78'),
('Boulangerie Sidi El Khier', 'Instagram: @sidi_el_khier, Phone: 0772 45 67 89'),
('Gourmandise Sans Gluten', 'Website: https://www.gourmandise-setif.com, Phone: 0663 78 90 21'),
('Superette FreeLife', 'Facebook: https://www.facebook.com/freelifesuperette, Phone: 0791 23 45 67'),
('Maison Du Pain Sans Gluten', 'Instagram: @maison_pain_setif, Phone: 0546 78 90 34'),
('Saveurs Saines', 'Facebook: https://www.facebook.com/saveurssaines, Phone: 0779 45 67 89'),
('Boulangerie Nour', 'Website: https://www.boulangerienour.com, Phone: 0652 34 56 78'),
('Délices Sans Gluten', 'Facebook: https://www.facebook.com/delicessansgluten, Phone: 0664 78 90 12'),
('Snack Naturalia', 'Instagram: @snack_naturalia, Phone: 0771 23 45 89'),
('Le Pain Sans Gluten', 'Website: https://www.lepainsansgluten.com, Phone: 0562 45 67 89');

-- Insert locations for Sétif
INSERT INTO `verdelia`.`location` (`location_position`, `location_name`) VALUES
(ST_GeomFromText('POINT(5.403 36.191)'), 'Aïn El Kebira, Sétif'),
(ST_GeomFromText('POINT(5.405 36.196)'), 'El Eulma, Sétif'),
(ST_GeomFromText('POINT(5.408 36.195)'), 'Bougaa, Sétif'),
(ST_GeomFromText('POINT(5.410 36.193)'), 'Guenzet, Sétif'),
(ST_GeomFromText('POINT(5.415 36.190)'), 'Aïn Oulmene, Sétif'),
(ST_GeomFromText('POINT(5.420 36.188)'), 'Bir El Arch, Sétif'),
(ST_GeomFromText('POINT(5.425 36.187)'), 'Beni Aziz, Sétif'),
(ST_GeomFromText('POINT(5.430 36.185)'), 'Draa Kebila, Sétif'),
(ST_GeomFromText('POINT(5.435 36.184)'), 'Hammam Guergour, Sétif'),
(ST_GeomFromText('POINT(5.440 36.182)'), 'Aïn Abessa, Sétif');


-- Insert providers into product_provider table
INSERT INTO `verdelia`.`product_provider` (`product_provider_location_id`, `product_provider_details_id`, `product_provider_type_id`) VALUES
(29, 1, 2),  -- Bakery
(30, 2, 2),
(31, 3, 2),
(32, 4, 4),  -- Supermarket
(33, 5, 2),
(34, 6, 2),
(35, 7, 2),
(36, 8, 2),
(37, 9, 1),  -- Restaurant
(38, 10, 2);




INSERT INTO `verdelia`.`provider_details` (`provider_name`, `provider_contact_info`) VALUES
('Sans Gluten Oran', 'Facebook: https://www.facebook.com/sansglutenoran, Phone: 0771 23 45 67'),
('BioLibre', 'Instagram: https://www.instagram.com/biolibre_oran, Phone: 0662 34 56 78'),
('Le Pain Sans Gluten', 'Website: https://www.lepainsansgluten.com, Phone: 0551 98 76 54'),
('Healthy Market', 'Phone: 0798 65 43 21'),
('Gluten-Free Factory Oran', 'Phone: 0567 89 01 23'),
('Chez Nour', 'Facebook: https://www.facebook.com/cheznouroran, Phone: 0775 43 21 09'),
('EpiDiet', 'Instagram: https://www.instagram.com/epidietoran, Phone: 0543 21 09 87'),
('La Vie Saine', 'Phone: 0654 78 90 12'),
('Free & Fresh', 'Website: https://www.freeandfresh.com, Phone: 0552 67 89 34'),
('Santaré', 'Phone: 0561 90 12 34');

INSERT INTO `verdelia`.`location` (`location_position`, `location_name`) VALUES
(ST_GeomFromText('POINT(-0.6298 35.6989)'), 'Place d’Armes'),
(ST_GeomFromText('POINT(-0.6243 35.6972)'), 'Rue Larbi Ben M’Hidi'),
(ST_GeomFromText('POINT(-0.6305 35.6961)'), 'Boulevard Emir Abdelkader'),
(ST_GeomFromText('POINT(-0.6333 35.6950)'), 'Avenue de la République'),
(ST_GeomFromText('POINT(-0.6357 35.7003)'), 'Quartier Akid Lotfi'),
(ST_GeomFromText('POINT(-0.6412 35.7015)'), 'Maraval'),
(ST_GeomFromText('POINT(-0.6445 35.7032)'), 'Bir El Djir'),
(ST_GeomFromText('POINT(-0.6490 35.7048)'), 'Les Palmiers'),
(ST_GeomFromText('POINT(-0.6522 35.6987)'), 'Cité Djamel'),
(ST_GeomFromText('POINT(-0.6543 35.6964)'), 'Es-Senia');

INSERT INTO `verdelia`.`product_provider` (`product_provider_location_id`, `product_provider_details_id`, `product_provider_type_id`) VALUES
(49,27,2),
(50,28,3),
(51,29,2),
(52,30,4),
(53,31,3),
(54,32,2),
(55,33,3),
(56,34,4),
(57,35,1),
(58,36,2);


-- Insert data into person_details table
INSERT INTO verdelia.person_details 
    (person_first_name, person_last_name, person_birth_date, person_gender, person_nationality) 
VALUES 
    ('Some', 'One', '2003-01-01', 'Male', 'Algerian');

-- Get the ID of the newly inserted person_details

-- Insert data into person table
INSERT INTO verdelia.person 
    (person_details_id, person_blood_type_id, person_location_id) 
VALUES 
    (1, 1, 1); 

-- Insert data into app_user table
INSERT INTO verdelia.app_user 
    (app_user_name, app_user_password, app_user_person_id, app_user_type_id) 
VALUES 
    ('SomeOne', 'password', 1, 1); 


-- Baked Goods
INSERT INTO `verdelia`.`product` (`product_owner`,`product_name`, `product_brand`,`product_description`, `product_provider_id`, `product_category_id`, `product_barcode`, `product_price`, `product_quantity`,`last_updated`,`created`) VALUES
(1,'Grano\'Sac Raisin Cacahuetes', 'Grano\'Sac','Delicious gluten-free baked goods made with raisins and peanuts. Perfect for a nutritious snack.', 1, 1, '1234567890123', 5.99, 100, CURDATE(), CURDATE()),
(1,'Butter Biscuits LEGER', 'LEGER','Light and crispy gluten-free butter biscuits, a guilt-free treat for any time of the day.', 1, 1, '1234567890124', 4.49, 150, CURDATE(), CURDATE()),
(1,'Cookies', 'Home Bakery','Indulgent gluten-free cookies baked to perfection, a delightful blend of flavors in every bite.', 1, 1, '1234567890125', 3.99, 200, CURDATE(), CURDATE()),
(1,'Gullon Cookies', 'Gullon','Classic gluten-free cookies from Gullon, a favorite snack for both kids and adults.', 1, 1, '1234567890126', 6.29, 120, CURDATE(), CURDATE());

-- Spreads
INSERT INTO `verdelia`.`product` (`product_owner`,`product_name`, `product_brand`,`product_description`, `product_provider_id`, `product_category_id`, `product_barcode`, `product_price`, `product_quantity`,`last_updated`,`created`) VALUES
(1,'Date Butter', 'NutriLife','A rich and creamy date butter, packed with nutrients and perfect for spreading on toast or crackers.', 1, 2, '1234567890127', 7.99, 80, CURDATE(), CURDATE()),
(1,'CARAIBE Crème à Tartiner', 'CARAIBE','Decadent chocolate spread from CARAIBE, a luxurious treat for chocolate lovers.', 1, 2, '1234567890128', 8.49, 100, CURDATE(), CURDATE()),
(1,'JUMPY Beurre De Cacahuète', 'JUMPY','Smooth and creamy peanut butter spread, a versatile ingredient for sandwiches, smoothies, and desserts.', 1, 2, '1234567890129', 5.79, 90, CURDATE(), CURDATE());

-- Cereals
INSERT INTO `verdelia`.`product` (`product_owner`,`product_name`, `product_brand`,`product_description`, `product_provider_id`, `product_category_id`, `product_barcode`, `product_price`, `product_quantity`,`last_updated`,`created`) VALUES
(1,'Semoule de pain', 'BioCereal','Organic gluten-free semolina, perfect for making bread, couscous, and various desserts.', 1, 3, '1234567890130', 3.99, 120, CURDATE(), CURDATE()),
(1,'Flocons D\'avoine (fariné)', 'NatureLand','Finely ground gluten-free oat flakes, ideal for baking bread, cookies, and other baked goods.', 1, 3, '1234567890131', 6.49, 80, CURDATE(), CURDATE()),
(1,'Flocons D\'avoine (petits)', 'Healthy Harvest','Whole gluten-free oat flakes, a nutritious addition to your breakfast bowl or baked treats.', 1, 3, '1234567890132', 4.99, 100, CURDATE(), CURDATE());

-- Pasta
INSERT INTO `verdelia`.`product` (`product_owner`,`product_name`, `product_brand`,`product_description`, `product_provider_id`, `product_category_id`, `product_barcode`, `product_price`, `product_quantity`,`last_updated`,`created`) VALUES
(1,'Farine à Pizza', 'Mama\'s Kitchen','Premium gluten-free pizza flour blend, perfect for making homemade pizzas with a crispy crust.', 1, 4, '1234567890133', 5.99, 150, CURDATE(), CURDATE()),
(1,'COUDE Pâtes sans gluten', 'Italian Delight','Gluten-free elbow pasta, ideal for pasta salads, casseroles, and creamy pasta dishes.', 1, 4, '1234567890134', 4.49, 100, CURDATE(), CURDATE());

-- Snacks
INSERT INTO `verdelia`.`product` (`product_owner`,`product_name`, `product_brand`,`product_description`, `product_provider_id`, `product_category_id`, `product_barcode`, `product_price`, `product_quantity`,`last_updated`,`created`) VALUES
(1,'Grano\'Sac Raisin Cacahuetes', 'Grano\'Sac','Delicious gluten-free baked goods made with raisins and peanuts. Perfect for a nutritious snack.', 1, 5, '1234567890123', 5.99, 100, CURDATE(), CURDATE()),
(1,'Cookies', 'Home Bakery','Indulgent gluten-free cookies baked to perfection, a delightful blend of flavors in every bite.', 1, 5, '1234567890125', 3.99, 200, CURDATE(), CURDATE()),
(1,'Gullon Cookies', 'Gullon','Classic gluten-free cookies from Gullon, a favorite snack for both kids and adults.', 1, 5, '1234567890126', 6.29, 120, CURDATE(), CURDATE());

-- Desserts
INSERT INTO `verdelia`.`product` (`product_owner`,`product_name`, `product_brand`,`product_description`, `product_provider_id`, `product_category_id`, `product_barcode`, `product_price`, `product_quantity`,`last_updated`,`created`) VALUES
(1,'Confiture Delicia fruit', 'Delicia','Exquisite gluten-free fruit jam, bursting with natural flavors and sweetness.', 1, 7, '1234567890135', 7.99, 80, CURDATE(), CURDATE()),
(1,'Confiture Ela fraise', 'Ela','Delightful strawberry jam, perfect for spreading on toast, biscuits, or pairing with cheese.', 1, 7, '1234567890136', 6.49, 90, CURDATE(), CURDATE()),
(1,'Flan Vanille Nouara', 'Nouara','Creamy vanilla flan dessert, a classic indulgence that melts in your mouth with every spoonful.', 1, 7, '1234567890137', 8.99, 70, CURDATE(), CURDATE());
INSERT INTO `verdelia`.`product` 
(`product_owner`, `product_name`, `product_brand`, `product_description`, `product_provider_id`, `product_category_id`, `product_barcode`, `product_price`, `product_quantity`, `last_updated`, `created`) 
VALUES
-- Juices
(1, 'Jus d\'Orange Naturel', 'Vitafruit', '100% natural orange juice, no added sugar.', 2, 6, '1234567890145', 250, 50, CURDATE(), CURDATE()),
(1, 'Jus de Pomme', 'NatureLand', 'Fresh apple juice, organic and preservative-free.', 3, 6, '1234567890146', 230, 40, CURDATE(), CURDATE()),
(1, 'Nectar Mangue', 'ExoticDelight', 'Smooth mango nectar, rich in vitamins.', 4, 6, '1234567890147', 280, 60, CURDATE(), CURDATE()),
(1, 'Jus Multifruits', 'VitaBoost', 'A blend of tropical fruits for an energy boost.', 5, 6, '1234567890148', 270, 45, CURDATE(), CURDATE()),

-- Milk and Dairy Alternatives
(1, 'Lait d\'Amande', 'Alpro', 'Delicious almond milk, lactose-free and vitamin-enriched.', 6, 6, '1234567890149', 550, 30, CURDATE(), CURDATE()),
(1, 'Lait de Soja', 'SoyJoy', 'Plant-based soy milk, perfect for lactose-intolerant individuals.', 7, 6, '1234567890150', 500, 35, CURDATE(), CURDATE()),
(1, 'Lait de Noisette', 'NutriMilk', 'Hazelnut milk with a creamy texture and a rich taste.', 8, 6, '1234567890151', 600, 25, CURDATE(), CURDATE()),
(1, 'Lait de Coco', 'TropiCoco', 'Refreshing coconut milk, ideal for cooking and drinking.', 9, 6, '1234567890152', 450, 40, CURDATE(), CURDATE()),

-- Tea and Infusions
(1, 'Thé Vert Bio', 'NatureHerbs', 'Organic green tea leaves, rich in antioxidants.', 10, 6, '1234567890153', 350, 50, CURDATE(), CURDATE()),
(1, 'Infusion Camomille', 'RelaxTea', 'Calming chamomile herbal infusion.', 11, 6, '1234567890154', 300, 60, CURDATE(), CURDATE()),
(1, 'Thé Noir Earl Grey', 'RoyalTea', 'Premium black tea with a hint of bergamot.', 12, 6, '1234567890155', 400, 40, CURDATE(), CURDATE()),

-- Coffee and Hot Drinks
(1, 'Café Moulu Arabica', 'CaféD\'Or', 'Finely ground Arabica coffee, strong and flavorful.', 13, 6, '1234567890156', 800, 30, CURDATE(), CURDATE()),
(1, 'Capsules Expresso', 'CaféExpress', 'Compatible espresso capsules with intense aroma.', 14, 6, '1234567890157', 1200, 20, CURDATE(), CURDATE()),
(1, 'Chocolat en Poudre', 'ChocoMelt', 'Rich cocoa powder, ideal for hot chocolate.', 15, 6, '1234567890158', 700, 50, CURDATE(), CURDATE()),
(1, 'Lait Chocolaté', 'ChocoLait', 'Sweetened chocolate-flavored milk drink.', 16, 6, '1234567890159', 500, 45, CURDATE(), CURDATE()),

-- Soft Drinks
(1, 'Eau Minérale Plate', 'AquaPure', 'Pure natural mineral water, essential for hydration.', 17, 6, '1234567890160', 80, 100, CURDATE(), CURDATE()),
(1, 'Eau Gazeuse', 'SparkleWater', 'Carbonated mineral water with a refreshing taste.', 18, 6, '1234567890161', 120, 90, CURDATE(), CURDATE()),
(1, 'Soda Citron', 'FizzUp', 'Refreshing lemon-flavored soft drink.', 19, 6, '1234567890162', 200, 70, CURDATE(), CURDATE()),
(1, 'Boisson Énergisante', 'PowerRush', 'Energy drink with a mix of caffeine and vitamins.', 20, 6, '1234567890163', 400, 60, CURDATE(), CURDATE());



INSERT INTO `verdelia`.`recipe` 
(`recipe_owner_id`, `recipe_category_id`, `recipe_preparation_time`, `recipe_instructions`, `recipe_name`, `recipe_description`, `recipe_creation`, `recipe_last_updated`)
VALUES
(1, 1, '0h30', 'Step 1: Do this.\nStep 2: Do that.', 'Tasty Appetizer', 'A delicious appetizer to start your meal.', NOW(), NOW()),
(1, 2, '0h45', 'Step 1: Prepare ingredients.\nStep 2: Cook.', 'Hearty Soup', 'A warm and comforting soup.', NOW(), NOW()),
(1, 3, '0h20', 'Step 1: Chop vegetables.\nStep 2: Mix ingredients.', 'Fresh Salad', 'A fresh and healthy salad.', NOW(), NOW()),
(1, 4, '1h0', 'Step 1: Marinate meat.\nStep 2: Grill.', 'Grilled Chicken', 'Juicy grilled chicken with herbs.', NOW(), NOW()),
(1, 5, '0h30', 'Step 1: Boil water.\nStep 2: Cook side dish.', 'Mashed Potatoes', 'Creamy mashed potatoes.', NOW(), NOW()),
(1, 6, '0h40', 'Step 1: Prepare pasta.\nStep 2: Cook sauce.', 'Spaghetti Bolognese', 'Classic Italian pasta dish.', NOW(), NOW()),
(1, 7, '1h30', 'Step 1: Prepare casserole.\nStep 2: Bake.', 'Cheesy Casserole', 'Cheesy and delicious casserole.', NOW(), NOW()),
(1, 8, '0h25', 'Step 1: Mix ingredients.\nStep 2: Cook.', 'Pancakes', 'Fluffy and light pancakes.', NOW(), NOW()),
(1, 9, '3h0', 'Step 1: Prepare dough.\nStep 2: Bake.', 'Sourdough Bread', 'Homemade sourdough bread.', NOW(), NOW()),
(1, 10, '1h15', 'Step 1: Prepare ingredients.\nStep 2: Bake.', 'Chocolate Cake', 'Rich and moist chocolate cake.', NOW(), NOW());

INSERT INTO  `verdelia`.`disease_severity` (`disease_severity_desc`) VALUES
('Marsh 0'),
('Marsh 1'),
('Marsh 2'),
('Marsh 3'),
('Marsh 3a'),
('Marsh 3b'),
('Marsh 3c'),
('Marsh 4');

insert into `verdelia`.`patient` (`patient_person_id` ,`patient_disease_severity_id`) values 
(1,1);


INSERT INTO `verdelia`.`symptom` (symptom_name, symptom_desc) VALUES
('Abdominal Pain', 'Pain in the stomach area'),
('Bloating', 'Swelling of the abdomen'),
('Diarrhea', 'Frequent loose stools'),
('Constipation', 'Difficulty in bowel movements'),
('Fatigue', 'Extreme tiredness'),
('Weight Loss', 'Unintentional loss of weight'),
('Anemia', 'Low red blood cell count'),
('Osteoporosis', 'Weakening of the bones'),
('Dermatitis Herpetiformis', 'Skin rash with blisters'),
('Nausea', 'Feeling of sickness with an inclination to vomit'),
('Vomiting', 'Ejecting stomach contents through the mouth'),
('Flatulence', 'Excessive gas in the digestive tract'),
('Headache', 'Pain in the head'),
('Joint Pain', 'Pain in the joints'),
('Muscle Cramps', 'Involuntary muscle contractions'),
('Depression', 'Persistent feeling of sadness'),
('Anxiety', 'Feeling of worry or fear'),
('Mouth Ulcers', 'Sores in the mouth'),
('Tingling Sensation', 'Pins and needles feeling in limbs'),
('Neuropathy', 'Damage to the nerves causing weakness or pain'),
('Infertility', 'Inability to conceive children'),
('Bone Pain', 'Pain in the bones'),
('Acid Reflux', 'Burning sensation in the chest'),
('Indigestion', 'Discomfort in the stomach after eating'),
('Irritability', 'Easily annoyed or angered'),
('Short Stature', 'Below-average height for age'),
('Delayed Puberty', 'Late onset of puberty changes'),
('Dizziness', 'Feeling of unsteadiness or loss of balance'),
('Malabsorption', 'Inability to absorb nutrients properly'),
('Iron Deficiency', 'Lack of sufficient iron in the body'),
('Calcium Deficiency', 'Lack of sufficient calcium in the body'),
('3 Deficiency', 'Lack of sufficient vitamin D in the body'),
('Alopecia Areata', 'Patchy hair loss'),
('Night Blindness', 'Difficulty seeing in low light conditions'),
('Glossitis', 'Inflammation of the tongue'),
('Cheilitis', 'Inflammation of the lips'),
('Peripheral Edema', 'Swelling of the lower limbs'),
('Ataxia', 'Lack of muscle coordination'),
('Seizures', 'Uncontrolled electrical activity in the brain'),
('Brain Fog', 'Cognitive dysfunction or confusion'),
('Mood Swings', 'Frequent changes in mood'),
('Panic Attacks', 'Sudden periods of intense fear'),
('Hyperthyroidism', 'Overactive thyroid gland'),
('Hypothyroidism', 'Underactive thyroid gland'),
('Heart Palpitations', 'Irregular or rapid heartbeat'),
('Sleep Disorders', 'Problems with sleeping'),
('Chronic Fatigue Syndrome', 'Persistent and severe fatigue'),
('Fibromyalgia', 'Widespread muscle pain and tenderness'),
('Dry Mouth', 'Lack of saliva production'),
('Dry Eyes', 'Lack of tear production'),
('Sinusitis', 'Inflammation of the sinuses'),
('Asthma', 'Respiratory condition with difficulty breathing'),
('Arthritis', 'Inflammation of the joints'),
('Eczema', 'Inflammatory skin condition with itchy rash'),
('Psoriasis', 'Skin condition with red, scaly patches'),
('Lactose Intolerance', 'Inability to digest lactose'),
('Intestinal Obstruction', 'Blockage of the intestines'),
('Gallstones', 'Stones formed in the gallbladder'),
('Pancreatitis', 'Inflammation of the pancreas'),
('Irritable Bowel Syndrome', 'Digestive disorder causing pain and discomfort'),
('Crohn’s Disease', 'Chronic inflammatory bowel disease'),
('Ulcerative Colitis', 'Chronic inflammation of the colon'),
('Lymphoma', 'Cancer of the lymphatic system'),
('Esophageal Cancer', 'Cancer of the esophagus'),
('Liver Disease', 'Impaired liver function'),
('Kidney Disease', 'Impaired kidney function'),
('Gallbladder Disease', 'Impaired gallbladder function'),
('Cholecystitis', 'Inflammation of the gallbladder'),
('Hypoglycemia', 'Low blood sugar levels'),
('Hyperglycemia', 'High blood sugar levels'),
('Celiac Crisis', 'Severe malnutrition and electrolyte imbalance due to celiac disease'),
('Small Intestinal Bacterial Overgrowth', 'Excessive bacteria in the small intestine'),
('Leaky Gut Syndrome', 'Increased intestinal permeability'),
('Candida Overgrowth', 'Excessive growth of Candida yeast in the body'),
('Fructose Malabsorption', 'Inability to digest fructose properly'),
('Histamine Intolerance', 'Sensitivity to histamine in foods'),
('Food Allergies', 'Immune response to certain foods'),
('Autoimmune Hepatitis', 'Immune system attacks liver cells'),
('Primary Biliary Cirrhosis', 'Chronic disease of the bile ducts'),
('Primary Sclerosing Cholangitis', 'Chronic disease affecting bile ducts and liver'),
('Peripheral Neuropathy', 'Damage to the peripheral nerves'),
('Central Neuropathy', 'Damage to the central nerves'),
('Chronic Kidney Disease', 'Long-term kidney damage and dysfunction'),
('Reproductive Disorders', 'Issues with reproductive system function'),
('Malignant Tumors', 'Cancerous growths'),
('Benign Tumors', 'Non-cancerous growths'),
('Nutrient Deficiencies', 'Lack of essential nutrients in the body'),
('Autoimmune Thyroiditis', 'Immune system attacks the thyroid gland'),
('Sjögren’s Syndrome', 'Autoimmune disease affecting glands that produce moisture'),
('Raynaud’s Phenomenon', 'Decreased blood flow to fingers and toes'),
('Systemic Lupus Erythematosus', 'Autoimmune disease affecting multiple organs'),
('Multiple Sclerosis', 'Disease affecting brain and spinal cord'),
('Dermatomyositis', 'Inflammatory disease affecting muscles and skin'),
('Scleroderma', 'Chronic connective tissue disease'),
('Ankylosing Spondylitis', 'Inflammatory arthritis affecting the spine'),
('Rheumatoid Arthritis', 'Autoimmune disease affecting joints'),
('Polymyalgia Rheumatica', 'Inflammatory disorder causing muscle pain and stiffness'),
('Temporal Arteritis', 'Inflammation of the temporal arteries'),
('Interstitial Lung Disease', 'Group of lung disorders causing scarring'),
('Pulmonary Fibrosis', 'Scarring of the lung tissue'),
('Sarcoidosis', 'Inflammatory disease affecting multiple organs'),
('Eosinophilic Esophagitis', 'Allergic condition affecting the esophagus'),
('Gastroesophageal Reflux Disease', 'Chronic acid reflux disease'),
('Peptic Ulcers', 'Sores in the lining of the stomach or duodenum'),
('Celiac Disease', 'Autoimmune disorder affecting the small intestine');


INSERT INTO `verdelia`.`serology_indicator` (serology_indicator_name, serology_indicator_desc) VALUES
('Antibody Level', 'Measurement of specific antibodies present in the blood. Often used to assess immune response or autoimmune conditions.'),
('Hemoglobin', 'The amount of hemoglobin in the blood, measured in grams per deciliter (g/dL). 2 is a protein in red blood cells that carries oxygen.'),
('Vitamin D', 'Measurement of the level of 3 in the blood, important for bone health and immune function.'),
('CRP', 'C-reactive protein (CRP) levels indicate inflammation in the body. High levels can suggest infection or chronic inflammatory conditions.'),
('ESR', 'Erythrocyte sedimentation rate (ESR) is a blood test that can reveal inflammatory activity in the body.'),
('Liver Enzymes', 'Measurement of enzymes like ALT and AST in the blood to assess liver function.'),
('Thyroid Function', 'Assessment of thyroid hormones (T3, T4, TSH) to evaluate thyroid gland activity.'),
('Iron', 'Measurement of iron levels in the blood, important for diagnosing anemia and other conditions.'),
('Calcium', 'Measurement of calcium levels in the blood, important for bone health, muscle function, and nerve signaling.'),
('Glucose', 'Blood sugar levels, important for diagnosing and monitoring diabetes.'),
('Cholesterol', 'Measurement of cholesterol levels, including HDL and LDL, important for assessing cardiovascular risk.'),
('Triglycerides', 'Measurement of triglyceride levels in the blood, important for assessing cardiovascular risk.'),
('Ferritin', 'Measurement of ferritin levels, which indicate the amount of stored iron in the body.'),
('B12', 'Measurement of Vitamin B12 levels, important for nerve function and the production of red blood cells.'),
('Folate', 'Measurement of folate levels, important for DNA synthesis and repair, and red blood cell production.'),
('IgA', 'Measurement of Immunoglobulin A (IgA) levels, important for immune function, particularly in mucous membranes.'),
('IgG', 'Measurement of Immunoglobulin G (IgG) levels, the most common antibody in blood and other body fluids, crucial for fighting bacterial and viral infections.'),
('IgM', 'Measurement of Immunoglobulin M (IgM) levels, the first antibody produced in response to an infection.'),
('Platelets', 'Measurement of platelet count in the blood, important for blood clotting.'),
('WBC', 'White blood cell count, important for assessing immune function and detecting infections.'),
('RBC', 'Red blood cell count, important for diagnosing anemia and other blood disorders.'),
('Albumin', 'Measurement of albumin levels, a protein made by the liver, important for maintaining oncotic pressure and transporting hormones, vitamins, and drugs.'),
('Globulin', 'Measurement of globulin levels, important for immune function and protein transport in the blood.'),
('Alkaline Phosphatase', 'Measurement of alkaline phosphatase levels, an enzyme related to the bile ducts; high levels can indicate liver or bone disorders.'),
('Bilirubin', 'Measurement of bilirubin levels, important for assessing liver function and diagnosing jaundice.'),
('Electrolytes', 'Measurement of electrolyte levels, including sodium, potassium, chloride, and bicarbonate, important for maintaining fluid balance and nerve/muscle function.');


-- Dummy data insertions
INSERT INTO `verdelia`.`serology` (patient_id, indicator_id, indicator_value, serology_date) VALUES
(1, '1', 'High', '2024-01-10'),
(1, '2', '13.5 g/dL', '2024-01-10'),
(1, '3', '20 ng/mL', '2024-01-10'),
(1, '1', 'Moderate', '2024-03-15'),
(1, '2', '14.0 g/dL', '2024-03-15'),
(1, '3', '22 ng/mL', '2024-03-15'),
(1, '1', 'Low', '2024-02-20'),
(1, '2', '12.0 g/dL', '2024-02-20'),
(1, '3', '18 ng/mL', '2024-02-20'),
(1, '1', 'Low', '2024-05-18'),
(1, '2', '11.5 g/dL', '2024-05-18'),
(1, '3', '16 ng/mL', '2024-05-18'),
(1, '1', 'High', '2024-04-25'),
(1, '2', '14.2 g/dL', '2024-04-25'),
(1, '3', '25 ng/mL', '2024-04-25'),
(1, '1', 'High', '2024-06-05'),
(1, '2', '13.8 g/dL', '2024-06-05'),
(1, '3', '24 ng/mL', '2024-06-05'),
(1, '1', 'Moderate', '2024-01-30'),
(1, '2', '13.0 g/dL', '2024-01-30'),
(1, '3', '19 ng/mL', '2024-01-30'),
(1, '1', 'Moderate', '2024-03-10'),
(1, '2', '13.3 g/dL', '2024-03-10'),
(1, '3', '21 ng/mL', '2024-03-10'),
(1, '1', 'Low', '2024-02-12'),
(1, '2', '12.2 g/dL', '2024-02-12'),
(1, '3', '17 ng/mL', '2024-02-12'),
(1, '1', 'Low', '2024-04-20'),
(1, '2', '11.8 g/dL', '2024-04-20'),
(1, '3', '15 ng/mL', '2024-04-20');



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


INSERT INTO `verdelia`.`product_image` (`product_image_url`, `product_ref_id`) VALUES
('/fs/product/1/1/a8d09b7c-4373-4279-8b84-156627bcfcfe', 1),
('/fs/product/1/2/4dcfa594-20da-4173-bf38-d55b5babf5fc', 2),
('/fs/product/1/3/e79b4666-111e-4fb2-8167-a59e10b5a2b2', 3),
('/fs/product/1/4/07e09aaa-5ce4-40e5-aaa3-e9df57ca4336', 4),
('/fs/product/1/5/09bcc68a-7561-47c8-b958-5be505993651', 5),
('/fs/product/1/6/98283a17-8faf-4288-94f4-b16881cf1a66', 6),
('/fs/product/1/7/141c909d-7358-4e67-bb22-c56b609ffc5e', 7),
('/fs/product/1/8/8f598bbb-6330-4a44-8f46-e62f2bc63fbc', 8),
('/fs/product/1/9/cffcd4ab-9fda-44e1-a554-75bc69d12c03', 9),
('/fs/product/1/10/07be024b-ebc0-4d70-9173-cb46c2ef6f2b', 10),
('/fs/product/1/11/d0ba0453-4daa-4710-9b6f-717e9b3a21eb', 11),
('/fs/product/1/12/fde200b6-6c51-49b5-8f03-4840518abab9', 12),
('/fs/product/1/13/fc222373-b07d-4ad9-97b4-f5e04de5af19', 13),
('/fs/product/1/14/3f8ea60b-fcb7-4936-b6ec-9d4c2228a8a4', 14),
('/fs/product/1/15/9ff2fc1c-a1b2-492d-b9be-62f238335d90', 15),
('/fs/product/1/16/e6b88aa0-e043-48f6-bab0-877a776d2ada', 16),
('/fs/product/1/17/7f5bed1f-85d9-48c2-8d51-dd085375b748', 17),
('/fs/product/1/18/5f9bf70a-f8ff-49fd-9457-57dc463b236a', 18),
('/fs/product/1/19/4100f11e-9cd8-4e73-b398-7a92213421a6', 19);

INSERT INTO `verdelia`.`recipe_image` (`recipe_image_url`, `recipe_ref_id`) VALUES
('/fs/recipe/1/1/c3a0479a-7158-453a-aca6-de2686273b9a', 1),
('/fs/recipe/1/2/c3c495df-499c-4080-bd94-fbfbac4b7373', 2),
('/fs/recipe/1/3/74a8713d-e4cd-410c-b283-ecd255043eb6', 3),
('/fs/recipe/1/4/bd454c87-b5f4-4c4c-bb27-0aec9034c6c1', 4),
('/fs/recipe/1/5/ba7c8858-68ba-4213-9743-5fb73d27bb28', 5),
('/fs/recipe/1/6/cb8f25b1-cb03-4c80-abf6-401a4fda2e1c', 6),
('/fs/recipe/1/7/debc1bf2-36c1-4fa3-828d-02a509897de9', 7),
('/fs/recipe/1/8/0a73e7f6-b355-42cb-b606-c9b0915ea010', 8),
('/fs/recipe/1/9/8ab55ac5-5974-44bb-bd8e-23db70b7e58b', 9),
('/fs/recipe/1/10/da75a418-4490-4ec1-b992-197b94929f38', 10);



SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;


