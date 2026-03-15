import api from './api';
import type {
    Patient,
    Visit,
    Department,
    QueueNumber,
    ServiceStation,
    PaginatedResponse,
    QueueBoardData,
    CallNextResponse,
    KioskCheckinResponse,
    WalkinCheckinResponse,
} from '@/types';

/**
 * Patient API Services
 * CRUD operations cho bệnh nhân
 */
export const patientApi = {
    // Lấy danh sách bệnh nhân (có phân trang)
    getAll: async (params?: {
        page?: number;
        search?: string;
    }): Promise<PaginatedResponse<Patient>> => {
        const response = await api.get('/patients/', { params });
        return response.data;
    },

    // Lấy chi tiết một bệnh nhân
    getById: async (id: string): Promise<Patient> => {
        const response = await api.get(`/patients/${id}/`);
        return response.data;
    },

    // Tạo bệnh nhân mới
    create: async (data: Partial<Patient>): Promise<Patient> => {
        const response = await api.post('/patients/', data);
        return response.data;
    },

    // Cập nhật bệnh nhân
    update: async (id: string, data: Partial<Patient>): Promise<Patient> => {
        const response = await api.patch(`/patients/${id}/`, data);
        return response.data;
    },

    // Xóa bệnh nhân
    delete: async (id: string): Promise<void> => {
        await api.delete(`/patients/${id}/`);
    },

    // Tìm kiếm bệnh nhân
    search: async (query: string): Promise<Patient[]> => {
        const response = await api.get('/patients/', {
            params: { search: query },
        });
        return response.data.results || response.data;
    },
};

/**
 * Insurance Mock API (Cổng Chính phủ giả lập)
 * Tra cứu thông tin công dân qua CCCD / mã BHYT
 */
export interface InsuranceLookupResult {
    status: 'success' | 'expired' | 'not_found';
    data: {
        patient_name: string;
        insurance_code: string;
        dob: string;
        gender: 'male' | 'female';
        address: string;
        card_issue_date: string;
        card_expire_date: string;
        benefit_rate: number;
        benefit_code: string;
        registered_hospital_code: string;
        registered_hospital_name: string;
        is_5_years_consecutive: boolean;
        check_time?: string;
    } | null;
}

export const insuranceApi = {
    lookup: async (query: string): Promise<InsuranceLookupResult> => {
        const response = await api.post('/insurance/lookup/', { query });
        return response.data;
    },
};

/**
 * Visit/Reception API Services
 * Quản lý tiếp nhận khám bệnh
 */
export const visitApi = {
    // Lấy danh sách visits
    getAll: async (params?: {
        page?: number;
        status?: string;
        patient?: string;
        today?: boolean;
        station_id?: string;
    }): Promise<PaginatedResponse<Visit>> => {
        const response = await api.get('/reception/visits/', { params });
        return response.data;
    },

    // Lấy chi tiết visit
    getById: async (id: string): Promise<Visit> => {
        const response = await api.get(`/reception/visits/${id}/`);
        return response.data;
    },

    // Tạo visit mới (tiếp nhận bệnh nhân)
    create: async (data: {
        patient: string;
        priority?: string;  // 'NORMAL' | 'PRIORITY' | 'EMERGENCY'
        pending_merge?: boolean;
        station_id?: string | null;
    }): Promise<Visit> => {
        const response = await api.post('/reception/visits/', data);
        return response.data;
    },

    // Cập nhật visit
    update: async (id: string, data: Partial<Visit>): Promise<Visit> => {
        const response = await api.patch(`/reception/visits/${id}/`, data);
        return response.data;
    },

    // Lấy visits hôm nay
    getToday: async (): Promise<Visit[]> => {
        const today = new Date().toISOString().split('T')[0];
        const response = await api.get('/reception/visits/', {
            params: { visit_date: today },
        });
        return response.data.results || response.data;
    },

    // Gọi AI triage agent cho visit (y tá gửi sinh hiệu + lý do khám)
    triage: async (id: string, data: {
        chief_complaint: string;
        vital_signs?: {
            heart_rate?: number;
            bp_systolic?: number;
            bp_diastolic?: number;
            respiratory_rate?: number;
            temperature?: number;
            spo2?: number;
            weight?: number;
            height?: number;
        };
        pain_scale?: number;
        consciousness?: string;
    }) => {
        const response = await api.post(`/reception/visits/${id}/triage/`, data);
        return response.data;
    },

    // Xác nhận kết quả phân luồng (AI hoặc thủ công)
    confirmTriage: async (id: string, data: {
        department_id: string;
        triage_method: 'AI' | 'MANUAL';
        triage_code?: string;
        chief_complaint?: string;
        vital_signs?: Record<string, number | undefined>;
        triage_confidence?: number;
        triage_ai_response?: string;
    }): Promise<Visit> => {
        const response = await api.post(`/reception/visits/${id}/confirm-triage/`, data);
        return response.data;
    },
};

/**
 * Department API Services
 * Danh sách khoa
 */
export const departmentApi = {
    getAll: async (): Promise<Department[]> => {
        const response = await api.get('/departments/');
        // Handle both paginated and non-paginated
        return Array.isArray(response.data) ? response.data : (response.data.results || []);
    },
};

/**
 * Pharmacy API Services
 * Quản lý đơn thuốc và danh mục thuốc
 */
export interface Medication {
    id: string;
    code: string;
    name: string;
    active_ingredient: string | null;
    strength: string | null;
    dosage_form: string | null;
    usage_route: string | null;
    unit: string;
    selling_price: number;
    inventory_count: number;
    category_name: string | null;
}

export interface PrescriptionDetail {
    id: string;
    medication: string;
    medication_name: string;
    medication_strength: string | null;
    medication_dosage_form: string | null;
    medication_unit: string;
    quantity: number;
    usage_instruction: string;
    duration_days: number | null;
    unit_price: number;
    dispensed_quantity: number;
}

export interface PrescriptionDetailInput {
    medication: string;
    quantity: number;
    usage_instruction: string;
    duration_days?: number | null;
}

export interface Prescription {
    id: string;
    visit: string;
    doctor: string;
    prescription_code: string;
    prescription_date: string;
    diagnosis: string | null;
    note: string | null;
    status: 'PENDING' | 'PARTIAL' | 'DISPENSED' | 'CANCELLED';
    total_price: number;
    patient_name: string | null;
    details: PrescriptionDetail[];
}

export const pharmacyApi = {
    searchMedications: async (query: string): Promise<Medication[]> => {
        const response = await api.get('/pharmacy/medications/', { params: { search: query } });
        return response.data.results || response.data || [];
    },

    getPrescriptionByVisit: async (visitId: string): Promise<Prescription | null> => {
        const response = await api.get('/pharmacy/prescriptions/', { params: { visit: visitId } });
        const results = response.data.results || response.data;
        return Array.isArray(results) && results.length > 0 ? results[0] : null;
    },

    createPrescription: async (data: {
        visit: string;
        doctor: string;
        diagnosis?: string;
        note?: string;
        details_input: PrescriptionDetailInput[];
    }): Promise<Prescription> => {
        const response = await api.post('/pharmacy/prescriptions/', data);
        return response.data;
    },

    updatePrescription: async (id: string, data: {
        diagnosis?: string;
        note?: string;
        details_input?: PrescriptionDetailInput[];
    }): Promise<Prescription> => {
        const response = await api.patch(`/pharmacy/prescriptions/${id}/`, data);
        return response.data;
    },

    getPrescriptions: async (params?: {
        status?: string;
    }): Promise<PaginatedResponse<Prescription>> => {
        const response = await api.get('/pharmacy/prescriptions/', { params });
        return response.data;
    },

    getPrescriptionById: async (id: string): Promise<Prescription> => {
        const response = await api.get(`/pharmacy/prescriptions/${id}/`);
        return response.data;
    },

    dispense: async (id: string, details?: any) => {
        const response = await api.post(`/pharmacy/prescriptions/${id}/dispense/`, details || {});
        return response.data;
    },

    refuse: async (id: string, reason?: string) => {
        const response = await api.post(`/pharmacy/prescriptions/${id}/refuse/`, { reason });
        return response.data;
    },
};
/**
 * Queue Management API Services
 * Hệ thống hàng chờ lâm sàng 3 luồng (Emergency / Booking / Walk-in)
 */
export const qmsApi = {
    // ==========================================
    // Legacy CRUD endpoints
    // ==========================================

    // Lấy danh sách hàng đợi
    getQueues: async (params?: {
        status?: string;
        station?: string;
    }): Promise<PaginatedResponse<QueueNumber>> => {
        const response = await api.get('/qms/queues/', { params });
        return response.data;
    },

    // Lấy hàng đợi đang chờ
    getWaiting: async (stationId?: string): Promise<QueueNumber[]> => {
        const response = await api.get('/qms/queues/', {
            params: { status: 'WAITING', station: stationId },
        });
        return response.data.results || response.data;
    },

    // Hoàn thành số hiện tại
    completeQueue: async (entryId: string): Promise<QueueNumber> => {
        const response = await api.patch(`/qms/entries/${entryId}/status/`, {
            status: 'COMPLETED',
        });
        return response.data;
    },

    // Bỏ qua số
    skipQueue: async (entryId: string): Promise<QueueNumber> => {
        const response = await api.patch(`/qms/entries/${entryId}/status/`, {
            status: 'SKIPPED',
        });
        return response.data;
    },

    // Đã gọi nhưng không có mặt
    noShowQueue: async (entryId: string): Promise<QueueNumber> => {
        const response = await api.patch(`/qms/entries/${entryId}/status/`, {
            status: 'NO_SHOW',
        });
        return response.data;
    },

    // Gọi lại bệnh nhân vắng
    recallQueue: async (entryId: string): Promise<QueueNumber & { audio_url?: string | null }> => {
        const response = await api.patch(`/qms/entries/${entryId}/status/`, {
            status: 'CALLED',
        });
        return response.data;
    },

    // === Display Pairing ===

    registerDisplay: async (): Promise<{ code: string }> => {
        const response = await api.post('/qms/display/register/');
        return response.data;
    },

    checkDisplay: async (code: string): Promise<{ paired: boolean; station_id?: string; station_name?: string }> => {
        const response = await api.get('/qms/display/check/', { params: { code } });
        return response.data;
    },

    pairDisplay: async (code: string, stationId: string): Promise<{ success: boolean; message: string }> => {
        const response = await api.post('/qms/display/pair/', { code, station_id: stationId });
        return response.data;
    },

    // === Service Stations ===

    // Lấy danh sách stations (hỗ trợ filter station_type)
    getStations: async (stationType?: string): Promise<ServiceStation[]> => {
        const params: Record<string, string> = {};
        if (stationType) params.station_type = stationType;
        const response = await api.get('/qms/stations/', { params });
        return response.data.results || response.data;
    },

    // Lấy station theo ID
    getStationById: async (id: string): Promise<ServiceStation> => {
        const response = await api.get(`/qms/stations/${id}/`);
        return response.data;
    },

    // ==========================================
    // Clinical Queue 3-Stream Endpoints
    // ==========================================

    /**
     * Kiosk Check-in — Bệnh nhân quét QR booking
     * POST /qms/kiosk/checkin/
     */
    kioskCheckin: async (appointmentId: string, stationId: string): Promise<KioskCheckinResponse> => {
        const response = await api.post('/qms/kiosk/checkin/', {
            appointment_id: appointmentId,
            station_id: stationId,
        });
        return response.data;
    },

    /**
     * Walk-in Check-in — Vãng lai lấy số
     * POST /qms/walkin/checkin/
     */
    walkinCheckin: async (data: {
        patient_id: string;
        station_id: string;
        reason?: string;
        is_elderly_or_child?: boolean;
    }): Promise<WalkinCheckinResponse> => {
        const response = await api.post('/qms/walkin/checkin/', data);
        return response.data;
    },

    /**
     * Emergency Flag — Nhân viên y tế flag cấp cứu
     * POST /qms/emergency/flag/
     */
    emergencyFlag: async (data: {
        patient_id: string;
        station_id: string;
        reason?: string;
    }): Promise<{ success: boolean; message: string; queue_number: string; priority: number }> => {
        const response = await api.post('/qms/emergency/flag/', data);
        return response.data;
    },

    /**
     * Doctor Call Next — Bác sĩ gọi bệnh nhân tiếp theo
     * Thuật toán: Emergency → Booking ưu tiên → Walk-in FCFS
     * POST /qms/doctor/call-next/
     */
    doctorCallNext: async (stationId: string): Promise<CallNextResponse> => {
        const response = await api.post('/qms/doctor/call-next/', {
            station_id: stationId,
        });
        return response.data;
    },

    /**
     * Queue Board — Bảng LED hàng đợi theo station
     * GET /qms/queue/board/?station_id=...
     */
    getQueueBoard: async (stationId: string): Promise<QueueBoardData> => {
        const response = await api.get('/qms/queue/board/', {
            params: { station_id: stationId },
        });
        return response.data.data;
    },

    // Legacy display (backward compat)
    getDisplayQueue: async () => {
        try {
            const [currentRes, waitingRes] = await Promise.all([
                api.get('/qms/queues/', { params: { status: 'IN_SERVICE' } }),
                api.get('/qms/queues/', { params: { status: 'WAITING' } }),
            ]);
            const current = currentRes.data.results || currentRes.data || [];
            const waiting = waitingRes.data.results || waitingRes.data || [];
            return {
                current_calls: current.slice(0, 3),
                upcoming: waiting.slice(0, 6),
                stats: {
                    total: current.length + waiting.length,
                    completed: 0,
                    waiting: waiting.length,
                },
            };
        } catch {
            return { current_calls: [], upcoming: [], stats: { total: 0, completed: 0, waiting: 0 } };
        }
    },
};

/**
 * Dashboard Statistics API
 */
export const dashboardApi = {
    // Lấy thống kê tổng quan
    getStats: async () => {
        // Gọi nhiều API song song để lấy số liệu
        const [patientsRes, visitsRes, queuesRes] = await Promise.all([
            api.get('/patients/', { params: { page: 1 } }),
            api.get('/reception/visits/', { params: { page: 1 } }),
            api.get('/qms/queues/', { params: { status: 'WAITING' } }),
        ]);

        return {
            totalPatients: patientsRes.data.count || 0,
            todayVisits: visitsRes.data.count || 0,
            waitingQueue: queuesRes.data.count || (queuesRes.data.results?.length || 0),
        };
    },
};

/**
 * EMR/Clinical API Services
 * Quản lý hồ sơ bệnh án điện tử
 */
export const emrApi = {
    // Lấy danh sách clinical records
    getAll: async (params?: {
        page?: number;
        visit?: string;
        visit__patient?: string;
    }) => {
        const response = await api.get('/emr/records/', { params });
        return response.data;
    },

    // Lấy chi tiết clinical record theo ID
    getById: async (id: string) => {
        const response = await api.get(`/emr/records/${id}/`);
        return response.data;
    },

    // Lấy clinical record theo visit ID
    getByVisit: async (visitId: string) => {
        const response = await api.get('/emr/records/', {
            params: { visit: visitId },
        });
        const results = response.data.results || response.data;
        return results.length > 0 ? results[0] : null;
    },

    // Tạo clinical record mới
    create: async (data: {
        visit: string;
        chief_complaint: string;
        vital_signs?: {
            temperature?: number;
            systolic_bp?: number;
            diastolic_bp?: number;
            heart_rate?: number;
            respiratory_rate?: number;
            spo2?: number;
            weight?: number;
            height?: number;
        };
    }) => {
        const response = await api.post('/emr/records/', data);
        return response.data;
    },

    // Cập nhật clinical record
    update: async (id: string, data: Partial<{
        chief_complaint: string;
        history_of_present_illness: string;
        physical_exam: string;
        vital_signs: {
            temperature?: number;
            systolic_bp?: number;
            diastolic_bp?: number;
            heart_rate?: number;
            respiratory_rate?: number;
            spo2?: number;
            weight?: number;
            height?: number;
        };
        final_diagnosis: string;
        treatment_plan: string;
        is_finalized: boolean;
    }>) => {
        const response = await api.patch(`/emr/records/${id}/`, data);
        return response.data;
    },

    // Lấy gợi ý AI cho visit
    getAISuggestions: async (visitId: string) => {
        const response = await api.get(`/emr/${visitId}/ai-suggestions/`);
        return response.data;
    },

    // Khóa hồ sơ & chuyển trạng thái đóng phí
    finalize: async (id: string) => {
        const response = await api.post(`/emr/records/${id}/finalize/`);
        return response.data;
    },
};

/**
 * AI Services
 * Triage, Vitals Assessment, Chat
 */
export const aiApi = {
    // Đánh giá phân luồng
    triageAssess: async (data: {
        visit_id?: string;
        patient_id?: string;
        patient_name?: string;
        age?: number;
        gender?: string;
        chief_complaint: string;
        symptoms?: string[];
        vital_signs: Record<string, number | undefined>;
        medical_history?: string;
        pain_scale?: number;
        consciousness?: string;
        onset?: string;
    }) => {
        const response = await api.post('/triage/assess/', data);
        return response.data;
    },

    // Đánh giá sinh hiệu (quick rule-based)
    vitalsAssess: async (vitalSigns: {
        temperature?: number;
        systolic_bp?: number;
        diastolic_bp?: number;
        heart_rate?: number;
        respiratory_rate?: number;
        spo2?: number;
    }) => {
        const response = await api.post('/vitals/assess/', { vital_signs: vitalSigns });
        return response.data;
    },

    // Kiểm tra tương tác thuốc
    checkDrugInteractions: async (medications: Array<{
        drug_name: string;
        dosage: string;
        frequency: string;
    }>) => {
        const response = await api.post('/pharmacy/interactions/', { medications });
        return response.data;
    },

    // Tạo tóm tắt bệnh nhân
    generateSummary: async (patientId: string) => {
        const response = await api.post('/patient/summary/', { patient_id: patientId });
        return response.data;
    },

    // Chat với AI (sync mode)
    chat: async (visitId: string, message: string, sessionId?: string) => {
        const response = await api.post('/chat/sync/', {
            visit_id: visitId,
            message,
            session_id: sessionId || `visit-${visitId}`,
        });
        return response.data;
    },

    // Chat streaming URL
    getChatStreamUrl: () => {
        const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
        return `${baseUrl}/chat/stream/`;
    },
};

/**
 * LIS (Laboratory Information System) API Services
 * Quản lý xét nghiệm
 */
export const lisApi = {
    // === Lab Orders ===
    getOrders: async (params?: {
        page?: number;
        status?: string;
        patient?: string;
        visit?: string;
    }) => {
        const response = await api.get('/lis/orders/', { params });
        return response.data;
    },

    getOrderById: async (id: string) => {
        const response = await api.get(`/lis/orders/${id}/`);
        return response.data;
    },

    createOrder: async (data: {
        visit: string;
        patient: string;
        tests: string[];  // Array of test IDs
        note?: string;
    }) => {
        const response = await api.post('/lis/orders/', data);
        return response.data;
    },

    updateOrderStatus: async (id: string, status: string) => {
        const response = await api.patch(`/lis/orders/${id}/`, { status });
        return response.data;
    },

    // === Lab Tests (Catalog) ===
    getTests: async (params?: { category?: string; search?: string }) => {
        const response = await api.get('/lis/tests/', { params });
        return response.data;
    },

    // === Lab Results ===
    enterResults: async (orderId: string, results: Array<{
        detail_id: string;
        value_string: string;
        value_numeric?: number;
    }>) => {
        const response = await api.post(`/lis/orders/${orderId}/results/`, { results });
        return response.data;
    },

    verifyOrder: async (orderId: string) => {
        const response = await api.post(`/lis/orders/${orderId}/verify/`);
        return response.data;
    },
};

/**
 * RIS (Radiology Information System) API Services
 * Quản lý chẩn đoán hình ảnh
 */
export const risApi = {
    // === Imaging Orders ===
    getOrders: async (params?: {
        page?: number;
        status?: string;
        patient?: string;
        visit?: string;
    }) => {
        const response = await api.get('/ris/orders/', { params });
        return response.data;
    },

    getOrderById: async (id: string) => {
        const response = await api.get(`/ris/orders/${id}/`);
        return response.data;
    },

    createOrder: async (data: {
        visit: string;
        patient: string;
        procedure: string;  // Procedure ID
        clinical_indication: string;
        priority?: string;
        note?: string;
    }) => {
        const response = await api.post('/ris/orders/', data);
        return response.data;
    },

    updateOrderStatus: async (id: string, status: string) => {
        const response = await api.patch(`/ris/orders/${id}/`, { status });
        return response.data;
    },

    // === Imaging Procedures (Catalog) ===
    getProcedures: async (params?: { modality?: string; search?: string }) => {
        const response = await api.get('/ris/procedures/', { params });
        return response.data;
    },

    // === Imaging Results ===
    submitResult: async (orderId: string, data: {
        findings: string;
        conclusion: string;
        recommendation?: string;
        is_abnormal?: boolean;
        is_critical?: boolean;
    }) => {
        const response = await api.post(`/ris/orders/${orderId}/result/`, data);
        return response.data;
    },

    // === Workflow Actions ===
    startExecution: async (orderId: string) => {
        const response = await api.post(`/ris/orders/${orderId}/start_execution/`);
        return response.data;
    },

    saveResult: async (orderId: string, data: {
        findings: string;
        conclusion: string;
        recommendation?: string;
    }) => {
        const response = await api.post(`/ris/orders/${orderId}/save_result/`, data);
        return response.data;
    },

    verifyResult: async (orderId: string) => {
        const response = await api.post(`/ris/orders/${orderId}/verify/`);
        return response.data;
    },
};

/**
 * CLS (Cận Lâm Sàng) Paraclinical API Services
 * Quản lý chỉ định dịch vụ cận lâm sàng (xét nghiệm, CĐHA, thăm dò chức năng)
 */
export const clsApi = {
    // Lấy danh mục dịch vụ CLS
    getServices: async (params?: { category?: string; search?: string }) => {
        const response = await api.get('/cls/services/', { params });
        return response.data;
    },

    // Lấy danh sách chỉ định theo lượt khám
    getOrders: async (params?: { visit?: string; status?: string }) => {
        const response = await api.get('/cls/orders/', { params });
        return response.data;
    },

    // Tạo nhiều chỉ định cùng lúc
    batchOrder: async (data: {
        visit_id: string;
        service_ids: string[];
    }): Promise<{ success: boolean; orders: Array<{ id: string; service_name: string; service_code: string; price: string; status: string }>; count: number; duplicates?: string[] }> => {
        const response = await api.post('/cls/batch-order/', data);
        return response.data;
    },
    // Lấy phiếu xét nghiệm cho trang LIS (Huyết học/Sinh hóa/Miễn dịch/Vi sinh)
    getLabOrders: async (params?: { visit?: string; status?: string; page?: number }) => {
        const response = await api.get('/cls/orders/', {
            params: { ...params, service_group: 'xet_nghiem' },
        });
        return response.data;
    },

    // Lấy phiếu CĐHA/Thăm dò cho trang RIS-CLS
    getImagingOrders: async (params?: { visit?: string; status?: string; page?: number }) => {
        const response = await api.get('/cls/orders/', {
            params: { ...params, service_group: 'chan_doan_hinh_anh' },
        });
        return response.data;
    },

    // Cập nhật trạng thái phiếu CLS (ORDERED → PROCESSING → COMPLETED)
    updateLabOrder: async (id: string, status: string) => {
        const response = await api.patch(`/cls/orders/${id}/`, { status });
        return response.data;
    },
};



/**
 * Billing API Services
 * Quản lý hóa đơn và thanh toán
 */
export const billingApi = {
    // === Invoices ===
    getInvoices: async (params?: {
        page?: number;
        status?: string;
        patient?: string;
        visit?: string;
    }) => {
        const response = await api.get('/billing/invoices/', { params });
        return response.data;
    },

    getInvoiceById: async (id: string) => {
        const response = await api.get(`/billing/invoices/${id}/`);
        return response.data;
    },

    createInvoice: async (visitId: string) => {
        const response = await api.post('/billing/invoices/', { visit: visitId });
        return response.data;
    },

    // === Payments ===
    createPayment: async (invoiceId: string, data: {
        amount: number;
        payment_method: string;
        insurance_coverage?: number;  // phần BHYT chi trả — backend dùng để cập nhật patient_payable
        note?: string;
    }) => {
        const response = await api.post(`/billing/invoices/${invoiceId}/pay/`, data);
        return response.data;
    },

    // === Service Catalog ===
    getServices: async (params?: { service_type?: string; search?: string }) => {
        const response = await api.get('/billing/services/', { params });
        return response.data;
    },
};

/**
 * Kiosk Self-Service API
 * Public endpoints (AllowAny) — KHÔNG dùng JWT auth
 * Sử dụng axios raw thay vì api instance (có JWT interceptor)
 */
import axios from 'axios';
import type {
    KioskSelfServiceIdentifyResponse,
    KioskSelfServiceRegisterResponse,
} from '@/types';

const KIOSK_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1');

export const kioskApi = {
    /**
     * Bước 1: Quét QR CCCD/BHYT → Xác thực bệnh nhân
     * POST /api/kiosk/identify/
     */
    identify: async (scanData: string): Promise<KioskSelfServiceIdentifyResponse> => {
        const response = await axios.post(`${KIOSK_BASE_URL}/kiosk/identify/`, {
            scan_data: scanData,
        }, {
            headers: { 'Content-Type': 'application/json' },
            timeout: 15000,
        });
        return response.data;
    },

    /**
     * Bước 2: Đăng ký lượt khám → Lấy số thứ tự
     * POST /api/kiosk/register/
     */
    register: async (patientId: string, chiefComplaint: string): Promise<KioskSelfServiceRegisterResponse> => {
        const response = await axios.post(`${KIOSK_BASE_URL}/kiosk/register/`, {
            patient_id: patientId,
            chief_complaint: chiefComplaint,
        }, {
            headers: { 'Content-Type': 'application/json' },
            timeout: 15000,
        });
        return response.data;
    },
};

