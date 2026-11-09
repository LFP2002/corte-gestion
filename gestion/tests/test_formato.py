from decimal import Decimal

from django.test import SimpleTestCase

from gestion.templatetags.moneda import clp


class FormatoMonedaTests(SimpleTestCase):
    def test_pesos_chilenos_sin_centavos(self):
        self.assertEqual(clp(Decimal('60000.00')), '$60.000')
        self.assertEqual(clp(Decimal('8000.00')), '$8.000')
        self.assertEqual(clp(Decimal('0.00')), '$0')

    def test_conserva_centavos_reales(self):
        self.assertEqual(clp(Decimal('1234.50')), '$1.234,50')
        self.assertEqual(clp(Decimal('2.81')), '$2,81')
        self.assertEqual(clp(Decimal('-1234.50')), '-$1.234,50')

    def test_valores_no_numericos(self):
        self.assertEqual(clp(None), '—')
        self.assertEqual(clp('abc'), '—')
