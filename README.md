# Parser-Utility

Parser Utility is a Django web application designed to streamline the conversion of flat files (tab-delimited text files) to structured formats such as JSON and XML, and vice versa. It enables users to easily transform data between formats commonly used in system integrations and data exchange workflows.

## Features

### 1) Bidirectional File Conversion 
   Supports conversion from tab-delimited text files to JSON and XML formats, as well as converting JSON or XML files back into tab-delimited text for easy import/export handling.

### 2) Conversion History and Downloads 
   Automatically stores a log of all past conversions, allowing users to view and download both input and output files at any time.

### 3) Role-Based Authentication 
   Differentiates access levels between standard users and administrators, ensuring secure control over application features.

### 4) Admin Panel with User Controls 
   Administrators have access to a dedicated registration form and can create, update, or delete user accounts as needed.

### 5) User Profile Management 
   Logged-in users can manage their own profile information, including updating their name, password, and company name.

## Tech Stack

1. Frontend: HTML, CSS, JavaScript
2. Backend: Django
3. Database: MySQL
4. File Storage: AWS S3

## Installation

1) Clone the repository
   
   ```
   git clone https://github.com/channapd/Parser-Utility.git
   ```

2) Navigate to the project folder

   ```
   cd Parser-Utility-main
   ```

3) Install dependencies

   ```
   pip install -r requirements.txt
   ```

4) Add API Keys

   Create a .env file and add the AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME, AWS_S3_REGION_NAME, DJANGO_SECRET_KEY


6) Run the application

   ```
   python manage.py runserver
   ```
