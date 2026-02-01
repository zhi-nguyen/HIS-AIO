from django.db import transaction
from django.utils import timezone
from .models import LabOrder, LabOrderDetail, LabTest, LabResult, LabCategory
from apps.medical_services.reception.models import Visit
from apps.core_services.authentication.models import Staff
from apps.medical_services.patients.models import Patient

def create_lab_order(visit_id: str, test_codes: list[str], doctor_id: str, note: str = None) -> LabOrder:
    """
    Creates a new Lab Order for a visit based on a list of test codes.
    """
    try:
        visit = Visit.objects.get(id=visit_id)
        doctor = Staff.objects.get(id=doctor_id)
        
        # Verify doctor role? (Optional check: if doctor.role != 'DOCTOR')

        with transaction.atomic():
            order = LabOrder.objects.create(
                visit=visit,
                patient=visit.patient,
                doctor=doctor,
                status=LabOrder.Status.PENDING,
                note=note
            )

            tests = LabTest.objects.filter(code__in=test_codes)
            if not tests:
                raise ValueError("No valid test codes provided.")

            for test in tests:
                LabOrderDetail.objects.create(
                    order=order,
                    test=test,
                    price_at_time=test.price
                )
            
            return order

    except (Visit.DoesNotExist, Staff.DoesNotExist) as e:
        raise ValueError(f"Invalid reference: {str(e)}")
    except Exception as e:
        raise ValueError(f"Could not create order: {str(e)}")

def input_lab_result(order_id: str, test_code: str, value_string: str, technician_id: str = None) -> LabResult:
    """
    Inputs a result for a specific test in an order.
    Auto-calculates abnormality based on min/max limits if value is numeric.
    """
    try:
        order = LabOrder.objects.get(id=order_id)
        test = LabTest.objects.get(code=test_code)
        
        detail = LabOrderDetail.objects.get(order=order, test=test)
        
        technician = None
        if technician_id:
            technician = Staff.objects.get(id=technician_id)

        # Basic numeric parsing logic
        value_numeric = None
        is_abnormal = False
        is_critical = False

        try:
            value_numeric = float(value_string)
            if test.min_limit is not None and value_numeric < test.min_limit:
                is_abnormal = True
            if test.max_limit is not None and value_numeric > test.max_limit:
                is_abnormal = True
            
            # Simple mock critical logic (e.g. 20% deviation)
            # In real life, specific critical limits exist.
            if is_abnormal:
                 # Check if way out of bounds (mock)
                 pass 

        except ValueError:
            pass # Not a number, just text result

        result, created = LabResult.objects.update_or_create(
            detail=detail,
            defaults={
                'value_string': value_string,
                'value_numeric': value_numeric,
                'is_abnormal': is_abnormal,
                'is_critical': is_critical,
                'technician': technician,
                'result_time': timezone.now()
            }
        )

        # Check if all details have results -> Update Order Status to COMPLETED
        # This is a simple check.
        total_details = order.details.count()
        completed_details = LabResult.objects.filter(detail__order=order).count()
        
        if completed_details >= total_details:
             order.status = LabOrder.Status.COMPLETED
             order.save()
        elif order.status == LabOrder.Status.PENDING:
             order.status = LabOrder.Status.PROCESSING
             order.save()

        return result

    except Exception as e:
        raise ValueError(f"Error inputting result: {str(e)}")

def get_patient_lab_history(patient_id: str, category_name: str = None) -> list[dict]:
    """
    Retrieves historical lab results for a patient, optionally filtering by category.
    Returns a list of simplified result dicts.
    """
    results_query = LabResult.objects.filter(
        detail__order__patient_id=patient_id
    ).select_related('detail__test', 'detail__test__category', 'detail__order')

    if category_name:
        results_query = results_query.filter(detail__test__category__name__icontains=category_name)

    history = []
    for res in results_query.order_by('-result_time'):
        history.append({
            "date": res.result_time.strftime("%Y-%m-%d %H:%M"),
            "test_name": res.detail.test.name,
            "category": res.detail.test.category.name,
            "value": res.value_string,
            "unit": res.detail.test.unit,
            "is_abnormal": res.is_abnormal
        })
    
    return history
