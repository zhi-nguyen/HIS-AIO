'use client';

import { useState, useCallback, useRef } from 'react';
import {
    Modal,
    Form,
    Select,
    AutoComplete,
    Card,
    Descriptions,
    Button,
    Typography,
    App,
} from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { visitApi, patientApi } from '@/lib/services';
import type { Patient } from '@/types';
import dayjs from 'dayjs';

const { Text } = Typography;

interface CreateVisitModalProps {
    open: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

export default function CreateVisitModal({ open, onClose, onSuccess }: CreateVisitModalProps) {
    const { message } = App.useApp();
    const [form] = Form.useForm();
    const [patientOptions, setPatientOptions] = useState<{ value: string; label: string; patient: Patient }[]>([]);
    const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
    const [searchPatient, setSearchPatient] = useState('');
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
            handleClose();
            onSuccess();
        } catch (error) {
            console.error('Error creating visit:', error);
            message.error('Không thể tạo lượt khám');
        }
    };

    const handleClose = () => {
        setSelectedPatient(null);
        setSearchPatient('');
        form.resetFields();
        onClose();
    };

    return (
        <Modal
            title="Tiếp nhận bệnh nhân"
            open={open}
            onCancel={handleClose}
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
                    <Button onClick={handleClose}>Hủy</Button>
                    <Button type="primary" htmlType="submit" icon={<PlusOutlined />}>
                        Tiếp nhận
                    </Button>
                </div>
            </Form>
        </Modal>
    );
}
