"""
PDF Export functionality for the reminder bot.
Generates comprehensive PDF reports with reminders and vault data.
"""

import os
import tempfile
from datetime import datetime
from typing import List, Dict
import pytz
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


class PDFExporter:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()

    def setup_custom_styles(self):
        """Setup custom paragraph styles for the PDF."""
        # Title style
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )

        # Section header style
        self.section_style = ParagraphStyle(
            'SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.darkgreen
        )

        # Subsection style
        self.subsection_style = ParagraphStyle(
            'SubsectionHeader',
            parent=self.styles['Heading3'],
            fontSize=14,
            spaceAfter=8,
            spaceBefore=12,
            textColor=colors.darkred
        )

        # Normal text style
        self.normal_style = ParagraphStyle(
            'CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )

        # Small text style
        self.small_style = ParagraphStyle(
            'CustomSmall',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.grey
        )

    def generate_export_pdf(self, chat_id: int, user_info: Dict, reminders: List[Dict],
                           vault_entries: List[Dict], include_history: bool = False) -> str:
        """
        Generate a comprehensive PDF export with all user data.

        Args:
            chat_id: User's chat ID
            user_info: User information dictionary
            reminders: List of reminder dictionaries
            vault_entries: List of vault entry dictionaries
            include_history: Whether to include sent/deleted items

        Returns:
            str: Path to the generated PDF file
        """
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix='.pdf',
            prefix=f'export_chat_{chat_id}_'
        )
        temp_file.close()

        # Create PDF document
        doc = SimpleDocTemplate(
            temp_file.name,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )

        # Build story (content)
        story = []
        story.extend(self._build_header(user_info))
        story.extend(self._build_summary(reminders, vault_entries))
        story.extend(self._build_reminders_section(reminders, include_history))
        story.append(PageBreak())
        story.extend(self._build_vault_section(vault_entries, include_history))
        story.extend(self._build_footer())

        # Build PDF
        doc.build(story)

        return temp_file.name

    def _build_header(self, user_info: Dict) -> List:
        """Build the PDF header section."""
        timezone = pytz.timezone('America/Argentina/Buenos_Aires')
        now = datetime.now(timezone)

        story = []

        # Title
        title = "📋 Exportación de Datos - Bot de Recordatorios"
        story.append(Paragraph(title, self.title_style))

        # User info
        user_name = user_info.get('first_name', 'Usuario')
        if user_info.get('last_name'):
            user_name += f" {user_info['last_name']}"
        if user_info.get('username'):
            user_name += f" (@{user_info['username']})"

        user_text = f"<b>Usuario:</b> {user_name}<br/>"
        user_text += f"<b>Chat ID:</b> {user_info.get('chat_id', 'N/A')}<br/>"
        user_text += f"<b>Fecha de exportación:</b> {now.strftime('%d/%m/%Y %H:%M:%S')}<br/>"
        user_text += f"<b>Zona horaria:</b> America/Argentina/Buenos_Aires"

        story.append(Paragraph(user_text, self.normal_style))
        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
        story.append(Spacer(1, 20))

        return story

    def _build_summary(self, reminders: List[Dict], vault_entries: List[Dict]) -> List:
        """Build summary statistics section."""
        story = []

        story.append(Paragraph("📊 Resumen de Datos", self.section_style))

        # Count by status
        reminder_stats = self._count_by_status(reminders, 'status')
        vault_stats = self._count_by_status(vault_entries, 'status')

        # Count by category
        reminder_categories = self._count_by_category(reminders)
        vault_categories = self._count_by_category(vault_entries)

        # Create summary table
        summary_data = [
            ['Tipo de Dato', 'Total', 'Activos', 'Completados/Eliminados'],
            ['Recordatorios',
             str(len(reminders)),
             str(reminder_stats.get('active', 0)),
             str(reminder_stats.get('sent', 0) + reminder_stats.get('cancelled', 0))],
            ['Bitácora',
             str(len(vault_entries)),
             str(vault_stats.get('active', 0)),
             str(vault_stats.get('deleted', 0))]
        ]

        summary_table = Table(summary_data, colWidths=[2.5*inch, 1.2*inch, 1.3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
        ]))

        story.append(summary_table)
        story.append(Spacer(1, 20))

        # Categories breakdown
        if reminder_categories or vault_categories:
            story.append(Paragraph("📂 Distribución por Categorías", self.subsection_style))

            categories_data = [['Categoría', 'Recordatorios', 'Bitácora']]
            all_categories = set(reminder_categories.keys()) | set(vault_categories.keys())

            for category in sorted(all_categories):
                categories_data.append([
                    category.title(),
                    str(reminder_categories.get(category, 0)),
                    str(vault_categories.get(category, 0))
                ])

            categories_table = Table(categories_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
            categories_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightcyan),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
            ]))

            story.append(categories_table)

        story.append(Spacer(1, 30))
        return story

    def _build_reminders_section(self, reminders: List[Dict], include_history: bool) -> List:
        """Build the reminders section."""
        story = []

        story.append(Paragraph("🔔 Recordatorios", self.section_style))

        if not reminders:
            story.append(Paragraph("No hay recordatorios para mostrar.", self.normal_style))
            return story

        # Group by status
        active_reminders = [r for r in reminders if r['status'] == 'active']
        sent_reminders = [r for r in reminders if r['status'] == 'sent']
        cancelled_reminders = [r for r in reminders if r['status'] == 'cancelled']

        # Active reminders
        if active_reminders:
            story.append(Paragraph("🔔 Recordatorios Pendientes", self.subsection_style))
            story.extend(self._build_reminders_table(active_reminders))
            story.append(Spacer(1, 15))

        # Historical reminders (if requested)
        if include_history:
            if sent_reminders:
                story.append(Paragraph("✅ Recordatorios Enviados", self.subsection_style))
                story.extend(self._build_reminders_table(sent_reminders))
                story.append(Spacer(1, 15))

            if cancelled_reminders:
                story.append(Paragraph("❌ Recordatorios Cancelados", self.subsection_style))
                story.extend(self._build_reminders_table(cancelled_reminders))
                story.append(Spacer(1, 15))

        return story

    def _build_reminders_table(self, reminders: List[Dict]) -> List:
        """Build a table for reminders."""
        story = []

        if not reminders:
            return story

        # Sort by datetime
        sorted_reminders = sorted(reminders, key=lambda x: x['datetime'])

        # Create table data
        table_data = [['ID', 'Fecha/Hora', 'Categoría', 'Texto']]

        for reminder in sorted_reminders:
            formatted_datetime = reminder['datetime'].strftime('%d/%m/%Y %H:%M')
            category = reminder.get('category', 'general').title()
            text = reminder['text']

            # Use Paragraph for text column to handle wrapping
            text_paragraph = Paragraph(text, self.normal_style)

            table_data.append([
                str(reminder['id']),
                formatted_datetime,
                category,
                text_paragraph
            ])

        # Create table with better column widths for full text
        table = Table(table_data, colWidths=[0.4*inch, 1.1*inch, 0.9*inch, 4.6*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightsteelblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (2, -1), 'CENTER'),
            ('ALIGN', (3, 0), (3, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('WORDWRAP', (3, 0), (3, -1), True)
        ]))

        story.append(table)
        return story

    def _build_vault_section(self, vault_entries: List[Dict], include_history: bool) -> List:
        """Build the vault/bitácora section."""
        story = []

        story.append(Paragraph("📖 Bitácora Personal", self.section_style))

        if not vault_entries:
            story.append(Paragraph("No hay entradas en la bitácora para mostrar.", self.normal_style))
            return story

        # Group by status
        active_entries = [v for v in vault_entries if v.get('status', 'active') == 'active']
        deleted_entries = [v for v in vault_entries if v.get('status') == 'deleted']

        # Active entries
        if active_entries:
            story.append(Paragraph("📝 Entradas Activas", self.subsection_style))
            story.extend(self._build_vault_entries(active_entries))
            story.append(Spacer(1, 15))

        # Deleted entries (if requested)
        if include_history and deleted_entries:
            story.append(Paragraph("🗑️ Entradas Eliminadas", self.subsection_style))
            story.extend(self._build_vault_entries(deleted_entries))

        return story

    def _build_vault_entries(self, entries: List[Dict]) -> List:
        """Build vault entries section."""
        story = []

        if not entries:
            return story

        # Sort by creation date
        sorted_entries = sorted(entries, key=lambda x: x['created_at'], reverse=True)

        # Group by category
        by_category = {}
        for entry in sorted_entries:
            category = entry.get('category', 'general')
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(entry)

        # Create section for each category
        for category in sorted(by_category.keys()):
            category_entries = by_category[category]

            # Category header
            category_title = f"📂 {category.title()} ({len(category_entries)} entradas)"
            story.append(Paragraph(category_title, self.subsection_style))

            # Create entries table
            table_data = [['ID', 'Fecha', 'Contenido']]

            for entry in category_entries:
                formatted_date = entry['created_at'].strftime('%d/%m/%Y')
                content = entry['text']

                # Use Paragraph for content column to handle wrapping
                content_paragraph = Paragraph(content, self.normal_style)

                table_data.append([
                    str(entry['id']),
                    formatted_date,
                    content_paragraph
                ])

            # Create table with better column widths for full text
            table = Table(table_data, colWidths=[0.4*inch, 1*inch, 5.6*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightcoral),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (1, -1), 'CENTER'),
                ('ALIGN', (2, 0), (2, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 1), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('WORDWRAP', (2, 0), (2, -1), True)
            ]))

            story.append(table)
            story.append(Spacer(1, 10))

        return story

    def _build_footer(self) -> List:
        """Build PDF footer."""
        story = []

        story.append(Spacer(1, 30))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
        story.append(Spacer(1, 10))

        footer_text = (
            "📱 Generado por Bot de Recordatorios<br/>"
            "🤖 Desarrollado con Claude Code<br/>"
            f"📅 Exportado el {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        )

        story.append(Paragraph(footer_text, self.small_style))

        return story

    def _count_by_status(self, items: List[Dict], status_field: str) -> Dict[str, int]:
        """Count items by status."""
        counts = {}
        for item in items:
            status = item.get(status_field, 'unknown')
            counts[status] = counts.get(status, 0) + 1
        return counts

    def _count_by_category(self, items: List[Dict]) -> Dict[str, int]:
        """Count items by category."""
        counts = {}
        for item in items:
            category = item.get('category', 'general')
            counts[category] = counts.get(category, 0) + 1
        return counts


def cleanup_temp_file(file_path: str) -> bool:
    """Clean up temporary PDF file."""
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
            return True
    except Exception:
        pass
    return False