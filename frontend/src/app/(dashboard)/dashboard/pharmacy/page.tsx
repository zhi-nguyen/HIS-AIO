'use client';

import { useState, useEffect, useCallback } from 'react';
import {
    Card,
    Table,
    Button,
    Space,
    Tag,
    Typography,
    Badge,
    Select,
    message,
    Modal,
    Descriptions,
    List,
    Divider,
} from 'antd';
import {
    ReloadOutlined,
    MedicineBoxOutlined,
    EyeOutlined,
    CheckCircleOutlined,
    PrinterOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { pharmacyApi } from '@/lib/services';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

/**
 * Pharmacy Page - Quản lý đơn thuốc
 * Medication & Prescription Management
 */

interface Medication {
    id: string;
    code: string;
    name: string;
    strength?: string;
    dosage_form?: string;
    unit: string;
}

interface PrescriptionDetail {
    id: string;
    medication: Medication;
    quantity: number;
    usage_instruction: string;
    duration_days?: number;
    dispensed_quantity: number;
}

interface Prescription {
    id: string;
    prescription_code: string;
    visit: { visit_code: string };
    patient?: { patient_code: string; full_name?: string; first_name?: string; last_name?: string };
    diagnosis?: string;
    note?: string;
    status: string;
    prescription_date: string;
    ai_interaction_warning?: string;
    total_price: number;
    details?: PrescriptionDetail[];
}

const statusConfig: Record<string, { color: string; label: string }> = {
    PENDING: { color: 'gold', label: 'Chờ phát thuốc' },
    PARTIAL: { color: 'cyan', label: 'Phát một phần' },
    DISPENSED: { color: 'green', label: 'Đã phát thuốc' },
    CANCELLED: { color: 'default', label: 'Đã hủy' },
};

export default function PharmacyPage() {
    const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
    const [loading, setLoading] = useState(false);
    const [statusFilter, setStatusFilter] = useState<string | undefined>('PENDING');
    const [selectedPrescription, setSelectedPrescription] = useState<Prescription | null>(null);
    const [detailModalOpen, setDetailModalOpen] = useState(false);
    const [dispensing, setDispensing] = useState(false);

    // Fetch prescriptions
    const fetchPrescriptions = useCallback(async () => {
        setLoading(true);
        try {
            const response = await pharmacyApi.getPrescriptions({ status: statusFilter });
            setPrescriptions(response.results || []);
        } catch (error) {
            console.error('Error fetching prescriptions:', error);
            message.error('Không thể tải danh sách đơn thuốc');
        } finally {
            setLoading(false);
        }
    }, [statusFilter]);

    useEffect(() => {
        fetchPrescriptions();
    }, [fetchPrescriptions]);

    // View prescription details
    const handleViewDetail = async (rx: Prescription) => {
        try {
            const detail = await pharmacyApi.getPrescriptionById(rx.id);
            setSelectedPrescription(detail);
            setDetailModalOpen(true);
        } catch (error) {
            console.error('Error fetching prescription detail:', error);
            message.error('Không thể tải chi tiết đơn thuốc');
        }
    };

    // Dispense prescription
    const handleDispense = async () => {
        if (!selectedPrescription?.details) return;

        setDispensing(true);
        try {
            // Dispense all remaining items
            const details = selectedPrescription.details
                .filter(d => d.quantity > d.dispensed_quantity)
                .map(d => ({
                    detail_id: d.id,
                    quantity: d.quantity - d.dispensed_quantity,
                }));

            if (details.length === 0) {
                message.warning('Đơn thuốc đã được phát đầy đủ');
                return;
            }

            await pharmacyApi.dispense(selectedPrescription.id, details);
            message.success('Đã phát thuốc thành công');
            setDetailModalOpen(false);
            fetchPrescriptions();
        } catch (error) {
            console.error('Error dispensing:', error);
            message.error('Không thể phát thuốc');
        } finally {
            setDispensing(false);
        }
    };

    // Table columns
    const columns: ColumnsType<Prescription> = [
        {
            title: 'Mã đơn',
            dataIndex: 'prescription_code',
            key: 'code',
            width: 130,
            render: (code: string) => <Text strong className="text-blue-600">{code}</Text>,
        },
        {
            title: 'Bệnh nhân',
            key: 'patient',
            render: (_, record) => {
                const patient = record.patient;
                if (!patient) return <Text type="secondary">-</Text>;
                return (
                    <Space orientation="vertical" size={0}>
                        <Text>
                            {patient.full_name ||
                                `${patient.last_name || ''} ${patient.first_name || ''}`}
                        </Text>
                        <Text type="secondary" className="text-xs">{patient.patient_code}</Text>
                    </Space>
                );
            },
        },
        {
            title: 'Mã khám',
            dataIndex: ['visit', 'visit_code'],
            key: 'visit',
            width: 120,
        },
        {
            title: 'Ngày kê',
            dataIndex: 'prescription_date',
            key: 'date',
            width: 110,
            render: (date: string) => dayjs(date).format('HH:mm DD/MM'),
        },
        {
            title: 'Tổng tiền',
            dataIndex: 'total_price',
            key: 'total',
            width: 110,
            render: (price: number) => (
                <Text strong>{price?.toLocaleString('vi-VN')} ₫</Text>
            ),
        },
        {
            title: 'Trạng thái',
            dataIndex: 'status',
            key: 'status',
            width: 130,
            render: (status: string) => {
                const config = statusConfig[status] || { color: 'default', label: status };
                return <Tag color={config.color}>{config.label}</Tag>;
            },
        },
        {
            title: 'Thao tác',
            key: 'actions',
            width: 150,
            render: (_, record) => (
                <Space>
                    <Button
                        size="small"
                        icon={<EyeOutlined />}
                        onClick={() => handleViewDetail(record)}
                    >
                        Chi tiết
                    </Button>
                </Space>
            ),
        },
    ];

    return (
        <div className="space-y-4">
            {/* Page Header */}
            <div className="flex justify-between items-center">
                <div>
                    <Title level={3} className="!mb-0">Dược phẩm</Title>
                    <Text type="secondary">Quản lý đơn thuốc và phát thuốc</Text>
                </div>
                <Space>
                    <Select
                        placeholder="Trạng thái"
                        value={statusFilter}
                        onChange={setStatusFilter}
                        allowClear
                        style={{ width: 150 }}
                        options={Object.entries(statusConfig).map(([k, v]) => ({
                            value: k,
                            label: v.label,
                        }))}
                    />
                    <Button icon={<ReloadOutlined />} onClick={fetchPrescriptions}>
                        Làm mới
                    </Button>
                </Space>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-4 gap-4">
                {Object.entries(statusConfig).map(([key, config]) => (
                    <Card size="small" key={key}>
                        <div className="text-center">
                            <Text type="secondary">{config.label}</Text>
                            <div className="text-2xl font-bold">
                                <Badge color={config.color} />
                                {prescriptions.filter(p => p.status === key).length}
                            </div>
                        </div>
                    </Card>
                ))}
            </div>

            {/* Main Table */}
            <Card>
                <Table
                    columns={columns}
                    dataSource={prescriptions}
                    rowKey="id"
                    loading={loading}
                    pagination={{ pageSize: 10, showTotal: (t) => `${t} đơn` }}
                    scroll={{ x: 900 }}
                />
            </Card>

            {/* Detail Modal */}
            <Modal
                title={
                    <Space>
                        <MedicineBoxOutlined />
                        Chi tiết đơn thuốc - {selectedPrescription?.prescription_code}
                    </Space>
                }
                open={detailModalOpen}
                onCancel={() => setDetailModalOpen(false)}
                width={700}
                footer={
                    selectedPrescription?.status !== 'DISPENSED' && selectedPrescription?.status !== 'CANCELLED' ? (
                        <Space>
                            <Button icon={<PrinterOutlined />}>In đơn</Button>
                            <Button
                                type="primary"
                                icon={<CheckCircleOutlined />}
                                loading={dispensing}
                                onClick={handleDispense}
                            >
                                Phát thuốc
                            </Button>
                        </Space>
                    ) : null
                }
            >
                {selectedPrescription && (
                    <div className="space-y-4">
                        <Descriptions size="small" column={2}>
                            <Descriptions.Item label="Chẩn đoán" span={2}>
                                {selectedPrescription.diagnosis || '-'}
                            </Descriptions.Item>
                            <Descriptions.Item label="Lời dặn" span={2}>
                                {selectedPrescription.note || '-'}
                            </Descriptions.Item>
                        </Descriptions>

                        {/* AI Warning */}
                        {selectedPrescription.ai_interaction_warning && (
                            <div className="bg-orange-50 border border-orange-200 rounded p-3">
                                <Text type="warning" strong>⚠️ Cảnh báo tương tác thuốc:</Text>
                                <div className="mt-1 text-sm">{selectedPrescription.ai_interaction_warning}</div>
                            </div>
                        )}

                        <Divider />

                        {/* Medication List */}
                        <List
                            size="small"
                            header={<Text strong>Danh sách thuốc</Text>}
                            dataSource={selectedPrescription.details}
                            renderItem={(detail: PrescriptionDetail) => (
                                <List.Item>
                                    <List.Item.Meta
                                        title={
                                            <Space>
                                                <Text strong>{detail.medication.name}</Text>
                                                {detail.medication.strength && (
                                                    <Tag>{detail.medication.strength}</Tag>
                                                )}
                                            </Space>
                                        }
                                        description={detail.usage_instruction}
                                    />
                                    <Space orientation="vertical" size={0} className="text-right">
                                        <Text>SL: {detail.quantity} {detail.medication.unit}</Text>
                                        {detail.dispensed_quantity > 0 && (
                                            <Text type="success" className="text-xs">
                                                Đã phát: {detail.dispensed_quantity}
                                            </Text>
                                        )}
                                    </Space>
                                </List.Item>
                            )}
                        />
                    </div>
                )}
            </Modal>
        </div>
    );
}
