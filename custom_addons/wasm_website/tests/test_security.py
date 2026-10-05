# -*- coding: utf-8 -*-
import uuid
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestQuoteAccessToken(TransactionCase):
    """Tests for access_token security feature on wasm.quote.request."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.quote = cls.env['wasm.quote.request'].create({
            'customer_name': 'عميل أمان',
            'phone': '0501234567',
            'email': 'security@test.com',
            'project_location': 'الرياض',
            'department': 'sales',
            'customer_type': 'company',
            'project_type': 'commercial',
        })

    def test_access_token_generated_on_create(self):
        """Test that access_token is auto-generated when creating a quote."""
        self.assertTrue(self.quote.access_token)
        self.assertEqual(len(self.quote.access_token), 36)

    def test_access_token_is_valid_uuid(self):
        """Test that access_token is a valid UUID4 string."""
        try:
            uuid.UUID(self.quote.access_token, version=4)
        except ValueError:
            self.fail("access_token is not a valid UUID4")

    def test_access_token_unique_per_record(self):
        """Test that each quote gets a unique access_token."""
        quote2 = self.env['wasm.quote.request'].create({
            'customer_name': 'عميل ثاني',
            'phone': '0509876543',
            'email': 'unique@test.com',
            'project_location': 'جدة',
            'department': 'engineering',
            'customer_type': 'individual',
            'project_type': 'residential',
        })
        self.assertNotEqual(self.quote.access_token, quote2.access_token)

    def test_access_token_not_copied(self):
        """Test that access_token is not copied when duplicating a quote."""
        quote_copy = self.quote.copy()
        self.assertTrue(quote_copy.access_token)
        self.assertNotEqual(self.quote.access_token, quote_copy.access_token)

    def test_access_token_searchable(self):
        """Test that quotes can be found by access_token."""
        found = self.env['wasm.quote.request'].search(
            [('access_token', '=', self.quote.access_token)], limit=1
        )
        self.assertEqual(found.id, self.quote.id)

    def test_invalid_token_returns_empty(self):
        """Test that invalid token returns no results."""
        found = self.env['wasm.quote.request'].search(
            [('access_token', '=', 'invalid-fake-token-12345')], limit=1
        )
        self.assertFalse(found)

    def test_sequence_uses_non_translated_sentinel(self):
        """Test that sequence generation uses 'New' sentinel (not translated)."""
        quote = self.env['wasm.quote.request'].create({
            'customer_name': 'Test Sentinel',
            'phone': '0501111111',
            'email': 'sentinel@test.com',
            'project_location': 'Dammam',
            'department': 'sales',
        })
        self.assertNotEqual(quote.name, 'New')
        self.assertTrue(quote.name.startswith('ARFA-RFQ-'))
