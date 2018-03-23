-- phpMyAdmin SQL Dump
-- version 4.6.6deb5
-- https://www.phpmyadmin.net/
--
-- Host: localhost:3306
-- Generation Time: Mar 18, 2018 at 03:57 PM
-- Server version: 5.7.21-0ubuntu0.17.10.1
-- PHP Version: 7.1.11-0ubuntu0.17.10.1

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `MasterMoviesMPP`
--

-- --------------------------------------------------------

--
-- Table structure for table `exportJob`
--

CREATE TABLE `exportJob` (
  `exportJobID` int(11) NOT NULL,
  `fk_jobUUID` binary(16) NOT NULL,
  `fk_nodeUUID` binary(16) DEFAULT NULL,
  `status` tinyint(4) NOT NULL DEFAULT '0',
  `failures` tinyint(4) NOT NULL DEFAULT '0'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `ingestJob`
--

CREATE TABLE `ingestJob` (
  `ingestJobID` int(11) NOT NULL,
  `fk_jobUUID` binary(16) NOT NULL,
  `fk_nodeUUID` binary(16) DEFAULT NULL,
  `status` int(11) NOT NULL DEFAULT '0',
  `failures` tinyint(4) NOT NULL DEFAULT '0'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `interface`
--

CREATE TABLE `interface` (
  `userID` int(11) NOT NULL,
  `username` varchar(64) NOT NULL,
  `password` varchar(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `interface`
--

INSERT INTO `interface` (`userID`, `username`, `password`) VALUES
(1, 'admin', '$2y$10$bPzwKJNKu0qBrI.5vu4K6eFuuWroyoLUWFIdutkcfNVN1QJGrjy5q');

-- --------------------------------------------------------

--
-- Table structure for table `job`
--

CREATE TABLE `job` (
  `jobID` int(11) NOT NULL,
  `jobUUID` binary(16) DEFAULT NULL,
  `sourceName` varchar(32) COLLATE utf8_unicode_ci NOT NULL,
  `dateAdded` timestamp NULL DEFAULT NULL,
  `dateCompleted` timestamp NULL DEFAULT NULL,
  `status` tinyint(4) NOT NULL DEFAULT '0',
  `completed` bit(1) NOT NULL DEFAULT b'0',
  `failed` bit(1) NOT NULL DEFAULT b'0',
  `mediaInfo` text COLLATE utf8_unicode_ci
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `node`
--

CREATE TABLE `node` (
  `nodeID` int(11) NOT NULL,
  `nodeUUID` binary(16) NOT NULL,
  `lastAccess` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `type` tinyint(4) NOT NULL,
  `fk_jobUUID` binary(16) DEFAULT NULL,
  `isActive` bit(1) NOT NULL DEFAULT b'0',
  `terminate` bit(1) NOT NULL DEFAULT b'0',
  `authorise` bit(1) NOT NULL DEFAULT b'1'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `output`
--

CREATE TABLE `output` (
  `outputID` int(11) NOT NULL,
  `active` bit(1) NOT NULL DEFAULT b'1',
  `maxY` smallint(6) NOT NULL,
  `maxX` smallint(6) NOT NULL,
  `CRF` tinyint(4) NOT NULL DEFAULT '23',
  `preset` varchar(9) COLLATE utf8_unicode_ci NOT NULL DEFAULT 'medium',
  `profile` varchar(9) COLLATE utf8_unicode_ci NOT NULL DEFAULT 'main',
  `maxFramerate` tinyint(4) NOT NULL DEFAULT '60',
  `audioBitrate` smallint(6) NOT NULL DEFAULT '128'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

--
-- Dumping data for table `output`
--

INSERT INTO `output` (`outputID`, `active`, `maxY`, `maxX`, `CRF`, `preset`, `profile`, `maxFramerate`, `audioBitrate`) VALUES
(1, b'1', 1080, 1920, 23, 'superfast', 'main', 60, 128),
(2, b'1', 720, 1280, 23, 'superfast', 'main', 60, 128);

-- --------------------------------------------------------

--
-- Table structure for table `policy`
--

CREATE TABLE `policy` (
  `policyID` int(11) NOT NULL,
  `policy` varchar(32) COLLATE utf8_unicode_ci NOT NULL,
  `value` varchar(64) COLLATE utf8_unicode_ci NOT NULL,
  `value_type` varchar(16) COLLATE utf8_unicode_ci NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

--
-- Dumping data for table `policy`
--

INSERT INTO `policy` (`policyID`, `policy`, `value`, `value_type`) VALUES
(1, 'ingestEnabled', '1', 'boolean'),
(2, 'transcodeEnabled', '1', 'boolean'),
(3, 'exportEnabled', '1', 'boolean'),
(4, 'terminateAll', '0', 'boolean'),
(5, 'nodeTimeout', '900', 'integer'),
(6, 'verifyDuringIngest', '1', 'boolean'),
(7, 'failureTolerance', '3', 'integer');

-- --------------------------------------------------------

--
-- Table structure for table `transcodeJob`
--

CREATE TABLE `transcodeJob` (
  `transcodeJobID` int(11) NOT NULL,
  `segmentPart` smallint(6) NOT NULL,
  `fk_jobUUID` binary(16) NOT NULL,
  `fk_nodeUUID` binary(16) DEFAULT NULL,
  `status` tinyint(4) NOT NULL DEFAULT '0',
  `failures` tinyint(4) NOT NULL DEFAULT '0'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `exportJob`
--
ALTER TABLE `exportJob`
  ADD PRIMARY KEY (`exportJobID`),
  ADD UNIQUE KEY `fk_jobUUID` (`fk_jobUUID`),
  ADD UNIQUE KEY `fk_nodeUUID` (`fk_nodeUUID`);

--
-- Indexes for table `ingestJob`
--
ALTER TABLE `ingestJob`
  ADD PRIMARY KEY (`ingestJobID`),
  ADD UNIQUE KEY `fk_jobUUID` (`fk_jobUUID`),
  ADD UNIQUE KEY `fk_nodeUUID` (`fk_nodeUUID`);

--
-- Indexes for table `interface`
--
ALTER TABLE `interface`
  ADD PRIMARY KEY (`userID`),
  ADD UNIQUE KEY `username` (`username`);

--
-- Indexes for table `job`
--
ALTER TABLE `job`
  ADD PRIMARY KEY (`jobID`),
  ADD UNIQUE KEY `jobUUID` (`jobUUID`) USING BTREE;

--
-- Indexes for table `node`
--
ALTER TABLE `node`
  ADD PRIMARY KEY (`nodeID`),
  ADD UNIQUE KEY `nodeUUID` (`nodeUUID`);

--
-- Indexes for table `output`
--
ALTER TABLE `output`
  ADD PRIMARY KEY (`outputID`);

--
-- Indexes for table `policy`
--
ALTER TABLE `policy`
  ADD PRIMARY KEY (`policyID`),
  ADD UNIQUE KEY `policy` (`policy`);

--
-- Indexes for table `transcodeJob`
--
ALTER TABLE `transcodeJob`
  ADD PRIMARY KEY (`transcodeJobID`),
  ADD UNIQUE KEY `segmentPart+JobUUID` (`segmentPart`,`fk_jobUUID`) USING BTREE,
  ADD UNIQUE KEY `fk_nodeUUID` (`fk_nodeUUID`),
  ADD KEY `fk_jobUUID` (`fk_jobUUID`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `exportJob`
--
ALTER TABLE `exportJob`
  MODIFY `exportJobID` int(11) NOT NULL AUTO_INCREMENT;
--
-- AUTO_INCREMENT for table `ingestJob`
--
ALTER TABLE `ingestJob`
  MODIFY `ingestJobID` int(11) NOT NULL AUTO_INCREMENT;
--
-- AUTO_INCREMENT for table `interface`
--
ALTER TABLE `interface`
  MODIFY `userID` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;
--
-- AUTO_INCREMENT for table `job`
--
ALTER TABLE `job`
  MODIFY `jobID` int(11) NOT NULL AUTO_INCREMENT;
--
-- AUTO_INCREMENT for table `node`
--
ALTER TABLE `node`
  MODIFY `nodeID` int(11) NOT NULL AUTO_INCREMENT;
--
-- AUTO_INCREMENT for table `output`
--
ALTER TABLE `output`
  MODIFY `outputID` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;
--
-- AUTO_INCREMENT for table `policy`
--
ALTER TABLE `policy`
  MODIFY `policyID` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;
--
-- AUTO_INCREMENT for table `transcodeJob`
--
ALTER TABLE `transcodeJob`
  MODIFY `transcodeJobID` int(11) NOT NULL AUTO_INCREMENT;
--
-- Constraints for dumped tables
--

--
-- Constraints for table `exportJob`
--
ALTER TABLE `exportJob`
  ADD CONSTRAINT `exportJob_ibfk_1` FOREIGN KEY (`fk_nodeUUID`) REFERENCES `node` (`nodeUUID`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `exportJob_ibfk_2` FOREIGN KEY (`fk_jobUUID`) REFERENCES `job` (`jobUUID`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `ingestJob`
--
ALTER TABLE `ingestJob`
  ADD CONSTRAINT `ingestJob_ibfk_1` FOREIGN KEY (`fk_nodeUUID`) REFERENCES `node` (`nodeUUID`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `ingestJob_ibfk_2` FOREIGN KEY (`fk_jobUUID`) REFERENCES `job` (`jobUUID`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `transcodeJob`
--
ALTER TABLE `transcodeJob`
  ADD CONSTRAINT `transcodeJob_ibfk_1` FOREIGN KEY (`fk_nodeUUID`) REFERENCES `node` (`nodeUUID`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `transcodeJob_ibfk_2` FOREIGN KEY (`fk_jobUUID`) REFERENCES `job` (`jobUUID`) ON DELETE CASCADE ON UPDATE CASCADE;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
