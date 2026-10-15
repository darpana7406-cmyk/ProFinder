# ProFinder – Smart Professional Service Discovery & Management System

> **Find. Compare. Connect. Get It Done.**

ProFinder is a web-based **Professional Service Discovery and Management System** that connects customers with service professionals through a centralized platform.

The system allows users to discover professionals, compare services, view ratings and reviews, check availability, communicate with providers, manage favorites, book services, apply coupons, and manage wallet transactions.

The project is developed using **Python Flask** for the backend and **MySQL** for database management.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Objectives](#objectives)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [System Architecture](#system-architecture)
- [Project Structure](#project-structure)
- [Database](#database)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Application Workflow](#application-workflow)
- [Security](#security)
- [Future Enhancements](#future-enhancements)
- [Developer](#developer)
- [License](#license)

---

## Project Overview

Finding a reliable professional for services such as repairs, maintenance, technical assistance, tutoring, and other professional work can be difficult when information is distributed across different platforms.

**ProFinder** provides a centralized solution where customers can search for professionals based on their requirements and evaluate them using information such as:

- Service category
- Service type
- Location
- Experience
- Pricing
- Ratings
- Customer reviews
- Availability

The platform also provides communication, booking, favorites, notifications, coupons, wallet transactions, and referral functionality.

---

## Objectives

The main objectives of ProFinder are:

- Provide a centralized platform for professional service discovery.
- Allow customers to search and compare service providers.
- Provide transparent information about services and pricing.
- Allow customers to view professional ratings and reviews.
- Provide service availability and booking functionality.
- Enable communication between customers and professionals.
- Provide favorites and search history for easier service discovery.
- Implement coupons and wallet-based transactions.
- Provide a referral and reward mechanism.
- Maintain structured and relational service data using MySQL.

---

## Features

### Customer Features

- User registration and login
- Secure password authentication
- Browse service categories
- Search for professionals
- Filter and compare professionals
- View professional profiles
- View services and pricing
- View ratings and reviews
- Check professional availability
- Book services
- Multi-service booking
- Add/remove professionals from favorites
- View search history
- Chat with professionals
- Receive notifications
- Apply coupons
- Manage wallet balance
- View wallet transactions
- Referral and reward system

### Professional Features

Professionals can manage their service-related information and interact with customers through the platform.

The system supports:

- Professional profiles
- Service listings
- Experience information
- Service pricing
- Availability management
- Customer communication
- Booking management
- Ratings and reviews
- Professional verification information

### Search and Filtering

Customers can discover professionals according to their requirements.

The platform supports searching and filtering based on information such as:

- Service category
- Service type
- Location
- Experience
- Rating
- Price
- Verification status

### Ratings and Reviews

Customers can provide feedback about professionals after using their services.

The system maintains:

- Professional ratings
- Customer reviews
- Review dates
- Number of reviews
- Approved reviews

This helps customers make better decisions when selecting a professional.

### Favorites

Customers can save professionals for future reference.

The favorites functionality allows users to:

- Add professionals to favorites
- Remove professionals from favorites
- View saved professionals
- Quickly access professional information

### Chat and Messaging

ProFinder provides an internal messaging system for communication between customers and professionals.

The system supports:

- One-to-one conversations
- Message timestamps
- Read/unread message status
- Conversation management
- Message deletion
- New message notifications

### Notifications

The notification system keeps users informed about important activities such as:

- New messages
- Booking-related events
- Referral activities
- Other system notifications

### Booking and Availability

Customers can check professional availability before booking a service.

The system maintains:

- Available dates
- Start time
- End time
- Booking status
- Professional information
- Service information

### Coupon System

The application includes a coupon mechanism for discounts.

The system supports:

- Coupon codes
- Discount calculation
- Validity dates
- Usage limits
- Coupon validation
- Customer eligibility

### Wallet

Customers can manage their service-related transactions through a wallet.

Wallet functionality includes:

- Wallet balance
- Wallet top-up
- Transaction history
- Payment-related transactions

### Referral System

ProFinder includes a referral mechanism through which users can invite other users.

The system supports:

- Referral codes
- Referral invitations
- Referral tracking
- Referral rewards
- Referral history

---

## Technology Stack

### Backend

- Python
- Flask
- Flask-MySQLdb
- PyMySQL
- Flask-Mail
- Werkzeug

### Frontend

- HTML5
- CSS3
- JavaScript
- Jinja2 Templates

### Database

- MySQL
- Relational database
- SQL
- Foreign key relationships

### Development Tools

- Python
- MySQL
- Git
- GitHub

---

## System Architecture

```text
                    ┌─────────────────────┐
                    │      Customer       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Web Interface    │
                    │   HTML / CSS / JS   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     Flask App       │
                    │       app.py        │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
             ▼                 ▼                 ▼
      Authentication      Service Logic     Notifications
             │                 │                 │
             └─────────────────┼─────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │      MySQL DB       │
                    │     profinder_db    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Professionals    │
                    └─────────────────────┘
```

---

## Project Structure

```text
ProFinder/
│
├── app.py
├── config.py
├── requirements.txt
├── .gitignore
│
├── database/
│   └── Database files / SQL scripts
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
└── templates/
    ├── HTML templates
    ├── Customer pages
    ├── Professional pages
    ├── Booking pages
    ├── Chat pages
    └── Dashboard pages
```

---

## Database

ProFinder uses a MySQL relational database for storing application data.

The database manages information related to:

```text
Person
Customer
Provider
Location
Service_Category
Service_Type
Provider_Service
Review
Availability
Favorite
Message
NotificationLog
Coupon
WalletTransaction
Referral
```

The database design allows different components of the application to be connected using relational relationships and foreign keys.

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/darpana7406-cmyk/ProFinder.git
```

Navigate to the project directory:

```bash
cd ProFinder
```

### 2. Create a Virtual Environment

For Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

For macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

The project includes a `requirements.txt` file.

Install the required packages using:

```bash
pip install -r requirements.txt
```

---

## Configuration

Configure the application according to your local MySQL setup.

The database configuration should contain your local MySQL information, for example:

```python
MYSQL_HOST = "localhost"
MYSQL_USER = "root"
MYSQL_PASSWORD = "your_password"
MYSQL_DB = "profinder_db"
```

Do not commit actual passwords, secret keys, API keys, or other sensitive credentials to GitHub.

For production deployment, environment variables should be used for sensitive configuration values.

---

## Database Setup

Create the MySQL database:

```sql
CREATE DATABASE profinder_db;
```

Import the SQL/database files available in the `database` directory.

Make sure that the MySQL server is running before starting the Flask application.

---

## Running the Application

After completing the installation and database configuration, run:

```bash
python app.py
```

The application will start on the configured Flask development server.

Open your browser and visit:

```text
http://127.0.0.1:5000/
```

---

## Application Workflow

```text
User
  │
  ▼
Register / Login
  │
  ▼
Select Service Category
  │
  ▼
Search Professionals
  │
  ▼
Filter / Compare
  │
  ▼
View Professional Profile
  │
  ├───────────────┐
  │               │
  ▼               ▼
Reviews         Services
  │               │
  └───────┬───────┘
          ▼
   Check Availability
          │
          ▼
      Book Service
          │
          ▼
 Apply Coupon / Wallet
          │
          ▼
   Communicate
          │
          ▼
   Service Completion
          │
          ▼
    Rating & Review
```

---

## Security

The application incorporates security mechanisms such as:

- Password hashing
- Session-based authentication
- Login-protected routes
- Role-based access control
- SQL parameterized queries
- Input validation
- Controlled access to customer/provider functionality

For production deployment, additional security measures should be considered, including:

- Environment-based secrets
- CSRF protection
- HTTPS
- Secure session cookies
- Rate limiting
- Strong password policies
- Input sanitization
- Secure email credentials

---

## Future Enhancements

### AI-Based Professional Recommendation

Develop a recommendation system that ranks professionals based on:

- User requirements
- Previous bookings
- Ratings
- Price
- Location
- Experience
- Availability

### Location-Based Matching

Integrate maps and geolocation services to recommend professionals based on distance from the customer.

### Online Payment Gateway

Integrate a secure online payment gateway such as Razorpay or Stripe.

### Mobile Application

Develop a mobile version of ProFinder using technologies such as:

- Flutter
- React Native

### Real-Time Notifications

Implement real-time notifications for:

- Booking confirmation
- Booking cancellation
- New messages
- Service reminders
- Payment updates

### Analytics Dashboard

Provide dashboards for:

- User activity
- Professional performance
- Booking statistics
- Revenue
- Popular services
- User growth

### Intelligent Ranking System

Develop an advanced ranking system combining:

```text
Rating
+ Experience
+ Price
+ Distance
+ Reviews
+ Availability
+ Customer Preferences
```

to generate personalized professional recommendations.

---

## Advantages

- Centralized professional service discovery
- Easy comparison of service providers
- Ratings and review system
- Availability-based booking
- Customer-provider communication
- Favorites and search history
- Coupon and wallet functionality
- Referral and reward system
- Relational MySQL database
- Role-based access control
- Scalable Flask-based architecture

---

## Academic Project

**Project:** ProFinder – Smart Professional Service Discovery and Management System

**Domain:** Web Development / Database Management System

**Backend:** Python Flask

**Frontend:** HTML, CSS, JavaScript, Jinja2

**Database:** MySQL

**Architecture:** Client-Server Web Application

**Project Type:** DBMS / Full-Stack Web Application

---

## Developer

**Darpana Shintre**

B.Tech – Electronics & Communication Engineering (AI & ML)

PRN: 1022411055

---

## Repository

[ProFinder – GitHub Repository](https://github.com/darpana7406-cmyk/ProFinder)

---

## License

This project is developed for academic and educational purposes.

---

## Acknowledgements

This project was developed as an academic project to demonstrate the implementation of a database-driven professional service discovery and management platform using Flask and MySQL.
