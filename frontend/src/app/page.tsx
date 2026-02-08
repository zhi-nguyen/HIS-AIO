import {
  MedicineBoxOutlined,
  PhoneOutlined,
  EnvironmentOutlined,
  ClockCircleOutlined,
  HeartOutlined,
  ExperimentOutlined,
  ScanOutlined,
  UserOutlined,
  CalendarOutlined,
} from '@ant-design/icons';
import Link from 'next/link';
import PatientChatbot from '@/components/patient/PatientChatbot';

/**
 * Public Homepage - Trang chủ công khai cho bệnh nhân
 * Giống các trang web bệnh viện thực tế
 */

export default function HomePage() {
  return (
    <div className="min-h-screen bg-white">
      {/* Header / Navigation */}
      <header className="bg-white shadow-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <MedicineBoxOutlined className="text-3xl text-blue-600" />
            <div>
              <h1 className="text-xl font-bold text-gray-800">Bệnh Viện Đa Khoa ABC</h1>
              <p className="text-xs text-gray-500">Chăm sóc sức khỏe - Tận tâm phục vụ</p>
            </div>
          </div>
          <nav className="hidden md:flex items-center gap-6">
            <Link href="/" className="text-gray-700 hover:text-blue-600">Trang chủ</Link>
            <Link href="#services" className="text-gray-700 hover:text-blue-600">Dịch vụ</Link>
            <Link href="#doctors" className="text-gray-700 hover:text-blue-600">Bác sĩ</Link>
            <Link href="#contact" className="text-gray-700 hover:text-blue-600">Liên hệ</Link>
            <Link href="/login" className="bg-blue-600 text-white px-4 py-2 rounded-full hover:bg-blue-700 transition">
              Đăng nhập
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="bg-gradient-to-br from-blue-600 via-blue-500 to-cyan-400 text-white py-20">
        <div className="max-w-7xl mx-auto px-4 grid md:grid-cols-2 gap-12 items-center">
          <div>
            <h2 className="text-4xl md:text-5xl font-bold mb-6">
              Chăm Sóc Sức Khỏe<br />
              <span className="text-cyan-200">Toàn Diện & Tận Tâm</span>
            </h2>
            <p className="text-lg text-blue-100 mb-8">
              Đội ngũ bác sĩ chuyên khoa giỏi, trang thiết bị hiện đại,
              phục vụ 24/7 để mang đến dịch vụ y tế chất lượng cao nhất cho bạn và gia đình.
            </p>
            <div className="flex gap-4">
              <Link href="#booking" className="bg-white text-blue-600 px-8 py-3 rounded-full font-semibold hover:bg-blue-50 transition shadow-lg">
                <CalendarOutlined className="mr-2" />
                Đặt lịch khám
              </Link>
              <Link href="tel:19001234" className="border-2 border-white text-white px-8 py-3 rounded-full font-semibold hover:bg-white/10 transition">
                <PhoneOutlined className="mr-2" />
                1900 1234
              </Link>
            </div>
          </div>
          <div className="hidden md:block">
            <div className="bg-white/10 backdrop-blur rounded-3xl p-8 border border-white/20">
              <div className="grid grid-cols-2 gap-4">
                <InfoCard icon={<UserOutlined />} number="50+" label="Bác sĩ chuyên khoa" />
                <InfoCard icon={<HeartOutlined />} number="20+" label="Chuyên khoa" />
                <InfoCard icon={<ClockCircleOutlined />} number="24/7" label="Phục vụ liên tục" />
                <InfoCard icon={<CalendarOutlined />} number="100K+" label="Bệnh nhân/năm" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Services Section */}
      <section id="services" className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4">
          <div className="text-center mb-12">
            <h3 className="text-3xl font-bold text-gray-800 mb-4">Dịch Vụ Y Tế</h3>
            <p className="text-gray-600 max-w-2xl mx-auto">
              Cung cấp đầy đủ các dịch vụ khám chữa bệnh với trang thiết bị hiện đại
            </p>
          </div>
          <div className="grid md:grid-cols-3 lg:grid-cols-4 gap-6">
            <ServiceCard icon={<HeartOutlined />} title="Nội khoa" desc="Khám và điều trị các bệnh lý nội khoa" />
            <ServiceCard icon={<MedicineBoxOutlined />} title="Ngoại khoa" desc="Phẫu thuật và can thiệp ngoại khoa" />
            <ServiceCard icon={<ExperimentOutlined />} title="Xét nghiệm" desc="Xét nghiệm máu, nước tiểu, sinh hóa" />
            <ServiceCard icon={<ScanOutlined />} title="Chẩn đoán HA" desc="X-quang, CT, MRI, siêu âm" />
            <ServiceCard icon={<UserOutlined />} title="Sản phụ khoa" desc="Chăm sóc sức khỏe phụ nữ" />
            <ServiceCard icon={<HeartOutlined />} title="Nhi khoa" desc="Khám và chăm sóc trẻ em" />
            <ServiceCard icon={<MedicineBoxOutlined />} title="Răng hàm mặt" desc="Điều trị các bệnh lý răng miệng" />
            <ServiceCard icon={<HeartOutlined />} title="Tim mạch" desc="Khám và điều trị bệnh tim" />
          </div>
        </div>
      </section>

      {/* Contact Section */}
      <section id="contact" className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4">
          <div className="grid md:grid-cols-3 gap-8">
            <ContactCard
              icon={<EnvironmentOutlined className="text-3xl text-blue-600" />}
              title="Địa chỉ"
              content="123 Đường ABC, Quận XYZ, TP. Hồ Chí Minh"
            />
            <ContactCard
              icon={<PhoneOutlined className="text-3xl text-blue-600" />}
              title="Hotline"
              content="1900 1234 (24/7)"
            />
            <ContactCard
              icon={<ClockCircleOutlined className="text-3xl text-blue-600" />}
              title="Giờ làm việc"
              content="Thứ 2 - CN: 7:00 - 20:00"
            />
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <div className="flex items-center justify-center gap-3 mb-4">
            <MedicineBoxOutlined className="text-2xl text-blue-400" />
            <span className="text-xl font-bold">Bệnh Viện Đa Khoa ABC</span>
          </div>
          <p className="text-gray-400 mb-6">
            © 2024 Bệnh Viện Đa Khoa ABC. Tất cả quyền được bảo lưu.
          </p>
          <div className="flex justify-center gap-6 text-gray-400">
            <Link href="#" className="hover:text-white">Chính sách bảo mật</Link>
            <Link href="#" className="hover:text-white">Điều khoản sử dụng</Link>
            <Link href="#" className="hover:text-white">Liên hệ</Link>
          </div>
        </div>
      </footer>

      {/* AI Chatbot */}
      <PatientChatbot />
    </div>
  );
}

// Components
function InfoCard({ icon, number, label }: { icon: React.ReactNode; number: string; label: string }) {
  return (
    <div className="bg-white/10 rounded-xl p-4 text-center">
      <div className="text-2xl mb-2">{icon}</div>
      <div className="text-2xl font-bold">{number}</div>
      <div className="text-sm text-blue-100">{label}</div>
    </div>
  );
}

function ServiceCard({ icon, title, desc }: { icon: React.ReactNode; title: string; desc: string }) {
  return (
    <div className="bg-white p-6 rounded-2xl shadow-sm hover:shadow-lg transition group cursor-pointer border border-gray-100">
      <div className="w-14 h-14 bg-blue-100 rounded-xl flex items-center justify-center text-blue-600 text-2xl mb-4 group-hover:bg-blue-600 group-hover:text-white transition">
        {icon}
      </div>
      <h4 className="font-semibold text-gray-800 mb-2">{title}</h4>
      <p className="text-sm text-gray-500">{desc}</p>
    </div>
  );
}

function ContactCard({ icon, title, content }: { icon: React.ReactNode; title: string; content: string }) {
  return (
    <div className="text-center p-8 rounded-2xl bg-gray-50 hover:bg-blue-50 transition">
      {icon}
      <h4 className="font-semibold text-gray-800 mt-4 mb-2">{title}</h4>
      <p className="text-gray-600">{content}</p>
    </div>
  );
}
