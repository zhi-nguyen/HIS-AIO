/**
 * Type definitions for HIS Frontend
 * Phù hợp với backend Django/DRF
 */

// ============================================================================
// AUTH TYPES
// ============================================================================

export interface LoginCredentials {
    email: string;  // Backend sử dụng email làm USERNAME_FIELD
    password: string;
}

export interface TokenResponse {
    access: string;
    refresh: string;
}

export interface JWTPayload {
    user_id: string;  // UUID từ backend
    email?: string;
    exp: number;
    iat: number;
    jti?: string;
    token_type?: string;
}

// ============================================================================
// STAFF & USER TYPES
// ============================================================================

export type StaffRole =
    | 'ADMIN'
    | 'DOCTOR'
    | 'NURSE'
    | 'RECEPTIONIST'
    | 'LAB_TECHNICIAN'
    | 'PHARMACIST'
    | 'AI_AGENT';

export interface Staff {
    id: string;
    user_id: string;
    role: StaffRole;
    department: string;
    department_link?: string;
    hire_date: string;
}

// ============================================================================
// PATIENT TYPES
// ============================================================================

export type Gender = 'M' | 'F' | 'O';

export interface Patient {
    id: string;
    patient_code: string;
    first_name: string;
    last_name: string;
    full_name?: string;  // computed property from backend
    full_address?: string;  // computed property from backend
    date_of_birth?: string;
    gender: Gender;
    contact_number?: string;
    id_card?: string;
    insurance_number?: string;
    address_detail?: string;
    province?: string;
    ward?: string;
    is_anonymous?: boolean;
    is_merged?: boolean;
    created_at?: string;
    updated_at?: string;
}

export interface PatientCreateInput {
    first_name: string;
    last_name: string;
    date_of_birth?: string;
    gender: Gender;
    contact_number?: string;
    id_card?: string;
    insurance_number?: string;
    address_detail?: string;
}

// ============================================================================
// VISIT / RECEPTION TYPES
// ============================================================================

// ============================================================================
// DEPARTMENT TYPES
// ============================================================================

export interface Department {
    id: string;
    code: string;
    name: string;
    is_active: boolean;
}

// ============================================================================
// VISIT/RECEPTION TYPES
// ============================================================================

// Backend Visit status from reception/models.py
export type VisitStatus = 'CHECK_IN' | 'TRIAGE' | 'WAITING' | 'IN_PROGRESS' | 'PENDING_RESULTS' | 'COMPLETED' | 'CANCELLED';
export type VisitPriority = 'NORMAL' | 'ONLINE_BOOKING' | 'PRIORITY' | 'EMERGENCY';

export interface Visit {
    id: string;
    visit_code: string;
    patient: Patient | string;  // Can be nested or just ID
    patient_detail?: Patient;
    status: VisitStatus;
    priority: VisitPriority;
    queue_number: number;
    check_in_time?: string;
    check_out_time?: string;
    assigned_staff?: string;
    // Triage fields
    chief_complaint?: string;
    vital_signs?: VitalSigns;
    triage_code?: string;
    triage_ai_response?: string;
    triage_confidence?: number;
    triage_key_factors?: string[];
    triage_matched_departments?: Array<{ code: string; name: string; score: string; specialties: string }>;
    recommended_department?: string;
    recommended_department_detail?: Department;
    confirmed_department?: string;
    confirmed_department_detail?: Department;
    triage_confirmed_at?: string;
    triage_method?: 'AI' | 'MANUAL';
    // Display helpers
    status_display?: string;
    priority_display?: string;
    created_at?: string;
    updated_at?: string;
}

export interface VisitCreateInput {
    patient: string;  // patient ID
    priority?: VisitPriority;
}

// ============================================================================
// QMS TYPES
// ============================================================================

export type QueueStatus = 'WAITING' | 'CALLED' | 'IN_PROGRESS' | 'COMPLETED' | 'SKIPPED' | 'NO_SHOW';
export type StationType = 'TRIAGE' | 'DOCTOR' | 'LAB' | 'IMAGING' | 'PHARMACY' | 'CASHIER';
export type QueueSourceType = 'WALK_IN' | 'ONLINE_BOOKING' | 'EMERGENCY';

export interface QueueNumber {
    id: string;
    number_code: string;  // VD: PK01-2026013101-005
    daily_sequence: number;
    visit: Visit | string;
    station: ServiceStation | string;
    status: QueueStatus;
    priority: number;
    created_date: string;
    created_time: string;
    called_at?: string;
}

export interface ServiceStation {
    id: string;
    code: string;
    name: string;
    station_type: StationType;
    is_active: boolean;
    room_location?: string;
    current_queue?: QueueNumber;
}

// --- Clinical Queue (3-Stream) Types ---

/** Bệnh nhân được gọi — response từ call_next_patient */
export interface CalledPatient {
    entry_id: string;
    visit_id: string;
    queue_number: string;
    daily_sequence: number;
    patient_name: string;
    source_type: QueueSourceType;
    priority: number;
    display_label: string;
    station_code: string;
    station_name: string;
    wait_time_minutes: number | null;
    audio_url: string | null;
}

/** Entry trong danh sách chờ */
export interface QueueBoardEntry {
    position: number;
    entry_id: string;
    queue_number: string;
    daily_sequence: number;
    patient_name: string;
    source_type: QueueSourceType;
    priority: number;
    wait_time_minutes: number | null;
}

/** Entry đã hoàn thành */
export interface QueueCompletedEntry {
    entry_id: string;
    queue_number: string;
    daily_sequence: number;
    patient_name: string;
    source_type: QueueSourceType;
    status: QueueStatus;
    end_time: string | null;
}

/** Response từ queue/board/ endpoint */
export interface QueueBoardData {
    station: { code: string; name: string };
    currently_serving: CalledPatient[];
    waiting_list: QueueBoardEntry[];
    completed_list: QueueCompletedEntry[];
    no_show_list: NoShowEntry[];
    total_waiting: number;
    estimated_wait_minutes: number;
}

/** Entry vắng mặt (có thể gọi lại) */
export interface NoShowEntry {
    entry_id: string;
    visit_id: string;
    queue_number: string;
    daily_sequence: number;
    patient_name: string;
    source_type: QueueSourceType;
    status: string;
    end_time: string | null;
}

/** Booking check-in lateness info */
export interface LatenessInfo {
    minutes: number;
    category: 'ON_TIME' | 'LATE' | 'EXPIRED';
}

/** Response từ kiosk/checkin/ */
export interface KioskCheckinResponse {
    success: boolean;
    message: string;
    queue_number: string;
    daily_sequence: number;
    priority: number;
    source: QueueSourceType;
    lateness_info: LatenessInfo;
    station: { code: string; name: string };
}

/** Response từ walkin/checkin/ */
export interface WalkinCheckinResponse {
    success: boolean;
    message: string;
    queue_number: string;
    daily_sequence: number;
    priority: number;
    source: QueueSourceType;
    station: { code: string; name: string };
}

/** Response từ doctor/call-next/ */
export interface CallNextResponse {
    success: boolean;
    message: string;
    called_patient: CalledPatient | null;
}

// ============================================================================
// EMR / CLINICAL TYPES
// ============================================================================

export interface VitalSigns {
    temperature?: number;
    systolic_bp?: number;
    diastolic_bp?: number;
    heart_rate?: number;
    respiratory_rate?: number;
    spo2?: number;
    weight?: number;
    height?: number;
}

export interface ClinicalRecord {
    id: string;
    visit: string | Visit;
    doctor?: string;
    doctor_name?: string;
    chief_complaint: string;
    history_of_present_illness?: string;
    physical_exam?: string;
    vital_signs?: VitalSigns;
    medical_summary?: string;
    final_diagnosis?: string;
    main_icd?: string;
    main_icd_code?: string;
    main_icd_name?: string;
    treatment_plan?: string;
    triage_agent_summary?: Record<string, unknown>;
    clinical_agent_summary?: Record<string, unknown>;
    core_agent_summary?: Record<string, unknown>;
    ai_suggestion_json?: Record<string, unknown>;
    is_finalized: boolean;
    created_at?: string;
    updated_at?: string;
}

export interface ICD10Code {
    id: string;
    code: string;
    name: string;
    description?: string;
}

export interface AISuggestion {
    differential_diagnosis?: string[];
    recommended_tests?: string[];
    treatment_suggestions?: string[];
    warnings?: string[];
    reasoning?: string;
}

// ============================================================================
// LIS TYPES
// ============================================================================

export interface LabTest {
    id: string;
    test_code: string;
    test_name: string;
    category: string;
    unit: string;
    reference_min?: number;
    reference_max?: number;
    price: number;
}

export type LabOrderStatus = 'PENDING' | 'SAMPLE_COLLECTED' | 'IN_PROGRESS' | 'COMPLETED' | 'VERIFIED';
export type ResultFlag = 'NORMAL' | 'LOW' | 'HIGH' | 'CRITICAL';

export interface LabOrderItem {
    id: string;
    lab_test: LabTest;
    result_value?: string;
    result_flag?: ResultFlag;
    notes?: string;
}

export interface LabOrder {
    id: string;
    order_code: string;
    visit: Visit;
    tests: LabOrderItem[];
    status: LabOrderStatus;
    ordered_by: string;
    created_at: string;
}

// ============================================================================
// RIS TYPES
// ============================================================================

export type Modality = 'XRAY' | 'CT' | 'MRI' | 'US' | 'OTHER';
export type ImagingOrderStatus = 'PENDING' | 'SCHEDULED' | 'IN_PROGRESS' | 'COMPLETED' | 'REPORTED';

export interface ImagingProcedure {
    id: string;
    procedure_code: string;
    procedure_name: string;
    modality: Modality;
    price: number;
}

export interface ImagingOrder {
    id: string;
    order_code: string;
    visit: Visit;
    procedure: ImagingProcedure;
    clinical_indication?: string;
    status: ImagingOrderStatus;
    report?: string;
    findings?: string;
    ordered_by: string;
    created_at: string;
}

// ============================================================================
// PHARMACY TYPES
// ============================================================================

export interface Medication {
    id: string;
    drug_code: string;
    drug_name: string;
    generic_name?: string;
    dosage_form: string;
    strength: string;
    unit: string;
    price: number;
}

export type PrescriptionStatus = 'PENDING' | 'DISPENSED' | 'PARTIALLY_DISPENSED' | 'CANCELLED';

export interface PrescriptionItem {
    id: string;
    medication: Medication;
    quantity: number;
    dosage: string;
    frequency: string;
    duration: string;
    instructions?: string;
}

export interface Prescription {
    id: string;
    prescription_code: string;
    visit: Visit;
    items: PrescriptionItem[];
    status: PrescriptionStatus;
    prescribed_by: string;
    created_at: string;
}

// ============================================================================
// AI TYPES
// ============================================================================

export type TriageLevel = 'RED' | 'ORANGE' | 'YELLOW' | 'GREEN' | 'BLUE';
export type InteractionSeverity = 'MINOR' | 'MODERATE' | 'MAJOR' | 'CONTRAINDICATED';

export interface TriageAssessmentInput {
    patient_id: string;
    patient_name: string;
    age: number;
    gender: string;
    chief_complaint: string;
    symptoms: string[];
    vital_signs: VitalSigns;
    medical_history?: string;
}

export interface TriageAssessmentResult {
    triage_level: TriageLevel;
    priority_score: number;
    recommended_department: string;
    ai_reasoning: string;
    vital_signs_assessment: {
        alerts: string[];
        recommendations: string[];
    };
}

export interface DrugInteractionInput {
    patient_id: string;
    medications: Array<{
        drug_name: string;
        dosage: string;
        frequency: string;
    }>;
}

export interface DrugInteraction {
    drug_pair: [string, string];
    severity: InteractionSeverity;
    description: string;
    recommendation: string;
}

export interface DrugInteractionResult {
    interactions: DrugInteraction[];
    safe_combinations: string[];
    ai_analysis: string;
}

// ============================================================================
// KIOSK SELF-SERVICE TYPES
// ============================================================================

/** Response từ POST /api/kiosk/identify/ */
export interface KioskSelfServiceIdentifyResponse {
    success: boolean;
    patient: {
        id: string;
        patient_code: string;
        full_name: string;
        date_of_birth: string | null;
        gender: string;
        is_new_patient: boolean;
    };
    insurance_info: {
        insurance_code: string;
        patient_name: string;
        dob: string;
        gender: string;
        benefit_rate: number;
        registered_hospital_name: string;
        registered_hospital_code: string;
        valid_from: string;
        valid_to: string;
    } | null;
    has_active_visit: boolean;
    active_visit_code: string | null;
}

/** Response từ POST /api/kiosk/register/ */
export interface KioskSelfServiceRegisterResponse {
    success: boolean;
    visit_code: string;
    queue_number: string;
    daily_sequence: number;
    estimated_wait_minutes: number;
    message: string;
}

/** Error response từ kiosk API */
export interface KioskErrorResponse {
    error: string;
    code: 'VALIDATION_ERROR' | 'INVALID_SCAN_DATA' | 'PATIENT_NOT_FOUND' | 'ACTIVE_VISIT_EXISTS' | 'SERVER_ERROR';
    active_visit_code?: string;
}

// ============================================================================
// API RESPONSE TYPES
// ============================================================================

export interface PaginatedResponse<T> {
    count: number;
    next: string | null;
    previous: string | null;
    results: T[];
}

export interface ApiError {
    detail?: string;
    message?: string;
    errors?: Record<string, string[]>;
}

