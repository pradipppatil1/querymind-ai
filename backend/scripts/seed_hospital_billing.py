import mysql.connector
from mysql.connector import Error
import random
from datetime import datetime, timedelta
from faker import Faker
import os
from dotenv import load_dotenv

load_dotenv()

fake = Faker()
Faker.seed(42)
random.seed(42)

def create_database_and_schema(cursor):
    print("Creating database 'hospital_billing' and schema...")
    cursor.execute("CREATE DATABASE IF NOT EXISTS hospital_billing")
    cursor.execute("USE hospital_billing")
    
    # Drop existing tables if re-running
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
    tables = ['claims', 'billing_records', 'procedures', 'admissions', 'providers', 'departments', 'patients']
    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

    cursor.execute("""
    CREATE TABLE patients (
        patient_id INT AUTO_INCREMENT PRIMARY KEY,
        first_name VARCHAR(100) NOT NULL,
        last_name VARCHAR(100) NOT NULL,
        dob DATE NOT NULL,
        gender VARCHAR(10),
        city VARCHAR(100),
        state VARCHAR(50)
    )
    """)

    cursor.execute("""
    CREATE TABLE departments (
        department_id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        floor INT,
        phone VARCHAR(20)
    )
    """)

    cursor.execute("""
    CREATE TABLE providers (
        provider_id INT AUTO_INCREMENT PRIMARY KEY,
        first_name VARCHAR(100) NOT NULL,
        last_name VARCHAR(100) NOT NULL,
        specialty VARCHAR(100),
        department_id INT,
        FOREIGN KEY (department_id) REFERENCES departments(department_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE admissions (
        admission_id INT AUTO_INCREMENT PRIMARY KEY,
        patient_id INT,
        provider_id INT,
        admission_date DATE NOT NULL,
        discharge_date DATE,
        primary_diagnosis VARCHAR(255),
        FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
        FOREIGN KEY (provider_id) REFERENCES providers(provider_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE procedures (
        procedure_id INT AUTO_INCREMENT PRIMARY KEY,
        admission_id INT,
        provider_id INT,
        procedure_name VARCHAR(255) NOT NULL,
        procedure_date DATE NOT NULL,
        cost DECIMAL(10, 2) NOT NULL,
        FOREIGN KEY (admission_id) REFERENCES admissions(admission_id),
        FOREIGN KEY (provider_id) REFERENCES providers(provider_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE billing_records (
        bill_id INT AUTO_INCREMENT PRIMARY KEY,
        admission_id INT,
        total_amount DECIMAL(10, 2) NOT NULL,
        status VARCHAR(50) NOT NULL,
        due_date DATE NOT NULL,
        FOREIGN KEY (admission_id) REFERENCES admissions(admission_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE claims (
        claim_id INT AUTO_INCREMENT PRIMARY KEY,
        bill_id INT,
        insurance_provider VARCHAR(100) NOT NULL,
        claim_status VARCHAR(50) NOT NULL,
        covered_amount DECIMAL(10, 2) NOT NULL,
        claim_date DATE NOT NULL,
        FOREIGN KEY (bill_id) REFERENCES billing_records(bill_id)
    )
    """)

def generate_data(cursor, conn):
    print("Generating synthetic data into MySQL (this may take a moment)...")
    
    # 1. Departments
    departments = ['Cardiology', 'Neurology', 'Orthopedics', 'Pediatrics', 'Oncology', 'Emergency']
    for i, dept in enumerate(departments):
        cursor.execute("INSERT INTO departments (name, floor, phone) VALUES (%s, %s, %s)",
                       (dept, i+1, fake.phone_number()[:15]))
    
    # 2. Providers
    provider_specialties = {
        1: ['Cardiologist', 'Cardiac Surgeon'],
        2: ['Neurologist', 'Neurosurgeon'],
        3: ['Orthopedic Surgeon', 'Physical Therapist'],
        4: ['Pediatrician'],
        5: ['Oncologist'],
        6: ['ER Physician', 'Trauma Surgeon']
    }
    for dept_id, specialties in provider_specialties.items():
        for _ in range(5):
            cursor.execute("INSERT INTO providers (first_name, last_name, specialty, department_id) VALUES (%s, %s, %s, %s)",
                           (fake.first_name(), fake.last_name(), random.choice(specialties), dept_id))

    # 3. Patients (300 patients)
    patients_data = []
    for _ in range(300):
        patients_data.append((fake.first_name(), fake.last_name(), fake.date_of_birth(minimum_age=1, maximum_age=90).strftime('%Y-%m-%d'),
                        random.choice(['M', 'F', 'Other']), fake.city(), fake.state_abbr()[:2]))
    cursor.executemany("INSERT INTO patients (first_name, last_name, dob, gender, city, state) VALUES (%s, %s, %s, %s, %s, %s)", patients_data)

    # 4. Admissions, Procedures, Billing, Claims (~1000 admissions)
    diagnoses = ['Heart Attack', 'Stroke', 'Fracture', 'Pneumonia', 'Cancer', 'Concussion', 'Appendicitis']
    procedure_names = ['ECG', 'MRI', 'X-Ray', 'Blood Test', 'Surgery', 'Chemotherapy', 'CT Scan']
    
    for i in range(1000):
        patient_id = random.randint(1, 300)
        provider_id = random.randint(1, 30)
        
        admit_date = fake.date_between(start_date='-2y', end_date='today')
        days_admitted = random.randint(1, 14)
        discharge_date = admit_date + timedelta(days=days_admitted)
        
        cursor.execute("INSERT INTO admissions (patient_id, provider_id, admission_date, discharge_date, primary_diagnosis) VALUES (%s, %s, %s, %s, %s)",
                       (patient_id, provider_id, admit_date.strftime('%Y-%m-%d'), discharge_date.strftime('%Y-%m-%d'), random.choice(diagnoses)))
        admission_id = cursor.lastrowid
        
        # Procedures (1 to 3 per admission)
        total_cost = 0
        for _ in range(random.randint(1, 3)):
            proc_date = admit_date + timedelta(days=random.randint(0, days_admitted))
            cost = round(random.uniform(100.0, 5000.0), 2)
            total_cost += cost
            cursor.execute("INSERT INTO procedures (admission_id, provider_id, procedure_name, procedure_date, cost) VALUES (%s, %s, %s, %s, %s)",
                           (admission_id, provider_id, random.choice(procedure_names), proc_date.strftime('%Y-%m-%d'), cost))
            
        # Billing
        bill_status = random.choice(['Paid', 'Pending', 'Overdue'])
        due_date = discharge_date + timedelta(days=30)
        cursor.execute("INSERT INTO billing_records (admission_id, total_amount, status, due_date) VALUES (%s, %s, %s, %s)",
                       (admission_id, total_cost, bill_status, due_date.strftime('%Y-%m-%d')))
        bill_id = cursor.lastrowid
        
        # Claims
        if random.random() > 0.2:
            insurance = random.choice(['BlueCross', 'Aetna', 'Cigna', 'Medicare', 'UnitedHealthcare'])
            claim_status = random.choice(['Approved', 'Denied', 'Pending'])
            covered_amount = round(total_cost * random.uniform(0.5, 1.0), 2) if claim_status == 'Approved' else 0
            cursor.execute("INSERT INTO claims (bill_id, insurance_provider, claim_status, covered_amount, claim_date) VALUES (%s, %s, %s, %s, %s)",
                           (bill_id, insurance, claim_status, covered_amount, discharge_date.strftime('%Y-%m-%d')))
        
        if i % 100 == 0:
            conn.commit()

    conn.commit()

def main():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", "tiger")
        )
        if conn.is_connected():
            cursor = conn.cursor()
            create_database_and_schema(cursor)
            generate_data(cursor, conn)
            
            cursor.execute("SELECT count(*) FROM admissions")
            print(f"Seed complete. Created {cursor.fetchone()[0]} admission records in MySQL database 'hospital_billing'.")
            
            cursor.close()
            conn.close()
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")

if __name__ == "__main__":
    main()
