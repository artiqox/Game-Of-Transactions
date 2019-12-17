# Game-Of-Transactions
Example AIE dApp - telegram bot that runs lottery like event.

Usage:
/gameMe gets telegram user one ticket.
/GameMyDude @friend gets your friend one ticket

Requirements:
ArtiqoxEnergy blockchain is used but its easy to migrate it to any NXT based blockchain.
mysql db:

CREATE TABLE `user` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(64) DEFAULT NULL,
  `displayname` varchar(64) DEFAULT NULL,
  `password_hash` varchar(128) DEFAULT NULL,
  `last_seen` datetime DEFAULT NULL,
  `confirm_my_stuff` varchar(288) DEFAULT NULL,
  `confirm_my_stuff_reverse` varchar(128) DEFAULT NULL,
  `username_confirmed_at` datetime DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `role` int(11) DEFAULT NULL,
  `aie_account` varchar(64) DEFAULT NULL,
  `aie_public_key` varchar(64) DEFAULT NULL,
  `aie_secret_encrypted` varchar(300) DEFAULT NULL,
  `aie_salt` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_user_username` (`username`),
  KEY `ix_user_aie_account` (`aie_account`),
  KEY `ix_user_aie_public_key` (`aie_public_key`),
  KEY `ix_user_confirm_my_stuff` (`confirm_my_stuff`),
  KEY `ix_user_confirm_my_stuff_reverse` (`confirm_my_stuff_reverse`),
  KEY `ix_user_displayname` (`displayname`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `usertelegram` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(120) DEFAULT NULL,
  `total_gives_amount` float DEFAULT '0',
  `total_gives_number` int(11) DEFAULT '0',
  `total_received_amount` float DEFAULT '0',
  `total_received_number` int(11) DEFAULT '0',
  `notify_me` tinyint(1) NOT NULL DEFAULT '0',
  `promote_me` tinyint(1) NOT NULL DEFAULT '0',
  `external_wallet` varchar(34) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
