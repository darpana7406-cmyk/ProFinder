CREATE DATABASE IF NOT EXISTS profinder_db;
USE profinder_db;

-- ============================================
-- 1. PERSON
-- ============================================
CREATE TABLE Person (
    PersonID INT PRIMARY KEY AUTO_INCREMENT,
    FirstName VARCHAR(50) NOT NULL,
    LastName VARCHAR(50) NOT NULL,
    Phone VARCHAR(15) UNIQUE,
    Age INT,
    LocationID INT,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Person_Email (
    EmailID INT PRIMARY KEY AUTO_INCREMENT,
    PersonID INT NOT NULL,
    Email VARCHAR(100) NOT NULL UNIQUE,
    IsPrimary BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (PersonID) REFERENCES Person(PersonID) ON DELETE CASCADE
);

-- ============================================
-- 2. LOCATION
-- ============================================
CREATE TABLE Location (
    LocationID INT PRIMARY KEY AUTO_INCREMENT,
    City VARCHAR(50) NOT NULL,
    State VARCHAR(50) NOT NULL,
    Zip VARCHAR(10)
);

ALTER TABLE Person ADD FOREIGN KEY (LocationID) REFERENCES Location(LocationID);

-- ============================================
-- 3. CUSTOMER
-- ============================================
CREATE TABLE Customer (
    CustomerID INT PRIMARY KEY AUTO_INCREMENT,
    PersonID INT UNIQUE NOT NULL,
    SearchHistory TEXT,
    FOREIGN KEY (PersonID) REFERENCES Person(PersonID) ON DELETE CASCADE
);

-- ============================================
-- 4. PROVIDER
-- ============================================
CREATE TABLE Provider (
    ProviderID INT PRIMARY KEY AUTO_INCREMENT,
    PersonID INT UNIQUE NOT NULL,
    ExperienceYears INT DEFAULT 0,
    CertificationDocs VARCHAR(255),
    IsVerified BOOLEAN DEFAULT FALSE,
    AvgRating DECIMAL(3,2) DEFAULT 0.00,
    AgencyID INT,
    FOREIGN KEY (PersonID) REFERENCES Person(PersonID) ON DELETE CASCADE
);

CREATE TABLE Individual_Professional (
    IndivID INT PRIMARY KEY AUTO_INCREMENT,
    ProviderID INT UNIQUE NOT NULL,
    FOREIGN KEY (ProviderID) REFERENCES Provider(ProviderID) ON DELETE CASCADE
);

CREATE TABLE Agency (
    AgencyID INT PRIMARY KEY AUTO_INCREMENT,
    AgencyName VARCHAR(100) NOT NULL,
    NumProfessionals INT DEFAULT 0
);

ALTER TABLE Provider ADD FOREIGN KEY (AgencyID) REFERENCES Agency(AgencyID);

-- ============================================
-- 5. SERVICE CATEGORIES
-- ============================================
CREATE TABLE Service_Category (
    CategoryID INT PRIMARY KEY AUTO_INCREMENT,
    CategoryName VARCHAR(50) NOT NULL UNIQUE,
    ParentCategoryID INT NULL,
    FOREIGN KEY (ParentCategoryID) REFERENCES Service_Category(CategoryID)
);

CREATE TABLE Service_Type (
    ServiceTypeID INT PRIMARY KEY AUTO_INCREMENT,
    ServiceName VARCHAR(100) NOT NULL,
    Description TEXT,
    CategoryID INT NOT NULL,
    FOREIGN KEY (CategoryID) REFERENCES Service_Category(CategoryID)
);

CREATE TABLE Provider_Service (
    ProviderServiceID INT PRIMARY KEY AUTO_INCREMENT,
    ProviderID INT NOT NULL,
    ServiceTypeID INT NOT NULL,
    PricePerHour DECIMAL(10,2) NOT NULL,
    UNIQUE KEY unique_provider_service (ProviderID, ServiceTypeID),
    FOREIGN KEY (ProviderID) REFERENCES Provider(ProviderID) ON DELETE CASCADE,
    FOREIGN KEY (ServiceTypeID) REFERENCES Service_Type(ServiceTypeID)
);

-- ============================================
-- 6. BOOKING & REVIEW
-- ============================================
CREATE TABLE Booking (
    BookingID INT PRIMARY KEY AUTO_INCREMENT,
    CustomerID INT NOT NULL,
    ProviderID INT NOT NULL,
    ServiceTypeID INT NOT NULL,
    BookingDate DATE NOT NULL,
    BookingTime TIME NOT NULL,
    Status ENUM('Pending','Confirmed','Completed','Cancelled') DEFAULT 'Pending',
    IsEmergency BOOLEAN DEFAULT FALSE,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (CustomerID) REFERENCES Customer(CustomerID) ON DELETE CASCADE,
    FOREIGN KEY (ProviderID) REFERENCES Provider(ProviderID),
    FOREIGN KEY (ServiceTypeID) REFERENCES Service_Type(ServiceTypeID)
);

CREATE TABLE Review (
    ReviewID INT PRIMARY KEY AUTO_INCREMENT,
    BookingID INT UNIQUE NOT NULL,
    CustomerID INT NOT NULL,
    ProviderID INT NOT NULL,
    Comment TEXT,
    Rating INT CHECK (Rating BETWEEN 1 AND 5),
    ReviewDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (BookingID) REFERENCES Booking(BookingID) ON DELETE CASCADE,
    FOREIGN KEY (CustomerID) REFERENCES Customer(CustomerID),
    FOREIGN KEY (ProviderID) REFERENCES Provider(ProviderID)
);

CREATE TABLE Availability (
    AvailabilityID INT PRIMARY KEY AUTO_INCREMENT,
    ProviderID INT NOT NULL,
    AvailableDate DATE NOT NULL,
    StartTime TIME NOT NULL,
    EndTime TIME NOT NULL,
    IsBooked BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (ProviderID) REFERENCES Provider(ProviderID) ON DELETE CASCADE
);

CREATE TABLE Users (
    UserID INT PRIMARY KEY AUTO_INCREMENT,
    PersonID INT UNIQUE NOT NULL,
    Username VARCHAR(50) UNIQUE NOT NULL,
    PasswordHash VARCHAR(255) NOT NULL,
    Role ENUM('customer','provider','admin') NOT NULL,
    FOREIGN KEY (PersonID) REFERENCES Person(PersonID) ON DELETE CASCADE
);

-- ============================================
-- SAMPLE DATA
-- ============================================
INSERT INTO Location (City, State, Zip) VALUES
('Pune', 'Maharashtra', '411001'),
('Mumbai', 'Maharashtra', '400001'),
('Bangalore', 'Karnataka', '560001'),
('Delhi', 'Delhi', '110001'),
('Chennai', 'Tamil Nadu', '600001');

INSERT INTO Service_Category (CategoryName) VALUES
('Home Services'),('Healthcare'),('Education'),('Technology'),
('Automobile'),('Beauty'),('Events'),('Professional Services');

INSERT INTO Service_Type (ServiceName, Description, CategoryID) VALUES
('Electrician','Electrical repair',1),
('Plumber','Pipe fitting',1),
('Carpenter','Woodwork',1),
('AC Repair','AC service',1),
('Doctor','General physician',2),
('Dentist','Dental care',2),
('Physiotherapist','Physical therapy',2),
('Tutor','Academic tutoring',3),
('Coding Teacher','Programming',3),
('Music Teacher','Music lessons',3),
('Developer','Software dev',4),
('Designer','Graphic design',4),
('Laptop Repair','Computer repair',4),
('Mechanic','Vehicle repair',5),
('Car Wash','Vehicle cleaning',5),
('Makeup Artist','Beauty',6),
('Barber','Hair cutting',6),
('Photographer','Event photo',7),
('Caterer','Food service',7),
('Lawyer','Legal',8),
('Architect','Building design',8);

INSERT INTO Person (FirstName, LastName, Phone, Age, LocationID) VALUES
('Rahul','Sharma','9876543210',35,1),
('Priya','Patel','9876543211',28,1),
('Amit','Kumar','9876543212',42,2),
('Sneha','Joshi','9876543213',30,1),
('Vikram','Singh','9876543214',38,3),
('Ananya','Desai','9876543215',26,1),
('Rohan','Mehta','9876543216',45,2),
('Kavita','Nair','9876543217',33,4),
('Suresh','Reddy','9876543218',50,5),
('Meera','Iyer','9876543219',29,1);

INSERT INTO Person_Email (PersonID, Email, IsPrimary) VALUES
(1,'rahul@email.com',TRUE),(2,'priya@email.com',TRUE),
(3,'amit@email.com',TRUE),(4,'sneha@email.com',TRUE),
(5,'vikram@email.com',TRUE),(6,'ananya@email.com',TRUE),
(7,'rohan@email.com',TRUE),(8,'kavita@email.com',TRUE),
(9,'suresh@email.com',TRUE),(10,'meera@email.com',TRUE);

INSERT INTO Customer (PersonID, SearchHistory) VALUES
(1,'Electrician, Plumber'),(2,'Doctor, Tutor'),(3,'Developer'),
(8,'Makeup Artist'),(9,'Mechanic');

INSERT INTO Agency (AgencyName, NumProfessionals) VALUES
('Elite Services Pvt Ltd',2),('ProConnect Agency',1);

INSERT INTO Provider (PersonID, ExperienceYears, IsVerified, AvgRating, AgencyID) VALUES
(4,8,TRUE,4.5,NULL),
(5,12,TRUE,4.8,1),
(6,5,TRUE,4.2,NULL),
(7,15,TRUE,4.9,1),
(10,6,FALSE,3.8,NULL);

INSERT INTO Individual_Professional (ProviderID) VALUES (1),(3),(5);

INSERT INTO Provider_Service (ProviderID, ServiceTypeID, PricePerHour) VALUES
(1,1,500.00),(1,3,600.00),(2,5,800.00),(2,7,700.00),
(3,11,1200.00),(3,13,400.00),(4,5,1500.00),
(4,6,1000.00),(5,16,900.00);

INSERT INTO Availability (ProviderID, AvailableDate, StartTime, EndTime) VALUES
(1,'2026-12-15','09:00:00','12:00:00'),
(2,'2026-12-15','10:00:00','13:00:00'),
(3,'2026-12-16','09:00:00','17:00:00'),
(4,'2026-12-15','11:00:00','15:00:00'),
(5,'2026-12-17','10:00:00','16:00:00');

-- Password for all users: password123
INSERT INTO Users (PersonID, Username, PasswordHash, Role) VALUES
(1,'rahul','pbkdf2:sha256:600000$xyz$placeholder1','customer'),
(2,'priya','pbkdf2:sha256:600000$xyz$placeholder2','customer'),
(4,'sneha','pbkdf2:sha256:600000$xyz$placeholder3','provider'),
(5,'vikram','pbkdf2:sha256:600000$xyz$placeholder4','provider'),
(10,'admin','pbkdf2:sha256:600000$xyz$placeholder5','admin');

INSERT INTO Booking (CustomerID, ProviderID, ServiceTypeID, BookingDate, BookingTime, Status) VALUES
(1,1,1,'2025-11-10','10:00:00','Completed'),
(2,2,5,'2025-11-11','11:00:00','Completed'),
(3,3,11,'2025-11-12','14:00:00','Completed');

INSERT INTO Review (BookingID, CustomerID, ProviderID, Comment, Rating) VALUES
(1,1,1,'Excellent work!',5),
(2,2,2,'Good consultation',4),
(3,3,3,'Very knowledgeable',5);

-- VIEWS
CREATE VIEW vw_professional_search AS
SELECT p.ProviderID, pe.FirstName, pe.LastName, p.ExperienceYears,
       p.IsVerified, p.AvgRating, l.City, l.State,
       st.ServiceName, sc.CategoryName, ps.PricePerHour
FROM Provider p
JOIN Person pe ON p.PersonID = pe.PersonID
LEFT JOIN Location l ON pe.LocationID = l.LocationID
JOIN Provider_Service ps ON p.ProviderID = ps.ProviderID
JOIN Service_Type st ON ps.ServiceTypeID = st.ServiceTypeID
JOIN Service_Category sc ON st.CategoryID = sc.CategoryID;