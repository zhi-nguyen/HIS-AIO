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
 * Visit/Reception API Services
 * Quản lý tiếp nhận khám bệnh
 */
export const visitApi = {
    // Lấy danh sách visits
    getAll: async (params?: {
        page?: number;
        status?: string;
        patient?: string;
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
    completeQueue: async (queueId: string): Promise<QueueNumber> => {
        const response = await api.patch(`/qms/queues/${queueId}/`, {
            status: 'COMPLETED',
        });
        return response.data;
    },

    // Bỏ qua số
    skipQueue: async (queueId: string): Promise<QueueNumber> => {
        const response = await api.patch(`/qms/queues/${queueId}/`, {
            status: 'SKIPPED',
        });
        return response.data;
    },

    // === Service Stations ===

    // Lấy danh sách stations
    getStations: async (): Promise<ServiceStation[]> => {
        const response = await api.get('/qms/stations/');
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
    chat: async (visitId: string, message: string) => {
        const response = await api.post('/chat/sync/', {
            visit_id: visitId,
            message,
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
        test_id: string;
        value_string: string;
        value_numeric?: number;
    }>) => {
        const response = await api.post(`/lis/orders/${orderId}/results/`, { results });
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
};

/**
 * Pharmacy API Services
 * Quản lý đơn thuốc và phát thuốc
 */
export const pharmacyApi = {
    // === Prescriptions ===
    getPrescriptions: async (params?: {
        page?: number;
        status?: string;
        visit?: string;
    }) => {
        const response = await api.get('/pharmacy/prescriptions/', { params });
        return response.data;
    },

    getPrescriptionById: async (id: string) => {
        const response = await api.get(`/pharmacy/prescriptions/${id}/`);
        return response.data;
    },

    createPrescription: async (data: {
        visit: string;
        diagnosis?: string;
        note?: string;
        details: Array<{
            medication: string;
            quantity: number;
            usage_instruction: string;
            duration_days?: number;
        }>;
    }) => {
        const response = await api.post('/pharmacy/prescriptions/', data);
        return response.data;
    },

    updateStatus: async (id: string, status: string) => {
        const response = await api.patch(`/pharmacy/prescriptions/${id}/`, { status });
        return response.data;
    },

    // === Medications (Catalog) ===
    getMedications: async (params?: { category?: string; search?: string }) => {
        const response = await api.get('/pharmacy/medications/', { params });
        return response.data;
    },

    // === Dispense ===
    dispense: async (prescriptionId: string, details: Array<{
        detail_id: string;
        quantity: number;
    }>) => {
        const response = await api.post(`/pharmacy/prescriptions/${prescriptionId}/dispense/`, { details });
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
    createPayment: async (data: {
        invoice: string;
        amount: number;
        payment_method: string;
        note?: string;
    }) => {
        const response = await api.post('/billing/payments/', data);
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

