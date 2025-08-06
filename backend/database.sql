CREATE DATABASE IF NOT EXISTS `quizo` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */;
USE `quizo`;

-- Drop the existing sign_up table if it exists
DROP TABLE IF EXISTS `sign_up`;

-- Create the updated sign_up table with additional columns
CREATE TABLE `sign_up` (
  `candidate_id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(50) NOT NULL,
  `gender` VARCHAR(10) NOT NULL,
  `dob` DATE NOT NULL,
  `mobile` VARCHAR(15) NOT NULL,
  `email` VARCHAR(45) NOT NULL,
  `password` VARCHAR(255) NOT NULL, -- To store the candidate's password (hashed)    
  UNIQUE KEY `email_UNIQUE` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert records into the updated sign_up table (without filling the new columns)
INSERT INTO `sign_up` (`name`, `gender`, `dob`, `mobile`, `email`, `password`) VALUES 
('Mridhul', 'Male', '1995-03-21', '1234567890', 'mridhul@gmail.com', 'cc'),
('Divya Tiwari', 'Female', '1997-08-14', '9876543210', 'divyansh01@gmail.com', 'hashed_password_2'),
('Hemant Sharma', 'Male', '1998-06-05', '1122334455', 'hemant56@gmail.com', 'hashed_password_3'),
('Krishna Kumar', 'Male', '1999-09-22', '2233445566', 'kumar1166@gmail.com', 'hashed_password_4'),
('Parth Patel', 'Male', '1996-11-30', '3344556677', 'parth529@gmail.com', 'hashed_password_5'),
('Admin Team', 'Other', '1985-04-12', '4455667788', 'quizo_admin@gmail.com', 'hashed_password_6');

