
import os
import sys
import django
import asyncio
from typing import List

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.ai_engine.rag_service.embeddings import (
    EmbeddingService,
    embed_clinical_note,
    embed_drug_info,
    embed_medical_protocol,
    embed_hospital_process
)

async def test_embeddings():
    print("Initializing Embedding Service...")
    service = EmbeddingService(provider='google')
    
    print("\n--- Testing Clinical Note Embedding ---")
    clinical_emb = await embed_clinical_note(
        chief_complaint="Đau ngực trái, khó thở",
        history_of_present_illness="Bệnh nhân thấy đau ngực trái âm ỉ 2 ngày nay",
        physical_exam="Tim đều, T1 T2 rõ, phổi không rale",
        final_diagnosis="Theo dõi Cơn đau thắt ngực ổn định",
        treatment_plan="Chụp mạch vành, dùng thuốc giãn mạch",
        embedding_service=service
    )
    print(f"Clinical Embedding generated. Dimension: {len(clinical_emb)}")
    assert len(clinical_emb) == 768

    print("\n--- Testing Drug Info Embedding ---")
    drug_emb = await embed_drug_info(
        name="Paracetamol",
        usage="Giảm đau, hạ sốt. Người lớn 500mg-1g mỗi 4-6 giờ.",
        contraindications="Quá mẫn với paracetamol. Suy gan nặng.",
        side_effects="Hiếm gặp: ban da, rối loạn tạo máu.",
        embedding_service=service
    )
    print(f"Drug Embedding generated. Dimension: {len(drug_emb)}")
    assert len(drug_emb) == 768

    print("\n--- Testing Medical Protocol Embedding ---")
    protocol_emb = await embed_medical_protocol(
        title="Phác đồ điều trị Tăng huyết áp",
        content="Khởi đầu bằng thuốc nhóm A hoặc C...",
        category="Tim mạch",
        embedding_service=service
    )
    print(f"Protocol Embedding generated. Dimension: {len(protocol_emb)}")
    assert len(protocol_emb) == 768

    print("\n--- Testing Hospital Process Embedding ---")
    process_emb = await embed_hospital_process(
        question="Làm thế nào để xin cấp lại thẻ BHYT?",
        answer="Liên hệ quầy đón tiếp số 3, mang theo CCCD.",
        category="Thủ tục hành chính",
        embedding_service=service
    )
    print(f"Process Embedding generated. Dimension: {len(process_emb)}")
    assert len(process_emb) == 768
    
    print("\nAll embedding tests passed successfully!")

if __name__ == "__main__":
    asyncio.run(test_embeddings())
