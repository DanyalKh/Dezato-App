/*
 Navicat Premium Data Transfer

 Source Server         : MariaDB
 Source Server Type    : MariaDB
 Source Server Version : 100212
 Source Host           : localhost:3306
 Source Schema         : fas1

 Target Server Type    : MariaDB
 Target Server Version : 100212
 File Encoding         : 65001

 Date: 16/07/2018 12:54:38
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for tabAddress Template
-- ----------------------------
DROP TABLE IF EXISTS `tabAddress Template`;
CREATE TABLE `tabAddress Template` (
  `name` varchar(140) COLLATE utf8mb4_unicode_ci NOT NULL,
  `creation` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `modified_by` varchar(140) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `owner` varchar(140) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `docstatus` int(1) NOT NULL DEFAULT 0,
  `parent` varchar(140) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `parentfield` varchar(140) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `parenttype` varchar(140) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `idx` int(8) NOT NULL DEFAULT 0,
  `_liked_by` text COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `country` varchar(140) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `_assign` text COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_default` int(1) NOT NULL DEFAULT 0,
  `_comments` text COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `template` longtext COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `_user_tags` text COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`name`),
  KEY `country` (`country`),
  KEY `parent` (`parent`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=COMPRESSED;

-- ----------------------------
-- Records of tabAddress Template
-- ----------------------------
BEGIN;
INSERT INTO `tabAddress Template` VALUES ('United Arab Emirates', '2018-01-08 12:17:11.624786', '2018-07-16 09:36:13.797830', 'Administrator', 'Administrator', 0, NULL, NULL, NULL, 0, NULL, 'United Arab Emirates', NULL, 1, NULL, '{{ address_line1 }}{% if address_line2 %}{{ address_line2 }}{% endif -%}{{ city }}<br>\n{% if state %}{{ state }}{% endif -%}\n{% if pincode %}{{ pincode }}<br>{% endif -%}\n{{ country }}<br>\n{% if phone %}Phone: {{ phone }}<br>{% endif -%}\n{% if fax %}Fax: {{ fax }}<br>{% endif -%}\n{% if email_id %}Email: {{ email_id }}<br>{% endif -%}', NULL);
COMMIT;

SET FOREIGN_KEY_CHECKS = 1;
