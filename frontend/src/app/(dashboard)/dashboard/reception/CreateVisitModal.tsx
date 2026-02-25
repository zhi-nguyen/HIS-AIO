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
    Table,
    Tag,
} from 'antd';
import {
    PlusOutlined,
    UserAddOutlined,
    AlertOutlined,
    SearchOutlined,
    IdcardOutlined,
    CheckCircleOutlined,
    ExclamationCircleOutlined,
} from '@ant-design/icons';
import { visitApi, patientApi, insuranceApi, type InsuranceLookupResult } from '@/lib/services';
import type { Patient } from '@/types';
import dayjs from 'dayjs';

const { Text } = Typography;

interface CreateVisitModalProps {
    open: boolean;
    onClose: () => void;
    onSuccess: () => void;
    emergencyMode?: boolean;
}

// ── Helpers ────────────────────────────────────────────────────
function splitVietnameseName(fullName: string): { lastName: string; firstName: string } {
    const parts = fullName.trim().split(/\s+/);
    if (parts.length <= 1) return { lastName: '', firstName: parts[0] || '' };
    const firstName = parts[parts.length - 1];
    const lastName = parts.slice(0, -1).join(' ');
    return { lastName, firstName };
}

function toTitleCase(str: string): string {
    return str
        .toLowerCase()
        .split(' ')
        .map(w => w.charAt(0).toUpperCase() + w.slice(1))
        .join(' ');
}

function mapGovGender(g: string): 'M' | 'F' | 'O' {
    if (g === 'male') return 'M';
    if (g === 'female') return 'F';
    return 'O';
}

// ── Types for CCCD scan state ──────────────────────────────────
interface GovData {
    fullName: string;
    firstName: string;
    lastName: string;
    dob: string | null;
    gender: 'M' | 'F' | 'O';
    address: string;
    insuranceCode: string;
    benefitRate: number;
    registeredHospital: string;
    cardExpire: string;
    status: 'success' | 'expired';
}

interface DiffField {
    field: string;
    label: string;
    gov: string;
    hospital: string;
    differs: boolean;
}

export default function CreateVisitModal({ open, onClose, onSuccess, emergencyMode = false }: CreateVisitModalProps) {
    const { message, modal } = App.useApp();
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

    // ── CCCD scan state ────────────────────────────────────────
    const [cccdInput, setCccdInput] = useState('');
    const [cccdLoading, setCccdLoading] = useState(false);
    const [govData, setGovData] = useState<GovData | null>(null);
    const [hospitalPatient, setHospitalPatient] = useState<Patient | null>(null);
    const [showDiffModal, setShowDiffModal] = useState(false);
    const [diffFields, setDiffFields] = useState<DiffField[]>([]);
    const [cccdScanned, setCccdScanned] = useState(false);

    // ── CCCD Scan Handler ──────────────────────────────────────
    const handleCccdScan = useCallback(async () => {
        const cccd = cccdInput.trim();
        if (!/^\d{12}$/.test(cccd)) {
            message.warning('CCCD phải là 12 chữ số');
            return;
        }

        setCccdLoading(true);
        setGovData(null);
        setHospitalPatient(null);
        setCccdScanned(false);

        try {
            // 1. Query government portal (insurance_mock)
            const govResult: InsuranceLookupResult = await insuranceApi.lookup(cccd);

            if (govResult.status === 'not_found' || !govResult.data) {
                message.warning('Không tìm thấy thông tin công dân trên cổng Chính phủ');
                setCccdLoading(false);
                return;
            }

            const { lastName, firstName } = splitVietnameseName(govResult.data.patient_name);
            const parsed: GovData = {
                fullName: toTitleCase(govResult.data.patient_name),
                firstName: toTitleCase(firstName),
                lastName: toTitleCase(lastName),
                dob: govResult.data.dob || null,
                gender: mapGovGender(govResult.data.gender),
                address: govResult.data.address,
                insuranceCode: govResult.data.insurance_code,
                benefitRate: govResult.data.benefit_rate,
                registeredHospital: govResult.data.registered_hospital_name,
                cardExpire: govResult.data.card_expire_date,
                status: govResult.status as 'success' | 'expired',
            };
            setGovData(parsed);

            if (govResult.status === 'expired') {
                message.warning('Thẻ BHYT đã hết hạn!');
            }

            // 2. Search hospital database by CCCD
            let existingPatient: Patient | null = null;
            try {
                const patients = await patientApi.search(cccd);
                existingPatient = patients.find(p => p.id_card === cccd) || null;
            } catch {
                // No results
            }

            setCccdScanned(true);

            if (existingPatient) {
                setHospitalPatient(existingPatient);

                // 3. Compare gov data vs hospital data
                const diffs: DiffField[] = [
                    {
                        field: 'name', label: 'Họ tên',
                        gov: parsed.fullName,
                        hospital: existingPatient.full_name || `${existingPatient.last_name} ${existingPatient.first_name}`,
                        differs: false,
                    },
                    {
                        field: 'dob', label: 'Ngày sinh',
                        gov: parsed.dob ? dayjs(parsed.dob).format('DD/MM/YYYY') : '—',
                        hospital: existingPatient.date_of_birth ? dayjs(existingPatient.date_of_birth).format('DD/MM/YYYY') : '—',
                        differs: false,
                    },
                    {
                        field: 'gender', label: 'Giới tính',
                        gov: parsed.gender === 'M' ? 'Nam' : parsed.gender === 'F' ? 'Nữ' : 'Khác',
                        hospital: existingPatient.gender === 'M' ? 'Nam' : existingPatient.gender === 'F' ? 'Nữ' : 'Khác',
                        differs: false,
                    },
                    {
                        field: 'address', label: 'Địa chỉ',
                        gov: parsed.address,
                        hospital: existingPatient.full_address || existingPatient.address_detail || '—',
                        differs: false,
                    },
                    {
                        field: 'insurance', label: 'Mã BHYT',
                        gov: parsed.insuranceCode,
                        hospital: existingPatient.insurance_number || '—',
                        differs: false,
                    },
                ];

                // Check diffs (case-insensitive, trimmed)
                const normalize = (s: string) => s.toLowerCase().replace(/\s+/g, ' ').trim();
                diffs[0].differs = normalize(diffs[0].gov) !== normalize(diffs[0].hospital);
                diffs[1].differs = diffs[1].gov !== diffs[1].hospital;
                diffs[2].differs = diffs[2].gov !== diffs[2].hospital;
                diffs[3].differs = normalize(diffs[3].gov) !== normalize(diffs[3].hospital);
                diffs[4].differs = normalize(diffs[4].gov) !== normalize(diffs[4].hospital);

                const hasDiff = diffs.some(d => d.differs);

                if (hasDiff) {
                    setDiffFields(diffs);
                    setShowDiffModal(true);
                } else {
                    message.success('Tìm thấy hồ sơ bệnh viện — thông tin trùng khớp ✓');
                    setSelectedPatient(existingPatient);
                    if (!emergencyMode) {
                        form.setFieldValue('patient', existingPatient.id);
                    }
                }
            } else {
                // New patient — auto-fill form
                message.success('Đã nhận thông tin từ Cổng Chính Phủ — bệnh nhân mới');
                if (emergencyMode) {
                    newPatientForm.setFieldsValue({
                        last_name: parsed.lastName,
                        first_name: parsed.firstName,
                        gender: parsed.gender,
                        date_of_birth: parsed.dob ? dayjs(parsed.dob) : undefined,
                        id_card: cccd,
                    });
                } else {
                    setShowNewPatientForm(true);
                    // Wait for form to render, then fill
                    setTimeout(() => {
                        newPatientForm.setFieldsValue({
                            last_name: parsed.lastName,
                            first_name: parsed.firstName,
                            gender: parsed.gender,
                            date_of_birth: parsed.dob ? dayjs(parsed.dob) : undefined,
                            contact_number: undefined,
                            id_card: cccd,
                        });
                    }, 100);
                }
            }
        } catch (error) {
            console.error('CCCD scan failed:', error);
            message.error('Lỗi khi truy vấn thông tin CCCD');
        } finally {
            setCccdLoading(false);
        }
    }, [cccdInput, message, emergencyMode, newPatientForm, form]);

    // ── Overwrite patient with gov data ────────────────────────
    const handleOverwritePatient = useCallback(async () => {
        if (!hospitalPatient || !govData) return;
        try {
            const updated = await patientApi.update(hospitalPatient.id, {
                first_name: govData.firstName,
                last_name: govData.lastName,
                gender: govData.gender,
                date_of_birth: govData.dob || undefined,
                address_detail: govData.address,
                insurance_number: govData.insuranceCode,
            });
            message.success('Đã cập nhật hồ sơ bệnh viện theo thông tin căn cước');
            setSelectedPatient(updated);
            setShowDiffModal(false);
            if (!emergencyMode) {
                form.setFieldValue('patient', updated.id);
            }
        } catch {
            message.error('Không thể cập nhật hồ sơ');
        }
    }, [hospitalPatient, govData, message, form, emergencyMode]);

    // ── Keep hospital data (no overwrite) ──────────────────────
    const handleKeepHospitalData = useCallback(() => {
        if (!hospitalPatient) return;
        setSelectedPatient(hospitalPatient);
        setShowDiffModal(false);
        if (!emergencyMode) {
            form.setFieldValue('patient', hospitalPatient.id);
        }
        message.info('Giữ nguyên thông tin bệnh viện');
    }, [hospitalPatient, form, emergencyMode, message]);

    // ── Patient search (normal mode) ───────────────────────────
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
            } catch {
                console.error('Error searching patients');
            }
        }, 400);
    }, []);

    const handlePatientSelect = (value: string, option: { patient: Patient }) => {
        setSelectedPatient(option.patient);
        setShowNewPatientForm(false);
        form.setFieldValue('patient', value);
    };

    // ── Create patient inline (normal mode) ────────────────────
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

    // ── Emergency: anonymous patient ───────────────────────────
    const handleEmergencySubmit = async () => {
        try {
            const anonPatient = await patientApi.create({
                first_name: 'Cấp cứu',
                last_name: `BN-${Date.now().toString(36).toUpperCase()}`,
                gender: 'O' as Patient['gender'],
                is_anonymous: true,
            } as Partial<Patient>);

            await visitApi.create({
                patient: anonPatient.id,
                priority: 'EMERGENCY',
                pending_merge: true,
            });

            message.success('Đã tiếp nhận cấp cứu! Bệnh nhân ẩn danh, chờ gộp hồ sơ');
            handleClose();
            onSuccess();
        } catch {
            message.error('Không thể tiếp nhận cấp cứu');
        }
    };

    // ── Emergency: with info ───────────────────────────────────
    const handleEmergencyWithInfo = async () => {
        try {
            let patient: Patient;

            // If patient was selected via CCCD scan
            if (selectedPatient) {
                patient = selectedPatient;
            } else {
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

                patient = await patientApi.create(patientData as Partial<Patient>);
            }

            await visitApi.create({
                patient: patient.id,
                priority: 'EMERGENCY',
                pending_merge: patient.is_anonymous || false,
            });

            message.success(
                patient.is_anonymous
                    ? 'Tiếp nhận cấp cứu ẩn danh, chờ gộp hồ sơ'
                    : `Tiếp nhận cấp cứu: ${patient.full_name || `${patient.last_name} ${patient.first_name}`}`
            );
            handleClose();
            onSuccess();
        } catch {
            message.error('Không thể tiếp nhận cấp cứu');
        }
    };

    // ── Normal submit ──────────────────────────────────────────
    const handleSubmit = async (values: { patient: string; priority?: string }) => {
        try {
            await visitApi.create({
                patient: values.patient,
                priority: values.priority,
            });
            message.success('Tiếp nhận bệnh nhân thành công!');
            handleClose();
            onSuccess();
        } catch {
            message.error('Không thể tạo lượt khám');
        }
    };

    const handleClose = () => {
        setSelectedPatient(null);
        setSearchPatient('');
        setShowNewPatientForm(false);
        setSearchDone(false);
        setCccdInput('');
        setGovData(null);
        setHospitalPatient(null);
        setCccdScanned(false);
        setShowDiffModal(false);
        setDiffFields([]);
        form.resetFields();
        newPatientForm.resetFields();
        onClose();
    };

    // ── CCCD Scan Section (shared between modes) ───────────────
    const CccdScanSection = (
        <Card
            size="small"
            className="mb-4"
            style={{ border: '1px solid #1677ff', background: '#f0f5ff' }}
            title={
                <span style={{ color: '#1677ff' }}>
                    <IdcardOutlined className="mr-2" />
                    Quét Căn cước công dân
                </span>
            }
        >
            <div className="flex gap-2">
                <Input
                    value={cccdInput}
                    onChange={(e) => setCccdInput(e.target.value)}
                    placeholder="Nhập số CCCD (12 chữ số)"
                    maxLength={12}
                    onPressEnter={handleCccdScan}
                    prefix={<IdcardOutlined />}
                    style={{ flex: 1 }}
                    disabled={cccdLoading}
                />
                <Button
                    type="primary"
                    icon={<SearchOutlined />}
                    onClick={handleCccdScan}
                    loading={cccdLoading}
                >
                    Tra cứu
                </Button>
            </div>

            {/* Gov data result */}
            {govData && cccdScanned && (
                <div className="mt-3">
                    <Alert
                        type={govData.status === 'expired' ? 'warning' : 'success'}
                        showIcon
                        icon={govData.status === 'expired' ? <ExclamationCircleOutlined /> : <CheckCircleOutlined />}
                        message={
                            <span>
                                <strong>Cổng Chính phủ:</strong> {govData.fullName}
                                {govData.status === 'expired' && <Tag color="red" className="ml-2">BHYT hết hạn</Tag>}
                            </span>
                        }
                        description={
                            <Descriptions size="small" column={2} className="mt-2">
                                <Descriptions.Item label="Ngày sinh">
                                    {govData.dob ? dayjs(govData.dob).format('DD/MM/YYYY') : '—'}
                                </Descriptions.Item>
                                <Descriptions.Item label="Giới tính">
                                    {govData.gender === 'M' ? 'Nam' : govData.gender === 'F' ? 'Nữ' : 'Khác'}
                                </Descriptions.Item>
                                <Descriptions.Item label="Địa chỉ" span={2}>{govData.address}</Descriptions.Item>
                                <Descriptions.Item label="BHYT">{govData.insuranceCode}</Descriptions.Item>
                                <Descriptions.Item label="Mức hưởng">{govData.benefitRate}%</Descriptions.Item>
                                <Descriptions.Item label="BV ĐKBĐ" span={2}>{govData.registeredHospital}</Descriptions.Item>
                            </Descriptions>
                        }
                    />

                    {/* Show match status */}
                    {hospitalPatient && !showDiffModal && selectedPatient && (
                        <Alert
                            type="info"
                            showIcon
                            icon={<CheckCircleOutlined />}
                            className="mt-2"
                            message={`Đã có hồ sơ bệnh viện: ${selectedPatient.patient_code} — ${selectedPatient.full_name}`}
                        />
                    )}
                </div>
            )}
        </Card>
    );

    // ── DIFF COMPARISON MODAL ──────────────────────────────────
    const DiffModal = (
        <Modal
            title={
                <span style={{ color: '#ff4d4f' }}>
                    <ExclamationCircleOutlined className="mr-2" />
                    Thông tin khác biệt giữa Căn cước và Hồ sơ Bệnh viện
                </span>
            }
            open={showDiffModal}
            onCancel={() => { setShowDiffModal(false); }}
            width={650}
            footer={
                <div className="flex justify-end gap-2">
                    <Button onClick={() => { setShowDiffModal(false); }}>
                        Hủy
                    </Button>
                    <Button onClick={handleKeepHospitalData}>
                        Giữ thông tin BV
                    </Button>
                    <Button type="primary" danger onClick={handleOverwritePatient}>
                        Ghi đè bằng Căn cước
                    </Button>
                </div>
            }
        >
            <Alert
                type="warning"
                showIcon
                className="mb-4"
                message="Thông tin bệnh nhân trên Căn cước công dân KHÁC với hồ sơ đang lưu tại bệnh viện"
                description="Bạn có muốn ghi đè thông tin bệnh viện bằng thông tin trên Căn cước? Nếu không, bệnh nhân sẽ được tiếp nhận với thông tin hiện tại của bệnh viện."
            />
            <Table
                dataSource={diffFields}
                pagination={false}
                size="small"
                rowKey="field"
                columns={[
                    {
                        title: 'Thông tin',
                        dataIndex: 'label',
                        width: 100,
                        render: (text: string, record: DiffField) => (
                            <Text strong style={record.differs ? { color: '#ff4d4f' } : undefined}>
                                {text} {record.differs && '⚠'}
                            </Text>
                        ),
                    },
                    {
                        title: '📛 Căn cước (Chính phủ)',
                        dataIndex: 'gov',
                        render: (text: string, record: DiffField) => (
                            <Text style={record.differs ? { color: '#52c41a', fontWeight: 600 } : undefined}>
                                {text}
                            </Text>
                        ),
                    },
                    {
                        title: '🏥 Hồ sơ Bệnh viện',
                        dataIndex: 'hospital',
                        render: (text: string, record: DiffField) => (
                            <Text style={record.differs ? { color: '#ff4d4f', fontWeight: 600 } : undefined}>
                                {text}
                            </Text>
                        ),
                    },
                ]}
            />
        </Modal>
    );

    // ── Patient form fields (shared) ───────────────────────────
    const PatientFormFields = (
        <div className="grid grid-cols-2 gap-x-4">
            <Form.Item name="last_name" label="Họ" rules={[{ required: true, message: 'Vui lòng nhập Họ' }]}>
                <Input placeholder="VD: Nguyễn" />
            </Form.Item>
            <Form.Item name="first_name" label="Tên" rules={[{ required: true, message: 'Vui lòng nhập Tên' }]}>
                <Input placeholder="VD: Văn A" />
            </Form.Item>
            <Form.Item name="date_of_birth" label="Ngày sinh">
                <DatePicker className="w-full" format="DD/MM/YYYY" placeholder="DD/MM/YYYY" />
            </Form.Item>
            <Form.Item name="gender" label="Giới tính" initialValue="O">
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
                <Input placeholder="Số CCCD" disabled={cccdScanned} />
            </Form.Item>
        </div>
    );

    // ══════════════════════════════════════════════════════════
    // EMERGENCY MODE
    // ══════════════════════════════════════════════════════════
    if (emergencyMode) {
        return (
            <>
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
                    width={650}
                >
                    {/* CCCD Scan */}
                    {CccdScanSection}

                    {/* Patient already matched via CCCD */}
                    {selectedPatient && (
                        <Card size="small" className="mb-4 bg-blue-50">
                            <Descriptions size="small" column={2}>
                                <Descriptions.Item label="Mã BN">{selectedPatient.patient_code}</Descriptions.Item>
                                <Descriptions.Item label="Họ tên">
                                    {selectedPatient.full_name || `${selectedPatient.last_name} ${selectedPatient.first_name}`}
                                </Descriptions.Item>
                                <Descriptions.Item label="Ngày sinh">
                                    {selectedPatient.date_of_birth ? dayjs(selectedPatient.date_of_birth).format('DD/MM/YYYY') : '—'}
                                </Descriptions.Item>
                                <Descriptions.Item label="CCCD">{selectedPatient.id_card || '—'}</Descriptions.Item>
                            </Descriptions>
                        </Card>
                    )}

                    {/* Manual form (hidden when patient is matched) */}
                    {!selectedPatient && (
                        <>
                            <Divider plain className="text-xs text-gray-400">hoặc nhập thủ công</Divider>
                            <Form form={newPatientForm} layout="vertical">
                                {PatientFormFields}
                            </Form>
                        </>
                    )}

                    <div className="flex justify-end gap-2 mt-4">
                        <Button onClick={handleClose}>Hủy</Button>
                        {!selectedPatient && (
                            <Button
                                danger
                                type="primary"
                                icon={<AlertOutlined />}
                                onClick={handleEmergencySubmit}
                            >
                                Tiếp nhận ẩn danh
                            </Button>
                        )}
                        <Button
                            type="primary"
                            icon={<PlusOutlined />}
                            onClick={handleEmergencyWithInfo}
                        >
                            {selectedPatient ? 'Tiếp nhận cấp cứu' : 'Tiếp nhận có thông tin'}
                        </Button>
                    </div>
                </Modal>
                {DiffModal}
            </>
        );
    }

    // ══════════════════════════════════════════════════════════
    // NORMAL MODE
    // ══════════════════════════════════════════════════════════
    return (
        <>
            <Modal
                title="Tiếp nhận bệnh nhân"
                open={open}
                onCancel={handleClose}
                footer={null}
                width={650}
            >
                {/* CCCD Scan */}
                {CccdScanSection}

                <Form form={form} layout="vertical" onFinish={handleSubmit} className="mt-4">
                    {/* Patient search (manual) */}
                    {!selectedPatient && (
                        <Form.Item
                            name="patient"
                            label="Tìm bệnh nhân"
                            rules={[{ required: !showNewPatientForm && !selectedPatient, message: 'Vui lòng chọn bệnh nhân' }]}
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
                    )}

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
                                {PatientFormFields}
                                <Button
                                    type="primary"
                                    icon={<PlusOutlined />}
                                    onClick={handleCreatePatient}
                                    loading={creatingPatient}
                                    block
                                >
                                    Tạo bệnh nhân &amp; chọn
                                </Button>
                            </Form>
                        </Card>
                    )}

                    {/* Selected patient card */}
                    {selectedPatient && (
                        <Card size="small" className="mb-4 bg-blue-50">
                            <div className="flex justify-between items-start">
                                <Descriptions size="small" column={2}>
                                    <Descriptions.Item label="Mã BN">{selectedPatient.patient_code}</Descriptions.Item>
                                    <Descriptions.Item label="Họ tên">
                                        {selectedPatient.full_name || `${selectedPatient.last_name} ${selectedPatient.first_name}`}
                                    </Descriptions.Item>
                                    <Descriptions.Item label="Ngày sinh">
                                        {selectedPatient.date_of_birth ? dayjs(selectedPatient.date_of_birth).format('DD/MM/YYYY') : '—'}
                                    </Descriptions.Item>
                                    <Descriptions.Item label="SĐT">{selectedPatient.contact_number || '—'}</Descriptions.Item>
                                </Descriptions>
                                <Button
                                    size="small"
                                    type="link"
                                    danger
                                    onClick={() => {
                                        setSelectedPatient(null);
                                        form.setFieldValue('patient', undefined);
                                    }}
                                >
                                    Bỏ chọn
                                </Button>
                            </div>
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
            {DiffModal}
        </>
    );
}
