'use client';

import { useState, useCallback, useRef } from 'react';
import {
    Modal,
    Form,
    Input,
    Select,
    AutoComplete,
    Card,
    Descriptions,
    Button,
    Typography,
    DatePicker,
    Divider,
    App,
    Alert,
} from 'antd';
import { PlusOutlined, UserAddOutlined, AlertOutlined, SearchOutlined } from '@ant-design/icons';
import { visitApi, patientApi } from '@/lib/services';
import type { Patient } from '@/types';
import dayjs from 'dayjs';

const { Text } = Typography;

interface CreateVisitModalProps {
    open: boolean;
    onClose: () => void;
    onSuccess: () => void;
    emergencyMode?: boolean;
}

export default function CreateVisitModal({ open, onClose, onSuccess, emergencyMode = false }: CreateVisitModalProps) {
    const { message } = App.useApp();
    const [form] = Form.useForm();
    const [patientOptions, setPatientOptions] = useState<{ value: string; label: string; patient: Patient }[]>([]);
    const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
    const [searchPatient, setSearchPatient] = useState('');
    const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    // Inline patient creation
    const [showNewPatientForm, setShowNewPatientForm] = useState(false);
    const [newPatientForm] = Form.useForm();
    const [creatingPatient, setCreatingPatient] = useState(false);
    const [searchDone, setSearchDone] = useState(false);

    // Search patients
    const handlePatientSearch = useCallback((value: string) => {
        setSearchPatient(value);
        setSearchDone(false);
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
                setSearchDone(true);
            } catch (error) {
                console.error('Error searching patients:', error);
            }
        }, 400);
    }, []);

    // Select patient
    const handlePatientSelect = (value: string, option: { patient: Patient }) => {
        setSelectedPatient(option.patient);
        setShowNewPatientForm(false);
        form.setFieldValue('patient', value);
    };

    // Create new patient inline
    const handleCreatePatient = async () => {
        try {
            const values = await newPatientForm.validateFields();
            setCreatingPatient(true);

            const patientData: Partial<Patient> = {
                first_name: values.first_name,
                last_name: values.last_name,
                gender: values.gender || 'O',
                date_of_birth: values.date_of_birth ? values.date_of_birth.format('YYYY-MM-DD') : undefined,
                contact_number: values.contact_number || undefined,
                id_card: values.id_card || undefined,
                is_anonymous: false,
            };

            const newPatient = await patientApi.create(patientData);
            setSelectedPatient(newPatient);
            setShowNewPatientForm(false);
            form.setFieldValue('patient', newPatient.id);
            message.success(`Đã tạo bệnh nhân: ${newPatient.full_name}`);
        } catch (error) {
            console.error('Error creating patient:', error);
            message.error('Không thể tạo bệnh nhân');
        } finally {
            setCreatingPatient(false);
        }
    };

    // Emergency: create anonymous patient + visit
    const handleEmergencySubmit = async () => {
        try {
            // Create anonymous patient
            const anonPatient = await patientApi.create({
                first_name: 'Cấp cứu',
                last_name: `BN-${Date.now().toString(36).toUpperCase()}`,
                gender: 'O' as Patient['gender'],
                is_anonymous: true,
            } as Partial<Patient>);

            // Create visit with EMERGENCY priority + pending_merge
            await visitApi.create({
                patient: anonPatient.id,
                priority: 'EMERGENCY',
                pending_merge: true,
            });

            message.success('Đã tiếp nhận cấp cứu! Bệnh nhân ẩn danh, chờ gộp hồ sơ');
            handleClose();
            onSuccess();
        } catch (error) {
            console.error('Error creating emergency visit:', error);
            message.error('Không thể tiếp nhận cấp cứu');
        }
    };

    // Emergency with known info
    const handleEmergencyWithInfo = async () => {
        try {
            const values = await newPatientForm.validateFields();

            const hasRealInfo = values.first_name?.trim() && values.last_name?.trim();

            const patientData: Partial<Patient> = {
                first_name: values.first_name?.trim() || 'Cấp cứu',
                last_name: values.last_name?.trim() || `BN-${Date.now().toString(36).toUpperCase()}`,
                gender: values.gender || 'O',
                date_of_birth: values.date_of_birth ? values.date_of_birth.format('YYYY-MM-DD') : undefined,
                contact_number: values.contact_number || undefined,
                id_card: values.id_card || undefined,
                is_anonymous: !hasRealInfo,
            };

            const patient = await patientApi.create(patientData as Partial<Patient>);

            await visitApi.create({
                patient: patient.id,
                priority: 'EMERGENCY',
                pending_merge: !hasRealInfo,
            });

            message.success(
                hasRealInfo
                    ? `Tiếp nhận cấp cứu: ${patient.full_name}`
                    : `Tiếp nhận cấp cứu ẩn danh, chờ gộp hồ sơ`
            );
            handleClose();
            onSuccess();
        } catch (error) {
            console.error('Error:', error);
            message.error('Không thể tiếp nhận cấp cứu');
        }
    };

    // Normal submit
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
        setShowNewPatientForm(false);
        setSearchDone(false);
        form.resetFields();
        newPatientForm.resetFields();
        onClose();
    };

    // ── EMERGENCY MODE ─────────────────────────────────────────
    if (emergencyMode) {
        return (
            <Modal
                title={
                    <span className="text-red-600">
                        <AlertOutlined className="mr-2" />
                        Tiếp nhận cấp cứu
                    </span>
                }
                open={open}
                onCancel={handleClose}
                footer={null}
                width={600}
            >
                <Alert
                    type="warning"
                    showIcon
                    className="mb-4"
                    message="Các trường thông tin đều không bắt buộc"
                    description="Nếu BN bất tỉnh hoặc không thể cung cấp thông tin, nhấn 'Tiếp nhận ẩn danh'. Hồ sơ sẽ được cắm cờ chờ gộp khi xác định danh tính."
                />

                <Form form={newPatientForm} layout="vertical">
                    <div className="grid grid-cols-2 gap-x-4">
                        <Form.Item name="last_name" label="Họ">
                            <Input placeholder="VD: Nguyễn" />
                        </Form.Item>
                        <Form.Item name="first_name" label="Tên">
                            <Input placeholder="VD: Văn A" />
                        </Form.Item>
                        <Form.Item name="date_of_birth" label="Ngày sinh">
                            <DatePicker className="w-full" format="DD/MM/YYYY" placeholder="DD/MM/YYYY" />
                        </Form.Item>
                        <Form.Item name="gender" label="Giới tính">
                            <Select placeholder="Chọn">
                                <Select.Option value="M">Nam</Select.Option>
                                <Select.Option value="F">Nữ</Select.Option>
                                <Select.Option value="O">Khác</Select.Option>
                            </Select>
                        </Form.Item>
                        <Form.Item name="contact_number" label="SĐT">
                            <Input placeholder="Số điện thoại" />
                        </Form.Item>
                        <Form.Item name="id_card" label="CCCD/CMND">
                            <Input placeholder="Số CCCD" />
                        </Form.Item>
                    </div>
                </Form>

                <div className="flex justify-end gap-2 mt-4">
                    <Button onClick={handleClose}>Hủy</Button>
                    <Button
                        danger
                        type="primary"
                        icon={<AlertOutlined />}
                        onClick={handleEmergencySubmit}
                    >
                        Tiếp nhận ẩn danh
                    </Button>
                    <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={handleEmergencyWithInfo}
                    >
                        Tiếp nhận có thông tin
                    </Button>
                </div>
            </Modal>
        );
    }

    // ── NORMAL MODE ──────────────────────────────────────────
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
                    rules={[{ required: !showNewPatientForm, message: 'Vui lòng chọn bệnh nhân' }]}
                >
                    <AutoComplete
                        options={patientOptions}
                        onSearch={handlePatientSearch}
                        onSelect={handlePatientSelect}
                        placeholder="Nhập mã BN, tên, SĐT để tìm..."
                        value={searchPatient}
                        onChange={setSearchPatient}
                        suffixIcon={<SearchOutlined />}
                    />
                </Form.Item>

                {/* No results → show create button */}
                {searchDone && patientOptions.length === 0 && searchPatient.length >= 2 && !showNewPatientForm && !selectedPatient && (
                    <Alert
                        type="info"
                        showIcon
                        className="mb-4"
                        message="Không tìm thấy bệnh nhân"
                        action={
                            <Button
                                type="primary"
                                size="small"
                                icon={<UserAddOutlined />}
                                onClick={() => setShowNewPatientForm(true)}
                            >
                                Thêm bệnh nhân mới
                            </Button>
                        }
                    />
                )}

                {/* Inline new patient form */}
                {showNewPatientForm && !selectedPatient && (
                    <Card
                        size="small"
                        className="mb-4 border-green-300 bg-green-50"
                        title={
                            <span className="text-green-700">
                                <UserAddOutlined className="mr-2" />
                                Thêm bệnh nhân mới
                            </span>
                        }
                        extra={
                            <Button size="small" onClick={() => setShowNewPatientForm(false)}>
                                Hủy
                            </Button>
                        }
                    >
                        <Form form={newPatientForm} layout="vertical" size="small">
                            <div className="grid grid-cols-2 gap-x-4">
                                <Form.Item
                                    name="last_name"
                                    label="Họ"
                                    rules={[{ required: true, message: 'Bắt buộc' }]}
                                >
                                    <Input placeholder="VD: Nguyễn" />
                                </Form.Item>
                                <Form.Item
                                    name="first_name"
                                    label="Tên"
                                    rules={[{ required: true, message: 'Bắt buộc' }]}
                                >
                                    <Input placeholder="VD: Văn A" />
                                </Form.Item>
                                <Form.Item name="date_of_birth" label="Ngày sinh">
                                    <DatePicker className="w-full" format="DD/MM/YYYY" placeholder="DD/MM/YYYY" />
                                </Form.Item>
                                <Form.Item
                                    name="gender"
                                    label="Giới tính"
                                    initialValue="O"
                                >
                                    <Select>
                                        <Select.Option value="M">Nam</Select.Option>
                                        <Select.Option value="F">Nữ</Select.Option>
                                        <Select.Option value="O">Khác</Select.Option>
                                    </Select>
                                </Form.Item>
                                <Form.Item name="contact_number" label="SĐT">
                                    <Input placeholder="Số điện thoại" />
                                </Form.Item>
                                <Form.Item name="id_card" label="CCCD/CMND">
                                    <Input placeholder="Số CCCD" />
                                </Form.Item>
                            </div>
                            <Button
                                type="primary"
                                icon={<PlusOutlined />}
                                onClick={handleCreatePatient}
                                loading={creatingPatient}
                                block
                            >
                                Tạo bệnh nhân & chọn
                            </Button>
                        </Form>
                    </Card>
                )}

                {/* Selected patient card */}
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

                <Divider className="my-3" />

                <div className="flex justify-end gap-2">
                    <Button onClick={handleClose}>Hủy</Button>
                    <Button type="primary" htmlType="submit" icon={<PlusOutlined />}>
                        Tiếp nhận
                    </Button>
                </div>
            </Form>
        </Modal>
    );
}
