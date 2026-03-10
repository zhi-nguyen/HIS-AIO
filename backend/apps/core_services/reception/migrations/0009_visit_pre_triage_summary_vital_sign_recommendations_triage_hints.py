"""
Migration: Add pre_triage_summary, vital_sign_recommendations, triage_hints to Visit

These fields support the Summarize Agent → Triage Agent communication pipeline:
- pre_triage_summary: Full text summary from Summarize Agent (kiosk checkin)
- vital_sign_recommendations: List of vital sign keys the agent recommends collecting
- triage_hints: Short note from Summarize Agent for the Triage Agent to focus on
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reception', '0008_visit_pending_merge'),
    ]

    operations = [
        migrations.AddField(
            model_name='visit',
            name='pre_triage_summary',
            field=models.TextField(
                blank=True,
                help_text='Toàn bộ tóm tắt bệnh án từ Summarize Agent sau khi bệnh nhân đăng ký kiosk',
                null=True,
                verbose_name='Tóm tắt tiền phân luồng',
            ),
        ),
        migrations.AddField(
            model_name='visit',
            name='vital_sign_recommendations',
            field=models.JSONField(
                blank=True,
                help_text='Danh sách key chỉ số SH Summarize Agent khuyến nghị (VD: ["spo2", "bp_systolic"])',
                null=True,
                verbose_name='Chỉ số SH được AI đề xuất thu thập',
            ),
        ),
        migrations.AddField(
            model_name='visit',
            name='triage_hints',
            field=models.TextField(
                blank=True,
                help_text='Tóm tắt ngắn từ Summarize Agent để Agent Triage chú ý (VD: BN THA mạn - chú ý BP_SYS)',
                null=True,
                verbose_name='Lời nhắc cho Agent Phân Luồng',
            ),
        ),
    ]
