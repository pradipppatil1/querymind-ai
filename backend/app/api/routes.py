from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
from app.services.classifier import QueryClassifier, QueryType
from app.services.schema_linker import SchemaLinker
from app.services.retriever import ExamplesRetriever
from app.services.generator import SQLGenerator
from app.services.validator import SQLValidator
from app.services.executor import SQLExecutor
from app.services.formatter import ResultFormatter
from app.services.cache import SemanticCache
from app.services.security import SecurityGuard
from app.services.auth_service import AuthService
from app.services.chat_service import ChatService
from app.services.email_service import EmailService

router = APIRouter()

# Instantiate services
classifier = QueryClassifier()
schema_linker = SchemaLinker()
retriever = ExamplesRetriever()
generator = SQLGenerator()
validator = SQLValidator()
executor = SQLExecutor()
formatter = ResultFormatter()
cache = SemanticCache()
security_guard = SecurityGuard()
auth_service = AuthService()
chat_service = ChatService()
email_service = EmailService()
security = HTTPBearer()

# --- Auth Dependencies ---
def get_current_user(auth: HTTPAuthorizationCredentials = Depends(security)):
    from jose import jwt, JWTError
    import os
    SECRET_KEY = os.getenv("JWT_SECRET", "secret")
    ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    try:
        payload = jwt.decode(auth.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

def get_admin_user(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user

# Simple in-memory state that syncs with MySQL for persistence
import json
from app.database.mysql_client import MySQLClient

def _load_admin_state():
    default_state = {
        "guardrails": {"allow_destructive": False, "max_limit": 100, "allowed_table_prefixes": []},
        "config": {"llm_provider": "openai", "temperature": 0.0, "sql_dialects": ["mysql"]}
    }
    try:
        db = MySQLClient()
        results, error = db.execute_query("SELECT config_key, config_value FROM system_config")
        if results:
            for row in results:
                key = row["config_key"]
                val = json.loads(row["config_value"])
                if key in default_state:
                    default_state[key] = val
    except Exception as e:
        print(f"Warning: Failed to load admin state from DB: {e}")
    return default_state

def _save_admin_state(key: str, value: dict):
    try:
        db = MySQLClient()
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO system_config (config_key, config_value) VALUES (%s, %s) ON DUPLICATE KEY UPDATE config_value = %s",
            (key, json.dumps(value), json.dumps(value))
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: Failed to save admin state to DB: {e}")

ADMIN_STATE = _load_admin_state()

class QueryRequest(BaseModel):
    query: str
    history: Optional[List[dict]] = []
    session_id: Optional[str] = None

# Rich annotated schema context for the Hospital Billing database
SCHEMA_CONTEXT = """
Table: patients
  - patient_id (INT, PK): Unique patient identifier
  - first_name (VARCHAR): Patient's first name
  - last_name (VARCHAR): Patient's last name
  - dob (DATE): Date of birth
  - gender (VARCHAR): Patient gender — values: 'M', 'F', 'Other'
  - city (VARCHAR): Patient's city of residence
  - state (VARCHAR): Patient's US state abbreviation (e.g. 'CA', 'NY', 'TX')

Table: departments
  - department_id (INT, PK): Unique department identifier
  - name (VARCHAR): Department name — values: 'Cardiology', 'Neurology', 'Orthopedics', 'Pediatrics', 'Oncology', 'Emergency'
  - floor (INT): Floor number where the department is located
  - phone (VARCHAR): Department contact phone number

Table: providers
  - provider_id (INT, PK): Unique provider (doctor/specialist) identifier
  - first_name (VARCHAR): Provider's first name
  - last_name (VARCHAR): Provider's last name
  - specialty (VARCHAR): Medical specialty — values: 'Cardiologist', 'Cardiac Surgeon', 'Neurologist', 'Neurosurgeon', 'Orthopedic Surgeon', 'Physical Therapist', 'Pediatrician', 'Oncologist', 'ER Physician', 'Trauma Surgeon'
  - department_id (INT, FK → departments.department_id): Department this provider belongs to

Table: admissions
  - admission_id (INT, PK): Unique admission identifier
  - patient_id (INT, FK → patients.patient_id): The admitted patient
  - provider_id (INT, FK → providers.provider_id): Primary attending provider
  - admission_date (DATE): Date the patient was admitted
  - discharge_date (DATE): Date the patient was discharged (may be NULL if still admitted)
  - primary_diagnosis (VARCHAR): Primary medical diagnosis — values: 'Heart Attack', 'Stroke', 'Fracture', 'Pneumonia', 'Cancer', 'Concussion', 'Appendicitis'

Table: procedures
  - procedure_id (INT, PK): Unique procedure identifier
  - admission_id (INT, FK → admissions.admission_id): The admission this procedure belongs to
  - provider_id (INT, FK → providers.provider_id): Provider who performed the procedure
  - procedure_name (VARCHAR): Type of procedure — values: 'ECG', 'MRI', 'X-Ray', 'Blood Test', 'Surgery', 'Chemotherapy', 'CT Scan'
  - procedure_date (DATE): Date the procedure was performed
  - cost (DECIMAL 10,2): Cost of this individual procedure in USD

Table: billing_records
  - bill_id (INT, PK): Unique billing record identifier
  - admission_id (INT, FK → admissions.admission_id): The admission being billed
  - total_amount (DECIMAL 10,2): Total billed amount in USD (sum of all procedure costs for the admission)
  - status (VARCHAR): Payment status — values: 'Paid', 'Pending', 'Overdue'
  - due_date (DATE): Payment due date (typically 30 days after discharge)

Table: claims
  - claim_id (INT, PK): Unique insurance claim identifier
  - bill_id (INT, FK → billing_records.bill_id): The billing record this claim is for
  - insurance_provider (VARCHAR): Insurance company — values: 'BlueCross', 'Aetna', 'Cigna', 'Medicare', 'UnitedHealthcare'
  - claim_status (VARCHAR): Status of the insurance claim — values: 'Approved', 'Denied', 'Pending'
  - covered_amount (DECIMAL 10,2): Amount covered by insurance (0 if Denied)
  - claim_date (DATE): Date the claim was submitted

Relationships:
  patients → admissions (1-to-many via patient_id)
  providers → admissions (1-to-many via provider_id)
  providers → departments (many-to-1 via department_id)
  admissions → procedures (1-to-many via admission_id)
  admissions → billing_records (1-to-1 via admission_id)
  billing_records → claims (1-to-many via bill_id)
"""

@router.post("/query")
def handle_query(request: QueryRequest, current_user: dict = Depends(get_current_user)):
    import time
    start_time = time.time()
    
    user = auth_service.get_user_by_username(current_user["sub"])
    nl_query = request.query
    history = request.history
    session_id = request.session_id

    # Create session if it doesn't exist
    if not session_id:
        title = nl_query[:50] + "..." if len(nl_query) > 50 else nl_query
        session_id = chat_service.create_session(user["id"], title)
    
    # Save user message
    chat_service.save_message(session_id, "user", nl_query)
    
    # Helper to finalize response and save to DB
    def finalize_response(response_data, is_error=False, is_unsupported=False):
        latency_ms = (time.time() - start_time) * 1000
        response_data["latency_ms"] = latency_ms
        
        # Determine the content for chat history
        content = response_data.get("summary") or response_data.get("message") or response_data.get("error")
        
        chat_service.save_message(session_id, "assistant", content, response_data)
        
        return {
            "data": response_data, 
            "error": response_data.get("error") if is_error else None,
            "clarification_needed": response_data.get("clarification_needed", False),
            "session_id": session_id
        }

    # 0. Semantic Caching
    if not history:
        cached_result = cache.get(nl_query)
        if cached_result:
            return finalize_response(cached_result["result"])

    # 1. Heuristic Security Check
    if not security_guard.check_query(nl_query):
        return finalize_response({"error": "Security alert: Potential prompt injection detected (Heuristics)."}, is_error=True)

    # 2. Intent Classification
    classification = classifier.classify(nl_query, history=history)
    
    if classification.query_type == QueryType.PROMPT_INJECTION:
        return finalize_response({"error": "Security alert: Potential prompt injection detected."}, is_error=True)
        
    if classification.query_type == QueryType.UNSUPPORTED:
        msg = f"I only have access to Hospital Billing data. {classification.reasoning}"
        return finalize_response({"summary": msg, "unsupported": True}, is_unsupported=True)
        
    # 2. Schema Linking
    resolved_schema = schema_linker.link(nl_query, classification.tables_mentioned, classification.columns_mentioned, SCHEMA_CONTEXT)
    
    # Ambiguity Check
    if resolved_schema.ambiguities and not (resolved_schema.resolved_tables and resolved_schema.resolved_columns):
        msg = f"I found some ambiguous terms: {', '.join(resolved_schema.ambiguities)}. Could you please clarify?"
        return finalize_response({"clarification_needed": True, "ambiguities": resolved_schema.ambiguities, "message": msg})
        
    # 3. Retrieve Examples
    examples = retriever.retrieve(nl_query)
    
    # 4. Generate SQL
    gen_result = generator.generate(nl_query, SCHEMA_CONTEXT, resolved_schema.model_dump(), examples, history=history)
    sql = gen_result.sql
    
    # 5. Validate SQL
    val_result = validator.validate(sql, allow_destructive=ADMIN_STATE["guardrails"]["allow_destructive"], max_limit=ADMIN_STATE["guardrails"]["max_limit"], allowed_table_prefixes=ADMIN_STATE["guardrails"]["allowed_table_prefixes"])
    if not val_result.valid:
        retry_gen = generator.generate(nl_query, SCHEMA_CONTEXT, resolved_schema.model_dump(), examples, error_message=", ".join(val_result.errors))
        sql = retry_gen.sql
        val_result = validator.validate(sql, allow_destructive=ADMIN_STATE["guardrails"]["allow_destructive"], max_limit=ADMIN_STATE["guardrails"]["max_limit"], allowed_table_prefixes=ADMIN_STATE["guardrails"]["allowed_table_prefixes"])
        if not val_result.valid:
            return finalize_response({"error": f"Invalid SQL: {', '.join(val_result.errors)}"}, is_error=True)
            
    # 6. Execute SQL
    exec_result = executor.execute(val_result.sanitized_sql)
    
    # 7. Format Result
    formatted = formatter.format(nl_query, exec_result)
    
    response = {
        "sql": val_result.sanitized_sql,
        "explanation": gen_result.explanation,
        "results": formatted.table,
        "summary": formatted.nl_summary
    }
    
    # Transpile to requested dialects
    from app.services.dialect_transpiler import transpile_all
    active_dialects = ADMIN_STATE["config"].get("sql_dialects", ["mysql"])
    # Fetch current schema for better transpilation (alias expansion, etc)
    db_schema = executor.get_schema()
    response["sql_dialect_versions"] = transpile_all(val_result.sanitized_sql, active_dialects, schema=db_schema)
        
    # Save to Cache on Success (now includes dialect versions)
    if not exec_result.error:
        cache.set(nl_query, response)
        
    return finalize_response(response)

# --- Auth API Endpoints ---
class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/auth/login")
def login(request: LoginRequest):
    user = auth_service.get_user_by_username(request.username)
    if not user or not auth_service.verify_password(request.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    auth_service.update_last_login(user["username"])
    
    user_data = {"sub": user["username"], "role": user["role"]}
    return {
        "access_token": auth_service.create_access_token(user_data),
        "refresh_token": auth_service.create_refresh_token(user_data),
        "user": {
            "username": user["username"],
            "role": user["role"],
            "last_login": user["last_login"],
            "password_reset_required": user["password_reset_required"]
        }
    }

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/auth/refresh")
def refresh(request: RefreshRequest):
    payload = auth_service.verify_refresh_token(request.refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    user_data = {"sub": payload["sub"], "role": payload["role"]}
    return {
        "access_token": auth_service.create_access_token(user_data)
    }

@router.get("/auth/me")
def get_me(current_user: dict = Depends(get_current_user)):
    user = auth_service.get_user_by_username(current_user["sub"])
    return {
        "username": user["username"],
        "role": user["role"],
        "last_login": user["last_login"],
        "password_reset_required": user["password_reset_required"]
    }

class ChangePasswordRequest(BaseModel):
    new_password: str

@router.post("/auth/change-password")
def change_password(request: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    hashed_password = auth_service.hash_password(request.new_password)
    
    conn = auth_service.db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET hashed_password = %s, password_reset_required = FALSE WHERE username = %s",
        (hashed_password, current_user["sub"])
    )
    conn.commit()
    cursor.close()
    conn.close()
    return {"status": "success"}

# --- Chat API Endpoints ---
@router.get("/chat/sessions")
def get_sessions(current_user: dict = Depends(get_current_user)):
    user = auth_service.get_user_by_username(current_user["sub"])
    sessions = chat_service.get_user_sessions(user["id"])
    return {"sessions": sessions}

@router.get("/chat/sessions/{session_id}")
def get_session_messages(session_id: str, current_user: dict = Depends(get_current_user)):
    messages = chat_service.get_session_messages(session_id)
    return {"messages": messages}

@router.delete("/chat/sessions/{session_id}")
def delete_session(session_id: str, current_user: dict = Depends(get_current_user)):
    chat_service.delete_session(session_id)
    return {"status": "success"}

# --- Admin User Management ---
class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str = "USER"

@router.post("/admin/users")
def create_user(request: CreateUserRequest, current_user: dict = Depends(get_admin_user)):
    hashed_password = auth_service.hash_password(request.password)
    
    conn = auth_service.db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, email, hashed_password, role, password_reset_required) VALUES (%s, %s, %s, %s, TRUE)",
            (request.username, request.email, hashed_password, request.role)
        )
        conn.commit()
        
        # Send email
        email_service.send_welcome_email(request.email, request.username, request.password)
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@router.get("/admin/users")
def list_users(current_user: dict = Depends(get_admin_user)):
    conn = auth_service.db.get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username, email, role, last_login, created_at FROM users")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return {"users": users}

@router.delete("/admin/users/{user_id}")
def delete_user(user_id: int, current_user: dict = Depends(get_admin_user)):
    conn = auth_service.db.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"status": "success"}

# --- Admin API Endpoints ---
@router.get("/admin/schema")
def get_schema(current_user: dict = Depends(get_admin_user)):
    return {"schema": SCHEMA_CONTEXT}

@router.get("/admin/examples")
def get_examples(limit: int = 100, current_user: dict = Depends(get_admin_user)):
    examples = retriever.get_all_examples(limit=limit)
    return {"examples": examples}

@router.post("/admin/examples")
def add_example(question: str, sql: str, current_user: dict = Depends(get_admin_user)):
    # Validation: Try executing the SQL before saving
    exec_res = executor.execute(sql)
    if exec_res.error:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400, 
            detail=f"SQL Validation Failed: {exec_res.error}"
        )
    
    retriever.add_example(question, sql)
    return {"status": "success", "message": f"Verified and added to Qdrant: {question}"}

@router.get("/admin/logs")
def get_logs(current_user: dict = Depends(get_admin_user)):
    conn = auth_service.db.get_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Fetch assistant messages which contain the SQL and execution data
    # Joined with sessions and users to get context
    query = """
        SELECT 
            m.id,
            u.username,
            m.content as answer,
            m.data,
            m.created_at,
            (SELECT content FROM chat_messages m2 
             WHERE m2.session_id = m.session_id 
             AND m2.created_at < m.created_at 
             AND m2.role = 'user' 
             ORDER BY m2.created_at DESC LIMIT 1) as nl_input
        FROM chat_messages m
        JOIN chat_sessions s ON m.session_id = s.id
        JOIN users u ON s.user_id = u.id
        WHERE m.role = 'assistant'
        ORDER BY m.created_at DESC
    """
    cursor.execute(query)
    logs = cursor.fetchall()
    
    # Parse JSON data strings into objects
    import json
    for log in logs:
        if log.get("data") and isinstance(log["data"], str):
            try:
                log["data"] = json.loads(log["data"])
            except:
                pass
    
    cursor.close()
    conn.close()
    return {"logs": logs}

@router.get("/admin/guardrails")
def get_guardrails(current_user: dict = Depends(get_admin_user)):
    return ADMIN_STATE["guardrails"]

class GuardrailUpdate(BaseModel):
    allow_destructive: bool
    max_limit: int
    allowed_table_prefixes: list[str]

@router.post("/admin/guardrails")
def update_guardrails(guardrails: dict, current_user: dict = Depends(get_admin_user)):
    ADMIN_STATE["guardrails"].update(guardrails)
    _save_admin_state("guardrails", ADMIN_STATE["guardrails"])
    return {"status": "success", "guardrails": ADMIN_STATE["guardrails"]}

@router.get("/admin/config")
def get_config(current_user: dict = Depends(get_admin_user)):
    return ADMIN_STATE["config"]

class ConfigUpdate(BaseModel):
    llm_provider: str
    temperature: float
    sql_dialects: list[str]

@router.post("/admin/config")
def update_config(config: ConfigUpdate, current_user: dict = Depends(get_admin_user)):
    ADMIN_STATE["config"]["llm_provider"] = config.llm_provider
    ADMIN_STATE["config"]["temperature"] = config.temperature
    
    # Enforce MySQL always present + max 2 additional dialects
    extras = [d for d in config.sql_dialects if d != "mysql"][:2]
    ADMIN_STATE["config"]["sql_dialects"] = ["mysql"] + extras
    
    _save_admin_state("config", ADMIN_STATE["config"])
    return {"status": "success", "config": ADMIN_STATE["config"]}

@router.get("/admin/dialects")
def get_available_dialects(current_user: dict = Depends(get_admin_user)):
    from app.services.dialect_transpiler import get_supported_dialects
    return {"dialects": get_supported_dialects()}
