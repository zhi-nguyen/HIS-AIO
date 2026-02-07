import api from './api';
import type {
    Patient,
    Visit,
    QueueNumber,
    ServiceStation,
    PaginatedResponse,
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
};

/**
 * Queue Management API Services
 * Hệ thống xếp hàng (QMS)
 */
export const qmsApi = {
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

    // Gọi số tiếp theo
    callNext: async (stationId: string): Promise<QueueNumber | null> => {
        const response = await api.post(`/qms/stations/${stationId}/call_next/`);
        return response.data;
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
