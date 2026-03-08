"""
Management command: seed_all — Chèn toàn bộ dữ liệu mẫu cho hệ thống HIS.

Bao gồm: Khoa Phòng, Staff/User, ICD-10, Thuốc, Xét nghiệm, CĐHA,
Nội trú (Ward/Room/Bed), QMS (ServiceStation), Billing, DMKT.

Usage:
    python manage.py seed_all
    python manage.py seed_all --clear   # Xóa hết rồi chèn lại
"""

from datetime import date
from django.core.management.base import BaseCommand
from django.core.management import call_command

from apps.core_services.authentication.models import User, Staff
from apps.core_services.departments.models import Department, DepartmentMember
from apps.core_services.core.models import (
    ICD10Category, ICD10Subcategory, ICD10Code, TechnicalService,
)
from apps.medical_services.pharmacy.models import (
    DrugCategory, Medication, MedicationLot,
)
from apps.medical_services.lis.models import LabCategory, LabTest
from apps.medical_services.ris.models import Modality, ImagingProcedure
from apps.medical_services.inpatients.models import (
    Ward as InpatientWard, Room, Bed,
)
from apps.core_services.qms.models import ServiceStation
from apps.core_services.billing.models import (
    PriceList, ServiceCatalog, ServicePrice,
)

from ._seed_data_staff import STAFF_DATA, DEFAULT_PASSWORD
from ._seed_data_icd10 import ICD10_CATEGORIES, ICD10_SUBCATEGORIES, ICD10_CODES
from ._seed_data_hospital import (
    DRUG_CATEGORIES, MEDICATIONS, get_lot_data,
    LAB_CATEGORIES, LAB_TESTS,
    MODALITIES, IMAGING_PROCEDURES,
    WARDS, ROOMS,
    SERVICE_STATIONS,
    PRICE_LISTS, SERVICE_CATALOG,
    TECHNICAL_SERVICES,
)


class Command(BaseCommand):
    help = 'Chèn toàn bộ dữ liệu mẫu cho hệ thống HIS (không bao gồm bệnh nhân)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear', action='store_true',
            help='Xóa toàn bộ dữ liệu seed trước khi chèn lại',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self._clear_all()

        self._header("1. KHOA PHÒNG")
        call_command('seed_departments')

        self._header("2. STAFF + USER ACCOUNTS")
        self._seed_staff()

        self._header("3. ICD-10")
        self._seed_icd10()

        self._header("4. THUỐC")
        self._seed_medications()

        self._header("5. XÉT NGHIỆM (LIS)")
        self._seed_lab()

        self._header("6. CHẨN ĐOÁN HÌNH ẢNH (RIS)")
        self._seed_imaging()

        self._header("7. NỘI TRÚ (Ward/Room/Bed)")
        self._seed_inpatient()

        self._header("8. QMS — ĐIỂM DỊCH VỤ")
        self._seed_service_stations()

        self._header("9. BẢNG GIÁ + DANH MỤC DỊCH VỤ")
        self._seed_billing()

        self._header("10. DANH MỤC KỸ THUẬT (DMKT)")
        self._seed_technical_services()

        self.stdout.write(self.style.SUCCESS(
            "\n" + "=" * 60 +
            "\n✓ HOÀN TẤT SEED TOÀN BỘ DỮ LIỆU HỆ THỐNG HIS!"
            "\n" + "=" * 60
        ))

    # ------------------------------------------------------------------ helpers
    def _header(self, title):
        self.stdout.write(self.style.MIGRATE_HEADING(f"\n{'=' * 60}\n  {title}\n{'=' * 60}"))

    def _ok(self, msg):
        self.stdout.write(f"  ✓ {msg}")

    def _clear_all(self):
        self.stdout.write(self.style.WARNING("⚠ Đang xóa toàn bộ dữ liệu seed..."))
        for model in [
            ServicePrice, ServiceCatalog, PriceList,
            Bed, Room, InpatientWard,
            ServiceStation,
            ImagingProcedure, Modality,
            LabTest, LabCategory,
            MedicationLot, Medication, DrugCategory,
            ICD10Code, ICD10Subcategory, ICD10Category,
            TechnicalService,
            DepartmentMember,
        ]:
            count = model.objects.count()
            if count:
                model.objects.all().delete()
                self.stdout.write(f"  ✗ Xóa {count} {model.__name__}")

        # Xóa Staff + User (chỉ user có email @bv.local)
        staff_users = User.objects.filter(email__endswith='@bv.local')
        cnt = staff_users.count()
        if cnt:
            Staff.objects.filter(user__in=staff_users).delete()
            staff_users.delete()
            self.stdout.write(f"  ✗ Xóa {cnt} User/Staff test")

    # ------------------------------------------------------------------ staff
    def _seed_staff(self):
        created = 0
        for email, first, last, role, code, dept_code, position in STAFF_DATA:
            # Tạo username duy nhất từ email (thêm prefix seed_ để tránh trùng)
            username = "seed_" + email.split('@')[0].replace('.', '_')

            try:
                user = User.objects.get(email=email)
                u_created = False
                # Cập nhật thông tin
                user.first_name = first
                user.last_name = last
                user.is_active = True
                user.is_staff = role == 'ADMIN'
                user.is_superuser = role == 'ADMIN'
                user.save()
            except User.DoesNotExist:
                user = User.objects.create_user(
                    email=email,
                    password=DEFAULT_PASSWORD,
                    username=username,
                    first_name=first,
                    last_name=last,
                    is_active=True,
                    is_staff=(role == 'ADMIN'),
                    is_superuser=(role == 'ADMIN'),
                )
                u_created = True

            dept_link = None
            if dept_code:
                dept_link = Department.objects.filter(code=dept_code).first()

            staff, s_created = Staff.objects.update_or_create(
                user=user,
                defaults={
                    'role': role,
                    'staff_code': code,
                    'department_link': dept_link,
                    'department': dept_link.name if dept_link else '',
                    'hire_date': date(2024, 1, 1),
                },
            )

            # DepartmentMember
            if dept_link and position:
                DepartmentMember.objects.update_or_create(
                    department=dept_link,
                    staff=staff,
                    defaults={'position': position, 'is_primary': True},
                )

            if u_created:
                created += 1
            self._ok(f"{'Tạo' if u_created else 'CN'} {email} [{role}]")

        self.stdout.write(self.style.SUCCESS(f"  → Tổng Staff: {Staff.objects.count()} (mới: {created})"))

    # ------------------------------------------------------------------ icd10
    def _seed_icd10(self):
        cat_map = {}
        for c in ICD10_CATEGORIES:
            obj, _ = ICD10Category.objects.update_or_create(
                code=c['code'], defaults={'name': c['name']}
            )
            cat_map[c['code']] = obj

        sub_map = {}
        for cat_code, sub_code, sub_name in ICD10_SUBCATEGORIES:
            cat = cat_map.get(cat_code)
            if not cat:
                continue
            obj, _ = ICD10Subcategory.objects.update_or_create(
                code=sub_code, defaults={'name': sub_name, 'category': cat}
            )
            sub_map[sub_code] = obj

        code_count = 0
        for sub_code, icd_code, icd_name, desc in ICD10_CODES:
            sub = sub_map.get(sub_code)
            if not sub:
                continue
            ICD10Code.objects.update_or_create(
                code=icd_code,
                defaults={'name': icd_name, 'description': desc, 'subcategory': sub},
            )
            code_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"  → {len(cat_map)} categories, {len(sub_map)} subcategories, {code_count} codes"
        ))

    # ------------------------------------------------------------------ meds
    def _seed_medications(self):
        cat_map = {}
        for cat_name in DRUG_CATEGORIES:
            obj, _ = DrugCategory.objects.update_or_create(name=cat_name)
            cat_map[cat_name] = obj

        lot_info = get_lot_data()
        med_count = 0
        for cat_name, code, name, ai, strength, form, route, unit, pp, sp, rx in MEDICATIONS:
            cat = cat_map.get(cat_name)
            med, _ = Medication.objects.update_or_create(
                code=code,
                defaults={
                    'category': cat, 'name': name, 'active_ingredient': ai,
                    'strength': strength, 'dosage_form': form, 'usage_route': route,
                    'unit': unit, 'purchase_price': pp, 'selling_price': sp,
                    'requires_prescription': rx, 'is_active': True,
                    'inventory_count': lot_info['initial_quantity'],
                    'min_stock': 50,
                },
            )
            lot_num = f"{lot_info['lot_number_prefix']}-{code}-001"
            MedicationLot.objects.update_or_create(
                medication=med, lot_number=lot_num,
                defaults={
                    'expiry_date': lot_info['expiry_date'],
                    'manufacture_date': lot_info['manufacture_date'],
                    'initial_quantity': lot_info['initial_quantity'],
                    'remaining_quantity': lot_info['initial_quantity'],
                    'import_date': lot_info['import_date'],
                    'import_price': pp,
                    'supplier': lot_info['supplier'],
                },
            )
            med_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"  → {len(cat_map)} nhóm thuốc, {med_count} thuốc (mỗi thuốc 1 lô)"
        ))

    # ------------------------------------------------------------------ lab
    def _seed_lab(self):
        cat_map = {}
        for name, desc in LAB_CATEGORIES:
            obj, _ = LabCategory.objects.update_or_create(name=name, defaults={'description': desc})
            cat_map[name] = obj

        test_count = 0
        for cat_name, code, name, unit, low, high, tat, price in LAB_TESTS:
            cat = cat_map.get(cat_name)
            if not cat:
                continue
            defaults = {
                'category': cat, 'name': name, 'price': price,
                'turnaround_time': tat,
            }
            if unit:
                defaults['unit'] = unit
            if low is not None:
                defaults['min_limit'] = low
            if high is not None:
                defaults['max_limit'] = high
            LabTest.objects.update_or_create(code=code, defaults=defaults)
            test_count += 1

        self.stdout.write(self.style.SUCCESS(f"  → {len(cat_map)} nhóm, {test_count} chỉ số XN"))

    # ------------------------------------------------------------------ imaging
    def _seed_imaging(self):
        mod_map = {}
        for code, name, desc, tat in MODALITIES:
            obj, _ = Modality.objects.update_or_create(
                code=code, defaults={'name': name, 'turnaround_time': tat}
            )
            mod_map[code] = obj

        proc_count = 0
        for mod_code, code, name, price, prep in IMAGING_PROCEDURES:
            mod = mod_map.get(mod_code)
            if not mod:
                continue
            # Extract body_part from name (e.g. 'X-Quang ngực thẳng' -> 'Ngực')
            body_part = name.split(' ', 1)[-1] if ' ' in name else name
            defaults = {'modality': mod, 'name': name, 'price': price, 'body_part': body_part}
            if prep:
                defaults['preparation'] = prep
            ImagingProcedure.objects.update_or_create(code=code, defaults=defaults)
            proc_count += 1

        self.stdout.write(self.style.SUCCESS(f"  → {len(mod_map)} loại máy, {proc_count} kỹ thuật"))

    # ------------------------------------------------------------------ inpatient
    def _seed_inpatient(self):
        ward_map = {}
        for dept_code, w_code, w_name, total_beds, floor in WARDS:
            dept = Department.objects.filter(code=dept_code).first()
            if not dept:
                continue
            ward, _ = InpatientWard.objects.update_or_create(
                code=w_code,
                defaults={'department': dept, 'name': w_name, 'total_beds': total_beds, 'floor': floor},
            )
            ward_map[w_code] = ward

        room_map = {}
        total_beds = 0
        for w_code, room_num, room_type, cap, price, bath, ac in ROOMS:
            ward = ward_map.get(w_code)
            if not ward:
                continue
            room, _ = Room.objects.update_or_create(
                ward=ward, room_number=room_num,
                defaults={
                    'room_type': room_type, 'capacity': cap,
                    'price_per_day': price, 'has_bathroom': bath, 'has_ac': ac,
                },
            )
            room_map[(w_code, room_num)] = room

            # Tạo giường cho mỗi phòng
            for i in range(1, cap + 1):
                bed_num = f"{room_num}-G{i:02d}"
                Bed.objects.update_or_create(
                    room=room, bed_number=bed_num,
                    defaults={'status': 'AVAILABLE'},
                )
                total_beds += 1

        self.stdout.write(self.style.SUCCESS(
            f"  → {len(ward_map)} ward, {len(room_map)} phòng, {total_beds} giường"
        ))

    # ------------------------------------------------------------------ QMS
    def _seed_service_stations(self):
        count = 0
        for code, name, stype, dept_code, location in SERVICE_STATIONS:
            dept = None
            if dept_code:
                dept = Department.objects.filter(code=dept_code).first()
            ServiceStation.objects.update_or_create(
                code=code,
                defaults={
                    'name': name, 'station_type': stype,
                    'department': dept, 'room_location': location,
                    'is_active': True,
                },
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f"  → {count} điểm dịch vụ"))

    # ------------------------------------------------------------------ billing
    def _seed_billing(self):
        pl_map = {}
        for code, name, is_default, is_active in PRICE_LISTS:
            obj, _ = PriceList.objects.update_or_create(
                code=code,
                defaults={
                    'name': name, 'is_default': is_default, 'is_active': is_active,
                    'effective_from': date(2024, 1, 1),
                },
            )
            pl_map[code] = obj

        svc_count = 0
        for code, name, stype, base, bhyt_code, bhyt_price in SERVICE_CATALOG:
            svc, _ = ServiceCatalog.objects.update_or_create(
                code=code,
                defaults={
                    'name': name, 'service_type': stype,
                    'base_price': base,
                    'bhyt_code': bhyt_code, 'bhyt_price': bhyt_price,
                },
            )
            # Giá cho bảng giá thường = base_price
            pl_thuong = pl_map.get('BG-THUONG')
            if pl_thuong:
                ServicePrice.objects.update_or_create(
                    service=svc, price_list=pl_thuong,
                    defaults={'price': base},
                )
            # Giá cho bảng giá BHYT
            if bhyt_price:
                pl_bhyt = pl_map.get('BG-BHYT')
                if pl_bhyt:
                    ServicePrice.objects.update_or_create(
                        service=svc, price_list=pl_bhyt,
                        defaults={'price': bhyt_price},
                    )
            svc_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"  → {len(pl_map)} bảng giá, {svc_count} dịch vụ"
        ))

    # ------------------------------------------------------------------ DMKT
    def _seed_technical_services(self):
        count = 0
        for code, name, group, unit, price, bhyt_price, is_bhyt in TECHNICAL_SERVICES:
            TechnicalService.objects.update_or_create(
                code=code,
                defaults={
                    'name': name, 'group': group, 'unit': unit,
                    'unit_price': price, 'bhyt_price': bhyt_price,
                    'is_covered_by_bhyt': is_bhyt, 'is_active': True,
                },
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f"  → {count} dịch vụ kỹ thuật"))
