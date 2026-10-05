# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestWasmQuoteRequest(TransactionCase):
    """Automated tests for wasm.quote.request model (Total Quality Protocol)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.service = cls.env['wasm.service'].create({
            'name': 'Test Service',
            'icon': 'fa-wrench',
            'category': 'civil',
            'short_description': 'Test service description',
        })

    def _create_quote(self, vals=None):
        """Helper to create a quote request with default values."""
        default_vals = {
            'customer_name': 'عميل اختبار',
            'phone': '0501234567',
            'email': 'test@example.com',
            'customer_type': 'company',
            'project_type': 'commercial',
            'project_location': 'الرياض',
            'department': 'sales',
        }
        if vals:
            default_vals.update(vals)
        return self.env['wasm.quote.request'].create(default_vals)

    def test_sequence_generation(self):
        """Test that creating a quote auto-generates a reference number."""
        quote = self._create_quote()
        self.assertTrue(quote.name)
        self.assertNotEqual(quote.name, 'جديد')
        self.assertTrue(quote.name.startswith('ARFA-RFQ-'))

    def test_default_state_is_new(self):
        """Test that new quotes start in 'new' state."""
        quote = self._create_quote()
        self.assertEqual(quote.state, 'new')

    def test_state_transitions(self):
        """Test full state transition workflow."""
        quote = self._create_quote()
        self.assertEqual(quote.state, 'new')

        quote.action_under_review()
        self.assertEqual(quote.state, 'under_review')

        quote.action_contacted()
        self.assertEqual(quote.state, 'contacted')

        quote.action_pricing()
        self.assertEqual(quote.state, 'pricing')

        quote.action_offer_sent()
        self.assertEqual(quote.state, 'offer_sent')

        quote.action_contracted()
        self.assertEqual(quote.state, 'contracted')

    def test_state_transition_returns_boolean(self):
        """Test that state transition methods return True (ORM write contract)."""
        quote = self._create_quote()
        result = quote.action_under_review()
        self.assertTrue(result)

    def test_attachment_count_compute(self):
        """Test that attachment_count is computed correctly."""
        quote = self._create_quote()
        self.assertEqual(quote.attachment_count, 0)

        attachment = self.env['ir.attachment'].create({
            'name': 'test_file.pdf',
            'datas': 'dGVzdA==',  # base64 'test'
            'res_model': 'wasm.quote.request',
            'res_id': quote.id,
        })
        quote.write({'attachment_ids': [(6, 0, [attachment.id])]}) 
        self.assertEqual(quote.attachment_count, 1)

    def test_currency_id_default(self):
        """Test that currency_id defaults to company currency."""
        quote = self._create_quote()
        self.assertEqual(quote.currency_id, self.env.company.currency_id)

    def test_service_link(self):
        """Test linking a service to a quote."""
        quote = self._create_quote({'service_id': self.service.id})
        self.assertEqual(quote.service_id, self.service)

    def test_close_action(self):
        """Test closing a quote request."""
        quote = self._create_quote()
        quote.action_closed()
        self.assertEqual(quote.state, 'closed')
