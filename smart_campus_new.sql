-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Dec 03, 2025 at 06:12 PM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.0.30

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `smart_campus_new`
--

-- --------------------------------------------------------

--
-- Table structure for table `ads`
--

CREATE TABLE `ads` (
  `id` int(11) NOT NULL,
  `instructor_id` int(11) NOT NULL,
  `course_id` int(11) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `text` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `ads`
--

INSERT INTO `ads` (`id`, `instructor_id`, `course_id`, `created_at`, `text`) VALUES
(1, 3, 1, '2025-11-23 17:54:05', 'Hi'),
(2, 3, 1, '2025-11-28 09:32:52', NULL),
(3, 3, 1, '2025-11-28 10:05:36', 'adcs');

-- --------------------------------------------------------

--
-- Table structure for table `assignment`
--

CREATE TABLE `assignment` (
  `id` int(11) NOT NULL,
  `course_id` int(11) DEFAULT NULL,
  `title` varchar(100) DEFAULT NULL,
  `description` text DEFAULT NULL,
  `start_time` datetime DEFAULT NULL,
  `end_time` datetime DEFAULT NULL,
  `type` enum('Quiz','Assignment') NOT NULL,
  `due_date` date DEFAULT NULL,
  `total_mark` int(11) DEFAULT NULL,
  `duration` int(11) DEFAULT NULL,
  `question_count` int(11) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `file_path` varchar(512) DEFAULT NULL,
  `published` tinyint(1) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `assignment`
--

INSERT INTO `assignment` (`id`, `course_id`, `title`, `description`, `start_time`, `end_time`, `type`, `due_date`, `total_mark`, `duration`, `question_count`, `created_at`, `file_path`, `published`) VALUES
(1, 1, 'Assignment ', NULL, NULL, NULL, 'Assignment', '2025-11-30', 20, NULL, NULL, '2025-11-23 21:37:12', NULL, 0),
(26, 1, 'بب', 'بببب', NULL, NULL, 'Assignment', '2025-12-10', 2, NULL, NULL, '2025-12-02 22:34:44', 'uploads/assignment_26_1764707684_assignment_6.pdf', 0),
(27, 1, 'صص', 'Quiz created from UI', NULL, NULL, 'Quiz', '2025-12-08', 10, NULL, NULL, '2025-12-02 22:59:53', NULL, 0),
(28, 1, 'e', 'Quiz created from UI', NULL, NULL, 'Quiz', '2025-12-10', 5, NULL, NULL, '2025-12-02 23:08:36', NULL, 1),
(29, 1, 'gg', '', NULL, NULL, 'Assignment', '2025-12-04', 5, NULL, NULL, '2025-12-03 10:17:26', 'uploads/assignment_29_1764749846_assignment_24_1764706962_assignment_6.pdf', 0),
(30, 1, 'qq', 'Quiz created from UI', NULL, NULL, 'Quiz', '2025-12-04', 5, NULL, NULL, '2025-12-03 10:17:57', NULL, 1);

-- --------------------------------------------------------

--
-- Table structure for table `assignment_submissions`
--

CREATE TABLE `assignment_submissions` (
  `id` int(11) NOT NULL,
  `assignment_id` int(11) DEFAULT NULL,
  `student_id` int(11) DEFAULT NULL,
  `original_filename` varchar(255) DEFAULT NULL,
  `file_path` varchar(500) DEFAULT NULL,
  `uploaded_at` datetime DEFAULT NULL,
  `locked` tinyint(1) NOT NULL DEFAULT 1,
  `grade` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `assignment_submissions`
--

INSERT INTO `assignment_submissions` (`id`, `assignment_id`, `student_id`, `original_filename`, `file_path`, `uploaded_at`, `locked`, `grade`) VALUES
(6, 1, 5, 'book.pdf', 'uploads/submission_5_1_1764490295_book.pdf', '2025-11-30 10:11:35', 1, 4);

-- --------------------------------------------------------

--
-- Table structure for table `attendance`
--

CREATE TABLE `attendance` (
  `id` int(11) NOT NULL,
  `student_id` int(11) NOT NULL,
  `course_id` int(11) NOT NULL,
  `date` date NOT NULL,
  `status` enum('Present','Absent') DEFAULT 'Present',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `session_id` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `attendance`
--

INSERT INTO `attendance` (`id`, `student_id`, `course_id`, `date`, `status`, `created_at`, `session_id`) VALUES
(1, 5, 1, '2025-11-23', 'Present', '2025-11-23 17:25:32', NULL),
(2, 5, 1, '2025-11-24', 'Present', '2025-11-24 07:11:14', NULL),
(3, 5, 1, '2025-11-24', 'Present', '2025-11-24 07:19:59', NULL),
(4, 5, 1, '2025-11-24', 'Present', '2025-11-24 08:28:42', NULL),
(5, 5, 1, '2025-11-27', 'Present', '2025-11-27 20:44:55', 8),
(6, 5, 1, '2025-11-29', 'Present', '2025-11-29 18:28:55', NULL),
(7, 5, 1, '2025-11-30', 'Present', '2025-11-30 08:59:26', 11);

-- --------------------------------------------------------

--
-- Table structure for table `attendance_sessions`
--

CREATE TABLE `attendance_sessions` (
  `id` int(11) NOT NULL,
  `course_id` int(11) NOT NULL,
  `started_by` int(11) NOT NULL,
  `start_time` datetime NOT NULL DEFAULT current_timestamp(),
  `end_time` datetime DEFAULT NULL,
  `active` tinyint(1) DEFAULT 1,
  `note` varchar(255) DEFAULT NULL,
  `session_code` varchar(20) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `attendance_sessions`
--

INSERT INTO `attendance_sessions` (`id`, `course_id`, `started_by`, `start_time`, `end_time`, `active`, `note`, `session_code`, `is_active`) VALUES
(1, 1, 3, '2025-11-27 21:41:29', '2025-11-27 21:41:31', 0, NULL, NULL, 1),
(2, 1, 3, '2025-11-27 21:41:39', '2025-11-27 21:41:43', 0, NULL, NULL, 1),
(3, 1, 3, '2025-11-27 21:44:26', '2025-11-27 22:00:47', 0, NULL, NULL, 1),
(4, 1, 3, '2025-11-27 22:16:58', '2025-11-27 22:24:03', 0, NULL, '961930', 1),
(5, 1, 3, '2025-11-27 22:24:03', '2025-11-27 22:24:12', 0, NULL, '244329', 1),
(6, 1, 3, '2025-11-27 22:24:12', '2025-11-27 22:30:01', 0, NULL, '702805', 1),
(7, 1, 3, '2025-11-27 22:30:01', '2025-11-27 22:44:40', 0, NULL, '751578', 1),
(8, 1, 3, '2025-11-27 22:44:40', '2025-11-27 22:45:01', 0, NULL, '339567', 1),
(9, 1, 3, '2025-11-27 23:20:34', '2025-11-27 23:20:37', 0, NULL, '184768', 1),
(10, 1, 3, '2025-11-30 10:59:08', '2025-11-30 10:59:16', 0, NULL, '711240', 1),
(11, 1, 3, '2025-11-30 10:59:16', NULL, 1, NULL, '458885', 1);

-- --------------------------------------------------------

--
-- Table structure for table `book`
--

CREATE TABLE `book` (
  `id` int(11) NOT NULL,
  `course_id` int(11) DEFAULT NULL,
  `title` varchar(100) DEFAULT NULL,
  `file_path` varchar(255) DEFAULT NULL,
  `type` enum('book','lecture','video','file') NOT NULL DEFAULT 'book',
  `uploaded_by` int(11) DEFAULT NULL,
  `description` text DEFAULT NULL,
  `uploaded_at` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `book`
--

INSERT INTO `book` (`id`, `course_id`, `title`, `file_path`, `type`, `uploaded_by`, `description`, `uploaded_at`) VALUES
(5, NULL, 'lec 1', 'uploads/lec_1.pdf', 'book', NULL, NULL, '2025-11-28 14:02:25'),
(6, 1, 'professional ethics', 'uploads/book.pdf', 'book', 1, NULL, '2025-11-28 16:52:38'),
(7, 1, 'test', 'uploads/ctQVHmtJ40f3ZMPuuTmZH24iVfdQuFNKjNgSkPWX_1.pdf', 'book', NULL, NULL, '2025-12-01 13:29:35'),
(8, 1, 'lec', 'uploads/submission_5_1_1764445520_book.pdf', 'book', NULL, NULL, '2025-12-02 07:38:56'),
(9, 1, 'g', 'uploads/assignment_6.pdf', 'book', NULL, NULL, '2025-12-02 10:09:33'),
(10, 1, 'tt', 'uploads/assignment_6.pdf', 'book', NULL, NULL, '2025-12-02 21:36:30'),
(11, 1, 'Lecture - سي', 'uploads/assignment_6.pdf', 'lecture', NULL, NULL, '2025-12-02 22:08:12'),
(12, 1, 'b', 'uploads/book.pdf', 'book', NULL, NULL, '2025-12-03 10:15:48'),
(13, 1, 'Lecture - l', 'uploads/assignment_24_1764706962_assignment_6.pdf', 'lecture', NULL, NULL, '2025-12-03 10:16:48');

-- --------------------------------------------------------

--
-- Table structure for table `course`
--

CREATE TABLE `course` (
  `id` int(11) NOT NULL,
  `course_name` varchar(100) DEFAULT NULL,
  `department` varchar(100) DEFAULT NULL,
  `instructor_id` int(11) DEFAULT NULL,
  `book_id` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `course`
--

INSERT INTO `course` (`id`, `course_name`, `department`, `instructor_id`, `book_id`) VALUES
(1, 'professional ethics', 'Electronics', 3, 13);

-- --------------------------------------------------------

--
-- Table structure for table `course_grades`
--

CREATE TABLE `course_grades` (
  `id` int(11) NOT NULL,
  `course_id` int(11) NOT NULL,
  `student_id` int(11) NOT NULL,
  `mid_grade` decimal(6,2) DEFAULT NULL,
  `final_grade` decimal(6,2) DEFAULT NULL,
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `course_grades`
--

INSERT INTO `course_grades` (`id`, `course_id`, `student_id`, `mid_grade`, `final_grade`, `updated_at`) VALUES
(1, 1, 7, 10.00, 75.00, '2025-12-03 16:59:25'),
(2, 1, 5, 5.00, 50.00, '2025-12-03 16:59:29');

-- --------------------------------------------------------

--
-- Table structure for table `grades`
--

CREATE TABLE `grades` (
  `id` int(11) NOT NULL,
  `student_id` int(11) DEFAULT NULL,
  `course_id` int(11) DEFAULT NULL,
  `assignment_id` int(11) DEFAULT NULL,
  `grade` decimal(5,2) DEFAULT NULL,
  `total_grade` decimal(5,2) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `grades`
--

INSERT INTO `grades` (`id`, `student_id`, `course_id`, `assignment_id`, `grade`, `total_grade`) VALUES
(1, 5, 1, 1, 20.00, 20.00);

-- --------------------------------------------------------

--
-- Table structure for table `quiz_question`
--

CREATE TABLE `quiz_question` (
  `id` int(11) NOT NULL,
  `assignment_id` int(11) NOT NULL,
  `q_type` enum('MCQ','TF','Short') NOT NULL DEFAULT 'MCQ',
  `question_text` text NOT NULL,
  `options` text DEFAULT NULL,
  `correct_answer` varchar(255) DEFAULT NULL,
  `marks` int(11) DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `quiz_question`
--

INSERT INTO `quiz_question` (`id`, `assignment_id`, `q_type`, `question_text`, `options`, `correct_answer`, `marks`, `created_at`) VALUES
(1, 28, 'MCQ', '2', '[\"hi\", \"bye\"]', '1', 1, '2025-12-02 21:09:00'),
(2, 28, 'MCQ', 'tt', '[\"file\", \"path\"]', '1', 1, '2025-12-02 21:09:23'),
(3, 30, 'MCQ', 'hi', '[\"hi\", \"bye\"]', '1', 1, '2025-12-03 08:18:29'),
(4, 30, 'MCQ', 'bye', '[\"hi\", \"bye\"]', '2', 1, '2025-12-03 08:18:46');

-- --------------------------------------------------------

--
-- Table structure for table `schedule`
--

CREATE TABLE `schedule` (
  `id` int(11) NOT NULL,
  `course_id` int(11) NOT NULL,
  `instructor_id` int(11) NOT NULL,
  `day` varchar(20) NOT NULL,
  `start_time` time NOT NULL,
  `end_time` time NOT NULL,
  `room` varchar(50) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `schedule`
--

INSERT INTO `schedule` (`id`, `course_id`, `instructor_id`, `day`, `start_time`, `end_time`, `room`, `created_at`) VALUES
(1, 1, 3, 'Sunday', '01:00:00', '03:00:00', 'Room3', '2025-11-23 11:35:41');

-- --------------------------------------------------------

--
-- Table structure for table `student_courses`
--

CREATE TABLE `student_courses` (
  `student_id` int(11) NOT NULL,
  `course_id` int(11) NOT NULL,
  `semester` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `student_courses`
--

INSERT INTO `student_courses` (`student_id`, `course_id`, `semester`) VALUES
(5, 1, '1'),
(7, 1, NULL);

-- --------------------------------------------------------

--
-- Stand-in structure for view `student_course_totals`
-- (See below for the actual view)
--
CREATE TABLE `student_course_totals` (
`student_id` int(11)
,`course_id` int(11)
,`total_grade` decimal(27,2)
);

-- --------------------------------------------------------

--
-- Table structure for table `submissions`
--

CREATE TABLE `submissions` (
  `id` int(11) NOT NULL,
  `assignment_id` int(11) NOT NULL,
  `student_id` int(11) NOT NULL,
  `file_path` varchar(255) DEFAULT NULL,
  `submitted_at` datetime DEFAULT NULL,
  `status` varchar(50) DEFAULT 'submitted',
  `grade` float DEFAULT NULL,
  `feedback` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `name` varchar(100) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `pass` varchar(100) DEFAULT NULL,
  `image` varchar(255) DEFAULT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `role` enum('Student','Instructor','Admin') NOT NULL,
  `department` varchar(100) DEFAULT NULL,
  `level` varchar(10) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `name`, `email`, `pass`, `image`, `phone`, `role`, `department`, `level`) VALUES
(1, 'Admin 1', 'admin1@example.com', '1234', 'uploads/admin.jpg', '011111111', 'Admin', '', ''),
(2, 'Student 1', 'student1@example.com', '1234', 'uploads/stu.jpg', '0101111111', 'Student', 'Electronic ', '1'),
(3, 'Instructor 1', 'inst1@example.com', '1234', 'uploads/prof.jpg', '012222933', 'Instructor', 'Electronic', ''),
(5, 'student 2', 'student2@gmail.com', '1234', 'uploads/stu.jpg', '01222223222', 'Student', 'Electronic', '4'),
(7, 'rana', 'ranaeldaly03@gmail.com', '1234', 'admin.png', '01112036070', 'Student', 'cs', '3');

-- --------------------------------------------------------

--
-- Structure for view `student_course_totals`
--
DROP TABLE IF EXISTS `student_course_totals`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `student_course_totals`  AS SELECT `grades`.`student_id` AS `student_id`, `grades`.`course_id` AS `course_id`, sum(`grades`.`grade`) AS `total_grade` FROM `grades` GROUP BY `grades`.`student_id`, `grades`.`course_id` ;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `ads`
--
ALTER TABLE `ads`
  ADD PRIMARY KEY (`id`),
  ADD KEY `instructor_id` (`instructor_id`),
  ADD KEY `course_id` (`course_id`);

--
-- Indexes for table `assignment`
--
ALTER TABLE `assignment`
  ADD PRIMARY KEY (`id`),
  ADD KEY `course_id` (`course_id`);

--
-- Indexes for table `assignment_submissions`
--
ALTER TABLE `assignment_submissions`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `attendance`
--
ALTER TABLE `attendance`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_attendance_student` (`student_id`),
  ADD KEY `idx_attendance_course` (`course_id`),
  ADD KEY `idx_attendance_date` (`date`),
  ADD KEY `session_id` (`session_id`);

--
-- Indexes for table `attendance_sessions`
--
ALTER TABLE `attendance_sessions`
  ADD PRIMARY KEY (`id`),
  ADD KEY `course_id` (`course_id`),
  ADD KEY `started_by` (`started_by`);

--
-- Indexes for table `book`
--
ALTER TABLE `book`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `course`
--
ALTER TABLE `course`
  ADD PRIMARY KEY (`id`),
  ADD KEY `instructor_id` (`instructor_id`),
  ADD KEY `book_id` (`book_id`);

--
-- Indexes for table `course_grades`
--
ALTER TABLE `course_grades`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uniq_course_student` (`course_id`,`student_id`);

--
-- Indexes for table `grades`
--
ALTER TABLE `grades`
  ADD PRIMARY KEY (`id`),
  ADD KEY `student_id` (`student_id`),
  ADD KEY `course_id` (`course_id`),
  ADD KEY `assignment_id` (`assignment_id`);

--
-- Indexes for table `quiz_question`
--
ALTER TABLE `quiz_question`
  ADD PRIMARY KEY (`id`),
  ADD KEY `assignment_id` (`assignment_id`);

--
-- Indexes for table `schedule`
--
ALTER TABLE `schedule`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_schedule_course` (`course_id`),
  ADD KEY `idx_schedule_instructor` (`instructor_id`);

--
-- Indexes for table `student_courses`
--
ALTER TABLE `student_courses`
  ADD PRIMARY KEY (`student_id`,`course_id`),
  ADD KEY `course_id` (`course_id`);

--
-- Indexes for table `submissions`
--
ALTER TABLE `submissions`
  ADD PRIMARY KEY (`id`),
  ADD KEY `assignment_id` (`assignment_id`),
  ADD KEY `student_id` (`student_id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `email` (`email`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `ads`
--
ALTER TABLE `ads`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `assignment`
--
ALTER TABLE `assignment`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=31;

--
-- AUTO_INCREMENT for table `assignment_submissions`
--
ALTER TABLE `assignment_submissions`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=9;

--
-- AUTO_INCREMENT for table `attendance`
--
ALTER TABLE `attendance`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;

--
-- AUTO_INCREMENT for table `attendance_sessions`
--
ALTER TABLE `attendance_sessions`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=12;

--
-- AUTO_INCREMENT for table `book`
--
ALTER TABLE `book`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=14;

--
-- AUTO_INCREMENT for table `course`
--
ALTER TABLE `course`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `course_grades`
--
ALTER TABLE `course_grades`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `grades`
--
ALTER TABLE `grades`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `quiz_question`
--
ALTER TABLE `quiz_question`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT for table `schedule`
--
ALTER TABLE `schedule`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `submissions`
--
ALTER TABLE `submissions`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `ads`
--
ALTER TABLE `ads`
  ADD CONSTRAINT `ads_ibfk_1` FOREIGN KEY (`instructor_id`) REFERENCES `users` (`id`),
  ADD CONSTRAINT `ads_ibfk_2` FOREIGN KEY (`course_id`) REFERENCES `course` (`id`);

--
-- Constraints for table `assignment`
--
ALTER TABLE `assignment`
  ADD CONSTRAINT `assignment_ibfk_1` FOREIGN KEY (`course_id`) REFERENCES `course` (`id`);

--
-- Constraints for table `attendance`
--
ALTER TABLE `attendance`
  ADD CONSTRAINT `attendance_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `attendance_ibfk_2` FOREIGN KEY (`course_id`) REFERENCES `course` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `attendance_ibfk_3` FOREIGN KEY (`session_id`) REFERENCES `attendance_sessions` (`id`),
  ADD CONSTRAINT `attendance_ibfk_4` FOREIGN KEY (`session_id`) REFERENCES `attendance_sessions` (`id`),
  ADD CONSTRAINT `attendance_ibfk_5` FOREIGN KEY (`session_id`) REFERENCES `attendance_sessions` (`id`);

--
-- Constraints for table `attendance_sessions`
--
ALTER TABLE `attendance_sessions`
  ADD CONSTRAINT `attendance_sessions_ibfk_1` FOREIGN KEY (`course_id`) REFERENCES `course` (`id`),
  ADD CONSTRAINT `attendance_sessions_ibfk_2` FOREIGN KEY (`started_by`) REFERENCES `users` (`id`);

--
-- Constraints for table `course`
--
ALTER TABLE `course`
  ADD CONSTRAINT `course_ibfk_1` FOREIGN KEY (`instructor_id`) REFERENCES `users` (`id`),
  ADD CONSTRAINT `course_ibfk_2` FOREIGN KEY (`book_id`) REFERENCES `book` (`id`);

--
-- Constraints for table `grades`
--
ALTER TABLE `grades`
  ADD CONSTRAINT `grades_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`),
  ADD CONSTRAINT `grades_ibfk_2` FOREIGN KEY (`course_id`) REFERENCES `course` (`id`),
  ADD CONSTRAINT `grades_ibfk_3` FOREIGN KEY (`assignment_id`) REFERENCES `assignment` (`id`);

--
-- Constraints for table `quiz_question`
--
ALTER TABLE `quiz_question`
  ADD CONSTRAINT `quiz_question_ibfk_1` FOREIGN KEY (`assignment_id`) REFERENCES `assignment` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `schedule`
--
ALTER TABLE `schedule`
  ADD CONSTRAINT `schedule_ibfk_1` FOREIGN KEY (`course_id`) REFERENCES `course` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `schedule_ibfk_2` FOREIGN KEY (`instructor_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `student_courses`
--
ALTER TABLE `student_courses`
  ADD CONSTRAINT `student_courses_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`),
  ADD CONSTRAINT `student_courses_ibfk_2` FOREIGN KEY (`course_id`) REFERENCES `course` (`id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;


-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Dec 07, 2025 at 08:37 PM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.0.30

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `smart_campus_new`
--

-- --------------------------------------------------------

--
-- Table structure for table `payments`
--

CREATE TABLE `payments` (
  `payment_id` int(11) NOT NULL,
  `student_id` int(11) NOT NULL,
  `term` enum('term1','term2') NOT NULL,
  `amount` decimal(10,2) DEFAULT 0.00,
  `paid_date` date DEFAULT curdate()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `payments`
--

INSERT INTO `payments` (`payment_id`, `student_id`, `term`, `amount`, `paid_date`) VALUES
(2, 5, 'term1', 1500.00, '2025-12-07');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `payments`
--
ALTER TABLE `payments`
  ADD PRIMARY KEY (`payment_id`),
  ADD KEY `student_id` (`student_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `payments`
--
ALTER TABLE `payments`
  MODIFY `payment_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `payments`
--
ALTER TABLE `payments`
  ADD CONSTRAINT `payments_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;

