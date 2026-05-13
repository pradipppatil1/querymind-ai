import os
from dotenv import load_dotenv
load_dotenv()

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from langchain_openai import OpenAIEmbeddings

# =============================================================================
# 100 Hand-Crafted Hospital Billing Examples
# Schema: patients, departments, providers, admissions, procedures,
#         billing_records, claims
# Enums:
#   gender: 'M', 'F', 'Other'
#   billing status: 'Paid', 'Pending', 'Overdue'
#   claim_status: 'Approved', 'Denied', 'Pending'
#   insurance: 'BlueCross', 'Aetna', 'Cigna', 'Medicare', 'UnitedHealthcare'
#   diagnoses: 'Heart Attack', 'Stroke', 'Fracture', 'Pneumonia',
#              'Cancer', 'Concussion', 'Appendicitis'
#   procedures: 'ECG', 'MRI', 'X-Ray', 'Blood Test', 'Surgery',
#               'Chemotherapy', 'CT Scan'
#   departments: 'Cardiology', 'Neurology', 'Orthopedics', 'Pediatrics',
#                'Oncology', 'Emergency'
# =============================================================================

HOSPITAL_EXAMPLES = [
    # ------------------------------------------------------------------ #
    # TIER 1 – SIMPLE SELECTS (25)                                         #
    # ------------------------------------------------------------------ #
    {
        "question": "How many patients are there in total?",
        "sql": "SELECT COUNT(*) AS total_patients FROM patients;"
    },
    {
        "question": "List all patients from California.",
        "sql": "SELECT * FROM patients WHERE state = 'CA';"
    },
    {
        "question": "Show all male patients.",
        "sql": "SELECT * FROM patients WHERE gender = 'M';"
    },
    {
        "question": "List all female patients.",
        "sql": "SELECT * FROM patients WHERE gender = 'F';"
    },
    {
        "question": "What are the names of all departments?",
        "sql": "SELECT name FROM departments;"
    },
    {
        "question": "List all providers who are Cardiologists.",
        "sql": "SELECT * FROM providers WHERE specialty = 'Cardiologist';"
    },
    {
        "question": "List all Pediatricians.",
        "sql": "SELECT first_name, last_name FROM providers WHERE specialty = 'Pediatrician';"
    },
    {
        "question": "Show all Oncologists.",
        "sql": "SELECT first_name, last_name FROM providers WHERE specialty = 'Oncologist';"
    },
    {
        "question": "List all billing records with Overdue status.",
        "sql": "SELECT * FROM billing_records WHERE status = 'Overdue';"
    },
    {
        "question": "Show all billing records that are Paid.",
        "sql": "SELECT * FROM billing_records WHERE status = 'Paid';"
    },
    {
        "question": "List all claims with a Denied status.",
        "sql": "SELECT * FROM claims WHERE claim_status = 'Denied';"
    },
    {
        "question": "Show all Approved insurance claims.",
        "sql": "SELECT * FROM claims WHERE claim_status = 'Approved';"
    },
    {
        "question": "List all admissions with a diagnosis of Heart Attack.",
        "sql": "SELECT * FROM admissions WHERE primary_diagnosis = 'Heart Attack';"
    },
    {
        "question": "Show all admissions where the diagnosis was Stroke.",
        "sql": "SELECT * FROM admissions WHERE primary_diagnosis = 'Stroke';"
    },
    {
        "question": "List all procedures named MRI.",
        "sql": "SELECT * FROM procedures WHERE procedure_name = 'MRI';"
    },
    {
        "question": "Show all Surgery procedures.",
        "sql": "SELECT * FROM procedures WHERE procedure_name = 'Surgery';"
    },
    {
        "question": "List all Chemotherapy procedures.",
        "sql": "SELECT * FROM procedures WHERE procedure_name = 'Chemotherapy';"
    },
    {
        "question": "Show all claims from BlueCross.",
        "sql": "SELECT * FROM claims WHERE insurance_provider = 'BlueCross';"
    },
    {
        "question": "List all claims filed by Aetna.",
        "sql": "SELECT * FROM claims WHERE insurance_provider = 'Aetna';"
    },
    {
        "question": "Show all Medicare claims.",
        "sql": "SELECT * FROM claims WHERE insurance_provider = 'Medicare';"
    },
    {
        "question": "List patients from New York state.",
        "sql": "SELECT first_name, last_name FROM patients WHERE state = 'NY';"
    },
    {
        "question": "List patients from Texas.",
        "sql": "SELECT first_name, last_name FROM patients WHERE state = 'TX';"
    },
    {
        "question": "Show the phone number of the Oncology department.",
        "sql": "SELECT phone FROM departments WHERE name = 'Oncology';"
    },
    {
        "question": "What floor is the Emergency department on?",
        "sql": "SELECT floor FROM departments WHERE name = 'Emergency';"
    },
    {
        "question": "List all pending billing records.",
        "sql": "SELECT * FROM billing_records WHERE status = 'Pending';"
    },

    # ------------------------------------------------------------------ #
    # TIER 2 – AGGREGATES (25)                                             #
    # ------------------------------------------------------------------ #
    {
        "question": "What is the total cost of all procedures?",
        "sql": "SELECT SUM(cost) AS total_cost FROM procedures;"
    },
    {
        "question": "What is the average cost of a procedure?",
        "sql": "SELECT AVG(cost) AS avg_cost FROM procedures;"
    },
    {
        "question": "What is the maximum amount billed?",
        "sql": "SELECT MAX(total_amount) AS max_billed FROM billing_records;"
    },
    {
        "question": "What is the minimum amount billed?",
        "sql": "SELECT MIN(total_amount) AS min_billed FROM billing_records;"
    },
    {
        "question": "How many admissions were there in total?",
        "sql": "SELECT COUNT(*) AS total_admissions FROM admissions;"
    },
    {
        "question": "How many admissions had a Stroke diagnosis?",
        "sql": "SELECT COUNT(*) FROM admissions WHERE primary_diagnosis = 'Stroke';"
    },
    {
        "question": "How many admissions had a Cancer diagnosis?",
        "sql": "SELECT COUNT(*) FROM admissions WHERE primary_diagnosis = 'Cancer';"
    },
    {
        "question": "How many procedures were performed in total?",
        "sql": "SELECT COUNT(*) AS total_procedures FROM procedures;"
    },
    {
        "question": "What is the total covered amount by Aetna?",
        "sql": "SELECT SUM(covered_amount) AS total_covered FROM claims WHERE insurance_provider = 'Aetna';"
    },
    {
        "question": "What is the average covered amount for Approved claims?",
        "sql": "SELECT AVG(covered_amount) FROM claims WHERE claim_status = 'Approved';"
    },
    {
        "question": "What is the total amount billed for Overdue records?",
        "sql": "SELECT SUM(total_amount) FROM billing_records WHERE status = 'Overdue';"
    },
    {
        "question": "How many claims have been Denied?",
        "sql": "SELECT COUNT(*) FROM claims WHERE claim_status = 'Denied';"
    },
    {
        "question": "Count the number of providers per specialty.",
        "sql": "SELECT specialty, COUNT(*) AS provider_count FROM providers GROUP BY specialty ORDER BY provider_count DESC;"
    },
    {
        "question": "Count the number of admissions per diagnosis.",
        "sql": "SELECT primary_diagnosis, COUNT(*) AS count FROM admissions GROUP BY primary_diagnosis ORDER BY count DESC;"
    },
    {
        "question": "What is the average cost of an MRI procedure?",
        "sql": "SELECT AVG(cost) FROM procedures WHERE procedure_name = 'MRI';"
    },
    {
        "question": "What is the total cost of all Surgery procedures?",
        "sql": "SELECT SUM(cost) FROM procedures WHERE procedure_name = 'Surgery';"
    },
    {
        "question": "How many billing records are Overdue?",
        "sql": "SELECT COUNT(*) FROM billing_records WHERE status = 'Overdue';"
    },
    {
        "question": "What is the total revenue from Paid billing records?",
        "sql": "SELECT SUM(total_amount) FROM billing_records WHERE status = 'Paid';"
    },
    {
        "question": "How many patients are from each state?",
        "sql": "SELECT state, COUNT(*) AS patient_count FROM patients GROUP BY state ORDER BY patient_count DESC;"
    },
    {
        "question": "How many unique insurance providers are there?",
        "sql": "SELECT COUNT(DISTINCT insurance_provider) FROM claims;"
    },
    {
        "question": "What is the total covered amount by Medicare?",
        "sql": "SELECT SUM(covered_amount) FROM claims WHERE insurance_provider = 'Medicare';"
    },
    {
        "question": "What is the average total_amount for all billing records?",
        "sql": "SELECT AVG(total_amount) AS avg_bill FROM billing_records;"
    },
    {
        "question": "How many male patients are there?",
        "sql": "SELECT COUNT(*) FROM patients WHERE gender = 'M';"
    },
    {
        "question": "How many female patients are there?",
        "sql": "SELECT COUNT(*) FROM patients WHERE gender = 'F';"
    },
    {
        "question": "What is the maximum covered amount in any single claim?",
        "sql": "SELECT MAX(covered_amount) FROM claims;"
    },

    # ------------------------------------------------------------------ #
    # TIER 3 – JOINS (25)                                                  #
    # ------------------------------------------------------------------ #
    {
        "question": "What are the names of patients admitted with a Heart Attack?",
        "sql": "SELECT p.first_name, p.last_name FROM patients p JOIN admissions a ON p.patient_id = a.patient_id WHERE a.primary_diagnosis = 'Heart Attack';"
    },
    {
        "question": "List patients admitted with Pneumonia.",
        "sql": "SELECT p.first_name, p.last_name FROM patients p JOIN admissions a ON p.patient_id = a.patient_id WHERE a.primary_diagnosis = 'Pneumonia';"
    },
    {
        "question": "Which providers work in the Cardiology department?",
        "sql": "SELECT pr.first_name, pr.last_name, pr.specialty FROM providers pr JOIN departments d ON pr.department_id = d.department_id WHERE d.name = 'Cardiology';"
    },
    {
        "question": "Which providers work in the Oncology department?",
        "sql": "SELECT pr.first_name, pr.last_name FROM providers pr JOIN departments d ON pr.department_id = d.department_id WHERE d.name = 'Oncology';"
    },
    {
        "question": "What is the total billing amount for patients from California?",
        "sql": "SELECT SUM(b.total_amount) FROM billing_records b JOIN admissions a ON b.admission_id = a.admission_id JOIN patients p ON a.patient_id = p.patient_id WHERE p.state = 'CA';"
    },
    {
        "question": "List all patients who have pending bills.",
        "sql": "SELECT DISTINCT p.first_name, p.last_name FROM patients p JOIN admissions a ON p.patient_id = a.patient_id JOIN billing_records b ON a.admission_id = b.admission_id WHERE b.status = 'Pending';"
    },
    {
        "question": "List all patients who have overdue bills.",
        "sql": "SELECT DISTINCT p.first_name, p.last_name FROM patients p JOIN admissions a ON p.patient_id = a.patient_id JOIN billing_records b ON a.admission_id = b.admission_id WHERE b.status = 'Overdue';"
    },
    {
        "question": "What is the billing status for admissions diagnosed with Cancer?",
        "sql": "SELECT b.status, COUNT(*) FROM billing_records b JOIN admissions a ON b.admission_id = a.admission_id WHERE a.primary_diagnosis = 'Cancer' GROUP BY b.status;"
    },
    {
        "question": "Show the insurance provider and covered amount for each claim linked to an overdue bill.",
        "sql": "SELECT c.insurance_provider, c.covered_amount FROM claims c JOIN billing_records b ON c.bill_id = b.bill_id WHERE b.status = 'Overdue';"
    },
    {
        "question": "List all BlueCross claims for Heart Attack admissions.",
        "sql": "SELECT c.claim_id, c.claim_status, c.covered_amount FROM claims c JOIN billing_records b ON c.bill_id = b.bill_id JOIN admissions a ON b.admission_id = a.admission_id WHERE a.primary_diagnosis = 'Heart Attack' AND c.insurance_provider = 'BlueCross';"
    },
    {
        "question": "What is the total cost of procedures performed by providers in the Emergency department?",
        "sql": "SELECT SUM(pr.cost) FROM procedures pr JOIN providers p ON pr.provider_id = p.provider_id JOIN departments d ON p.department_id = d.department_id WHERE d.name = 'Emergency';"
    },
    {
        "question": "Which department generated the most procedure revenue?",
        "sql": "SELECT d.name, SUM(pr.cost) AS revenue FROM departments d JOIN providers p ON d.department_id = p.department_id JOIN procedures pr ON p.provider_id = pr.provider_id GROUP BY d.name ORDER BY revenue DESC LIMIT 1;"
    },
    {
        "question": "How many admissions did each provider handle?",
        "sql": "SELECT p.first_name, p.last_name, COUNT(a.admission_id) AS admission_count FROM providers p JOIN admissions a ON p.provider_id = a.provider_id GROUP BY p.provider_id ORDER BY admission_count DESC;"
    },
    {
        "question": "Which provider performed the most procedures?",
        "sql": "SELECT p.first_name, p.last_name, COUNT(pr.procedure_id) AS procedure_count FROM providers p JOIN procedures pr ON p.provider_id = pr.provider_id GROUP BY p.provider_id ORDER BY procedure_count DESC LIMIT 1;"
    },
    {
        "question": "What are the total billing amounts per department?",
        "sql": "SELECT d.name, SUM(b.total_amount) AS total_billed FROM departments d JOIN providers p ON d.department_id = p.department_id JOIN admissions a ON p.provider_id = a.provider_id JOIN billing_records b ON a.admission_id = b.admission_id GROUP BY d.name;"
    },
    {
        "question": "List patients and their billing status.",
        "sql": "SELECT p.first_name, p.last_name, b.status FROM patients p JOIN admissions a ON p.patient_id = a.patient_id JOIN billing_records b ON a.admission_id = b.admission_id;"
    },
    {
        "question": "Show distinct insurance providers used for Stroke admissions.",
        "sql": "SELECT DISTINCT c.insurance_provider FROM claims c JOIN billing_records b ON c.bill_id = b.bill_id JOIN admissions a ON b.admission_id = a.admission_id WHERE a.primary_diagnosis = 'Stroke';"
    },
    {
        "question": "How many unique procedures were performed for patients from New York?",
        "sql": "SELECT COUNT(DISTINCT pr.procedure_name) FROM procedures pr JOIN admissions a ON pr.admission_id = a.admission_id JOIN patients p ON a.patient_id = p.patient_id WHERE p.state = 'NY';"
    },
    {
        "question": "What is the total amount covered by UnitedHealthcare for Cancer patients?",
        "sql": "SELECT SUM(c.covered_amount) FROM claims c JOIN billing_records b ON c.bill_id = b.bill_id JOIN admissions a ON b.admission_id = a.admission_id WHERE a.primary_diagnosis = 'Cancer' AND c.insurance_provider = 'UnitedHealthcare';"
    },
    {
        "question": "List providers and the total cost of procedures they performed.",
        "sql": "SELECT p.first_name, p.last_name, SUM(pr.cost) AS total_cost FROM providers p JOIN procedures pr ON p.provider_id = pr.provider_id GROUP BY p.provider_id ORDER BY total_cost DESC;"
    },
    {
        "question": "Which patients had an MRI performed?",
        "sql": "SELECT DISTINCT p.first_name, p.last_name FROM patients p JOIN admissions a ON p.patient_id = a.patient_id JOIN procedures pr ON a.admission_id = pr.admission_id WHERE pr.procedure_name = 'MRI';"
    },
    {
        "question": "List claims and the patient name for each claim.",
        "sql": "SELECT p.first_name, p.last_name, c.claim_id, c.insurance_provider, c.claim_status FROM claims c JOIN billing_records b ON c.bill_id = b.bill_id JOIN admissions a ON b.admission_id = a.admission_id JOIN patients p ON a.patient_id = p.patient_id;"
    },
    {
        "question": "What is the average claim coverage per insurance provider?",
        "sql": "SELECT insurance_provider, AVG(covered_amount) AS avg_coverage FROM claims GROUP BY insurance_provider ORDER BY avg_coverage DESC;"
    },
    {
        "question": "Which diagnoses have the highest average billing amount?",
        "sql": "SELECT a.primary_diagnosis, AVG(b.total_amount) AS avg_bill FROM admissions a JOIN billing_records b ON a.admission_id = b.admission_id GROUP BY a.primary_diagnosis ORDER BY avg_bill DESC;"
    },
    {
        "question": "How many Denied claims are there per insurance provider?",
        "sql": "SELECT insurance_provider, COUNT(*) AS denied_count FROM claims WHERE claim_status = 'Denied' GROUP BY insurance_provider ORDER BY denied_count DESC;"
    },

    # ------------------------------------------------------------------ #
    # TIER 4 – TEMPORAL & COMPLEX (25)                                     #
    # ------------------------------------------------------------------ #
    {
        "question": "How many admissions occurred in 2024?",
        "sql": "SELECT COUNT(*) FROM admissions WHERE admission_date >= '2024-01-01' AND admission_date <= '2024-12-31';"
    },
    {
        "question": "How many admissions occurred in 2023?",
        "sql": "SELECT COUNT(*) FROM admissions WHERE admission_date >= '2023-01-01' AND admission_date <= '2023-12-31';"
    },
    {
        "question": "List all procedures performed after 2024-01-01.",
        "sql": "SELECT * FROM procedures WHERE procedure_date > '2024-01-01';"
    },
    {
        "question": "Show all claims filed before 2023-06-01.",
        "sql": "SELECT * FROM claims WHERE claim_date < '2023-06-01';"
    },
    {
        "question": "Find bills that are overdue as of today.",
        "sql": "SELECT * FROM billing_records WHERE status = 'Overdue' AND due_date <= CURRENT_DATE;"
    },
    {
        "question": "Which patient had the longest hospital stay?",
        "sql": "SELECT p.first_name, p.last_name, DATEDIFF(a.discharge_date, a.admission_date) AS stay_days FROM patients p JOIN admissions a ON p.patient_id = a.patient_id ORDER BY stay_days DESC LIMIT 1;"
    },
    {
        "question": "What is the average hospital stay duration in days?",
        "sql": "SELECT AVG(DATEDIFF(discharge_date, admission_date)) AS avg_stay_days FROM admissions WHERE discharge_date IS NOT NULL;"
    },
    {
        "question": "List admissions that lasted more than 7 days.",
        "sql": "SELECT * FROM admissions WHERE DATEDIFF(discharge_date, admission_date) > 7;"
    },
    {
        "question": "What is the total procedure cost in 2023?",
        "sql": "SELECT SUM(cost) FROM procedures WHERE procedure_date >= '2023-01-01' AND procedure_date <= '2023-12-31';"
    },
    {
        "question": "How many claims were filed in 2024?",
        "sql": "SELECT COUNT(*) FROM claims WHERE claim_date >= '2024-01-01' AND claim_date <= '2024-12-31';"
    },
    {
        "question": "What is the total Surgery cost in 2023?",
        "sql": "SELECT SUM(cost) FROM procedures WHERE procedure_name = 'Surgery' AND procedure_date >= '2023-01-01' AND procedure_date <= '2023-12-31';"
    },
    {
        "question": "Which department has the highest number of admissions?",
        "sql": "SELECT d.name, COUNT(a.admission_id) AS admission_count FROM departments d JOIN providers p ON d.department_id = p.department_id JOIN admissions a ON p.provider_id = a.provider_id GROUP BY d.name ORDER BY admission_count DESC LIMIT 1;"
    },
    {
        "question": "What percentage of claims are Denied?",
        "sql": "SELECT (COUNT(CASE WHEN claim_status = 'Denied' THEN 1 END) * 100.0 / COUNT(*)) AS denial_rate FROM claims;"
    },
    {
        "question": "Show the top 5 most expensive billing records.",
        "sql": "SELECT * FROM billing_records ORDER BY total_amount DESC LIMIT 5;"
    },
    {
        "question": "Show the top 5 most expensive procedures.",
        "sql": "SELECT procedure_name, cost FROM procedures ORDER BY cost DESC LIMIT 5;"
    },
    {
        "question": "List the 10 most recent admissions.",
        "sql": "SELECT * FROM admissions ORDER BY admission_date DESC LIMIT 10;"
    },
    {
        "question": "What is the net uncovered amount (total billed minus covered) per insurance provider?",
        "sql": "SELECT c.insurance_provider, SUM(b.total_amount - c.covered_amount) AS net_uncovered FROM claims c JOIN billing_records b ON c.bill_id = b.bill_id GROUP BY c.insurance_provider ORDER BY net_uncovered DESC;"
    },
    {
        "question": "List all patients admitted and discharged within the same month in 2024.",
        "sql": "SELECT p.first_name, p.last_name FROM patients p JOIN admissions a ON p.patient_id = a.patient_id WHERE YEAR(a.admission_date) = 2024 AND MONTH(a.admission_date) = MONTH(a.discharge_date);"
    },
    {
        "question": "Which month in 2023 had the most admissions?",
        "sql": "SELECT MONTH(admission_date) AS month, COUNT(*) AS count FROM admissions WHERE admission_date >= '2023-01-01' AND admission_date <= '2023-12-31' GROUP BY MONTH(admission_date) ORDER BY count DESC LIMIT 1;"
    },
    {
        "question": "What is the total amount billed per month in 2023?",
        "sql": "SELECT MONTH(b.due_date) AS month, SUM(b.total_amount) AS total FROM billing_records b WHERE b.due_date >= '2023-01-01' AND b.due_date <= '2023-12-31' GROUP BY MONTH(b.due_date) ORDER BY month;"
    },
    {
        "question": "Find patients who have been admitted more than once.",
        "sql": "SELECT p.first_name, p.last_name, COUNT(a.admission_id) AS admission_count FROM patients p JOIN admissions a ON p.patient_id = a.patient_id GROUP BY p.patient_id HAVING admission_count > 1 ORDER BY admission_count DESC;"
    },
    {
        "question": "What is the ratio of covered to billed amount for each insurance provider?",
        "sql": "SELECT c.insurance_provider, SUM(c.covered_amount) / SUM(b.total_amount) AS coverage_ratio FROM claims c JOIN billing_records b ON c.bill_id = b.bill_id GROUP BY c.insurance_provider ORDER BY coverage_ratio DESC;"
    },
    {
        "question": "Which diagnosis results in the longest average hospital stay?",
        "sql": "SELECT primary_diagnosis, AVG(DATEDIFF(discharge_date, admission_date)) AS avg_days FROM admissions GROUP BY primary_diagnosis ORDER BY avg_days DESC LIMIT 1;"
    },
    {
        "question": "List patients whose total billed amount exceeds 5000.",
        "sql": "SELECT p.first_name, p.last_name, SUM(b.total_amount) AS total_billed FROM patients p JOIN admissions a ON p.patient_id = a.patient_id JOIN billing_records b ON a.admission_id = b.admission_id GROUP BY p.patient_id HAVING total_billed > 5000 ORDER BY total_billed DESC;"
    },
    {
        "question": "What is the total procedure revenue for each year?",
        "sql": "SELECT YEAR(procedure_date) AS year, SUM(cost) AS total_revenue FROM procedures GROUP BY YEAR(procedure_date) ORDER BY year;"
    },
]


def seed():
    print(f"Seeding {len(HOSPITAL_EXAMPLES)} hand-crafted hospital billing examples into Qdrant...")

    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    client = QdrantClient(host=host, port=port)
    collection_name = "few_shot_examples"

    # Recreate collection
    if client.collection_exists(collection_name=collection_name):
        client.delete_collection(collection_name=collection_name)
        print(f"Deleted existing '{collection_name}' collection.")

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
    )
    print(f"Created fresh '{collection_name}' collection.")

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    print("Embedding questions and upserting points...")
    points = []
    for i, ex in enumerate(HOSPITAL_EXAMPLES):
        vector = embeddings.embed_query(ex["question"])
        points.append(
            PointStruct(
                id=i,
                vector=vector,
                payload={"question": ex["question"], "sql": ex["sql"]}
            )
        )
        if (i + 1) % 10 == 0:
            print(f"  Embedded {i + 1}/{len(HOSPITAL_EXAMPLES)}...")

    client.upsert(collection_name=collection_name, points=points)
    print(f"\nSuccessfully seeded {len(points)} hospital billing examples into '{collection_name}'!")


if __name__ == "__main__":
    seed()
