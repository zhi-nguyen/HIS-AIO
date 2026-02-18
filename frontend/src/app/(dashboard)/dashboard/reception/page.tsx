'use client';

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
    Card,
    Table,
    Button,
    Input,
    Space,
    Tag,
    Modal,
    Form,
    Select,
    Typography,
    Tooltip,
    AutoComplete,
    Descriptions,
    Badge,
    App,
} from 'antd';
import {
    PlusOutlined,
    SearchOutlined,
    UserAddOutlined,
    CheckCircleOutlined,
    ReloadOutlined,
    RobotOutlined,
    MedicineBoxOutlined,
    CheckOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { visitApi, patientApi, departmentApi } from '@/lib/services';
import type { Visit, Patient, Department } from '@/types';
import TriageModal from './TriageModal';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

/**
 * Reception Page
 * Tiếp nhận bệnh nhân, phân luồng AI, và xác nhận khoa hướng đến
 */

const statusConfig: Record<string, { color: string; label: string }> = {
    CHECK_IN: { color: 'cyan', label: 'Check-in' },
    TRIAGE: { color: 'orange', label: 'Phân luồng' },
    WAITING: { color: 'gold', label: 'Chờ khám' },
    IN_PROGRESS: { color: 'blue', label: 'Đang khám' },
    PENDING_RESULTS: { color: 'purple', label: 'Chờ CLS' },
    COMPLETED: { color: 'green', label: 'Hoàn thành' },
    CANCELLED: { color: 'red', label: 'Đã hủy' },
};

const priorityConfig: Record<string, { color: string; label: string }> = {
    NORMAL: { color: 'default', label: 'Bình thường' },
    PRIORITY: { color: 'orange', label: 'Ưu tiên' },
    EMERGENCY: { color: 'red', label: 'Cấp cứu' },
};

export default function ReceptionPage() {
    const { message } = App.useApp();
    const [visits, setVisits] = useState<Visit[]>([]);
    const [loading, setLoading] = useState(false);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [patientOptions, setPatientOptions] = useState<{ value: string; label: string; patient: Patient }[]>([]);
    const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
    const [searchPatient, setSearchPatient] = useState('');
    const [form] = Form.useForm();

    // --- Triage State (only open/close + visit ref, all other state is in TriageModal) ---
    const [triageModalOpen, setTriageModalOpen] = useState(false);
    const [triageVisit, setTriageVisit] = useState<Visit | null>(null);
    const [departments, setDepartments] = useState<Department[]>([]);

    // Fetch visits
    const fetchVisits = useCallback(async () => {
        setLoading(true);
        try {
            const response = await visitApi.getAll();
            const list = Array.isArray(response) ? response : (response.results || []);
            setVisits(list);
        } catch (error) {
            console.error('Error fetching visits:', error);
            message.error('Không thể tải danh sách lượt khám');
        } finally {
            setLoading(false);
        }
    }, [message]);

    // Fetch departments
    const fetchDepartments = useCallback(async () => {
        try {
            const depts = await departmentApi.getAll();
            setDepartments(depts);
        } catch (error) {
            console.error('Error fetching departments:', error);
        }
    }, []);

    useEffect(() => {
        fetchVisits();
        fetchDepartments();
    }, [fetchVisits, fetchDepartments]);

    // Debounce timer ref
    const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    // Search patients with debounce (400ms)
    const handlePatientSearch = useCallback((value: string) => {
        setSearchPatient(value);
        if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
        if (value.length < 2) {
            setPatientOptions([]);
            return;
        }
        searchTimerRef.current = setTimeout(async () => {
            try {
                const patients = await patientApi.search(value);
                setPatientOptions(
                    patients.map((p) => ({
                        value: p.id,
                        label: `${p.patient_code} - ${p.full_name || `${p.last_name} ${p.first_name}`}`,
                        patient: p,
                    }))
                );
            } catch (error) {
                console.error('Error searching patients:', error);
            }
        }, 400);
    }, []);

    // Select patient
    const handlePatientSelect = (value: string, option: { patient: Patient }) => {
        setSelectedPatient(option.patient);
        form.setFieldValue('patient', value);
    };

    // Create new visit
    const handleSubmit = async (values: { patient: string; priority?: string }) => {
        try {
            await visitApi.create({
                patient: values.patient,
                priority: values.priority,
            });
            message.success('Tiếp nhận bệnh nhân thành công!');
            setIsModalOpen(false);
            form.resetFields();
            setSelectedPatient(null);
            setSearchPatient('');
            fetchVisits();
        } catch (error) {
            console.error('Error creating visit:', error);
            message.error('Không thể tạo lượt khám');
        }
    };

    // Mở modal phân luồng — LUÔN fetch fresh data từ backend
    const openTriageModal = useCallback(async (visit: Visit) => {
        try {
            // Nếu visit đã qua AI (TRIAGE), phải fetch fresh để lấy đúng state
            if (visit.status === 'TRIAGE') {
                const freshVisit = await visitApi.getById(visit.id);
                setTriageVisit(freshVisit);
            } else {
                // CHECK_IN: chưa có data triage, dùng record từ table cũng đúng
                setTriageVisit(visit);
            }
        } catch (error) {
            console.error('Error fetching visit:', error);
            // Fallback: dùng record cũ nếu fetch thất bại
            setTriageVisit(visit);
        }
        setTriageModalOpen(true);
    }, []);

    // Callback khi triage thành công
    const handleTriageSuccess = useCallback(() => {
        fetchVisits();
    }, [fetchVisits]);

    // Computed Stats (Memoized)
    const stats = useMemo(() => {
        return {
            total: visits.length,
            waiting: visits.filter((v) => ['CHECK_IN', 'TRIAGE', 'WAITING'].includes(v.status)).length,
            inProgress: visits.filter((v) => v.status === 'IN_PROGRESS').length,
            completed: visits.filter((v) => v.status === 'COMPLETED').length,
        };
    }, [visits]);

    // Table columns (Memoized)
    const columns: ColumnsType<Visit> = useMemo(() => [
        {
            title: 'STT',
            dataIndex: 'queue_number',
            key: 'queue_number',
            width: 70,
            render: (num: number) => (
                <Badge
                    count={num}
                    style={{ backgroundColor: '#1E88E5', fontSize: 14, minWidth: 32 }}
                    overflowCount={999}
                />
            ),
        },
        {
            title: 'Mã khám',
            dataIndex: 'visit_code',
            key: 'visit_code',
            width: 140,
            render: (code: string) => <Text strong className="text-blue-600">{code}</Text>,
        },
        {
            title: 'Bệnh nhân',
            dataIndex: 'patient',
            key: 'patient',
            render: (_: unknown, record: Visit) => {
                const patient = record.patient_detail || record.patient;
                if (typeof patient === 'object' && patient) {
                    return (
                        <Space style={{ flexDirection: 'column', alignItems: 'flex-start', gap: 0 }}>
                            <Text strong>{patient.full_name || `${patient.last_name} ${patient.first_name}`}</Text>
                            <Text type="secondary" className="text-xs">{patient.patient_code}</Text>
                        </Space>
                    );
                }
                return patient || '-';
            },
        },
        {
            title: 'Check-in',
            dataIndex: 'check_in_time',
            key: 'check_in_time',
            width: 90,
            render: (time: string) => time ? dayjs(time).format('HH:mm') : '-',
        },
        {
            title: 'Ưu tiên',
            dataIndex: 'priority',
            key: 'priority',
            width: 110,
            render: (priority: string) => {
                const config = priorityConfig[priority] || { color: 'default', label: priority };
                return <Tag color={config.color}>{config.label}</Tag>;
            },
        },
        {
            title: 'Trạng thái',
            dataIndex: 'status',
            key: 'status',
            width: 120,
            render: (status: string) => {
                const config = statusConfig[status] || { color: 'default', label: status };
                return <Tag color={config.color}>{config.label}</Tag>;
            },
        },
        {
            title: 'Khoa hướng đến',
            key: 'department',
            width: 140,
            render: (_: unknown, record: Visit) => {
                if (record.confirmed_department_detail) {
                    return <Tag color="blue" icon={<CheckOutlined />}>{record.confirmed_department_detail.name}</Tag>;
                }
                if (record.recommended_department_detail) {
                    return <Tag color="orange">{record.recommended_department_detail.name} (AI)</Tag>;
                }
                return <Text type="secondary">-</Text>;
            },
        },
        {
            title: 'Thao tác',
            key: 'actions',
            width: 150,
            render: (_: unknown, record: Visit) => (
                <Space>
                    {record.status === 'CHECK_IN' && (
                        <Tooltip title="Phân luồng bằng AI">
                            <Button
                                type="primary"
                                size="small"
                                icon={<RobotOutlined />}
                                onClick={() => openTriageModal(record)}
                            >
                                Phân luồng
                            </Button>
                        </Tooltip>
                    )}
                    {record.status === 'TRIAGE' && !record.confirmed_department && (
                        <Tooltip title="Tiếp tục phân luồng">
                            <Button
                                size="small"
                                icon={<MedicineBoxOutlined />}
                                onClick={() => openTriageModal(record)}
                            >
                                Chốt khoa
                            </Button>
                        </Tooltip>
                    )}
                    {record.status === 'COMPLETED' && (
                        <Tag icon={<CheckCircleOutlined />} color="success">
                            Xong
                        </Tag>
                    )}
                </Space>
            ),
        },
    ], [openTriageModal]);

    return (
        <div className="space-y-4">
            {/* Page Header */}
            <div className="flex justify-between items-center">
                <div>
                    <Title level={3} className="!mb-0">Tiếp nhận Khám bệnh</Title>
                    <Text type="secondary">Quản lý lượt khám và tiếp nhận bệnh nhân</Text>
                </div>
                <Button type="primary" icon={<UserAddOutlined />} onClick={() => setIsModalOpen(true)}>
                    Tiếp nhận mới
                </Button>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-4 gap-4">
                <Card size="small">
                    <div className="text-center">
                        <Text type="secondary">Tổng hôm nay</Text>
                        <div className="text-2xl font-bold text-blue-600">{stats.total}</div>
                    </div>
                </Card>
                <Card size="small">
                    <div className="text-center">
                        <Text type="secondary">Đang chờ</Text>
                        <div className="text-2xl font-bold text-orange-500">{stats.waiting}</div>
                    </div>
                </Card>
                <Card size="small">
                    <div className="text-center">
                        <Text type="secondary">Đang khám</Text>
                        <div className="text-2xl font-bold text-blue-500">{stats.inProgress}</div>
                    </div>
                </Card>
                <Card size="small">
                    <div className="text-center">
                        <Text type="secondary">Hoàn thành</Text>
                        <div className="text-2xl font-bold text-green-500">{stats.completed}</div>
                    </div>
                </Card>
            </div>

            {/* Main Content */}
            <Card>
                <div className="flex justify-between items-center mb-4">
                    <Space>
                        <Input.Search
                            placeholder="Tìm mã khám, bệnh nhân..."
                            allowClear
                            style={{ width: 280 }}
                            prefix={<SearchOutlined className="text-gray-400" />}
                        />
                        <Select
                            placeholder="Trạng thái"
                            allowClear
                            style={{ width: 140 }}
                            options={Object.entries(statusConfig).map(([k, v]) => ({
                                value: k,
                                label: v.label,
                            }))}
                        />
                    </Space>
                    <Button icon={<ReloadOutlined />} onClick={fetchVisits}>
                        Làm mới
                    </Button>
                </div>

                <Table
                    columns={columns}
                    dataSource={visits}
                    rowKey="id"
                    loading={loading}
                    pagination={{ pageSize: 10, showTotal: (t) => `Tổng ${t} lượt khám` }}
                    scroll={{ x: 1100 }}
                />
            </Card>

            {/* Create Visit Modal */}
            <Modal
                title="Tiếp nhận bệnh nhân"
                open={isModalOpen}
                onCancel={() => {
                    setIsModalOpen(false);
                    setSelectedPatient(null);
                    setSearchPatient('');
                    form.resetFields();
                }}
                footer={null}
                width={600}
            >
                <Form form={form} layout="vertical" onFinish={handleSubmit} className="mt-4">
                    <Form.Item
                        name="patient"
                        label="Tìm bệnh nhân"
                        rules={[{ required: true, message: 'Vui lòng chọn bệnh nhân' }]}
                    >
                        <AutoComplete
                            options={patientOptions}
                            onSearch={handlePatientSearch}
                            onSelect={handlePatientSelect}
                            placeholder="Nhập mã BN, tên, SĐT để tìm..."
                            value={searchPatient}
                            onChange={setSearchPatient}
                        />
                    </Form.Item>

                    {selectedPatient && (
                        <Card size="small" className="mb-4 bg-blue-50">
                            <Descriptions size="small" column={2}>
                                <Descriptions.Item label="Mã BN">{selectedPatient.patient_code}</Descriptions.Item>
                                <Descriptions.Item label="Họ tên">
                                    {selectedPatient.full_name || `${selectedPatient.last_name} ${selectedPatient.first_name}`}
                                </Descriptions.Item>
                                <Descriptions.Item label="Ngày sinh">
                                    {selectedPatient.date_of_birth ? dayjs(selectedPatient.date_of_birth).format('DD/MM/YYYY') : '-'}
                                </Descriptions.Item>
                                <Descriptions.Item label="SĐT">{selectedPatient.contact_number || '-'}</Descriptions.Item>
                            </Descriptions>
                        </Card>
                    )}

                    <Form.Item name="priority" label="Mức độ ưu tiên" initialValue="NORMAL">
                        <Select>
                            <Select.Option value="NORMAL">Bình thường</Select.Option>
                            <Select.Option value="PRIORITY">Ưu tiên (Người già/Trẻ em)</Select.Option>
                            <Select.Option value="EMERGENCY">Cấp cứu</Select.Option>
                        </Select>
                    </Form.Item>

                    <div className="flex justify-end gap-2 mt-6">
                        <Button onClick={() => setIsModalOpen(false)}>Hủy</Button>
                        <Button type="primary" htmlType="submit" icon={<PlusOutlined />}>
                            Tiếp nhận
                        </Button>
                    </div>
                </Form>
            </Modal>

            {/* Triage Modal */}
            <TriageModal
                visit={triageVisit}
                open={triageModalOpen}
                departments={departments}
                onClose={() => setTriageModalOpen(false)}
                onSuccess={handleTriageSuccess}
            />
        </div>
    );
}
