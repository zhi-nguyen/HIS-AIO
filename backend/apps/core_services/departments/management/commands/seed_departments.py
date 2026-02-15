"""
Management command: Chèn dữ liệu Khoa Phòng mẫu.

Dành cho bệnh viện đa khoa hạng I (25+ khoa phòng).
Mỗi khoa bao gồm: code, tên, mô tả, chuyên khoa, triệu chứng điển hình
để AI triage agent có thể chỉ định chính xác.

Usage:
    python manage.py seed_departments
    python manage.py seed_departments --clear   # Xóa hết rồi chèn lại
"""

from django.core.management.base import BaseCommand
from apps.core_services.departments.models import Department


# =============================================================================
# DỮ LIỆU KHOA PHÒNG MẪU
# =============================================================================

DEPARTMENTS_DATA = [
    # ===================== KHOA CẤP CỨU =====================
    {
        "code": "CC",
        "name": "Khoa Cấp Cứu",
        "description": (
            "Tiếp nhận, xử trí ban đầu các trường hợp cấp cứu nội - ngoại khoa. "
            "Hoạt động 24/7, có phòng hồi sức, phòng thủ thuật, phòng theo dõi."
        ),
        "specialties": "Cấp cứu nội khoa, Cấp cứu ngoại khoa, Hồi sức, Chống độc",
        "typical_symptoms": (
            "Ngừng tim, ngừng thở, sốc, đa chấn thương, bỏng nặng, ngộ độc, "
            "co giật liên tục, hôn mê, chảy máu ồ ạt, đau ngực cấp, khó thở cấp, "
            "tai nạn giao thông, đột quỵ, sốc phản vệ"
        ),
    },
    # ===================== KHỐI NỘI KHOA =====================
    {
        "code": "NOI_TQ",
        "name": "Khoa Nội Tổng Quát",
        "description": (
            "Khám, chẩn đoán và điều trị các bệnh nội khoa tổng quát. "
            "Tiếp nhận bệnh nhân chưa xác định rõ chuyên khoa."
        ),
        "specialties": "Nội tổng quát, Bệnh nhiễm trùng, Bệnh tự miễn, Dị ứng",
        "typical_symptoms": (
            "Sốt kéo dài, mệt mỏi, sụt cân không rõ nguyên nhân, đau nhức toàn thân, "
            "thiếu máu, phù, dị ứng, nổi ban, ngứa toàn thân, rối loạn điện giải"
        ),
    },
    {
        "code": "NOI_TM",
        "name": "Khoa Nội Tim Mạch",
        "description": (
            "Chuyên chẩn đoán, điều trị các bệnh lý tim mạch. "
            "Có phòng can thiệp tim mạch, phòng siêu âm tim, Holter monitor."
        ),
        "specialties": "Tim mạch, Mạch vành, Tăng huyết áp, Rối loạn nhịp tim, Suy tim, Bệnh van tim",
        "typical_symptoms": (
            "Đau ngực, tức ngực, khó thở khi gắng sức, hồi hộp đánh trống ngực, "
            "phù chân, tăng huyết áp, hạ huyết áp, ngất xỉu, rối loạn nhịp tim, "
            "đau thắt ngực, tim đập nhanh, tim đập chậm"
        ),
    },
    {
        "code": "NOI_TH",
        "name": "Khoa Nội Tiêu Hóa",
        "description": (
            "Chẩn đoán, điều trị bệnh lý đường tiêu hóa và gan mật. "
            "Có phòng nội soi tiêu hóa trên, dưới."
        ),
        "specialties": "Tiêu hóa, Gan mật, Nội soi tiêu hóa, Bệnh dạ dày, Bệnh đại tràng",
        "typical_symptoms": (
            "Đau bụng, đau thượng vị, ợ hơi, ợ chua, buồn nôn, nôn, tiêu chảy, "
            "táo bón, đi cầu ra máu, phân đen, vàng da, đau hạ sườn phải, "
            "chướng bụng, khó tiêu, trào ngược dạ dày, xuất huyết tiêu hóa"
        ),
    },
    {
        "code": "NOI_HH",
        "name": "Khoa Nội Hô Hấp",
        "description": (
            "Chẩn đoán, điều trị bệnh lý hô hấp - phổi. "
            "Có phòng đo chức năng hô hấp, phòng nội soi phế quản."
        ),
        "specialties": "Hô hấp, Phổi, Hen suyễn, COPD, Lao phổi, Viêm phổi",
        "typical_symptoms": (
            "Ho kéo dài, ho ra máu, khó thở, thở khò khè, đau ngực khi hít thở, "
            "sốt kèm ho, khạc đàm, tức ngực, thở nhanh, hen suyễn, "
            "viêm phế quản, viêm phổi, tràn dịch màng phổi"
        ),
    },
    {
        "code": "NOI_TK",
        "name": "Khoa Nội Thần Kinh",
        "description": (
            "Chẩn đoán, điều trị bệnh lý thần kinh trung ương và ngoại vi. "
            "Có phòng đo điện não (EEG), điện cơ (EMG)."
        ),
        "specialties": "Thần kinh, Đột quỵ, Động kinh, Parkinson, Đau đầu, Bệnh tủy sống",
        "typical_symptoms": (
            "Đau đầu dữ dội, chóng mặt, yếu liệt nửa người, tê bì tay chân, "
            "méo miệng, nói khó, mất ý thức, co giật, run tay, mất trí nhớ, "
            "đau dây thần kinh, mất thăng bằng, rối loạn giấc ngủ"
        ),
    },
    {
        "code": "NOI_NT",
        "name": "Khoa Nội Tiết",
        "description": (
            "Chẩn đoán, điều trị bệnh lý nội tiết - chuyển hóa. "
            "Quản lý bệnh nhân đái tháo đường, tuyến giáp."
        ),
        "specialties": "Nội tiết, Đái tháo đường, Tuyến giáp, Rối loạn lipid, Loãng xương",
        "typical_symptoms": (
            "Tiểu nhiều, khát nước nhiều, sụt cân nhanh, mệt mỏi kéo dài, "
            "bướu cổ, run tay, đổ mồ hôi nhiều, rối loạn kinh nguyệt, "
            "tăng cân bất thường, đường huyết cao, cholesterol cao"
        ),
    },
    # ===================== KHỐI NGOẠI KHOA =====================
    {
        "code": "NGOAI_TQ",
        "name": "Khoa Ngoại Tổng Quát",
        "description": (
            "Phẫu thuật các bệnh lý ngoại khoa tổng quát: ổ bụng, thành bụng, "
            "mạch máu ngoại vi. Có phòng mổ, phòng hậu phẫu."
        ),
        "specialties": "Ngoại tổng quát, Phẫu thuật bụng, Thoát vị, Ruột thừa, Sỏi mật",
        "typical_symptoms": (
            "Đau bụng dữ dội, đau hố chậu phải, bụng cứng, nôn mửa liên tục, "
            "sưng bẹn, khối u dưới da, áp xe, nhiễm trùng mô mềm, "
            "tắc ruột, viêm ruột thừa, sỏi mật"
        ),
    },
    {
        "code": "NGOAI_CT",
        "name": "Khoa Ngoại Chấn Thương Chỉnh Hình",
        "description": (
            "Phẫu thuật chấn thương, bệnh lý cơ xương khớp. "
            "Có phòng bó bột, phòng mổ chỉnh hình, phục hồi chức năng."
        ),
        "specialties": "Chấn thương, Chỉnh hình, Cột sống, Khớp, Thay khớp, Bàn tay",
        "typical_symptoms": (
            "Gãy xương, trật khớp, đau khớp, sưng khớp, biến dạng chi, "
            "đau lưng, đau cổ, thoát vị đĩa đệm, chấn thương thể thao, "
            "không cử động được tay chân, bong gân, rách dây chằng"
        ),
    },
    {
        "code": "NGOAI_TK",
        "name": "Khoa Ngoại Thần Kinh",
        "description": (
            "Phẫu thuật bệnh lý hệ thần kinh: sọ não, cột sống, thần kinh ngoại vi."
        ),
        "specialties": "Phẫu thuật sọ não, Phẫu thuật cột sống, U não, Chấn thương sọ não",
        "typical_symptoms": (
            "Chấn thương đầu nặng, vỡ sọ, máu tụ nội sọ, u não, đau đầu dữ dội kèm nôn, "
            "yếu liệt tiến triển, chèn ép tủy sống, thoát vị đĩa đệm nặng cần phẫu thuật"
        ),
    },
    # ===================== SẢN - NHI =====================
    {
        "code": "SAN",
        "name": "Khoa Sản",
        "description": (
            "Khám thai, theo dõi thai, đỡ đẻ, phẫu thuật sản khoa. "
            "Có phòng sanh, phòng mổ sản, phòng hậu sản."
        ),
        "specialties": "Sản khoa, Phụ khoa, Thai sản, Kế hoạch hóa gia đình",
        "typical_symptoms": (
            "Đau bụng khi mang thai, ra máu âm đạo, vỡ ối, chuyển dạ, "
            "kinh nguyệt bất thường, đau bụng kinh, khối u phụ khoa, "
            "khí hư bất thường, rối loạn kinh nguyệt, tiền sản giật"
        ),
    },
    {
        "code": "NHI",
        "name": "Khoa Nhi",
        "description": (
            "Khám, chẩn đoán và điều trị bệnh lý trẻ em (0-16 tuổi). "
            "Có khu sơ sinh, phòng cấp cứu nhi."
        ),
        "specialties": "Nhi khoa, Sơ sinh, Nhi hô hấp, Nhi tiêu hóa, Nhi thần kinh",
        "typical_symptoms": (
            "Trẻ sốt cao, co giật ở trẻ, trẻ bỏ bú, trẻ tiêu chảy, trẻ nôn ói, "
            "trẻ khó thở, phát ban ở trẻ, trẻ đau bụng, trẻ sụt cân, "
            "trẻ chậm phát triển, viêm phổi trẻ em, viêm tiểu phế quản"
        ),
    },
    # ===================== CHUYÊN KHOA LẺ =====================
    {
        "code": "TMH",
        "name": "Khoa Tai Mũi Họng",
        "description": (
            "Khám, chẩn đoán, phẫu thuật bệnh lý tai - mũi - họng - thanh quản. "
            "Có phòng đo thính lực, nội soi TMH."
        ),
        "specialties": "Tai Mũi Họng, Thính học, Thanh quản, Xoang, Amidan",
        "typical_symptoms": (
            "Đau họng, khàn tiếng, khó nuốt, đau tai, ù tai, giảm thính lực, "
            "chảy dịch tai, nghẹt mũi, chảy mũi, viêm xoang, chảy máu mũi, "
            "amidan sưng, ngủ ngáy, ngưng thở khi ngủ"
        ),
    },
    {
        "code": "RHM",
        "name": "Khoa Răng Hàm Mặt",
        "description": (
            "Khám, điều trị, phẫu thuật bệnh lý răng - miệng - hàm - mặt."
        ),
        "specialties": "Nha khoa, Phẫu thuật hàm mặt, Chỉnh nha, Nha chu, Implant",
        "typical_symptoms": (
            "Đau răng, sưng nướu, chảy máu nướu, sâu răng, áp xe răng, "
            "gãy xương hàm, khớp cắn lệch, u hàm, viêm tuyến nước bọt, "
            "đau quai hàm, miệng không há được"
        ),
    },
    {
        "code": "MAT",
        "name": "Khoa Mắt",
        "description": (
            "Khám, chẩn đoán, phẫu thuật bệnh lý mắt. "
            "Có phòng đo thị lực, sinh hiển vi, laser mắt."
        ),
        "specialties": "Nhãn khoa, Đục thủy tinh thể, Glaucoma, Võng mạc, Khúc xạ",
        "typical_symptoms": (
            "Mờ mắt, đau mắt, đỏ mắt, chảy nước mắt, mắt sưng, "
            "nhìn đôi, mất thị lực đột ngột, ruồi bay trước mắt, "
            "ngứa mắt, đau nhức hốc mắt, chấn thương mắt"
        ),
    },
    {
        "code": "DALIEU",
        "name": "Khoa Da Liễu",
        "description": (
            "Khám, chẩn đoán, điều trị bệnh lý da - niêm mạc - tóc - móng. "
            "Điều trị bệnh lây truyền qua đường tình dục."
        ),
        "specialties": "Da liễu, Bệnh da, Thẩm mỹ da, STI, Nấm da",
        "typical_symptoms": (
            "Phát ban, ngứa, nổi mụn, rụng tóc, da đổi màu, vảy nến, "
            "chàm, nổi mề đay, mụn trứng cá, nấm da, herpes, "
            "loét da, bỏng nắng nặng, dị ứng da"
        ),
    },
    {
        "code": "UB",
        "name": "Khoa Ung Bướu",
        "description": (
            "Chẩn đoán, điều trị ung thư bằng hóa trị, xạ trị, liệu pháp đích. "
            "Tầm soát ung thư."
        ),
        "specialties": "Ung thư, Hóa trị, Xạ trị, Liệu pháp miễn dịch, Tầm soát ung thư",
        "typical_symptoms": (
            "Khối u sờ thấy, sụt cân không rõ nguyên nhân, mệt mỏi kéo dài, "
            "hạch to, chảy máu bất thường, đau kéo dài không giảm, "
            "thay đổi thói quen tiêu hóa, nuốt khó tiến triển"
        ),
    },
    {
        "code": "TN",
        "name": "Khoa Tiết Niệu",
        "description": (
            "Chẩn đoán, phẫu thuật bệnh lý hệ tiết niệu - sinh dục nam. "
            "Có phòng nội soi niệu, tán sỏi."
        ),
        "specialties": "Tiết niệu, Sỏi thận, Tuyến tiền liệt, Nam khoa, Thận học",
        "typical_symptoms": (
            "Tiểu đau, tiểu rắt, tiểu máu, tiểu khó, đau hông lưng, "
            "sỏi thận, phù mặt, phù chân, tiểu đêm nhiều, "
            "bí tiểu, nhiễm trùng đường tiểu, sưng tinh hoàn"
        ),
    },
    {
        "code": "TT",
        "name": "Khoa Tâm Thần",
        "description": (
            "Chẩn đoán, điều trị bệnh lý tâm thần - tâm lý. "
            "Tư vấn tâm lý, liệu pháp hành vi nhận thức."
        ),
        "specialties": "Tâm thần, Tâm lý, Trầm cảm, Lo âu, Tâm thần phân liệt",
        "typical_symptoms": (
            "Mất ngủ kéo dài, lo âu, trầm cảm, hoang tưởng, ảo giác, "
            "stress nặng, rối loạn cảm xúc, có ý định tự hại, "
            "rối loạn ăn uống, nghiện chất, hoảng loạn"
        ),
    },
    {
        "code": "PHCN",
        "name": "Khoa Phục Hồi Chức Năng",
        "description": (
            "Phục hồi chức năng vận động, ngôn ngữ sau chấn thương, đột quỵ, "
            "phẫu thuật. Vật lý trị liệu."
        ),
        "specialties": "Phục hồi chức năng, Vật lý trị liệu, Ngôn ngữ trị liệu, Hoạt động trị liệu",
        "typical_symptoms": (
            "Yếu cơ sau đột quỵ, cứng khớp sau phẫu thuật, đau mạn tính, "
            "khó vận động, liệt sau chấn thương tủy, rối loạn nuốt, "
            "rối loạn ngôn ngữ, cần tập phục hồi chức năng"
        ),
    },
    {
        "code": "YHCT",
        "name": "Khoa Y Học Cổ Truyền",
        "description": (
            "Khám, điều trị bệnh bằng phương pháp y học cổ truyền: "
            "châm cứu, bấm huyệt, xoa bóp, thuốc nam, thuốc bắc."
        ),
        "specialties": "Y học cổ truyền, Châm cứu, Bấm huyệt, Thuốc đông y",
        "typical_symptoms": (
            "Đau lưng mạn tính, đau khớp mãn, mất ngủ, stress, "
            "tê bì tay chân, đau vai gáy, đau đầu mạn tính, "
            "rối loạn tiêu hóa mạn, cần phục hồi sức khỏe tổng quát"
        ),
    },
    # ===================== CẬN LÂM SÀNG =====================
    {
        "code": "CDHA",
        "name": "Khoa Chẩn Đoán Hình Ảnh",
        "description": (
            "Thực hiện các kỹ thuật chẩn đoán hình ảnh: X-quang, CT Scanner, "
            "MRI, siêu âm, DSA. Hỗ trợ chẩn đoán cho các khoa lâm sàng."
        ),
        "specialties": "X-quang, CT Scanner, MRI, Siêu âm, Chụp mạch (DSA)",
        "typical_symptoms": (
            "Cần chụp X-quang, CT, MRI, siêu âm để chẩn đoán. "
            "Không nhận bệnh nhân trực tiếp, chỉ qua chỉ định bác sĩ."
        ),
    },
    {
        "code": "XN",
        "name": "Khoa Xét Nghiệm",
        "description": (
            "Thực hiện xét nghiệm huyết học, sinh hóa, vi sinh, miễn dịch, "
            "giải phẫu bệnh. Hỗ trợ chẩn đoán và theo dõi điều trị."
        ),
        "specialties": "Huyết học, Sinh hóa, Vi sinh, Miễn dịch, Giải phẫu bệnh",
        "typical_symptoms": (
            "Cần xét nghiệm máu, nước tiểu, vi sinh. "
            "Không nhận bệnh nhân trực tiếp, chỉ qua chỉ định bác sĩ."
        ),
    },
    {
        "code": "DUOC",
        "name": "Khoa Dược",
        "description": (
            "Quản lý, cấp phát thuốc, kiểm soát tương tác thuốc. "
            "Dược lâm sàng tư vấn sử dụng thuốc cho bệnh nhân."
        ),
        "specialties": "Dược lâm sàng, Quản lý thuốc, Tương tác thuốc",
        "typical_symptoms": (
            "Cần cấp phát thuốc, tư vấn thuốc. "
            "Không nhận bệnh nhân trực tiếp."
        ),
    },
    {
        "code": "GMHS",
        "name": "Khoa Gây Mê Hồi Sức",
        "description": (
            "Gây mê, gây tê cho phẫu thuật. Hồi sức sau mổ, "
            "điều trị tích cực (ICU). Kiểm soát đau."
        ),
        "specialties": "Gây mê, Hồi sức tích cực (ICU), Kiểm soát đau, Gây tê vùng",
        "typical_symptoms": (
            "Cần hồi sức tích cực, suy đa cơ quan, sốc nhiễm khuẩn, "
            "suy hô hấp cần thở máy, hậu phẫu nặng."
        ),
    },
]


class Command(BaseCommand):
    help = 'Chèn dữ liệu mẫu Khoa Phòng (25+ khoa theo chuẩn BV đa khoa hạng I)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Xóa toàn bộ khoa phòng hiện có trước khi chèn lại',
        )

    def handle(self, *args, **options):
        if options['clear']:
            count = Department.objects.count()
            Department.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Đã xóa {count} khoa phòng cũ.'))

        created_count = 0
        updated_count = 0

        for dept_data in DEPARTMENTS_DATA:
            dept, created = Department.objects.update_or_create(
                code=dept_data['code'],
                defaults={
                    'name': dept_data['name'],
                    'description': dept_data['description'],
                    'specialties': dept_data['specialties'],
                    'typical_symptoms': dept_data['typical_symptoms'],
                    'is_active': True,
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1
            self.stdout.write(f"  {'✓ Tạo' if created else '↻ Cập nhật'}: {dept.code} - {dept.name}")

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Hoàn tất! Tạo mới: {created_count}, Cập nhật: {updated_count}, '
            f'Tổng trong DB: {Department.objects.count()}'
        ))
