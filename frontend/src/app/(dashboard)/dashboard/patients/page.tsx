'use client';

import { useState, useEffect } from 'react';
import {
    Card,
    Table,
    Button,
    Input,
    Space,
    Tag,
    Modal,
    Form,
    DatePicker,
    Select,
    App,
    Typography,
    Tooltip,
    Popconfirm,
} from 'antd';
import {
    PlusOutlined,
    SearchOutlined,
    EditOutlined,
    DeleteOutlined,
    ReloadOutlined,
    UserOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { patientApi } from '@/lib/services';
import type { Patient } from '@/types';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

/**
 * Patients Page
 * Quản lý danh sách bệnh nhân (CRUD)
 */

const genderLabels: Record<string, string> = {
    M: 'Nam',
    F: 'Nữ',
    O: 'Khác',
};

const genderColors: Record<string, string> = {
    M: 'blue',
    F: 'pink',
    O: 'default',
};

export default function PatientsPage() {
    const [patients, setPatients] = useState<Patient[]>([]);
    const [loading, setLoading] = useState(false);
    const [searchText, setSearchText] = useState('');
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingPatient, setEditingPatient] = useState<Patient | null>(null);
    const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 });
    const [form] = Form.useForm();
    const { message } = App.useApp();

    // Fetch patients
    const fetchPatients = async (page = 1, search = '') => {
        setLoading(true);
        try {
            const response = await patientApi.getAll({ page, search });
            // Hỗ trợ cả response paginated ({count, results}) và non-paginated (array)
            const list = Array.isArray(response) ? response : (response.results || []);
            const total = Array.isArray(response) ? response.length : (response.count || 0);
            setPatients(list);
            setPagination({
                current: page,
                pageSize: 10,
                total,
            });
        } catch (error) {
            console.error('Error fetching patients:', error);
            message.error('Không thể tải danh sách bệnh nhân');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchPatients();
    }, []);

    // Handle search
    const handleSearch = (value: string) => {
        setSearchText(value);
        fetchPatients(1, value);
    };

    // Handle table pagination
    const handleTableChange = (pag: { current?: number; pageSize?: number }) => {
        fetchPatients(pag.current || 1, searchText);
    };

    // Open modal for create/edit
    const openModal = (patient?: Patient) => {
        setEditingPatient(patient || null);
        if (patient) {
            form.setFieldsValue({
                ...patient,
                date_of_birth: patient.date_of_birth ? dayjs(patient.date_of_birth) : null,
            });
        } else {
            form.resetFields();
        }
        setIsModalOpen(true);
    };

    const handleSubmit = async (values: Record<string, unknown>) => {
        try {
            const data = {
                ...values,
                date_of_birth: values.date_of_birth
                    ? dayjs(values.date_of_birth as string).format('YYYY-MM-DD')
                    : undefined,
            };

            if (editingPatient) {
                await patientApi.update(editingPatient.id, data);
                message.success('Cập nhật bệnh nhân thành công!');
            } else {
                await patientApi.create(data);
                message.success('Thêm bệnh nhân mới thành công!');
            }

            setIsModalOpen(false);
            setEditingPatient(null);
            form.resetFields();
            await fetchPatients(1, searchText);
        } catch (error) {
            console.error('Error saving patient:', error);
            message.error('Không thể lưu thông tin bệnh nhân');
        }
    };

    // Handle delete
    const handleDelete = async (id: string) => {
        try {
            await patientApi.delete(id);
            message.success('Đã xóa bệnh nhân');
            fetchPatients(pagination.current, searchText);
        } catch (error) {
            console.error('Error deleting patient:', error);
            message.error('Không thể xóa bệnh nhân');
        }
    };

    // Table columns
    const columns: ColumnsType<Patient> = [
        {
            title: 'Mã BN',
            dataIndex: 'patient_code',
            key: 'patient_code',
            width: 120,
            render: (code: string) => <Text strong className="text-blue-600">{code}</Text>,
        },
        {
            title: 'Họ và tên',
            dataIndex: 'full_name',
            key: 'full_name',
            render: (_: unknown, record: Patient) => (
                <Space>
                    <UserOutlined className="text-gray-400" />
                    <Text>{record.full_name || `${record.last_name} ${record.first_name}`}</Text>
                </Space>
            ),
        },
        {
            title: 'Ngày sinh',
            dataIndex: 'date_of_birth',
            key: 'date_of_birth',
            width: 120,
            render: (date: string) => date ? dayjs(date).format('DD/MM/YYYY') : '-',
        },
        {
            title: 'Giới tính',
            dataIndex: 'gender',
            key: 'gender',
            width: 100,
            render: (gender: string) => (
                <Tag color={genderColors[gender]}>{genderLabels[gender] || gender}</Tag>
            ),
        },
        {
            title: 'SĐT',
            dataIndex: 'contact_number',
            key: 'contact_number',
            width: 120,
        },
        {
            title: 'BHYT',
            dataIndex: 'insurance_number',
            key: 'insurance_number',
            width: 150,
            render: (ins: string) => ins || <Text type="secondary">-</Text>,
        },
        {
            title: 'Thao tác',
            key: 'actions',
            width: 120,
            render: (_: unknown, record: Patient) => (
                <Space>
                    <Tooltip title="Sửa">
                        <Button
                            type="text"
                            icon={<EditOutlined />}
                            onClick={() => openModal(record)}
                        />
                    </Tooltip>
                    <Popconfirm
                        title="Xóa bệnh nhân?"
                        description="Bạn có chắc muốn xóa bệnh nhân này?"
                        onConfirm={() => handleDelete(record.id)}
                        okText="Xóa"
                        cancelText="Hủy"
                    >
                        <Tooltip title="Xóa">
                            <Button type="text" danger icon={<DeleteOutlined />} />
                        </Tooltip>
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    return (
        <div className="space-y-4">
            {/* Page Header */}
            <div className="flex justify-between items-center">
                <div>
                    <Title level={3} className="!mb-0">Quản lý Bệnh nhân</Title>
                    <Text type="secondary">Danh sách bệnh nhân trong hệ thống</Text>
                </div>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => openModal()}>
                    Thêm mới
                </Button>
            </div>

            {/* Main Content */}
            <Card>
                {/* Toolbar */}
                <div className="flex justify-between items-center mb-4">
                    <Input.Search
                        placeholder="Tìm theo mã, tên, SĐT..."
                        allowClear
                        onSearch={handleSearch}
                        style={{ width: 300 }}
                        prefix={<SearchOutlined className="text-gray-400" />}
                    />
                    <Button icon={<ReloadOutlined />} onClick={() => fetchPatients(1, '')}>
                        Làm mới
                    </Button>
                </div>

                {/* Table */}
                <Table
                    columns={columns}
                    dataSource={patients}
                    rowKey="id"
                    loading={loading}
                    pagination={{
                        ...pagination,
                        showSizeChanger: false,
                        showTotal: (total) => `Tổng ${total} bệnh nhân`,
                    }}
                    onChange={handleTableChange}
                    scroll={{ x: 900 }}
                />
            </Card>

            {/* Create/Edit Modal */}
            <Modal
                title={editingPatient ? 'Cập nhật bệnh nhân' : 'Thêm bệnh nhân mới'}
                open={isModalOpen}
                onCancel={() => setIsModalOpen(false)}
                footer={null}
                width={600}
            >
                <Form
                    form={form}
                    layout="vertical"
                    onFinish={handleSubmit}
                    className="mt-4"
                >
                    <div className="grid grid-cols-2 gap-4">
                        <Form.Item
                            name="last_name"
                            label="Họ"
                            rules={[{ required: true, message: 'Vui lòng nhập họ' }]}
                        >
                            <Input placeholder="Nguyễn" />
                        </Form.Item>
                        <Form.Item
                            name="first_name"
                            label="Tên"
                            rules={[{ required: true, message: 'Vui lòng nhập tên' }]}
                        >
                            <Input placeholder="Văn A" />
                        </Form.Item>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <Form.Item name="date_of_birth" label="Ngày sinh">
                            <DatePicker className="w-full" format="DD/MM/YYYY" placeholder="Chọn ngày" />
                        </Form.Item>
                        <Form.Item name="gender" label="Giới tính" initialValue="O">
                            <Select>
                                <Select.Option value="M">Nam</Select.Option>
                                <Select.Option value="F">Nữ</Select.Option>
                                <Select.Option value="O">Khác</Select.Option>
                            </Select>
                        </Form.Item>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <Form.Item name="contact_number" label="Số điện thoại">
                            <Input placeholder="0912345678" />
                        </Form.Item>
                        <Form.Item name="id_card" label="CMND/CCCD">
                            <Input placeholder="Số CMND/CCCD" />
                        </Form.Item>
                    </div>

                    <Form.Item name="insurance_number" label="Số thẻ BHYT">
                        <Input placeholder="Số thẻ bảo hiểm y tế" />
                    </Form.Item>

                    <Form.Item name="address_detail" label="Địa chỉ chi tiết">
                        <Input.TextArea rows={2} placeholder="Số nhà, đường, phường/xã..." />
                    </Form.Item>

                    <div className="flex justify-end gap-2 mt-6">
                        <Button onClick={() => setIsModalOpen(false)}>Hủy</Button>
                        <Button type="primary" htmlType="submit">
                            {editingPatient ? 'Cập nhật' : 'Thêm mới'}
                        </Button>
                    </div>
                </Form>
            </Modal>
        </div>
    );
}
